"""P5-W4 tests: five-axis verdicts, 14-section reports, knowledge promotion.

The pure verdict tests prove the fail-closed formal PASS gate.  The API tests
run against the seeded PostgreSQL authority and prove that an incomplete
evidence chain cannot become PASS, reports are versioned/frozen and knowledge is
never promoted without an explicit human review transition.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import replace
from types import SimpleNamespace

import asyncpg
import pytest
from fastapi.testclient import TestClient

from noahsark.config import settings
from noahsark.domain.verdict_rules import (
    FORMAL_PASS_PRECONDITIONS,
    VerdictFacts,
    derive_verdict,
)
from noahsark.main import app
from noahsark.seed import seed_database
from noahsark.services.verdict_facts import evidence_facts, lease_fence_valid

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping W4 API tests",
)

client = TestClient(app)
GOOD = VerdictFacts(
    mode="formal",
    execution_status="COMPLETED",
    validity_status="VALID",
    business_verdict="PASS",
    evidence_status="COMPLETE",
    verification_status="PASS",
    approval_valid=True,
    boundary_frozen=True,
    required_evidence_complete=True,
    digest_verified=True,
    no_blocking_anomaly=True,
    denominator_eligible=True,
)


def _dsn() -> str:
    assert DATABASE_URL
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _ping() -> None:
    connection = await asyncpg.connect(_dsn())
    try:
        await connection.fetch("SELECT 1")
    finally:
        await connection.close()


@pytest.fixture(scope="module")
def seeded_database():
    try:
        asyncio.run(_ping())
    except (OSError, asyncpg.PostgresError) as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")
    asyncio.run(seed_database(reset=True))
    return True


def _headers(role: str = "ADMIN", actor: str | None = "admin-01") -> dict[str, str]:
    headers = {"X-NoahsArk-Role": role, "Idempotency-Key": f"w4-{uuid.uuid4().hex}"}
    if actor is not None:
        headers["X-NoahsArk-Actor"] = actor
    return headers


# ---------------------------------------------------------------------------
# Pure verdict derivation
# ---------------------------------------------------------------------------
def test_formal_pass_requires_all_eleven_preconditions() -> None:
    result = derive_verdict(GOOD)
    assert result["decision"] == "PASS"
    assert result["formal_pass"] is True
    assert set(result["pass_preconditions"]) == set(FORMAL_PASS_PRECONDITIONS)
    assert len(FORMAL_PASS_PRECONDITIONS) == 11
    assert all(result["pass_preconditions"].values())
    assert result["denominator"]["eligible"] is True

    failures = {
        "approval_valid": replace(GOOD, approval_valid=False),
        "boundary_frozen": replace(GOOD, boundary_frozen=False),
        "mode_formal": replace(GOOD, mode="smoke"),
        "execution_completed": replace(GOOD, execution_status="RUNNING"),
        "sample_valid": replace(GOOD, validity_status="INVALID"),
        "business_pass": replace(GOOD, business_verdict="FAIL"),
        "required_evidence_complete": replace(
            GOOD, required_evidence_complete=False
        ),
        "digest_verified": replace(GOOD, digest_verified=False),
        "linux_review_pass": replace(GOOD, verification_status="NOT_RUN"),
        "no_blocking_anomaly": replace(GOOD, no_blocking_anomaly=False),
        "denominator_eligible": replace(GOOD, denominator_eligible=False),
    }
    assert set(failures) == set(FORMAL_PASS_PRECONDITIONS)
    for name, facts in failures.items():
        derived = derive_verdict(facts)
        assert derived["decision"] != "PASS", name
        assert derived["formal_pass"] is False, name
        assert derived["pass_preconditions"][name] is False, name


def test_smoke_pass_is_mode_outcome_only() -> None:
    smoke = replace(GOOD, mode="smoke")
    result = derive_verdict(smoke)
    assert result["decision"] == "NOT_APPLICABLE"
    assert result["mode_outcome"] == "PASS"
    assert result["formal_pass"] is False
    assert result["denominator"]["formal_denominator"] is False


def test_manifest_counts_must_be_backed_by_evidence_rows() -> None:
    manifest = SimpleNamespace(
        required_evidence={"required_total": 2, "required_verified": 2},
        completeness={},
        anomalies={},
    )
    one_verified = [
        SimpleNamespace(expected=True, verified=True, content_digest="sha256:a")
    ]
    required, digest, no_blocking = evidence_facts(manifest, one_verified)
    assert required is False
    assert digest is False
    assert no_blocking is True

    two_verified = [
        *one_verified,
        SimpleNamespace(expected=True, verified=True, content_digest="sha256:b"),
    ]
    required, digest, no_blocking = evidence_facts(manifest, two_verified)
    assert required is True
    assert digest is True
    assert no_blocking is True


def test_lease_fence_mismatch_blocks_pass_even_with_all_eleven_preconditions() -> None:
    result = derive_verdict(replace(GOOD, lease_fence_valid=False))
    assert result["decision"] == "BLOCKED"
    assert result["failure_class"] == "blocked"
    assert result["formal_pass"] is False
    assert result["denominator"]["eligible"] is False
    # The 11 contract prerequisites can all be true while the run's lease
    # fencing token is stale; the fence still keeps it out of PASS.
    assert all(result["pass_preconditions"].values())


def test_lease_fence_requires_matching_run_lease_and_epoch() -> None:
    run = SimpleNamespace(
        mode="formal", lease_id=uuid.uuid4(), lease_epoch=7, run_id=uuid.uuid4()
    )
    matching = SimpleNamespace(lease_id=run.lease_id, epoch=7, run_id=run.run_id)
    assert lease_fence_valid(run, matching) is True
    assert lease_fence_valid(run, None) is False
    assert (
        lease_fence_valid(
            run, SimpleNamespace(lease_id=run.lease_id, epoch=6, run_id=run.run_id)
        )
        is False
    )
    assert (
        lease_fence_valid(
            run,
            SimpleNamespace(lease_id=uuid.uuid4(), epoch=7, run_id=run.run_id),
        )
        is False
    )
    static_run = SimpleNamespace(
        mode="static", lease_id=None, lease_epoch=None, run_id=run.run_id
    )
    assert lease_fence_valid(static_run, None) is True


def test_evidence_and_review_failures_are_fail_closed() -> None:
    incomplete = replace(
        GOOD,
        evidence_status="INCOMPLETE",
        required_evidence_complete=False,
        digest_verified=False,
    )
    result = derive_verdict(incomplete)
    assert result["decision"] == "BLOCKED"
    assert result["failure_class"] == "invalid-evidence"
    assert result["formal_pass"] is False

    unreviewed = replace(GOOD, verification_status="NOT_RUN")
    result = derive_verdict(unreviewed)
    assert result["decision"] == "NEEDS_REVIEW"
    assert result["failure_class"] == "needs-review"
    assert result["formal_pass"] is False


# ---------------------------------------------------------------------------
# Verdict API against seeded authority
# ---------------------------------------------------------------------------
def test_verdict_api_never_passes_an_incomplete_run(seeded_database) -> None:
    response = client.post("/api/v1/runs/run-031/verdicts", headers=_headers())
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["run_id"] == str(_uuid_or_none(data["run_id"]))
    assert data["decision"] != "PASS"
    assert data["formal_pass"] is False
    assert data["exact_formal_pass_axes"] is True
    assert set(data["pass_preconditions"]) == set(FORMAL_PASS_PRECONDITIONS)
    assert data["pass_preconditions"]["approval_valid"] is False
    assert data["pass_preconditions"]["required_evidence_complete"] is False
    assert data["pass_preconditions"]["digest_verified"] is False
    assert data["reasons"][0]["code"] == "APPROVAL_OR_BOUNDARY_INVALID"

    detail = client.get("/api/v1/tasks/tsk-voice-000/verdict").json()["data"]
    assert detail["available"] is True
    assert detail["formal_pass"] is False
    assert detail["decision"] != "PASS"

    replay = client.post("/api/v1/runs/run-031/verdicts", headers=_headers())
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "VERDICT_IMMUTABLE"

    forbidden = client.post("/api/v1/runs/run-039/verdicts", headers=_headers("OBSERVER"))
    assert forbidden.status_code == 403


def _uuid_or_none(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def test_reports_are_fourteen_sections_versioned_and_frozen(seeded_database) -> None:
    first = client.post(
        "/api/v1/tasks/tsk-voice-001/reports",
        headers=_headers(),
        json={"title": "W4 acceptance report", "disclosure": "INTERNAL"},
    )
    assert first.status_code == 201, first.text
    created = first.json()["data"]
    assert created["sections"] == 14
    assert len(created["categories"]) == 14

    report_id = created["display_id"]
    detail = client.get(f"/api/v1/reports/{report_id}").json()["data"]
    assert detail["version"] >= 4
    assert detail["sections"] == 14
    assert detail["lifecycle"] == "DRAFT"
    categories = [
        section["category"] for section in detail["content"]["sections"]
    ]
    assert categories == created["categories"]
    assert detail["record_separation"]["independent"] is True
    assert detail["denominator_statement"]["smoke_excluded"] is True

    frozen = client.post(
        f"/api/v1/reports/{report_id}/freeze", headers=_headers()
    )
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["data"]["lifecycle"] == "FROZEN"
    assert frozen.json()["data"]["frozen"] is True

    again = client.post(f"/api/v1/reports/{report_id}/freeze", headers=_headers())
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "REPORT_NOT_DRAFT"

    second = client.post(
        "/api/v1/tasks/tsk-voice-001/reports",
        headers=_headers(),
        json={"title": "W4 correction", "disclosure": "INTERNAL"},
    )
    assert second.status_code == 201, second.text
    assert second.json()["data"]["version"] == detail["version"] + 1

    denied = client.post(
        "/api/v1/tasks/tsk-voice-001/reports",
        headers=_headers("APPROVER"),
        json={"title": "Denied", "disclosure": "INTERNAL"},
    )
    assert denied.status_code == 403


# ---------------------------------------------------------------------------
# Knowledge promotion
# ---------------------------------------------------------------------------
def test_knowledge_candidate_cannot_be_promoted_without_review(seeded_database) -> None:
    body = {
        "target_library": "COMMON",
        "reason": "Reviewed against the frozen baseline and source evidence.",
        "similarity_check": {"checked": True, "candidates": ["kn-wake-false-trigger"]},
    }
    proposed = client.post(
        "/api/v1/knowledge/candidates/knc-014/promotions",
        headers=_headers(),
        json=body,
    )
    assert proposed.status_code == 409
    assert proposed.json()["error"]["code"] == "KNOWLEDGE_PROMOTION_FORBIDDEN"
    assert proposed.json()["error"]["details"]["reason"] == "REVIEW_NOT_COMPLETE"

    still = client.get("/api/v1/knowledge/candidates").json()["data"]["items"]
    status_by_id = {item["display_id"]: item["status"] for item in still}
    assert status_by_id["knc-014"] == "PROPOSED"

    approved = client.post(
        "/api/v1/knowledge/candidates/knc-006/promotions",
        headers=_headers(),
        json=body,
    )
    assert approved.status_code == 201, approved.text
    promoted = approved.json()["data"]
    assert promoted["status"] == "PROMOTED"
    assert promoted["automatic_promotion_allowed"] is False
    assert promoted["requires_human_review"] is True

    item = client.get(f"/api/v1/knowledge/{promoted['knowledge_display_id']}")
    assert item.status_code == 200, item.text
    assert item.json()["data"]["status"] == "APPROVED"

    replay = client.post(
        "/api/v1/knowledge/candidates/knc-006/promotions",
        headers=_headers(),
        json=body,
    )
    assert replay.status_code == 409

    denied = client.post(
        "/api/v1/knowledge/candidates/knc-012/promotions",
        headers=_headers("APPROVER"),
        json=body,
    )
    assert denied.status_code == 403


# ---------------------------------------------------------------------------
# TaskCard projection
# ---------------------------------------------------------------------------
def test_task_card_preserves_progress_and_freshness(seeded_database) -> None:
    body = client.get("/api/v1/tasks/tsk-voice-001/overview").json()["data"]
    card = body["task_card"]
    assert card["stage"] == "EXECUTING"
    assert card["run_state"] == "RUNNING"
    assert card["progress"]["mode"] == "COUNTS"
    assert isinstance(card["progress"]["percent"], (int, float))
    assert card["freshness"]["is_stale"] is False
    assert card["last_authoritative_update"] is not None
    assert card["resources"]["node_display_id"] == "node-lab-win-01"
    assert card["resources"]["device_display_id"] == "dev-tcl-001"

    unknown = client.get("/api/v1/tasks/tsk-voice-000/overview").json()["data"]
    unknown_card = unknown["task_card"]
    assert unknown_card["progress"]["mode"] == "INDETERMINATE"
    assert unknown_card["progress"]["percent"] is None
    assert unknown_card["progress"]["total"] == 0
    assert unknown_card["freshness"]["is_stale"] is False
