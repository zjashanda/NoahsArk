"""Read-only device and node projections.

Metadata only: no control or write action is exposed in batch 2.  Device
communication, occupancy, execution permit, run execution status and freshness
are returned separately, and release is derived solely from the three lease
preconditions.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["devices"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]


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


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.get_node(session, node_id))
