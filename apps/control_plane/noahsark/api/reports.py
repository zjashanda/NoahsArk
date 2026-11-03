"""Read-only report projections.

Version, denominator statement, the four record classes and disclosure are
returned separately.  A report's release view comes from lease preconditions,
never from its verdict or PASS decision.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models, reports, writes
from .deps import CAP_REPORT_WRITE, Principal, get_principal, require_capability
from .envelope import correlation_id, success
from .writes import IdempotencyKey

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


class ReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    disclosure: str = Field(default="INTERNAL", min_length=1, max_length=32)


@router.post("/tasks/{task_id}/reports")
async def post_report(
    task_id: str,
    body: ReportCreate,
    request: Request,
    session: Session,
    idempotency_key: IdempotencyKey,
    principal: Annotated[Principal, Depends(require_capability(CAP_REPORT_WRITE))],
) -> JSONResponse:
    payload = body.model_dump()
    data, status_code = await writes.execute_idempotent(
        session,
        scope="POST /api/v1/tasks/{task_id}/reports",
        key=idempotency_key,
        request_hash=writes.request_fingerprint(request.url.path, payload),
        action=lambda: reports.create_report(
            session,
            task_id,
            title=body.title,
            disclosure=body.disclosure,
            principal_role=principal.role,
            actor=principal.actor,
            correlation_id=correlation_id(request),
            path=request.url.path,
        ),
    )
    return JSONResponse(status_code=status_code, content=success(request, data))


@router.post("/reports/{report_id}/freeze")
async def post_report_freeze(
    report_id: str,
    request: Request,
    session: Session,
    idempotency_key: IdempotencyKey,
    principal: Annotated[Principal, Depends(require_capability(CAP_REPORT_WRITE))],
) -> JSONResponse:
    payload: dict[str, object] = {}
    data, status_code = await writes.execute_idempotent(
        session,
        scope="POST /api/v1/reports/{report_id}/freeze",
        key=idempotency_key,
        request_hash=writes.request_fingerprint(request.url.path, payload),
        action=lambda: reports.freeze_report(
            session,
            report_id,
            principal_role=principal.role,
            actor=principal.actor,
            correlation_id=correlation_id(request),
            path=request.url.path,
        ),
        status_code=200,
    )
    return JSONResponse(status_code=status_code, content=success(request, data))
