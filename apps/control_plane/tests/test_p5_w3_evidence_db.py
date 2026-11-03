"""P5-W3 evidence orchestration against the seeded PostgreSQL authority.

Unit tests cover the byte store; these tests cover the database side that
cannot be faked honestly:

- receive -> verify transitions and their audit events;
- corrupt/missing blobs fail closed;
- raw evidence reads append ALLOW and DENY access events, including unknown
  roles;
- retention dry-run is non-destructive, holds are skipped, and only an explicit
  ADMIN purge removes eligible blobs while retaining metadata and audit;
- the manifest summary exposes relative storage keys and never an absolute
  path.

The suite skips cleanly when PostgreSQL is not configured or unreachable.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from noahsark.config import settings
from noahsark.errors import ApiError
from noahsark.models import EvidenceItem
from noahsark.seed import seed_database
from noahsark.services import audit
from noahsark.services.evidence_storage import (
    RETENTION_CONFIRM_PHRASE,
    ContentAddressedStorage,
    attach_evidence_blob,
    digest_bytes,
    execute_retention_cleanup,
    manifest_summary,
    read_raw_evidence,
    resolve_evidence_item,
    retention_dry_run,
    verify_evidence_blob,
)

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping W3 evidence DB tests",
)

SessionFactory = async_sessionmaker[AsyncSession]


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
def seeded_database() -> bool:
    try:
        asyncio.run(_ping())
    except (OSError, asyncpg.PostgresError) as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")
    asyncio.run(seed_database(reset=True))
    return True


@asynccontextmanager
async def _database() -> AsyncIterator[SessionFactory]:
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def _display(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _evidence(
    display_id: str,
    *,
    created_at: datetime | None = None,
    state: str = "declared",
    content_digest: str | None = None,
    retention: dict | None = None,
    received: bool = False,
    verified: bool = False,
    expected: bool = True,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=uuid.uuid4(),
        display_id=display_id,
        evidence_class="execution_log",
        role="required",
        state=state,
        content_digest=content_digest,
        size_bytes=None,
        media_type="application/octet-stream",
        digest_scope="raw_bytes" if content_digest else None,
        provenance={"producer": "pytest", "trust_level": "test"},
        upload=None,
        locator=None,
        retention=retention or {"class": "task_scoped", "archive_state": "pending"},
        access_level="summary",
        classification=None,
        integrity=None,
        log_read=None,
        related_event_ids=[],
        supersedes=None,
        notes=None,
        expected=expected,
        received=received,
        verified=verified,
        created_at=created_at or datetime.now(UTC),
    )


def _assert_api_error(exc_info: pytest.ExceptionInfo[ApiError], status: int, code: str) -> None:
    assert exc_info.value.status_code == status
    assert exc_info.value.code == code


def _actions(events: list) -> list[str]:
    return [event.action for event in events]


# ---------------------------------------------------------------------------
# Receive / verify
# ---------------------------------------------------------------------------
def test_receive_then_verify_is_audited_and_never_collapsed(tmp_path) -> None:
    async def scenario() -> None:
        async with _database() as factory, factory() as session:
            item = _evidence(_display("ev-w3-receive"), state="declared")
            session.add(item)
            await session.commit()
            evidence_id = item.evidence_id
            store = ContentAddressedStorage(tmp_path / "store")
            receive_correlation = f"w3-receive-{uuid.uuid4().hex}"

            payload = await attach_evidence_blob(
                session,
                item,
                b"raw evidence bytes",
                storage=store,
                actor_role="ADMIN",
                actor_id=None,
                correlation_id=receive_correlation,
                path="/api/v1/evidence/w3/content",
            )
            await session.commit()

            assert payload["received"] is True
            assert payload["verified"] is False
            assert payload["received_is_not_verified"] is True
            row = await session.get(EvidenceItem, evidence_id)
            assert row is not None
            assert row.state == "complete"
            assert row.received is True
            assert row.verified is False
            assert row.content_digest == digest_bytes(b"raw evidence bytes")
            assert row.integrity["digest_verified"] is False
            receive_events = await audit.load_events(
                session, correlation_prefix=receive_correlation
            )
            assert _actions(receive_events) == ["EVIDENCE_RECEIVED"]
            assert receive_events[0].after["received"] is True
            assert receive_events[0].after["verified"] is False

            # Re-receiving identical bytes is idempotent and stays unverified.
            again = await attach_evidence_blob(
                session,
                row,
                b"raw evidence bytes",
                storage=store,
                actor_role="ADMIN",
                actor_id=None,
                correlation_id=f"w3-receive-again-{uuid.uuid4().hex}",
                path="/api/v1/evidence/w3/content",
            )
            await session.commit()
            assert again["state"] == "complete"
            assert again["verified"] is False

            # Different bytes are never accepted for the same evidence item.
            with pytest.raises(ApiError) as exc_info:
                await attach_evidence_blob(
                    session,
                    row,
                    b"different bytes",
                    storage=store,
                    actor_role="ADMIN",
                    actor_id=None,
                    correlation_id=f"w3-overwrite-{uuid.uuid4().hex}",
                    path="/api/v1/evidence/w3/content",
                )
            _assert_api_error(exc_info, 409, "EVIDENCE_IMMUTABLE")
            await session.rollback()

            row = await session.get(EvidenceItem, evidence_id)
            assert row is not None
            verify_correlation = f"w3-verify-{uuid.uuid4().hex}"
            verify_payload, integrity = await verify_evidence_blob(
                session,
                row,
                storage=store,
                actor_role="ADMIN",
                actor_id=None,
                correlation_id=verify_correlation,
                path="/api/v1/evidence/w3/verify",
            )
            await session.commit()

            assert integrity.ok is True
            assert verify_payload["verified"] is True
            assert verify_payload["received_is_not_verified"] is False
            row = await session.get(EvidenceItem, evidence_id)
            assert row is not None
            assert row.state == "verified"
            assert row.verified is True
            assert row.integrity["integrity_status"] == "OK"

            verify_events = await audit.load_events(
                session, correlation_prefix=verify_correlation
            )
            assert _actions(verify_events) == ["EVIDENCE_VERIFIED"]
            assert verify_events[0].after["verified"] is True

            await session.delete(row)
            await session.commit()

    asyncio.run(scenario())


def test_corrupt_and_missing_blobs_fail_closed_with_audit(tmp_path) -> None:
    async def scenario() -> None:
        async with _database() as factory, factory() as session:
            store = ContentAddressedStorage(tmp_path / "store")
            item = _evidence(_display("ev-w3-corrupt"))
            session.add(item)
            await session.commit()
            evidence_id = item.evidence_id
            payload = await attach_evidence_blob(
                session,
                item,
                b"bytes to corrupt",
                storage=store,
                actor_role="ADMIN",
                actor_id=None,
                correlation_id=f"w3-corrupt-receive-{uuid.uuid4().hex}",
                path="/api/v1/evidence/w3/content",
            )
            await session.commit()
            digest = payload["digest"]
            store.path_for(digest).write_bytes(b"tampered")

            row = await session.get(EvidenceItem, evidence_id)
            assert row is not None
            corrupt_correlation = f"w3-corrupt-{uuid.uuid4().hex}"
            verify_payload, integrity = await verify_evidence_blob(
                session,
                row,
                storage=store,
                actor_role="ADMIN",
                actor_id=None,
                correlation_id=corrupt_correlation,
                path="/api/v1/evidence/w3/verify",
            )
            await session.commit()

            assert integrity.ok is False
            assert verify_payload["verified"] is False
            assert verify_payload["state"] == "conflicted"
            row = await session.get(EvidenceItem, evidence_id)
            assert row is not None
            assert row.state == "conflicted"
            assert row.verified is False
            events = await audit.load_events(
                session, correlation_prefix=corrupt_correlation
            )
            assert _actions(events) == ["EVIDENCE_INTEGRITY_FAILED"]
            assert events[0].after["integrity_status"] == "DIGEST_MISMATCH"

            with pytest.raises(ApiError) as exc_info:
                await read_raw_evidence(
                    session,
                    row,
                    storage=store,
                    actor_role="ADMIN",
                    actor_id=None,
                    correlation_id=f"w3-corrupt-read-{uuid.uuid4().hex}",
                    path="/api/v1/evidence/w3/content",
                )
            _assert_api_error(exc_info, 409, "EVIDENCE_INTEGRITY_FAILURE")

            store.delete_blob(digest)
            with pytest.raises(ApiError) as exc_info:
                await read_raw_evidence(
                    session,
                    row,
                    storage=store,
                    actor_role="ADMIN",
                    actor_id=None,
                    correlation_id=f"w3-missing-read-{uuid.uuid4().hex}",
                    path="/api/v1/evidence/w3/content",
                )
            _assert_api_error(exc_info, 404, "NOT_FOUND")

            await session.rollback()
            row = await session.get(EvidenceItem, evidence_id)
            assert row is not None
            await session.delete(row)
            await session.commit()

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Access audit
# ---------------------------------------------------------------------------
def test_raw_access_allows_and_denies_with_audit(tmp_path) -> None:
    async def scenario() -> None:
        async with _database() as factory, factory() as session:
            store = ContentAddressedStorage(tmp_path / "store")
            item = _evidence(_display("ev-w3-access"))
            session.add(item)
            await session.commit()
            evidence_id = item.evidence_id
            received = await attach_evidence_blob(
                session,
                item,
                b"raw access bytes",
                storage=store,
                actor_role="ADMIN",
                actor_id=None,
                correlation_id=f"w3-access-receive-{uuid.uuid4().hex}",
                path="/api/v1/evidence/w3/content",
            )
            await session.commit()
            assert received["received"] is True

            row = await session.get(EvidenceItem, evidence_id)
            assert row is not None
            allow_correlation = f"w3-access-allow-{uuid.uuid4().hex}"
            data, integrity = await read_raw_evidence(
                session,
                row,
                storage=store,
                actor_role="ADMIN",
                actor_id=None,
                correlation_id=allow_correlation,
                path="/api/v1/evidence/w3/content",
            )
            await session.commit()
            assert data == b"raw access bytes"
            assert integrity.ok is True
            allow_events = await audit.load_events(
                session, correlation_prefix=allow_correlation
            )
            assert _actions(allow_events) == ["EVIDENCE_RAW_ACCESS"]
            assert allow_events[0].access_decision == "ALLOW"
            assert allow_events[0].result == "SUCCESS"
            assert allow_events[0].after["raw_content_read"] is True

            deny_correlation = f"w3-access-deny-{uuid.uuid4().hex}"
            with pytest.raises(ApiError) as exc_info:
                await read_raw_evidence(
                    session,
                    row,
                    storage=store,
                    actor_role="OBSERVER",
                    actor_id=None,
                    correlation_id=deny_correlation,
                    path="/api/v1/evidence/w3/content",
                )
            _assert_api_error(exc_info, 403, "FORBIDDEN")
            await session.commit()
            deny_events = await audit.load_events(
                session, correlation_prefix=deny_correlation
            )
            assert _actions(deny_events) == ["EVIDENCE_RAW_ACCESS"]
            assert deny_events[0].access_decision == "DENY"
            assert deny_events[0].result == "DENIED"
            assert deny_events[0].after["raw_content_read"] is False

            unknown_correlation = f"w3-access-unknown-{uuid.uuid4().hex}"
            with pytest.raises(ApiError) as exc_info:
                await read_raw_evidence(
                    session,
                    row,
                    storage=store,
                    actor_role="NOT_A_ROLE",
                    actor_id=None,
                    correlation_id=unknown_correlation,
                    path="/api/v1/evidence/w3/content",
                )
            _assert_api_error(exc_info, 403, "FORBIDDEN")
            await session.commit()
            unknown_events = await audit.load_events(
                session, correlation_prefix=unknown_correlation
            )
            assert _actions(unknown_events) == ["EVIDENCE_RAW_ACCESS"]
            assert unknown_events[0].access_decision == "DENY"

            row = await session.get(EvidenceItem, evidence_id)
            assert row is not None
            await session.delete(row)
            await session.commit()

    asyncio.run(scenario())


def test_digest_mismatch_on_receive_does_not_mutate_or_audit(tmp_path) -> None:
    async def scenario() -> None:
        async with _database() as factory, factory() as session:
            item = _evidence(_display("ev-w3-mismatch"))
            session.add(item)
            await session.commit()
            evidence_id = item.evidence_id
            store = ContentAddressedStorage(tmp_path / "store")
            correlation = f"w3-mismatch-{uuid.uuid4().hex}"
            declared = digest_bytes(b"declared bytes that do not match")

            with pytest.raises(ApiError) as exc_info:
                await attach_evidence_blob(
                    session,
                    item,
                    b"actual bytes",
                    storage=store,
                    expected_digest=declared,
                    actor_role="ADMIN",
                    actor_id=None,
                    correlation_id=correlation,
                    path="/api/v1/evidence/w3/content",
                )
            _assert_api_error(exc_info, 400, "EVIDENCE_DIGEST_MISMATCH")
            await session.rollback()

            row = await session.get(EvidenceItem, evidence_id)
            assert row is not None
            assert row.received is False
            assert row.verified is False
            assert row.content_digest is None
            assert await audit.load_events(session, correlation_prefix=correlation) == []

            await session.delete(row)
            await session.commit()

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------
def test_retention_dry_run_then_admin_purge_keeps_metadata_and_audit(tmp_path) -> None:
    async def scenario() -> None:
        async with _database() as factory, factory() as session:
            store = ContentAddressedStorage(tmp_path / "store")
            now = datetime(2026, 10, 30, tzinfo=UTC)
            old = now - timedelta(days=60)
            recent = now - timedelta(days=1)

            eligible = _evidence(
                _display("ev-w3-ret-eligible"),
                created_at=old,
                state="verified",
                received=True,
                verified=True,
            )
            held = _evidence(
                _display("ev-w3-ret-held"),
                created_at=old,
                state="verified",
                received=True,
                verified=True,
                retention={"class": "legal_hold", "archive_state": "hold"},
            )
            recent_item = _evidence(
                _display("ev-w3-ret-recent"),
                created_at=recent,
                state="verified",
                received=True,
                verified=True,
            )
            missing = _evidence(
                _display("ev-w3-ret-missing"),
                created_at=old,
                state="complete",
                received=True,
                verified=False,
            )
            corrupt = _evidence(
                _display("ev-w3-ret-corrupt"),
                created_at=old,
                state="complete",
                received=True,
                verified=False,
            )
            for row in (eligible, held, recent_item, missing, corrupt):
                session.add(row)
            await session.commit()

            for row, data in (
                (eligible, b"eligible bytes"),
                (held, b"held bytes"),
                (recent_item, b"recent bytes"),
                (missing, b"missing bytes"),
                (corrupt, b"corrupt bytes"),
            ):
                blob = store.put_blob(data)
                row.content_digest = blob.digest
                row.size_bytes = blob.size_bytes
                row.state = row.state if row.state in ("verified", "complete") else "complete"
            await session.commit()
            eligible_id = eligible.evidence_id
            eligible_digest = eligible.content_digest
            held_id = held.evidence_id
            held_digest = held.content_digest
            missing_id = missing.evidence_id
            missing_digest = missing.content_digest
            corrupt_id = corrupt.evidence_id
            corrupt_digest = corrupt.content_digest
            recent_id = recent_item.evidence_id
            store.delete_blob(missing_digest)
            store.path_for(corrupt_digest).write_bytes(b"tampered")

            plan = await retention_dry_run(
                session, storage=store, now=now, limit=500
            )
            candidate_ids = {row["display_id"] for row in plan["candidates"]}
            assert eligible.display_id in candidate_ids
            assert missing.display_id in candidate_ids
            assert corrupt.display_id in candidate_ids
            assert held.display_id not in candidate_ids
            assert recent_item.display_id not in candidate_ids
            skipped = {row["display_id"]: row["reason"] for row in plan["skipped"]}
            assert skipped[held.display_id] == "retention_hold"
            assert skipped[recent_item.display_id] == "within_retention_window"
            assert plan["dry_run"] is True
            assert plan["deleted_count"] == 0
            assert store.has_blob(eligible_digest) is True

            with pytest.raises(ApiError) as exc_info:
                await execute_retention_cleanup(
                    session,
                    dry_run=False,
                    confirm=RETENTION_CONFIRM_PHRASE,
                    principal_role="OBSERVER",
                    actor_id=None,
                    correlation_id=f"w3-ret-nonadmin-{uuid.uuid4().hex}",
                    path="/api/v1/settings/retention/cleanup",
                    storage=store,
                    now=now,
                )
            _assert_api_error(exc_info, 403, "FORBIDDEN")
            await session.rollback()
            assert store.has_blob(eligible_digest) is True

            with pytest.raises(ApiError) as exc_info:
                await execute_retention_cleanup(
                    session,
                    dry_run=False,
                    confirm="WRONG",
                    principal_role="ADMIN",
                    actor_id=None,
                    correlation_id=f"w3-ret-confirm-{uuid.uuid4().hex}",
                    path="/api/v1/settings/retention/cleanup",
                    storage=store,
                    now=now,
                )
            _assert_api_error(exc_info, 400, "VALIDATION_ERROR")
            await session.rollback()
            assert store.has_blob(eligible_digest) is True

            purge_correlation = f"w3-ret-purge-{uuid.uuid4().hex}"
            result = await execute_retention_cleanup(
                session,
                dry_run=False,
                confirm=RETENTION_CONFIRM_PHRASE,
                principal_role="ADMIN",
                actor_id=None,
                correlation_id=purge_correlation,
                path="/api/v1/settings/retention/cleanup",
                storage=store,
                now=now,
            )
            await session.commit()

            purged_ids = {row["display_id"] for row in result["purged"]}
            assert eligible.display_id in purged_ids
            assert held.display_id not in purged_ids
            assert missing.display_id not in purged_ids
            assert corrupt.display_id not in purged_ids
            assert result["destructive"] is True
            assert result["deleted_count"] >= 1
            assert store.has_blob(eligible_digest) is False
            assert store.has_blob(held_digest) is True

            row = await session.get(EvidenceItem, eligible_id)
            assert row is not None
            assert row.retention["archive_state"] == "purged"
            assert row.content_digest == eligible_digest

            purge_events = await audit.load_events(
                session, correlation_prefix=purge_correlation
            )
            assert "EVIDENCE_RETENTION_PURGED" in _actions(purge_events)
            purge_event = next(
                event
                for event in purge_events
                if event.action == "EVIDENCE_RETENTION_PURGED"
                and event.object_id == eligible.display_id
            )
            assert purge_event.after["metadata_retained"] is True
            assert purge_event.after["audit_retained"] is True

            for evidence_id in (
                eligible_id,
                held_id,
                recent_id,
                missing_id,
                corrupt_id,
            ):
                fresh = await session.get(EvidenceItem, evidence_id)
                if fresh is not None:
                    await session.delete(fresh)
            await session.commit()

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Manifest / path leakage
# ---------------------------------------------------------------------------
def test_manifest_summary_uses_relative_keys_only(tmp_path) -> None:
    async def scenario() -> None:
        async with _database() as factory, factory() as session:
            item = await resolve_evidence_item(session, "ev-voice-trace-01")
            store = ContentAddressedStorage(tmp_path / "empty-store")

            summary = await manifest_summary(session, item, storage=store)

            assert summary["manifest"]["display_id"] == "man-run-042"
            assert summary["counts"] == summary["manifest_counts"]
            assert summary["counts"]["expected"] == 5
            assert summary["counts"]["received"] == 4
            assert summary["counts"]["verified"] == 3
            assert summary["counts"]["missing"] == 1
            assert summary["counts"]["pending_verification"] == 1
            assert summary["counts"]["evidence_status"] == "INCOMPLETE"
            assert summary["received_not_verified"] == 1
            assert summary["absolute_path_exposed"] is False
            assert summary["manifest"]["absolute_path_exposed"] is False
            assert len(summary["items"]) == 5
            for row in summary["items"]:
                if row["storage_key"] is not None:
                    assert row["storage_key"].startswith("sha256/")
                    assert ".." not in row["storage_key"]
                assert row["blob_state"] == "missing"
            assert str(tmp_path) not in json.dumps(summary)

    asyncio.run(scenario())
