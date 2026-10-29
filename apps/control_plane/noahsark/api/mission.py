"""Read-only mission control projection."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["mission"], dependencies=[Depends(get_principal)])


@router.get("/mission")
async def get_mission(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    return success(request, await read_models.mission(session))
