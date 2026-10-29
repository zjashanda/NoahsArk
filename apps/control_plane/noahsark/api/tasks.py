"""Read-only task projections.

``{task_id}`` accepts either the stable UUID or a display id such as
``tsk-voice-001``.  All five axes are returned as separate fields; no helper
collapses them into a single verdict.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["tasks"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("/tasks")
async def list_tasks(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_tasks(session, limit=limit, cursor=cursor)
    return success(request, data)


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.get_task(session, task_id))


@router.get("/tasks/{task_id}/overview")
async def get_task_overview(
    task_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.task_overview(session, task_id))


@router.get("/tasks/{task_id}/revisions")
async def get_task_revisions(
    task_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.task_revisions(session, task_id))


@router.get("/tasks/{task_id}/plan")
async def get_task_plan(
    task_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.task_plan(session, task_id))


@router.get("/tasks/{task_id}/runs")
async def get_task_runs(
    task_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.task_runs(session, task_id))


@router.get("/tasks/{task_id}/evidence")
async def get_task_evidence(
    task_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.task_evidence(session, task_id))


@router.get("/tasks/{task_id}/verdict")
async def get_task_verdict(
    task_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.task_verdict(session, task_id))


@router.get("/tasks/{task_id}/live")
async def get_task_live(
    task_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.task_live(session, task_id))


@router.get("/tasks/{task_id}/knowledge")
async def get_task_knowledge(
    task_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.task_knowledge(session, task_id))
