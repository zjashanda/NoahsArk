"""Read-only intake draft projections."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["intake"], dependencies=[Depends(get_principal)])


@router.get("/intake/drafts")
async def list_drafts(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_intake_drafts(
        session, limit=limit, cursor=cursor
    )
    return success(request, data)


@router.get("/intake/drafts/{draft_id}")
async def get_draft(
    draft_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    data = await read_models.get_intake_draft(session, draft_id)
    return success(request, data)
