"""Read-only run and attempt projections.

``{run_id}`` and ``{attempt_id}`` accept either the stable UUID or a display id
(``run-042`` / ``att-112``).  The five axes, link signals and freshness are
returned as separate fields; release is derived only from lease preconditions.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models, verdicts, writes
from .deps import CAP_VERDICT_WRITE, Principal, get_principal, require_capability
from .envelope import correlation_id, success
from .writes import IdempotencyKey

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


@router.post("/runs/{run_id}/verdicts")
async def post_verdict(
    run_id: str,
    request: Request,
    session: Session,
    idempotency_key: IdempotencyKey,
    principal: Annotated[Principal, Depends(require_capability(CAP_VERDICT_WRITE))],
) -> JSONResponse:
    payload: dict[str, object] = {}
    data, status_code = await writes.execute_idempotent(
        session,
        scope="POST /api/v1/runs/{run_id}/verdicts",
        key=idempotency_key,
        request_hash=writes.request_fingerprint(request.url.path, payload),
        action=lambda: verdicts.evaluate_run(
            session,
            run_id,
            principal_role=principal.role,
            actor=principal.actor,
            correlation_id=correlation_id(request),
            path=request.url.path,
        ),
    )
    return JSONResponse(status_code=status_code, content=success(request, data))
