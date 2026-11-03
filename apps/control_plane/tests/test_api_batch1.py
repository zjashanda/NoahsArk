"""W2 batch 1 read-only API tests.

These tests require the seeded PostgreSQL database, exactly like the W1 seed
tests.  They skip (never fall back to SQLite) when no database is configured or
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
from noahsark.seed import TASK_DISPLAY, seed_database, stable_uuid

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping W2 API tests",
)

client = TestClient(app)
TASK_PATH = f"/api/v1/tasks/{TASK_DISPLAY}"

# W3 is the only wave allowed to add write methods.  These four POST routes are
# asserted exactly; any additional non-GET /api/v1 operation fails the test.
W3_WRITE_OPERATIONS = {
    ("/api/v1/intake/drafts", "post"),
    ("/api/v1/tasks", "post"),
    ("/api/v1/tasks/{task_id}/approvals", "post"),
    ("/api/v1/runs/{run_id}/stop-requests", "post"),
    ("/api/v1/devices/{device_id}/release-requests", "post"),
    # B2 development session surface (explicitly not production auth).
    ("/api/v1/auth/dev-login", "post"),
    ("/api/v1/auth/logout", "post"),
    # W4 write surface: verdict derivation, reports and knowledge promotion.
    ("/api/v1/runs/{run_id}/verdicts", "post"),
    ("/api/v1/tasks/{task_id}/reports", "post"),
    ("/api/v1/reports/{report_id}/freeze", "post"),
    ("/api/v1/knowledge/candidates/{candidate_id}/promotions", "post"),
    # Node/device topology management (ADMIN-only CRUD).
    ("/api/v1/nodes", "post"),
    ("/api/v1/nodes/{node_id}", "patch"),
    ("/api/v1/nodes/{node_id}", "delete"),
    ("/api/v1/devices", "post"),
    ("/api/v1/devices/{device_id}", "patch"),
    ("/api/v1/devices/{device_id}", "delete"),
}

W3_WRITE_PATHS = {path for path, _method in W3_WRITE_OPERATIONS}

# The intake and task collections are both UI read routes and write targets.
# The other write templates are write-only and must never expose GET.
W3_READ_WRITE_PATHS = {
    "/api/v1/intake/drafts",
    "/api/v1/tasks",
    "/api/v1/devices",
    "/api/v1/devices/{device_id}",
    "/api/v1/nodes/{node_id}",
}

TASK_ENDPOINTS = [
    "/api/v1/tasks",
    TASK_PATH,
    f"{TASK_PATH}/overview",
    f"{TASK_PATH}/revisions",
    f"{TASK_PATH}/plan",
    f"{TASK_PATH}/runs",
    f"{TASK_PATH}/evidence",
    f"{TASK_PATH}/verdict",
    f"{TASK_PATH}/live",
    f"{TASK_PATH}/knowledge",
]

BATCH1_ENDPOINTS = [
    "/api/v1/mission",
    "/api/v1/intake/drafts",
    "/api/v1/intake/drafts/drf-009",
    *TASK_ENDPOINTS,
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


def test_all_batch1_endpoints_return_200(seeded_database):
    for path in BATCH1_ENDPOINTS:
        response = client.get(path)
        assert response.status_code == 200, f"{path}: {response.text}"
        body = response.json()
        assert "data" in body, path
        assert body["meta"]["server_authoritative"] is True, path


def test_task_lookup_accepts_display_id_and_uuid(seeded_database):
    by_display = client.get(f"/api/v1/tasks/{TASK_DISPLAY}")
    by_uuid = client.get(f"/api/v1/tasks/{stable_uuid('task:' + TASK_DISPLAY)}")

    assert by_display.status_code == 200
    assert by_uuid.status_code == 200
    assert by_display.json()["data"]["display_id"] == TASK_DISPLAY
    assert by_uuid.json()["data"]["display_id"] == TASK_DISPLAY
    assert by_uuid.json()["data"]["task_id"] == str(stable_uuid("task:" + TASK_DISPLAY))


def test_axes_release_evidence_and_progress_are_separate(seeded_database):
    body = client.get(f"{TASK_PATH}/overview").json()["data"]

    assert set(body["axes"]) == {
        "execution_status",
        "validity_status",
        "business_verdict",
        "evidence_status",
        "verification_status",
    }
    assert body["release_state"] == "held"
    assert body["release"]["preconditions"] == {
        "local_stop_confirmed": True,
        "safe_cleanup_done": False,
        "occupancy_reconciled": False,
    }
    counts = body["evidence_counts"]
    assert counts["expected"] == 5
    assert counts["received"] == 4
    assert counts["verified"] == 3
    progress = body["progress"]
    assert progress["mode"] == "COUNTS"
    assert progress["total"] > 0
    assert isinstance(progress["percent"], (int, float))


def test_evidence_endpoint_returns_ledger_and_counts(seeded_database):
    body = client.get(f"{TASK_PATH}/evidence").json()["data"]
    assert len(body["items"]) == 5
    assert body["counts"]["expected"] == 5
    assert body["counts"]["verified"] == 3
    assert all(
        {"expected", "received", "verified"} <= set(item) for item in body["items"]
    )


def test_verdict_endpoint_is_200_without_seeded_verdict(seeded_database):
    body = client.get(f"{TASK_PATH}/verdict").json()["data"]
    assert body["available"] is False
    assert body["decision"] == "NOT_EVALUATED"
    assert body["formal_pass"] is False
    assert body["release_state"] == "held"


def test_observer_role_can_read(seeded_database):
    response = client.get(
        f"{TASK_PATH}/overview", headers={"X-NoahsArk-Role": "OBSERVER"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["display_id"] == TASK_DISPLAY


def test_unknown_role_is_forbidden(seeded_database):
    response = client.get(
        "/api/v1/tasks", headers={"X-NoahsArk-Role": "NOT_A_ROLE"}
    )
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert body["error"]["retryable"] is False


def test_unknown_task_returns_enveloped_404(seeded_database):
    response = client.get("/api/v1/tasks/tsk-does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_lists_support_limit_and_cursor(seeded_database):
    first = client.get("/api/v1/tasks", params={"limit": 1}).json()["data"]
    assert len(first["items"]) == 1
    assert first["next_cursor"] is not None

    second = client.get(
        "/api/v1/tasks",
        params={"limit": 1, "cursor": first["next_cursor"]},
    ).json()["data"]
    assert len(second["items"]) == 1
    assert second["items"][0]["task_id"] != first["items"][0]["task_id"]


def test_batch1_exposes_no_write_endpoints(seeded_database):
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
                allowed = {
                    method
                    for template, method in W3_WRITE_OPERATIONS
                    if template == path
                }
                if path in W3_READ_WRITE_PATHS:
                    allowed.add("get")
            else:
                allowed = {"get"}
            assert set(operations) == allowed, f"{path} exposes {set(operations)}"

    missing_key = client.post("/api/v1/tasks", json={})
    assert missing_key.status_code == 400
    assert missing_key.json()["error"]["code"] == "IDEMPOTENCY_REQUIRED"
