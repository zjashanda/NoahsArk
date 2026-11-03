"""Cleanup determinism, release preconditions, and transport projection."""

from __future__ import annotations

import pytest

from noahsark_node.cleanup import (
    CleanupManager,
    project_cleanup_receipt,
    release_preconditions,
)

NODE_ID = "00000000-0000-4000-8000-000000000001"


def _perform(manager: CleanupManager, *, stop_confirmed: bool = True) -> dict:
    return manager.perform(
        run_id="run-1",
        job_id="job-1",
        attempt=1,
        lease_id="lease-1",
        lease_epoch=3,
        stop_confirmed=stop_confirmed,
    )


def test_cleanup_receipt_id_is_deterministic_for_replay() -> None:
    manager = CleanupManager(NODE_ID)

    first = _perform(manager)
    second = _perform(manager)

    assert first["receipt_id"] == second["receipt_id"]
    assert first["local_stop_confirmed"] is True
    assert first["safe_cleanup_done"] is True
    assert first["cleanup_status"] == "completed"


def test_failed_stop_blocks_release_even_when_occupancy_reconciled() -> None:
    manager = CleanupManager(NODE_ID)
    failed = _perform(manager, stop_confirmed=False)

    preconditions = release_preconditions(failed, occupancy_reconciled=True)

    assert preconditions.can_confirm_release is False
    assert "local_stop_confirmed" in preconditions.blockers
    assert "safe_cleanup_done" in preconditions.blockers
    assert "occupancy_reconciled" not in preconditions.blockers


def test_missing_occupancy_blocks_release() -> None:
    manager = CleanupManager(NODE_ID)
    completed = _perform(manager)

    preconditions = release_preconditions(completed, occupancy_reconciled=False)

    assert preconditions.can_confirm_release is False
    assert preconditions.blockers == ("occupancy_reconciled",)


def test_transport_projection_uses_only_shared_release_fields() -> None:
    manager = CleanupManager(NODE_ID)
    receipt = _perform(manager)

    projected = project_cleanup_receipt(receipt, occupancy_reconciled=False)

    assert projected["cleanup_receipt_id"] == receipt["receipt_id"]
    assert projected["cleanup_status"] == "completed"
    assert projected["local_stop_confirmed"] is True
    assert projected["safe_cleanup_done"] is True
    assert projected["occupancy_reconciled"] is False
    assert projected["completed_at"] == receipt["finished_at"]
    assert "receipt_id" not in projected
    assert "steps" not in projected


def test_transport_projection_rejects_malformed_receipt() -> None:
    with pytest.raises(ValueError):
        project_cleanup_receipt({"cleanup_status": "completed"})
