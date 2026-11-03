"""Epoch fencing and facts-only receipt shape."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from noahsark_node.protocol import (
    FORBIDDEN_FACT_KEYS,
    OUTCOME_KEYS,
    FactsOnlyViolation,
    JobMessage,
    LeaseTracker,
    assert_facts_only,
    assert_node_observed_outcome,
    build_node_observed_outcome,
    build_receipt,
    deterministic_id,
)

NODE_ID = "00000000-0000-4000-8000-000000000001"


def _job(*, epoch: int = 1, lease_id: str | None = None) -> JobMessage:
    return JobMessage(
        job_id=str(uuid4()),
        lease_id=lease_id or str(uuid4()),
        epoch=epoch,
        attempt=1,
        run_id=None,
        artifacts=(),
        artifact_contents={},
    )


def _outcome() -> dict[str, object]:
    return build_node_observed_outcome(
        execution_status="COMPLETED",
        validity_status="VALID",
        business_verdict="NOT_EVALUATED",
        evidence_status="UNVERIFIED",
    )


def test_lease_tracker_rejects_stale_epoch() -> None:
    tracker = LeaseTracker(lease_id="lease-a", epoch=5)

    assert tracker.observe("lease-b", 4) is False
    assert tracker.matches("lease-a", 5)
    assert tracker.epoch == 5


def test_lease_tracker_rejects_second_lease_at_same_epoch() -> None:
    tracker = LeaseTracker()
    assert tracker.observe("lease-a", 5) is True

    assert tracker.observe("lease-b", 5) is False
    assert tracker.matches("lease-a", 5)


def test_lease_tracker_accepts_newer_epoch_and_round_trips() -> None:
    tracker = LeaseTracker()
    assert tracker.observe("lease-a", 5, "job-a") is True
    assert tracker.observe("lease-b", 6, "job-b") is True
    restored = LeaseTracker.from_dict(tracker.to_dict())

    assert restored.matches("lease-b", 6)
    assert restored.job_id == "job-b"


def test_receipt_outcome_contains_only_node_observed_fields() -> None:
    job = _job()
    receipt = build_receipt(
        node_id=NODE_ID,
        job=job,
        status="completed",
        outcome=_outcome(),
        facts={"source": "simulator", "executed_on_device": False},
        started_at="2026-10-30T00:00:00Z",
        finished_at="2026-10-30T00:00:01Z",
        duration_ms=1000,
        node_boot_id=str(uuid4()),
    )

    outcome = receipt["payload"]["outcome"]  # type: ignore[index]
    assert set(outcome) == OUTCOME_KEYS
    assert outcome["used_for_decision"] is False
    assert outcome["node_observed_verification_status"] == "NOT_RUN"
    assert_facts_only(receipt)
    assert FORBIDDEN_FACT_KEYS.isdisjoint(outcome)


def test_receipt_rejects_platform_fields_in_facts() -> None:
    with pytest.raises(FactsOnlyViolation):
        build_receipt(
            node_id=NODE_ID,
            job=_job(),
            status="completed",
            outcome=_outcome(),
            facts={"business_verdict": "PASS"},
            started_at="2026-10-30T00:00:00Z",
            finished_at="2026-10-30T00:00:01Z",
            duration_ms=1,
        )


def test_receipt_rejects_outcome_that_claims_a_decision() -> None:
    outcome = _outcome()
    outcome["used_for_decision"] = True

    with pytest.raises(FactsOnlyViolation):
        build_receipt(
            node_id=NODE_ID,
            job=_job(),
            status="completed",
            outcome=outcome,
            facts={},
            started_at="2026-10-30T00:00:00Z",
            finished_at="2026-10-30T00:00:01Z",
            duration_ms=1,
        )


def test_receipt_rejects_extra_outcome_key() -> None:
    outcome = _outcome()
    outcome["business_verdict"] = "PASS"
    with pytest.raises(FactsOnlyViolation):
        assert_node_observed_outcome(outcome)


def test_receipt_boot_id_defaults_to_uuid_and_rejects_non_uuid() -> None:
    first = build_receipt(
        node_id=NODE_ID,
        job=_job(),
        status="completed",
        outcome=_outcome(),
        facts={},
        started_at="2026-10-30T00:00:00Z",
        finished_at=None,
        duration_ms=0,
    )
    UUID(str(first["payload"]["node_boot_id"]))  # type: ignore[index]

    with pytest.raises(ValueError):
        build_receipt(
            node_id=NODE_ID,
            job=_job(),
            status="completed",
            outcome=_outcome(),
            facts={},
            started_at="2026-10-30T00:00:00Z",
            finished_at=None,
            duration_ms=0,
            node_boot_id="dev-boot",
        )


def test_deterministic_ids_are_stable_for_replay() -> None:
    job = _job()
    first = build_receipt(
        node_id=NODE_ID,
        job=job,
        status="completed",
        outcome=_outcome(),
        facts={},
        started_at="2026-10-30T00:00:00Z",
        finished_at=None,
        duration_ms=0,
        receipt_id=deterministic_id("job_receipt", job.job_id),
        message_id=deterministic_id("job_message", job.job_id),
    )
    second = build_receipt(
        node_id=NODE_ID,
        job=job,
        status="completed",
        outcome=_outcome(),
        facts={},
        started_at="2026-10-30T00:00:00Z",
        finished_at=None,
        duration_ms=0,
        receipt_id=deterministic_id("job_receipt", job.job_id),
        message_id=deterministic_id("job_message", job.job_id),
    )

    assert first["payload"]["receipt_id"] == second["payload"]["receipt_id"]  # type: ignore[index]
    assert first["message_id"] == second["message_id"]
