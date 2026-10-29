"""W2 batch 3 read-only API tests.

Requires the seeded PostgreSQL database, like batch 1 and 2.  Skips (never
falls back to SQLite) when no PostgreSQL DATABASE_URL is configured or reachable.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

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

BATCH3_ENDPOINTS = [
    "/api/v1/knowledge",
    "/api/v1/knowledge/kn-wake-false-trigger",
    "/api/v1/knowledge/candidates",
    "/api/v1/runtime/models",
    "/api/v1/runtime/toolchain",
    "/api/v1/agents",
    "/api/v1/agents/agt-planner",
    "/api/v1/reviews",
    "/api/v1/audit",
    "/api/v1/audit/aud-20261029-041",
    "/api/v1/recovery",
    "/api/v1/settings",
    "/api/v1/settings/access",
    "/api/v1/settings/notifications",
    "/api/v1/settings/retention",
]

SECRET_MARKERS = (
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


def _walk(value: Any, path: str = "") -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.append((f"{path}.{key}".strip("."), key))
            found.extend(_walk(item, f"{path}.{key}".strip(".")))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk(item, f"{path}[{index}]"))
    return found


def _assert_no_secret_fields(payload: Any) -> None:
    for _, key in _walk(payload):
        if key == "secrets_exposed":
            continue
        lowered = str(key).lower()
        assert not any(
            marker in lowered for marker in SECRET_MARKERS
        ), f"secret-like field exposed: {key}"


def test_all_batch3_endpoints_return_200(seeded_database):
    for path in BATCH3_ENDPOINTS:
        response = client.get(path)
        assert response.status_code == 200, f"{path}: {response.text}"
        body = response.json()
        assert "data" in body, path
        assert body["meta"]["server_authoritative"] is True, path


def test_knowledge_lookup_accepts_display_id_and_uuid(seeded_database):
    display = "kn-wake-false-trigger"
    uuid_value = str(stable_uuid(f"knowledge:{display}"))
    by_display = client.get(f"/api/v1/knowledge/{display}")
    by_uuid = client.get(f"/api/v1/knowledge/{uuid_value}")
    assert by_display.status_code == 200, by_display.text
    assert by_uuid.status_code == 200, by_uuid.text
    assert by_display.json()["data"]["display_id"] == display
    assert by_uuid.json()["data"]["display_id"] == display
    assert by_display.json()["data"]["status"] == "APPROVED"


def test_knowledge_list_and_candidates_preserve_status_and_policy(seeded_database):
    listing = client.get("/api/v1/knowledge").json()["data"]
    assert listing["total"] == 3
    assert {item["display_id"] for item in listing["items"]} == {
        "kn-wake-false-trigger",
        "kn-noise-profile",
        "kn-legacy-flaky",
    }
    assert listing["status_counts"] == {"APPROVED": 1, "CORROBORATED": 1, "STALE": 1}

    candidates = client.get("/api/v1/knowledge/candidates").json()["data"]
    assert candidates["total"] == 4
    assert candidates["automatic_promotion_allowed"] is False
    assert candidates["requires_human_review"] is True
    assert candidates["policy"]["automatic_promotion_allowed"] is False
    assert candidates["policy"]["requires_human_review"] is True
    statuses = {item["display_id"]: item["status"] for item in candidates["items"]}
    assert statuses == {
        "knc-014": "PROPOSED",
        "knc-012": "UNDER_REVIEW",
        "knc-009": "NEEDS_INFO",
        "knc-006": "APPROVED",
    }
    for item in candidates["items"]:
        assert item["automatic_promotion_allowed"] is False
        assert item["requires_human_review"] is True


def test_runtime_models_and_toolchain_are_read_only(seeded_database):
    models = client.get("/api/v1/runtime/models").json()["data"]
    assert models["total"] == 4
    assert models["read_only"] is True
    assert models["q09_pending"] is True
    assert models["drifted_count"] == 1
    bindings = {item["binding"]: item for item in models["items"]}
    assert bindings["mb-plan-03"]["status"] == "LOCKED"
    assert bindings["mb-summary-01"]["drift"] == "VERSION_MISMATCH"

    toolchain = client.get("/api/v1/runtime/toolchain").json()["data"]
    assert toolchain["total"] == 3
    assert toolchain["read_only"] is True
    assert toolchain["q09_pending"] is True
    assert toolchain["drifted_count"] == 1
    locks = {item["name"]: item["lock"] for item in toolchain["items"]}
    assert locks == {
        "lstest": "LOCKED",
        "audio-harness": "DRIFT",
        "serial-adapter": "LOCKED",
    }


def test_agents_reviews_and_agent_lookup(seeded_database):
    agents = client.get("/api/v1/agents").json()["data"]
    assert agents["total"] == 3
    assert agents["read_only"] is True
    assert agents["q09_pending"] is True
    assert {item["display_id"] for item in agents["items"]} == {
        "agt-planner",
        "agt-runner-win",
        "agt-verifier",
    }

    display = "agt-planner"
    uuid_value = str(stable_uuid(f"agent:{display}"))
    for identifier in (display, uuid_value):
        detail = client.get(f"/api/v1/agents/{identifier}")
        assert detail.status_code == 200, detail.text
        data = detail.json()["data"]
        assert data["display_id"] == display
        assert data["model_binding"] == "mb-plan-03"
        assert data["model"]["binding"] == "mb-plan-03"
        assert data["read_only"] is True

    reviews = client.get("/api/v1/reviews").json()["data"]
    assert reviews["total"] == 2
    assert reviews["read_only"] is True
    by_id = {item["display_id"]: item for item in reviews["items"]}
    assert by_id["revw-007"]["stage"] == "PENDING"
    assert by_id["revw-007"]["task_display_id"] == "tsk-voice-001"
    assert by_id["revw-007"]["revision_display_id"] == "rev-003"
    assert by_id["revw-006"]["stage"] == "COMPLETED"
    assert reviews["open_risk_count"] == 1


def test_audit_integrity_is_read_only_and_secret_free(seeded_database):
    listing = client.get("/api/v1/audit").json()["data"]
    assert listing["total"] == 5
    assert listing["append_only"] is True
    assert listing["read_only"] is True
    assert listing["denied_count"] == 1
    assert {item["integrity"] for item in listing["items"]} == {"HASH_CHAIN_OK"}
    _assert_no_secret_fields(listing)

    detail = client.get("/api/v1/audit/aud-20261029-041").json()["data"]
    assert detail["event_id"] == "aud-20261029-041"
    assert detail["action"] == "APPROVAL_GRANTED"
    assert detail["access_decision"] == "ALLOW"
    assert detail["hash_chain"]["append_only"] is True
    assert detail["hash_chain"]["integrity"] == "HASH_CHAIN_OK"
    assert detail["append_only"] is True
    _assert_no_secret_fields(detail)


def test_recovery_projection_is_read_only_and_never_claims_drill(seeded_database):
    body = client.get("/api/v1/recovery").json()["data"]
    assert body["read_only"] is True
    assert body["hash_chain"]["status"] == "HASH_CHAIN_OK"
    assert body["hash_chain"]["event_count"] == 5
    assert body["hash_chain"]["append_only"] is True
    assert len(body["stop_first_steps"]) == 6
    assert [step["order"] for step in body["stop_first_steps"]] == list(range(1, 7))
    assert len(body["recovery_order"]) == 4
    assert body["drill"]["performed"] is False
    assert body["drill"]["rpo_claim"] is None
    assert body["drill"]["rto_claim"] is None
    assert body["drill"]["backup_conclusion"] == "NOT PROVEN"
    assert body["idempotency"]["key_count"] == 1
    assert body["idempotency"]["scopes"] == ["approval"]
    assert body["reconciliation"]["reconciling_run_count"] == 1
    assert body["reconciliation"]["runs"][0]["display_id"] == "run-042"
    _assert_no_secret_fields(body)


def test_settings_expose_no_secrets_and_keep_categories(seeded_database):
    listing = client.get("/api/v1/settings").json()["data"]
    assert listing["total"] == 12
    assert listing["read_only"] is True
    assert listing["secrets_exposed"] is False
    assert set(listing["categories"]) == {
        "notification",
        "retention",
        "runtime_model",
        "runtime_lock",
    }
    _assert_no_secret_fields(listing)

    access = client.get("/api/v1/settings/access").json()["data"]
    assert access["total_roles"] == 4
    assert access["total_users"] == 5
    assert {role["role_code"] for role in access["roles"]} == {
        "SUPER_ADMIN",
        "SESSION_MANAGER",
        "APPROVER",
        "OBSERVER",
    }
    assert access["secrets_exposed"] is False
    _assert_no_secret_fields(access)

    notifications = client.get("/api/v1/settings/notifications").json()["data"]
    assert notifications["total"] == 2
    assert notifications["degraded_count"] == 1
    assert notifications["dead_letter_total"] == 2
    assert {item["delivery"] for item in notifications["items"]} == {
        "HEALTHY",
        "DEGRADED",
    }
    _assert_no_secret_fields(notifications)

    retention = client.get("/api/v1/settings/retention").json()["data"]
    assert retention["total"] == 3
    assert {item["object"] for item in retention["items"]} == {
        "审计事件",
        "证据元数据",
        "报告",
    }
    _assert_no_secret_fields(retention)


def test_batch3_lists_support_limit_and_cursor(seeded_database):
    for base in (
        "/api/v1/knowledge",
        "/api/v1/knowledge/candidates",
        "/api/v1/agents",
        "/api/v1/reviews",
        "/api/v1/audit",
    ):
        first = client.get(base, params={"limit": 1}).json()["data"]
        assert len(first["items"]) == 1, base
        assert first["next_cursor"] is not None, base
        second = client.get(
            base, params={"limit": 1, "cursor": first["next_cursor"]}
        ).json()["data"]
        assert len(second["items"]) == 1, base
        assert second["items"][0] != first["items"][0], base


def test_observer_role_can_read_batch3(seeded_database):
    for path in BATCH3_ENDPOINTS:
        response = client.get(path, headers={"X-NoahsArk-Role": "OBSERVER"})
        assert response.status_code == 200, f"{path}: {response.text}"


def test_unknown_role_is_forbidden_on_batch3(seeded_database):
    for path in (
        "/api/v1/knowledge",
        "/api/v1/runtime/models",
        "/api/v1/agents",
        "/api/v1/audit",
        "/api/v1/settings",
    ):
        response = client.get(path, headers={"X-NoahsArk-Role": "NOT_A_ROLE"})
        assert response.status_code == 403, path
        body = response.json()
        assert body["error"]["code"] == "FORBIDDEN"
        assert body["error"]["retryable"] is False


def test_unknown_batch3_identifiers_return_enveloped_404(seeded_database):
    for path in (
        "/api/v1/knowledge/kn-does-not-exist",
        "/api/v1/agents/agt-does-not-exist",
        "/api/v1/audit/aud-does-not-exist",
    ):
        response = client.get(path)
        assert response.status_code == 404, path
        assert response.json()["error"]["code"] == "NOT_FOUND"


def test_batch3_exposes_no_write_endpoints(seeded_database):
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
        "/api/v1/knowledge",
        "/api/v1/knowledge/candidates",
        "/api/v1/runtime/models",
        "/api/v1/agents",
        "/api/v1/audit",
        "/api/v1/settings",
        "/api/v1/recovery",
    ):
        assert client.post(path).status_code in {404, 405}, path
