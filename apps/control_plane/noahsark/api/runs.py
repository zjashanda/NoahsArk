"""Read-only run and attempt projections.

``{run_id}`` and ``{attempt_id}`` accept either the stable UUID or a display id
(``run-042`` / ``att-112``).  The five axes, link signals and freshness are
returned as separate fields; release is derived only from lease preconditions.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["runs"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("/runs")
async def list_runs(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_runs(session, limit=limit, cursor=cursor)
    return success(request, data)


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.get_run(session, run_id))


@router.get("/runs/{run_id}/attempts/{attempt_id}")
async def get_run_attempt(
    run_id: str,
    attempt_id: str,
    request: Request,
    session: Session,
) -> dict:
    data = await read_models.get_run_attempt(session, run_id, attempt_id)
    return success(request, data)
