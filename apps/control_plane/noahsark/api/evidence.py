"""Read-only evidence ledger and verdict projections.

``expected`` / ``received`` / ``verified`` stay independent, and
``evidence_status`` is one of the four contract values (COMPLETE / INCOMPLETE /
CONFLICTED / UNVERIFIED).  A missing verdict is reported as unavailable rather
than fabricated as PASS.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["evidence"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("/evidence")
async def list_evidence(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_evidence(session, limit=limit, cursor=cursor)
    return success(request, data)


@router.get("/evidence/{evidence_id}")
async def get_evidence(
    evidence_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.get_evidence(session, evidence_id))


@router.get("/verdicts")
async def list_verdicts(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_verdicts(session, limit=limit, cursor=cursor)
    return success(request, data)
