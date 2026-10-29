"""Read-only report projections.

Version, denominator statement, the four record classes and disclosure are
returned separately.  A report's release view comes from lease preconditions,
never from its verdict or PASS decision.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["reports"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("/reports")
async def list_reports(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_reports(session, limit=limit, cursor=cursor)
    return success(request, data)


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.get_report(session, report_id))
