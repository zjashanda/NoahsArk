"""W2 batch 2 read-only API tests.

These tests require the seeded PostgreSQL database, exactly like the batch-1
suite.  They skip (never fall back to SQLite) when no database is configured or
reachable.
"""

from __future__ import annotations

import asyncio
import os

import asyncpg
import pytest
from fastapi.testclient import TestClient

from noahsark.config import settings
from noahsark.main import app
from noahsark.seed import seed_database, stable_uuid

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping W2 API tests",
)

client = TestClient(app)

# W3 is the only wave allowed to add write methods.  These four POST routes are
# asserted exactly; any additional non-GET /api/v1 operation fails the test.
W3_WRITE_OPERATIONS = {
    ("/api/v1/intake/drafts", "post"),
    ("/api/v1/tasks/{task_id}/approvals", "post"),
    ("/api/v1/runs/{run_id}/stop-requests", "post"),
    ("/api/v1/devices/{device_id}/release-requests", "post"),
}

W3_WRITE_PATHS = {path for path, _method in W3_WRITE_OPERATIONS}

# Only the intake collection is both a UI read route and a W3 write target.
# The other three templates are write-only and must never expose GET.
W3_READ_WRITE_PATHS = {"/api/v1/intake/drafts"}

BATCH2_ENDPOINTS = [
    "/api/v1/runs",
    "/api/v1/runs/run-042",
    "/api/v1/runs/run-042/attempts/att-112",
    "/api/v1/evidence",
    "/api/v1/evidence/ev-voice-trace-01",
    "/api/v1/verdicts",
    "/api/v1/devices",
    "/api/v1/devices/dev-tcl-001",
    "/api/v1/nodes/node-lab-win-01",
    "/api/v1/reports",
    "/api/v1/reports/rpt-voice-001",
]


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
    asyncio.run(seed_database(reset=False))
    return True


def test_all_batch2_endpoints_return_200(seeded_database):
    for path in BATCH2_ENDPOINTS:
        response = client.get(path)
        assert response.status_code == 200, f"{path}: {response.text}"
        body = response.json()
        assert "data" in body, path
        assert body["meta"]["server_authoritative"] is True, path


def test_runs_lookup_accepts_display_id_and_uuid(seeded_database):
    for path, uuid_key, display in [
        ("/api/v1/runs/run-042", "run:run-042", "run-042"),
        (
            "/api/v1/runs/run-042/attempts/att-112",
            "attempt:att-112",
            "att-112",
        ),
    ]:
        by_display = client.get(path)
        by_uuid = client.get(path.replace(display, str(stable_uuid(uuid_key))))
        assert by_display.status_code == 200, by_display.text
        assert by_uuid.status_code == 200, by_uuid.text
        assert by_display.json()["data"]["display_id"] == display
        assert by_uuid.json()["data"]["display_id"] == display


def test_evidence_device_node_report_lookup_accepts_display_id_and_uuid(
    seeded_database,
):
    cases = [
        ("/api/v1/evidence", "evidence:ev-voice-trace-01", "ev-voice-trace-01"),
        ("/api/v1/devices", "device:dev-tcl-001", "dev-tcl-001"),
        ("/api/v1/nodes", "node:node-lab-win-01", "node-lab-win-01"),
        ("/api/v1/reports", "report:rpt-voice-001", "rpt-voice-001"),
    ]
    for base, uuid_key, display in cases:
        by_display = client.get(f"{base}/{display}")
        by_uuid = client.get(f"{base}/{stable_uuid(uuid_key)}")
        assert by_display.status_code == 200, by_display.text
        assert by_uuid.status_code == 200, by_uuid.text
        assert by_display.json()["data"]["display_id"] == display
        assert by_uuid.json()["data"]["display_id"] == display


def test_run_detail_keeps_axes_signals_and_release_separate(seeded_database):
    body = client.get("/api/v1/runs/run-042").json()["data"]

    assert set(body["axes"]) == {
        "execution_status",
        "validity_status",
        "business_verdict",
        "evidence_status",
        "verification_status",
    }
    assert body["communication_state"] == "ONLINE"
    assert body["occupancy_state"] == "OCCUPIED"
    assert body["execution_permit"] == "GRANTED"
    assert body["execution_status"] == "RUNNING"
    assert body["business_verdict"] == "NOT_EVALUATED"

    freshness = body["freshness"]
    assert freshness["is_stale"] is False
    assert freshness["communication_state"] == "ONLINE"
    assert freshness["last_authoritative_update"] is not None

    assert body["release_state"] == "held"
    assert body["release"]["preconditions"] == {
        "local_stop_confirmed": True,
        "safe_cleanup_done": False,
        "occupancy_reconciled": False,
    }
    assert body["release"]["preconditions_met"] is False
    assert body["release"]["independent_of_verdict"] is True
    assert body["pass_implies_release"] is False

    assert body["attempt_count"] == 2
    assert {attempt["display_id"] for attempt in body["attempts"]} == {
        "att-112",
        "att-111",
    }
    for attempt in body["attempts"]:
        assert set(attempt["axes"]) == set(body["axes"])


def test_attempt_detail_is_scoped_to_its_run(seeded_database):
    body = client.get("/api/v1/runs/run-042/attempts/att-112").json()["data"]
    assert body["display_id"] == "att-112"
    assert body["run"]["display_id"] == "run-042"
    assert body["execution_status"] == "RUNNING"
    assert body["release_state"] == "held"
    assert body["signals"]["communication_state"] == "ONLINE"
    assert body["signals"]["occupancy_state"] == "OCCUPIED"
    assert body["signals"]["execution_permit"] == "GRANTED"
    assert body["signals"]["execution_status"] == "RUNNING"

    mismatched = client.get("/api/v1/runs/run-039/attempts/att-112")
    assert mismatched.status_code == 404
    assert mismatched.json()["error"]["code"] == "NOT_FOUND"


def test_evidence_counts_and_status_are_not_collapsed(seeded_database):
    listing = client.get("/api/v1/evidence").json()["data"]
    assert listing["total"] == 5
    assert len(listing["items"]) == 5
    counts = listing["counts"]
    assert counts["expected"] == 5
    assert counts["received"] == 4
    assert counts["verified"] == 3
    assert counts["missing"] == 1
    assert counts["pending_verification"] == 1
    assert listing["evidence_status"] in {
        "COMPLETE",
        "INCOMPLETE",
        "CONFLICTED",
        "UNVERIFIED",
    }
    assert listing["evidence_status"] == "INCOMPLETE"
    for item in listing["items"]:
        assert {"expected", "received", "verified"} <= set(item)
        assert item["evidence_status"] in {
            "COMPLETE",
            "INCOMPLETE",
            "CONFLICTED",
            "UNVERIFIED",
        }
        if item["received"] and not item["verified"]:
            assert item["evidence_status"] == "UNVERIFIED"

    detail = client.get("/api/v1/evidence/ev-voice-trace-01").json()["data"]
    assert detail["display_id"] == "ev-voice-trace-01"
    assert detail["expected"] is True
    assert detail["received"] is True
    assert detail["verified"] is True
    assert detail["item_evidence_status"] == "COMPLETE"
    assert detail["evidence_status"] == "INCOMPLETE"
    assert detail["counts"]["verified"] == 3
    assert detail["run"]["display_id"] == "run-042"


def test_verdicts_list_is_200_and_unavailable_when_unseeded(seeded_database):
    body = client.get("/api/v1/verdicts").json()["data"]
    assert body["available"] is False
    assert body["total"] == 0
    assert body["items"] == []


def test_device_detail_keeps_signals_and_release_separate(seeded_database):
    listing = client.get("/api/v1/devices").json()["data"]
    assert listing["total"] == 4
    assert {item["display_id"] for item in listing["items"]} == {
        "dev-tcl-001",
        "dev-tcl-002",
        "dev-tcl-003",
        "dev-tcl-004",
    }
    for item in listing["items"]:
        assert {"communication_state", "occupancy_state"} <= set(item)
        assert "freshness" in item
        assert "release_state" in item

    body = client.get("/api/v1/devices/dev-tcl-001").json()["data"]
    assert body["display_id"] == "dev-tcl-001"
    assert body["node"]["display_id"] == "node-lab-win-01"
    assert body["current_lease"]["display_id"] == "lease-7781"
    assert body["signals"]["communication_state"] == "ONLINE"
    assert body["signals"]["occupancy_state"] == "OCCUPIED"
    assert body["signals"]["execution_permit"] == "GRANTED"
    assert body["signals"]["execution_status"] == "RUNNING"
    assert body["freshness"]["is_stale"] is False
    assert body["release_state"] == "held"
    assert body["release"]["preconditions"] == {
        "local_stop_confirmed": True,
        "safe_cleanup_done": False,
        "occupancy_reconciled": False,
    }
    assert body["release"]["independent_of_verdict"] is True
    assert body["pass_implies_release"] is False


def test_node_detail_lists_devices_and_leases_separately(seeded_database):
    body = client.get("/api/v1/nodes/node-lab-win-01").json()["data"]
    assert body["display_id"] == "node-lab-win-01"
    assert body["communication_state"] == "ONLINE"
    assert body["summary"]["device_count"] == 3
    assert body["summary"]["lease_count"] == 2
    assert len(body["devices"]) == 3
    assert len(body["leases"]) == 2
    assert body["signals"]["communication_state"] == "ONLINE"
    assert "freshness" in body["signals"]


def test_report_detail_separates_version_denominator_records_and_disclosure(
    seeded_database,
):
    listing = client.get("/api/v1/reports").json()["data"]
    assert listing["total"] == 2
    assert {item["display_id"] for item in listing["items"]} == {
        "rpt-voice-001",
        "rpt-static-004",
    }

    body = client.get("/api/v1/reports/rpt-voice-001").json()["data"]
    assert body["display_id"] == "rpt-voice-001"
    assert body["version"] == 3
    assert body["lifecycle"] == "FROZEN"
    assert body["frozen"] is True
    assert body["denominator"] == 40
    assert body["denominator_statement"]["formal_denominator"] == 40
    assert body["denominator_statement"]["smoke_excluded"] is True
    assert body["disclosure"] == "INTERNAL"
    assert body["sections"] == 14

    separation = body["record_separation"]
    assert separation["independent"] is True
    assert len(separation["run_records"]) == 1
    assert len(separation["evidence_records"]) == 5
    assert len(separation["release_records"]) == 1
    assert len(separation["unresolved_records"]) == 1

    assert body["release_state"] == "held"
    assert body["release"]["preconditions_met"] is False
    assert body["release"]["independent_of_verdict"] is True
    assert body["release_confirmed"] is False
    assert body["runs"][0]["decision"] == "NOT_EVALUATED"


def test_observer_role_can_read_batch2(seeded_database):
    for path in BATCH2_ENDPOINTS:
        response = client.get(path, headers={"X-NoahsArk-Role": "OBSERVER"})
        assert response.status_code == 200, f"{path}: {response.text}"


def test_unknown_role_is_forbidden_on_batch2(seeded_database):
    for path in ("/api/v1/runs", "/api/v1/evidence", "/api/v1/devices"):
        response = client.get(path, headers={"X-NoahsArk-Role": "NOT_A_ROLE"})
        assert response.status_code == 403, path
        body = response.json()
        assert body["error"]["code"] == "FORBIDDEN"
        assert body["error"]["retryable"] is False


def test_unknown_batch2_identifiers_return_enveloped_404(seeded_database):
    for path in (
        "/api/v1/runs/run-does-not-exist",
        "/api/v1/evidence/ev-does-not-exist",
        "/api/v1/devices/dev-does-not-exist",
        "/api/v1/nodes/node-does-not-exist",
        "/api/v1/reports/rpt-does-not-exist",
    ):
        response = client.get(path)
        assert response.status_code == 404, path
        assert response.json()["error"]["code"] == "NOT_FOUND"


def test_batch2_lists_support_limit_and_cursor(seeded_database):
    for base in ("/api/v1/runs", "/api/v1/evidence", "/api/v1/devices"):
        first = client.get(base, params={"limit": 1}).json()["data"]
        assert len(first["items"]) == 1, base
        assert first["next_cursor"] is not None, base

        second = client.get(
            base, params={"limit": 1, "cursor": first["next_cursor"]}
        ).json()["data"]
        assert len(second["items"]) == 1, base
        assert second["items"][0] != first["items"][0], base


def test_batch2_exposes_no_write_endpoints(seeded_database):
    schema = client.get("/openapi.json").json()
    post_paths = set()
    for path, operations in schema["paths"].items():
        if path.startswith("/api/v1"):
            for method in operations:
                if method != "get":
                    post_paths.add((path, method))
    assert post_paths == W3_WRITE_OPERATIONS

    for path, operations in schema["paths"].items():
        if path.startswith("/api/v1"):
            if path in W3_WRITE_PATHS:
                allowed = {"post"}
                if path in W3_READ_WRITE_PATHS:
                    allowed.add("get")
            else:
                allowed = {"get"}
            assert set(operations) == allowed, f"{path} exposes {set(operations)}"

    for path in (
        "/api/v1/runs",
        "/api/v1/evidence",
        "/api/v1/devices",
        "/api/v1/reports",
    ):
        assert client.post(path).status_code in {404, 405}, path
