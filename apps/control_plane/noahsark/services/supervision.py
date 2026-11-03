"""Create a task with its initial revision and OpenCode supervisor binding.

The write path is deliberately narrow: one transaction creates the task, its
first revision, a ``PENDING`` supervisor binding and three append-only audit
events.  No run, verdict or evidence row is implied by task creation.

The read path projects only binding state and sanitized result metadata.  The
remote OpenCode session id is masked and no lease/dispatch/worker internals are
exposed.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError, not_found, validation_error
from ..integrations.opencode.errors import (
    OpenCodeError,
    OpenCodeNotFoundError,
)
from ..integrations.opencode.protocol import MessageView, OpenCodeProvider
from ..integrations.opencode.sanitizer import sanitize_text
from ..models import (
    Agent,
    Approval,
    Attempt,
    Case,
    Device,
    EvidenceItem,
    EvidenceManifest,
    Gate,
    Lease,
    Node,
    Report,
    Review,
    Run,
    SupervisorSession,
    Task,
    TaskRevision,
    Verdict,
)
from ..models.supervisor import ACTIVE_SUPERVISOR_STATES, TERMINAL_SUPERVISOR_STATES
from . import audit
from .canonical import canonical_digest
from .test_campaigns import (
    delete_task_campaigns,
    load_task_campaigns,
    validate_task_campaigns_deletable,
)
from .writes import resolve_actor_id

DEFAULT_TASK_CATEGORY = "voice_interaction"
MAX_EXECUTION_RESOURCES = 50
TASK_STATUS_ON_CREATE = "DRAFT"
REVISION_STATUS_ON_CREATE = "DRAFT"
SUPERVISOR_STATE_ON_CREATE = "PENDING"

SESSION_MESSAGES_MAX = 200
SESSION_MESSAGES_MAX_CHARS = 200_000
SESSION_MESSAGE_MAX_CHARS = 20_000
SESSION_REPLY_MAX_CHARS = 20_000


@dataclass(frozen=True, slots=True)
class TaskDraft:
    """Typed task-creation input; the router parses the request into this."""

    title: str
    objective: str
    entry_mode: str
    lead_agent_id: str
    lead_session_id: uuid.UUID
    prompt: str
    task_category: str = DEFAULT_TASK_CATEGORY
    project_id: uuid.UUID | None = None
    node_ids: list[uuid.UUID] = field(default_factory=list)
    device_ids: list[uuid.UUID] = field(default_factory=list)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def prompt_digest(prompt: str) -> str:
    return "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def mask_remote_session_id(value: str | None) -> str | None:
    """Mask a remote session id so the read API never echoes the full value."""

    if not value:
        return None
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


async def _resolve_agent(session: AsyncSession, identifier: str) -> Agent:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("agent", identifier)
    conditions = [Agent.display_id == raw]
    try:
        conditions.append(Agent.agent_id == uuid.UUID(raw))
    except ValueError:
        pass
    agent = (
        await session.execute(select(Agent).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if agent is None:
        raise not_found("agent", identifier)
    return agent


async def _resolve_task(session: AsyncSession, identifier: str) -> Task:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("task", identifier)
    conditions = [Task.display_id == raw]
    try:
        conditions.append(Task.task_id == uuid.UUID(raw))
    except ValueError:
        pass
    task = (
        await session.execute(select(Task).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if task is None:
        raise not_found("task", identifier)
    return task


async def _resolve_nodes(
    session: AsyncSession, node_ids: list[uuid.UUID]
) -> list[Node]:
    """Resolve every requested node; an unknown id is a 404, never dropped."""

    ordered = list(dict.fromkeys(node_ids))
    if not ordered:
        return []
    rows = (
        await session.execute(select(Node).where(Node.node_id.in_(ordered)))
    ).scalars().all()
    by_id = {row.node_id: row for row in rows}
    for node_id in ordered:
        if node_id not in by_id:
            raise not_found("node", str(node_id))
    return [by_id[node_id] for node_id in ordered]


async def _resolve_devices(
    session: AsyncSession, device_ids: list[uuid.UUID]
) -> list[Device]:
    """Resolve every requested device; an unknown id is a 404, never dropped."""

    ordered = list(dict.fromkeys(device_ids))
    if not ordered:
        return []
    rows = (
        await session.execute(select(Device).where(Device.device_id.in_(ordered)))
    ).scalars().all()
    by_id = {row.device_id: row for row in rows}
    for device_id in ordered:
        if device_id not in by_id:
            raise not_found("device", str(device_id))
    return [by_id[device_id] for device_id in ordered]


def _execution_context_snapshot(
    nodes: list[Node], devices: list[Device]
) -> dict[str, list[dict[str, Any]]]:
    """Immutable-at-creation snapshot of the selected execution resources."""

    return {
        "nodes": [
            {
                "node_id": str(node.node_id),
                "display_id": node.display_id,
                "hostname": node.hostname,
                "communication_state": node.communication_state,
            }
            for node in sorted(nodes, key=lambda item: item.display_id)
        ],
        "devices": [
            {
                "device_id": str(device.device_id),
                "display_id": device.display_id,
                "node_id": str(device.node_id),
                "identity": dict(device.identity or {}),
                "endpoints": list(device.endpoints or []),
                "capabilities": list(device.capabilities or []),
            }
            for device in sorted(devices, key=lambda item: item.display_id)
        ],
    }


async def create_task_with_supervisor(
    session: AsyncSession,
    *,
    draft: TaskDraft,
    principal_role: str,
    actor: str | None,
    correlation_id: str | None,
    path: str,
) -> dict[str, Any]:
    """Atomically create Task + initial revision + PENDING supervisor binding."""

    if not draft.prompt.strip():
        raise validation_error(
            "prompt must not be empty", details={"field": "prompt"}
        )
    if (
        len(draft.node_ids) > MAX_EXECUTION_RESOURCES
        or len(draft.device_ids) > MAX_EXECUTION_RESOURCES
    ):
        raise validation_error(
            "at most 50 nodes and 50 devices may be selected",
            details={
                "field": "node_ids,device_ids",
                "max": MAX_EXECUTION_RESOURCES,
                "node_ids": len(draft.node_ids),
                "device_ids": len(draft.device_ids),
            },
        )

    nodes = await _resolve_nodes(session, list(draft.node_ids))
    devices = await _resolve_devices(session, list(draft.device_ids))
    # A device cannot execute without its owning node: auto-include the node in
    # the snapshot rather than silently dropping the device or its endpoint
    # detail from the prompt.
    selected_node_ids = {node.node_id for node in nodes}
    implicit_node_ids = [
        device.node_id
        for device in devices
        if device.node_id not in selected_node_ids
    ]
    if implicit_node_ids:
        nodes = nodes + await _resolve_nodes(session, implicit_node_ids)
    execution_context = _execution_context_snapshot(nodes, devices)

    agent = await _resolve_agent(session, draft.lead_agent_id)
    actor_id = await resolve_actor_id(session, actor)
    now = datetime.now(UTC)

    task_id = uuid.uuid4()
    revision_id = uuid.uuid4()
    supervisor_id = uuid.uuid4()
    task_display = f"tsk-{task_id.hex[:8]}"
    revision_display = f"rev-{revision_id.hex[:8]}"
    supervisor_display = f"sup-{supervisor_id.hex[:8]}"

    digest = prompt_digest(draft.prompt)
    prompt_bytes = len(draft.prompt.encode("utf-8"))
    submitted_by = str(actor_id) if actor_id is not None else (actor or principal_role)

    task = Task(
        task_id=task_id,
        display_id=task_display,
        task_category=draft.task_category,
        title=draft.title,
        objective=draft.objective,
        entry_mode=draft.entry_mode,
        origin={
            "submitted_by": submitted_by,
            "submitted_at": _iso(now),
            "entry_mode": draft.entry_mode,
            "correlation_id": correlation_id,
        },
        execution_context=execution_context,
        status=TASK_STATUS_ON_CREATE,
        lead_agent_id=agent.agent_id,
        lead_session_id=draft.lead_session_id,
        project_id=draft.project_id,
        current_revision_id=revision_id,
        revision_ids=[str(revision_id)],
        updated_at=now,
        created_at=now,
        source="control-plane",
        seed=False,
    )
    content = {
        "title": draft.title,
        "objective": draft.objective,
        "entry_mode": draft.entry_mode,
        "prompt_digest": digest,
        "prompt_bytes": prompt_bytes,
    }
    revision = TaskRevision(
        revision_id=revision_id,
        display_id=revision_display,
        task_id=task_id,
        revision_number=1,
        parent_revision_id=None,
        change_kind="initial",
        change_reason=None,
        origin={
            "submitted_by": submitted_by,
            "submitted_at": _iso(now),
            "correlation_id": correlation_id,
        },
        content=content,
        status=REVISION_STATUS_ON_CREATE,
        immutable=False,
        content_digest=canonical_digest(content),
        frozen_scope={},
        created_at=now,
        source="control-plane",
        seed=False,
    )
    supervisor = SupervisorSession(
        supervisor_session_id=supervisor_id,
        display_id=supervisor_display,
        task_id=task_id,
        revision_id=revision_id,
        state=SUPERVISOR_STATE_ON_CREATE,
        remote_session_id=None,
        prompt_digest=digest,
        prompt_bytes=prompt_bytes,
        result_summary=None,
        error_code=None,
        result_updated_at=None,
        created_at=now,
        updated_at=now,
        source="control-plane",
        seed=False,
    )
    # Flush in FK order.  The mappers declare no ORM relationships, so the unit
    # of work cannot infer that the revision and binding depend on the task.
    session.add(task)
    await session.flush()
    session.add(revision)
    await session.flush()
    session.add(supervisor)
    await session.flush()

    await audit.append_event(
        session,
        actor_role=principal_role,
        actor_id=actor_id,
        action="TASK_CREATED",
        object_type="task",
        object_id=task_display,
        before=None,
        after={
            "task_id": str(task_id),
            "display_id": task_display,
            "status": TASK_STATUS_ON_CREATE,
            "lead_agent_id": str(agent.agent_id),
            "lead_session_id": str(draft.lead_session_id),
            "task_category": draft.task_category,
            "node_count": len(execution_context["nodes"]),
            "device_count": len(execution_context["devices"]),
        },
        reason="Task created with an initial revision and supervisor binding",
        correlation_id=correlation_id,
        path=path,
    )
    await audit.append_event(
        session,
        actor_role=principal_role,
        actor_id=actor_id,
        action="TASK_REVISION_CREATED",
        object_type="task_revision",
        object_id=revision_display,
        before=None,
        after={
            "revision_id": str(revision_id),
            "display_id": revision_display,
            "task_id": str(task_id),
            "revision_number": 1,
            "change_kind": "initial",
            "status": REVISION_STATUS_ON_CREATE,
            "content_digest": revision.content_digest,
            "prompt_digest": digest,
            "prompt_bytes": prompt_bytes,
        },
        reason="Initial immutable-revision candidate created",
        correlation_id=correlation_id,
        path=path,
    )
    await audit.append_event(
        session,
        actor_role=principal_role,
        actor_id=actor_id,
        action="SUPERVISOR_SESSION_CREATED",
        object_type="supervisor_session",
        object_id=supervisor_display,
        before=None,
        after={
            "supervisor_session_id": str(supervisor_id),
            "display_id": supervisor_display,
            "task_id": str(task_id),
            "revision_id": str(revision_id),
            "state": SUPERVISOR_STATE_ON_CREATE,
            "remote_session_id": None,
            "prompt_digest": digest,
            "prompt_bytes": prompt_bytes,
        },
        reason="Supervisor binding created in PENDING state",
        correlation_id=correlation_id,
        path=path,
    )

    return {
        "task_id": str(task_id),
        "display_id": task_display,
        "task_category": draft.task_category,
        "title": draft.title,
        "objective": draft.objective,
        "entry_mode": draft.entry_mode,
        "status": TASK_STATUS_ON_CREATE,
        "lead_agent_id": str(agent.agent_id),
        "lead_agent_display_id": agent.display_id,
        "lead_session_id": str(draft.lead_session_id),
        "current_revision_id": str(revision_id),
        "revision_display_id": revision_display,
        "supervisor_session_id": str(supervisor_id),
        "supervisor_display_id": supervisor_display,
        "supervisor_state": SUPERVISOR_STATE_ON_CREATE,
        "prompt_digest": digest,
        "prompt_bytes": prompt_bytes,
        "execution_context": execution_context,
        "created_at": _iso(now),
        "created": True,
    }


def _supervisor_projection(
    row: SupervisorSession, task: Task, revision: TaskRevision | None
) -> dict[str, Any]:
    masked = mask_remote_session_id(row.remote_session_id)
    result_available = bool(
        row.result_summary or row.error_code or row.state in TERMINAL_SUPERVISOR_STATES
    )
    return {
        "task_id": str(task.task_id),
        "task_display_id": task.display_id,
        "task_status": task.status,
        "supervisor_session_id": str(row.supervisor_session_id),
        "supervisor_display_id": row.display_id,
        "revision_id": str(row.revision_id),
        "revision_display_id": revision.display_id if revision is not None else None,
        "state": row.state,
        "state_is_terminal": row.state in TERMINAL_SUPERVISOR_STATES,
        "remote_session_id": masked,
        "remote_session_id_masked": True,
        "prompt": {
            "digest": row.prompt_digest,
            "bytes": row.prompt_bytes,
        },
        "result": {
            "available": result_available,
            "summary": row.result_summary,
            "error_code": row.error_code,
            "updated_at": _iso(row.result_updated_at),
        },
        "binding": {
            "task_id": str(row.task_id),
            "one_active_session_per_task": True,
            "stable": True,
            "remote_session_stored_separately": True,
        },
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
        "read_only": True,
    }


async def _load_supervisor_row(
    session: AsyncSession, task: Task
) -> SupervisorSession | None:
    """Return the active binding first, otherwise the most recent history row."""

    active_first = case((SupervisorSession.state.in_(ACTIVE_SUPERVISOR_STATES), 0), else_=1)
    return (
        await session.execute(
            select(SupervisorSession)
            .where(SupervisorSession.task_id == task.task_id)
            .order_by(active_first, SupervisorSession.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def get_task_supervisor(
    session: AsyncSession, identifier: str
) -> dict[str, Any]:
    """Return the active (or latest) supervisor binding for a task."""

    task = await _resolve_task(session, identifier)
    row = await _load_supervisor_row(session, task)
    if row is None:
        raise not_found("supervisor_session", identifier)
    revision = await session.get(TaskRevision, row.revision_id)
    return _supervisor_projection(row, task, revision)


def _iso_from_ms(value: int) -> str:
    return (
        datetime.fromtimestamp(value / 1000, UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _project_session_messages(
    messages: tuple[MessageView, ...],
    *,
    max_messages: int = SESSION_MESSAGES_MAX,
    max_chars: int = SESSION_MESSAGES_MAX_CHARS,
) -> tuple[list[dict[str, Any]], bool]:
    """Sanitize and bound an ordered conversation without leaking provider data.

    Message order is preserved.  Only non-synthetic text parts survive, and
    every part is passed through the OpenCode sanitizer before it reaches the
    response.  ``truncated`` is true when either the message count or the total
    character budget was exhausted.
    """

    selected = messages[:max_messages]
    truncated = len(messages) > max_messages
    remaining = max_chars
    projected: list[dict[str, Any]] = []

    for message in selected:
        if remaining <= 0:
            truncated = True
            break
        parts: list[dict[str, Any]] = []
        for part in message.parts:
            if part.synthetic:
                continue
            if remaining <= 0:
                truncated = True
                break
            sanitized = sanitize_text(part.text, max_chars=remaining)
            if sanitized.truncated:
                truncated = True
            parts.append({"type": "text", "text": sanitized.text})
            remaining -= len(sanitized.text)
        entry: dict[str, Any] = {
            "message_id": message.message_id,
            "role": message.role.value,
            "created_at": _iso_from_ms(message.created_at_ms),
            "parts": parts,
        }
        if message.error_name:
            entry["error_code"] = sanitize_text(
                message.error_name, max_chars=120
            ).text
        projected.append(entry)

    return projected, truncated


def _provider_api_error(exc: OpenCodeError) -> ApiError:
    """Map a provider failure onto the stable API vocabulary without leaking it."""

    match exc:
        case OpenCodeNotFoundError():
            return ApiError(
                404,
                "SESSION_NOT_FOUND",
                "OpenCode session was not found",
                retryable=False,
                details={"provider_code": exc.code},
            )
        case _:
            return ApiError(
                502,
                "PROVIDER_UNAVAILABLE",
                "OpenCode provider is unavailable",
                retryable=exc.retryable,
                details={"provider_code": exc.code},
            )


async def get_task_session_messages(
    session: AsyncSession,
    identifier: str,
    provider: OpenCodeProvider,
) -> dict[str, Any]:
    """Return a sanitized, bounded, read-only view of the bound conversation."""

    task = await _resolve_task(session, identifier)
    row = await _load_supervisor_row(session, task)
    if row is None:
        raise not_found("supervisor_session", identifier)
    if not row.remote_session_id:
        raise ApiError(
            409,
            "SESSION_NOT_BOUND",
            "Task has no bound OpenCode session",
            retryable=False,
            details={"task_id": task.display_id},
        )

    try:
        messages = await provider.session_messages(row.remote_session_id)
    except OpenCodeError as exc:
        raise _provider_api_error(exc) from exc

    projected, truncated = _project_session_messages(messages.messages)
    return {
        "task_id": str(task.task_id),
        "task_display_id": task.display_id,
        "supervisor_session_id": str(row.supervisor_session_id),
        "supervisor_display_id": row.display_id,
        "remote_session_id": mask_remote_session_id(row.remote_session_id),
        "remote_session_id_masked": True,
        "state": row.state,
        "state_is_terminal": row.state in TERMINAL_SUPERVISOR_STATES,
        "message_count": len(projected),
        "truncated": truncated,
        "limits": {
            "max_messages": SESSION_MESSAGES_MAX,
            "max_chars": SESSION_MESSAGES_MAX_CHARS,
        },
        "messages": projected,
        "read_only": True,
    }


def _clean_session_message_text(text: str) -> str:
    """Bound and validate a follow-up turn before any provider call."""

    clean = text.strip()
    if not clean:
        raise ApiError(
            422,
            "SESSION_MESSAGE_EMPTY",
            "Session message text must not be empty",
            retryable=False,
            details={"field": "text"},
        )
    if len(text) > SESSION_MESSAGE_MAX_CHARS:
        raise ApiError(
            413,
            "SESSION_MESSAGE_TOO_LARGE",
            "Session message text exceeds the maximum length",
            retryable=False,
            details={
                "field": "text",
                "max_chars": SESSION_MESSAGE_MAX_CHARS,
                "actual_chars": len(text),
            },
        )
    return clean


async def send_task_session_message(
    session: AsyncSession,
    identifier: str,
    text: str,
    provider: OpenCodeProvider,
    *,
    actor: str | None,
    role: str,
    correlation_id: str | None,
    path: str,
) -> dict[str, Any]:
    """Send one follow-up turn to a terminal task's bound OpenCode session.

    The supervisor binding is not advanced: a follow-up is a conversation
    action on a finished business task, so ``COMPLETED``/``FAILED``/``STOPPED``
    stays untouched.  Concurrent execution states are rejected rather than
    queueing a second prompt against a session the worker is still driving.
    """

    clean = _clean_session_message_text(text)
    task = await _resolve_task(session, identifier)
    row = await _load_supervisor_row(session, task)
    if row is None:
        raise not_found("supervisor_session", identifier)
    if not row.remote_session_id:
        raise ApiError(
            409,
            "SESSION_NOT_BOUND",
            "Task has no bound OpenCode session",
            retryable=False,
            details={"task_id": task.display_id},
        )
    if row.state in ACTIVE_SUPERVISOR_STATES:
        raise ApiError(
            409,
            "SESSION_BUSY",
            "Task session is still executing; wait for a terminal state",
            retryable=True,
            details={"task_id": task.display_id, "state": row.state},
        )

    try:
        turn = await provider.send_message(row.remote_session_id, clean)
    except OpenCodeError as exc:
        raise _provider_api_error(exc) from exc

    reply = sanitize_text(turn.text, max_chars=SESSION_REPLY_MAX_CHARS)
    await audit.append_event(
        session,
        actor_role=role,
        actor_id=await resolve_actor_id(session, actor),
        action="SESSION_MESSAGE_SENT",
        object_type="supervisor_session",
        object_id=row.display_id,
        before=None,
        after={
            "task_id": str(task.task_id),
            "supervisor_session_id": str(row.supervisor_session_id),
            "state": row.state,
            "remote_session_id": mask_remote_session_id(row.remote_session_id),
            "message_id": turn.message_id,
            "role": "assistant",
            "text_chars": len(reply.text),
        },
        reason="Follow-up message sent to the bound OpenCode session",
        correlation_id=correlation_id,
        path=path,
    )

    return {
        "task_id": str(task.task_id),
        "task_display_id": task.display_id,
        "supervisor_session_id": str(row.supervisor_session_id),
        "supervisor_display_id": row.display_id,
        "remote_session_id": mask_remote_session_id(row.remote_session_id),
        "remote_session_id_masked": True,
        "state": row.state,
        "message_id": turn.message_id,
        "role": "assistant",
        "text": reply.text,
        "created_at": _iso_from_ms(turn.created_at_ms),
        "read_only": False,
    }


def _task_active_error(task: Task, row: SupervisorSession) -> ApiError:
    return ApiError(
        409,
        "TASK_ACTIVE",
        "Task is still executing; wait for a terminal state before deleting it",
        retryable=True,
        details={"task_id": task.display_id, "state": row.state},
    )


async def _delete_remote_session(
    provider: OpenCodeProvider, remote_session_id: str
) -> bool:
    """Delete the bound provider session; an already-gone session is success."""

    try:
        return bool(await provider.delete_session(remote_session_id))
    except OpenCodeNotFoundError:
        # The provider may surface 404 instead of swallowing it; the desired
        # end state already holds, so treat it as an idempotent success.
        return True
    except OpenCodeError as exc:
        raise _provider_api_error(exc) from exc


async def delete_task_and_session(
    session: AsyncSession,
    identifier: str,
    provider: OpenCodeProvider,
    *,
    actor: str | None,
    role: str,
    correlation_id: str | None,
    path: str,
) -> dict[str, Any]:
    """Delete a terminal task, every dependent row and its provider session.

    Campaigns linked through ``test_campaigns.task_id`` are part of the task's
    application-level footprint: a ``QUEUED``/``RUNNING`` campaign makes the
    whole delete fail with ``409 CAMPAIGN_ACTIVE`` before any provider or
    database change, while terminal campaigns are removed together with their
    resource leases and ``TEST_CAMPAIGN_DELETED`` audit events.

    The provider is called first: a provider failure aborts with a typed 502
    before any database row is removed, so the local binding is never silently
    orphaned from a live remote session.  The whole database deletion then runs
    in one transaction in foreign-key order (campaigns, then children before
    ``task_revisions`` and ``tasks``).  A second call finds no task and returns
    404.  Artifact blob files are not removed here; only their metadata cascades
    with the campaign rows.
    """

    task = await _resolve_task(session, identifier)
    row = await _load_supervisor_row(session, task)
    if row is not None and row.state in ACTIVE_SUPERVISOR_STATES:
        raise _task_active_error(task, row)

    campaigns = await load_task_campaigns(session, task.task_id)
    await validate_task_campaigns_deletable(task.task_id, campaigns)

    remote_session_id = row.remote_session_id if row is not None else None
    session_deleted = False
    if remote_session_id:
        session_deleted = await _delete_remote_session(
            provider, remote_session_id
        )

    actor_id = await resolve_actor_id(session, actor)
    campaign_ids, campaign_leases_released = await delete_task_campaigns(
        session,
        campaigns,
        actor_role=role,
        actor_id=actor_id,
        correlation_id=correlation_id,
        path=path,
    )

    run_ids = select(Run.run_id).where(Run.task_id == task.task_id)
    attempt_ids = select(Attempt.attempt_id).where(Attempt.run_id.in_(run_ids))

    # FK order: supervisor_sessions references task_revisions; evidence and
    # execution rows reference runs/attempts/leases; revisions and tasks go last.
    await session.execute(
        delete(SupervisorSession).where(
            SupervisorSession.task_id == task.task_id
        )
    )
    await session.execute(
        delete(EvidenceItem).where(
            or_(
                EvidenceItem.task_id == task.task_id,
                EvidenceItem.run_id.in_(run_ids),
                EvidenceItem.attempt_id.in_(attempt_ids),
            )
        )
    )
    await session.execute(
        delete(Attempt).where(Attempt.run_id.in_(run_ids))
    )
    await session.execute(
        delete(EvidenceManifest).where(
            EvidenceManifest.task_id == task.task_id
        )
    )
    await session.execute(delete(Lease).where(Lease.task_id == task.task_id))
    await session.execute(delete(Verdict).where(Verdict.task_id == task.task_id))
    await session.execute(delete(Report).where(Report.task_id == task.task_id))
    await session.execute(delete(Review).where(Review.task_id == task.task_id))
    await session.execute(delete(Gate).where(Gate.task_id == task.task_id))
    await session.execute(
        delete(Approval).where(Approval.task_id == task.task_id)
    )
    await session.execute(delete(Case).where(Case.task_id == task.task_id))
    await session.execute(delete(Run).where(Run.task_id == task.task_id))
    await session.execute(
        delete(TaskRevision).where(TaskRevision.task_id == task.task_id)
    )
    await session.execute(delete(Task).where(Task.task_id == task.task_id))

    await audit.append_event(
        session,
        actor_role=role,
        actor_id=actor_id,
        action="TASK_DELETE",
        object_type="task",
        object_id=task.display_id,
        before={
            "task_id": str(task.task_id),
            "display_id": task.display_id,
            "status": task.status,
            "supervisor_session_id": (
                str(row.supervisor_session_id) if row is not None else None
            ),
            "supervisor_state": row.state if row is not None else None,
            "remote_session_id": mask_remote_session_id(remote_session_id),
        },
        after={
            "task_id": str(task.task_id),
            "display_id": task.display_id,
            "deleted": True,
            "session_deleted": session_deleted,
        },
        reason="Task and bound OpenCode session deleted",
        correlation_id=correlation_id,
        path=path,
    )
    await session.commit()

    return {
        "task_id": str(task.task_id),
        "display_id": task.display_id,
        "deleted": True,
        "session_deleted": session_deleted,
        "campaigns_deleted": len(campaign_ids),
        "campaign_ids": campaign_ids,
        "campaign_leases_released": campaign_leases_released,
    }
