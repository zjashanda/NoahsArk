"""Device and node projections plus admin-only management routes."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..errors import ApiError, not_found
from ..models.device import Device, Lease, Node
from ..services import audit, read_models
from ..services.auth import Principal
from .deps import get_principal, require_admin
from .envelope import correlation_id, success

router = APIRouter(tags=["devices"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]
Admin = Annotated[Principal, Depends(require_admin)]

NodeStatus = Literal["ACTIVE", "DRAINING", "QUARANTINED", "RETIRED"]
CommunicationState = Literal["ONLINE", "STALE", "OFFLINE"]
PoolState = Literal[
    "DISCOVERED",
    "READY",
    "RESERVED",
    "ATTACHED",
    "DRAINING",
    "QUARANTINED",
    "OFFLINE",
    "RETIRED",
]
HealthState = Literal["HEALTHY", "DEGRADED", "UNHEALTHY", "UNKNOWN"]
OccupancyState = Literal["IDLE", "OCCUPIED", "RELEASING"]


class NodeCreate(BaseModel):
    display_id: str = Field(min_length=1, max_length=80)
    hostname: str = Field(min_length=1, max_length=200)
    agent_version: str = Field(default="unknown", max_length=80)
    identity: dict = Field(default_factory=dict)
    os: dict = Field(default_factory=dict)
    runtime: dict = Field(default_factory=dict)
    capabilities: list = Field(default_factory=list)
    endpoint_ids: list = Field(default_factory=list)
    status: NodeStatus = "ACTIVE"
    communication_state: CommunicationState = "OFFLINE"


class NodeUpdate(BaseModel):
    hostname: str | None = Field(default=None, min_length=1, max_length=200)
    agent_version: str | None = Field(default=None, max_length=80)
    capabilities: list | None = None
    endpoint_ids: list | None = None
    status: NodeStatus | None = None
    communication_state: CommunicationState | None = None


class DeviceCreate(BaseModel):
    display_id: str = Field(min_length=1, max_length=80)
    node_id: uuid.UUID
    firmware_version: str = Field(default="unknown", max_length=80)
    config_digest: str = Field(default="unknown", max_length=80)
    adapter_version: str = Field(default="unknown", max_length=80)
    identity: dict = Field(default_factory=dict)
    capabilities: list = Field(default_factory=list)
    endpoints: list = Field(default_factory=list)
    project_scope: list = Field(default_factory=list)
    pool_state: PoolState = "DISCOVERED"
    health_state: HealthState = "UNKNOWN"
    communication_state: CommunicationState = "OFFLINE"
    occupancy_state: OccupancyState = "IDLE"


class DeviceUpdate(BaseModel):
    display_id: str | None = Field(default=None, min_length=1, max_length=80)
    identity: dict | None = None
    firmware_version: str | None = Field(default=None, max_length=80)
    config_digest: str | None = Field(default=None, max_length=80)
    adapter_version: str | None = Field(default=None, max_length=80)
    capabilities: list | None = None
    endpoints: list | None = None
    project_scope: list | None = None
    pool_state: PoolState | None = None
    health_state: HealthState | None = None
    communication_state: CommunicationState | None = None
    occupancy_state: OccupancyState | None = None


def _now() -> datetime:
    return datetime.now(UTC)


async def _resolve_node(session: AsyncSession, identifier: str) -> Node:
    try:
        node_id = uuid.UUID(identifier)
    except ValueError as exc:
        raise not_found("node", identifier) from exc
    node = await session.get(Node, node_id)
    if node is None:
        raise not_found("node", identifier)
    return node


async def _resolve_device(session: AsyncSession, identifier: str) -> Device:
    try:
        device_id = uuid.UUID(identifier)
    except ValueError as exc:
        raise not_found("device", identifier) from exc
    device = await session.get(Device, device_id)
    if device is None:
        raise not_found("device", identifier)
    return device


async def _node_display_taken(session: AsyncSession, display_id: str) -> bool:
    row = await session.execute(select(Node.node_id).where(Node.display_id == display_id))
    return row.scalar_one_or_none() is not None


async def _device_display_taken(session: AsyncSession, display_id: str) -> bool:
    row = await session.execute(
        select(Device.device_id).where(Device.display_id == display_id)
    )
    return row.scalar_one_or_none() is not None


async def _audit_write(
    session: AsyncSession,
    request: Request,
    principal: Principal,
    *,
    action: str,
    object_type: str,
    object_id: str,
    before: dict | None,
    after: dict,
) -> None:
    await audit.append_event(
        session,
        actor_role=principal.role,
        actor_id=None,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before=before,
        after=after,
        reason=None,
        correlation_id=correlation_id(request),
        path=request.url.path,
    )


@router.get("/devices")
async def list_devices(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_devices(session, limit=limit, cursor=cursor)
    return success(request, data)


@router.get("/devices/{device_id}")
async def get_device(
    device_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.get_device(session, device_id))


@router.get("/nodes")
async def list_nodes(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_nodes(session, limit=limit, cursor=cursor)
    return success(request, data)


@router.get("/nodes/enrollment-token")
async def get_node_enrollment_token(
    request: Request,
    principal: Admin,
) -> dict:
    """Return the platform enrollment token for rendering install commands.

    ADMIN only.  The value is never logged; it is the same credential the
    ``/node/v1/enroll`` route compares against.
    """

    return success(
        request,
        {"token": settings.node_enrollment_token, "issued": True},
    )


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.get_node(session, node_id))


@router.post("/nodes")
async def create_node(
    request: Request,
    body: NodeCreate,
    session: Session,
    principal: Admin,
) -> dict:
    if await _node_display_taken(session, body.display_id):
        raise ApiError(409, "NODE_ALREADY_EXISTS", "Node display_id already exists")
    node = Node(
        node_id=uuid.uuid4(),
        display_id=body.display_id,
        hostname=body.hostname,
        identity=body.identity,
        agent_version=body.agent_version,
        os=body.os,
        runtime=body.runtime,
        communication_state=body.communication_state,
        heartbeat_interval_seconds=30,
        status=body.status,
        interactive_session={},
        work_dir={},
        spool={},
        capabilities=body.capabilities,
        endpoint_ids=body.endpoint_ids,
        updated_at=_now(),
    )
    session.add(node)
    await session.flush()
    await _audit_write(
        session,
        request,
        principal,
        action="NODE_CREATED",
        object_type="node",
        object_id=node.display_id,
        before=None,
        after={
            "node_id": str(node.node_id),
            "display_id": node.display_id,
            "hostname": node.hostname,
            "status": node.status,
        },
    )
    await session.commit()
    return success(
        request,
        {
            "node_id": str(node.node_id),
            "display_id": node.display_id,
            "created": True,
        },
    )


@router.post("/nodes/{node_id}/token")
async def issue_node_token(
    node_id: str,
    request: Request,
    session: Session,
    principal: Admin,
) -> dict:
    """Issue a fresh per-node agent token; the plaintext is returned once.

    Only the SHA-256 digest is persisted (in ``identity``), so a database read
    never reveals a usable credential.  Re-issuing rotates the token.
    """

    node = await _resolve_node(session, node_id)
    token = secrets.token_urlsafe(32)
    identity = dict(node.identity or {})
    identity["agent_token_hash"] = hashlib.sha256(token.encode("utf-8")).hexdigest()
    node.identity = identity
    node.updated_at = _now()
    await _audit_write(
        session,
        request,
        principal,
        action="NODE_TOKEN_ISSUED",
        object_type="node",
        object_id=node.display_id,
        before=None,
        after={"node_id": str(node.node_id), "issued": True},
    )
    await session.commit()
    return success(
        request,
        {"node_id": str(node.node_id), "token": token, "issued": True},
    )


@router.patch("/nodes/{node_id}")
async def update_node(
    node_id: str,
    request: Request,
    body: NodeUpdate,
    session: Session,
    principal: Admin,
) -> dict:
    node = await _resolve_node(session, node_id)
    before = {
        "hostname": node.hostname,
        "agent_version": node.agent_version,
        "status": node.status,
        "communication_state": node.communication_state,
    }
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(node, field, value)
    node.updated_at = _now()
    await _audit_write(
        session,
        request,
        principal,
        action="NODE_UPDATED",
        object_type="node",
        object_id=node.display_id,
        before=before,
        after={**changes, "node_id": str(node.node_id)},
    )
    await session.commit()
    return success(
        request,
        {
            "node_id": str(node.node_id),
            "display_id": node.display_id,
            "updated": True,
        },
    )


@router.delete("/nodes/{node_id}")
async def delete_node(
    node_id: str,
    request: Request,
    session: Session,
    principal: Admin,
) -> dict:
    node = await _resolve_node(session, node_id)
    device_count = await session.execute(
        select(Device.device_id).where(Device.node_id == node.node_id).limit(1)
    )
    if device_count.scalar_one_or_none() is not None:
        raise ApiError(
            409,
            "NODE_HAS_DEVICES",
            "Remove or move the node's devices before deleting it",
        )
    await _audit_write(
        session,
        request,
        principal,
        action="NODE_DELETED",
        object_type="node",
        object_id=node.display_id,
        before={"node_id": str(node.node_id), "display_id": node.display_id},
        after={"deleted": True},
    )
    await session.delete(node)
    await session.commit()
    return success(request, {"node_id": str(node.node_id), "deleted": True})


@router.post("/devices")
async def create_device(
    request: Request,
    body: DeviceCreate,
    session: Session,
    principal: Admin,
) -> dict:
    node = await session.get(Node, body.node_id)
    if node is None:
        raise not_found("node", str(body.node_id))
    if await _device_display_taken(session, body.display_id):
        raise ApiError(409, "DEVICE_ALREADY_EXISTS", "Device display_id already exists")
    device = Device(
        device_id=uuid.uuid4(),
        display_id=body.display_id,
        node_id=body.node_id,
        identity=body.identity,
        capabilities=body.capabilities,
        endpoints=body.endpoints,
        firmware_version=body.firmware_version,
        config_digest=body.config_digest,
        adapter_version=body.adapter_version,
        project_scope=body.project_scope,
        pool_state=body.pool_state,
        health_state=body.health_state,
        communication_state=body.communication_state,
        occupancy_state=body.occupancy_state,
        provenance={},
        updated_at=_now(),
    )
    session.add(device)
    await session.flush()
    await _audit_write(
        session,
        request,
        principal,
        action="DEVICE_CREATED",
        object_type="device",
        object_id=device.display_id,
        before=None,
        after={
            "device_id": str(device.device_id),
            "display_id": device.display_id,
            "node_id": str(node.node_id),
            "pool_state": device.pool_state,
        },
    )
    await session.commit()
    return success(
        request,
        {
            "device_id": str(device.device_id),
            "display_id": device.display_id,
            "node_id": str(device.node_id),
            "created": True,
        },
    )


@router.patch("/devices/{device_id}")
async def update_device(
    device_id: str,
    request: Request,
    body: DeviceUpdate,
    session: Session,
    principal: Admin,
) -> dict:
    device = await _resolve_device(session, device_id)
    before = {
        "display_id": device.display_id,
        "identity": device.identity,
        "endpoints": device.endpoints,
        "capabilities": device.capabilities,
    }
    if (
        body.display_id is not None
        and body.display_id != device.display_id
        and await _device_display_taken(session, body.display_id)
    ):
        raise ApiError(
            409,
            "DEVICE_ALREADY_EXISTS",
            "Device display_id already exists",
        )
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(device, field, value)
    device.updated_at = _now()
    await _audit_write(
        session,
        request,
        principal,
        action="DEVICE_UPDATED",
        object_type="device",
        object_id=device.display_id,
        before=before,
        after={**changes, "device_id": str(device.device_id)},
    )
    await session.commit()
    return success(
        request,
        {
            "device_id": str(device.device_id),
            "display_id": device.display_id,
            "updated": True,
        },
    )


@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: str,
    request: Request,
    session: Session,
    principal: Admin,
) -> dict:
    device = await _resolve_device(session, device_id)
    lease = await session.execute(
        select(Lease.lease_id).where(Lease.device_id == device.device_id).limit(1)
    )
    if lease.scalar_one_or_none() is not None:
        raise ApiError(
            409,
            "DEVICE_HAS_LEASES",
            "Device is referenced by a lease and cannot be deleted",
        )
    await _audit_write(
        session,
        request,
        principal,
        action="DEVICE_DELETED",
        object_type="device",
        object_id=device.display_id,
        before={"device_id": str(device.device_id), "display_id": device.display_id},
        after={"deleted": True},
    )
    await session.delete(device)
    await session.commit()
    return success(request, {"device_id": str(device.device_id), "deleted": True})
