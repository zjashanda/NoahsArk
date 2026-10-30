"""W3 write services.

Every write is guarded here, not in the router: permission is resolved by the
route dependency, then this module enforces state-machine rules, idempotency,
append-only audit and atomic commit.  A request never mutates a frozen revision,
never marks a run STOPPED, and never claims a device was released from a release
*request*.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError, forbidden, not_found
from ..models import (
    Approval,
    AuditEvent,
    Device,
    IdempotencyKey,
    IntakeDraft,
    Lease,
    Node,
    Run,
    Task,
    TaskRevision,
    User,
    WriteRequest,
)
from . import audit

ACTIVE_RUN_STATES = frozenset({"CREATED", "DISPATCHED", "RUNNING", "FINISHING"})
FROZEN_REVISION_STATES = frozenset({"FROZEN"})
RELEASE_PRECONDITION_KEYS = (
    "local_stop_confirmed",
    "safe_cleanup_done",
    "occupancy_reconciled",
)


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------
def request_fingerprint(path: str, payload: Any) -> str:
    canonical = json.dumps(
        {"path": path, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _find_key(
    session: AsyncSession, scope: str, key: str
) -> IdempotencyKey | None:
    return (
        await session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.scope == scope, IdempotencyKey.key == key
            )
        )
    ).scalar_one_or_none()


async def execute_idempotent(
    session: AsyncSession,
    *,
    scope: str,
    key: str,
    request_hash: str,
    action: Callable[[], Awaitable[dict[str, Any]]],
    status_code: int = 201,
) -> tuple[dict[str, Any], int]:
    """Run ``action`` once per ``(scope, key)`` and persist its response.

    Reusing a key with the identical payload returns the original response; any
    payload difference is a hard conflict.  The audit row and idempotency row are
    committed in the same transaction as the write.
    """

    existing = await _find_key(session, scope, key)
    if existing is not None:
        if existing.request_hash != request_hash:
            raise ApiError(
                409,
                "IDEMPOTENCY_CONFLICT",
                "Idempotency-Key was already used with a different payload",
                details={"scope": scope, "key": key},
            )
        return dict(existing.response or {}), existing.status_code

    try:
        data = await action()
        session.add(
            IdempotencyKey(
                id=uuid.uuid4(),
                scope=scope,
                key=key,
                request_hash=request_hash,
                status_code=status_code,
                response=data,
            )
        )
        await session.commit()
        return data, status_code
    except IntegrityError as exc:
        await session.rollback()
        existing = await _find_key(session, scope, key)
        if existing is None:
            raise ApiError(
                409,
                "INVALID_STATE_TRANSITION",
                "Write conflicted with existing state; refresh and retry",
                retryable=False,
            ) from exc
        if existing.request_hash != request_hash:
            raise ApiError(
                409,
                "IDEMPOTENCY_CONFLICT",
                "Idempotency-Key was already used with a different payload",
                details={"scope": scope, "key": key},
            ) from exc
        return dict(existing.response or {}), existing.status_code


# ---------------------------------------------------------------------------
# Audit (append-only) -- delegated to the hash-chain service
# ---------------------------------------------------------------------------
async def append_audit(
    session: AsyncSession,
    *,
    actor_role: str,
    actor_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    reason: str | None,
    correlation_id: str | None,
    path: str,
) -> AuditEvent:
    return await audit.append_event(
        session,
        actor_role=actor_role,
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before=before,
        after=after,
        reason=reason,
        correlation_id=correlation_id,
        path=path,
    )


async def resolve_actor_id(
    session: AsyncSession, actor: str | None
) -> uuid.UUID | None:
    if not actor:
        return None
    raw = actor.strip()
    if not raw:
        return None
    user = (
        await session.execute(
            select(User).where(User.display_id == raw).limit(1)
        )
    ).scalar_one_or_none()
    if user is not None:
        return user.user_id
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


def _actor_uuid(actor: str | None, role: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"noahsark-actor:{actor or role}")


def _as_uuid(value: Any) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if not isinstance(value, str):
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def _resolve(
    session: AsyncSession,
    model: Any,
    display_field: Any,
    id_field: Any,
    identifier: str,
    object_type: str,
) -> Any:
    raw = (identifier or "").strip()
    parsed = _as_uuid(raw)
    conditions = [display_field == raw]
    if parsed is not None:
        conditions.append(id_field == parsed)
    row = (
        await session.execute(select(model).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if row is None:
        raise not_found(object_type, identifier)
    return row


# ---------------------------------------------------------------------------
# 1. Intake draft
# ---------------------------------------------------------------------------
async def create_intake_draft(
    session: AsyncSession,
    *,
    title: str,
    entry_mode: str,
    summary: str | None,
    owner_role: str,
    sources: list[Any],
    facts: list[Any],
    conflicts: list[Any],
    gaps: list[Any],
    freshness: dict[str, Any],
    principal_role: str,
    actor: str | None,
    correlation_id: str | None,
    path: str,
) -> dict[str, Any]:
    draft_id = uuid.uuid4()
    display_id = f"drf-{draft_id.hex[:8]}"
    row = IntakeDraft(
        draft_id=draft_id,
        display_id=display_id,
        title=title,
        entry_mode=entry_mode,
        stage="DRAFT",
        source_count=len(sources),
        conflict_count=len(conflicts),
        gap_count=len(gaps),
        owner_role=owner_role or principal_role,
        summary=summary,
        sources=sources,
        facts=facts,
        conflicts=conflicts,
        gaps=gaps,
        freshness=freshness,
        source="control-plane",
        seed=False,
    )
    session.add(row)
    await append_audit(
        session,
        actor_role=principal_role,
        actor_id=await resolve_actor_id(session, actor),
        action="INTAKE_DRAFT_CREATED",
        object_type="intake_draft",
        object_id=display_id,
        before=None,
        after={
            "draft_id": str(draft_id),
            "display_id": display_id,
            "title": title,
            "entry_mode": entry_mode,
            "stage": "DRAFT",
        },
        reason=f"Created intake draft in {entry_mode} mode",
        correlation_id=correlation_id,
        path=path,
    )
    return {
        "draft_id": str(draft_id),
        "display_id": display_id,
        "title": title,
        "entry_mode": entry_mode,
        "stage": "DRAFT",
        "owner_role": owner_role or principal_role,
        "source_count": len(sources),
        "conflict_count": len(conflicts),
        "gap_count": len(gaps),
        "created": True,
    }


# ---------------------------------------------------------------------------
# 2. Approval
# ---------------------------------------------------------------------------
async def create_approval(
    session: AsyncSession,
    *,
    task_identifier: str,
    revision_identifier: str | None,
    decision: str,
    comment: str,
    revision_content_digest: str,
    scope_snapshot: dict[str, Any],
    principal_role: str,
    actor: str | None,
    correlation_id: str | None,
    path: str,
) -> dict[str, Any]:
    task = await _resolve(
        session, Task, Task.display_id, Task.task_id, task_identifier, "task"
    )
    if revision_identifier:
        revision = await _resolve(
            session,
            TaskRevision,
            TaskRevision.display_id,
            TaskRevision.revision_id,
            revision_identifier,
            "task_revision",
        )
        if revision.task_id != task.task_id:
            raise not_found("task_revision", revision_identifier)
    else:
        if task.current_revision_id is None:
            raise ApiError(
                409,
                "INVALID_STATE_TRANSITION",
                "Task has no current revision to approve",
                details={"task_id": task.display_id},
            )
        revision = await session.get(TaskRevision, task.current_revision_id)
        if revision is None:
            raise not_found("task_revision", str(task.current_revision_id))

    if revision.status not in FROZEN_REVISION_STATES:
        raise ApiError(
            409,
            "INVALID_STATE_TRANSITION",
            f"Revision {revision.display_id} is {revision.status}; only FROZEN revisions can be approved",
            details={
                "revision_id": revision.display_id,
                "revision_status": revision.status,
            },
        )
    if revision_content_digest != revision.content_digest:
        raise ApiError(
            409,
            "INVALID_STATE_TRANSITION",
            "revision_content_digest does not match the frozen revision digest",
            details={
                "revision_id": revision.display_id,
                "expected_digest": revision.content_digest,
            },
        )
    if not scope_snapshot:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "scope_snapshot must not be empty",
            details={"field": "scope_snapshot"},
        )

    actor_id = await resolve_actor_id(session, actor)
    approver_id = actor_id or _actor_uuid(actor, principal_role)
    submitter_id = (
        _as_uuid((task.origin or {}).get("submitted_by"))
        or _as_uuid((revision.origin or {}).get("submitted_by"))
        or task.lead_session_id
        or approver_id
    )
    if actor_id is not None and actor_id == submitter_id:
        raise forbidden(
            "Self-approval is not allowed",
            details={
                "reason": "SELF_APPROVAL_FORBIDDEN",
                "approver_id": str(actor_id),
                "submitter_id": str(submitter_id),
            },
        )

    now = datetime.now(UTC)
    approval_id = uuid.uuid4()
    display_id = f"apr-{approval_id.hex[:8]}"
    row = Approval(
        approval_id=approval_id,
        display_id=display_id,
        task_id=task.task_id,
        revision_id=revision.revision_id,
        submitter_id=submitter_id,
        approver_id=approver_id,
        decision=decision,
        comment=comment,
        revision_content_digest=revision_content_digest,
        scope_snapshot=scope_snapshot,
        self_approval=False,
        prevent_self_review=True,
        wait_timer_seconds=0,
        effective_at=now if decision == "APPROVED" else None,
        decided_at=now,
        withdrawn_reason=None,
        superseded_by_approval_id=None,
        idempotency_key=f"approval:{approval_id.hex}",
        source="control-plane",
        seed=False,
    )
    session.add(row)
    await append_audit(
        session,
        actor_role=principal_role,
        actor_id=actor_id,
        action="APPROVAL_RECORDED",
        object_type="task_revision",
        object_id=revision.display_id,
        before={
            "revision_status": revision.status,
            "approved_at": revision.approved_at.isoformat()
            if revision.approved_at
            else None,
        },
        after={
            "approval_id": display_id,
            "decision": decision,
            "revision_content_digest": revision_content_digest,
            "scope_snapshot": scope_snapshot,
        },
        reason=comment,
        correlation_id=correlation_id,
        path=path,
    )
    return {
        "approval_id": str(approval_id),
        "display_id": display_id,
        "task_id": str(task.task_id),
        "task_display_id": task.display_id,
        "revision_id": str(revision.revision_id),
        "revision_display_id": revision.display_id,
        "decision": decision,
        "comment": comment,
        "revision_content_digest": revision_content_digest,
        "scope_snapshot": scope_snapshot,
        "self_approval": False,
        "prevent_self_review": True,
        "decided_at": now.isoformat().replace("+00:00", "Z"),
        "created": True,
    }


# ---------------------------------------------------------------------------
# 3. STOP request
# ---------------------------------------------------------------------------
async def create_stop_request(
    session: AsyncSession,
    *,
    run_identifier: str,
    reason: str,
    principal_role: str,
    actor: str | None,
    correlation_id: str | None,
    path: str,
) -> dict[str, Any]:
    run = await _resolve(
        session, Run, Run.display_id, Run.run_id, run_identifier, "run"
    )
    if (
        run.lifecycle_status not in ACTIVE_RUN_STATES
        or run.execution_status in {"COMPLETED", "ABORTED", "STOPPED"}
    ):
        raise ApiError(
            409,
            "INVALID_STATE_TRANSITION",
            f"Run {run.display_id} is not stoppable in "
            f"{run.lifecycle_status}/{run.execution_status}",
            details={
                "run_id": run.display_id,
                "lifecycle_status": run.lifecycle_status,
                "execution_status": run.execution_status,
            },
        )

    before = {
        "lifecycle_status": run.lifecycle_status,
        "execution_status": run.execution_status,
        "stop_requested_at": run.stop_requested_at.isoformat()
        if run.stop_requested_at
        else None,
        "stop_reason": run.stop_reason,
    }
    now = datetime.now(UTC)
    if run.stop_requested_at is None:
        run.stop_requested_at = now
    run.stop_reason = reason
    run.updated_at = now
    stop_request_id = f"stop-{uuid.uuid4().hex[:12]}"
    actor_id = await resolve_actor_id(session, actor)
    session.add(
        WriteRequest(
            request_id=uuid.uuid4(),
            display_id=stop_request_id,
            request_type="STOP",
            target_type="run",
            target_id=run.display_id,
            status="REQUESTED",
            reason=reason,
            payload={
                "stop_request_id": stop_request_id,
                "stops_run_immediately": False,
            },
            requested_by=actor_id,
            requested_role=principal_role,
            correlation_id=correlation_id,
            created_at=now,
            source="control-plane",
            seed=False,
        )
    )
    after = {
        "lifecycle_status": run.lifecycle_status,
        "execution_status": run.execution_status,
        "stop_requested_at": run.stop_requested_at.isoformat()
        if run.stop_requested_at
        else None,
        "stop_reason": run.stop_reason,
        "stop_request_id": stop_request_id,
        "stops_run_immediately": False,
    }
    await append_audit(
        session,
        actor_role=principal_role,
        actor_id=actor_id,
        action="STOP_REQUESTED",
        object_type="run",
        object_id=run.display_id,
        before=before,
        after=after,
        reason=reason,
        correlation_id=correlation_id,
        path=path,
    )
    return {
        "stop_request_id": stop_request_id,
        "run_id": str(run.run_id),
        "run_display_id": run.display_id,
        "requested": True,
        "stop_requested_at": run.stop_requested_at.isoformat().replace("+00:00", "Z"),
        "stop_reason": run.stop_reason,
        "lifecycle_status": run.lifecycle_status,
        "execution_status": run.execution_status,
        "stops_run_immediately": False,
        "created": True,
    }


# ---------------------------------------------------------------------------
# 4. Device release request
# ---------------------------------------------------------------------------
async def create_release_request(
    session: AsyncSession,
    *,
    device_identifier: str,
    reason: str | None,
    on_site_confirmed: bool,
    principal_role: str,
    actor: str | None,
    correlation_id: str | None,
    path: str,
) -> dict[str, Any]:
    device = await _resolve(
        session,
        Device,
        Device.display_id,
        Device.device_id,
        device_identifier,
        "device",
    )
    lease: Lease | None = None
    if device.current_lease_id is not None:
        lease = await session.get(Lease, device.current_lease_id)
    if lease is None:
        lease = (
            await session.execute(
                select(Lease)
                .where(
                    Lease.device_id == device.device_id,
                    Lease.state != "RELEASED",
                )
                .limit(1)
            )
        ).scalar_one_or_none()

    preconditions = dict(lease.release_preconditions or {}) if lease else {}
    missing: list[str] = []
    for key in RELEASE_PRECONDITION_KEYS:
        if preconditions.get(key) is not True:
            missing.append(key)

    run = await session.get(Run, lease.run_id) if lease else None
    cleanup_receipt_present = bool(run and run.cleanup_receipt_id is not None)
    if not cleanup_receipt_present:
        missing.append("cleanup_receipt")

    node = await session.get(Node, lease.node_id) if lease else None
    r05_node_reachable = bool(node and node.communication_state == "ONLINE")
    r05_satisfied = r05_node_reachable or on_site_confirmed
    if not r05_satisfied:
        missing.append("r05_node_reachable_or_on_site_confirmed")

    if lease is None or missing:
        raise ApiError(
            409,
            "RELEASE_PRECONDITION_FAILED",
            "Device release preconditions are not satisfied",
            details={
                "reason": "RELEASE_PRECONDITION_FAILED",
                "device_id": device.display_id,
                "lease_id": lease.display_id if lease else None,
                "missing": missing,
                "preconditions": preconditions,
                "cleanup_receipt_present": cleanup_receipt_present,
                "r05_satisfied": r05_satisfied,
                "r05_node_reachable": r05_node_reachable,
                "on_site_confirmed": on_site_confirmed,
            },
        )

    request_id = f"rel-{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)
    actor_id = await resolve_actor_id(session, actor)
    session.add(
        WriteRequest(
            request_id=uuid.uuid4(),
            display_id=request_id,
            request_type="RELEASE",
            target_type="device",
            target_id=device.display_id,
            status="REQUESTED",
            reason=reason or "Release request confirmed with all preconditions",
            payload={
                "release_request_id": request_id,
                "lease_id": lease.display_id,
                "preconditions": preconditions,
                "release_equals_pass": False,
            },
            requested_by=actor_id,
            requested_role=principal_role,
            correlation_id=correlation_id,
            created_at=now,
            source="control-plane",
            seed=False,
        )
    )
    await append_audit(
        session,
        actor_role=principal_role,
        actor_id=actor_id,
        action="RELEASE_REQUESTED",
        object_type="device",
        object_id=device.display_id,
        before={
            "occupancy_state": device.occupancy_state,
            "pool_state": device.pool_state,
            "release_preconditions": preconditions,
        },
        after={
            "release_request_id": request_id,
            "release_state": "REQUESTED",
            "preconditions": preconditions,
            "cleanup_receipt_present": True,
            "r05_satisfied": True,
            "release_equals_pass": False,
            "verdict_unchanged": True,
        },
        reason=reason or "Release request confirmed with all preconditions",
        correlation_id=correlation_id,
        path=path,
    )
    return {
        "release_request_id": request_id,
        "device_id": str(device.device_id),
        "device_display_id": device.display_id,
        "lease_id": str(lease.lease_id),
        "lease_display_id": lease.display_id,
        "requested": True,
        "release_state": "REQUESTED",
        "preconditions": preconditions,
        "cleanup_receipt_present": True,
        "r05_satisfied": True,
        "release_equals_pass": False,
        "verdict_unchanged": True,
        "requested_at": now.isoformat().replace("+00:00", "Z"),
        "created": True,
    }
