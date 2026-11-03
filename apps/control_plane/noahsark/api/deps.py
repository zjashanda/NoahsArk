"""FastAPI identity dependencies.

Authentication is delegated to ``services.auth`` providers.  The default
``dev_headers`` mode keeps the pre-W1 header contract: a blank role means
OBSERVER, an unknown role fails closed with 403.  A supplied session token is
always validated server-side and can never be downgraded to its header claims.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_optional_session
from ..domain.permissions import Capability, ensure_capability
from ..errors import ApiError, forbidden
from ..integrations.opencode.errors import OpenCodeConfigError
from ..integrations.opencode.http_provider import OpenCodeHTTPProvider
from ..integrations.opencode.protocol import OpenCodeProvider
from ..services.auth import Credentials, Principal, build_provider
from ..supervisor.config import SupervisorSettings

ROLE_OBSERVER = "OBSERVER"
ROLE_APPROVER = "APPROVER"
ROLE_SESSION_MANAGER = "SESSION_MANAGER"
ROLE_ADMIN = "ADMIN"
VALID_ROLES = frozenset({ROLE_OBSERVER, ROLE_APPROVER, ROLE_SESSION_MANAGER, ROLE_ADMIN})

CAP_READ = "READ"
CAP_CREATE_TASK = "CREATE_TASK"
CAP_APPROVE = "APPROVE"
CAP_STOP = "STOP"
CAP_RELEASE = "RELEASE"
CAP_DEVICE_CONTROL = "DEVICE_CONTROL"
CAP_EVIDENCE_WRITE = "EVIDENCE_WRITE"
CAP_EVIDENCE_RAW = "EVIDENCE_RAW"
CAP_VERDICT_WRITE = "VERDICT_WRITE"
CAP_REPORT_WRITE = "REPORT_WRITE"
CAP_KNOWLEDGE_PROMOTE = "KNOWLEDGE_PROMOTE"
CAP_KNOWLEDGE_MERGE_COMMON = "KNOWLEDGE_MERGE_COMMON"
CAP_KNOWLEDGE_MERGE_TOOL = "KNOWLEDGE_MERGE_TOOL"
CAP_KNOWLEDGE_PROMOTE_ANOMALY = "KNOWLEDGE_PROMOTE_ANOMALY"

ALL_CAPABILITIES = frozenset(
    {
        CAP_READ,
        CAP_CREATE_TASK,
        CAP_APPROVE,
        CAP_STOP,
        CAP_RELEASE,
        CAP_DEVICE_CONTROL,
        CAP_EVIDENCE_WRITE,
        CAP_EVIDENCE_RAW,
        CAP_VERDICT_WRITE,
        CAP_REPORT_WRITE,
        CAP_KNOWLEDGE_PROMOTE,
        CAP_KNOWLEDGE_MERGE_COMMON,
        CAP_KNOWLEDGE_MERGE_TOOL,
        CAP_KNOWLEDGE_PROMOTE_ANOMALY,
    }
)

# Explicit allow-list.  Evaluation is explicit DENY -> explicit ALLOW ->
# default DENY, so an unknown role or an unlisted capability never falls open.
ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    ROLE_OBSERVER: frozenset({CAP_READ}),
    ROLE_APPROVER: frozenset({CAP_READ, CAP_CREATE_TASK, CAP_APPROVE}),
    ROLE_SESSION_MANAGER: frozenset(
        {CAP_READ, CAP_CREATE_TASK, CAP_STOP, CAP_RELEASE, CAP_DEVICE_CONTROL}
    ),
    ROLE_ADMIN: ALL_CAPABILITIES,
}


async def get_principal(
    x_noahsark_role: str | None = Header(default=None, alias="X-NoahsArk-Role"),
    x_noahsark_actor: str | None = Header(default=None, alias="X-NoahsArk-Actor"),
    x_noahsark_session: str | None = Header(default=None, alias="X-NoahsArk-Session"),
    session: Annotated[AsyncSession | None, Depends(get_optional_session)] = None,
) -> Principal:
    provider = build_provider(
        settings.auth_mode,
        issuer=settings.oidc_issuer,
        audience=settings.oidc_audience,
        jwks_url=settings.oidc_jwks_url,
    )
    return await provider.authenticate(
        Credentials(
            role_header=x_noahsark_role,
            actor_header=x_noahsark_actor,
            session_token=x_noahsark_session,
        ),
        session,
    )


def require_roles(*allowed: str) -> Callable:
    """Reusable dependency factory for future writes.  Default deny."""

    allowed_set = frozenset(allowed)

    async def dependency(
        principal: Annotated[Principal, Depends(get_principal)],
    ) -> Principal:
        if principal.role not in allowed_set:
            raise forbidden(
                f"Role {principal.role} is not allowed for this operation",
                details={"required_roles": sorted(allowed_set), "actual_role": principal.role},
            )
        return principal

    return dependency


# Convenience dependencies reserved for the future write surface.
require_approver = require_roles(ROLE_APPROVER, ROLE_ADMIN)
require_session_manager = require_roles(ROLE_SESSION_MANAGER, ROLE_ADMIN)
require_admin = require_roles(ROLE_ADMIN)


def require_capability(capability: Capability | str) -> Callable:
    """Dependency factory: server-side capability check for a write route.

    The role header is an identity claim only; the decision is made here from
    the domain role map.  Unknown roles fail closed inside ``ensure_capability``.
    ``capability`` may be the enum or its string code; it is normalized once so
    the 403 error path never receives a bare string.
    """

    required = capability if isinstance(capability, Capability) else Capability(capability)

    async def dependency(
        principal: Annotated[Principal, Depends(get_principal)],
    ) -> Principal:
        ensure_capability(principal.role, required)
        return principal

    return dependency


async def get_opencode_provider() -> AsyncIterator[OpenCodeProvider]:
    """Yield the configured, single-attempt OpenCode read client.

    The provider is constructed per request so the API follows the same
    environment configuration as the supervisor worker.  Missing configuration
    is a typed 502 rather than a silent fallback to fake content.
    """

    try:
        config = SupervisorSettings().provider_config()
    except (OpenCodeConfigError, ValueError) as exc:
        provider_code = (
            exc.code
            if isinstance(exc, OpenCodeConfigError)
            else "OPENCODE_CONFIG_INVALID"
        )
        raise ApiError(
            502,
            "PROVIDER_UNAVAILABLE",
            "OpenCode provider is not configured",
            retryable=True,
            details={"provider_code": provider_code},
        ) from exc
    provider = OpenCodeHTTPProvider(config)
    try:
        yield provider
    finally:
        await provider.aclose()
