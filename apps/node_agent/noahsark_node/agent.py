"""Stop-first agent orchestration.

Cycle order is deliberate:

    register -> heartbeat -> poll -> STOP -> stop actions -> upload -> dedupe
    -> reconcile -> resume

A STOP found in the poll is handled before any job in the same response. Receipts
are spool-first: a job receipt produced during ``resume`` is uploaded on the next
cycle, never ahead of a pending STOP.

Restart safety: the current lease/epoch fence, handled STOP ids, stopped leases,
boot identity, and the last cleanup projection are persisted in the local spool.
A restarted process therefore cannot execute stale work or replay a STOP.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .cleanup import (
    CleanupManager,
    ReleasePreconditions,
    project_cleanup_receipt,
    release_preconditions,
)
from .client import (
    ControlPlaneClient,
    ControlPlaneRejected,
    ControlPlaneUnavailable,
    PollMessage,
)
from .executor import SimulatedExecutor
from .protocol import (
    EXECUTOR_SOURCE,
    JobMessage,
    LeaseTracker,
    StopSignal,
    build_node_observed_outcome,
    build_receipt,
    deterministic_id,
    utc_now_iso,
    uuid_str,
)
from .spool import (
    PRIORITY_RECEIPT,
    PRIORITY_STOP,
    PRIORITY_STOP_ACTION,
    Spool,
    SpoolEntry,
    UploadAck,
    UploadDeferred,
    UploadRejected,
)
from .tools import (
    ERROR_INVALID_TOOL_ARGS,
    ERROR_UNKNOWN_TOOL,
    STATUS_SUCCEEDED,
    InvalidToolArgsError,
    ToolResult,
    UnknownToolError,
    rejected_result,
    run_tool,
)
from .verifier import ArtifactVerifier

STATE_LEASE = "lease"
STATE_STOPPED_LEASES = "stopped_leases"
STATE_HANDLED_STOPS = "handled_stop_ids"
STATE_LAST_CLEANUP = "last_cleanup_receipt"
STATE_BOOT = "boot"
MAX_PERSISTED_STOPS = 500


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _state_items(state: dict[str, object] | None) -> list[object]:
    if state is None:
        return []
    items = state.get("items")
    return list(items) if isinstance(items, list) else []


@dataclass(slots=True)
class CycleReport:
    steps: list[str] = field(default_factory=list)
    stop_handled: bool = False
    jobs_executed: int = 0
    jobs_refused: int = 0
    jobs_skipped: int = 0
    commands_executed: int = 0
    commands_failed: int = 0
    uploaded: int = 0
    duplicates: int = 0
    upload_rejected: int = 0
    release_confirmed: bool = False
    blockers: tuple[str, ...] = ()
    skipped_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "steps": list(self.steps),
            "stop_handled": self.stop_handled,
            "jobs_executed": self.jobs_executed,
            "jobs_refused": self.jobs_refused,
            "jobs_skipped": self.jobs_skipped,
            "commands_executed": self.commands_executed,
            "commands_failed": self.commands_failed,
            "uploaded": self.uploaded,
            "duplicates": self.duplicates,
            "upload_rejected": self.upload_rejected,
            "release_confirmed": self.release_confirmed,
            "blockers": list(self.blockers),
            "skipped_reason": self.skipped_reason,
        }


class NodeAgent:
    def __init__(
        self,
        *,
        client: ControlPlaneClient,
        spool: Spool,
        verifier: ArtifactVerifier,
        executor: SimulatedExecutor,
        cleanup: CleanupManager,
        node_id: str,
        local_stop_hook: Callable[[StopSignal], bool] | None = None,
        node_boot_id: str | None = None,
    ) -> None:
        self.client = client
        self.spool = spool
        self.verifier = verifier
        self.executor = executor
        self.cleanup = cleanup
        self.node_id = node_id
        self.local_stop_hook = local_stop_hook
        self.lease = self._restore_lease()
        self._last_cleanup_receipt = self.spool.get_state(STATE_LAST_CLEANUP)
        self._handled_stop_ids = self._restore_handled_stop_ids()
        self._stopped_leases = self._restore_stopped_leases()
        self.node_boot_id, self.node_restart_count = self._initialize_boot(node_boot_id)
        self._registered = False

    # -- durable state -------------------------------------------------

    def _restore_lease(self) -> LeaseTracker:
        state = self.spool.get_state(STATE_LEASE)
        return LeaseTracker.from_dict(state) if state is not None else LeaseTracker()

    def _restore_handled_stop_ids(self) -> set[str]:
        return {
            str(item)
            for item in _state_items(self.spool.get_state(STATE_HANDLED_STOPS))
            if isinstance(item, str)
        }

    def _restore_stopped_leases(self) -> set[tuple[str, int]]:
        restored: set[tuple[str, int]] = set()
        for item in _state_items(self.spool.get_state(STATE_STOPPED_LEASES)):
            if not isinstance(item, dict):
                continue
            lease_id = item.get("lease_id")
            epoch = item.get("epoch")
            if lease_id is None or epoch is None:
                continue
            restored.add((str(lease_id), _as_int(epoch)))
        return restored

    def _initialize_boot(self, provided_boot_id: str | None) -> tuple[str, int]:
        previous = self.spool.get_state(STATE_BOOT)
        previous_restarts = _as_int(previous.get("restart_count")) if previous else 0
        if provided_boot_id is not None:
            boot_id = provided_boot_id
            restart_count = previous_restarts
        elif previous is None:
            boot_id = uuid_str()
            restart_count = 0
        else:
            boot_id = uuid_str()
            restart_count = previous_restarts + 1
        self.spool.set_state(
            STATE_BOOT,
            {"boot_id": boot_id, "restart_count": restart_count},
        )
        return boot_id, restart_count

    def _persist_lease(self) -> None:
        self.spool.set_state(STATE_LEASE, self.lease.to_dict())

    def _persist_stopped_leases(self) -> None:
        items = [
            {"lease_id": lease_id, "epoch": epoch}
            for lease_id, epoch in sorted(self._stopped_leases)[-MAX_PERSISTED_STOPS:]
        ]
        self.spool.set_state(STATE_STOPPED_LEASES, {"items": items})

    def _persist_handled_stop_ids(self) -> None:
        items = sorted(self._handled_stop_ids)[-MAX_PERSISTED_STOPS:]
        self.spool.set_state(STATE_HANDLED_STOPS, {"items": items})

    def _persist_last_cleanup(self, receipt: dict[str, object]) -> None:
        self._last_cleanup_receipt = receipt
        self.spool.set_state(STATE_LAST_CLEANUP, receipt)

    # -- cycle ---------------------------------------------------------

    def run_cycle(self) -> CycleReport:
        report = CycleReport()
        self._register(report)
        self._heartbeat(report)
        messages = self._poll(report)

        stops: list[StopSignal] = []
        jobs: list[PollMessage] = []
        commands: list[PollMessage] = []
        for message in messages:
            if message.kind == "lease":
                self._apply_lease_mapping(message.payload)
            elif message.kind == "stop":
                try:
                    signal = message.stop_signal()
                except (KeyError, TypeError, ValueError) as exc:
                    report.skipped_reason = f"invalid_stop:{exc}"
                    continue
                if self.lease.applies(signal.lease_id, signal.epoch):
                    stops.append(signal)
            elif message.kind == "job":
                jobs.append(message)
            elif message.kind == "command":
                commands.append(message)

        new_stops = [
            item for item in stops if item.signal_id not in self._handled_stop_ids
        ]
        if new_stops:
            # STOP-first: every new STOP is handled before any job in this poll.
            report.steps.append("stop")
            for signal in new_stops:
                self._handle_stop(signal, report)
            report.steps.append("stop_actions")
            report.steps.append("upload")
            self._drain(report)
            report.steps.append("dedupe")
            report.steps.append("reconcile")
            reconciliation = self._reconcile(report)
            preconditions = self._release_state(reconciliation)
            report.release_confirmed = preconditions.can_confirm_release
            report.blockers = preconditions.blockers
            self._run_commands(commands, report)
            return report

        report.steps.append("upload")
        self._drain(report)
        report.steps.append("dedupe")
        report.steps.append("reconcile")
        reconciliation = self._reconcile(report)
        preconditions = self._release_state(reconciliation)
        report.release_confirmed = preconditions.can_confirm_release
        report.blockers = preconditions.blockers
        report.steps.append("resume")
        for message in jobs:
            self._maybe_execute(message, report)
        self._run_commands(commands, report)
        return report

    def _register(self, report: CycleReport) -> None:
        if self._registered:
            return
        report.steps.append("register")
        try:
            response = self.client.register()
        except (ControlPlaneUnavailable, ControlPlaneRejected) as exc:
            report.steps.append("register_unavailable")
            report.skipped_reason = str(exc)
            return
        self._registered = True
        lease_raw = response.get("lease")
        if isinstance(lease_raw, dict):
            self._apply_lease_mapping(lease_raw)

    def _heartbeat(self, report: CycleReport) -> None:
        report.steps.append("heartbeat")
        try:
            response = self.client.heartbeat(
                {
                    "spool_pending": self.spool.count_pending(),
                    "lease": self.lease.to_dict(),
                    "simulated": True,
                }
            )
        except (ControlPlaneUnavailable, ControlPlaneRejected) as exc:
            report.steps.append("heartbeat_unavailable")
            report.skipped_reason = str(exc)
            return
        lease_raw = response.get("lease")
        if isinstance(lease_raw, dict):
            self._apply_lease_mapping(lease_raw)

    def _poll(self, report: CycleReport) -> list[PollMessage]:
        report.steps.append("poll")
        try:
            return self.client.poll(self.lease)
        except (ControlPlaneUnavailable, ControlPlaneRejected) as exc:
            report.steps.append("poll_unavailable")
            report.skipped_reason = str(exc)
            return []

    def _handle_stop(self, signal: StopSignal, report: CycleReport) -> None:
        self._stopped_leases.add((signal.lease_id, signal.epoch))
        stop_confirmed = True
        if self.local_stop_hook is not None:
            stop_confirmed = bool(self.local_stop_hook(signal))
        cleanup_receipt = self.cleanup.perform(
            run_id=signal.job_id,
            job_id=signal.job_id,
            attempt=1,
            lease_id=signal.lease_id,
            lease_epoch=signal.epoch,
            stop_confirmed=stop_confirmed,
        )
        self._persist_last_cleanup(cleanup_receipt)

        # Deterministic IDs: a redelivered STOP after a crash/restart reuses the
        # same spool keys, so INSERT OR IGNORE dedupes it instead of replaying.
        action_message_id = deterministic_id(
            "stop_action", self.node_id, signal.signal_id
        )
        # Priority 0: the local STOP action must replay before any receipt.
        self.spool.enqueue(
            message_id=action_message_id,
            kind="stop_action",
            priority=PRIORITY_STOP,
            payload={
                "message_id": action_message_id,
                "action": "local_stop_confirmed",
                "job_id": signal.job_id,
                "lease_id": signal.lease_id,
                "epoch": signal.epoch,
                "reason": signal.reason,
                "local_stop_confirmed": bool(cleanup_receipt["local_stop_confirmed"]),
                "simulated": True,
                "source": EXECUTOR_SOURCE,
            },
            job_id=signal.job_id,
            lease_id=signal.lease_id,
            epoch=signal.epoch,
        )

        stop_job = JobMessage(
            job_id=signal.job_id,
            lease_id=signal.lease_id,
            epoch=signal.epoch,
            attempt=1,
            run_id=signal.job_id,
            artifacts=(),
            artifact_contents={},
        )
        outcome = build_node_observed_outcome(
            execution_status="ABORTED",
            validity_status="BLOCKED",
            business_verdict="NOT_EVALUATED",
            evidence_status="UNVERIFIED",
        )
        receipt_message_id = deterministic_id(
            "stop_receipt_message", self.node_id, signal.signal_id
        )
        receipt = build_receipt(
            node_id=self.node_id,
            job=stop_job,
            status="stopped",
            outcome=outcome,
            facts={
                "source": EXECUTOR_SOURCE,
                "simulated": True,
                "executed_on_device": False,
                "stop_reason": signal.reason,
                "local_stop_confirmed": bool(cleanup_receipt["local_stop_confirmed"]),
                "cleanup_receipt_id": cleanup_receipt["receipt_id"],
            },
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            duration_ms=0,
            cleanup_receipt=project_cleanup_receipt(
                cleanup_receipt, occupancy_reconciled=False
            ),
            node_boot_id=self.node_boot_id,
            node_restart_count=self.node_restart_count,
            receipt_id=deterministic_id(
                "stop_receipt", self.node_id, signal.signal_id
            ),
            message_id=receipt_message_id,
        )
        self.spool.enqueue(
            message_id=str(receipt["message_id"]),
            kind="receipt",
            # Priority 5: the stop receipt follows the local stop action.
            priority=PRIORITY_STOP_ACTION,
            payload=receipt,
            job_id=signal.job_id,
            lease_id=signal.lease_id,
            epoch=signal.epoch,
        )
        # Persist dedupe state only after both durable entries exist.
        self._handled_stop_ids.add(signal.signal_id)
        self._persist_handled_stop_ids()
        self._persist_stopped_leases()
        report.stop_handled = True
        # The epoch is intentionally NOT reset: a completed STOP must not make
        # stale jobs/STOPs from an older epoch acceptable again. Re-execution of
        # this lease is blocked by _stopped_leases instead.

    def _drain(self, report: CycleReport) -> None:
        def uploader(entry: SpoolEntry) -> UploadAck:
            try:
                return self.client.post_receipt(entry.payload)
            except ControlPlaneUnavailable as exc:
                raise UploadDeferred(str(exc)) from exc
            except ControlPlaneRejected as exc:
                raise UploadRejected(str(exc)) from exc

        result = self.spool.drain(uploader)
        report.uploaded += result.uploaded
        report.duplicates += result.duplicates
        report.upload_rejected += result.rejected
        if result.error is not None:
            report.skipped_reason = result.error

    def _reconcile(self, report: CycleReport) -> dict[str, object]:
        try:
            response = self.client.reconcile(
                self.lease, executed_job_ids=self.spool.executed_job_ids()
            )
        except (ControlPlaneUnavailable, ControlPlaneRejected) as exc:
            report.skipped_reason = str(exc)
            return {}
        lease_raw = response.get("lease")
        if isinstance(lease_raw, dict):
            self._apply_lease_mapping(lease_raw)
        return response

    def _release_state(self, reconciliation: dict[str, object]) -> ReleasePreconditions:
        if self._last_cleanup_receipt is None:
            return ReleasePreconditions(False, False, False)
        return release_preconditions(
            self._last_cleanup_receipt,
            occupancy_reconciled=bool(reconciliation.get("occupancy_reconciled", False)),
        )

    def _apply_lease_mapping(self, raw: object) -> None:
        if not isinstance(raw, dict):
            return
        lease_id = raw.get("lease_id")
        epoch = raw.get("epoch")
        if lease_id is None or epoch is None:
            return
        observed = self.lease.observe(
            str(lease_id),
            _as_int(epoch),
            str(raw["job_id"]) if raw.get("job_id") is not None else None,
        )
        if observed:
            self._persist_lease()

    def _run_commands(
        self, messages: list[PollMessage], report: CycleReport
    ) -> None:
        if not messages:
            return
        report.steps.append("commands")
        for message in messages:
            self._execute_command(message, report)

    def _execute_command(self, message: PollMessage, report: CycleReport) -> None:
        try:
            command = message.command()
        except (KeyError, TypeError, ValueError) as exc:
            report.skipped_reason = f"invalid_command:{exc}"
            report.commands_failed += 1
            return

        try:
            result = run_tool(
                command.tool_id,
                dict(command.args),
                timeout_seconds=command.timeout_seconds,
            )
        except UnknownToolError as exc:
            result = rejected_result(
                command.tool_id, ERROR_UNKNOWN_TOOL, str(exc)
            )
        except InvalidToolArgsError as exc:
            result = rejected_result(
                command.tool_id, ERROR_INVALID_TOOL_ARGS, str(exc)
            )

        self._post_command_result(command.command_id, result, report)

    def _post_command_result(
        self, command_id: str, result: ToolResult, report: CycleReport
    ) -> None:
        payload = result.to_payload(node_id=self.node_id, command_id=command_id)
        try:
            self.client.post_command_result(payload)
        except (ControlPlaneUnavailable, ControlPlaneRejected) as exc:
            report.skipped_reason = f"command_result:{exc}"
        if result.status == STATUS_SUCCEEDED:
            report.commands_executed += 1
        else:
            report.commands_failed += 1

    def _maybe_execute(self, message: PollMessage, report: CycleReport) -> None:
        try:
            job = message.job()
        except (KeyError, TypeError, ValueError) as exc:
            report.skipped_reason = f"invalid_job:{exc}"
            report.jobs_skipped += 1
            return
        if (job.lease_id, job.epoch) in self._stopped_leases:
            report.jobs_skipped += 1
            return
        if not self.lease.observe(job.lease_id, job.epoch, job.job_id):
            report.jobs_skipped += 1
            return
        self._persist_lease()

        # Spool a `started` fact before claiming/executing. Deterministic IDs make
        # a crash/redelivery idempotent rather than a duplicate execution record.
        started = build_receipt(
            node_id=self.node_id,
            job=job,
            status="started",
            outcome=build_node_observed_outcome(
                execution_status="RUNNING",
                validity_status="UNKNOWN",
                business_verdict="NOT_EVALUATED",
                evidence_status="UNVERIFIED",
            ),
            facts={
                "source": EXECUTOR_SOURCE,
                "simulated": True,
                "executed_on_device": False,
                "job_id": job.job_id,
                "lease_id": job.lease_id,
                "epoch": job.epoch,
            },
            started_at=utc_now_iso(),
            finished_at=None,
            duration_ms=0,
            node_boot_id=self.node_boot_id,
            node_restart_count=self.node_restart_count,
            receipt_id=deterministic_id(
                "job_receipt", self.node_id, job.job_id, job.attempt, "started"
            ),
            message_id=deterministic_id(
                "job_message", self.node_id, job.job_id, job.attempt, "started"
            ),
        )
        self.spool.enqueue(
            message_id=str(started["message_id"]),
            kind="receipt",
            priority=PRIORITY_RECEIPT,
            payload=started,
            job_id=job.job_id,
            lease_id=job.lease_id,
            epoch=job.epoch,
        )
        if not self.spool.begin_job(job.job_id, job.lease_id, job.epoch):
            report.jobs_skipped += 1
            return

        result = self.executor.execute(job)
        receipt = build_receipt(
            node_id=self.node_id,
            job=job,
            status=result.status,
            outcome=result.outcome,
            facts=result.facts,
            started_at=result.started_at,
            finished_at=result.finished_at,
            duration_ms=result.duration_ms,
            error=result.error,
            node_boot_id=self.node_boot_id,
            node_restart_count=self.node_restart_count,
            receipt_id=deterministic_id(
                "job_receipt", self.node_id, job.job_id, job.attempt, result.status
            ),
            message_id=deterministic_id(
                "job_message", self.node_id, job.job_id, job.attempt, result.status
            ),
        )
        self.spool.enqueue(
            message_id=str(receipt["message_id"]),
            kind="receipt",
            priority=PRIORITY_RECEIPT,
            payload=receipt,
            job_id=job.job_id,
            lease_id=job.lease_id,
            epoch=job.epoch,
        )
        if result.status == "completed":
            report.jobs_executed += 1
        else:
            report.jobs_refused += 1
