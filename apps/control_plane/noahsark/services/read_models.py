"""Read-only projections over the authoritative PostgreSQL control-plane tables.

Every public helper returns plain ``dict``/``list`` structures.  ORM instances
never leave this module, so routers and tests cannot accidentally depend on
session-bound objects.
"""

from __future__ import annotations

import base64
import binascii
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError, not_found
from ..models import (
    Agent,
    Approval,
    Attempt,
    AuditEvent,
    Case,
    Device,
    EvidenceItem,
    EvidenceManifest,
    Gate,
    IdempotencyKey,
    IntakeDraft,
    KnowledgeCandidate,
    KnowledgeItem,
    Lease,
    Node,
    Report,
    Review,
    Role,
    Run,
    Setting,
    Task,
    TaskRevision,
    User,
    Verdict,
)

ACTIVE_RUN_STATES = frozenset({"CREATED", "DISPATCHED", "RUNNING", "FINISHING"})
AXIS_FIELDS = (
    "execution_status",
    "validity_status",
    "business_verdict",
    "evidence_status",
    "verification_status",
)


# ---------------------------------------------------------------------------
# Primitive helpers
# ---------------------------------------------------------------------------
def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _uid(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        offset = int(base64.urlsafe_b64decode(padded.encode()).decode())
    except (ValueError, binascii.Error):
        raise ApiError(400, "INVALID_CURSOR", "cursor is not a valid pagination cursor")
    if offset < 0:
        raise ApiError(400, "INVALID_CURSOR", "cursor is not a valid pagination cursor")
    return offset


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


async def _get_task_by_identifier(session: AsyncSession, identifier: str) -> Task:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("task", identifier)
    parsed = _parse_uuid(raw)
    conditions = [Task.display_id == raw]
    if parsed is not None:
        conditions.append(Task.task_id == parsed)
    task = (
        await session.execute(select(Task).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if task is None:
        raise not_found("task", identifier)
    return task


async def _get_draft_by_identifier(
    session: AsyncSession, identifier: str
) -> IntakeDraft:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("intake_draft", identifier)
    parsed = _parse_uuid(raw)
    conditions = [IntakeDraft.display_id == raw]
    if parsed is not None:
        conditions.append(IntakeDraft.draft_id == parsed)
    draft = (
        await session.execute(select(IntakeDraft).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if draft is None:
        raise not_found("intake_draft", identifier)
    return draft


async def _get_run_by_identifier(session: AsyncSession, identifier: str) -> Run:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("run", identifier)
    parsed = _parse_uuid(raw)
    conditions = [Run.display_id == raw]
    if parsed is not None:
        conditions.append(Run.run_id == parsed)
    run = (
        await session.execute(select(Run).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if run is None:
        raise not_found("run", identifier)
    return run


async def _get_attempt_by_identifier(
    session: AsyncSession, identifier: str
) -> Attempt:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("attempt", identifier)
    parsed = _parse_uuid(raw)
    conditions = [Attempt.display_id == raw]
    if parsed is not None:
        conditions.append(Attempt.attempt_id == parsed)
    attempt = (
        await session.execute(select(Attempt).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if attempt is None:
        raise not_found("attempt", identifier)
    return attempt


async def _get_evidence_by_identifier(
    session: AsyncSession, identifier: str
) -> EvidenceItem:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("evidence", identifier)
    parsed = _parse_uuid(raw)
    conditions = [EvidenceItem.display_id == raw]
    if parsed is not None:
        conditions.append(EvidenceItem.evidence_id == parsed)
    item = (
        await session.execute(select(EvidenceItem).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if item is None:
        raise not_found("evidence", identifier)
    return item


async def _get_device_by_identifier(session: AsyncSession, identifier: str) -> Device:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("device", identifier)
    parsed = _parse_uuid(raw)
    conditions = [Device.display_id == raw]
    if parsed is not None:
        conditions.append(Device.device_id == parsed)
    device = (
        await session.execute(select(Device).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if device is None:
        raise not_found("device", identifier)
    return device


async def _get_node_by_identifier(session: AsyncSession, identifier: str) -> Node:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("node", identifier)
    parsed = _parse_uuid(raw)
    conditions = [Node.display_id == raw]
    if parsed is not None:
        conditions.append(Node.node_id == parsed)
    node = (
        await session.execute(select(Node).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if node is None:
        raise not_found("node", identifier)
    return node


async def _get_report_by_identifier(session: AsyncSession, identifier: str) -> Report:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("report", identifier)
    parsed = _parse_uuid(raw)
    conditions = [Report.display_id == raw]
    if parsed is not None:
        conditions.append(Report.report_id == parsed)
    report = (
        await session.execute(select(Report).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if report is None:
        raise not_found("report", identifier)
    return report


# ---------------------------------------------------------------------------
# Projection helpers
# ---------------------------------------------------------------------------
def _axes(source: Run | Attempt | Verdict | None) -> dict[str, str]:
    if source is None:
        return {field: "UNKNOWN" for field in AXIS_FIELDS}
    return {field: getattr(source, field) for field in AXIS_FIELDS}


def _preconditions(lease: Lease | None) -> dict[str, bool]:
    stored = lease.release_preconditions if lease is not None else None
    stored = stored or {}
    return {
        "local_stop_confirmed": bool(stored.get("local_stop_confirmed", False)),
        "safe_cleanup_done": bool(stored.get("safe_cleanup_done", False)),
        "occupancy_reconciled": bool(stored.get("occupancy_reconciled", False)),
    }


def _release(lease: Lease | None) -> dict[str, Any]:
    """Derive release_state from the three stored preconditions.

    PASS and release are independent: this projection never consults a
    verdict.  A missing lease means the release concept does not apply.
    """

    preconditions = _preconditions(lease)
    all_met = all(preconditions.values())
    if lease is None:
        state = "not_applicable"
    elif lease.state == "QUARANTINED":
        state = "quarantined"
    elif lease.state == "RELEASED" or lease.released_at is not None:
        state = "released"
    elif lease.state in ("RELEASING", "RECLAIM_PENDING"):
        state = "release_requested"
    elif all_met and lease.occupancy_state == "IDLE":
        state = "released"
    else:
        state = "held"
    return {
        "release_state": state,
        "preconditions": preconditions,
        "preconditions_met": all_met,
        "lease_id": _uid(lease.lease_id) if lease is not None else None,
        "lease_state": lease.state if lease is not None else None,
        "lease_epoch": lease.epoch if lease is not None else None,
        "released_at": _iso(lease.released_at) if lease is not None else None,
        # Release is derived only from lease state + the three preconditions.
        # It is deliberately independent of business_verdict / formal PASS.
        "independent_of_verdict": True,
    }


def _freshness(communication_state: str | None, *sources: Any) -> dict[str, Any]:
    """Project freshness independently from state/permit/occupancy.

    ``communication_state`` says whether the link is ONLINE/STALE/OFFLINE;
    freshness says how old the authoritative observation is.  They are related
    but never collapsed: an ONLINE run can still be stale.
    """

    moment: datetime | None = None
    origin: str | None = None
    for name, source in sources:
        if source is None:
            continue
        candidate = (
            getattr(source, "last_heartbeat_at", None)
            or getattr(source, "last_seen_at", None)
            or getattr(source, "finished_at", None)
            or getattr(source, "started_at", None)
            or getattr(source, "updated_at", None)
        )
        if candidate is None:
            continue
        if candidate.tzinfo is None:
            candidate = candidate.replace(tzinfo=UTC)
        if moment is None or candidate > moment:
            moment = candidate
            origin = name
    stale = communication_state in ("STALE", "OFFLINE")
    return {
        "is_stale": stale,
        "communication_state": communication_state,
        "last_authoritative_update": _iso(moment),
        "last_known_at": _iso(moment),
        "source": origin,
    }


def _run_dict(run: Run) -> dict[str, Any]:
    axes = _axes(run)
    return {
        "run_id": _uid(run.run_id),
        "display_id": run.display_id,
        "task_id": _uid(run.task_id),
        "revision_id": _uid(run.revision_id),
        "mode": run.mode,
        "lifecycle_status": run.lifecycle_status,
        **axes,
        "axes": axes,
        "formal_denominator_eligible": run.formal_denominator_eligible,
        "attempt_count": len(run.attempt_ids or []),
        "attempt_ids": list(run.attempt_ids or []),
        "node_id": _uid(run.node_id),
        "device_id": _uid(run.device_id),
        "lease_id": _uid(run.lease_id),
        "lease_epoch": run.lease_epoch,
        "communication_state": run.communication_state,
        "occupancy_state": run.occupancy_state,
        "execution_permit": run.execution_permit,
        "failure_classification": run.failure_classification,
        "error_code": run.error_code,
        "stop_requested_at": _iso(run.stop_requested_at),
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "last_heartbeat_at": _iso(run.last_heartbeat_at),
        "created_at": _iso(run.created_at),
        "updated_at": _iso(run.updated_at),
    }


def _attempt_dict(attempt: Attempt) -> dict[str, Any]:
    axes = _axes(attempt)
    return {
        "attempt_id": _uid(attempt.attempt_id),
        "display_id": attempt.display_id,
        "run_id": _uid(attempt.run_id),
        "case_id": _uid(attempt.case_id),
        "case_version": attempt.case_version,
        "run_mode": attempt.run_mode,
        "attempt_ordinal": attempt.attempt_ordinal,
        **axes,
        "axes": axes,
        "evidence_origin": attempt.evidence_origin,
        "denominator_eligible": attempt.denominator_eligible,
        "retry_of_attempt_id": _uid(attempt.retry_of_attempt_id),
        "flaky_suspect": attempt.flaky_suspect,
        "node_id": _uid(attempt.node_id),
        "device_id": _uid(attempt.device_id),
        "evidence_ids": list(attempt.evidence_ids or []),
        "facts": list(attempt.facts or []),
        "failure_classification": attempt.failure_classification,
        "failure_detail": attempt.failure_detail,
        "started_at": _iso(attempt.started_at),
        "finished_at": _iso(attempt.finished_at),
    }


def _revision_dict(revision: TaskRevision) -> dict[str, Any]:
    return {
        "revision_id": _uid(revision.revision_id),
        "display_id": revision.display_id,
        "task_id": _uid(revision.task_id),
        "revision_number": revision.revision_number,
        "parent_revision_id": _uid(revision.parent_revision_id),
        "change_kind": revision.change_kind,
        "change_reason": revision.change_reason,
        "status": revision.status,
        "immutable": revision.immutable,
        "content_digest": revision.content_digest,
        "frozen_scope": revision.frozen_scope,
        "frozen_at": _iso(revision.frozen_at),
        "approved_at": _iso(revision.approved_at),
        "bundle_id": _uid(revision.bundle_id),
        "superseded_by_revision_id": _uid(revision.superseded_by_revision_id),
        "created_at": _iso(revision.created_at),
    }


def _approval_dict(approval: Approval) -> dict[str, Any]:
    return {
        "approval_id": _uid(approval.approval_id),
        "display_id": approval.display_id,
        "task_id": _uid(approval.task_id),
        "revision_id": _uid(approval.revision_id),
        "submitter_id": _uid(approval.submitter_id),
        "approver_id": _uid(approval.approver_id),
        "decision": approval.decision,
        "comment": approval.comment,
        "revision_content_digest": approval.revision_content_digest,
        "scope_snapshot": approval.scope_snapshot,
        "self_approval": approval.self_approval,
        "prevent_self_review": approval.prevent_self_review,
        "wait_timer_seconds": approval.wait_timer_seconds,
        "effective_at": _iso(approval.effective_at),
        "decided_at": _iso(approval.decided_at),
    }


def _gate_dict(gate: Gate) -> dict[str, Any]:
    return {
        "gate_id": _uid(gate.gate_id),
        "display_id": gate.display_id,
        "gate_code": gate.gate_code,
        "order_index": gate.order_index,
        "status": gate.status,
        "run_id": _uid(gate.run_id),
        "entered_at": _iso(gate.entered_at),
        "exited_at": _iso(gate.exited_at),
        "evaluated_by": gate.evaluated_by,
        "blocker_owner": gate.blocker_owner,
        "blockers": list(gate.blockers or []),
        "evidence_refs": list(gate.evidence_refs or []),
        "version": gate.version,
        "notes": gate.notes,
    }


def _case_dict(case: Case) -> dict[str, Any]:
    return {
        "case_id": _uid(case.case_id),
        "display_id": case.display_id,
        "task_id": _uid(case.task_id),
        "name": case.name,
        "case_version": case.case_version,
        "content_digest": case.content_digest,
        "status": case.status,
        "steps": list(case.steps or []),
        "required_inputs": list(case.required_inputs or []),
        "validity_conditions": list(case.validity_conditions or []),
        "required_evidence": list(case.required_evidence or []),
        "assertion_refs": list(case.assertion_refs or []),
        "frozen_by_revision_id": _uid(case.frozen_by_revision_id),
        "run_mode": case.run_mode,
        "reference_only": case.reference_only,
    }


def _evidence_dict(item: EvidenceItem) -> dict[str, Any]:
    return {
        "evidence_id": _uid(item.evidence_id),
        "display_id": item.display_id,
        "task_id": _uid(item.task_id),
        "run_id": _uid(item.run_id),
        "attempt_id": _uid(item.attempt_id),
        "evidence_class": item.evidence_class,
        "role": item.role,
        "state": item.state,
        "content_digest": item.content_digest,
        "size_bytes": item.size_bytes,
        "media_type": item.media_type,
        "access_level": item.access_level,
        "expected": item.expected,
        "received": item.received,
        "verified": item.verified,
        "provenance": item.provenance,
        "upload": item.upload,
        "integrity": item.integrity,
        "created_at": _iso(item.created_at),
    }


def _evidence_item_status(item: EvidenceItem) -> str:
    """Four-value evidence state for one ledger item.

    ``received`` is not ``verified``: a received but unverified item is
    UNVERIFIED, never COMPLETE.
    """

    if item.state == "conflicted":
        return "CONFLICTED"
    if item.state in ("unavailable", "quarantined"):
        return "INCOMPLETE"
    if item.verified and item.state == "verified":
        return "COMPLETE"
    if item.received:
        return "UNVERIFIED"
    return "INCOMPLETE"


def _evidence_status_from_counts(counts: dict[str, int]) -> str:
    if counts["conflicted"] > 0:
        return "CONFLICTED"
    if counts["expected"] > counts["received"]:
        return "INCOMPLETE"
    if counts["received"] > counts["verified"]:
        return "UNVERIFIED"
    if counts["expected"] > 0:
        return "COMPLETE"
    return "UNVERIFIED"


def _manifest_dict(manifest: EvidenceManifest) -> dict[str, Any]:
    return {
        "manifest_id": _uid(manifest.manifest_id),
        "display_id": manifest.display_id,
        "task_id": _uid(manifest.task_id),
        "revision_id": _uid(manifest.revision_id),
        "run_id": _uid(manifest.run_id),
        "mode": manifest.mode,
        "acceptance_level": manifest.acceptance_level,
        "test_level": manifest.test_level,
        "required_evidence": manifest.required_evidence,
        "completeness": manifest.completeness,
        "denominators": manifest.denominators,
        "anomalies": manifest.anomalies,
        "created_at": _iso(manifest.created_at),
        "created_by": manifest.created_by,
    }


def _verdict_dict(verdict: Verdict) -> dict[str, Any]:
    axes = _axes(verdict)  # type: ignore[arg-type]
    return {
        "verdict_id": _uid(verdict.verdict_id),
        "display_id": verdict.display_id,
        "task_id": _uid(verdict.task_id),
        "revision_id": _uid(verdict.revision_id),
        "run_id": _uid(verdict.run_id),
        "mode": verdict.mode,
        "acceptance_level": verdict.acceptance_level,
        "test_level": verdict.test_level,
        **axes,
        "axes": axes,
        "decision": verdict.decision,
        "mode_outcome": verdict.mode_outcome,
        "failure_class": verdict.failure_class,
        "formal_pass": verdict.formal_pass,
        "reasons": list(verdict.reasons or []),
        "denominator": verdict.denominator,
        "pass_preconditions": verdict.pass_preconditions,
        "decided_at": _iso(verdict.decided_at),
    }


def _report_dict(report: Report) -> dict[str, Any]:
    """Report projection.

    Version, denominator, the four record classes and disclosure stay separate:
    a frozen report never mutates in place, and the release record is not the
    verdict record.
    """

    runs = list(report.runs or [])
    evidence_records = list(report.evidence_index_data or [])
    release_records = list(report.release_index or [])
    unresolved_records = list(report.unresolved or [])
    return {
        "report_id": _uid(report.report_id),
        "display_id": report.display_id,
        "task_id": _uid(report.task_id),
        "revision_id": _uid(report.revision_id),
        "version": report.version,
        "title": report.title,
        "lifecycle": report.lifecycle,
        "frozen": report.lifecycle == "FROZEN",
        "frozen_at": _iso(report.frozen_at),
        "denominator": report.denominator,
        "denominator_statement": dict(report.denominator_statement or {}),
        "disclosure": report.disclosure,
        "access": dict(report.access or {}),
        "sections": report.sections,
        "evidence_index_count": report.evidence_index,
        "runs": runs,
        "evidence_index_data": evidence_records,
        "release_index": release_records,
        "unresolved": unresolved_records,
        "redaction": dict(report.redaction or {}),
        "record_separation": {
            "run_records": runs,
            "evidence_records": evidence_records,
            "release_records": release_records,
            "unresolved_records": unresolved_records,
            "independent": True,
            "note": (
                "Run, evidence, release and unresolved records are reported "
                "independently; none is merged into a single outcome or PASS flag."
            ),
        },
        "content": dict(report.content or {}),
        "report_digest": report.report_digest,
        "notes": report.notes,
        "created_at": _iso(report.created_at),
    }


def _draft_dict(draft: IntakeDraft) -> dict[str, Any]:
    return {
        "draft_id": _uid(draft.draft_id),
        "display_id": draft.display_id,
        "title": draft.title,
        "entry_mode": draft.entry_mode,
        "stage": draft.stage,
        "source_count": draft.source_count,
        "conflict_count": draft.conflict_count,
        "gap_count": draft.gap_count,
        "owner_role": draft.owner_role,
        "summary": draft.summary,
        "sources": list(draft.sources or []),
        "facts": list(draft.facts or []),
        "conflicts": list(draft.conflicts or []),
        "gaps": list(draft.gaps or []),
        "freshness": dict(draft.freshness or {}),
        "created_at": _iso(draft.created_at),
        "updated_at": _iso(draft.updated_at),
    }


def _knowledge_dict(item: KnowledgeItem) -> dict[str, Any]:
    return {
        "knowledge_id": _uid(item.knowledge_id),
        "display_id": item.display_id,
        "status": item.status,
        "title": item.title,
        "applicability": item.applicability,
        "summary": item.summary,
        "source_chain": list(item.source_chain or []),
        "version": item.version,
        "updated_at": _iso(item.updated_at),
    }


def _candidate_dict(candidate: KnowledgeCandidate) -> dict[str, Any]:
    return {
        "candidate_id": _uid(candidate.candidate_id),
        "display_id": candidate.display_id,
        "status": candidate.status,
        "title": candidate.title,
        "source_chain": list(candidate.source_chain or []),
        "applicability": candidate.applicability,
        "proposed_by": candidate.proposed_by,
        "automatic_promotion_allowed": candidate.automatic_promotion_allowed,
        "requires_human_review": candidate.requires_human_review,
        "updated_at": _iso(candidate.updated_at),
    }


def _node_dict(node: Node) -> dict[str, Any]:
    return {
        "node_id": _uid(node.node_id),
        "display_id": node.display_id,
        "hostname": node.hostname,
        "communication_state": node.communication_state,
        "status": node.status,
        "last_heartbeat_at": _iso(node.last_heartbeat_at),
        "heartbeat_interval_seconds": node.heartbeat_interval_seconds,
        "interactive_session": node.interactive_session,
        "spool": node.spool,
        "capabilities": list(node.capabilities or []),
        "updated_at": _iso(node.updated_at),
    }


def _device_dict(device: Device) -> dict[str, Any]:
    return {
        "device_id": _uid(device.device_id),
        "display_id": device.display_id,
        "node_id": _uid(device.node_id),
        "pool_state": device.pool_state,
        "health_state": device.health_state,
        "communication_state": device.communication_state,
        "occupancy_state": device.occupancy_state,
        "current_lease_id": _uid(device.current_lease_id),
        "firmware_version": device.firmware_version,
        "last_seen_at": _iso(device.last_seen_at),
        "updated_at": _iso(device.updated_at),
    }


def _lease_dict(lease: Lease) -> dict[str, Any]:
    return {
        "lease_id": _uid(lease.lease_id),
        "display_id": lease.display_id,
        "node_id": _uid(lease.node_id),
        "device_id": _uid(lease.device_id),
        "task_id": _uid(lease.task_id),
        "revision_id": _uid(lease.revision_id),
        "run_id": _uid(lease.run_id),
        "epoch": lease.epoch,
        "state": lease.state,
        "occupancy_state": lease.occupancy_state,
        "communication_state": lease.communication_state,
        "execution_permit": lease.execution_permit,
        "release_preconditions": _preconditions(lease),
        "release": _release(lease),
        "acquired_at": _iso(lease.acquired_at),
        "expires_at": _iso(lease.expires_at),
        "last_heartbeat_at": _iso(lease.last_heartbeat_at),
        "released_at": _iso(lease.released_at),
        "version": lease.version,
    }


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
async def _select_active_run(session: AsyncSession, task_id: uuid.UUID) -> Run | None:
    runs = (
        await session.execute(
            select(Run)
            .where(Run.task_id == task_id)
            .order_by(Run.updated_at.desc(), Run.created_at.desc())
        )
    ).scalars().all()
    for run in runs:
        if run.lifecycle_status in ACTIVE_RUN_STATES:
            return run
    return runs[0] if runs else None


async def _select_lease(
    session: AsyncSession, task_id: uuid.UUID, run: Run | None
) -> Lease | None:
    if run is not None and run.lease_id is not None:
        lease = await session.get(Lease, run.lease_id)
        if lease is not None:
            return lease
    lease = (
        await session.execute(
            select(Lease)
            .where(Lease.task_id == task_id, Lease.state != "RELEASED")
            .order_by(Lease.acquired_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return lease


async def _lease_for_run(session: AsyncSession, run: Run) -> Lease | None:
    if run.lease_id is not None:
        lease = await session.get(Lease, run.lease_id)
        if lease is not None:
            return lease
    return (
        await session.execute(
            select(Lease)
            .where(Lease.run_id == run.run_id)
            .order_by(Lease.acquired_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _leases_for_runs(
    session: AsyncSession, run_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Lease]:
    if not run_ids:
        return {}
    leases = (
        await session.execute(
            select(Lease)
            .where(Lease.run_id.in_(run_ids))
            .order_by(Lease.acquired_at.desc())
        )
    ).scalars().all()
    grouped: dict[uuid.UUID, Lease] = {}
    for lease in leases:
        grouped.setdefault(lease.run_id, lease)
    return grouped


async def _release_for_report(
    session: AsyncSession, report: Report
) -> dict[str, Any]:
    """Derive the report's release view from lease preconditions, not verdicts."""

    run_id: uuid.UUID | None = None
    for record in report.runs or []:
        if isinstance(record, dict) and record.get("run_id"):
            run_id = _parse_uuid(str(record["run_id"]))
            if run_id is not None:
                break
    if run_id is None:
        return _release(None)
    run = await session.get(Run, run_id)
    if run is None:
        return _release(None)
    return _release(await _lease_for_run(session, run))


async def _evidence_counts(
    session: AsyncSession, task_id: uuid.UUID | None = None
) -> dict[str, int]:
    query = select(
        func.count(EvidenceItem.evidence_id),
        func.count().filter(EvidenceItem.expected.is_(True)),
        func.count().filter(EvidenceItem.received.is_(True)),
        func.count().filter(EvidenceItem.verified.is_(True)),
        func.count().filter(EvidenceItem.state == "conflicted"),
    )
    if task_id is not None:
        query = query.where(EvidenceItem.task_id == task_id)
    row = (await session.execute(query)).one()
    total, expected, received, verified, conflicted = (int(value or 0) for value in row)
    return {
        "total": total,
        "expected": expected,
        "received": received,
        "verified": verified,
        "conflicted": conflicted,
        "missing": max(expected - received, 0),
        "pending_verification": max(received - verified, 0),
    }


async def _progress(
    session: AsyncSession, task: Task, revision_id: uuid.UUID | None
) -> dict[str, Any]:
    case_filters = [
        Case.task_id == task.task_id,
        Case.run_mode == "formal",
        Case.reference_only.is_(False),
        Case.status == "ACTIVE",
    ]
    if revision_id is not None:
        case_filters.append(Case.frozen_by_revision_id == revision_id)
    total = int(
        (
            await session.execute(
                select(func.count(Case.case_id)).where(*case_filters)
            )
        ).scalar_one()
        or 0
    )
    completed = int(
        (
            await session.execute(
                select(func.count(distinct(Attempt.case_id)))
                .join(Run, Run.run_id == Attempt.run_id)
                .where(
                    Run.task_id == task.task_id,
                    Attempt.run_mode == "formal",
                    Attempt.execution_status == "COMPLETED",
                    Attempt.denominator_eligible.is_(True),
                )
            )
        ).scalar_one()
        or 0
    )
    mode = "COUNTS" if total > 0 else "INDETERMINATE"
    percent = None
    if mode == "COUNTS" and total > 0:
        bounded = min(max(completed / total, 0.0), 1.0)
        percent = round(bounded * 100, 1)
    return {
        "mode": mode,
        "denominator_kind": "APPROVED_CASE_COUNT",
        "completed": completed if total > 0 else None,
        "total": total,
        "percent": percent,
        "percent_label": "已完成正式用例占比" if percent is not None else None,
    }


async def _task_summary(session: AsyncSession, task: Task) -> dict[str, Any]:
    revision = None
    if task.current_revision_id is not None:
        revision = await session.get(TaskRevision, task.current_revision_id)
    run = await _select_active_run(session, task.task_id)
    lease = await _select_lease(session, task.task_id, run)
    axes = _axes(run)
    release = _release(lease)
    counts = await _evidence_counts(session, task.task_id)
    progress = await _progress(
        session, task, revision.revision_id if revision is not None else None
    )
    return {
        "task_id": _uid(task.task_id),
        "display_id": task.display_id,
        "title": task.title,
        "objective": task.objective,
        "task_category": task.task_category,
        "entry_mode": task.entry_mode,
        "status": task.status,
        **axes,
        "axes": axes,
        "current_revision_id": _uid(task.current_revision_id),
        "revision_number": revision.revision_number if revision is not None else None,
        "revision_status": revision.status if revision is not None else None,
        "change_kind": revision.change_kind if revision is not None else None,
        "revision_count": len(task.revision_ids or []),
        "latest_run_id": _uid(run.run_id) if run is not None else None,
        "latest_run_mode": run.mode if run is not None else None,
        "latest_run_lifecycle": run.lifecycle_status if run is not None else None,
        "release": release,
        "release_state": release["release_state"],
        "evidence_counts": counts,
        "counts": counts,
        "progress": progress,
        "created_at": _iso(task.created_at),
        "updated_at": _iso(task.updated_at),
    }


def _task_identity(task: Task) -> dict[str, Any]:
    return {
        "task_id": _uid(task.task_id),
        "display_id": task.display_id,
        "title": task.title,
        "status": task.status,
        "current_revision_id": _uid(task.current_revision_id),
    }


async def _attempts_for_runs(
    session: AsyncSession, run_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[Attempt]]:
    if not run_ids:
        return {}
    attempts = (
        await session.execute(
            select(Attempt)
            .where(Attempt.run_id.in_(run_ids))
            .order_by(Attempt.attempt_ordinal)
        )
    ).scalars().all()
    grouped: dict[uuid.UUID, list[Attempt]] = {}
    for attempt in attempts:
        grouped.setdefault(attempt.run_id, []).append(attempt)
    return grouped


# ---------------------------------------------------------------------------
# Public read models
# ---------------------------------------------------------------------------
async def mission(session: AsyncSession) -> dict[str, Any]:
    tasks = (
        await session.execute(
            select(Task).order_by(Task.updated_at.desc(), Task.task_id.desc())
        )
    ).scalars().all()
    task_items = [await _task_summary(session, task) for task in tasks]

    runs = (
        await session.execute(
            select(Run).order_by(Run.updated_at.desc(), Run.created_at.desc())
        )
    ).scalars().all()
    nodes = (
        await session.execute(select(Node).order_by(Node.display_id))
    ).scalars().all()
    devices = (
        await session.execute(select(Device).order_by(Device.display_id))
    ).scalars().all()

    running = [run for run in runs if run.lifecycle_status in ACTIVE_RUN_STATES]
    quarantined = [device for device in devices if device.pool_state == "QUARANTINED"]
    occupied = [device for device in devices if device.occupancy_state == "OCCUPIED"]
    item = {
        "tasks": task_items,
        "items": task_items,
        "runs": [_run_dict(run) for run in runs],
        "nodes": [_node_dict(node) for node in nodes],
        "devices": [_device_dict(device) for device in devices],
        "summary": {
            "task_count": len(task_items),
            "run_count": len(runs),
            "running_run_count": len(running),
            "occupied_device_count": len(occupied),
            "quarantined_device_count": len(quarantined),
        },
    }
    return item


async def list_intake_drafts(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (await session.execute(select(func.count()).select_from(IntakeDraft))).scalar_one()
    )
    rows = (
        await session.execute(
            select(IntakeDraft)
            .order_by(IntakeDraft.updated_at.desc(), IntakeDraft.draft_id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = [_draft_dict(draft) for draft in rows[:limit]]
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
    }


async def get_intake_draft(
    session: AsyncSession, identifier: str
) -> dict[str, Any]:
    draft = await _get_draft_by_identifier(session, identifier)
    return _draft_dict(draft)


async def list_tasks(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (await session.execute(select(func.count()).select_from(Task))).scalar_one()
    )
    rows = (
        await session.execute(
            select(Task)
            .order_by(Task.updated_at.desc(), Task.task_id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = [await _task_summary(session, task) for task in rows[:limit]]
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
    }


async def get_task(session: AsyncSession, identifier: str) -> dict[str, Any]:
    task = await _get_task_by_identifier(session, identifier)
    summary = await _task_summary(session, task)
    revision = None
    if task.current_revision_id is not None:
        revision = await session.get(TaskRevision, task.current_revision_id)
    return {
        **summary,
        "task": summary,
        "current_revision": _revision_dict(revision) if revision is not None else None,
    }


async def task_overview(session: AsyncSession, identifier: str) -> dict[str, Any]:
    task = await _get_task_by_identifier(session, identifier)
    summary = await _task_summary(session, task)
    revision = None
    if task.current_revision_id is not None:
        revision = await session.get(TaskRevision, task.current_revision_id)
    gates = (
        await session.execute(
            select(Gate)
            .where(Gate.task_id == task.task_id)
            .order_by(Gate.order_index, Gate.gate_code)
        )
    ).scalars().all()
    run = await _select_active_run(session, task.task_id)
    lease = await _select_lease(session, task.task_id, run)
    return {
        **summary,
        "task": summary,
        "current_revision": _revision_dict(revision) if revision is not None else None,
        "gates": [_gate_dict(gate) for gate in gates],
        "run": _run_dict(run) if run is not None else None,
        "lease": _lease_dict(lease) if lease is not None else None,
    }


async def task_revisions(
    session: AsyncSession, identifier: str
) -> dict[str, Any]:
    task = await _get_task_by_identifier(session, identifier)
    revisions = (
        await session.execute(
            select(TaskRevision)
            .where(TaskRevision.task_id == task.task_id)
            .order_by(TaskRevision.revision_number)
        )
    ).scalars().all()
    approval = (
        await session.execute(
            select(Approval)
            .where(
                Approval.task_id == task.task_id,
                Approval.revision_id == task.current_revision_id,
            )
            .order_by(Approval.decided_at.desc().nullslast())
            .limit(1)
        )
    ).scalar_one_or_none()
    items = [_revision_dict(revision) for revision in revisions]
    return {
        **_task_identity(task),
        "revisions": items,
        "items": items,
        "approval": _approval_dict(approval) if approval is not None else None,
    }


async def task_plan(session: AsyncSession, identifier: str) -> dict[str, Any]:
    task = await _get_task_by_identifier(session, identifier)
    revision = None
    if task.current_revision_id is not None:
        revision = await session.get(TaskRevision, task.current_revision_id)
    cases = (
        await session.execute(
            select(Case)
            .where(Case.task_id == task.task_id)
            .order_by(Case.run_mode, Case.display_id, Case.case_version)
        )
    ).scalars().all()
    gates = (
        await session.execute(
            select(Gate)
            .where(Gate.task_id == task.task_id)
            .order_by(Gate.order_index, Gate.gate_code)
        )
    ).scalars().all()
    return {
        **_task_identity(task),
        "revision": _revision_dict(revision) if revision is not None else None,
        "cases": [_case_dict(case) for case in cases],
        "gates": [_gate_dict(gate) for gate in gates],
        "progress": await _progress(
            session, task, revision.revision_id if revision is not None else None
        ),
    }


async def task_runs(session: AsyncSession, identifier: str) -> dict[str, Any]:
    task = await _get_task_by_identifier(session, identifier)
    runs = (
        await session.execute(
            select(Run)
            .where(Run.task_id == task.task_id)
            .order_by(Run.started_at.desc().nullslast(), Run.display_id)
        )
    ).scalars().all()
    attempts_by_run = await _attempts_for_runs(
        session, [run.run_id for run in runs]
    )
    items = []
    for run in runs:
        item = _run_dict(run)
        item["attempts"] = [
            _attempt_dict(attempt)
            for attempt in attempts_by_run.get(run.run_id, [])
        ]
        items.append(item)
    return {
        **_task_identity(task),
        "runs": items,
        "items": items,
        "progress": (await _task_summary(session, task))["progress"],
    }


async def task_evidence(session: AsyncSession, identifier: str) -> dict[str, Any]:
    task = await _get_task_by_identifier(session, identifier)
    evidence = (
        await session.execute(
            select(EvidenceItem)
            .where(EvidenceItem.task_id == task.task_id)
            .order_by(EvidenceItem.display_id)
        )
    ).scalars().all()
    manifests = (
        await session.execute(
            select(EvidenceManifest)
            .where(EvidenceManifest.task_id == task.task_id)
            .order_by(EvidenceManifest.created_at.desc())
        )
    ).scalars().all()
    run = await _select_active_run(session, task.task_id)
    counts = await _evidence_counts(session, task.task_id)
    items = [_evidence_dict(item) for item in evidence]
    return {
        **_task_identity(task),
        "axes": _axes(run),
        "evidence_status": run.evidence_status if run is not None else "UNKNOWN",
        "items": items,
        "evidence": items,
        "manifests": [_manifest_dict(manifest) for manifest in manifests],
        "counts": counts,
        "evidence_counts": counts,
    }


async def task_verdict(session: AsyncSession, identifier: str) -> dict[str, Any]:
    task = await _get_task_by_identifier(session, identifier)
    verdict = (
        await session.execute(
            select(Verdict)
            .where(Verdict.task_id == task.task_id)
            .order_by(Verdict.decided_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    run = await _select_active_run(session, task.task_id)
    lease = await _select_lease(session, task.task_id, run)
    release = _release(lease)
    axes = _axes(verdict) if verdict is not None else _axes(run)
    return {
        **_task_identity(task),
        "available": verdict is not None,
        "derived": verdict is None,
        "axes": axes,
        "decision": verdict.decision if verdict is not None else "NOT_EVALUATED",
        "mode_outcome": verdict.mode_outcome if verdict is not None else "NOT_EVALUATED",
        "failure_class": verdict.failure_class if verdict is not None else None,
        "formal_pass": verdict.formal_pass if verdict is not None else False,
        "reasons": (
            list(verdict.reasons or [])
            if verdict is not None
            else ["No finalized verdict row exists; axes are derived from the active run."]
        ),
        "verdict": _verdict_dict(verdict) if verdict is not None else None,
        "release": release,
        "release_state": release["release_state"],
    }


async def task_live(session: AsyncSession, identifier: str) -> dict[str, Any]:
    task = await _get_task_by_identifier(session, identifier)
    run = await _select_active_run(session, task.task_id)
    lease = await _select_lease(session, task.task_id, run)
    attempt = None
    if run is not None:
        attempt = (
            await session.execute(
                select(Attempt)
                .where(Attempt.run_id == run.run_id)
                .order_by(Attempt.attempt_ordinal.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
    node = await session.get(Node, run.node_id) if run and run.node_id else None
    device = await session.get(Device, run.device_id) if run and run.device_id else None
    if device is None and lease is not None:
        device = await session.get(Device, lease.device_id)
    if node is None and lease is not None:
        node = await session.get(Node, lease.node_id)

    heartbeat = None
    for candidate in (attempt, run, lease, node):
        if candidate is None:
            continue
        heartbeat = getattr(candidate, "last_heartbeat_at", None) or getattr(
            candidate, "finished_at", None
        ) or getattr(candidate, "started_at", None)
        if heartbeat is not None:
            break
    freshness = {
        "is_stale": bool(
            (run is not None and run.communication_state in ("STALE", "OFFLINE"))
            or (node is not None and node.communication_state in ("STALE", "OFFLINE"))
        ),
        "last_authoritative_update": _iso(heartbeat),
        "last_known_at": _iso(heartbeat),
    }
    release = _release(lease)
    axes = _axes(attempt) if attempt is not None else _axes(run)
    return {
        **_task_identity(task),
        "axes": axes,
        "run": _run_dict(run) if run is not None else None,
        "attempt": _attempt_dict(attempt) if attempt is not None else None,
        "node": _node_dict(node) if node is not None else None,
        "device": _device_dict(device) if device is not None else None,
        "lease": _lease_dict(lease) if lease is not None else None,
        "link": {
            "communication_state": getattr(run, "communication_state", None),
            "occupancy_state": getattr(run, "occupancy_state", None),
            "execution_status": getattr(run, "execution_status", None),
            "execution_permit": getattr(run, "execution_permit", None),
            "lease_state": getattr(lease, "state", None),
            "lease_id": _uid(lease.lease_id) if lease is not None else None,
            "epoch": lease.epoch if lease is not None else None,
            "pool_state": getattr(device, "pool_state", None),
            "health_state": getattr(device, "health_state", None),
        },
        "freshness": freshness,
        "release": release,
        "release_state": release["release_state"],
    }


async def task_knowledge(session: AsyncSession, identifier: str) -> dict[str, Any]:
    task = await _get_task_by_identifier(session, identifier)
    runs = (
        await session.execute(
            select(Run.display_id).where(Run.task_id == task.task_id)
        )
    ).scalars().all()
    attempts = (
        await session.execute(
            select(Attempt.display_id)
            .join(Run, Run.run_id == Attempt.run_id)
            .where(Run.task_id == task.task_id)
        )
    ).scalars().all()
    evidence = (
        await session.execute(
            select(EvidenceItem.display_id).where(EvidenceItem.task_id == task.task_id)
        )
    ).scalars().all()
    related_ids = set(runs) | set(attempts) | set(evidence)
    knowledge = (
        await session.execute(
            select(KnowledgeItem).order_by(KnowledgeItem.updated_at.desc())
        )
    ).scalars().all()
    candidates = (
        await session.execute(
            select(KnowledgeCandidate).order_by(KnowledgeCandidate.updated_at.desc())
        )
    ).scalars().all()
    knowledge_items = [
        _knowledge_dict(item)
        for item in knowledge
        if related_ids & set(item.source_chain or [])
    ]
    candidate_items = [
        _candidate_dict(item)
        for item in candidates
        if related_ids & set(item.source_chain or [])
    ]
    return {
        **_task_identity(task),
        "items": knowledge_items,
        "knowledge": knowledge_items,
        "candidates": candidate_items,
    }


# ---------------------------------------------------------------------------
# Batch 2 public read models: runs/attempts, evidence, infrastructure, reports
# ---------------------------------------------------------------------------
async def list_runs(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (await session.execute(select(func.count()).select_from(Run))).scalar_one()
    )
    rows = (
        await session.execute(
            select(Run)
            .order_by(Run.updated_at.desc(), Run.run_id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    leases = await _leases_for_runs(session, [run.run_id for run in page])
    items = []
    for run in page:
        lease = leases.get(run.run_id)
        release = _release(lease)
        items.append(
            {
                **_run_dict(run),
                "release": release,
                "release_state": release["release_state"],
                "freshness": _freshness(
                    run.communication_state, ("run", run), ("lease", lease)
                ),
            }
        )
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
    }


async def get_run(session: AsyncSession, identifier: str) -> dict[str, Any]:
    run = await _get_run_by_identifier(session, identifier)
    attempts = (
        await session.execute(
            select(Attempt)
            .where(Attempt.run_id == run.run_id)
            .order_by(Attempt.attempt_ordinal)
        )
    ).scalars().all()
    lease = await _lease_for_run(session, run)
    release = _release(lease)
    node = await session.get(Node, run.node_id) if run.node_id else None
    device = await session.get(Device, run.device_id) if run.device_id else None
    if device is None and lease is not None:
        device = await session.get(Device, lease.device_id)
    if node is None and lease is not None:
        node = await session.get(Node, lease.node_id)
    latest_attempt = attempts[-1] if attempts else None
    freshness = _freshness(
        run.communication_state,
        ("attempt", latest_attempt),
        ("run", run),
        ("lease", lease),
        ("device", device),
        ("node", node),
    )
    return {
        **_run_dict(run),
        "attempt_count": len(attempts),
        "attempts": [_attempt_dict(attempt) for attempt in attempts],
        "release": release,
        "release_state": release["release_state"],
        "node": _node_dict(node) if node is not None else None,
        "device": _device_dict(device) if device is not None else None,
        "lease": _lease_dict(lease) if lease is not None else None,
        "freshness": freshness,
        "signals": {
            "communication_state": run.communication_state,
            "occupancy_state": run.occupancy_state,
            "execution_permit": run.execution_permit,
            "execution_status": run.execution_status,
            "freshness": freshness,
        },
        "pass_implies_release": False,
    }


async def get_run_attempt(
    session: AsyncSession, run_identifier: str, attempt_identifier: str
) -> dict[str, Any]:
    run = await _get_run_by_identifier(session, run_identifier)
    attempt = await _get_attempt_by_identifier(session, attempt_identifier)
    if attempt.run_id != run.run_id:
        # Never leak an attempt through a run it does not belong to.
        raise not_found("attempt", attempt_identifier)
    lease = await _lease_for_run(session, run)
    release = _release(lease)
    freshness = _freshness(
        run.communication_state, ("attempt", attempt), ("run", run), ("lease", lease)
    )
    return {
        **_attempt_dict(attempt),
        "run": _run_dict(run),
        "release": release,
        "release_state": release["release_state"],
        "freshness": freshness,
        "signals": {
            "communication_state": run.communication_state,
            "occupancy_state": run.occupancy_state,
            "execution_permit": run.execution_permit,
            "execution_status": attempt.execution_status,
            "freshness": freshness,
        },
        "pass_implies_release": False,
    }


async def list_evidence(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (
            await session.execute(select(func.count()).select_from(EvidenceItem))
        ).scalar_one()
    )
    rows = (
        await session.execute(
            select(EvidenceItem)
            .order_by(EvidenceItem.created_at.desc(), EvidenceItem.display_id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    counts = await _evidence_counts(session)
    items = []
    for item in page:
        payload = _evidence_dict(item)
        payload["evidence_status"] = _evidence_item_status(item)
        items.append(payload)
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
        "counts": counts,
        "evidence_counts": counts,
        "evidence_status": _evidence_status_from_counts(counts),
    }


async def get_evidence(session: AsyncSession, identifier: str) -> dict[str, Any]:
    item = await _get_evidence_by_identifier(session, identifier)
    run = await session.get(Run, item.run_id) if item.run_id else None
    attempt = await session.get(Attempt, item.attempt_id) if item.attempt_id else None
    manifest = None
    if run is not None and run.evidence_manifest_id is not None:
        manifest = await session.get(EvidenceManifest, run.evidence_manifest_id)
    counts = await _evidence_counts(session, item.task_id)
    payload = _evidence_dict(item)
    payload["evidence_status"] = _evidence_item_status(item)
    return {
        **payload,
        "item": payload,
        "evidence_status": (
            run.evidence_status if run is not None else payload["evidence_status"]
        ),
        "item_evidence_status": payload["evidence_status"],
        "axes": _axes(run),
        "run": _run_dict(run) if run is not None else None,
        "attempt": _attempt_dict(attempt) if attempt is not None else None,
        "manifest": _manifest_dict(manifest) if manifest is not None else None,
        "counts": counts,
        "evidence_counts": counts,
    }


async def list_verdicts(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (await session.execute(select(func.count()).select_from(Verdict))).scalar_one()
    )
    rows = (
        await session.execute(
            select(Verdict)
            .order_by(Verdict.decided_at.desc(), Verdict.verdict_id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = []
    for verdict in rows[:limit]:
        run = await session.get(Run, verdict.run_id)
        lease = await _lease_for_run(session, run) if run is not None else None
        release = _release(lease)
        items.append(
            {
                **_verdict_dict(verdict),
                "release": release,
                "release_state": release["release_state"],
                "release_independent_of_verdict": True,
            }
        )
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
        "available": total > 0,
    }


async def list_devices(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (await session.execute(select(func.count()).select_from(Device))).scalar_one()
    )
    rows = (
        await session.execute(
            select(Device)
            .order_by(Device.display_id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    node_ids = {device.node_id for device in page if device.node_id is not None}
    lease_ids = {
        device.current_lease_id
        for device in page
        if device.current_lease_id is not None
    }
    nodes = (
        (
            await session.execute(select(Node).where(Node.node_id.in_(node_ids)))
        ).scalars().all()
        if node_ids
        else []
    )
    leases = (
        (
            await session.execute(select(Lease).where(Lease.lease_id.in_(lease_ids)))
        ).scalars().all()
        if lease_ids
        else []
    )
    node_map = {node.node_id: node for node in nodes}
    lease_map = {lease.lease_id: lease for lease in leases}

    items = []
    for device in page:
        node = node_map.get(device.node_id)
        lease = lease_map.get(device.current_lease_id) if device.current_lease_id else None
        release = _release(lease)
        items.append(
            {
                **_device_dict(device),
                "node": _node_dict(node) if node is not None else None,
                "current_lease": (
                    _lease_dict(lease) if lease is not None else None
                ),
                "release": release,
                "release_state": release["release_state"],
                "freshness": _freshness(
                    device.communication_state,
                    ("device", device),
                    ("lease", lease),
                    ("node", node),
                ),
            }
        )
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
    }


async def get_device(session: AsyncSession, identifier: str) -> dict[str, Any]:
    device = await _get_device_by_identifier(session, identifier)
    node = await session.get(Node, device.node_id) if device.node_id else None
    current_lease = (
        await session.get(Lease, device.current_lease_id)
        if device.current_lease_id
        else None
    )
    leases = (
        await session.execute(
            select(Lease)
            .where(Lease.device_id == device.device_id)
            .order_by(Lease.acquired_at.desc())
        )
    ).scalars().all()
    run = (
        await session.get(Run, current_lease.run_id)
        if current_lease is not None
        else None
    )
    release = _release(current_lease)
    freshness = _freshness(
        device.communication_state,
        ("device", device),
        ("lease", current_lease),
        ("node", node),
    )
    return {
        **_device_dict(device),
        "node": _node_dict(node) if node is not None else None,
        "current_lease": (
            _lease_dict(current_lease) if current_lease is not None else None
        ),
        "lease": _lease_dict(current_lease) if current_lease is not None else None,
        "leases": [_lease_dict(lease) for lease in leases],
        "run": _run_dict(run) if run is not None else None,
        "release": release,
        "release_state": release["release_state"],
        "freshness": freshness,
        "signals": {
            "communication_state": device.communication_state,
            "occupancy_state": device.occupancy_state,
            "execution_permit": (
                current_lease.execution_permit
                if current_lease is not None
                else None
            ),
            "execution_status": run.execution_status if run is not None else None,
            "freshness": freshness,
        },
        "pass_implies_release": False,
    }


async def list_nodes(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (await session.execute(select(func.count()).select_from(Node))).scalar_one()
    )
    rows = (
        await session.execute(
            select(Node)
            .order_by(Node.display_id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = [
        {
            **_node_dict(node),
            "freshness": _freshness(node.communication_state, ("node", node)),
        }
        for node in rows[:limit]
    ]
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
    }


async def get_node(session: AsyncSession, identifier: str) -> dict[str, Any]:
    node = await _get_node_by_identifier(session, identifier)
    devices = (
        await session.execute(
            select(Device)
            .where(Device.node_id == node.node_id)
            .order_by(Device.display_id)
        )
    ).scalars().all()
    leases = (
        await session.execute(
            select(Lease)
            .where(Lease.node_id == node.node_id)
            .order_by(Lease.acquired_at.desc())
        )
    ).scalars().all()
    latest_lease = leases[0] if leases else None
    freshness = _freshness(
        node.communication_state,
        ("node", node),
        ("lease", latest_lease),
        ("device", devices[0] if devices else None),
    )
    return {
        **_node_dict(node),
        "devices": [_device_dict(device) for device in devices],
        "leases": [_lease_dict(lease) for lease in leases],
        "summary": {
            "device_count": len(devices),
            "occupied_device_count": sum(
                1 for device in devices if device.occupancy_state == "OCCUPIED"
            ),
            "quarantined_device_count": sum(
                1 for device in devices if device.pool_state == "QUARANTINED"
            ),
            "lease_count": len(leases),
        },
        "freshness": freshness,
        "signals": {
            "communication_state": node.communication_state,
            "status": node.status,
            "freshness": freshness,
        },
    }


async def list_leases(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (await session.execute(select(func.count()).select_from(Lease))).scalar_one()
    )
    rows = (
        await session.execute(
            select(Lease)
            .order_by(Lease.acquired_at.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = [_lease_dict(lease) for lease in rows[:limit]]
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
    }


async def list_reports(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (await session.execute(select(func.count()).select_from(Report))).scalar_one()
    )
    rows = (
        await session.execute(
            select(Report)
            .order_by(Report.created_at.desc(), Report.display_id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = []
    for report in rows[:limit]:
        release = await _release_for_report(session, report)
        items.append(
            {
                **_report_dict(report),
                "release": release,
                "release_state": release["release_state"],
            }
        )
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
    }


async def get_report(session: AsyncSession, identifier: str) -> dict[str, Any]:
    report = await _get_report_by_identifier(session, identifier)
    release = await _release_for_report(session, report)
    return {
        **_report_dict(report),
        "release": release,
        "release_state": release["release_state"],
        "release_confirmed": release["release_state"] == "released",
    }


# ---------------------------------------------------------------------------
# Batch 3 public read models: knowledge, runtime, agents, audit, settings
# ---------------------------------------------------------------------------
SECRET_FIELD_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "certificate",
    "credential",
    "authorization",
)

STOP_FIRST_STEPS = (
    ("1 · 处理待 STOP", "先送达并确认 STOP，未送达前不得显示已停止。"),
    ("2 · 停止后续动作", "节点回执 local_stop_confirmed。"),
    ("3 · 补传", "补传离线期间事实。"),
    ("4 · 去重", "按 attempt 与 evidence digest 去重。"),
    ("5 · 对账", "占用、lease、epoch 对账。"),
    ("6 · 恢复领取", "仅在此后恢复新派发。"),
)

RECOVERY_ORDER = (
    "数据库恢复",
    "manifest / 摘要恢复",
    "任务 / 运行恢复",
    "设备占用对账",
)


def _sanitize(value: Any) -> Any:
    """Recursively drop secret-bearing fields.

    Read routes never carry credentials, private keys, certificates or tokens.
    Unknown nested payloads (settings values, audit before/after) are filtered
    defensively so a future seed or write can never leak them through a read.
    """

    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if any(marker in str(key).lower() for marker in SECRET_FIELD_MARKERS):
                cleaned[key] = "[REDACTED]"
            else:
                cleaned[key] = _sanitize(item)
        return cleaned
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


async def _get_knowledge_by_identifier(
    session: AsyncSession, identifier: str
) -> KnowledgeItem:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("knowledge", identifier)
    parsed = _parse_uuid(raw)
    conditions = [KnowledgeItem.display_id == raw]
    if parsed is not None:
        conditions.append(KnowledgeItem.knowledge_id == parsed)
    item = (
        await session.execute(select(KnowledgeItem).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if item is None:
        raise not_found("knowledge", identifier)
    return item


async def _get_agent_by_identifier(session: AsyncSession, identifier: str) -> Agent:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("agent", identifier)
    parsed = _parse_uuid(raw)
    conditions = [Agent.display_id == raw]
    if parsed is not None:
        conditions.append(Agent.agent_id == parsed)
    agent = (
        await session.execute(select(Agent).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if agent is None:
        raise not_found("agent", identifier)
    return agent


async def _get_audit_event_by_identifier(
    session: AsyncSession, identifier: str
) -> AuditEvent:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("audit_event", identifier)
    event = await session.get(AuditEvent, raw)
    if event is None:
        raise not_found("audit_event", identifier)
    return event


def _agent_dict(agent: Agent) -> dict[str, Any]:
    return {
        "agent_id": _uid(agent.agent_id),
        "display_id": agent.display_id,
        "name": agent.name,
        "role": agent.role,
        "model_binding": agent.model_binding,
        "status": agent.status,
        "last_review": _iso(agent.last_review),
        "created_at": _iso(agent.created_at),
    }


def _review_dict(
    review: Review, task_display: str | None, revision_display: str | None
) -> dict[str, Any]:
    return {
        "review_id": _uid(review.review_id),
        "display_id": review.display_id,
        "task_id": _uid(review.task_id),
        "task_display_id": task_display,
        "revision_id": _uid(review.revision_id),
        "revision_display_id": revision_display,
        "stage": review.stage,
        "consensus": review.consensus,
        "open_risks": review.open_risks,
        "updated_at": _iso(review.updated_at),
        "created_at": _iso(review.created_at),
    }


def _audit_dict(event: AuditEvent, *, include_payload: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_id": event.event_id,
        "occurred_at": _iso(event.occurred_at),
        "actor_id": _uid(event.actor_id),
        "actor_role": event.actor_role,
        "action": event.action,
        "object_type": event.object_type,
        "object_id": event.object_id,
        "access_decision": event.access_decision,
        "result": event.result,
        "integrity": event.integrity,
        "correlation_id": event.correlation_id,
        "correlation": _sanitize(dict(event.correlation or {})),
        "prev_event_hash": event.prev_event_hash,
        "event_hash": event.event_hash,
        "created_at": _iso(event.created_at),
        "read_only": True,
    }
    if include_payload:
        payload["reason"] = event.reason
        payload["before"] = _sanitize(event.before)
        payload["after"] = _sanitize(event.after)
        payload["hash_chain"] = {
            "integrity": event.integrity,
            "prev_event_hash": event.prev_event_hash,
            "event_hash": event.event_hash,
            "append_only": True,
            "read_only": True,
        }
    return payload


def _setting_dict(row: Setting) -> dict[str, Any]:
    return {
        "setting_id": _uid(row.setting_id),
        "category": row.category,
        "key": row.key,
        "value": _sanitize(dict(row.value or {})),
        "version": row.version,
        "updated_at": _iso(row.updated_at),
        "created_at": _iso(row.created_at),
    }


def _runtime_model_dict(row: Setting) -> dict[str, Any]:
    value = dict(row.value or {})
    return {
        "binding": value.get("binding") or row.key,
        "purpose": value.get("purpose"),
        "model": value.get("model"),
        "status": value.get("status"),
        "drift": value.get("drift"),
        "setting_key": row.key,
        "version": row.version,
        "updated_at": _iso(row.updated_at),
    }


def _toolchain_dict(row: Setting) -> dict[str, Any]:
    value = dict(row.value or {})
    return {
        "name": value.get("name") or row.key,
        "version": value.get("version"),
        "lock": value.get("lock"),
        "drift": value.get("lock") == "DRIFT",
        "checked_at": value.get("checked_at"),
        "setting_key": row.key,
        "updated_at": _iso(row.updated_at),
    }


async def list_knowledge(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (
            await session.execute(select(func.count()).select_from(KnowledgeItem))
        ).scalar_one()
    )
    rows = (
        await session.execute(
            select(KnowledgeItem)
            .order_by(KnowledgeItem.updated_at.desc(), KnowledgeItem.display_id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = [_knowledge_dict(item) for item in rows[:limit]]
    status_counts: dict[str, int] = {}
    for item in items:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
        "status_counts": status_counts,
    }


async def get_knowledge(session: AsyncSession, identifier: str) -> dict[str, Any]:
    item = await _get_knowledge_by_identifier(session, identifier)
    payload = _knowledge_dict(item)
    return {
        **payload,
        "item": payload,
        "content": _sanitize(dict(item.content or {})),
        "approved_by": _uid(item.approved_by),
        "created_at": _iso(item.created_at),
        "read_only": True,
    }


async def list_knowledge_candidates(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (
            await session.execute(select(func.count()).select_from(KnowledgeCandidate))
        ).scalar_one()
    )
    rows = (
        await session.execute(
            select(KnowledgeCandidate)
            .order_by(
                KnowledgeCandidate.updated_at.desc(),
                KnowledgeCandidate.display_id,
            )
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = [_candidate_dict(candidate) for candidate in rows[:limit]]
    status_counts: dict[str, int] = {}
    for item in items:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
        "status_counts": status_counts,
        "automatic_promotion_allowed": False,
        "requires_human_review": True,
        "policy": {
            "automatic_promotion_allowed": False,
            "requires_human_review": True,
            "note": "Candidates can only be promoted by a human-approved flow; no automatic promotion exists.",
        },
    }


async def runtime_models(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    base = select(Setting).where(Setting.category == "runtime_model")
    total = int(
        (
            await session.execute(
                select(func.count()).select_from(Setting).where(
                    Setting.category == "runtime_model"
                )
            )
        ).scalar_one()
    )
    rows = (
        await session.execute(
            base.order_by(Setting.key).offset(offset).limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = [_runtime_model_dict(row) for row in rows[:limit]]
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
        "drifted_count": sum(1 for item in items if item["drift"] not in (None, "NONE")),
        "read_only": True,
        "q09_pending": True,
        "note": "RT read access is provisional pending Q-09; no runtime write action is exposed.",
    }


async def runtime_toolchain(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    base = select(Setting).where(Setting.category == "runtime_lock")
    total = int(
        (
            await session.execute(
                select(func.count()).select_from(Setting).where(
                    Setting.category == "runtime_lock"
                )
            )
        ).scalar_one()
    )
    rows = (
        await session.execute(
            base.order_by(Setting.key).offset(offset).limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = [_toolchain_dict(row) for row in rows[:limit]]
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
        "drifted_count": sum(1 for item in items if item["drift"]),
        "read_only": True,
        "q09_pending": True,
        "note": "Toolchain locks are read-only facts pending Q-09; writes require ADMIN_ONLY.",
    }


async def list_agents(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (await session.execute(select(func.count()).select_from(Agent))).scalar_one()
    )
    rows = (
        await session.execute(
            select(Agent)
            .order_by(Agent.display_id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = [_agent_dict(agent) for agent in rows[:limit]]
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
        "read_only": True,
        "q09_pending": True,
        "note": "Agent registry is read-only pending Q-09; no governance write is exposed.",
    }


async def get_agent(session: AsyncSession, identifier: str) -> dict[str, Any]:
    agent = await _get_agent_by_identifier(session, identifier)
    payload = _agent_dict(agent)
    binding = (
        await session.execute(
            select(Setting).where(
                Setting.category == "runtime_model",
                Setting.key == agent.model_binding,
            )
        )
    ).scalar_one_or_none()
    return {
        **payload,
        "agent": payload,
        "model": _runtime_model_dict(binding) if binding is not None else None,
        "read_only": True,
        "q09_pending": True,
    }


async def list_reviews(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (await session.execute(select(func.count()).select_from(Review))).scalar_one()
    )
    rows = (
        await session.execute(
            select(Review)
            .order_by(Review.updated_at.desc(), Review.display_id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    task_ids = {review.task_id for review in page}
    revision_ids = {review.revision_id for review in page}
    tasks = (
        (
            await session.execute(select(Task).where(Task.task_id.in_(task_ids)))
        ).scalars().all()
        if task_ids
        else []
    )
    revisions = (
        (
            await session.execute(
                select(TaskRevision).where(
                    TaskRevision.revision_id.in_(revision_ids)
                )
            )
        ).scalars().all()
        if revision_ids
        else []
    )
    task_map = {task.task_id: task.display_id for task in tasks}
    revision_map = {
        revision.revision_id: revision.display_id for revision in revisions
    }
    items = [
        _review_dict(
            review,
            task_map.get(review.task_id),
            revision_map.get(review.revision_id),
        )
        for review in page
    ]
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
        "open_risk_count": sum(item["open_risks"] for item in items),
        "read_only": True,
    }


async def list_audit(
    session: AsyncSession, *, limit: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    offset = _decode_cursor(cursor)
    total = int(
        (
            await session.execute(select(func.count()).select_from(AuditEvent))
        ).scalar_one()
    )
    rows = (
        await session.execute(
            select(AuditEvent)
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.event_id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    has_more = len(rows) > limit
    items = [_audit_dict(event) for event in rows[:limit]]
    denied = sum(1 for item in items if item["access_decision"] == "DENY")
    return {
        "items": items,
        "total": total,
        "next_cursor": _encode_cursor(offset + len(items)) if has_more else None,
        "denied_count": denied,
        "append_only": True,
        "read_only": True,
    }


async def get_audit_event(session: AsyncSession, identifier: str) -> dict[str, Any]:
    event = await _get_audit_event_by_identifier(session, identifier)
    payload = _audit_dict(event, include_payload=True)
    return {
        **payload,
        "event": payload,
        "append_only": True,
        "corrections_are_new_events": True,
    }


async def recovery(session: AsyncSession) -> dict[str, Any]:
    events = (
        await session.execute(
            select(AuditEvent).order_by(
                AuditEvent.occurred_at.desc(), AuditEvent.event_id.desc()
            )
        )
    ).scalars().all()
    integrity_values = sorted(
        {event.integrity for event in events if event.integrity is not None}
    )
    chained = bool(events) and all(event.integrity == "HASH_CHAIN_OK" for event in events)

    idempotency_total = int(
        (
            await session.execute(
                select(func.count()).select_from(IdempotencyKey)
            )
        ).scalar_one()
    )
    idempotency_scopes = (
        await session.execute(
            select(IdempotencyKey.scope)
            .distinct()
            .order_by(IdempotencyKey.scope)
        )
    ).scalars().all()

    reconcile_events = [
        event for event in events if event.action in {"RECONCILE_STARTED", "RECONCILED"}
    ]
    run_display_ids = {
        event.object_id
        for event in reconcile_events
        if event.object_type == "run" and event.object_id
    }
    runs = (
        (
            await session.execute(
                select(Run)
                .where(Run.display_id.in_(run_display_ids))
                .order_by(Run.display_id)
            )
        ).scalars().all()
        if run_display_ids
        else []
    )
    reconciliation_runs = [
        {
            "run_id": _uid(run.run_id),
            "display_id": run.display_id,
            "lifecycle_status": run.lifecycle_status,
            "execution_status": run.execution_status,
            "communication_state": run.communication_state,
            "occupancy_state": run.occupancy_state,
            "stop_requested_at": _iso(run.stop_requested_at),
            "pending_stop": run.stop_requested_at is not None
            and run.execution_status not in {"COMPLETED", "STOPPED", "FAILED"},
        }
        for run in runs
    ]
    pending_stop_count = sum(
        1 for item in reconciliation_runs if item["pending_stop"]
    )

    return {
        "read_only": True,
        "hash_chain": {
            "status": "HASH_CHAIN_OK" if chained else "NOT_VERIFIED",
            "event_count": len(events),
            "integrity_values": integrity_values,
            "append_only": True,
            "read_only": True,
        },
        "idempotency": {
            "key_count": idempotency_total,
            "scopes": list(idempotency_scopes),
            "replay_safe": True,
        },
        "reconciliation": {
            "reconciling_run_count": len(reconciliation_runs),
            "pending_stop_count": pending_stop_count,
            "runs": reconciliation_runs,
        },
        "stop_first_steps": [
            {"order": index + 1, "title": title, "body": body}
            for index, (title, body) in enumerate(STOP_FIRST_STEPS)
        ],
        "recovery_order": [
            {"order": index + 1, "title": title}
            for index, title in enumerate(RECOVERY_ORDER)
        ],
        "drill": {
            "performed": False,
            "rpo_claim": None,
            "rto_claim": None,
            "backup_conclusion": "NOT PROVEN",
            "note": (
                "Static records only. No RPO/RTO may be claimed until a recovery "
                "drill completes; no recovery write action is exposed."
            ),
        },
        "events": [_audit_dict(event) for event in events[:10]],
        "note": (
            "Recovery and reconciliation only handle facts and occupancy; they "
            "never change business verdicts and PASS stays independent of release."
        ),
    }


async def list_settings(session: AsyncSession) -> dict[str, Any]:
    rows = (
        await session.execute(
            select(Setting).order_by(Setting.category, Setting.key)
        )
    ).scalars().all()
    items = [_setting_dict(row) for row in rows]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(item["category"], []).append(item)
    return {
        "items": items,
        "categories": grouped,
        "total": len(items),
        "read_only": True,
        "secrets_exposed": False,
    }


async def settings_access(session: AsyncSession) -> dict[str, Any]:
    roles = (
        await session.execute(
            select(Role).order_by(Role.sort_order, Role.role_code)
        )
    ).scalars().all()
    users = (
        await session.execute(select(User).order_by(User.display_id))
    ).scalars().all()
    role_items = [
        {
            "role_code": role.role_code,
            "role": role.role_code,
            "name": role.name,
            "scope": role.scope,
            "access_level": role.access_level,
            "capabilities": list(role.capabilities or []),
            "sort_order": role.sort_order,
            "read_only": True,
        }
        for role in roles
    ]
    user_items = [
        {
            "user_id": _uid(user.user_id),
            "display_id": user.display_id,
            "name": user.name,
            "actor_kind": user.actor_kind,
            "role_code": user.role_code,
            "status": user.status,
            "read_only": True,
        }
        for user in users
    ]
    return {
        "roles": role_items,
        "users": user_items,
        "items": role_items,
        "total_roles": len(role_items),
        "total_users": len(user_items),
        "read_only": True,
        "secrets_exposed": False,
        "note": "Role headers are a development scaffold, not authentication.",
    }


async def settings_notifications(session: AsyncSession) -> dict[str, Any]:
    rows = (
        await session.execute(
            select(Setting)
            .where(Setting.category == "notification")
            .order_by(Setting.key)
        )
    ).scalars().all()
    items = []
    for row in rows:
        value = dict(row.value or {})
        items.append(
            {
                "key": row.key,
                "channel": value.get("channel"),
                "target": value.get("target"),
                "delivery": value.get("delivery"),
                "dead_letter": value.get("dead_letter", 0),
                "value": _sanitize(value),
                "version": row.version,
                "updated_at": _iso(row.updated_at),
                "read_only": True,
            }
        )
    return {
        "items": items,
        "total": len(items),
        "degraded_count": sum(1 for item in items if item["delivery"] not in (None, "HEALTHY")),
        "dead_letter_total": sum(int(item["dead_letter"] or 0) for item in items),
        "read_only": True,
        "secrets_exposed": False,
        "note": "Notification targets are already masked; no credential is exposed.",
    }


async def settings_retention(session: AsyncSession) -> dict[str, Any]:
    rows = (
        await session.execute(
            select(Setting)
            .where(Setting.category == "retention")
            .order_by(Setting.key)
        )
    ).scalars().all()
    items = []
    for row in rows:
        value = dict(row.value or {})
        items.append(
            {
                "key": row.key,
                "object": value.get("object"),
                "policy": value.get("policy"),
                "version": value.get("version"),
                "effective_at": value.get("effective_at"),
                "setting_version": row.version,
                "updated_at": _iso(row.updated_at),
                "read_only": True,
            }
        )
    return {
        "items": items,
        "total": len(items),
        "read_only": True,
        "note": (
            "Retention changes create compensating events; audit rows are never "
            "modified in place. No retention write is exposed."
        ),
    }
