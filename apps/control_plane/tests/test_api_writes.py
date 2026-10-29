"""W3 write-surface tests: capabilities, idempotency, audit and STOP/release.

These tests require the seeded PostgreSQL database (like the W1/W2 suites) and
skip cleanly when no PostgreSQL DATABASE_URL is configured or reachable.

What they lock down:

- exactly one capability per write intent, with OBSERVER denied everywhere;
- APPROVER cannot request STOP and SESSION_MANAGER cannot approve;
- every write requires ``Idempotency-Key``; replays are byte-identical and a
  different payload under the same key is a hard 409;
- a STOP request records intent but never sets run lifecycle to STOPPED;
- a release request without the three preconditions plus cleanup receipt and
  R-05 fails closed with 409, and a successful request still does not release
  the device or touch PASS;
- every accepted write appends exactly one audit event.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import asyncpg
import pytest
from fastapi.testclient import TestClient

from noahsark.config import settings
from noahsark.main import app
from noahsark.seed import digest, seed_database

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping W3 write tests",
)

client = TestClient(app)

INTAKE = "/api/v1/intake/drafts"
APPROVAL = "/api/v1/tasks/tsk-voice-001/approvals"
STOP = "/api/v1/runs/run-042/stop-requests"
RELEASE = "/api/v1/devices/dev-tcl-001/release-requests"

FROZEN_REVISION = "rev-001"
FROZEN_DIGEST = digest("revision:rev-001")

STOP_ROLES = [("SESSION_MANAGER", "session-manager-01"), ("ADMIN", "admin-01")]
CREATE_ROLES = [
    ("APPROVER", "approver-02"),
    ("SESSION_MANAGER", "session-manager-01"),
    ("ADMIN", "admin-01"),
]
APPROVE_ROLES = [
    ("APPROVER", "approver-02", "APPROVED"),
    ("ADMIN", "admin-01", "APPROVED"),
]
RELEASE_ROLES = [("SESSION_MANAGER", "session-manager-01"), ("ADMIN", "admin-01")]


def _dsn() -> str:
    assert DATABASE_URL
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


def _run(coro):
    return asyncio.run(coro)


async def _ping() -> None:
    connection = await asyncpg.connect(_dsn())
    try:
        await connection.fetch("SELECT 1")
    finally:
        await connection.close()


async def _execute(query: str, *args) -> None:
    connection = await asyncpg.connect(_dsn())
    try:
        await connection.execute(query, *args)
    finally:
        await connection.close()


async def _fetchval(query: str, *args):
    connection = await asyncpg.connect(_dsn())
    try:
        return await connection.fetchval(query, *args)
    finally:
        await connection.close()


@pytest.fixture(scope="module")
def seeded_database():
    try:
        _run(_ping())
    except (OSError, asyncpg.PostgresError) as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")
    _run(seed_database(reset=True))
    return True


def _key() -> str:
    return f"test-w3-{uuid.uuid4().hex}"


def _headers(role: str, actor: str | None = None, key: str | None = None) -> dict:
    headers = {"X-NoahsArk-Role": role}
    if actor is not None:
        headers["X-NoahsArk-Actor"] = actor
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _intake_body(title: str = "W3 write-surface draft") -> dict:
    return {
        "title": title,
        "entry_mode": "conversation",
        "summary": "Operator supplied context for a new task.",
        "sources": [{"kind": "conversation", "ref": "thread-1"}],
        "facts": [{"statement": "device is in the lab"}],
        "conflicts": [],
        "gaps": [],
        "freshness": {"captured_at": "2026-10-29T10:00:00Z"},
    }


def _approval_body(decision: str = "APPROVED") -> dict:
    return {
        "decision": decision,
        "comment": "Scope reviewed against the frozen revision digest.",
        "revision_content_digest": FROZEN_DIGEST,
        "scope_snapshot": {"task": "tsk-voice-001", "revision": FROZEN_REVISION},
        "revision_id": FROZEN_REVISION,
    }


def _stop_body(reason: str = "Operator requested a safe stop") -> dict:
    return {"reason": reason}


def _release_body(reason: str = "Bench teardown after cleanup") -> dict:
    return {"reason": reason, "on_site_confirmed": False}


def _preconditions(*values: bool) -> dict:
    keys = (
        "local_stop_confirmed",
        "safe_cleanup_done",
        "occupancy_reconciled",
    )
    return dict(zip(keys, values, strict=True))


# ---------------------------------------------------------------------------
# Success per capability
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("role,actor", CREATE_ROLES)
def test_create_task_capability_creates_intake_draft(seeded_database, role, actor):
    response = client.post(
        INTAKE,
        json=_intake_body(title=f"draft by {role}"),
        headers=_headers(role, actor, _key()),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["meta"]["server_authoritative"] is True
    data = body["data"]
    assert data["created"] is True
    assert data["stage"] == "DRAFT"
    assert data["owner_role"] == role


@pytest.mark.parametrize("role,actor,decision", APPROVE_ROLES)
def test_approve_capability_records_approval(seeded_database, role, actor, decision):
    # The schema allows at most one APPROVED approval per revision, so clear the
    # prior parametrized row to keep each role's success path independent.
    _run(
        _execute(
            "DELETE FROM approvals WHERE revision_id = "
            "(SELECT revision_id FROM task_revisions WHERE display_id = $1)",
            FROZEN_REVISION,
        )
    )
    response = client.post(
        APPROVAL,
        json=_approval_body(decision),
        headers=_headers(role, actor, _key()),
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["created"] is True
    assert data["decision"] == decision
    assert data["revision_display_id"] == FROZEN_REVISION
    assert data["revision_content_digest"] == FROZEN_DIGEST
    assert data["scope_snapshot"] == {
        "task": "tsk-voice-001",
        "revision": FROZEN_REVISION,
    }
    assert data["self_approval"] is False


@pytest.mark.parametrize("role,actor", STOP_ROLES)
def test_stop_capability_records_request_without_stopping_run(
    seeded_database, role, actor
):
    before = client.get("/api/v1/runs/run-042").json()["data"]
    assert before["lifecycle_status"] == "RUNNING"
    assert before["execution_status"] == "RUNNING"

    response = client.post(
        STOP,
        json=_stop_body(f"stop request by {role}"),
        headers=_headers(role, actor, _key()),
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["requested"] is True
    assert data["stops_run_immediately"] is False
    assert data["lifecycle_status"] == "RUNNING"
    assert data["execution_status"] == "RUNNING"

    after = client.get("/api/v1/runs/run-042").json()["data"]
    assert after["lifecycle_status"] == "RUNNING"
    assert after["execution_status"] == "RUNNING"
    assert after["axes"]["execution_status"] == "RUNNING"

    persisted = _run(
        _fetchval(
            "SELECT status FROM write_requests WHERE display_id = $1",
            data["stop_request_id"],
        )
    )
    assert persisted == "REQUESTED"


def test_stop_request_is_persisted_but_never_sets_stopped(seeded_database):
    response = client.post(
        STOP,
        json=_stop_body("regression guard for STOP semantics"),
        headers=_headers("ADMIN", "admin-01", _key()),
    )
    assert response.status_code == 201, response.text
    run = client.get("/api/v1/runs/run-042").json()["data"]
    assert run["lifecycle_status"] != "STOPPED"
    assert run["execution_status"] != "STOPPED"
    assert run["lifecycle_status"] == "RUNNING"


@pytest.mark.parametrize("role,actor", RELEASE_ROLES)
def test_release_capability_records_request_without_releasing(
    seeded_database, role, actor
):
    receipt = str(uuid.uuid4())
    _run(
        _execute(
            "UPDATE leases SET release_preconditions = $1::jsonb "
            "WHERE display_id = 'lease-7781'",
            '{"local_stop_confirmed": true, "safe_cleanup_done": true, '
            '"occupancy_reconciled": true}',
        )
    )
    _run(
        _execute(
            "UPDATE runs SET cleanup_receipt_id = $1::uuid "
            "WHERE display_id = 'run-042'",
            receipt,
        )
    )
    try:
        response = client.post(
            RELEASE,
            json=_release_body(f"release request by {role}"),
            headers=_headers(role, actor, _key()),
        )
        assert response.status_code == 201, response.text
        data = response.json()["data"]
        assert data["requested"] is True
        assert data["release_state"] == "REQUESTED"
        assert data["preconditions"] == _preconditions(True, True, True)
        assert data["cleanup_receipt_present"] is True
        assert data["r05_satisfied"] is True
        assert data["release_equals_pass"] is False
        assert data["verdict_unchanged"] is True

        persisted = _run(
            _fetchval(
                "SELECT request_type FROM write_requests WHERE display_id = $1",
                data["release_request_id"],
            )
        )
        assert persisted == "RELEASE"

        # A release *request* is not a release: occupancy is still OCCUPIED, so
        # the read projection must stay held even with all preconditions met.
        device = client.get("/api/v1/devices/dev-tcl-001").json()["data"]
        assert device["occupancy_state"] == "OCCUPIED"
        assert device["release_state"] == "held"
        assert device["release"]["independent_of_verdict"] is True

        verdict = client.get("/api/v1/tasks/tsk-voice-001/verdict").json()["data"]
        assert verdict["available"] is False
        assert verdict["formal_pass"] is False
    finally:
        _run(
            _execute(
                "UPDATE leases SET release_preconditions = $1::jsonb "
                "WHERE display_id = 'lease-7781'",
                '{"local_stop_confirmed": true, "safe_cleanup_done": false, '
                '"occupancy_reconciled": false}',
            )
        )
        _run(
            _execute(
                "UPDATE runs SET cleanup_receipt_id = NULL "
                "WHERE display_id = 'run-042'"
            )
        )


# ---------------------------------------------------------------------------
# Role separation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", INTAKE, _intake_body()),
        ("post", APPROVAL, _approval_body()),
        ("post", STOP, _stop_body()),
        ("post", RELEASE, _release_body()),
    ],
)
def test_observer_is_forbidden_on_every_write(seeded_database, method, path, body):
    response = getattr(client, method)(
        path,
        json=body,
        headers=_headers("OBSERVER", "observer-01", _key()),
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_approver_cannot_request_stop(seeded_database):
    response = client.post(
        STOP,
        json=_stop_body(),
        headers=_headers("APPROVER", "approver-02", _key()),
    )
    assert response.status_code == 403, response.text
    error = response.json()["error"]
    assert error["code"] == "FORBIDDEN"
    assert error["details"]["required_capability"] == "STOP"


def test_session_manager_cannot_approve(seeded_database):
    response = client.post(
        APPROVAL,
        json=_approval_body(),
        headers=_headers("SESSION_MANAGER", "session-manager-01", _key()),
    )
    assert response.status_code == 403, response.text
    error = response.json()["error"]
    assert error["code"] == "FORBIDDEN"
    assert error["details"]["required_capability"] == "APPROVE"


def test_session_manager_cannot_approve_even_with_frozen_revision(seeded_database):
    # Capability must be checked before any state-machine work, so a valid
    # frozen revision must not leak a different error code.
    response = client.post(
        APPROVAL,
        json=_approval_body(),
        headers=_headers("SESSION_MANAGER", key=_key()),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "path,body",
    [
        (INTAKE, _intake_body()),
        (APPROVAL, _approval_body()),
        (STOP, _stop_body()),
        (RELEASE, _release_body()),
    ],
)
def test_missing_idempotency_key_is_rejected(seeded_database, path, body):
    response = client.post(path, json=body, headers=_headers("ADMIN", "admin-01"))
    assert response.status_code == 400, response.text
    error = response.json()["error"]
    assert error["code"] == "IDEMPOTENCY_REQUIRED"
    assert error["details"]["header"] == "Idempotency-Key"


def test_blank_idempotency_key_is_rejected(seeded_database):
    response = client.post(
        INTAKE,
        json=_intake_body(),
        headers=_headers("ADMIN", "admin-01", "   "),
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "IDEMPOTENCY_REQUIRED"


def test_replayed_key_and_payload_returns_original_response(seeded_database):
    key = _key()
    body = _intake_body("idempotent replay")
    headers = _headers("ADMIN", "admin-01", key)

    first = client.post(INTAKE, json=body, headers=headers)
    second = client.post(INTAKE, json=body, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["data"] == second.json()["data"]


def test_same_key_with_different_payload_conflicts(seeded_database):
    key = _key()
    headers = _headers("ADMIN", "admin-01", key)

    first = client.post(INTAKE, json=_intake_body("original title"), headers=headers)
    second = client.post(INTAKE, json=_intake_body("different title"), headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text
    error = second.json()["error"]
    assert error["code"] == "IDEMPOTENCY_CONFLICT"
    assert error["retryable"] is False


# ---------------------------------------------------------------------------
# Fail-closed release preconditions + audit
# ---------------------------------------------------------------------------
def test_release_precondition_failure_is_409(seeded_database):
    response = client.post(
        RELEASE,
        json=_release_body(),
        headers=_headers("SESSION_MANAGER", "session-manager-01", _key()),
    )
    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "RELEASE_PRECONDITION_FAILED"
    details = error["details"]
    assert details["reason"] == "RELEASE_PRECONDITION_FAILED"
    assert set(details["missing"]) >= {
        "safe_cleanup_done",
        "occupancy_reconciled",
        "cleanup_receipt",
    }
    assert details["r05_node_reachable"] is True
    assert details["on_site_confirmed"] is False


def test_accepted_write_appends_one_audit_event(seeded_database):
    before = _run(_fetchval("SELECT count(*) FROM audit_events"))

    response = client.post(
        INTAKE,
        json=_intake_body("audited draft"),
        headers=_headers("ADMIN", "admin-01", _key()),
    )
    assert response.status_code == 201, response.text

    after = _run(_fetchval("SELECT count(*) FROM audit_events"))
    assert after == before + 1

    latest = _run(
        _fetchval(
            "SELECT action FROM audit_events ORDER BY occurred_at DESC, event_id DESC LIMIT 1"
        )
    )
    assert latest == "INTAKE_DRAFT_CREATED"
