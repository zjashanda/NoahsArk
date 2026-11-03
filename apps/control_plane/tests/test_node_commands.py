"""Node command channel tests against a disposable node.

Covers the admin enqueue surface, the single-claim poll, and result storage.
The shared database is never reset; the fixture node is deleted afterwards and
``node_commands`` rows cascade with it.
"""

from __future__ import annotations

import asyncio
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
    reason="DATABASE_URL is not configured for PostgreSQL; skipping node command tests",
)

client = TestClient(app)

ADMIN_HEADERS = {"X-NoahsArk-Role": "ADMIN", "X-NoahsArk-Actor": "node-command-test"}
OBSERVER_HEADERS = {"X-NoahsArk-Role": "OBSERVER", "X-NoahsArk-Actor": "observer"}
NODES = "/api/v1/nodes"
GATEWAY = "/node/v1"


def _dsn() -> str:
    assert DATABASE_URL
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _ping() -> None:
    connection = await asyncpg.connect(_dsn())
    try:
        await connection.fetch("SELECT 1")
    finally:
        await connection.close()


@pytest.fixture(scope="module", autouse=True)
def database_ready() -> bool:
    try:
        asyncio.run(_ping())
    except (OSError, asyncpg.PostgresError) as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")
    return True


def _create_node(display_id: str) -> str:
    response = client.post(
        NODES,
        json={"display_id": display_id, "hostname": "node-command-test"},
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
    display_id = f"test-node-cmd-{uuid.uuid4().hex[:12]}"
    node_id = _create_node(display_id)
    token = _issue_token(node_id)
    try:
        yield {"node_id": node_id, "display_id": display_id, "token": token}
    finally:
        _delete_node(node_id)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _enqueue(
    node_id: str,
    *,
    tool_id: str = "usb.scan",
    args: dict | None = None,
    headers: dict[str, str] | None = None,
):
    return client.post(
        f"{NODES}/{node_id}/commands",
        json={"tool_id": tool_id, "args": args or {}},
        headers=headers or ADMIN_HEADERS,
    )


def _poll(node: dict[str, str]):
    return client.post(
        f"{GATEWAY}/poll",
        json={"node_id": node["node_id"], "timeout_seconds": 1},
        headers=_bearer(node["token"]),
    )


def test_enqueue_requires_admin(node: dict[str, str]) -> None:
    response = _enqueue(node["node_id"], headers=OBSERVER_HEADERS)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_unknown_tool_is_rejected(node: dict[str, str]) -> None:
    response = _enqueue(node["node_id"], tool_id="shell.exec")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNKNOWN_TOOL"


def test_usb_scan_rejects_arguments(node: dict[str, str]) -> None:
    response = _enqueue(node["node_id"], args={"command": "whoami"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_TOOL_ARGS"


def test_enqueue_queues_and_poll_claims_exactly_once(
    node: dict[str, str],
) -> None:
    created = _enqueue(node["node_id"])
    assert created.status_code == 200, created.text
    data = created.json()["data"]
    assert data["status"] == "QUEUED"
    command_id = data["command_id"]

    first = _poll(node)
    assert first.status_code == 200, first.text
    messages = first.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["kind"] == "command"
    assert messages[0]["command_id"] == command_id
    assert messages[0]["tool_id"] == "usb.scan"
    assert messages[0]["args"] == {}
    assert messages[0]["timeout_seconds"] == 30

    second = _poll(node)
    assert second.status_code == 200, second.text
    assert second.json()["messages"] == []

    got = client.get(f"{NODES}/{node['node_id']}/commands/{command_id}", headers=ADMIN_HEADERS)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["status"] == "SENT"


def test_command_result_stores_status_and_output(node: dict[str, str]) -> None:
    created = _enqueue(node["node_id"])
    command_id = created.json()["data"]["command_id"]
    assert len(_poll(node).json()["messages"]) == 1

    response = client.post(
        f"{GATEWAY}/command-results",
        json={
            "node_id": node["node_id"],
            "command_id": command_id,
            "status": "SUCCEEDED",
            "exit_code": 0,
            "stdout": "device_id,vid,pid\nTCL003,1a86,55d4\n",
            "stderr": "",
            "truncated": False,
            "started_at": "2026-10-31T00:00:00Z",
            "finished_at": "2026-10-31T00:00:01Z",
        },
        headers=_bearer(node["token"]),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True}

    got = client.get(f"{NODES}/{node['node_id']}/commands/{command_id}", headers=ADMIN_HEADERS)
    data = got.json()["data"]
    assert data["status"] == "SUCCEEDED"
    assert data["exit_code"] == 0
    assert "TCL003" in data["stdout"]
    assert data["started_at"] is not None
    assert data["finished_at"] is not None


def test_command_result_for_unknown_command_is_not_found(
    node: dict[str, str],
) -> None:
    response = client.post(
        f"{GATEWAY}/command-results",
        json={
            "node_id": node["node_id"],
            "command_id": str(uuid.uuid4()),
            "status": "FAILED",
            "error_code": "TOOL_UNAVAILABLE",
        },
        headers=_bearer(node["token"]),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMMAND_NOT_FOUND"
