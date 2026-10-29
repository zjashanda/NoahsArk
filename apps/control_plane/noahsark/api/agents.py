"""Read-only agent registry and review projections.

AG access is provisional pending Q-09.  Agents and reviews are read-only; no
registration, pause, retirement or review decision endpoint is exposed.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["agents"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("/agents")
async def list_agents(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_agents(session, limit=limit, cursor=cursor)
    return success(request, data)


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.get_agent(session, agent_id))


@router.get("/reviews")
async def list_reviews(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_reviews(session, limit=limit, cursor=cursor)
    return success(request, data)
