"""ADMIN topology writes: create, update and delete nodes and devices.

The router owns request parsing; this module owns the invariants:

- ``display_id`` is unique per table (pre-checked and still guarded by the
  database constraint for concurrent writers);
- a device is always attached to an existing node;
- a node cannot be deleted while devices or leases reference it;
- a device cannot be deleted while leases reference it;
- every accepted write appends exactly one hash-chained audit event with the
  actor, role, correlation id and request path.

Audit payloads carry operational metadata only: certificate material, keys,
tokens and ``identity`` blobs are never copied into the audit log.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError, not_found, validation_error
from ..models import Device, Lease, Node
from . import audit
from .writes import resolve_actor_id

NON_NULLABLE_NODE_FIELDS = frozenset(
    {
        "display_id",
        "hostname",
        "agent_version",
        "communication_state",
        "status",
        "heartbeat_interval_seconds",
        "identity",
        "os",
        "runtime",
        "interactive_session",
        "work_dir",
        "spool",
        "capabilities",
        "endpoint_ids",
    }
)
NODE_PATCHABLE_FIELDS = NON_NULLABLE_NODE_FIELDS | {
    "last_heartbeat_at",
    "quarantine_reason",
    "draining_reason",
    "error_code",
}
NON_NULLABLE_DEVICE_FIELDS = frozenset(
    {
        "display_id",
        "node_id",
        "firmware_version",
        "config_digest",
        "adapter_version",
        "pool_state",
        "health_state",
        "communication_state",
        "occupancy_state",
        "identity",
        "capabilities",
        "endpoints",
        "project_scope",
        "provenance",
    }
)
# ``current_lease_id`` is lease-owned state and is deliberately not patchable.
DEVICE_PATCHABLE_FIELDS = NON_NULLABLE_DEVICE_FIELDS | {
    "equivalence",
    "last_seen_at",
    "quarantine_reason",
    "draining_reason",
    "error_code",
}


@dataclass(frozen=True, slots=True)
class WriteContext:
    """Identity and audit coordinates resolved by the route dependency."""

    role: str
    actor: str | None
    correlation_id: str | None
    path: str


@dataclass(frozen=True, slots=True)
class TopologyPatch:
    """An identifier plus the fields the caller actually supplied."""

    identifier: str
    changes: dict[str, Any]


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _as_uuid(value: Any) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if not isinstance(value, str):
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def _resolve_node(session: AsyncSession, identifier: str) -> Node:
    raw = (identifier or "").strip()
    conditions = [Node.display_id == raw]
    parsed = _as_uuid(raw)
    if parsed is not None:
        conditions.append(Node.node_id == parsed)
    node = (
        await session.execute(select(Node).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if node is None:
        raise not_found("node", identifier)
    return node


async def _resolve_device(session: AsyncSession, identifier: str) -> Device:
    raw = (identifier or "").strip()
    conditions = [Device.display_id == raw]
    parsed = _as_uuid(raw)
    if parsed is not None:
        conditions.append(Device.device_id == parsed)
    device = (
        await session.execute(select(Device).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if device is None:
        raise not_found("device", identifier)
    return device


async def _display_id_taken(
    session: AsyncSession, model: Any, display_id: str, *, exclude: uuid.UUID | None = None
) -> bool:
    query = select(model.display_id).where(model.display_id == display_id)
    if exclude is not None:
        query = query.where(model.__table__.c[model.__mapper__.primary_key[0].name] != exclude)
    return (await session.execute(query.limit(1))).scalar_one_or_none() is not None


async def _commit(
    session: AsyncSession, *, code: str, message: str, details: dict[str, Any]
) -> None:
    """Commit a write, translating a late unique/FK race into a 409."""

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(409, code, message, retryable=False, details=details) from exc


def _node_view(node: Node) -> dict[str, Any]:
    return {
        "node_id": str(node.node_id),
        "display_id": node.display_id,
        "hostname": node.hostname,
        "agent_version": node.agent_version,
        "communication_state": node.communication_state,
        "status": node.status,
        "heartbeat_interval_seconds": node.heartbeat_interval_seconds,
        "last_heartbeat_at": _iso(node.last_heartbeat_at),
        "quarantine_reason": node.quarantine_reason,
        "draining_reason": node.draining_reason,
        "error_code": node.error_code,
        "capabilities": list(node.capabilities or []),
        "endpoint_ids": list(node.endpoint_ids or []),
        "created_at": _iso(node.created_at),
        "updated_at": _iso(node.updated_at),
    }


def _node_audit(node: Node) -> dict[str, Any]:
    return {
        "node_id": str(node.node_id),
        "display_id": node.display_id,
        "hostname": node.hostname,
        "agent_version": node.agent_version,
        "communication_state": node.communication_state,
        "status": node.status,
        "heartbeat_interval_seconds": node.heartbeat_interval_seconds,
        "quarantine_reason": node.quarantine_reason,
        "draining_reason": node.draining_reason,
        "error_code": node.error_code,
    }


def _device_view(device: Device) -> dict[str, Any]:
    return {
        "device_id": str(device.device_id),
        "display_id": device.display_id,
        "node_id": str(device.node_id),
        "firmware_version": device.firmware_version,
        "config_digest": device.config_digest,
        "adapter_version": device.adapter_version,
        "pool_state": device.pool_state,
        "health_state": device.health_state,
        "communication_state": device.communication_state,
        "occupancy_state": device.occupancy_state,
        "current_lease_id": (
            str(device.current_lease_id) if device.current_lease_id else None
        ),
        "capabilities": list(device.capabilities or []),
        "endpoints": list(device.endpoints or []),
        "project_scope": list(device.project_scope or []),
        "last_seen_at": _iso(device.last_seen_at),
        "quarantine_reason": device.quarantine_reason,
        "draining_reason": device.draining_reason,
        "error_code": device.error_code,
        "created_at": _iso(device.created_at),
        "updated_at": _iso(device.updated_at),
    }


def _device_audit(device: Device) -> dict[str, Any]:
    return {
        "device_id": str(device.device_id),
        "display_id": device.display_id,
        "node_id": str(device.node_id),
        "firmware_version": device.firmware_version,
        "config_digest": device.config_digest,
        "adapter_version": device.adapter_version,
        "pool_state": device.pool_state,
        "health_state": device.health_state,
        "communication_state": device.communication_state,
        "occupancy_state": device.occupancy_state,
        "quarantine_reason": device.quarantine_reason,
        "draining_reason": device.draining_reason,
        "error_code": device.error_code,
    }


def _reject_null_none(payload: dict[str, Any], non_nullable: frozenset[str]) -> None:
    for field in non_nullable:
        if field in payload and payload[field] is None:
            raise validation_error(
                f"{field} cannot be null", details={"field": field}
            )


def _apply(node: Any, payload: dict[str, Any], patchable: set[str] | frozenset[str]) -> None:
    for field, value in payload.items():
        if field not in patchable:
            raise validation_error(
                f"{field} is not a mutable field",
                details={"field": field, "mutable_fields": sorted(patchable)},
            )
        setattr(node, field, value)


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
async def create_node(
    session: AsyncSession, ctx: WriteContext, payload: dict[str, Any]
) -> dict[str, Any]:
    display_id = str(payload["display_id"]).strip()
    if await _display_id_taken(session, Node, display_id):
        raise ApiError(
            409,
            "DISPLAY_ID_CONFLICT",
            f"Node display_id {display_id!r} already exists",
            details={"object_type": "node", "display_id": display_id},
        )
    now = datetime.now(UTC)
    node = Node(
        node_id=uuid.uuid4(),
        display_id=display_id,
        hostname=payload["hostname"],
        agent_version=payload["agent_version"],
        communication_state=payload.get("communication_state", "OFFLINE"),
        status=payload.get("status", "ACTIVE"),
        heartbeat_interval_seconds=payload.get("heartbeat_interval_seconds", 30),
        last_heartbeat_at=payload.get("last_heartbeat_at"),
        identity=payload.get("identity") or {},
        os=payload.get("os") or {},
        runtime=payload.get("runtime") or {},
        interactive_session=payload.get("interactive_session") or {},
        work_dir=payload.get("work_dir") or {},
        spool=payload.get("spool") or {},
        capabilities=payload.get("capabilities") or [],
        endpoint_ids=payload.get("endpoint_ids") or [],
        quarantine_reason=payload.get("quarantine_reason"),
        draining_reason=payload.get("draining_reason"),
        error_code=payload.get("error_code"),
        updated_at=now,
        source="control-plane",
        seed=False,
    )
    session.add(node)
    await audit.append_event(
        session,
        actor_role=ctx.role,
        actor_id=await resolve_actor_id(session, ctx.actor),
        action="NODE_CREATED",
        object_type="node",
        object_id=node.display_id,
        before=None,
        after=_node_audit(node),
        reason=f"Created node {node.display_id}",
        correlation_id=ctx.correlation_id,
        path=ctx.path,
    )
    await _commit(
        session,
        code="DISPLAY_ID_CONFLICT",
        message=f"Node display_id {display_id!r} already exists",
        details={"object_type": "node", "display_id": display_id},
    )
    return _node_view(node)


async def update_node(
    session: AsyncSession, ctx: WriteContext, patch: TopologyPatch
) -> dict[str, Any]:
    node = await _resolve_node(session, patch.identifier)
    _reject_null_none(patch.changes, NON_NULLABLE_NODE_FIELDS)
    new_display = patch.changes.get("display_id")
    if (
        new_display is not None
        and new_display != node.display_id
        and await _display_id_taken(session, Node, new_display, exclude=node.node_id)
    ):
        raise ApiError(
            409,
            "DISPLAY_ID_CONFLICT",
            f"Node display_id {new_display!r} already exists",
            details={"object_type": "node", "display_id": new_display},
        )
    before = _node_audit(node)
    _apply(node, patch.changes, NODE_PATCHABLE_FIELDS)
    node.updated_at = datetime.now(UTC)
    await audit.append_event(
        session,
        actor_role=ctx.role,
        actor_id=await resolve_actor_id(session, ctx.actor),
        action="NODE_UPDATED",
        object_type="node",
        object_id=before["display_id"],
        before=before,
        after=_node_audit(node),
        reason=f"Updated node {node.display_id}",
        correlation_id=ctx.correlation_id,
        path=ctx.path,
    )
    await _commit(
        session,
        code="DISPLAY_ID_CONFLICT",
        message="Node update conflicted with an existing display_id",
        details={"object_type": "node", "display_id": node.display_id},
    )
    return _node_view(node)


async def delete_node(
    session: AsyncSession, ctx: WriteContext, identifier: str
) -> dict[str, Any]:
    node = await _resolve_node(session, identifier)
    device_count = int(
        (
            await session.execute(
                select(Device.device_id).where(Device.node_id == node.node_id).limit(1)
            )
        ).scalar_one_or_none()
        is not None
    )
    lease_count = int(
        (
            await session.execute(
                select(Lease.lease_id).where(Lease.node_id == node.node_id).limit(1)
            )
        ).scalar_one_or_none()
        is not None
    )
    if device_count or lease_count:
        raise ApiError(
            409,
            "RESOURCE_IN_USE",
            f"Node {node.display_id} is still referenced",
            details={
                "object_type": "node",
                "display_id": node.display_id,
                "has_devices": bool(device_count),
                "has_leases": bool(lease_count),
            },
        )
    before = _node_audit(node)
    await session.delete(node)
    await audit.append_event(
        session,
        actor_role=ctx.role,
        actor_id=await resolve_actor_id(session, ctx.actor),
        action="NODE_DELETED",
        object_type="node",
        object_id=before["display_id"],
        before=before,
        after=None,
        reason=f"Deleted node {before['display_id']}",
        correlation_id=ctx.correlation_id,
        path=ctx.path,
    )
    await _commit(
        session,
        code="RESOURCE_IN_USE",
        message=f"Node {before['display_id']} is still referenced",
        details={"object_type": "node", "display_id": before["display_id"]},
    )
    return {"node_id": before["node_id"], "display_id": before["display_id"], "deleted": True}


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------
async def create_device(
    session: AsyncSession, ctx: WriteContext, payload: dict[str, Any]
) -> dict[str, Any]:
    display_id = str(payload["display_id"]).strip()
    node = await _resolve_node(session, str(payload["node_id"]))
    if await _display_id_taken(session, Device, display_id):
        raise ApiError(
            409,
            "DISPLAY_ID_CONFLICT",
            f"Device display_id {display_id!r} already exists",
            details={"object_type": "device", "display_id": display_id},
        )
    now = datetime.now(UTC)
    device = Device(
        device_id=uuid.uuid4(),
        display_id=display_id,
        node_id=node.node_id,
        firmware_version=payload.get("firmware_version", "unknown"),
        config_digest=payload.get("config_digest", "unknown"),
        adapter_version=payload.get("adapter_version", "unknown"),
        pool_state=payload.get("pool_state", "DISCOVERED"),
        health_state=payload.get("health_state", "UNKNOWN"),
        communication_state=payload.get("communication_state", "OFFLINE"),
        occupancy_state=payload.get("occupancy_state", "IDLE"),
        identity=payload.get("identity") or {},
        capabilities=payload.get("capabilities") or [],
        endpoints=payload.get("endpoints") or [],
        project_scope=payload.get("project_scope") or [],
        provenance=payload.get("provenance") or {},
        equivalence=payload.get("equivalence"),
        last_seen_at=payload.get("last_seen_at"),
        quarantine_reason=payload.get("quarantine_reason"),
        draining_reason=payload.get("draining_reason"),
        error_code=payload.get("error_code"),
        updated_at=now,
        source="control-plane",
        seed=False,
    )
    session.add(device)
    await audit.append_event(
        session,
        actor_role=ctx.role,
        actor_id=await resolve_actor_id(session, ctx.actor),
        action="DEVICE_CREATED",
        object_type="device",
        object_id=device.display_id,
        before=None,
        after=_device_audit(device),
        reason=f"Created device {device.display_id} on node {node.display_id}",
        correlation_id=ctx.correlation_id,
        path=ctx.path,
    )
    await _commit(
        session,
        code="DISPLAY_ID_CONFLICT",
        message=f"Device display_id {display_id!r} already exists",
        details={"object_type": "device", "display_id": display_id},
    )
    return _device_view(device)


async def update_device(
    session: AsyncSession, ctx: WriteContext, patch: TopologyPatch
) -> dict[str, Any]:
    device = await _resolve_device(session, patch.identifier)
    _reject_null_none(patch.changes, NON_NULLABLE_DEVICE_FIELDS)
    new_display = patch.changes.get("display_id")
    if (
        new_display is not None
        and new_display != device.display_id
        and await _display_id_taken(
            session, Device, new_display, exclude=device.device_id
        )
    ):
        raise ApiError(
            409,
            "DISPLAY_ID_CONFLICT",
            f"Device display_id {new_display!r} already exists",
            details={"object_type": "device", "display_id": new_display},
        )
    if "node_id" in patch.changes:
        node = await _resolve_node(session, str(patch.changes["node_id"]))
        if node.node_id != device.node_id:
            lease = (
                await session.execute(
                    select(Lease.lease_id).where(Lease.device_id == device.device_id).limit(1)
                )
            ).scalar_one_or_none()
            if lease is not None:
                raise ApiError(
                    409,
                    "RESOURCE_IN_USE",
                    f"Device {device.display_id} still has leases and cannot move nodes",
                    details={"object_type": "device", "display_id": device.display_id},
                )
        patch.changes["node_id"] = node.node_id
    before = _device_audit(device)
    _apply(device, patch.changes, DEVICE_PATCHABLE_FIELDS)
    device.updated_at = datetime.now(UTC)
    await audit.append_event(
        session,
        actor_role=ctx.role,
        actor_id=await resolve_actor_id(session, ctx.actor),
        action="DEVICE_UPDATED",
        object_type="device",
        object_id=before["display_id"],
        before=before,
        after=_device_audit(device),
        reason=f"Updated device {device.display_id}",
        correlation_id=ctx.correlation_id,
        path=ctx.path,
    )
    await _commit(
        session,
        code="DISPLAY_ID_CONFLICT",
        message="Device update conflicted with an existing display_id",
        details={"object_type": "device", "display_id": device.display_id},
    )
    return _device_view(device)


async def delete_device(
    session: AsyncSession, ctx: WriteContext, identifier: str
) -> dict[str, Any]:
    device = await _resolve_device(session, identifier)
    lease = (
        await session.execute(
            select(Lease.lease_id).where(Lease.device_id == device.device_id).limit(1)
        )
    ).scalar_one_or_none()
    if lease is not None or device.current_lease_id is not None:
        raise ApiError(
            409,
            "RESOURCE_IN_USE",
            f"Device {device.display_id} is still referenced by a lease",
            details={
                "object_type": "device",
                "display_id": device.display_id,
                "current_lease_id": (
                    str(device.current_lease_id) if device.current_lease_id else None
                ),
            },
        )
    before = _device_audit(device)
    await session.delete(device)
    await audit.append_event(
        session,
        actor_role=ctx.role,
        actor_id=await resolve_actor_id(session, ctx.actor),
        action="DEVICE_DELETED",
        object_type="device",
        object_id=before["display_id"],
        before=before,
        after=None,
        reason=f"Deleted device {before['display_id']}",
        correlation_id=ctx.correlation_id,
        path=ctx.path,
    )
    await _commit(
        session,
        code="RESOURCE_IN_USE",
        message=f"Device {before['display_id']} is still referenced by a lease",
        details={"object_type": "device", "display_id": before["display_id"]},
    )
    return {
        "device_id": before["device_id"],
        "display_id": before["display_id"],
        "deleted": True,
    }
