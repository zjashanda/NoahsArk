"""W1 database/seed tests.

These tests only run when DATABASE_URL (or apps/control_plane/.env) points at
PostgreSQL.  They never fall back to SQLite and skip cleanly when no database
is configured or reachable.
"""

from __future__ import annotations

import asyncio
import json
import os

import asyncpg
import pytest

from noahsark.config import settings
from noahsark.seed import (
    ATTEMPTS,
    EVIDENCE,
    RUNS,
    TASK,
    seed_database,
    stable_uuid,
)

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping W1 DB tests",
)

REQUIRED_TABLES = {
    "tasks",
    "task_revisions",
    "approvals",
    "gates",
    "cases",
    "runs",
    "attempts",
    "leases",
    "devices",
    "nodes",
    "evidence_items",
    "evidence_manifests",
    "verdicts",
    "reports",
    "knowledge_items",
    "knowledge_candidates",
    "audit_events",
    "idempotency_keys",
    "users",
    "roles",
}

EXPECTED_COUNTS = {
    "tasks": 2,
    "task_revisions": 5,
    "approvals": 1,
    "gates": 8,
    "cases": 5,
    "runs": 4,
    "attempts": 3,
    "leases": 3,
    "devices": 4,
    "nodes": 2,
    "evidence_items": 5,
    "evidence_manifests": 1,
    "reports": 2,
    "knowledge_items": 3,
    "knowledge_candidates": 4,
    "agents": 3,
    "reviews": 2,
    "audit_events": 5,
    "roles": 4,
    "users": 5,
    "settings": 12,
}


def _dsn() -> str:
    assert DATABASE_URL
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


def _run(coro):
    return asyncio.run(coro)


async def _fetch(query: str, *args):
    connection = await asyncpg.connect(_dsn())
    try:
        return await connection.fetch(query, *args)
    finally:
        await connection.close()


@pytest.fixture(scope="module")
def seeded_database():
    try:
        _run(_fetch("SELECT 1"))
    except (OSError, asyncpg.PostgresError) as exc:  # pragma: no cover - environment-specific
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")
    _run(seed_database(reset=True))
    _run(seed_database(reset=False))  # second run proves idempotency
    return True


def test_required_tables_exist(seeded_database):
    rows = _run(_fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
    tables = {row["tablename"] for row in rows}
    assert REQUIRED_TABLES <= tables, REQUIRED_TABLES - tables


def test_seed_counts_are_exact(seeded_database):
    for table, expected in EXPECTED_COUNTS.items():
        rows = _run(_fetch(f"SELECT count(*) AS count FROM {table}"))
        assert rows[0]["count"] == expected, f"{table}: {rows[0]['count']} != {expected}"


def test_seed_is_idempotent(seeded_database):
    before = {
        table: _run(_fetch(f"SELECT count(*) AS count FROM {table}"))[0]["count"]
        for table in EXPECTED_COUNTS
    }
    _run(seed_database(reset=False))
    after = {
        table: _run(_fetch(f"SELECT count(*) AS count FROM {table}"))[0]["count"]
        for table in EXPECTED_COUNTS
    }
    assert before == after


def test_deterministic_task_and_run_ids(seeded_database):
    task = _run(_fetch("SELECT task_id, display_id FROM tasks WHERE display_id = $1", "tsk-voice-001"))[0]
    assert task["task_id"] == TASK
    assert TASK == stable_uuid("task:tsk-voice-001")

    runs = _run(_fetch("SELECT run_id, display_id FROM runs ORDER BY display_id"))
    assert [row["display_id"] for row in runs] == ["run-031", "run-036", "run-039", "run-042"]
    assert {row["display_id"]: row["run_id"] for row in runs} == RUNS
    assert RUNS["run-042"] == stable_uuid("run:run-042")


def test_deterministic_evidence_and_attempt_ids(seeded_database):
    evidence = _run(_fetch("SELECT evidence_id, display_id, content_digest FROM evidence_items ORDER BY display_id"))
    assert {row["display_id"]: row["evidence_id"] for row in evidence} == EVIDENCE
    assert all(row["content_digest"] is None or row["content_digest"].startswith("sha256:") for row in evidence)
    verified = _run(_fetch("SELECT count(*) AS count FROM evidence_items WHERE verified"))
    assert verified[0]["count"] == 3

    attempts = _run(_fetch("SELECT attempt_id, display_id FROM attempts ORDER BY display_id"))
    assert {row["display_id"]: row["attempt_id"] for row in attempts} == ATTEMPTS


def test_audit_events_use_stable_string_ids(seeded_database):
    rows = _run(_fetch("SELECT event_id FROM audit_events ORDER BY event_id DESC"))
    assert [row["event_id"] for row in rows] == [
        "aud-20261029-041",
        "aud-20261029-040",
        "aud-20261029-039",
        "aud-20261029-038",
        "aud-20261029-037",
    ]


def test_five_axes_are_independent_columns(seeded_database):
    expected_axes = {
        "execution_status",
        "validity_status",
        "business_verdict",
        "evidence_status",
        "verification_status",
    }
    for table in ("runs", "attempts"):
        rows = _run(
            _fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = $1",
                table,
            )
        )
        columns = {row["column_name"] for row in rows}
        assert expected_axes <= columns, f"{table} missing axes: {expected_axes - columns}"
        assert "verdict" not in columns
        assert "verdict_boolean" not in columns


def test_release_three_preconditions_are_stored(seeded_database):
    row = _run(
        _fetch(
            "SELECT release_preconditions FROM leases WHERE display_id = $1",
            "lease-7781",
        )
    )[0]
    preconditions = row["release_preconditions"]
    if isinstance(preconditions, str):
        preconditions = json.loads(preconditions)
    assert set(preconditions) == {
        "local_stop_confirmed",
        "safe_cleanup_done",
        "occupancy_reconciled",
    }


def test_seeded_rows_are_marked_prototype(seeded_database):
    for table in ("tasks", "runs", "evidence_items", "audit_events"):
        rows = _run(
            _fetch(
                f"SELECT count(*) AS total, count(*) FILTER (WHERE source = 'prototype-fixture' AND seed) AS seeded FROM {table}"
            )
        )
        assert rows[0]["total"] == rows[0]["seeded"], table
