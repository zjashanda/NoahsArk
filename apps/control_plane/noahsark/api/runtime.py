"""Read-only runtime model and toolchain projections.

RT access is provisional pending Q-09.  Only GET routes exist: no model
binding, lock, drift or toolchain mutation is exposed.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["runtime"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("/runtime/models")
async def get_runtime_models(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.runtime_models(session, limit=limit, cursor=cursor)
    return success(request, data)


@router.get("/runtime/toolchain")
async def get_runtime_toolchain(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.runtime_toolchain(session, limit=limit, cursor=cursor)
    return success(request, data)
