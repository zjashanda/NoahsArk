"""W8 Wave 2 task 3: DB-backed intake/approval bridge into the gate projection.

This is L2 simulated integration: it drives the real control-plane ``TestClient``
against the seeded PostgreSQL database, then feeds the real gate rows returned by
the read projection into the pure ``gate_sequence`` guard.  It makes no
real-device, production, RPO or RTO claim.

The suite skips only when PostgreSQL is not configured or not reachable; an
application failure is never converted into a skip.
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
from noahsark.services.domain_rules import GATE_ORDER, gate_can_enter, gate_sequence

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping W8 write bridge",
)

client = TestClient(app)

INTAKE = "/api/v1/intake/drafts"
APPROVAL = "/api/v1/tasks/tsk-voice-001/approvals"
OVERVIEW = "/api/v1/tasks/tsk-voice-001/overview"

FROZEN_REVISION = "rev-001"
FROZEN_DIGEST = digest("revision:rev-001")

ENTRY_MODES = (
    ("conversation", {"kind": "conversation", "ref": "thread-w8-01"}),
    ("file", {"kind": "file", "ref": "spec-w8.pdf"}),
    ("spreadsheet", {"kind": "spreadsheet", "ref": "matrix-w8.xlsx"}),
)


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


def _key(prefix: str) -> str:
    return f"test-w8-{prefix}-{uuid.uuid4().hex}"


def _headers(role: str, actor: str | None = None, key: str | None = None) -> dict:
    headers = {"X-NoahsArk-Role": role}
    if actor is not None:
        headers["X-NoahsArk-Actor"] = actor
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _intake_body(entry_mode: str, source: dict) -> dict:
    return {
        "title": f"W8 {entry_mode} intake draft",
        "entry_mode": entry_mode,
        "summary": f"Operator supplied {entry_mode} context for a new task.",
        "sources": [source],
        "facts": [{"statement": f"{entry_mode} source normalized once"}],
        "conflicts": [],
        "gaps": [],
        "freshness": {"captured_at": "2026-10-30T09:00:00Z"},
    }


def _approval_body() -> dict:
    return {
        "decision": "APPROVED",
        "comment": "Scope reviewed against the frozen revision digest.",
        "revision_content_digest": FROZEN_DIGEST,
        "scope_snapshot": {"task": "tsk-voice-001", "revision": FROZEN_REVISION},
        "revision_id": FROZEN_REVISION,
    }


def _gates_with_status(
    gates: list[dict], statuses: dict[str, str]
) -> list[dict]:
    """Copy the real gate rows and apply a controlled status per gate code."""

    by_code = {gate["gate_code"]: dict(gate) for gate in gates}
    rows: list[dict] = []
    for code in GATE_ORDER:
        row = by_code[code]
        row["status"] = statuses.get(code, "PENDING")
        row["blockers"] = []
        rows.append(row)
    return rows


def _blocker_codes(blockers: list[dict]) -> list[str]:
    return [str(blocker["code"]) for blocker in blockers]


# ---------------------------------------------------------------------------
# Three intake entry modes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("entry_mode,source", ENTRY_MODES)
def test_each_entry_mode_creates_a_persisted_draft(
    seeded_database, entry_mode: str, source: dict
) -> None:
    response = client.post(
        INTAKE,
        json=_intake_body(entry_mode, source),
        headers=_headers("ADMIN", "admin-01", _key(f"intake-{entry_mode}")),
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["created"] is True
    assert data["entry_mode"] == entry_mode
    assert data["stage"] == "DRAFT"
    assert data["owner_role"] == "ADMIN"
    assert data["source_count"] == 1
    assert data["conflict_count"] == 0
    assert data["gap_count"] == 0

    read = client.get(
        f"{INTAKE}/{data['display_id']}",
        headers=_headers("OBSERVER", "observer-01"),
    )
    assert read.status_code == 200, read.text
    persisted = read.json()["data"]
    assert persisted["entry_mode"] == entry_mode
    assert persisted["stage"] == "DRAFT"
    assert persisted["sources"] == [source]


# ---------------------------------------------------------------------------
# Approval -> G1 -> G2 bridge
# ---------------------------------------------------------------------------
def test_approval_bridge_enables_g2_only_after_g1_passes(seeded_database) -> None:
    # Keep re-runs independent: the schema allows one APPROVED approval per
    # revision, and the module reset makes the prior row stale only on a replay.
    _run(
        _execute(
            "DELETE FROM approvals WHERE revision_id = "
            "(SELECT revision_id FROM task_revisions WHERE display_id = $1)",
            FROZEN_REVISION,
        )
    )

    response = client.post(
        APPROVAL,
        json=_approval_body(),
        headers=_headers("APPROVER", "approver-02", _key("approval")),
    )
    assert response.status_code == 201, response.text
    approval = response.json()["data"]
    assert approval["created"] is True
    assert approval["decision"] == "APPROVED"
    assert approval["task_display_id"] == "tsk-voice-001"
    assert approval["revision_display_id"] == FROZEN_REVISION
    assert approval["revision_content_digest"] == FROZEN_DIGEST

    persisted = _run(
        _fetchval(
            "SELECT a.decision FROM approvals a "
            "JOIN task_revisions r ON r.revision_id = a.revision_id "
            "WHERE r.display_id = $1 ORDER BY a.decided_at DESC LIMIT 1",
            FROZEN_REVISION,
        )
    )
    assert persisted == "APPROVED"

    overview = client.get(
        OVERVIEW, headers=_headers("OBSERVER", "observer-01")
    ).json()["data"]
    seeded_gates = overview["gates"]
    assert [gate["gate_code"] for gate in seeded_gates] == list(GATE_ORDER)

    closed_statuses = {code: "PENDING" for code in GATE_ORDER}
    closed_statuses["G0"] = "PASSED"
    closed_statuses["G2"] = "PASSED"
    closed_gates = _gates_with_status(seeded_gates, closed_statuses)
    closed_g2 = {
        gate["gate_code"]: gate for gate in gate_sequence(closed_gates)["gates"]
    }["G2"]
    assert closed_g2["sequence_valid"] is False
    assert _blocker_codes(closed_g2["blockers"]) == [
        "GATE_PREDECESSOR_NOT_PASSED"
    ]
    assert "G1" in closed_g2["blockers"][0]["message"]

    approved_status = "PASSED" if approval["decision"] == "APPROVED" else "FAILED"
    open_statuses = dict(closed_statuses)
    open_statuses["G1"] = approved_status
    open_gates = _gates_with_status(seeded_gates, open_statuses)
    open_projection = gate_sequence(open_gates)
    open_g2 = {gate["gate_code"]: gate for gate in open_projection["gates"]}["G2"]
    assert open_g2["sequence_valid"] is True
    assert open_g2["blockers"] == []
    assert open_projection["blocked"] is False
    assert open_projection["gates_are_business_pass"] is False

    allowed, blockers = gate_can_enter("G2", open_gates)
    assert allowed is True
    assert blockers == []


def test_g2_stays_fail_closed_while_g1_is_missing(seeded_database) -> None:
    overview = client.get(
        OVERVIEW, headers=_headers("OBSERVER", "observer-01")
    ).json()["data"]

    statuses = {code: "PENDING" for code in GATE_ORDER}
    statuses["G0"] = "PASSED"
    statuses["G2"] = "PASSED"
    gates = _gates_with_status(overview["gates"], statuses)

    projection = gate_sequence(gates)
    g2 = {gate["gate_code"]: gate for gate in projection["gates"]}["G2"]
    assert g2["sequence_valid"] is False
    assert _blocker_codes(g2["blockers"]) == ["GATE_PREDECESSOR_NOT_PASSED"]
    assert "G1" in g2["blockers"][0]["message"]

    allowed, blockers = gate_can_enter("G2", gates)
    assert allowed is False
    assert _blocker_codes(blockers) == ["GATE_PREDECESSOR_NOT_PASSED"]
