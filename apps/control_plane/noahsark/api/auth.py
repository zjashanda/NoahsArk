"""Development account login for the local control plane.

This is an explicitly development-only surface.  It exists so the console can
obtain a server-side session instead of trusting ``X-NoahsArk-Role``.  The
header path remains available in ``dev_headers`` mode for backward
compatibility and is never treated as production authentication.

Security properties:

* passwords are verified with Argon2id via ``services.passwords``;
* unknown users run a dummy verification and get the same ``401`` shape as a
  wrong password, so the endpoint does not confirm account existence;
* every success and denial appends one hash-chained audit event;
* the response contains the one-time token but never a password or digest.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..domain.permissions import capabilities_for, normalize_role
from ..errors import ApiError, unauthorized
from ..models import User
from ..services import audit, passwords, sessions
from .deps import Principal, get_principal
from .envelope import correlation_id, success, utc_iso

router = APIRouter(tags=["auth"])

Session = Annotated[AsyncSession, Depends(get_session)]

DEV_AUTH_MODES = frozenset(
    {"dev", "dev_headers", "header", "headers", "session", "sessions"}
)
INVALID_CREDENTIALS = "Invalid username or password"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    # ``password`` is the wire field; the Python attribute avoids echoing it in
    # logs, reprs or validation errors.
    secret: SecretStr = Field(alias="password")

    model_config = ConfigDict(populate_by_name=True)


def _dev_login_allowed() -> bool:
    if not settings.dev_session_enabled:
        return False
    return normalize_role(settings.auth_mode).lower() in DEV_AUTH_MODES


async def _audit_attempt(
    session: AsyncSession,
    request: Request,
    *,
    username: str,
    decision: str,
    reason: str,
    role: str = "UNKNOWN",
    actor_id=None,
    session_id: str | None = None,
) -> None:
    payload: dict[str, object] = {
        "decision": decision,
        "reason": reason,
        "role": role,
    }
    if session_id is not None:
        payload["session_id"] = session_id
    await audit.append_event(
        session,
        actor_role=role if decision == "ALLOW" else "UNKNOWN",
        actor_id=actor_id,
        action="AUTH_LOGIN",
        object_type="user_account",
        object_id=username or "<empty>",
        before=None,
        after=payload,
        reason=reason,
        correlation_id=correlation_id(request),
        path=request.url.path,
        access_decision=decision,
        result="SUCCESS" if decision == "ALLOW" else "DENIED",
    )


@router.post("/auth/dev-login")
async def dev_login(
    body: LoginRequest,
    request: Request,
    session: Session,
) -> dict:
    """Verify a local account and issue a server-side session token."""

    if not _dev_login_allowed():
        raise ApiError(
            403,
            "DEV_LOGIN_DISABLED",
            "The development login endpoint is disabled in this configuration",
            retryable=False,
        )

    username = body.username.strip()
    submitted = body.secret.get_secret_value()
    user = (
        await session.execute(select(User).where(User.display_id == username))
    ).scalar_one_or_none()

    if user is None:
        passwords.verify_dummy(submitted)
        await _audit_attempt(
            session,
            request,
            username=username,
            decision="DENY",
            reason="unknown_user",
        )
        await session.commit()
        raise unauthorized(INVALID_CREDENTIALS, code="INVALID_CREDENTIALS")

    if user.status != "ACTIVE" or not user.password_hash:
        passwords.verify_dummy(submitted)
        await _audit_attempt(
            session,
            request,
            username=username,
            decision="DENY",
            reason="account_not_loginable",
            role=user.role_code,
            actor_id=user.user_id,
        )
        await session.commit()
        raise unauthorized(INVALID_CREDENTIALS, code="INVALID_CREDENTIALS")

    if not passwords.verify_password(submitted, user.password_hash):
        await _audit_attempt(
            session,
            request,
            username=username,
            decision="DENY",
            reason="bad_credential",
            role=user.role_code,
            actor_id=user.user_id,
        )
        await session.commit()
        raise unauthorized(INVALID_CREDENTIALS, code="INVALID_CREDENTIALS")

    try:
        capabilities = capabilities_for(user.role_code)
    except ApiError:
        await _audit_attempt(
            session,
            request,
            username=username,
            decision="DENY",
            reason="role_not_permitted",
            role=user.role_code,
            actor_id=user.user_id,
        )
        await session.commit()
        raise

    issued = await sessions.issue_session(
        session,
        role=user.role_code,
        actor=user.display_id,
        actor_id=user.user_id,
        ttl_seconds=settings.session_ttl_seconds,
    )
    await _audit_attempt(
        session,
        request,
        username=username,
        decision="ALLOW",
        reason="password_verified",
        role=user.role_code,
        actor_id=user.user_id,
        session_id=str(issued.record.session_id),
    )
    await session.commit()

    return success(
        request,
        {
            "token": issued.token,
            "token_type": "Bearer",
            "session_id": str(issued.record.session_id),
            "actor": user.display_id,
            "role": user.role_code,
            "capabilities": sorted(capability.value for capability in capabilities),
            "issued_at": utc_iso(issued.record.issued_at),
            "expires_at": utc_iso(issued.record.expires_at),
        },
    )


@router.get("/auth/session")
async def current_session(
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> dict:
    """Describe the caller's active identity without exposing credentials."""

    capabilities = capabilities_for(principal.role)
    return success(
        request,
        {
            "actor": principal.actor,
            "role": principal.role,
            "capabilities": sorted(capability.value for capability in capabilities),
            "auth_method": principal.auth_method,
            "authenticated": principal.authenticated,
            "session_id": (
                str(principal.session_id) if principal.session_id is not None else None
            ),
        },
    )


@router.post("/auth/logout")
async def logout(
    request: Request,
    session: Session,
    principal: Annotated[Principal, Depends(get_principal)],
) -> dict:
    """Revoke the presented session immediately."""

    if principal.session_id is None:
        raise unauthorized(
            "A server-side session token is required to log out",
            code="SESSION_REQUIRED",
        )
    record = await sessions.revoke_session(
        session,
        principal.session_id,
        reason="logout",
        now=datetime.now(UTC),
    )
    await audit.append_event(
        session,
        actor_role=principal.role,
        actor_id=principal.actor_id,
        action="AUTH_LOGOUT",
        object_type="session",
        object_id=str(record.session_id),
        before=None,
        after={"revoked": True},
        reason="logout",
        correlation_id=correlation_id(request),
        path=request.url.path,
    )
    await session.commit()
    return success(
        request,
        {
            "revoked": True,
            "session_id": str(record.session_id),
            "revoked_at": utc_iso(record.revoked_at),
        },
    )
