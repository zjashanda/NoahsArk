"""Authentication abstraction.

The request layer depends on a ``Principal`` only.  Providers decide how a
principal is established; every failure path is closed:

* unknown role -> ``403 FORBIDDEN``
* missing/expired/revoked session -> ``401``
* unconfigured or unimplemented OIDC -> ``503`` (never anonymous fallback)

``DevHeaderProvider`` preserves the pre-W1 header behavior by default and is
the only provider wired for the current development surface.  ``OIDCProvider``
is an explicit stub; it never pretends to validate a token.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.permissions import VALID_ROLES, capabilities_for, normalize_role
from ..errors import ApiError, forbidden, unauthorized
from . import sessions


@dataclass(frozen=True)
class Principal:
    role: str
    actor: str | None = None
    header_role: str | None = None
    actor_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    auth_method: str = "dev-header"
    authenticated: bool = False

    @property
    def is_observer(self) -> bool:
        return self.role == "OBSERVER"


@dataclass(frozen=True)
class Credentials:
    role_header: str | None = None
    actor_header: str | None = None
    session_token: str | None = None


class AuthProvider(Protocol):
    """Contract every identity source implements."""

    name: str

    async def authenticate(
        self,
        credentials: Credentials,
        session: AsyncSession | None = None,
    ) -> Principal: ...


class DevHeaderProvider:
    """Development identity from ``X-NoahsArk-Role``/``X-NoahsArk-Actor``.

    With ``require_session=True`` the header path is disabled and a valid
    server-side session token is mandatory.
    """

    name = "dev-header"

    def __init__(self, *, require_session: bool = False) -> None:
        self.require_session = require_session

    async def authenticate(
        self,
        credentials: Credentials,
        session: AsyncSession | None = None,
    ) -> Principal:
        if credentials.session_token:
            if session is None:
                raise ApiError(
                    503,
                    "AUTH_UNAVAILABLE",
                    "Session validation is unavailable; refusing to fall back to headers",
                    retryable=True,
                )
            record = await sessions.resolve_session(session, credentials.session_token)
            capabilities_for(record.role_code)  # fail closed if stored role is invalid
            return Principal(
                role=record.role_code,
                actor=record.actor,
                header_role=credentials.role_header,
                actor_id=record.actor_id,
                session_id=record.session_id,
                auth_method="session",
                authenticated=True,
            )

        if self.require_session:
            raise unauthorized(
                "A session token is required for this deployment",
                code="SESSION_REQUIRED",
            )

        raw = credentials.role_header
        role = normalize_role(raw) or "OBSERVER"
        if role not in VALID_ROLES:
            raise forbidden(
                f"Unknown role header {raw!r}; expected one of "
                + ", ".join(sorted(VALID_ROLES)),
                details={"header": "X-NoahsArk-Role", "valid_roles": sorted(VALID_ROLES)},
            )
        return Principal(
            role=role,
            actor=credentials.actor_header,
            header_role=raw,
            auth_method="dev-header",
            authenticated=False,
        )


class OIDCProvider:
    """OIDC stub.  Fails closed until real token verification is implemented."""

    name = "oidc"

    def __init__(
        self,
        *,
        issuer: str | None = None,
        audience: str | None = None,
        jwks_url: str | None = None,
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self.jwks_url = jwks_url

    @property
    def configured(self) -> bool:
        return bool(self.issuer and self.audience and self.jwks_url)

    async def authenticate(
        self,
        credentials: Credentials,
        session: AsyncSession | None = None,
    ) -> Principal:
        if not credentials.session_token:
            raise unauthorized(
                "An OIDC bearer token is required",
                code="OIDC_TOKEN_REQUIRED",
            )
        if not self.configured:
            raise ApiError(
                503,
                "AUTH_PROVIDER_UNAVAILABLE",
                "OIDC is selected but not configured",
                retryable=True,
            )
        raise ApiError(
            503,
            "OIDC_NOT_IMPLEMENTED",
            "OIDC token verification is not implemented in this build",
            retryable=True,
        )


def build_provider(
    mode: str | None,
    *,
    issuer: str | None = None,
    audience: str | None = None,
    jwks_url: str | None = None,
) -> AuthProvider:
    """Select a provider; unknown modes fail closed."""

    normalized = (mode or "dev_headers").strip().lower()
    if normalized in {"dev", "dev_headers", "header", "headers"}:
        return DevHeaderProvider(require_session=False)
    if normalized in {"session", "sessions"}:
        return DevHeaderProvider(require_session=True)
    if normalized == "oidc":
        return OIDCProvider(issuer=issuer, audience=audience, jwks_url=jwks_url)
    raise ApiError(
        503,
        "AUTH_MODE_INVALID",
        f"Unsupported auth mode {mode!r}",
        retryable=False,
        details={"auth_mode": mode},
    )
