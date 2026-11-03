"""Node/device topology write tests.

The ADMIN gate and the OpenAPI surface are DB-free: the session dependency is
overridden with ``None`` so the capability check runs before any query.  The
CRUD tests are opt-in with ``NOAHSARK_DB_WRITE_TESTS=1`` because they write to
the configured PostgreSQL database; they create uniquely named rows and remove
only those rows in ``finally``.  They never seed, truncate or reset the DB.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from noahsark.config import settings
from noahsark.db import get_session
from noahsark.main import app

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

ADMIN = {"X-NoahsArk-Role": "ADMIN", "X-NoahsArk-Actor": "admin-01"}
DB_TESTS = os.environ.get("NOAHSARK_DB_WRITE_TESTS") == "1"


@pytest.fixture
def db_free_client() -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_session, None)


def _headers(role: str) -> dict[str, str]:
    return {"X-NoahsArk-Role": role, "X-NoahsArk-Actor": f"{role.lower()}-actor"}


WRITE_REQUESTS = [
    ("post", "/api/v1/nodes", {"display_id": "n", "hostname": "h", "agent_version": "v"}),
    ("patch", "/api/v1/nodes/nd-missing", {"hostname": "h"}),
    ("delete", "/api/v1/nodes/nd-missing", None),
    ("post", "/api/v1/devices", {"display_id": "d", "node_id": "nd-missing"}),
    ("patch", "/api/v1/devices/dv-missing", {"health_state": "HEALTHY"}),
    ("delete", "/api/v1/devices/dv-missing", None),
]


@pytest.mark.parametrize("role", ["OBSERVER", "APPROVER", "SESSION_MANAGER"])
@pytest.mark.parametrize(("method", "path", "body"), WRITE_REQUESTS)
def test_topology_writes_are_admin_only(db_free_client, role, method, path, body):
    response = db_free_client.request(method, path, json=body, headers=_headers(role))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_topology_write_schema_is_exposed():
    schema = TestClient(app).get("/openapi.json").json()
    paths = schema["paths"]
    assert set(paths["/api/v1/nodes"]) == {"post"}
    assert set(paths["/api/v1/nodes/{node_id}"]) == {"get", "patch", "delete"}
    assert set(paths["/api/v1/devices"]) == {"get", "post"}
    assert set(paths["/api/v1/devices/{device_id}"]) == {"get", "patch", "delete"}


def test_admin_body_validation_rejects_unknown_and_invalid_fields(db_free_client):
    unknown = db_free_client.post(
        "/api/v1/nodes",
        json={
            "display_id": "node-x",
            "hostname": "host",
            "agent_version": "1.0",
            "surprise": True,
        },
        headers=ADMIN,
    )
    assert unknown.status_code == 400
    invalid_state = db_free_client.post(
        "/api/v1/nodes",
        json={
            "display_id": "node-x",
            "hostname": "host",
            "agent_version": "1.0",
            "status": "BROKEN",
        },
        headers=ADMIN,
    )
    assert invalid_state.status_code == 400


db_required = pytest.mark.skipif(
    not DB_TESTS,
    reason="set NOAHSARK_DB_WRITE_TESTS=1 to run topology DB writes",
)


@db_required
def test_node_and_device_crud_round_trip():
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:10]
    node_display = f"node-test-{suffix}"
    device_display = f"dev-test-{suffix}"
    node_id: str | None = None
    device_id: str | None = None
    try:
        created_node = client.post(
            "/api/v1/nodes",
            json={
                "display_id": node_display,
                "hostname": f"HOST-{suffix}",
                "agent_version": "0.1.0-test",
                "communication_state": "ONLINE",
                "status": "ACTIVE",
            },
            headers=ADMIN,
        )
        assert created_node.status_code == 201, created_node.text
        node = created_node.json()["data"]
        node_id = node["node_id"]
        assert node["display_id"] == node_display

        duplicate = client.post(
            "/api/v1/nodes",
            json={
                "display_id": node_display,
                "hostname": "other",
                "agent_version": "0.1.0-test",
            },
            headers=ADMIN,
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "DISPLAY_ID_CONFLICT"

        missing_node = client.post(
            "/api/v1/devices",
            json={
                "display_id": f"dev-missing-{suffix}",
                "node_id": f"nd-missing-{suffix}",
            },
            headers=ADMIN,
        )
        assert missing_node.status_code == 404
        assert missing_node.json()["error"]["code"] == "NOT_FOUND"

        created_device = client.post(
            "/api/v1/devices",
            json={
                "display_id": device_display,
                "node_id": node_id,
                "firmware_version": "V038",
                "config_digest": "sha256:test",
                "adapter_version": "2.2.0",
                "pool_state": "READY",
                "health_state": "HEALTHY",
                "communication_state": "ONLINE",
            },
            headers=ADMIN,
        )
        assert created_device.status_code == 201, created_device.text
        device = created_device.json()["data"]
        device_id = device["device_id"]
        assert device["node_id"] == node_id

        duplicate_device = client.post(
            "/api/v1/devices",
            json={"display_id": device_display, "node_id": node_id},
            headers=ADMIN,
        )
        assert duplicate_device.status_code == 409

        patched_node = client.patch(
            f"/api/v1/nodes/{node_id}",
            json={"hostname": f"RENAMED-{suffix}", "status": "DRAINING"},
            headers=ADMIN,
        )
        assert patched_node.status_code == 200, patched_node.text
        assert patched_node.json()["data"]["hostname"] == f"RENAMED-{suffix}"
        assert patched_node.json()["data"]["status"] == "DRAINING"

        patched_device = client.patch(
            f"/api/v1/devices/{device_id}",
            json={"health_state": "DEGRADED", "occupancy_state": "OCCUPIED"},
            headers=ADMIN,
        )
        assert patched_device.status_code == 200, patched_device.text
        assert patched_device.json()["data"]["health_state"] == "DEGRADED"

        listed = client.get("/api/v1/devices", params={"limit": 200})
        assert listed.status_code == 200
        assert any(
            item["display_id"] == device_display for item in listed.json()["data"]["items"]
        )

        deleted_device = client.delete(f"/api/v1/devices/{device_id}", headers=ADMIN)
        assert deleted_device.status_code == 200, deleted_device.text
        assert deleted_device.json()["data"]["deleted"] is True
        device_id = None

        deleted_node = client.delete(f"/api/v1/nodes/{node_id}", headers=ADMIN)
        assert deleted_node.status_code == 200, deleted_node.text
        assert deleted_node.json()["data"]["deleted"] is True
        node_id = None

        assert client.get(f"/api/v1/nodes/{node_display}").status_code == 404
        assert client.get(f"/api/v1/devices/{device_display}").status_code == 404
    finally:
        if device_id is not None:
            client.delete(f"/api/v1/devices/{device_id}", headers=ADMIN)
        if node_id is not None:
            client.delete(f"/api/v1/nodes/{node_id}", headers=ADMIN)


@db_required
def test_delete_rejects_referenced_node_and_device():
    client = TestClient(app)
    node = client.delete("/api/v1/nodes/node-lab-win-01", headers=ADMIN)
    assert node.status_code == 409
    assert node.json()["error"]["code"] == "RESOURCE_IN_USE"
    device = client.delete("/api/v1/devices/dev-tcl-001", headers=ADMIN)
    assert device.status_code == 409
    assert device.json()["error"]["code"] == "RESOURCE_IN_USE"


@db_required
def test_created_node_emits_audit_event():
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:10]
    display = f"node-audit-{suffix}"
    correlation = f"topology-test-{suffix}"
    node_id: str | None = None
    try:
        response = client.post(
            "/api/v1/nodes",
            json={
                "display_id": display,
                "hostname": f"AUDIT-{suffix}",
                "agent_version": "0.1.0-test",
            },
            headers={**ADMIN, "X-Correlation-ID": correlation},
        )
        assert response.status_code == 201, response.text
        node_id = response.json()["data"]["node_id"]

        events = client.get("/api/v1/audit", params={"limit": 200}).json()["data"]["items"]
        match = [
            event
            for event in events
            if event["action"] == "NODE_CREATED"
            and event["object_id"] == display
            and event["correlation_id"] == correlation
        ]
        assert len(match) == 1, match
        assert match[0]["actor_role"] == "ADMIN"
    finally:
        if node_id is not None:
            client.delete(f"/api/v1/nodes/{node_id}", headers=ADMIN)
