"""Versioned, immutable 14-section acceptance reports.

A report is always bound to one task and its current revision.  Creation writes
a new version; freezing is a one-way transition.  Later corrections create a new
version instead of mutating a frozen report.  The four record classes (runs,
evidence, release, unresolved) stay separate.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError, not_found
from ..models import Report, Task, TaskRevision
from . import audit
from .canonical import canonical_digest
from .report_freeze import freeze_report
from .report_model import (
    DEFAULT_ACCESS,
    DENOMINATOR_STATEMENT,
    DISCLOSURE_VALUES,
    REPORT_CATEGORY_NAMES,
    knowledge_records,
)
from .report_sections import build_sections, collect_inputs
from .writes import resolve_actor_id


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


async def create_report(
    session: AsyncSession,
    task_identifier: str,
    *,
    title: str,
    disclosure: str,
    principal_role: str,
    actor: str | None,
    correlation_id: str | None,
    path: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    if disclosure not in DISCLOSURE_VALUES:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "disclosure is not a supported report disclosure level",
            details={"allowed": sorted(DISCLOSURE_VALUES)},
        )
    task = await _resolve_task(session, task_identifier)
    revision = (
        await session.get(TaskRevision, task.current_revision_id)
        if task.current_revision_id
        else None
    )
    runs, verdicts, manifests, evidence, releases, knowledge, candidates = (
        await collect_inputs(session, task, revision)
    )
    knowledge_items, proposed = knowledge_records(runs, evidence, knowledge, candidates)
    sections = build_sections(
        task,
        revision,
        disclosure,
        runs,
        verdicts,
        manifests,
        evidence,
        releases,
        knowledge_items,
        proposed,
    )
    denominator = (
        int((revision.frozen_scope or {}).get("sample_count", 0)) if revision else 0
    )
    denominator_statement = {
        "formal_denominator": denominator,
        "excluded_invalid": 0,
        "excluded_blocked": 0,
        "excluded_stopped": 0,
        "excluded_infra": 0,
        "smoke_excluded": True,
        "statement": DENOMINATOR_STATEMENT,
    }
    max_version = int(
        (
            await session.execute(
                select(func.max(Report.version)).where(Report.task_id == task.task_id)
            )
        ).scalar_one()
        or 0
    )
    report_id = uuid.uuid4()
    display_id = f"rpt-{report_id.hex[:8]}"
    created_at = now or datetime.now(UTC)
    access = dict(DEFAULT_ACCESS)
    content = {
        "report_scope": {
            "task_id": str(task.task_id),
            "revision_id": str(revision.revision_id) if revision else None,
            "run_ids": [str(run.run_id) for run in runs],
            "contract_version": "1.0",
        },
        "sections": sections,
        "category_names": list(REPORT_CATEGORY_NAMES),
    }
    runs_payload = [
        {
            "run_id": str(run.run_id),
            "display_id": run.display_id,
            "mode": run.mode,
            "decision": (
                verdicts[run.run_id].decision
                if run.run_id in verdicts
                else "NOT_EVALUATED"
            ),
            "release_state": next(
                (
                    record["release_state"]
                    for record in releases
                    if record["run_id"] == str(run.run_id)
                ),
                "not_applicable",
            ),
        }
        for run in runs
    ]
    evidence_payload = [
        {
            "evidence_id": str(item.evidence_id),
            "display_id": item.display_id,
            "state": item.state,
            "content_digest": item.content_digest,
            "verified": item.verified,
        }
        for item in evidence
    ]
    release_payload = list(releases)
    unresolved = sections[-1]["items"]
    redaction = {
        "policy_id": "redact-default",
        "applied": False,
        "redacted_paths": [],
    }
    digest_payload = {
        "report_id": str(report_id),
        "display_id": display_id,
        "task_id": str(task.task_id),
        "revision_id": str(revision.revision_id) if revision else None,
        "version": max_version + 1,
        "content": content,
        "runs": runs_payload,
        "evidence": evidence_payload,
        "release": release_payload,
        "unresolved": unresolved,
    }
    report_digest = canonical_digest(digest_payload)
    row = Report(
        report_id=report_id,
        display_id=display_id,
        task_id=task.task_id,
        revision_id=revision.revision_id if revision else None,
        version=max_version + 1,
        title=title,
        lifecycle="DRAFT",
        denominator=denominator,
        disclosure=disclosure,
        sections=len(REPORT_CATEGORY_NAMES),
        evidence_index=len(evidence),
        denominator_statement=denominator_statement,
        runs=runs_payload,
        evidence_index_data=evidence_payload,
        release_index=release_payload,
        access=access,
        unresolved=unresolved,
        redaction=redaction,
        report_digest=report_digest,
        notes=None,
        content=content,
        frozen_at=None,
        created_at=created_at,
    )
    session.add(row)
    await audit.append_event(
        session,
        actor_role=principal_role,
        actor_id=await resolve_actor_id(session, actor),
        action="REPORT_CREATED",
        object_type="report",
        object_id=display_id,
        before=None,
        after={
            "report_id": display_id,
            "task_id": task.display_id,
            "version": max_version + 1,
            "sections": len(REPORT_CATEGORY_NAMES),
            "report_digest": report_digest,
        },
        reason="Created versioned DRAFT acceptance report",
        correlation_id=correlation_id,
        path=path,
    )
    return {
        "report_id": str(report_id),
        "display_id": display_id,
        "task_id": str(task.task_id),
        "version": max_version + 1,
        "lifecycle": "DRAFT",
        "sections": len(REPORT_CATEGORY_NAMES),
        "categories": list(REPORT_CATEGORY_NAMES),
        "report_digest": report_digest,
        "created": True,
    }


__all__ = ["REPORT_CATEGORY_NAMES", "create_report", "freeze_report"]
