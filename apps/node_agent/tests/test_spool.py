"""Spool durability, ordering, idempotence, and bounded retry behavior."""

from __future__ import annotations

from pathlib import Path

from noahsark_node.spool import (
    PRIORITY_RECEIPT,
    PRIORITY_STOP,
    PRIORITY_STOP_ACTION,
    Spool,
    UploadAck,
    UploadDeferred,
    UploadRejected,
)


def _spool(tmp_path: Path, name: str = "spool.sqlite3") -> Spool:
    return Spool(tmp_path / name)


def _enqueue(
    spool: Spool,
    message_id: str,
    *,
    priority: int = PRIORITY_RECEIPT,
    kind: str = "receipt",
) -> None:
    spool.enqueue(
        message_id=message_id,
        kind=kind,
        payload={"message_id": message_id, "kind": kind},
        priority=priority,
    )


def test_pending_entries_survive_close_and_reopen(tmp_path: Path) -> None:
    spool = _spool(tmp_path)
    _enqueue(spool, "m1")
    spool.close()

    reopened = _spool(tmp_path)

    assert [entry.message_id for entry in reopened.pending()] == ["m1"]
    reopened.close()


def test_enqueue_is_idempotent_by_message_id(tmp_path: Path) -> None:
    spool = _spool(tmp_path)

    assert spool.enqueue(
        message_id="m1", kind="receipt", payload={"x": 1}, priority=10
    ) is True
    assert spool.enqueue(
        message_id="m1", kind="receipt", payload={"x": 2}, priority=10
    ) is False
    assert len(spool.pending()) == 1


def test_pending_order_is_stop_action_then_stop_receipt_then_job(
    tmp_path: Path,
) -> None:
    spool = _spool(tmp_path)
    _enqueue(spool, "job", priority=PRIORITY_RECEIPT)
    _enqueue(spool, "stop-receipt", priority=PRIORITY_STOP_ACTION)
    _enqueue(spool, "stop-action", priority=PRIORITY_STOP, kind="stop_action")

    assert [entry.message_id for entry in spool.pending()] == [
        "stop-action",
        "stop-receipt",
        "job",
    ]


def test_duplicate_ack_is_recorded_once_across_reopen(tmp_path: Path) -> None:
    spool = _spool(tmp_path)
    _enqueue(spool, "m1")

    result = spool.drain(lambda entry: UploadAck(entry.message_id, duplicate=True))
    assert result.duplicates == 1
    assert result.uploaded == 0
    spool.close()

    reopened = _spool(tmp_path)
    assert reopened.is_uploaded("m1") is True
    assert reopened.pending() == []
    reopened.close()


def test_transient_failure_stops_at_first_entry_and_keeps_it_pending(
    tmp_path: Path,
) -> None:
    spool = _spool(tmp_path)
    _enqueue(spool, "first", priority=PRIORITY_STOP, kind="stop_action")
    _enqueue(spool, "second", priority=PRIORITY_RECEIPT)

    def uploader(entry) -> UploadAck:
        if entry.message_id == "first":
            raise UploadDeferred("control plane down")
        return UploadAck(entry.message_id)

    result = spool.drain(uploader)

    assert result.deferred is True
    assert result.uploaded == 0
    entries = spool.pending()
    assert [entry.message_id for entry in entries] == ["first", "second"]
    assert entries[0].attempts == 1
    assert entries[1].attempts == 0


def test_permanent_rejection_is_dead_lettered_and_does_not_block_queue(
    tmp_path: Path,
) -> None:
    spool = _spool(tmp_path)
    _enqueue(spool, "bad", priority=PRIORITY_STOP, kind="stop_action")
    _enqueue(spool, "good", priority=PRIORITY_RECEIPT)

    def uploader(entry) -> UploadAck:
        if entry.message_id == "bad":
            raise UploadRejected("schema rejected")
        return UploadAck(entry.message_id)

    result = spool.drain(uploader)

    assert result.rejected == 1
    assert result.uploaded == 1
    assert spool.count_rejected() == 1
    assert spool.pending() == []
    assert spool.is_uploaded("good") is True


def test_job_claim_is_once_across_reopen(tmp_path: Path) -> None:
    spool = _spool(tmp_path)
    assert spool.begin_job("job-1", "lease-1", 3) is True
    spool.close()

    reopened = _spool(tmp_path)
    assert reopened.begin_job("job-1", "lease-1", 3) is False
    assert reopened.has_executed("job-1") is True
    reopened.close()


def test_agent_state_round_trips_across_reopen(tmp_path: Path) -> None:
    spool = _spool(tmp_path)
    spool.set_state("lease", {"lease_id": "lease-1", "epoch": 7, "job_id": None})
    spool.close()

    reopened = _spool(tmp_path)
    state = reopened.get_state("lease")
    assert state == {"lease_id": "lease-1", "epoch": 7, "job_id": None}
    assert reopened.get_state("missing") is None
    reopened.close()


def test_drain_only_runs_pending_entries(tmp_path: Path) -> None:
    spool = _spool(tmp_path)
    _enqueue(spool, "m1")
    spool.drain(lambda entry: UploadAck(entry.message_id))
    calls: list[str] = []

    def uploader(entry) -> UploadAck:
        calls.append(entry.message_id)
        return UploadAck(entry.message_id)

    result = spool.drain(uploader)
    assert result.uploaded == 0
    assert calls == []


def test_unknown_state_payload_fails_closed(tmp_path: Path) -> None:
    spool = _spool(tmp_path)
    spool._conn.execute(  # noqa: SLF001 - direct corrupt-state fixture
        "INSERT INTO agent_state (state_key, value, updated_at) VALUES (?, ?, ?)",
        ("broken", "[]", "2026-10-30T00:00:00Z"),
    )
    spool._conn.commit()
    assert spool.get_state("broken") is None
    spool.close()
