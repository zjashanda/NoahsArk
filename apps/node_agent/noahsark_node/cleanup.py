"""Cleanup receipt and release preconditions.

A missing cleanup receipt blocks release confirmation only; it must not by itself
make the evidence set incomplete or produce a platform FAIL. Release requires all
three independent facts: local stop confirmed, safe cleanup done, occupancy
reconciled by the control plane.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .protocol import canonical_json, deterministic_id, utc_now_iso

SIM_DEVICE_ID = "00000000-0000-4000-8000-0000000000d1"
SIM_ENDPOINTS = ("sim://audio", "sim://serial")


@dataclass(frozen=True, slots=True)
class ReleasePreconditions:
    local_stop_confirmed: bool
    safe_cleanup_done: bool
    occupancy_reconciled: bool

    @property
    def can_confirm_release(self) -> bool:
        return (
            self.local_stop_confirmed
            and self.safe_cleanup_done
            and self.occupancy_reconciled
        )

    @property
    def blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if not self.local_stop_confirmed:
            blockers.append("local_stop_confirmed")
        if not self.safe_cleanup_done:
            blockers.append("safe_cleanup_done")
        if not self.occupancy_reconciled:
            blockers.append("occupancy_reconciled")
        return tuple(blockers)


def _sha256_prefixed(value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _step(
    step_id: str,
    action: str,
    status: str,
    timestamp: str,
    detail_code: str | None = None,
) -> dict[str, object]:
    return {
        "step_id": step_id,
        "action": action,
        "status": status,
        "started_at": timestamp,
        "finished_at": timestamp,
        "detail_code": detail_code,
        "evidence_ids": [],
    }


class CleanupManager:
    """Development cleanup simulator; no real processes or devices are touched."""

    def __init__(
        self,
        node_id: str,
        *,
        device_id: str = SIM_DEVICE_ID,
        device_model: str = "simulated-node",
    ) -> None:
        self.node_id = node_id
        self.device_id = device_id
        self.device_model = device_model

    def perform(
        self,
        *,
        run_id: str,
        job_id: str,
        attempt: int,
        lease_id: str,
        lease_epoch: int,
        stop_confirmed: bool = True,
        release_ok: bool = True,
    ) -> dict[str, object]:
        started_at = utc_now_iso()
        stop_status = "completed" if stop_confirmed else "failed"
        release_status = "completed" if release_ok else "failed"
        steps = [
            _step("stop-1", "stop_safe", stop_status, started_at),
            _step("stop-2", "terminate_processes", stop_status, started_at),
            _step("rel-1", "release_endpoints", release_status, started_at),
            _step("rel-2", "verify_idle", release_status, started_at),
        ]
        local_stop_confirmed = stop_confirmed and all(
            step["status"] == "completed" for step in steps[:2]
        )
        safe_cleanup_done = (
            local_stop_confirmed
            and release_ok
            and all(step["status"] == "completed" for step in steps[2:])
        )
        cleanup_status = "completed" if local_stop_confirmed and safe_cleanup_done else "failed"
        finished_at = utc_now_iso()
        resources: dict[str, object] = {
            "processes_terminated": ["sim-runner"] if local_stop_confirmed else [],
            "files_closed": True,
            "endpoints_released": list(SIM_ENDPOINTS) if safe_cleanup_done else [],
            "device_reset_performed": safe_cleanup_done,
            "device_state_after": "idle" if safe_cleanup_done else "unsafe",
            "spool_flushed": True,
            "residual_warnings": [],
        }
        facts: dict[str, object] = {
            "cleanup_status": cleanup_status,
            "local_stop_confirmed": local_stop_confirmed,
            "safe_cleanup_done": safe_cleanup_done,
            "steps": steps,
            "resources": resources,
            "warnings": [],
        }
        receipt: dict[str, object] = {
            "schema_version": "1.0",
            "receipt_type": "cleanup",
            # Deterministic for (node, job, attempt, lease, epoch): replaying a
            # STOP after a restart yields the same cleanup_receipt_id so the
            # control plane can dedupe instead of recording a new cleanup.
            "receipt_id": deterministic_id(
                "cleanup",
                self.node_id,
                job_id,
                attempt,
                lease_id,
                lease_epoch,
            ),
            "task_id": None,
            "revision_id": None,
            "run_id": run_id,
            "job_id": job_id,
            "attempt": attempt,
            "node_id": self.node_id,
            "device_identity": {
                "device_id": self.device_id,
                "model": self.device_model,
                "serial": None,
                "firmware": None,
                "endpoints": list(SIM_ENDPOINTS),
            },
            "lease_id": lease_id,
            "lease_epoch": lease_epoch,
            "started_at": started_at,
            "finished_at": finished_at,
            "cleanup_status": cleanup_status,
            "local_stop_confirmed": local_stop_confirmed,
            "safe_cleanup_done": safe_cleanup_done,
            "failure_code": None if cleanup_status == "completed" else "LOCAL_SAFE_STOP",
            "steps": steps,
            "resources": resources,
            "safety_stop": None,
            "warnings": [],
            "facts_digest": _sha256_prefixed(facts),
            "signature": None,
            "produced_at": finished_at,
            "notes": "development simulator cleanup; no real device touched",
        }
        receipt["receipt_digest"] = _sha256_prefixed(
            {key: value for key, value in receipt.items() if key != "receipt_digest"}
        )
        return receipt


def release_preconditions(
    cleanup_receipt: dict[str, object],
    *,
    occupancy_reconciled: bool,
) -> ReleasePreconditions:
    return ReleasePreconditions(
        local_stop_confirmed=bool(cleanup_receipt.get("local_stop_confirmed", False)),
        safe_cleanup_done=bool(cleanup_receipt.get("safe_cleanup_done", False)),
        occupancy_reconciled=occupancy_reconciled,
    )


def project_cleanup_receipt(
    cleanup_receipt: Mapping[str, object],
    *,
    occupancy_reconciled: bool = False,
) -> dict[str, object]:
    """Project the local cleanup result onto the transport receipt shape.

    ``receipt.cleanup_receipt`` is only the minimum release projection (R-02).
    The authoritative detailed cleanup receipt stays local/evidence-stored and
    is referenced by ``cleanup_receipt_id``. The node never claims occupancy
    reconciliation: that is a control-plane fact.
    """
    receipt_id = cleanup_receipt.get("receipt_id")
    finished_at = cleanup_receipt.get("finished_at")
    cleanup_status = cleanup_receipt.get("cleanup_status")
    if not isinstance(receipt_id, str) or not isinstance(finished_at, str):
        raise ValueError("cleanup receipt is missing receipt_id/finished_at")
    if not isinstance(cleanup_status, str):
        raise ValueError("cleanup receipt is missing cleanup_status")
    projected: dict[str, object] = {
        "cleanup_receipt_id": receipt_id,
        "cleanup_status": cleanup_status,
        "local_stop_confirmed": bool(cleanup_receipt.get("local_stop_confirmed", False)),
        "safe_cleanup_done": bool(cleanup_receipt.get("safe_cleanup_done", False)),
        "occupancy_reconciled": bool(occupancy_reconciled),
        "completed_at": finished_at,
    }
    notes = cleanup_receipt.get("notes")
    if isinstance(notes, str) and notes:
        projected["notes"] = notes[:2000]
    return projected


def dump_receipt(receipt: dict[str, object]) -> str:
    return json.dumps(receipt, sort_keys=True, indent=2)
