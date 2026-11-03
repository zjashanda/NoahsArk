"""Supervisor binding tests for task creation and the read projection.

The suite requires the migrated, seeded PostgreSQL database and skips cleanly
when it is unavailable.  It locks down:

- one task + one initial revision + one PENDING supervisor binding per POST;
- idempotent replay, hard conflict on a changed payload and capability denial;
- the partial unique index that allows only one active binding per task;
- masked remote session ids, sanitized result metadata and no lease/dispatch
  internals in the read projection;
- no run, verdict or evidence row is created as a side effect of task creation.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import asyncpg
import pytest
from fastapi.testclient import TestClient
from noahsark.config import settings
from noahsark.main import app
from noahsark.models.supervisor import SUPERVISOR_STATES
from noahsark.seed import seed_database

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping supervisor tests",
)

client = TestClient(app)
TASKS = "/api/v1/tasks"


def _dsn() -> str:
    assert DATABASE_URL
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


def _run(coro):
    return asyncio.run(coro)


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(_dsn())


async def _ping() -> None:
    connection = await _connect()
    try:
        await connection.fetch("SELECT 1")
    finally:
        await connection.close()


async def _execute(query: str, *args) -> None:
    connection = await _connect()
    try:
        await connection.execute(query, *args)
    finally:
        await connection.close()


async def _fetch(query: str, *args) -> list[asyncpg.Record]:
    connection = await _connect()
    try:
        return list(await connection.fetch(query, *args))
    finally:
        await connection.close()


async def _fetchrow(query: str, *args) -> asyncpg.Record | None:
    connection = await _connect()
    try:
        return await connection.fetchrow(query, *args)
    finally:
        await connection.close()


async def _fetchval(query: str, *args):
    connection = await _connect()
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
    return f"test-supervisor-{uuid.uuid4().hex}"


def _headers(role: str = "ADMIN", key: str | None = None) -> dict:
    headers = {"X-NoahsArk-Role": role, "X-NoahsArk-Actor": "admin-01"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _body(**overrides) -> dict:
    body = {
        "title": "Supervisor binding task",
        "objective": "Verify the task creates a durable PENDING supervisor binding.",
        "entry_mode": "conversation",
        "lead_agent_id": "agt-planner",
        "lead_session_id": str(uuid.uuid4()),
        "prompt": "Open the task and prepare a plan. Never echo this prompt.",
    }
    body.update(overrides)
    return body


def _create(body: dict | None = None, role: str = "ADMIN") -> dict:
    payload = body or _body()
    response = client.post(TASKS, json=payload, headers=_headers(role, _key()))
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_create_task_binds_pending_supervisor_without_execution_rows(
    seeded_database,
):
    body = _body()
    before = _run(
        _fetchrow(
            "SELECT (SELECT count(*) FROM runs) AS runs, "
            "(SELECT count(*) FROM verdicts) AS verdicts, "
            "(SELECT count(*) FROM evidence_items) AS evidence"
        )
    )
    data = _create(body)
    task_id = data["task_id"]

    assert data["status"] == "DRAFT"
    assert data["status"] != "PASS"
    assert data["supervisor_state"] == "PENDING"
    assert data["revision_display_id"].startswith("rev-")
    assert data["prompt_digest"].startswith("sha256:")
    assert data["prompt_bytes"] == len(body["prompt"].encode("utf-8"))

    row = _run(
        _fetchrow(
            "SELECT s.state, s.remote_session_id, s.prompt_digest, s.prompt_bytes, "
            "s.task_id, s.revision_id, t.status, t.lead_session_id, "
            "t.current_revision_id, r.content::text AS content "
            "FROM supervisor_sessions s "
            "JOIN tasks t ON t.task_id = s.task_id "
            "JOIN task_revisions r ON r.revision_id = s.revision_id "
            "WHERE s.task_id = $1::uuid",
            task_id,
        )
    )
    assert row is not None
    assert row["state"] == "PENDING"
    assert row["remote_session_id"] is None
    assert row["prompt_bytes"] == len(body["prompt"].encode("utf-8"))
    assert row["status"] == "DRAFT"
    assert str(row["lead_session_id"]) == body["lead_session_id"]
    assert str(row["current_revision_id"]) == str(row["revision_id"])
    assert body["prompt"] not in (row["content"] or "")

    after = _run(
        _fetchrow(
            "SELECT (SELECT count(*) FROM runs) AS runs, "
            "(SELECT count(*) FROM verdicts) AS verdicts, "
            "(SELECT count(*) FROM evidence_items) AS evidence"
        )
    )
    assert after == before
    assert (
        _run(
            _fetchval(
                "SELECT count(*) FROM runs WHERE task_id = $1::uuid", task_id
            )
        )
        == 0
    )
    assert (
        _run(
            _fetchval(
                "SELECT count(*) FROM verdicts WHERE task_id = $1::uuid", task_id
            )
        )
        == 0
    )
    assert (
        _run(
            _fetchval(
                "SELECT count(*) FROM evidence_items WHERE task_id = $1::uuid",
                task_id,
            )
        )
        == 0
    )


def test_idempotent_replay_returns_same_binding(seeded_database):
    key = _key()
    body = _body(title="Idempotent supervisor task")
    headers = _headers("ADMIN", key)

    first = client.post(TASKS, json=body, headers=headers)
    second = client.post(TASKS, json=body, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["data"] == second.json()["data"]

    task_id = first.json()["data"]["task_id"]
    assert (
        _run(
            _fetchval(
                "SELECT count(*) FROM supervisor_sessions WHERE task_id = $1::uuid",
                task_id,
            )
        )
        == 1
    )
    assert (
        _run(
            _fetchval(
                "SELECT count(*) FROM task_revisions WHERE task_id = $1::uuid",
                task_id,
            )
        )
        == 1
    )
    assert (
        _run(
            _fetchval(
                "SELECT count(*) FROM audit_events WHERE object_id = $1",
                first.json()["data"]["display_id"],
            )
        )
        == 1
    )


def test_same_key_with_different_payload_conflicts(seeded_database):
    key = _key()
    headers = _headers("ADMIN", key)
    first = client.post(TASKS, json=_body(title="Original"), headers=headers)
    second = client.post(TASKS, json=_body(title="Changed"), headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text
    error = second.json()["error"]
    assert error["code"] == "IDEMPOTENCY_CONFLICT"
    assert error["retryable"] is False


def test_observer_cannot_create_task(seeded_database):
    response = client.post(
        TASKS, json=_body(), headers=_headers("OBSERVER", _key())
    )
    assert response.status_code == 403, response.text
    error = response.json()["error"]
    assert error["code"] == "FORBIDDEN"
    assert error["details"]["required_capability"] == "CREATE_TASK"


def test_one_active_supervisor_session_per_task(seeded_database):
    data = _create(_body(title="Active binding invariant"))
    task_id = data["task_id"]
    revision_id = data["current_revision_id"]

    with pytest.raises(asyncpg.UniqueViolationError):
        _run(
            _execute(
                "INSERT INTO supervisor_sessions ("
                "supervisor_session_id, display_id, task_id, revision_id, state, "
                "remote_session_id, prompt_digest, prompt_bytes, result_summary, "
                "error_code, result_updated_at, schema_version, source, seed, "
                "created_at, updated_at) VALUES ("
                "$1::uuid, $2, $3::uuid, $4::uuid, 'PENDING', NULL, "
                "'sha256:dup', 1, NULL, NULL, NULL, '1.0', 'control-plane', "
                "false, now(), now())",
                str(uuid.uuid4()),
                f"sup-{uuid.uuid4().hex[:8]}",
                task_id,
                revision_id,
            )
        )

    # Terminal history is allowed: once the first binding is terminal a new
    # active binding for a later revision can be inserted.
    _run(
        _execute(
            "UPDATE supervisor_sessions SET state = 'COMPLETED', updated_at = now() "
            "WHERE task_id = $1::uuid",
            task_id,
        )
    )
    _run(
        _execute(
            "INSERT INTO supervisor_sessions ("
            "supervisor_session_id, display_id, task_id, revision_id, state, "
            "remote_session_id, prompt_digest, prompt_bytes, result_summary, "
            "error_code, result_updated_at, schema_version, source, seed, "
            "created_at, updated_at) VALUES ("
            "$1::uuid, $2, $3::uuid, $4::uuid, 'PENDING', NULL, "
            "'sha256:next', 1, NULL, NULL, NULL, '1.0', 'control-plane', "
            "false, now(), now())",
            str(uuid.uuid4()),
            f"sup-{uuid.uuid4().hex[:8]}",
            task_id,
            revision_id,
        )
    )


def test_supervisor_projection_masks_remote_id_and_hides_internals(
    seeded_database,
):
    data = _create(_body(title="Projection redaction"))
    task_id = data["task_id"]
    remote_id = "ses_remote_secret_9876"
    _run(
        _execute(
            "UPDATE supervisor_sessions SET state = 'BINDING', "
            "remote_session_id = $1, result_summary = $2, "
            "error_code = 'E_REMOTE_TIMEOUT', result_updated_at = now(), "
            "updated_at = now() WHERE task_id = $3::uuid",
            remote_id,
            "Sanitized worker summary",
            task_id,
        )
    )

    response = client.get(
        f"{TASKS}/{data['display_id']}/supervisor", headers=_headers()
    )
    assert response.status_code == 200, response.text
    projection = response.json()["data"]
    assert projection["supervisor_session_id"] == data["supervisor_session_id"]
    assert projection["task_id"] == task_id
    assert projection["state"] == "BINDING"
    assert projection["state_is_terminal"] is False
    assert projection["remote_session_id"] == "ses_***9876"
    assert projection["remote_session_id_masked"] is True
    assert projection["result"]["available"] is True
    assert projection["result"]["summary"] == "Sanitized worker summary"
    assert projection["result"]["error_code"] == "E_REMOTE_TIMEOUT"
    assert remote_id not in json.dumps(projection)
    assert projection["binding"]["stable"] is True
    assert projection["binding"]["one_active_session_per_task"] is True

    forbidden_fragments = ("lease", "dispatch", "worker", "token", "transcript")
    for key in _keys(projection):
        assert not any(
            fragment in key.lower() for fragment in forbidden_fragments
        ), f"internal field leaked: {key}"

    second = client.get(
        f"{TASKS}/{task_id}/supervisor", headers=_headers()
    ).json()["data"]
    assert second["supervisor_session_id"] == projection["supervisor_session_id"]
    assert second["state"] == "BINDING"


def test_supervisor_read_404_for_unknown_task(seeded_database):
    response = client.get(
        f"{TASKS}/tsk-does-not-exist/supervisor", headers=_headers()
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_unknown_lead_agent_is_rejected(seeded_database):
    response = client.post(
        TASKS,
        json=_body(lead_agent_id="agt-does-not-exist"),
        headers=_headers("ADMIN", _key()),
    )
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("field", ["remote_session_id", "opencode_session_id"])
def test_create_task_rejects_caller_supplied_session_id(seeded_database, field):
    """The platform binds by creating a session, never by attaching to one."""
    before = _run(_fetchval("SELECT count(*) FROM tasks"))
    response = client.post(
        TASKS,
        json=_body(**{field: "ses_e6442b5ffffeJldY7d4ZmKwsI4"}),
        headers=_headers("ADMIN", _key()),
    )
    assert response.status_code == 400, response.text
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["errors"][0]["type"] == "extra_forbidden"
    assert _run(_fetchval("SELECT count(*) FROM tasks")) == before


def test_state_vocabulary_is_explicit():
    assert SUPERVISOR_STATES == (
        "PENDING",
        "BINDING",
        "READY",
        "DISPATCHED",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "STOP_REQUESTED",
        "STOPPED",
    )


def _keys(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.append(str(key))
            found.extend(_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_keys(item))
    return found
