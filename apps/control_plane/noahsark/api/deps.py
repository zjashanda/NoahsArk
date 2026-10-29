"""Development identity dependencies.

Role headers are a scaffold, not authentication: they are parsed server-side so
unknown roles fail closed.  Read endpoints run for every valid role.  W3 writes
use the capability allow-list below, which denies by default and therefore never
trusts a client-supplied role beyond the four known role codes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header

from ..domain.permissions import Capability, ensure_capability
from ..errors import forbidden

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

ALL_CAPABILITIES = frozenset(
    {
        CAP_READ,
        CAP_CREATE_TASK,
        CAP_APPROVE,
        CAP_STOP,
        CAP_RELEASE,
        CAP_DEVICE_CONTROL,
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


@dataclass(frozen=True)
class Principal:
    role: str
    actor: str | None
    header_role: str | None

    @property
    def is_observer(self) -> bool:
        return self.role == ROLE_OBSERVER


async def get_principal(
    x_noahsark_role: str | None = Header(default=None, alias="X-NoahsArk-Role"),
    x_noahsark_actor: str | None = Header(default=None, alias="X-NoahsArk-Actor"),
) -> Principal:
    raw = x_noahsark_role.strip().upper() if x_noahsark_role else ROLE_OBSERVER
    role = raw or ROLE_OBSERVER
    if role not in VALID_ROLES:
        raise forbidden(
            f"Unknown role header {x_noahsark_role!r}; expected one of "
            + ", ".join(sorted(VALID_ROLES)),
            details={"header": "X-NoahsArk-Role", "valid_roles": sorted(VALID_ROLES)},
        )
    return Principal(role=role, actor=x_noahsark_actor, header_role=x_noahsark_role)


def require_roles(*allowed: str) -> Callable:
    """Reusable dependency factory for future writes (W3).  Default deny."""

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
