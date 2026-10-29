"""Every UI route from ``design/ui-app/routes.json`` maps to a read endpoint.

``routes.json`` is a read-only reference owned by the UI track; this test never
writes it.  The mapping below is the contract between the 39 console screens and
the W2 read API.  ``IN-02`` is the new-intake compose screen: it has no dedicated
read endpoint and is backed by the intake draft collection (its submit path is a
W3 write).
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import asyncpg
import pytest
from fastapi.testclient import TestClient

from noahsark.config import settings
from noahsark.main import app
from noahsark.seed import seed_database

ROUTES_JSON = (
    Path(__file__).resolve().parents[3] / "design" / "ui-app" / "routes.json"
)

# route id -> (OpenAPI path template, concrete path with seeded identifiers)
UI_ROUTE_ENDPOINTS: dict[str, tuple[str, str]] = {
    "MC-01": ("/api/v1/mission", "/api/v1/mission"),
    "IN-01": ("/api/v1/intake/drafts", "/api/v1/intake/drafts"),
    "IN-02": ("/api/v1/intake/drafts", "/api/v1/intake/drafts"),
    "IN-03": ("/api/v1/intake/drafts/{draft_id}", "/api/v1/intake/drafts/drf-009"),
    "TK-01": ("/api/v1/tasks", "/api/v1/tasks"),
    "TK-02": (
        "/api/v1/tasks/{task_id}/overview",
        "/api/v1/tasks/tsk-voice-001/overview",
    ),
    "TK-03": (
        "/api/v1/tasks/{task_id}/revisions",
        "/api/v1/tasks/tsk-voice-001/revisions",
    ),
    "TK-04": (
        "/api/v1/tasks/{task_id}/plan",
        "/api/v1/tasks/tsk-voice-001/plan",
    ),
    "TK-05": (
        "/api/v1/tasks/{task_id}/runs",
        "/api/v1/tasks/tsk-voice-001/runs",
    ),
    "TK-06": (
        "/api/v1/tasks/{task_id}/evidence",
        "/api/v1/tasks/tsk-voice-001/evidence",
    ),
    "TK-07": (
        "/api/v1/tasks/{task_id}/verdict",
        "/api/v1/tasks/tsk-voice-001/verdict",
    ),
    "TK-08": (
        "/api/v1/tasks/{task_id}/live",
        "/api/v1/tasks/tsk-voice-001/live",
    ),
    "TK-09": (
        "/api/v1/tasks/{task_id}/knowledge",
        "/api/v1/tasks/tsk-voice-001/knowledge",
    ),
    "RN-01": ("/api/v1/runs", "/api/v1/runs"),
    "RN-02": ("/api/v1/runs/{run_id}", "/api/v1/runs/run-042"),
    "RN-03": (
        "/api/v1/runs/{run_id}/attempts/{attempt_id}",
        "/api/v1/runs/run-042/attempts/att-112",
    ),
    "EV-01": ("/api/v1/evidence", "/api/v1/evidence"),
    "EV-02": (
        "/api/v1/evidence/{evidence_id}",
        "/api/v1/evidence/ev-voice-trace-01",
    ),
    "EV-03": ("/api/v1/verdicts", "/api/v1/verdicts"),
    "DV-01": ("/api/v1/devices", "/api/v1/devices"),
    "DV-02": ("/api/v1/devices/{device_id}", "/api/v1/devices/dev-tcl-001"),
    "DV-03": ("/api/v1/nodes/{node_id}", "/api/v1/nodes/node-lab-win-01"),
    "RP-01": ("/api/v1/reports", "/api/v1/reports"),
    "RP-02": ("/api/v1/reports/{report_id}", "/api/v1/reports/rpt-voice-001"),
    "KN-01": ("/api/v1/knowledge", "/api/v1/knowledge"),
    "KN-02": (
        "/api/v1/knowledge/{knowledge_id}",
        "/api/v1/knowledge/kn-wake-false-trigger",
    ),
    "KN-03": ("/api/v1/knowledge/candidates", "/api/v1/knowledge/candidates"),
    "RT-01": ("/api/v1/runtime/models", "/api/v1/runtime/models"),
    "RT-02": ("/api/v1/runtime/toolchain", "/api/v1/runtime/toolchain"),
    "AG-01": ("/api/v1/agents", "/api/v1/agents"),
    "AG-02": ("/api/v1/agents/{agent_id}", "/api/v1/agents/agt-planner"),
    "AG-03": ("/api/v1/reviews", "/api/v1/reviews"),
    "AU-01": ("/api/v1/audit", "/api/v1/audit"),
    "AU-02": ("/api/v1/audit/{event_id}", "/api/v1/audit/aud-20261029-041"),
    "AU-03": ("/api/v1/recovery", "/api/v1/recovery"),
    "ST-01": ("/api/v1/settings", "/api/v1/settings"),
    "ST-02": ("/api/v1/settings/access", "/api/v1/settings/access"),
    "ST-03": (
        "/api/v1/settings/notifications",
        "/api/v1/settings/notifications",
    ),
    "ST-04": ("/api/v1/settings/retention", "/api/v1/settings/retention"),
}

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url


def _load_ui_routes() -> list[dict]:
    assert ROUTES_JSON.exists(), f"routes.json missing at {ROUTES_JSON}"
    payload = json.loads(ROUTES_JSON.read_text(encoding="utf-8"))
    return payload["routes"]


def test_routes_json_has_39_routes_and_mapping_covers_all():
    routes = _load_ui_routes()
    assert len(routes) == 39, f"expected 39 UI routes, found {len(routes)}"
    route_ids = {route["id"] for route in routes}
    assert route_ids == set(UI_ROUTE_ENDPOINTS), (
        f"unmapped={sorted(route_ids - set(UI_ROUTE_ENDPOINTS))} "
        f"extra={sorted(set(UI_ROUTE_ENDPOINTS) - route_ids)}"
    )


# W3 write templates that legitimately share a path with a UI read template.
# IN-01/IN-02 read the intake draft collection; creating a draft is a POST on
# the same path.  No other UI template may expose a non-GET method.
WRITE_POST_TEMPLATES = {
    "/api/v1/intake/drafts",
    "/api/v1/tasks/{task_id}/approvals",
    "/api/v1/runs/{run_id}/stop-requests",
    "/api/v1/devices/{device_id}/release-requests",
}


def test_every_ui_route_maps_to_a_get_read_endpoint():
    schema = TestClient(app).get("/openapi.json").json()
    paths = schema["paths"]
    for route_id, (template, _concrete) in UI_ROUTE_ENDPOINTS.items():
        assert template in paths, f"{route_id} template {template} is not served"
        operations = set(paths[template])
        assert "get" in operations, f"{route_id} {template} is not readable"
        extra = operations - {"get"}
        expected_extra = {"post"} if template in WRITE_POST_TEMPLATES else set()
        assert extra == expected_extra, (
            f"{route_id} {template} exposes {operations}"
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
    if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
        pytest.skip("DATABASE_URL is not configured for PostgreSQL")
    try:
        asyncio.run(_ping())
    except (OSError, asyncpg.PostgresError) as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")
    asyncio.run(seed_database(reset=True))
    return True


def test_every_ui_route_concrete_read_returns_200(seeded_database):
    client = TestClient(app)
    for route_id, (_template, concrete) in UI_ROUTE_ENDPOINTS.items():
        response = client.get(concrete)
        assert response.status_code == 200, f"{route_id} {concrete}: {response.text}"
        assert "data" in response.json(), route_id
