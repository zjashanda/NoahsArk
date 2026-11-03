"""Resolve authoritative facts for verdict derivation."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import not_found
from ..models import (
    Approval,
    Attempt,
    EvidenceItem,
    EvidenceManifest,
    Lease,
    Run,
    TaskRevision,
)


async def resolve_run(session: AsyncSession, identifier: str) -> Run:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("run", identifier)
    conditions = [Run.display_id == raw]
    try:
        conditions.append(Run.run_id == uuid.UUID(raw))
    except ValueError:
        pass
    run = (
        await session.execute(select(Run).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if run is None:
        raise not_found("run", identifier)
    return run


async def approved_approval(
    session: AsyncSession, revision_id: uuid.UUID
) -> Approval | None:
    return (
        await session.execute(
            select(Approval)
            .where(
                Approval.revision_id == revision_id,
                Approval.decision == "APPROVED",
            )
            .order_by(Approval.decided_at.desc().nullslast())
            .limit(1)
        )
    ).scalar_one_or_none()


async def manifest_for_run(
    session: AsyncSession, run: Run
) -> EvidenceManifest | None:
    if run.evidence_manifest_id is not None:
        manifest = await session.get(EvidenceManifest, run.evidence_manifest_id)
        if manifest is not None:
            return manifest
    return (
        await session.execute(
            select(EvidenceManifest)
            .where(EvidenceManifest.run_id == run.run_id)
            .order_by(EvidenceManifest.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def evidence_items(
    session: AsyncSession, run: Run, manifest: EvidenceManifest | None
) -> list[EvidenceItem]:
    conditions = [EvidenceItem.run_id == run.run_id]
    if manifest is not None and manifest.evidence_items:
        ids = []
        for value in manifest.evidence_items:
            try:
                ids.append(uuid.UUID(str(value)))
            except ValueError:
                continue
        if ids:
            conditions.append(EvidenceItem.evidence_id.in_(ids))
    return list(
        (
            await session.execute(select(EvidenceItem).where(or_(*conditions)))
        ).scalars().all()
    )


async def load_attempts(session: AsyncSession, run: Run) -> list[Attempt]:
    return list(
        (
            await session.execute(
                select(Attempt)
                .where(Attempt.run_id == run.run_id)
                .order_by(Attempt.attempt_ordinal)
            )
        ).scalars().all()
    )


async def load_lease(session: AsyncSession, run: Run) -> Lease | None:
    if run.lease_id is None:
        return None
    return await session.get(Lease, run.lease_id)


def lease_fence_valid(run: Run, lease: Lease | None) -> bool:
    """True only when the run and its lease share one live fencing token.

    Static runs have no node lease, so they are exempt.  Every device-backed
    mode is fail-closed: a missing lease, a missing epoch, a lease for another
    run or a stale/different epoch can never satisfy the derivation fence.
    """

    if run.mode == "static":
        return True
    if lease is None or run.lease_epoch is None:
        return False
    return (
        run.lease_id is not None
        and lease.lease_id == run.lease_id
        and lease.run_id == run.run_id
        and lease.epoch == run.lease_epoch
    )


def evidence_facts(
    manifest: EvidenceManifest | None, items: list[EvidenceItem]
) -> tuple[bool, bool, bool]:
    if manifest is None:
        return False, False, False
    required = dict(manifest.required_evidence or {})
    completeness = dict(manifest.completeness or {})
    required_total = int(required.get("required_total", 0) or 0)
    required_verified = int(required.get("required_verified", 0) or 0)
    missing = list(completeness.get("missing") or [])
    unverified = list(completeness.get("unverified") or [])
    conflicted = list(completeness.get("conflicted") or [])
    expected_items = [item for item in items if item.expected]
    verified_items = [
        item for item in expected_items if item.verified and item.content_digest
    ]
    # Manifest counters are claims; the rows must actually back them.  A
    # manifest that says "5 verified" while only 3 rows exist fails closed.
    required_complete = (
        required_total > 0
        and required_total == required_verified
        and len(expected_items) >= required_total
        and not missing
        and not unverified
        and not conflicted
    )
    digest_verified = required_complete and len(verified_items) >= required_total
    anomalies = dict(manifest.anomalies or {})
    blocking = list(anomalies.get("blocking_ids") or [])
    no_blocking = not blocking and not conflicted
    return required_complete, digest_verified, no_blocking


def approval_valid(approval: Approval | None, revision: TaskRevision) -> bool:
    if approval is None or approval.effective_at is None:
        return False
    if approval.revision_id != revision.revision_id:
        return False
    return approval.revision_content_digest == revision.content_digest


def boundary_frozen(
    revision: TaskRevision, manifest: EvidenceManifest | None
) -> bool:
    if revision.status not in {"FROZEN", "APPROVED"} or not revision.immutable:
        return False
    if manifest is None or manifest.revision_id != revision.revision_id:
        return False
    bundle = dict(manifest.bundle or {})
    bundle_id = bundle.get("bundle_id")
    if revision.bundle_id is None or bundle_id is None:
        return False
    return str(revision.bundle_id) == str(bundle_id)


__all__ = [
    "approval_valid",
    "approved_approval",
    "boundary_frozen",
    "evidence_facts",
    "evidence_items",
    "lease_fence_valid",
    "load_attempts",
    "load_lease",
    "manifest_for_run",
    "resolve_run",
]
