"""SQLite spool: a node-local queue, never a source of authority.

Ordering is explicit so replay always runs STOP-related facts first:

    local STOP / stop action (0) -> stop receipt (5) -> job receipts (10)
    -> reconcile (20; currently an immediate call, not spooled)

Control-plane responses and heartbeats drive the actual STOP handling; the
priority constants below only order what is already persisted. Entries are keyed
by ``message_id`` to make uploads idempotent. Executed job ids are recorded
separately so a reconnect cannot execute the same started job twice.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

PRIORITY_STOP = 0
PRIORITY_STOP_ACTION = 5
PRIORITY_RECEIPT = 10
PRIORITY_RECONCILE = 20


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class SpoolEntry:
    entry_id: int
    message_id: str
    kind: str
    priority: int
    job_id: str | None
    lease_id: str | None
    epoch: int | None
    payload: dict[str, object]
    attempts: int
    created_at: str


@dataclass(frozen=True, slots=True)
class UploadAck:
    message_id: str
    duplicate: bool = False


@dataclass(slots=True)
class DrainResult:
    uploaded: int = 0
    duplicates: int = 0
    rejected: int = 0
    deferred: bool = False
    error: str | None = None


class UploadDeferred(RuntimeError):
    """Retryable failure: the control plane is unreachable; keep the entry."""


class UploadRejected(RuntimeError):
    """Permanent failure: the control plane refused the entry; dead-letter it."""


class Spool:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS spool_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL,
                priority INTEGER NOT NULL,
                job_id TEXT,
                lease_id TEXT,
                epoch INTEGER,
                payload TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                uploaded_at TEXT
            );
            CREATE INDEX IF NOT EXISTS ix_spool_pending
                ON spool_entries(state, priority, created_at, entry_id);
            CREATE TABLE IF NOT EXISTS executed_jobs (
                job_id TEXT PRIMARY KEY,
                lease_id TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                executed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS upload_acks (
                message_id TEXT PRIMARY KEY,
                duplicate INTEGER NOT NULL,
                acknowledged_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_state (
                state_key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def enqueue(
        self,
        *,
        message_id: str,
        kind: str,
        payload: Mapping[str, object],
        priority: int,
        job_id: str | None = None,
        lease_id: str | None = None,
        epoch: int | None = None,
    ) -> bool:
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO spool_entries
                (message_id, kind, priority, job_id, lease_id, epoch, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                kind,
                priority,
                job_id,
                lease_id,
                epoch,
                json.dumps(dict(payload), sort_keys=True, separators=(",", ":")),
                _utc_now_iso(),
            ),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def pending(self, limit: int = 500) -> list[SpoolEntry]:
        rows = self._conn.execute(
            """
            SELECT entry_id, message_id, kind, priority, job_id, lease_id, epoch,
                   payload, attempts, created_at
            FROM spool_entries
            WHERE state = 'pending'
            ORDER BY priority ASC, created_at ASC, entry_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            SpoolEntry(
                entry_id=int(row["entry_id"]),
                message_id=str(row["message_id"]),
                kind=str(row["kind"]),
                priority=int(row["priority"]),
                job_id=str(row["job_id"]) if row["job_id"] is not None else None,
                lease_id=str(row["lease_id"]) if row["lease_id"] is not None else None,
                epoch=int(row["epoch"]) if row["epoch"] is not None else None,
                payload=json.loads(str(row["payload"])),
                attempts=int(row["attempts"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

    def is_uploaded(self, message_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM spool_entries WHERE message_id = ? AND state = 'uploaded'",
            (message_id,),
        ).fetchone()
        return row is not None

    def mark_uploaded(self, message_id: str, *, duplicate: bool = False) -> None:
        """Mark an entry uploaded; the attempt was already counted by drain."""
        now = _utc_now_iso()
        self._conn.execute(
            """
            UPDATE spool_entries
            SET state = 'uploaded', uploaded_at = ?
            WHERE message_id = ?
            """,
            (now, message_id),
        )
        self._conn.execute(
            """
            INSERT OR REPLACE INTO upload_acks (message_id, duplicate, acknowledged_at)
            VALUES (?, ?, ?)
            """,
            (message_id, 1 if duplicate else 0, now),
        )
        self._conn.commit()

    def record_attempt(self, message_id: str) -> None:
        self._conn.execute(
            "UPDATE spool_entries SET attempts = attempts + 1 WHERE message_id = ?",
            (message_id,),
        )
        self._conn.commit()

    def mark_rejected(self, message_id: str) -> None:
        """Dead-letter a permanently rejected entry; never retried silently."""
        self._conn.execute(
            "UPDATE spool_entries SET state = 'rejected' WHERE message_id = ?",
            (message_id,),
        )
        self._conn.commit()

    def begin_job(self, job_id: str, lease_id: str, epoch: int) -> bool:
        """Claim a job once; returns False when it was already started."""
        try:
            self._conn.execute(
                "INSERT INTO executed_jobs (job_id, lease_id, epoch, executed_at) "
                "VALUES (?, ?, ?, ?)",
                (job_id, lease_id, epoch, _utc_now_iso()),
            )
        except sqlite3.IntegrityError:
            return False
        self._conn.commit()
        return True

    def has_executed(self, job_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM executed_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None

    def executed_job_ids(self) -> list[str]:
        rows = self._conn.execute("SELECT job_id FROM executed_jobs").fetchall()
        return [str(row["job_id"]) for row in rows]

    def count_pending(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM spool_entries WHERE state = 'pending'"
        ).fetchone()
        return int(row["count"]) if row is not None else 0

    def count_uploaded(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM spool_entries WHERE state = 'uploaded'"
        ).fetchone()
        return int(row["count"]) if row is not None else 0

    def count_rejected(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM spool_entries WHERE state = 'rejected'"
        ).fetchone()
        return int(row["count"]) if row is not None else 0

    def set_state(self, key: str, value: Mapping[str, object]) -> None:
        """Persist agent bookkeeping (lease fence, boot id, STOP dedupe)."""
        self._conn.execute(
            """
            INSERT INTO agent_state (state_key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(state_key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (
                key,
                json.dumps(dict(value), sort_keys=True, separators=(",", ":")),
                _utc_now_iso(),
            ),
        )
        self._conn.commit()

    def get_state(self, key: str) -> dict[str, object] | None:
        row = self._conn.execute(
            "SELECT value FROM agent_state WHERE state_key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        parsed = json.loads(str(row["value"]))
        return parsed if isinstance(parsed, dict) else None

    def drain(
        self, uploader: Callable[[SpoolEntry], UploadAck]
    ) -> DrainResult:
        result = DrainResult()
        for entry in self.pending():
            if self.is_uploaded(entry.message_id):
                continue
            self.record_attempt(entry.message_id)
            try:
                ack = uploader(entry)
            except UploadRejected as exc:
                # Permanent: dead-letter and keep draining the rest so one bad
                # entry cannot block STOP-first replay forever.
                self.mark_rejected(entry.message_id)
                result.rejected += 1
                result.error = str(exc)
                continue
            except UploadDeferred as exc:
                # Transient: stop at the first deferred entry; priority order is
                # preserved and the next cycle retries from the same point.
                result.deferred = True
                result.error = str(exc)
                break
            self.mark_uploaded(entry.message_id, duplicate=ack.duplicate)
            if ack.duplicate:
                result.duplicates += 1
            else:
                result.uploaded += 1
        return result
