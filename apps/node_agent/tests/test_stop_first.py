"""STOP-first ordering and stopped-lease fencing."""

from __future__ import annotations

import json
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


def _stop_receipt(fake: FakeControlPlane) -> dict:
    return next(
        receipt
        for receipt in fake.receipts
        if receipt["payload"]["status"] == "stopped"
    )


def test_stop_is_handled_before_job_in_same_poll(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    job_id = str(uuid4())
    lease_id = str(uuid4())
    artifact = make_artifact(b"bundle", signer)
    fake.polls.append(
        [
            job_item(job_id=job_id, lease_id=lease_id, epoch=1, artifacts=[artifact]),
            stop_item(
                signal_id=str(uuid4()),
                job_id=job_id,
                lease_id=lease_id,
                epoch=1,
            ),
        ]
    )

    report = agent.run_cycle()

    assert report.stop_handled is True
    assert report.jobs_executed == 0
    assert "started" not in receipt_statuses(fake, job_id)
    assert "completed" not in receipt_statuses(fake, job_id)
    assert receipt_statuses(fake, job_id) == ["stopped"]


def test_stop_action_is_uploaded_before_stop_receipt(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    job_id = str(uuid4())
    lease_id = str(uuid4())
    fake.polls.append(
        [stop_item(signal_id=str(uuid4()), job_id=job_id, lease_id=lease_id, epoch=1)]
    )

    agent.run_cycle()

    assert fake.uploaded_order == ["stop_action", "receipt"]
    assert fake.actions[0]["local_stop_confirmed"] is True


def test_job_for_stopped_lease_is_not_executed_later(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    lease_id = str(uuid4())
    stopped_job = str(uuid4())
    fake.polls.append(
        [
            stop_item(
                signal_id=str(uuid4()),
                job_id=stopped_job,
                lease_id=lease_id,
                epoch=1,
            )
        ]
    )
    agent.run_cycle()

    later_job = str(uuid4())
    artifact = make_artifact(b"should-not-run", signer)
    fake.polls.append(
        [
            job_item(
                job_id=later_job,
                lease_id=lease_id,
                epoch=1,
                artifacts=[artifact],
            )
        ]
    )
    report = agent.run_cycle()

    assert report.jobs_skipped == 1
    assert receipt_statuses(fake, later_job) == []


def test_stop_for_stale_epoch_is_ignored(tmp_path) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake)
    lease_id = str(uuid4())
    fake.polls.append([lease_item(lease_id=lease_id, epoch=5)])
    agent.run_cycle()

    fake.polls.append(
        [
            stop_item(
                signal_id=str(uuid4()),
                job_id=str(uuid4()),
                lease_id=lease_id,
                epoch=4,
            )
        ]
    )
    report = agent.run_cycle()

    assert report.stop_handled is False
    assert fake.receipts == []


def test_stop_for_ahead_epoch_is_ignored(tmp_path) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake)
    lease_id = str(uuid4())
    fake.polls.append([lease_item(lease_id=lease_id, epoch=5)])
    agent.run_cycle()

    fake.polls.append(
        [
            stop_item(
                signal_id=str(uuid4()),
                job_id=str(uuid4()),
                lease_id=lease_id,
                epoch=6,
            )
        ]
    )
    report = agent.run_cycle()

    # EPOCH_AHEAD: reconcile first; a future token must not be acted on.
    assert report.stop_handled is False
    assert fake.receipts == []
    assert fake.actions == []
    assert agent.lease.matches(lease_id, 5)


def test_all_stops_in_one_poll_are_handled_before_jobs(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    first_job = str(uuid4())
    second_job = str(uuid4())
    lease_id = str(uuid4())
    fake.polls.append(
        [
            job_item(
                job_id=first_job,
                lease_id=lease_id,
                epoch=1,
                artifacts=[make_artifact(b"one", signer)],
            ),
            stop_item(
                signal_id=str(uuid4()),
                job_id=first_job,
                lease_id=lease_id,
                epoch=1,
            ),
            stop_item(
                signal_id=str(uuid4()),
                job_id=second_job,
                lease_id=lease_id,
                epoch=1,
            ),
        ]
    )

    report = agent.run_cycle()

    assert report.stop_handled is True
    assert report.jobs_executed == 0
    stopped_jobs = {
        receipt["payload"]["job_id"]
        for receipt in fake.receipts
        if receipt["payload"]["status"] == "stopped"
    }
    assert stopped_jobs == {first_job, second_job}


def test_stop_receipt_carries_minimal_cleanup_projection(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    job_id = str(uuid4())
    lease_id = str(uuid4())
    fake.polls.append(
        [stop_item(signal_id=str(uuid4()), job_id=job_id, lease_id=lease_id, epoch=1)]
    )

    agent.run_cycle()

    cleanup = _stop_receipt(fake)["payload"]["cleanup_receipt"]
    assert set(cleanup) == {
        "cleanup_receipt_id",
        "cleanup_status",
        "local_stop_confirmed",
        "safe_cleanup_done",
        "occupancy_reconciled",
        "completed_at",
        "notes",
    }
    assert cleanup["occupancy_reconciled"] is False
    assert cleanup["local_stop_confirmed"] is True
    assert cleanup["safe_cleanup_done"] is True
    assert json.dumps(cleanup)


def test_release_requires_control_plane_reconciliation(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    job_id = str(uuid4())
    lease_id = str(uuid4())
    fake.polls.append(
        [stop_item(signal_id=str(uuid4()), job_id=job_id, lease_id=lease_id, epoch=1)]
    )

    unreconciled = agent.run_cycle()
    assert unreconciled.release_confirmed is False
    assert "occupancy_reconciled" in unreconciled.blockers

    fake.reconciled = True
    fake.polls.append([])
    reconciled = agent.run_cycle()
    assert reconciled.release_confirmed is True
    assert reconciled.blockers == ()


def test_stop_does_not_regress_epoch(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    lease_id = str(uuid4())
    fake.polls.append([lease_item(lease_id=lease_id, epoch=5)])
    agent.run_cycle()
    fake.polls.append(
        [stop_item(signal_id=str(uuid4()), job_id=str(uuid4()), lease_id=lease_id, epoch=5)]
    )
    agent.run_cycle()

    assert agent.lease.epoch == 5
    assert agent.lease.matches(lease_id, 5)
