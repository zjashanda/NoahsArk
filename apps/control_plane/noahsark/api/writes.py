"""W3 write surface: task creation, intake drafts, approvals, STOP and release.

Every route requires an ``Idempotency-Key`` and a capability granted by
``deps.ROLE_CAPABILITIES``.  State-machine guards live in the service modules;
routers only parse/validate and render the envelope.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..errors import ApiError
from ..integrations.opencode.protocol import OpenCodeProvider
from ..services import supervision, writes
from ..services.supervision import TaskDraft
from .deps import (
    CAP_APPROVE,
    CAP_CREATE_TASK,
    CAP_RELEASE,
    CAP_STOP,
    Principal,
    get_opencode_provider,
    require_admin,
    require_capability,
)
from .envelope import correlation_id, success

router = APIRouter(tags=["writes"])

Session = Annotated[AsyncSession, Depends(get_session)]
Provider = Annotated[OpenCodeProvider, Depends(get_opencode_provider)]


async def require_idempotency_key(
    x_idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
) -> str:
    if x_idempotency_key is None or not x_idempotency_key.strip():
        raise ApiError(
            400,
            "IDEMPOTENCY_REQUIRED",
            "Idempotency-Key header is required for write requests",
            retryable=False,
            details={"header": "Idempotency-Key"},
        )
    key = x_idempotency_key.strip()
    if len(key) > 300:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "Idempotency-Key must be at most 300 characters",
            details={"header": "Idempotency-Key", "max_length": 300},
        )
    return key


IdempotencyKey = Annotated[str, Depends(require_idempotency_key)]


class IntakeDraftCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    entry_mode: Literal["conversation", "file", "spreadsheet", "form", "template"]
    summary: str | None = None
    owner_role: str | None = Field(default=None, max_length=80)
    sources: list[Any] = Field(default_factory=list)
    facts: list[Any] = Field(default_factory=list)
    conflicts: list[Any] = Field(default_factory=list)
    gaps: list[Any] = Field(default_factory=list)
    freshness: dict[str, Any] = Field(default_factory=dict)


class ApprovalCreate(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    comment: str = Field(min_length=1)
    revision_content_digest: str = Field(min_length=1, max_length=120)
    scope_snapshot: dict[str, Any]
    revision_id: str | None = None

    @field_validator("scope_snapshot")
    @classmethod
    def _scope_not_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("scope_snapshot must not be empty")
        return value


class TaskCreate(BaseModel):
    # The platform always creates its own OpenCode session during binding.  A
    # caller must not be able to pass an existing (for example local TUI)
    # session id and make the platform attach to it.
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=20000)
    entry_mode: Literal["conversation", "file", "spreadsheet", "form", "template"] = (
        "conversation"
    )
    task_category: Literal["voice_interaction"] = "voice_interaction"
    lead_agent_id: str = Field(min_length=1, max_length=120)
    lead_session_id: UUID
    prompt: str = Field(min_length=1, max_length=200_000)
    project_id: UUID | None = None
    node_ids: list[UUID] = Field(default_factory=list, max_length=50)
    device_ids: list[UUID] = Field(default_factory=list, max_length=50)


class SessionMessageCreate(BaseModel):
    """A follow-up turn; length/blank rules live in the service for stable codes."""

    text: str


class StopRequestCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ReleaseRequestCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
    on_site_confirmed: bool = False


def _render(request: Request, data: dict[str, Any], status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=success(request, data))


@router.post("/intake/drafts")
async def post_intake_draft(
    body: IntakeDraftCreate,
    request: Request,
    session: Session,
    idempotency_key: IdempotencyKey,
    principal: Annotated[Principal, Depends(require_capability(CAP_CREATE_TASK))],
) -> JSONResponse:
    payload = body.model_dump()
    scope = "POST /api/v1/intake/drafts"
    data, status_code = await writes.execute_idempotent(
        session,
        scope=scope,
        key=idempotency_key,
        request_hash=writes.request_fingerprint(request.url.path, payload),
        action=lambda: writes.create_intake_draft(
            session,
            title=body.title,
            entry_mode=body.entry_mode,
            summary=body.summary,
            owner_role=body.owner_role or principal.role,
            sources=body.sources,
            facts=body.facts,
            conflicts=body.conflicts,
            gaps=body.gaps,
            freshness=body.freshness,
            principal_role=principal.role,
            actor=principal.actor,
            correlation_id=correlation_id(request),
            path=request.url.path,
        ),
    )
    return _render(request, data, status_code)


@router.post("/tasks")
async def post_task(
    body: TaskCreate,
    request: Request,
    session: Session,
    idempotency_key: IdempotencyKey,
    principal: Annotated[Principal, Depends(require_capability(CAP_CREATE_TASK))],
) -> JSONResponse:
    payload = body.model_dump(mode="json")
    scope = "POST /api/v1/tasks"
    data, status_code = await writes.execute_idempotent(
        session,
        scope=scope,
        key=idempotency_key,
        request_hash=writes.request_fingerprint(request.url.path, payload),
        action=lambda: supervision.create_task_with_supervisor(
            session,
            draft=TaskDraft(
                title=body.title,
                objective=body.objective,
                entry_mode=body.entry_mode,
                task_category=body.task_category,
                lead_agent_id=body.lead_agent_id,
                lead_session_id=body.lead_session_id,
                prompt=body.prompt,
                project_id=body.project_id,
                node_ids=list(body.node_ids),
                device_ids=list(body.device_ids),
            ),
            principal_role=principal.role,
            actor=principal.actor,
            correlation_id=correlation_id(request),
            path=request.url.path,
        ),
    )
    return _render(request, data, status_code)


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    request: Request,
    session: Session,
    provider: Provider,
    principal: Annotated[Principal, Depends(require_admin)],
) -> JSONResponse:
    """Delete a terminal task, its supervisor/revision/dependent rows and session.

    ADMIN-only.  Deleting is idempotent from the caller's perspective: the
    second call returns ``404 NOT_FOUND`` because the task no longer exists.
    No ``Idempotency-Key`` is required for this DELETE.
    """

    data = await supervision.delete_task_and_session(
        session,
        task_id,
        provider,
        actor=principal.actor,
        role=principal.role,
        correlation_id=correlation_id(request),
        path=request.url.path,
    )
    return _render(request, data, 200)


@router.post("/tasks/{task_id}/session/messages")
async def post_task_session_message(
    task_id: str,
    body: SessionMessageCreate,
    request: Request,
    session: Session,
    provider: Provider,
    idempotency_key: IdempotencyKey,
    principal: Annotated[Principal, Depends(require_capability(CAP_CREATE_TASK))],
) -> JSONResponse:
    payload = {"text": body.text}
    scope = "POST /api/v1/tasks/{task_id}/session/messages"
    data, status_code = await writes.execute_idempotent(
        session,
        scope=scope,
        key=idempotency_key,
        request_hash=writes.request_fingerprint(request.url.path, payload),
        status_code=202,
        action=lambda: supervision.send_task_session_message(
            session,
            task_id,
            body.text,
            provider,
            actor=principal.actor,
            role=principal.role,
            correlation_id=correlation_id(request),
            path=request.url.path,
        ),
    )
    return _render(request, data, status_code)


@router.post("/tasks/{task_id}/approvals")
async def post_approval(
    task_id: str,
    body: ApprovalCreate,
    request: Request,
    session: Session,
    idempotency_key: IdempotencyKey,
    principal: Annotated[Principal, Depends(require_capability(CAP_APPROVE))],
) -> JSONResponse:
    payload = body.model_dump()
    scope = "POST /api/v1/tasks/{task_id}/approvals"
    data, status_code = await writes.execute_idempotent(
        session,
        scope=scope,
        key=idempotency_key,
        request_hash=writes.request_fingerprint(request.url.path, payload),
        action=lambda: writes.create_approval(
            session,
            task_identifier=task_id,
            revision_identifier=body.revision_id,
            decision=body.decision,
            comment=body.comment,
            revision_content_digest=body.revision_content_digest,
            scope_snapshot=body.scope_snapshot,
            principal_role=principal.role,
            actor=principal.actor,
            correlation_id=correlation_id(request),
            path=request.url.path,
        ),
    )
    return _render(request, data, status_code)


@router.post("/runs/{run_id}/stop-requests")
async def post_stop_request(
    run_id: str,
    body: StopRequestCreate,
    request: Request,
    session: Session,
    idempotency_key: IdempotencyKey,
    principal: Annotated[Principal, Depends(require_capability(CAP_STOP))],
) -> JSONResponse:
    payload = body.model_dump()
    scope = "POST /api/v1/runs/{run_id}/stop-requests"
    data, status_code = await writes.execute_idempotent(
        session,
        scope=scope,
        key=idempotency_key,
        request_hash=writes.request_fingerprint(request.url.path, payload),
        action=lambda: writes.create_stop_request(
            session,
            run_identifier=run_id,
            reason=body.reason,
            principal_role=principal.role,
            actor=principal.actor,
            correlation_id=correlation_id(request),
            path=request.url.path,
        ),
    )
    return _render(request, data, status_code)


@router.post("/devices/{device_id}/release-requests")
async def post_release_request(
    device_id: str,
    body: ReleaseRequestCreate,
    request: Request,
    session: Session,
    idempotency_key: IdempotencyKey,
    principal: Annotated[Principal, Depends(require_capability(CAP_RELEASE))],
) -> JSONResponse:
    payload = body.model_dump()
    scope = "POST /api/v1/devices/{device_id}/release-requests"
    data, status_code = await writes.execute_idempotent(
        session,
        scope=scope,
        key=idempotency_key,
        request_hash=writes.request_fingerprint(request.url.path, payload),
        action=lambda: writes.create_release_request(
            session,
            device_identifier=device_id,
            reason=body.reason,
            on_site_confirmed=body.on_site_confirmed,
            principal_role=principal.role,
            actor=principal.actor,
            correlation_id=correlation_id(request),
            path=request.url.path,
        ),
    )
    return _render(request, data, status_code)
