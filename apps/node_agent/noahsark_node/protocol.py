"""Protocol data structures and facts-only guards.

The receipt/outcome shape follows the intent of
``docs/contracts/schemas/security/receipt.schema.json``: the node reports
``node_observed_*`` facts with ``used_for_decision=false``. Full signed-envelope
conformance is PENDING under the G-NODE decision gate.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

SCHEMA_VERSION = "1.0"
PROTOCOL_VERSION = "noahsark.node/v1"
EXECUTOR_SOURCE = "node_agent_simulator"
RECEIPT_TTL_SECONDS = 300
# Stable namespace so replaying the same stop/job produces the same IDs after a
# process restart; the spool can then dedupe by message_id instead of duplicating.
AGENT_ID_NAMESPACE = uuid.UUID("6f4d1f8e-6f0a-5c1c-9d4b-2f3d6a7b8c90")

EXECUTION_STATUSES = frozenset({"NOT_STARTED", "RUNNING", "COMPLETED", "ABORTED", "SKIPPED"})
VALIDITY_STATUSES = frozenset({"VALID", "INVALID", "BLOCKED", "UNKNOWN"})
BUSINESS_VERDICTS = frozenset(
    {"PASS", "FAIL", "EXPECTED", "WARN", "NEEDS_REVIEW", "NOT_EVALUATED"}
)
EVIDENCE_STATUSES = frozenset({"COMPLETE", "INCOMPLETE", "CONFLICTED", "UNVERIFIED"})
RECEIPT_STATUSES = frozenset(
    {
        "accepted",
        "rejected",
        "started",
        "completed",
        "failed",
        "stopped",
        "blocked",
        "infra_error",
        "cleanup_complete",
    }
)
OUTCOME_KEYS = frozenset(
    {
        "node_observed_execution_status",
        "node_observed_validity_status",
        "node_observed_business_verdict",
        "node_observed_evidence_status",
        "node_observed_verification_status",
        "used_for_decision",
    }
)

FORBIDDEN_FACT_KEYS = frozenset(
    {
        "business_verdict",
        "verification_status",
        "execution_status",
        "validity_status",
        "evidence_status",
        "platform_verdict",
        "release_status",
    }
)

RELEASE_BLOCKERS = (
    "local_stop_confirmed",
    "safe_cleanup_done",
    "occupancy_reconciled",
)


class FactsOnlyViolation(ValueError):
    """Raised when a payload tries to publish a platform-owned decision field."""


def uuid_str() -> str:
    return str(uuid.uuid4())


def deterministic_id(*parts: object) -> str:
    """Stable UUID for replay-safe spool keys (same inputs -> same id)."""
    return str(uuid.uuid5(AGENT_ID_NAMESPACE, ":".join(str(part) for part in parts)))


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def iso_after(value: str, seconds: float) -> str:
    return (parse_iso(value) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def nonce() -> str:
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode("ascii").rstrip("=")[:22]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def payload_digest(payload: Any) -> str:
    """``sha256:`` digest of the canonical payload, as bound by the envelope."""
    encoded = canonical_json(payload).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    uri: str
    sha256: str
    size_bytes: int
    signature: str | None = None
    key_id: str | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ArtifactRef:
        artifact_id = str(raw["artifact_id"])
        sha256 = str(raw["sha256"]).lower()
        signature_raw = raw.get("signature")
        key_id_raw = raw.get("key_id")
        return cls(
            artifact_id=artifact_id,
            uri=str(raw.get("uri", f"sim://artifact/{artifact_id}")),
            sha256=sha256,
            size_bytes=int(raw.get("size_bytes", 0)),
            signature=str(signature_raw) if signature_raw is not None else None,
            key_id=str(key_id_raw) if key_id_raw is not None else None,
        )


@dataclass(frozen=True, slots=True)
class StopSignal:
    signal_id: str
    job_id: str
    lease_id: str
    epoch: int
    reason: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> StopSignal:
        return cls(
            signal_id=str(raw.get("signal_id", raw.get("message_id", uuid_str()))),
            job_id=str(raw["job_id"]),
            lease_id=str(raw["lease_id"]),
            epoch=int(raw["epoch"]),
            reason=str(raw.get("reason", "control_plane_stop")),
        )


@dataclass(frozen=True, slots=True)
class JobMessage:
    job_id: str
    lease_id: str
    epoch: int
    attempt: int
    run_id: str | None
    artifacts: tuple[ArtifactRef, ...]
    artifact_contents: Mapping[str, bytes]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> JobMessage:
        artifacts: list[ArtifactRef] = []
        contents: dict[str, bytes] = {}
        raw_artifacts = raw.get("artifacts", [])
        if isinstance(raw_artifacts, list):
            for item in raw_artifacts:
                if not isinstance(item, Mapping):
                    raise ValueError("artifact entry must be an object")
                ref = ArtifactRef.from_mapping(item)
                artifacts.append(ref)
                encoded = item.get("content_b64")
                if encoded is not None:
                    try:
                        contents[ref.artifact_id] = base64.b64decode(
                            str(encoded), validate=True
                        )
                    except (binascii.Error, ValueError) as exc:
                        raise ValueError(
                            f"invalid artifact content for {ref.artifact_id}"
                        ) from exc
        run_id_raw = raw.get("run_id")
        return cls(
            job_id=str(raw["job_id"]),
            lease_id=str(raw["lease_id"]),
            epoch=int(raw["epoch"]),
            attempt=int(raw.get("attempt", 1)),
            run_id=str(run_id_raw) if run_id_raw is not None else None,
            artifacts=tuple(artifacts),
            artifact_contents=contents,
        )


@dataclass(frozen=True, slots=True)
class CommandMessage:
    """An allow-listed tool invocation claimed from the platform queue.

    ``args`` is parsed but never interpolated into a command line: the tool
    registry owns the executable and its fixed arguments.
    """

    command_id: str
    tool_id: str
    args: Mapping[str, Any]
    timeout_seconds: int

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CommandMessage:
        command_id = str(raw["command_id"])
        tool_id = str(raw["tool_id"])
        args_raw = raw.get("args")
        if args_raw is None:
            args: Mapping[str, Any] = {}
        elif isinstance(args_raw, Mapping):
            args = args_raw
        else:
            raise ValueError("command args must be an object")
        try:
            timeout_seconds = int(raw.get("timeout_seconds", 30))
        except (TypeError, ValueError) as exc:
            raise ValueError("command timeout_seconds must be an integer") from exc
        if timeout_seconds <= 0:
            raise ValueError("command timeout_seconds must be positive")
        return cls(
            command_id=command_id,
            tool_id=tool_id,
            args=args,
            timeout_seconds=timeout_seconds,
        )


@dataclass(slots=True)
class LeaseTracker:
    """Tracks the newest lease epoch observed from the control plane."""

    lease_id: str | None = None
    epoch: int = -1
    job_id: str | None = None

    def observe(self, lease_id: str, epoch: int, job_id: str | None = None) -> bool:
        if self.epoch >= 0:
            # Fencing: never move backwards, and never let a different lease
            # reuse the current epoch. A genuinely new lease must bump epoch.
            if epoch < self.epoch:
                return False
            if epoch == self.epoch and self.lease_id is not None and lease_id != self.lease_id:
                return False
        self.lease_id = lease_id
        self.epoch = epoch
        self.job_id = job_id
        return True

    def matches(self, lease_id: str, epoch: int) -> bool:
        return self.lease_id == lease_id and self.epoch == epoch

    def applies(self, lease_id: str, epoch: int) -> bool:
        """Only a STOP carrying the current fencing token may change the run."""
        if self.epoch < 0:
            return True
        return epoch == self.epoch and (
            self.lease_id is None or lease_id == self.lease_id
        )

    def clear(self) -> None:
        self.lease_id = None
        self.epoch = -1
        self.job_id = None

    def to_dict(self) -> dict[str, object]:
        return {"lease_id": self.lease_id, "epoch": self.epoch, "job_id": self.job_id}

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> LeaseTracker:
        lease_id_raw = raw.get("lease_id")
        epoch_raw = raw.get("epoch")
        if lease_id_raw is None or epoch_raw is None:
            return cls()
        try:
            epoch = int(str(epoch_raw))
        except ValueError:
            return cls()
        job_id_raw = raw.get("job_id")
        return cls(
            lease_id=str(lease_id_raw),
            epoch=epoch,
            job_id=str(job_id_raw) if job_id_raw is not None else None,
        )


def build_node_observed_outcome(
    *,
    execution_status: str,
    validity_status: str,
    business_verdict: str,
    evidence_status: str,
) -> dict[str, object]:
    if execution_status not in EXECUTION_STATUSES:
        raise ValueError(f"invalid node execution status: {execution_status}")
    if validity_status not in VALIDITY_STATUSES:
        raise ValueError(f"invalid node validity status: {validity_status}")
    if business_verdict not in BUSINESS_VERDICTS:
        raise ValueError(f"invalid node business verdict: {business_verdict}")
    if evidence_status not in EVIDENCE_STATUSES:
        raise ValueError(f"invalid node evidence status: {evidence_status}")
    return {
        "node_observed_execution_status": execution_status,
        "node_observed_validity_status": validity_status,
        "node_observed_business_verdict": business_verdict,
        "node_observed_evidence_status": evidence_status,
        "node_observed_verification_status": "NOT_RUN",
        "used_for_decision": False,
    }


def assert_facts_only(value: Any, path: str = "payload") -> None:
    """Reject platform decision keys anywhere in a node-produced payload."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text in FORBIDDEN_FACT_KEYS:
                raise FactsOnlyViolation(f"{path}.{key_text} is platform-owned")
            assert_facts_only(item, f"{path}.{key_text}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_facts_only(item, f"{path}[{index}]")


def assert_node_observed_outcome(outcome: Mapping[str, object]) -> None:
    """Enforce the exact facts-only outcome shape at the receipt boundary."""
    keys = set(outcome)
    if keys != OUTCOME_KEYS:
        missing = sorted(OUTCOME_KEYS - keys)
        extra = sorted(keys - OUTCOME_KEYS)
        raise FactsOnlyViolation(
            f"outcome must contain exactly node_observed_* fields; "
            f"missing={missing} extra={extra}"
        )
    if outcome["used_for_decision"] is not False:
        raise FactsOnlyViolation("outcome.used_for_decision must be False")
    if outcome["node_observed_verification_status"] != "NOT_RUN":
        raise FactsOnlyViolation("node_observed_verification_status must be NOT_RUN")
    execution_status = str(outcome["node_observed_execution_status"])
    validity_status = str(outcome["node_observed_validity_status"])
    business_verdict = str(outcome["node_observed_business_verdict"])
    evidence_status = str(outcome["node_observed_evidence_status"])
    if execution_status not in EXECUTION_STATUSES:
        raise FactsOnlyViolation(f"invalid node execution status: {execution_status}")
    if validity_status not in VALIDITY_STATUSES:
        raise FactsOnlyViolation(f"invalid node validity status: {validity_status}")
    if business_verdict not in BUSINESS_VERDICTS:
        raise FactsOnlyViolation(f"invalid node business verdict: {business_verdict}")
    if evidence_status not in EVIDENCE_STATUSES:
        raise FactsOnlyViolation(f"invalid node evidence status: {evidence_status}")


def build_receipt(
    *,
    node_id: str,
    job: JobMessage,
    status: str,
    outcome: Mapping[str, object],
    facts: Mapping[str, object],
    started_at: str,
    finished_at: str | None,
    duration_ms: int,
    sequence: int = 1,
    error: Mapping[str, object] | None = None,
    cleanup_receipt: Mapping[str, object] | None = None,
    artifacts: list[Mapping[str, object]] | None = None,
    node_boot_id: str | None = None,
    node_restart_count: int = 0,
    receipt_id: str | None = None,
    message_id: str | None = None,
) -> dict[str, object]:
    if status not in RECEIPT_STATUSES:
        raise ValueError(f"invalid receipt status: {status}")
    assert_node_observed_outcome(outcome)
    boot_id = node_boot_id or uuid_str()
    try:
        uuid.UUID(boot_id)
    except ValueError as exc:
        raise ValueError(f"node_boot_id must be a canonical UUID: {boot_id}") from exc
    issued_at = utc_now_iso()
    payload: dict[str, object] = {
        "receipt_id": receipt_id or uuid_str(),
        "job_id": job.job_id,
        "attempt": job.attempt,
        "lease_id": job.lease_id,
        "epoch": job.epoch,
        "sequence": sequence,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": max(0, duration_ms),
        "outcome": dict(outcome),
        "facts": dict(facts),
        "error": dict(error) if error is not None else None,
        "evidence_manifest": None,
        "cleanup_receipt": dict(cleanup_receipt) if cleanup_receipt is not None else None,
        "artifacts": list(artifacts or []),
        "log_query_result": None,
        "idempotency_key": f"{job.job_id}:{job.attempt}:{status}",
        "node_boot_id": boot_id,
        "node_restart_count": node_restart_count,
    }
    receipt: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "message_type": "receipt",
        "sender_role": "node",
        "message_id": message_id or uuid_str(),
        "node_id": node_id,
        "job_id": job.job_id,
        "lease_id": job.lease_id,
        "epoch": job.epoch,
        "nonce": nonce(),
        "issued_at": issued_at,
        "expires_at": iso_after(issued_at, RECEIPT_TTL_SECONDS),
        "payload_hash": payload_digest(payload),
        "payload": payload,
    }
    assert_facts_only(receipt)
    return receipt
