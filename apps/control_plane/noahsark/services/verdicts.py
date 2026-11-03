"""Persist an immutable five-axis verdict for a run.

The derivation lives in ``domain.verdict_rules``; this service resolves the
authoritative facts (approval, frozen revision, manifest, evidence, attempts and
lease), records the verdict once, and appends an audit event.  A verdict row is
never updated in place: re-evaluating an already-decided run is a conflict.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.verdict_rules import VerdictFacts, derive_verdict, exact_formal_pass_axes
from ..errors import ApiError
from ..models import Attempt, Task, TaskRevision, Verdict
from . import audit
from .canonical import canonical_digest
from .verdict_facts import (
    approval_valid,
    approved_approval,
    boundary_frozen,
    evidence_facts,
    evidence_items,
    lease_fence_valid,
    load_attempts,
    load_lease,
    manifest_for_run,
    resolve_run,
)
from .writes import resolve_actor_id


def verdict_immutable(run_display: str, verdict_display: str) -> ApiError:
    return ApiError(
        409,
        "VERDICT_IMMUTABLE",
        "A verdict already exists for this run; historical verdicts are never overwritten",
        retryable=False,
        details={"run_id": run_display, "verdict_id": verdict_display},
    )


def _case_results(attempts: list[Attempt]) -> list[dict[str, Any]]:
    return [
        {
            "attempt_id": str(attempt.attempt_id),
            "display_id": attempt.display_id,
            "case_id": str(attempt.case_id),
            "case_version": attempt.case_version,
            "attempt_ordinal": attempt.attempt_ordinal,
            "execution_status": attempt.execution_status,
            "validity_status": attempt.validity_status,
            "business_verdict": attempt.business_verdict,
            "evidence_status": attempt.evidence_status,
            "verification_status": attempt.verification_status,
            "failure_class": attempt.failure_classification,
            "denominator_eligible": attempt.denominator_eligible,
            "flaky_suspect": attempt.flaky_suspect,
        }
        for attempt in attempts
    ]


async def evaluate_run(
    session: AsyncSession,
    identifier: str,
    *,
    principal_role: str,
    actor: str | None,
    correlation_id: str | None,
    path: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    run = await resolve_run(session, identifier)
    existing = (
        await session.execute(
            select(Verdict).where(Verdict.run_id == run.run_id).limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise verdict_immutable(run.display_id, existing.display_id)

    task = await session.get(Task, run.task_id)
    revision = await session.get(TaskRevision, run.revision_id)
    if task is None or revision is None:
        raise ApiError(
            409,
            "VERDICT_FACTS_MISSING",
            "Run has no authoritative task or revision",
            details={"run_id": run.display_id},
        )
    manifest = await manifest_for_run(session, run)
    items = await evidence_items(session, run, manifest)
    attempts = await load_attempts(session, run)
    approval = await approved_approval(session, revision.revision_id)
    lease = await load_lease(session, run)

    required_complete, digest_verified, no_blocking = evidence_facts(manifest, items)
    stop_triggered = run.stop_requested_at is not None or run.lifecycle_status == "STOPPED"
    infra_failure = run.failure_classification == "INFRA_ERROR"
    denominator_eligible = (
        run.formal_denominator_eligible
        and run.mode == "formal"
        and run.validity_status == "VALID"
        and run.evidence_status == "COMPLETE"
        and run.execution_status == "COMPLETED"
        and lease is not None
    )
    facts = VerdictFacts(
        mode=run.mode,
        execution_status=run.execution_status,
        validity_status=run.validity_status,
        business_verdict=run.business_verdict,
        evidence_status=run.evidence_status,
        verification_status=run.verification_status,
        approval_valid=approval_valid(approval, revision),
        boundary_frozen=boundary_frozen(revision, manifest),
        required_evidence_complete=required_complete,
        digest_verified=digest_verified,
        no_blocking_anomaly=no_blocking,
        denominator_eligible=denominator_eligible,
        stop_triggered=stop_triggered,
        infra_failure=infra_failure,
        lease_fence_valid=lease_fence_valid(run, lease),
    )
    derived = derive_verdict(facts)
    decided_at = now or datetime.now(UTC)
    verdict_id = uuid.uuid4()
    display_id = f"vrd-{verdict_id.hex[:8]}"
    case_results = _case_results(attempts)
    manifest_payload = (
        {
            "manifest_id": str(manifest.manifest_id),
            "display_id": manifest.display_id,
            "manifest_digest": manifest.manifest_digest,
        }
        if manifest is not None
        else {}
    )
    node_receipt = dict(manifest.node_receipt or {}) if manifest is not None else {}
    if node_receipt:
        node_receipt = {**node_receipt, "used_for_decision": False}
    payload = {
        "verdict_id": str(verdict_id),
        "display_id": display_id,
        "task_id": str(run.task_id),
        "revision_id": str(run.revision_id),
        "run_id": str(run.run_id),
        "mode": run.mode,
        "axes": facts.axes,
        "decision": derived["decision"],
        "mode_outcome": derived["mode_outcome"],
        "failure_class": derived["failure_class"],
        "formal_pass": derived["formal_pass"],
        "pass_preconditions": derived["pass_preconditions"],
        "denominator": derived["denominator"],
        "reasons": derived["reasons"],
        "exact_formal_pass_axes": exact_formal_pass_axes(facts),
        "case_results": case_results,
        "evidence_manifest": manifest_payload,
        "decided_by": {
            "kind": "linux_verdict_service",
            "identity": actor or "verdict-service",
            "role": principal_role,
        },
        "decided_at": decided_at.isoformat().replace("+00:00", "Z"),
    }
    digest = canonical_digest(payload)
    row = Verdict(
        verdict_id=verdict_id,
        display_id=display_id,
        task_id=run.task_id,
        revision_id=run.revision_id,
        run_id=run.run_id,
        mode=run.mode,
        acceptance_level=(
            manifest.acceptance_level if manifest is not None else "L4"
        ),
        test_level=manifest.test_level if manifest is not None else "T6",
        execution_status=run.execution_status,
        validity_status=run.validity_status,
        business_verdict=run.business_verdict,
        evidence_status=run.evidence_status,
        verification_status=run.verification_status,
        decision=derived["decision"],
        mode_outcome=derived["mode_outcome"],
        failure_class=derived["failure_class"],
        formal_pass=derived["formal_pass"],
        case_results=case_results,
        denominator=derived["denominator"],
        pass_preconditions=derived["pass_preconditions"],
        reasons=derived["reasons"],
        anomalies=dict(manifest.anomalies or {}) if manifest is not None else None,
        evidence_manifest=manifest_payload,
        verification=(
            dict(manifest.linux_verification or {})
            if manifest is not None and manifest.linux_verification
            else None
        ),
        cleanup_receipt=(
            dict(manifest.cleanup_receipt or {})
            if manifest is not None and manifest.cleanup_receipt
            else None
        ),
        node_reported_status=node_receipt or None,
        decided_by=payload["decided_by"],
        decided_at=decided_at,
        verdict_digest=digest,
    )
    session.add(row)
    await audit.append_event(
        session,
        actor_role=principal_role,
        actor_id=await resolve_actor_id(session, actor),
        action="VERDICT_RECORDED",
        object_type="run",
        object_id=run.display_id,
        before=None,
        after={
            "verdict_id": display_id,
            "decision": derived["decision"],
            "formal_pass": derived["formal_pass"],
            "failure_class": derived["failure_class"],
            "pass_preconditions": derived["pass_preconditions"],
            "verdict_digest": digest,
        },
        reason=derived["reasons"][0]["message"],
        correlation_id=correlation_id,
        path=path,
    )
    return {
        **payload,
        "verdict_digest": digest,
        "created": True,
    }


__all__ = ["evaluate_run", "verdict_immutable"]
