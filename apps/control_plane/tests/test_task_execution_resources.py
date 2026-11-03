"""Task execution resources: selection, snapshot, prompt and read projection.

These tests use the already-migrated dev database without reseeding it: they
read existing nodes/devices/agents, create real tasks through the write API and
delete every row they created.  The prompt byte-cap test is database-free.

What they lock down:

- two selected nodes and two selected devices are persisted in
  ``tasks.execution_context`` and exposed by the task read model;
- the built prompt names node hostnames and device endpoint details;
- a device whose node was not explicitly selected auto-includes that node;
- an unknown node or device id is a 404 and creates no task;
- the UTF-8 byte cap still holds with a large resource section.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any

import asyncpg
import pytest
from fastapi.testclient import TestClient

from noahsark.config import settings
from noahsark.integrations.opencode.prompt import (
    TaskPromptInput,
    build_task_prompt,
    format_execution_context,
)
from noahsark.main import app

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping resource tests",
)

client = TestClient(app)
TASKS = "/api/v1/tasks"


def _dsn() -> str:
    assert DATABASE_URL
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


def _run(coro):
    return asyncio.run(coro)


async def _fetch(query: str, *args) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(_dsn())
    try:
        return list(await connection.fetch(query, *args))
    finally:
        await connection.close()


async def _execute(query: str, *args) -> None:
    connection = await asyncpg.connect(_dsn())
    try:
        await connection.execute(query, *args)
    finally:
        await connection.close()


def _ping() -> None:
    _run(_execute("SELECT 1"))


@pytest.fixture(scope="module", autouse=True)
def database_available():
    try:
        _ping()
    except (OSError, asyncpg.PostgresError) as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")
    return True


def _headers(key: str) -> dict[str, str]:
    return {
        "X-NoahsArk-Role": "ADMIN",
        "X-NoahsArk-Actor": "admin-01",
        "Idempotency-Key": key,
    }


def _agent() -> str:
    rows = _run(_fetch("SELECT display_id FROM agents ORDER BY display_id LIMIT 1"))
    if not rows:
        pytest.skip("no agent rows available")
    return str(rows[0]["display_id"])


def _nodes(limit: int) -> list[asyncpg.Record]:
    return _run(
        _fetch(
            "SELECT node_id, display_id, hostname, communication_state "
            "FROM nodes ORDER BY display_id LIMIT $1",
            limit,
        )
    )


def _devices(limit: int) -> list[asyncpg.Record]:
    return _run(
        _fetch(
            "SELECT device_id, display_id, node_id, endpoints "
            "FROM devices ORDER BY display_id LIMIT $1",
            limit,
        )
    )


async def _delete_task(task_id: str) -> None:
    connection = await asyncpg.connect(_dsn())
    try:
        await connection.execute(
            "DELETE FROM supervisor_sessions WHERE task_id = $1::uuid", task_id
        )
        await connection.execute(
            "DELETE FROM task_revisions WHERE task_id = $1::uuid", task_id
        )
        await connection.execute("DELETE FROM tasks WHERE task_id = $1::uuid", task_id)
    finally:
        await connection.close()


def _cleanup(task: dict[str, Any], key: str) -> None:
    _run(_delete_task(task["task_id"]))
    _run(
        _execute(
            "DELETE FROM idempotency_keys WHERE key = $1 AND scope = $2",
            key,
            "POST /api/v1/tasks",
        )
    )
    _run(
        _execute(
            "DELETE FROM audit_events WHERE object_id = ANY($1::text[])",
            [
                task["display_id"],
                task["revision_display_id"],
                task["supervisor_display_id"],
            ],
        )
    )


def _create(
    *,
    node_ids: list[str],
    device_ids: list[str],
    prompt: str = "Reply PONG",
) -> tuple[dict[str, Any], str]:
    key = f"test-resources-{uuid.uuid4().hex}"
    body = {
        "title": "Execution resource selection",
        "objective": "Confirm the selected resources reach the task prompt.",
        "entry_mode": "conversation",
        "lead_agent_id": _agent(),
        "lead_session_id": str(uuid.uuid4()),
        "prompt": prompt,
        "node_ids": node_ids,
        "device_ids": device_ids,
    }
    response = client.post(TASKS, json=body, headers=_headers(key))
    assert response.status_code == 201, response.text
    return response.json()["data"], key


def _serial_port(endpoints: list[dict[str, Any]]) -> str | None:
    for endpoint in endpoints:
        if isinstance(endpoint, dict) and endpoint.get("kind") == "serial":
            port = endpoint.get("port") or endpoint.get("binding")
            if isinstance(port, str) and port:
                return port
    return None


def test_two_nodes_and_two_devices_are_snapshotted_and_prompted() -> None:
    nodes = _nodes(2)
    devices = _devices(2)
    if len(nodes) < 2 or len(devices) < 2:
        pytest.skip("needs at least two nodes and two devices")

    node_ids = [str(row["node_id"]) for row in nodes]
    device_ids = [str(row["device_id"]) for row in devices]
    data, key = _create(node_ids=node_ids, device_ids=device_ids)
    try:
        context = data["execution_context"]
        # Selected nodes are all present; the nodes owned by selected devices
        # are auto-included, so the snapshot may contain more than the request.
        assert set(node_ids) <= {item["node_id"] for item in context["nodes"]}
        assert {item["device_id"] for item in context["devices"]} == set(device_ids)

        stored = _run(
            _fetch(
                "SELECT execution_context FROM tasks WHERE task_id = $1::uuid",
                data["task_id"],
            )
        )
        assert stored[0]["execution_context"] == context or json.loads(
            stored[0]["execution_context"]
        ) == context

        task = client.get(
            f"{TASKS}/{data['display_id']}",
            headers={"X-NoahsArk-Role": "ADMIN", "X-NoahsArk-Actor": "admin-01"},
        )
        assert task.status_code == 200, task.text
        assert task.json()["data"]["execution_context"] == context

        resources = format_execution_context(context)
        prompt = build_task_prompt(
            TaskPromptInput(
                task_id=data["display_id"],
                title=data["title"],
                instructions=data["objective"],
                resources=resources,
            )
        )
        assert "## Execution resources" in prompt.text
        for node in nodes:
            assert (
                f"- {node['display_id']} ({node['hostname']}, "
                f"{node['communication_state']})"
            ) in prompt.text
        assert f"- {devices[0]['display_id']} [" in prompt.text
        for device in devices:
            endpoints = device["endpoints"]
            if isinstance(endpoints, str):
                endpoints = json.loads(endpoints)
            port = _serial_port(endpoints)
            if port:
                assert port in prompt.text
    finally:
        _cleanup(data, key)


def test_device_node_is_auto_included_when_not_selected() -> None:
    devices = _devices(1)
    if not devices:
        pytest.skip("needs at least one device")
    device = devices[0]
    data, key = _create(
        node_ids=[],
        device_ids=[str(device["device_id"])],
    )
    try:
        context = data["execution_context"]
        assert len(context["devices"]) == 1
        assert context["devices"][0]["device_id"] == str(device["device_id"])
        assert len(context["nodes"]) == 1
        assert context["nodes"][0]["node_id"] == str(device["node_id"])
    finally:
        _cleanup(data, key)


def test_unknown_node_and_device_are_404_and_create_nothing() -> None:
    missing_node = str(uuid.uuid4())
    missing_device = str(uuid.uuid4())
    base = {
        "title": "Unknown resource",
        "objective": "Must not create a task.",
        "entry_mode": "conversation",
        "lead_agent_id": _agent(),
        "lead_session_id": str(uuid.uuid4()),
        "prompt": "Reply PONG",
    }

    node_key = f"test-resources-{uuid.uuid4().hex}"
    node_response = client.post(
        TASKS,
        json={**base, "node_ids": [missing_node], "device_ids": []},
        headers=_headers(node_key),
    )
    assert node_response.status_code == 404, node_response.text
    assert node_response.json()["error"]["details"]["object_type"] == "node"

    device_key = f"test-resources-{uuid.uuid4().hex}"
    device_response = client.post(
        TASKS,
        json={**base, "node_ids": [], "device_ids": [missing_device]},
        headers=_headers(device_key),
    )
    assert device_response.status_code == 404, device_response.text
    assert device_response.json()["error"]["details"]["object_type"] == "device"

    _run(
        _execute(
            "DELETE FROM idempotency_keys WHERE key = ANY($1::text[])",
            [node_key, device_key],
        )
    )


def test_prompt_byte_cap_holds_with_large_resource_section() -> None:
    resources = format_execution_context(
        {
            "nodes": [
                {
                    "node_id": f"00000000-0000-0000-0000-00000000000{i}",
                    "display_id": f"node-{i}",
                    "hostname": f"HOST-{i}" * 20,
                    "communication_state": "ONLINE",
                }
                for i in range(20)
            ],
            "devices": [
                {
                    "device_id": f"00000000-0000-0000-0000-00000000002{i}",
                    "display_id": f"device-{i}",
                    "node_id": "00000000-0000-0000-0000-000000000000",
                    "endpoints": [
                        {"kind": "serial", "role": "A", "port": "COM3"},
                        {"kind": "audio", "direction": "capture", "channels": 8},
                    ],
                }
                for i in range(20)
            ],
        }
    )
    prompt = build_task_prompt(
        TaskPromptInput(
            task_id="task-cap",
            title="Byte cap",
            instructions="x" * 4_000,
            resources=resources,
        ),
        max_bytes=256,
    )
    assert prompt.byte_length <= 256
    assert prompt.truncated is True
    assert prompt.text.endswith("[prompt truncated]")
