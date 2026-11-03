"""Simulated executor.

It never touches a real device. It verifies every artifact first and emits only
``node_observed_*`` facts with ``used_for_decision=false``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic

from .protocol import (
    EXECUTOR_SOURCE,
    JobMessage,
    build_node_observed_outcome,
    utc_now_iso,
)
from .verifier import ArtifactVerifier, sha256_hex


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    status: str
    outcome: dict[str, object]
    facts: dict[str, object]
    started_at: str
    finished_at: str
    duration_ms: int
    error: dict[str, object] | None = None


def _elapsed_ms(started: float) -> int:
    return max(0, int((monotonic() - started) * 1000))


class SimulatedExecutor:
    def __init__(self, verifier: ArtifactVerifier) -> None:
        self._verifier = verifier

    def _rejected(self, job: JobMessage, reason: str, started: float) -> ExecutionResult:
        outcome = build_node_observed_outcome(
            execution_status="NOT_STARTED",
            validity_status="INVALID",
            business_verdict="NOT_EVALUATED",
            evidence_status="UNVERIFIED",
        )
        facts: dict[str, object] = {
            "source": EXECUTOR_SOURCE,
            "simulated": True,
            "job_id": job.job_id,
            "lease_id": job.lease_id,
            "epoch": job.epoch,
            "artifact_check": reason,
            "executed_on_device": False,
        }
        return ExecutionResult(
            status="rejected",
            outcome=outcome,
            facts=facts,
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            duration_ms=_elapsed_ms(started),
            error={
                "code": "ARTIFACT_MISMATCH",
                "message": reason,
                "retryable": False,
            },
        )

    def execute(
        self, job: JobMessage, contents: Mapping[str, bytes] | None = None
    ) -> ExecutionResult:
        started = monotonic()
        started_at = utc_now_iso()
        content_map = job.artifact_contents if contents is None else contents

        artifact_facts: list[dict[str, object]] = []
        for artifact in job.artifacts:
            content = content_map.get(artifact.artifact_id)
            if content is None:
                return self._rejected(job, f"artifact_missing:{artifact.artifact_id}", started)
            verification = self._verifier.verify(artifact, content)
            if not verification.ok:
                return self._rejected(
                    job, f"{verification.reason}:{artifact.artifact_id}", started
                )
            artifact_facts.append(
                {
                    "artifact_id": artifact.artifact_id,
                    "sha256": sha256_hex(content),
                    "signature_key_id": artifact.key_id,
                    "signature_verified": True,
                }
            )

        finished_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        outcome = build_node_observed_outcome(
            execution_status="COMPLETED",
            validity_status="VALID",
            business_verdict="NOT_EVALUATED",
            evidence_status="UNVERIFIED",
        )
        facts: dict[str, object] = {
            "source": EXECUTOR_SOURCE,
            "simulated": True,
            "executed_on_device": False,
            "job_id": job.job_id,
            "lease_id": job.lease_id,
            "epoch": job.epoch,
            "artifact_checks": artifact_facts,
            "session_type": "service",
            "note": "simulator only; no serial, audio, power, or lstest access",
        }
        return ExecutionResult(
            status="completed",
            outcome=outcome,
            facts=facts,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=_elapsed_ms(started),
        )
