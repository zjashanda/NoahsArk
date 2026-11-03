"""Build the fixed 14 report sections from authoritative rows."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    EvidenceItem,
    EvidenceManifest,
    KnowledgeCandidate,
    KnowledgeItem,
    Lease,
    Node,
    Run,
    Task,
    TaskRevision,
    Verdict,
)
from .report_model import release_record, section


async def collect_inputs(
    session: AsyncSession, task: Task, revision: TaskRevision | None
) -> tuple[
    list[Run],
    dict[uuid.UUID, Verdict],
    list[EvidenceManifest],
    list[EvidenceItem],
    list[dict[str, Any]],
    list[KnowledgeItem],
    list[KnowledgeCandidate],
]:
    runs = list(
        (
            await session.execute(
                select(Run).where(Run.task_id == task.task_id).order_by(Run.display_id)
            )
        ).scalars().all()
    )
    run_ids = [run.run_id for run in runs]
    verdicts: dict[uuid.UUID, Verdict] = {}
    if run_ids:
        for verdict in (
            await session.execute(select(Verdict).where(Verdict.run_id.in_(run_ids)))
        ).scalars().all():
            verdicts[verdict.run_id] = verdict
    manifests = list(
        (
            await session.execute(
                select(EvidenceManifest).where(EvidenceManifest.task_id == task.task_id)
            )
        ).scalars().all()
    )
    evidence = list(
        (
            await session.execute(
                select(EvidenceItem)
                .where(EvidenceItem.task_id == task.task_id)
                .order_by(EvidenceItem.display_id)
            )
        ).scalars().all()
    )
    releases = []
    for run in runs:
        lease = await session.get(Lease, run.lease_id) if run.lease_id else None
        node = await session.get(Node, run.node_id) if run.node_id else None
        releases.append(release_record(lease, run, node))
    knowledge = list((await session.execute(select(KnowledgeItem))).scalars().all())
    candidates = list(
        (await session.execute(select(KnowledgeCandidate))).scalars().all()
    )
    return runs, verdicts, manifests, evidence, releases, knowledge, candidates


def build_sections(
    task: Task,
    revision: TaskRevision | None,
    disclosure: str,
    runs: list[Run],
    verdicts: dict[uuid.UUID, Verdict],
    manifests: list[EvidenceManifest],
    evidence: list[EvidenceItem],
    releases: list[dict[str, Any]],
    knowledge_items: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    static_runs = [run for run in runs if run.mode == "static"]
    smoke_runs = [run for run in runs if run.mode == "smoke"]
    formal_runs = [run for run in runs if run.mode == "formal"]
    formal_records = []
    for run in formal_runs:
        verdict = verdicts.get(run.run_id)
        formal_records.append(
            {
                "run_id": str(run.run_id),
                "display_id": run.display_id,
                "axes": {
                    "execution_status": run.execution_status,
                    "validity_status": run.validity_status,
                    "business_verdict": run.business_verdict,
                    "evidence_status": run.evidence_status,
                    "verification_status": run.verification_status,
                },
                "decision": verdict.decision if verdict else "NOT_EVALUATED",
                "failure_class": verdict.failure_class if verdict else None,
                "formal_pass": verdict.formal_pass if verdict else False,
            }
        )
    blockers = [
        record
        for record in releases
        if record["release_state"]
        in {"held", "held_pending_cleanup", "held_pending_reconciliation", "quarantined"}
    ]
    unresolved = [
        {
            "code": "release_not_confirmed",
            "run_id": record["run_id"],
            "missing": record["missing"],
            "blocking": False,
        }
        for record in releases
        if record["release_state"] != "released"
        and record["release_state"] != "not_applicable"
    ]
    for run in formal_runs:
        verdict = verdicts.get(run.run_id)
        if verdict is not None and verdict.decision == "NEEDS_REVIEW":
            unresolved.append(
                {
                    "code": "verdict_needs_review",
                    "run_id": str(run.run_id),
                    "blocking": True,
                }
            )
    human_notes = [item for item in evidence if item.evidence_class == "human_note"]
    return [
        section(
            "summary",
            "MIXED",
            [
                {
                    "task_id": str(task.task_id),
                    "display_id": task.display_id,
                    "title": task.title,
                    "revision_id": str(revision.revision_id) if revision else None,
                    "revision_number": revision.revision_number if revision else None,
                    "contract_version": "1.0",
                    "environment": "control-plane",
                    "disclosure": disclosure,
                    "conclusion": "见 formal_records 与 metrics；本报告不单独声明正式 PASS",
                }
            ],
        ),
        section(
            "automated_checks",
            "AUTOMATED_CHECK",
            [
                {
                    "run_id": str(run.run_id),
                    "display_id": run.display_id,
                    "verification_status": run.verification_status,
                }
                for run in static_runs
            ],
        ),
        section(
            "smoke",
            "SMOKE",
            [
                {
                    "run_id": str(run.run_id),
                    "display_id": run.display_id,
                    "formal_denominator_excluded": True,
                }
                for run in smoke_runs
            ],
            empty="NOT_APPLICABLE",
        ),
        section("formal_records", "FORMAL", formal_records),
        section(
            "human_supplements",
            "HUMAN_SUPPLEMENT",
            [
                {
                    "evidence_id": str(item.evidence_id),
                    "display_id": item.display_id,
                    "non_automatic": True,
                }
                for item in human_notes
            ],
        ),
        section("deviations", "MIXED", []),
        section(
            "completion_assessment",
            "MIXED",
            [
                {
                    "formal_run_count": len(formal_runs),
                    "smoke_run_count": len(smoke_runs),
                    "static_run_count": len(static_runs),
                }
            ],
        ),
        section("blockers", "MIXED", blockers),
        section(
            "metrics",
            "MIXED",
            [
                {
                    "formal_denominator": (
                        int((revision.frozen_scope or {}).get("sample_count", 0))
                        if revision
                        else 0
                    ),
                    "formal_run_count": len(formal_runs),
                    "manifests": [
                        {
                            "manifest_id": str(manifest.manifest_id),
                            "denominators": dict(manifest.denominators or {}),
                        }
                        for manifest in manifests
                    ],
                }
            ],
        ),
        section("residual_risks", "MIXED", []),
        section(
            "deliverables_reusable_assets",
            "MIXED",
            [*knowledge_items, *candidates],
        ),
        section("lessons_learned", "MIXED", []),
        section(
            "evidence_index",
            "MIXED",
            [
                {
                    "evidence_id": str(item.evidence_id),
                    "display_id": item.display_id,
                    "content_digest": item.content_digest,
                    "size_bytes": item.size_bytes,
                    "access_level": item.access_level,
                    "verified": item.verified,
                }
                for item in evidence
            ],
        ),
        section("unresolved_items", "MIXED", unresolved),
    ]


__all__ = ["build_sections", "collect_inputs"]
