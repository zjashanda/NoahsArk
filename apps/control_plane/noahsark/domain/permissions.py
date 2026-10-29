"""Server-side capability model for the NoahsArk control plane.

Clients never decide what they may do: the role header is only an identity
claim and every write re-checks the capability on the server.  Unknown roles
fail closed with ``403 FORBIDDEN``.

The five capabilities map to the four W3 write intents plus read/settings:

=================  ==========================================================
Capability         Meaning
=================  ==========================================================
READ               Inspect the control plane.
CREATE_TASK        Create intake drafts (the entry point to a task).
APPROVE            Approve or reject a frozen revision.
STOP               Request a run STOP (a request, never an execution fact).
RELEASE            Request device/lease release (a request, not a release).
DEVICE_CONTROL     Device control operations (reserved for later waves).
SETTINGS           Change control-plane settings (reserved for later waves).
=================  ==========================================================
"""

from __future__ import annotations

from enum import StrEnum

from ..errors import forbidden


class Capability(StrEnum):
    READ = "READ"
    CREATE_TASK = "CREATE_TASK"
    APPROVE = "APPROVE"
    STOP = "STOP"
    RELEASE = "RELEASE"
    DEVICE_CONTROL = "DEVICE_CONTROL"
    SETTINGS = "SETTINGS"


ALL_CAPABILITIES: frozenset[Capability] = frozenset(Capability)

ROLE_CAPABILITIES: dict[str, frozenset[Capability]] = {
    "OBSERVER": frozenset({Capability.READ}),
    "APPROVER": frozenset(
        {Capability.READ, Capability.CREATE_TASK, Capability.APPROVE}
    ),
    "SESSION_MANAGER": frozenset(
        {
            Capability.READ,
            Capability.CREATE_TASK,
            Capability.STOP,
            Capability.RELEASE,
            Capability.DEVICE_CONTROL,
        }
    ),
    "ADMIN": ALL_CAPABILITIES,
}

VALID_ROLES: frozenset[str] = frozenset(ROLE_CAPABILITIES)


def normalize_role(role: str | None) -> str:
    return (role or "").strip().upper()


def capabilities_for(role: str | None) -> frozenset[Capability]:
    """Return the role's capabilities.

    Unknown/blank roles raise ``403 FORBIDDEN``; there is no default role and
    no implicit capability grant.
    """

    normalized = normalize_role(role)
    capabilities = ROLE_CAPABILITIES.get(normalized)
    if capabilities is None:
        raise forbidden(
            f"Unknown role {role!r}; expected one of " + ", ".join(sorted(VALID_ROLES)),
            details={"role": role, "valid_roles": sorted(VALID_ROLES)},
        )
    return capabilities


def _coerce(capability: Capability | str) -> Capability:
    """Accept either the enum or its string value (dependency constants)."""

    return capability if isinstance(capability, Capability) else Capability(capability)


def has_capability(role: str | None, capability: Capability | str) -> bool:
    return _coerce(capability) in capabilities_for(role)


def ensure_capability(role: str | None, capability: Capability | str) -> None:
    """Raise ``403 FORBIDDEN`` unless ``role`` holds ``capability``."""

    required = _coerce(capability)
    capabilities = capabilities_for(role)
    if required not in capabilities:
        raise forbidden(
            f"Role {normalize_role(role)} lacks capability {required.value}",
            details={
                "required_capability": required.value,
                "actual_role": normalize_role(role),
                "granted_capabilities": sorted(item.value for item in capabilities),
            },
        )
