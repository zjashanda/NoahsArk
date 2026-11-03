"""Node Gateway tests against a disposable node in the dev database.

These tests never reset or truncate the shared database.  A uniquely named node
is created through the admin API, exercised through ``/node/v1/*``, and deleted
again; only append-only audit rows remain as history.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import uuid
from collections.abc import AsyncIterator

import asyncpg
import pytest
from fastapi.testclient import TestClient

from noahsark.config import settings
from noahsark.main import app

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping node gateway tests",
)

client = TestClient(app)

ADMIN_HEADERS = {"X-NoahsArk-Role": "ADMIN", "X-NoahsArk-Actor": "node-gateway-test"}
NODES = "/api/v1/nodes"
GATEWAY = "/node/v1"


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


async def _fetchrow(query: str, *args):
    connection = await asyncpg.connect(_dsn())
    try:
        return await connection.fetchrow(query, *args)
    finally:
        await connection.close()


@pytest.fixture(scope="module", autouse=True)
def database_ready() -> bool:
    try:
        _run(_ping())
    except (OSError, asyncpg.PostgresError) as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")
    return True


def _create_node(display_id: str) -> str:
    response = client.post(
        NODES,
        json={"display_id": display_id, "hostname": "node-gateway-test"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["node_id"]


def _issue_token(node_id: str) -> str:
    response = client.post(f"{NODES}/{node_id}/token", headers=ADMIN_HEADERS)
    assert response.status_code == 200, response.text
    return response.json()["data"]["token"]


def _delete_node(node_id: str) -> None:
    client.delete(f"{NODES}/{node_id}", headers=ADMIN_HEADERS)


@pytest.fixture(scope="module")
def node() -> AsyncIterator[dict[str, str]]:
    display_id = f"test-node-gw-{uuid.uuid4().hex[:12]}"
    node_id = _create_node(display_id)
    token = _issue_token(node_id)
    try:
        yield {"node_id": node_id, "display_id": display_id, "token": token}
    finally:
        _delete_node(node_id)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_body(node_id: str, version: str = "0.1.0") -> dict[str, object]:
    return {
        "node_id": node_id,
        "agent_version": version,
        "protocol_version": "1",
    }


def test_register_with_good_token_marks_node_online(node: dict[str, str]) -> None:
    response = client.post(
        f"{GATEWAY}/register",
        json=_register_body(node["node_id"], version="1.2.3"),
        headers=_bearer(node["token"]),
    )

    assert response.status_code == 200
    assert response.json() == {"node_id": node["node_id"], "registered": True}
    row = _run(
        _fetchrow(
            "SELECT communication_state, agent_version, status, last_heartbeat_at "
            "FROM nodes WHERE node_id = $1",
            uuid.UUID(node["node_id"]),
        )
    )
    assert row["communication_state"] == "ONLINE"
    assert row["agent_version"] == "1.2.3"
    assert row["status"] == "ACTIVE"
    assert row["last_heartbeat_at"] is not None


def test_register_without_token_is_unauthorized(node: dict[str, str]) -> None:
    response = client.post(f"{GATEWAY}/register", json=_register_body(node["node_id"]))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NODE_UNAUTHORIZED"


def test_register_with_bad_token_is_unauthorized(node: dict[str, str]) -> None:
    response = client.post(
        f"{GATEWAY}/register",
        json=_register_body(node["node_id"]),
        headers=_bearer("not-the-issued-token"),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NODE_UNAUTHORIZED"


def test_register_unknown_node_is_not_found(node: dict[str, str]) -> None:
    response = client.post(
        f"{GATEWAY}/register",
        json=_register_body(str(uuid.uuid4())),
        headers=_bearer(node["token"]),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NODE_NOT_FOUND"


def test_heartbeat_updates_last_heartbeat_at(node: dict[str, str]) -> None:
    node_uuid = uuid.UUID(node["node_id"])
    _run(
        _execute(
            "UPDATE nodes SET last_heartbeat_at = now() - interval '1 hour', "
            "communication_state = 'OFFLINE', agent_version = 'old' "
            "WHERE node_id = $1",
            node_uuid,
        )
    )
    before = _run(
        _fetchrow(
            "SELECT last_heartbeat_at FROM nodes WHERE node_id = $1", node_uuid
        )
    )

    response = client.post(
        f"{GATEWAY}/heartbeat",
        json={**_register_body(node["node_id"], version="2.0.0"), "status": {}},
        headers=_bearer(node["token"]),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    after = _run(
        _fetchrow(
            "SELECT communication_state, agent_version, last_heartbeat_at "
            "FROM nodes WHERE node_id = $1",
            node_uuid,
        )
    )
    assert after["communication_state"] == "ONLINE"
    assert after["agent_version"] == "2.0.0"
    assert after["last_heartbeat_at"] > before["last_heartbeat_at"]


def test_poll_returns_empty_messages(node: dict[str, str]) -> None:
    response = client.post(
        f"{GATEWAY}/poll",
        json={
            "node_id": node["node_id"],
            "lease_id": None,
            "epoch": 1,
            "timeout_seconds": 25,
        },
        headers=_bearer(node["token"]),
    )

    assert response.status_code == 200
    assert response.json() == {"messages": []}


def test_receipts_are_acknowledged_once(node: dict[str, str]) -> None:
    response = client.post(
        f"{GATEWAY}/receipts",
        json={
            "node_id": node["node_id"],
            "message_id": "msg-test-1",
            "kind": "receipt",
        },
        headers=_bearer(node["token"]),
    )

    assert response.status_code == 200
    assert response.json() == {"accepted": True, "duplicate": False}


def test_reconcile_returns_empty_messages(node: dict[str, str]) -> None:
    response = client.post(
        f"{GATEWAY}/reconcile",
        json={
            "node_id": node["node_id"],
            "lease_id": None,
            "epoch": 1,
            "executed_job_ids": [],
        },
        headers=_bearer(node["token"]),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "messages": []}


def test_token_issuance_stores_hash_and_returns_plaintext_once() -> None:
    display_id = f"test-node-token-{uuid.uuid4().hex[:12]}"
    node_id = _create_node(display_id)
    try:
        response = client.post(f"{NODES}/{node_id}/token", headers=ADMIN_HEADERS)
        assert response.status_code == 200
        data = response.json()["data"]
        token = data["token"]
        assert data["node_id"] == node_id
        assert data["issued"] is True
        assert isinstance(token, str) and len(token) >= 32

        row = _run(
            _fetchrow(
                "SELECT identity FROM nodes WHERE node_id = $1", uuid.UUID(node_id)
            )
        )
        identity = row["identity"]
        if isinstance(identity, str):
            identity = json.loads(identity)
        stored = identity["agent_token_hash"]
        assert stored == hashlib.sha256(token.encode("utf-8")).hexdigest()
        # The plaintext must never be persisted anywhere in the identity blob.
        assert token not in str(identity)

        rotated = client.post(f"{NODES}/{node_id}/token", headers=ADMIN_HEADERS)
        assert rotated.status_code == 200
        assert rotated.json()["data"]["token"] != token
    finally:
        _delete_node(node_id)


# ---------------------------------------------------------------------------
# Platform enrollment flow
# ---------------------------------------------------------------------------
ENROLL = f"{GATEWAY}/enroll"
ENROLLMENT_TOKEN_URL = f"{NODES}/enrollment-token"


def _enroll(token: str, hostname: str, agent_version: str | None = None):
    payload: dict[str, object] = {"enrollment_token": token, "hostname": hostname}
    if agent_version is not None:
        payload["agent_version"] = agent_version
    return client.post(ENROLL, json=payload)


def _enroll_ok(hostname: str, agent_version: str | None = None) -> dict[str, str]:
    response = _enroll(settings.node_enrollment_token, hostname, agent_version)
    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data) == {"node_id", "display_id", "agent_token"}
    return data


def _identity(node_id: str) -> dict:
    row = _run(
        _fetchrow("SELECT identity FROM nodes WHERE node_id = $1", uuid.UUID(node_id))
    )
    identity = row["identity"]
    if isinstance(identity, str):
        identity = json.loads(identity)
    return identity


def test_enroll_with_valid_token_creates_node_and_hashes_token() -> None:
    hostname = f"enroll-{uuid.uuid4().hex[:10]}"
    response = _enroll(settings.node_enrollment_token, hostname, "9.9.9")

    assert response.status_code == 200
    data = response.json()
    assert data["display_id"] == hostname
    token = data["agent_token"]
    assert isinstance(token, str) and len(token) >= 32

    try:
        identity = _identity(data["node_id"])
        assert identity["agent_token_hash"] == hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()
        assert token not in str(identity)

        row = _run(
            _fetchrow(
                "SELECT hostname, agent_version, status, communication_state, "
                "updated_at FROM nodes WHERE node_id = $1",
                uuid.UUID(data["node_id"]),
            )
        )
        assert row["hostname"] == hostname
        assert row["agent_version"] == "9.9.9"
        assert row["status"] == "ACTIVE"
        assert row["communication_state"] == "OFFLINE"
        assert row["updated_at"] is not None

        event = _run(
            _fetchrow(
                "SELECT after FROM audit_events WHERE action = 'NODE_ENROLLED' "
                "AND object_id = $1 ORDER BY occurred_at DESC LIMIT 1",
                data["display_id"],
            )
        )
        payload = event["after"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        assert payload["node_id"] == data["node_id"]
        assert token not in str(payload)
        assert settings.node_enrollment_token not in str(payload)
    finally:
        _delete_node(data["node_id"])


def test_enroll_with_bad_or_blank_token_is_unauthorized() -> None:
    hostname = f"enroll-bad-{uuid.uuid4().hex[:10]}"

    bad = _enroll("not-the-enrollment-token", hostname)
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "ENROLLMENT_UNAUTHORIZED"

    blank = _enroll("   ", hostname)
    assert blank.status_code == 401
    assert blank.json()["error"]["code"] == "ENROLLMENT_UNAUTHORIZED"

    row = _run(
        _fetchrow("SELECT node_id FROM nodes WHERE hostname = $1", hostname)
    )
    assert row is None


def test_enroll_duplicate_hostname_gets_unique_display_id() -> None:
    hostname = f"enroll-dup-{uuid.uuid4().hex[:10]}"
    first = _enroll_ok(hostname)
    try:
        second = _enroll_ok(hostname)
        try:
            assert first["display_id"] == hostname
            assert second["display_id"] != first["display_id"]
            assert second["display_id"].startswith(f"{hostname}-")
            assert len(second["display_id"]) <= 80
        finally:
            _delete_node(second["node_id"])
    finally:
        _delete_node(first["node_id"])


def test_enrolled_node_can_register_and_heartbeat() -> None:
    hostname = f"enroll-live-{uuid.uuid4().hex[:10]}"
    data = _enroll_ok(hostname, "0.1.0")
    try:
        registered = client.post(
            f"{GATEWAY}/register",
            json=_register_body(data["node_id"], version="1.0.0"),
            headers=_bearer(data["agent_token"]),
        )
        assert registered.status_code == 200, registered.text

        heartbeat = client.post(
            f"{GATEWAY}/heartbeat",
            json={**_register_body(data["node_id"], version="1.1.0"), "status": {}},
            headers=_bearer(data["agent_token"]),
        )
        assert heartbeat.status_code == 200, heartbeat.text

        row = _run(
            _fetchrow(
                "SELECT communication_state, agent_version, last_heartbeat_at "
                "FROM nodes WHERE node_id = $1",
                uuid.UUID(data["node_id"]),
            )
        )
        assert row["communication_state"] == "ONLINE"
        assert row["agent_version"] == "1.1.0"
        assert row["last_heartbeat_at"] is not None
    finally:
        _delete_node(data["node_id"])


def test_enrollment_token_read_is_admin_only() -> None:
    admin = client.get(ENROLLMENT_TOKEN_URL, headers=ADMIN_HEADERS)
    assert admin.status_code == 200
    data = admin.json()["data"]
    assert data == {"token": settings.node_enrollment_token, "issued": True}

    for role in ("OBSERVER", "APPROVER", "SESSION_MANAGER"):
        denied = client.get(
            ENROLLMENT_TOKEN_URL,
            headers={"X-NoahsArk-Role": role, "X-NoahsArk-Actor": "enroll-test"},
        )
        assert denied.status_code == 403, (role, denied.text)
        assert settings.node_enrollment_token not in denied.text
