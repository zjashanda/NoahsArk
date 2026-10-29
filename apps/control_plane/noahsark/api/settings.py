"""Read-only settings projections.

Settings reads never expose passwords, secret keys, certificates or tokens:
stored JSONB values pass through the read-model secret filter.  Literal
sub-routes are declared before ``/settings`` consumers need them; no write
route exists.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["settings"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/settings")
async def list_settings(
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.list_settings(session))


@router.get("/settings/access")
async def get_settings_access(
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.settings_access(session))


@router.get("/settings/notifications")
async def get_settings_notifications(
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.settings_notifications(session))


@router.get("/settings/retention")
async def get_settings_retention(
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.settings_retention(session))
