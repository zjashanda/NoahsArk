"""Read-only knowledge and candidate projections.

Candidates are listed before the detail route so ``/knowledge/candidates`` is
never captured as a knowledge identifier.  Candidate status and the
``automatic_promotion_allowed=false`` / ``requires_human_review=true`` policy
are preserved verbatim.  Promotion is a separate, capability-guarded write that
requires a human reviewer and a candidate already in ``APPROVED`` state.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import knowledge, read_models, writes
from .deps import (
    CAP_KNOWLEDGE_PROMOTE,
    Principal,
    get_principal,
    require_capability,
)
from .envelope import correlation_id, success
from .writes import IdempotencyKey

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


class PromotionCreate(BaseModel):
    target_library: str = Field(min_length=1, max_length=16)
    reason: str = Field(min_length=1, max_length=2000)
    similarity_check: dict = Field(default_factory=dict)


@router.post("/knowledge/candidates/{candidate_id}/promotions")
async def post_knowledge_promotion(
    candidate_id: str,
    body: PromotionCreate,
    request: Request,
    session: Session,
    idempotency_key: IdempotencyKey,
    principal: Annotated[Principal, Depends(require_capability(CAP_KNOWLEDGE_PROMOTE))],
) -> JSONResponse:
    payload = body.model_dump()
    data, status_code = await writes.execute_idempotent(
        session,
        scope="POST /api/v1/knowledge/candidates/{candidate_id}/promotions",
        key=idempotency_key,
        request_hash=writes.request_fingerprint(request.url.path, payload),
        action=lambda: knowledge.promote_candidate(
            session,
            candidate_id,
            target_library=body.target_library,
            reason=body.reason,
            similarity_check=body.similarity_check,
            principal_role=principal.role,
            actor=principal.actor,
            correlation_id=correlation_id(request),
            path=request.url.path,
        ),
    )
    return JSONResponse(status_code=status_code, content=success(request, data))


@router.get("/knowledge/{knowledge_id}")
async def get_knowledge(
    knowledge_id: str,
    request: Request,
    session: Session,
) -> dict:
    data = await read_models.get_knowledge(session, knowledge_id)
    return success(request, data)
