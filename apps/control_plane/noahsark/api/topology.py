"""ADMIN-only topology writes for the Node Management console.

Routes are intentionally separate from the read-only ``api/devices.py``
projections: reads stay open to every authenticated principal, while every
mutation here is gated by ``require_admin`` (no capability is granted to
non-admin roles for node/device topology).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import topology
from ..services.topology import TopologyPatch, WriteContext
from .deps import Principal, require_admin
from .envelope import correlation_id, success

router = APIRouter(tags=["topology"])

Session = Annotated[AsyncSession, Depends(get_session)]
Admin = Annotated[Principal, Depends(require_admin)]

NodeCommunicationState = Literal["ONLINE", "STALE", "OFFLINE"]
NodeStatus = Literal["ACTIVE", "DRAINING", "QUARANTINED", "RETIRED"]
DevicePoolState = Literal[
    "DISCOVERED",
    "READY",
    "RESERVED",
    "ATTACHED",
    "DRAINING",
    "QUARANTINED",
    "OFFLINE",
    "RETIRED",
]
DeviceHealthState = Literal["HEALTHY", "DEGRADED", "UNHEALTHY", "UNKNOWN"]
DeviceOccupancyState = Literal["IDLE", "OCCUPIED", "RELEASING"]


class NodeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_id: str = Field(min_length=1, max_length=80)
    hostname: str = Field(min_length=1, max_length=200)
    agent_version: str = Field(min_length=1, max_length=80)
    communication_state: NodeCommunicationState = "OFFLINE"
    status: NodeStatus = "ACTIVE"
    heartbeat_interval_seconds: int = Field(default=30, ge=1, le=3600)
    last_heartbeat_at: datetime | None = None
    identity: dict[str, Any] = Field(default_factory=dict)
    os: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)
    interactive_session: dict[str, Any] = Field(default_factory=dict)
    work_dir: dict[str, Any] = Field(default_factory=dict)
    spool: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[Any] = Field(default_factory=list)
    endpoint_ids: list[Any] = Field(default_factory=list)
    quarantine_reason: str | None = None
    draining_reason: str | None = None
    error_code: str | None = Field(default=None, max_length=80)


class NodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_id: str | None = Field(default=None, min_length=1, max_length=80)
    hostname: str | None = Field(default=None, min_length=1, max_length=200)
    agent_version: str | None = Field(default=None, min_length=1, max_length=80)
    communication_state: NodeCommunicationState | None = None
    status: NodeStatus | None = None
    heartbeat_interval_seconds: int | None = Field(default=None, ge=1, le=3600)
    last_heartbeat_at: datetime | None = None
    identity: dict[str, Any] | None = None
    os: dict[str, Any] | None = None
    runtime: dict[str, Any] | None = None
    interactive_session: dict[str, Any] | None = None
    work_dir: dict[str, Any] | None = None
    spool: dict[str, Any] | None = None
    capabilities: list[Any] | None = None
    endpoint_ids: list[Any] | None = None
    quarantine_reason: str | None = None
    draining_reason: str | None = None
    error_code: str | None = Field(default=None, max_length=80)


class DeviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_id: str = Field(min_length=1, max_length=80)
    node_id: str = Field(min_length=1)
    firmware_version: str = Field(default="unknown", max_length=80)
    config_digest: str = Field(default="unknown", max_length=80)
    adapter_version: str = Field(default="unknown", max_length=80)
    pool_state: DevicePoolState = "DISCOVERED"
    health_state: DeviceHealthState = "UNKNOWN"
    communication_state: NodeCommunicationState = "OFFLINE"
    occupancy_state: DeviceOccupancyState = "IDLE"
    identity: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[Any] = Field(default_factory=list)
    endpoints: list[Any] = Field(default_factory=list)
    project_scope: list[Any] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    equivalence: dict[str, Any] | None = None
    last_seen_at: datetime | None = None
    quarantine_reason: str | None = None
    draining_reason: str | None = None
    error_code: str | None = Field(default=None, max_length=80)


class DeviceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_id: str | None = Field(default=None, min_length=1, max_length=80)
    node_id: str | None = Field(default=None, min_length=1)
    firmware_version: str | None = Field(default=None, max_length=80)
    config_digest: str | None = Field(default=None, max_length=80)
    adapter_version: str | None = Field(default=None, max_length=80)
    pool_state: DevicePoolState | None = None
    health_state: DeviceHealthState | None = None
    communication_state: NodeCommunicationState | None = None
    occupancy_state: DeviceOccupancyState | None = None
    identity: dict[str, Any] | None = None
    capabilities: list[Any] | None = None
    endpoints: list[Any] | None = None
    project_scope: list[Any] | None = None
    provenance: dict[str, Any] | None = None
    equivalence: dict[str, Any] | None = None
    last_seen_at: datetime | None = None
    quarantine_reason: str | None = None
    draining_reason: str | None = None
    error_code: str | None = Field(default=None, max_length=80)


def _context(request: Request, principal: Principal) -> WriteContext:
    return WriteContext(
        role=principal.role,
        actor=principal.actor,
        correlation_id=correlation_id(request),
        path=request.url.path,
    )


def _render(request: Request, data: dict[str, Any], status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=success(request, data))


@router.post("/nodes", status_code=201)
async def post_node(
    body: NodeCreate, request: Request, session: Session, principal: Admin
) -> JSONResponse:
    data = await topology.create_node(
        session, _context(request, principal), body.model_dump(exclude_unset=True)
    )
    return _render(request, data, 201)


@router.patch("/nodes/{node_id}")
async def patch_node(
    node_id: str,
    body: NodeUpdate,
    request: Request,
    session: Session,
    principal: Admin,
) -> JSONResponse:
    data = await topology.update_node(
        session,
        _context(request, principal),
        TopologyPatch(
            identifier=node_id, changes=body.model_dump(exclude_unset=True)
        ),
    )
    return _render(request, data, 200)


@router.delete("/nodes/{node_id}")
async def delete_node(
    node_id: str, request: Request, session: Session, principal: Admin
) -> JSONResponse:
    data = await topology.delete_node(session, _context(request, principal), node_id)
    return _render(request, data, 200)


@router.post("/devices", status_code=201)
async def post_device(
    body: DeviceCreate, request: Request, session: Session, principal: Admin
) -> JSONResponse:
    data = await topology.create_device(
        session, _context(request, principal), body.model_dump(exclude_unset=True)
    )
    return _render(request, data, 201)


@router.patch("/devices/{device_id}")
async def patch_device(
    device_id: str,
    body: DeviceUpdate,
    request: Request,
    session: Session,
    principal: Admin,
) -> JSONResponse:
    data = await topology.update_device(
        session,
        _context(request, principal),
        TopologyPatch(
            identifier=device_id, changes=body.model_dump(exclude_unset=True)
        ),
    )
    return _render(request, data, 200)


@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: str, request: Request, session: Session, principal: Admin
) -> JSONResponse:
    data = await topology.delete_device(session, _context(request, principal), device_id)
    return _render(request, data, 200)
