"""Read-only task projections.

``{task_id}`` accepts either the stable UUID or a display id such as
``tsk-voice-001``.  All five axes are returned as separate fields; no helper
collapses them into a single verdict.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..integrations.opencode.errors import OpenCodeError
from ..integrations.opencode.protocol import OpenCodeProvider
from ..services import read_models, supervision
from .deps import get_opencode_provider, get_principal
from .envelope import success

router = APIRouter(tags=["tasks"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Provider = Annotated[OpenCodeProvider, Depends(get_opencode_provider)]
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


@router.get("/tasks/{task_id}/supervisor")
async def get_task_supervisor(
    task_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await supervision.get_task_supervisor(session, task_id))


@router.get("/tasks/{task_id}/session/messages")
async def get_task_session_messages(
    task_id: str,
    request: Request,
    session: Session,
    provider: Provider,
) -> dict:
    return success(
        request,
        await supervision.get_task_session_messages(session, task_id, provider),
    )


@router.get("/tasks/{task_id}/session/stream")
async def stream_task_session_events(
    task_id: str,
    session: Session,
    provider: Provider,
) -> StreamingResponse:
    """Relay sanitized OpenCode process events as SSE.

    Events are merged into ~80ms batches so a token-level model stream becomes
    one compact SSE frame instead of one HTTP broadcast per token.  The 1.5s
    message poll remains the authoritative fallback if this stream drops.
    """

    async def generate():
        queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

        async def produce() -> None:
            try:
                async for event in supervision.stream_task_session_events(
                    session, task_id, provider
                ):
                    await queue.put(event)
            except OpenCodeError as exc:
                await queue.put(
                    {
                        "type": "stream.error",
                        "code": exc.code,
                        "message": exc.message,
                        "retryable": exc.retryable,
                    }
                )
            finally:
                await queue.put(None)

        producer = asyncio.create_task(produce())
        try:
            while True:
                first = await queue.get()
                if first is None:
                    break
                batch = [first]
                deadline = time.monotonic() + 0.08
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        item = await asyncio.wait_for(queue.get(), remaining)
                    except TimeoutError:
                        break
                    if item is None:
                        yield f"data: {json.dumps(batch, ensure_ascii=False)}\n\n"
                        return
                    batch.append(item)
                yield f"data: {json.dumps(batch, ensure_ascii=False)}\n\n"
        finally:
            producer.cancel()
            try:
                await producer
            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
