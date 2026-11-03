"""Restart safety: persisted epoch fence, STOP dedupe, and spool replay."""

from __future__ import annotations

from uuid import uuid4

from conftest import (
    FakeControlPlane,
    build_agent,
    job_item,
    lease_item,
    make_artifact,
    receipt_statuses,
    stop_item,
)


def test_lease_epoch_fence_survives_restart(tmp_path, signer) -> None:
    first_fake = FakeControlPlane()
    first_agent = build_agent(tmp_path, first_fake, signer=signer)
    lease_id = str(uuid4())
    first_fake.polls.append([lease_item(lease_id=lease_id, epoch=5)])
    first_agent.run_cycle()
    first_agent.spool.close()

    second_fake = FakeControlPlane()
    second_agent = build_agent(tmp_path, second_fake, signer=signer)
    stale_job = str(uuid4())
    second_fake.polls.append(
        [
            job_item(
                job_id=stale_job,
                lease_id=lease_id,
                epoch=4,
                artifacts=[make_artifact(b"stale", signer)],
            )
        ]
    )
    report = second_agent.run_cycle()

    assert second_agent.node_restart_count == 1
    assert report.jobs_skipped == 1
    assert receipt_statuses(second_fake, stale_job) == []
    second_agent.spool.close()


def test_handled_stop_is_not_replayed_after_restart(tmp_path, signer) -> None:
    first_fake = FakeControlPlane()
    first_agent = build_agent(tmp_path, first_fake, signer=signer)
    job_id = str(uuid4())
    lease_id = str(uuid4())
    signal_id = str(uuid4())
    stop = stop_item(
        signal_id=signal_id, job_id=job_id, lease_id=lease_id, epoch=1
    )
    first_fake.polls.append([stop])
    first_agent.run_cycle()
    assert first_fake.uploaded_order == ["stop_action", "receipt"]
    first_agent.spool.close()

    second_fake = FakeControlPlane()
    second_agent = build_agent(tmp_path, second_fake, signer=signer)
    second_fake.polls.append([stop])
    report = second_agent.run_cycle()

    assert report.stop_handled is False
    assert second_fake.actions == []
    assert second_fake.receipts == []
    second_agent.spool.close()


def test_pending_receipt_replays_after_restart(tmp_path) -> None:
    first_agent = build_agent(tmp_path, FakeControlPlane())
    first_agent.spool.enqueue(
        message_id="pending-1",
        kind="receipt",
        priority=10,
        payload={
            "message_type": "receipt",
            "message_id": "pending-1",
            "payload": {"status": "completed", "job_id": str(uuid4())},
        },
    )
    assert first_agent.spool.count_pending() == 1
    first_agent.spool.close()

    second_fake = FakeControlPlane()
    second_agent = build_agent(tmp_path, second_fake)
    second_agent.run_cycle()

    assert [receipt["message_id"] for receipt in second_fake.receipts] == ["pending-1"]
    assert second_agent.spool.count_pending() == 0
    second_agent.spool.close()


def test_last_cleanup_projection_survives_restart(tmp_path, signer) -> None:
    first_fake = FakeControlPlane()
    first_agent = build_agent(tmp_path, first_fake, signer=signer)
    first_fake.polls.append(
        [
            stop_item(
                signal_id=str(uuid4()),
                job_id=str(uuid4()),
                lease_id=str(uuid4()),
                epoch=1,
            )
        ]
    )
    first_agent.run_cycle()
    first_agent.spool.close()

    second_fake = FakeControlPlane()
    second_fake.reconciled = True
    second_agent = build_agent(tmp_path, second_fake, signer=signer)
    report = second_agent.run_cycle()

    assert report.release_confirmed is True
    second_agent.spool.close()


def test_boot_id_changes_and_restart_count_grows(tmp_path) -> None:
    first_agent = build_agent(tmp_path, FakeControlPlane())
    first_boot = first_agent.node_boot_id
    assert first_agent.node_restart_count == 0
    first_agent.spool.close()

    second_agent = build_agent(tmp_path, FakeControlPlane())
    assert second_agent.node_boot_id != first_boot
    assert second_agent.node_restart_count == 1
    second_agent.spool.close()
