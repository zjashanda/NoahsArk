"""Static report vocabulary and small record projections."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..models import EvidenceItem, KnowledgeCandidate, KnowledgeItem, Lease, Node, Run
from .domain_rules import lease_release_projection

REPORT_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("summary", "MIXED"),
    ("automated_checks", "AUTOMATED_CHECK"),
    ("smoke", "SMOKE"),
    ("formal_records", "FORMAL"),
    ("human_supplements", "HUMAN_SUPPLEMENT"),
    ("deviations", "MIXED"),
    ("completion_assessment", "MIXED"),
    ("blockers", "MIXED"),
    ("metrics", "MIXED"),
    ("residual_risks", "MIXED"),
    ("deliverables_reusable_assets", "MIXED"),
    ("lessons_learned", "MIXED"),
    ("evidence_index", "MIXED"),
    ("unresolved_items", "MIXED"),
)
REPORT_CATEGORY_NAMES = tuple(name for name, _kind in REPORT_CATEGORIES)
DENOMINATOR_STATEMENT = (
    "formal_denominator = 有效正式样本；smoke/invalid/blocked/stopped/infra 不计入。"
)
DISCLOSURE_VALUES = frozenset({"INTERNAL", "RESTRICTED", "PUBLIC"})
DEFAULT_ACCESS = {
    "default_visibility": "summary_and_index",
    "raw_material_requires": "evidence_reader",
}


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def section(
    category: str, kind: str, items: list[Any], *, empty: str = "EMPTY"
) -> dict[str, Any]:
    if not items:
        return {
            "category": category,
            "record_kind": kind,
            "status": empty,
            "items": [],
        }
    return {
        "category": category,
        "record_kind": kind,
        "status": "PRESENT",
        "items": items,
    }


def release_record(
    lease: Lease | None, run: Run | None, node: Node | None
) -> dict[str, Any]:
    if lease is None:
        return {
            "run_id": str(run.run_id) if run is not None else None,
            "release_state": "not_applicable",
            "release_confirmed": False,
            "missing": [],
        }
    projection = lease_release_projection(lease, run=run, node=node)
    return {
        "run_id": str(run.run_id) if run is not None else None,
        "lease_id": str(lease.lease_id),
        "release_state": projection["release_state"],
        "release_confirmed": projection["release_confirmed"],
        "missing": list(projection["missing"]),
    }


def knowledge_records(
    runs: list[Run],
    evidence: list[EvidenceItem],
    knowledge: list[KnowledgeItem],
    candidates: list[KnowledgeCandidate],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    related = {run.display_id for run in runs} | {
        item.display_id for item in evidence
    }
    items = [
        {
            "knowledge_id": str(item.knowledge_id),
            "display_id": item.display_id,
            "status": item.status,
            "title": item.title,
        }
        for item in knowledge
        if related & set(item.source_chain or [])
    ]
    proposed = [
        {
            "candidate_id": str(item.candidate_id),
            "display_id": item.display_id,
            "status": item.status,
            "title": item.title,
            "requires_human_review": item.requires_human_review,
        }
        for item in candidates
        if related & set(item.source_chain or [])
    ]
    return items, proposed


__all__ = [
    "DEFAULT_ACCESS",
    "DENOMINATOR_STATEMENT",
    "DISCLOSURE_VALUES",
    "REPORT_CATEGORIES",
    "REPORT_CATEGORY_NAMES",
    "iso",
    "knowledge_records",
    "release_record",
    "section",
]
