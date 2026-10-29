"""Read-only knowledge and candidate projections.

Candidates are listed before the detail route so ``/knowledge/candidates`` is
never captured as a knowledge identifier.  Candidate status and the
``automatic_promotion_allowed=false`` / ``requires_human_review=true`` policy
are preserved verbatim; this batch exposes no promotion or write action.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["knowledge"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("/knowledge")
async def list_knowledge(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_knowledge(session, limit=limit, cursor=cursor)
    return success(request, data)


@router.get("/knowledge/candidates")
async def list_knowledge_candidates(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_knowledge_candidates(
        session, limit=limit, cursor=cursor
    )
    return success(request, data)


@router.get("/knowledge/{knowledge_id}")
async def get_knowledge(
    knowledge_id: str,
    request: Request,
    session: Session,
) -> dict:
    data = await read_models.get_knowledge(session, knowledge_id)
    return success(request, data)
