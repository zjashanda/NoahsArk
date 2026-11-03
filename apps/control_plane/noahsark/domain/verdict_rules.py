"""Five-axis verdict derivation with a fail-closed formal PASS gate.

The five axes are always evaluated independently.  A ``PASS`` decision is only
produced when every one of the 11 formal PASS preconditions holds; any missing
precondition keeps ``formal_pass`` false even if all five axes look green.

No node-reported status, device release state or archive state is an input
here.  Release and PASS remain independent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FORMAL_PASS_PRECONDITIONS: tuple[str, ...] = (
    "approval_valid",
    "boundary_frozen",
    "mode_formal",
    "execution_completed",
    "sample_valid",
    "business_pass",
    "required_evidence_complete",
    "digest_verified",
    "linux_review_pass",
    "no_blocking_anomaly",
    "denominator_eligible",
)

AXIS_FIELDS: tuple[str, ...] = (
    "execution_status",
    "validity_status",
    "business_verdict",
    "evidence_status",
    "verification_status",
)

EXACT_FORMAL_PASS_AXES: dict[str, str] = {
    "execution_status": "COMPLETED",
    "validity_status": "VALID",
    "business_verdict": "PASS",
    "evidence_status": "COMPLETE",
    "verification_status": "PASS",
}

DECISIONS = (
    "PASS",
    "FAIL",
    "INVALID",
    "BLOCKED",
    "STOPPED",
    "NEEDS_REVIEW",
    "NOT_EVALUATED",
    "NOT_APPLICABLE",
)
MODE_OUTCOMES = ("PASS", "FAIL", "BLOCKED", "STOPPED", "NOT_EVALUATED", "NOT_APPLICABLE")
FAILURE_CLASSES = (
    "none",
    "invalid-input",
    "invalid-environment",
    "invalid-evidence",
    "blocked",
    "stopped",
    "infra-error",
    "valid-failure",
    "unsupported",
    "needs-review",
)


@dataclass(frozen=True, slots=True)
class VerdictFacts:
    """Everything the derivation may read, already resolved by the service."""

    mode: str
    execution_status: str
    validity_status: str
    business_verdict: str
    evidence_status: str
    verification_status: str
    approval_valid: bool
    boundary_frozen: bool
    required_evidence_complete: bool
    digest_verified: bool
    no_blocking_anomaly: bool
    denominator_eligible: bool
    stop_triggered: bool = False
    infra_failure: bool = False
    # Contract step-2 lease/epoch fence; deliberately not one of the 11 PASS
    # prerequisites, so it can block PASS even when all 11 are true.
    lease_fence_valid: bool = True

    @property
    def axes(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in AXIS_FIELDS}


def pass_preconditions(facts: VerdictFacts) -> dict[str, bool]:
    """Return exactly the 11 contract preconditions, never a subset."""

    return {
        "approval_valid": facts.approval_valid,
        "boundary_frozen": facts.boundary_frozen,
        "mode_formal": facts.mode == "formal",
        "execution_completed": facts.execution_status == "COMPLETED",
        "sample_valid": facts.validity_status == "VALID",
        "business_pass": facts.business_verdict == "PASS",
        "required_evidence_complete": facts.required_evidence_complete,
        "digest_verified": facts.digest_verified,
        "linux_review_pass": facts.verification_status == "PASS",
        "no_blocking_anomaly": facts.no_blocking_anomaly,
        "denominator_eligible": facts.denominator_eligible,
    }


def _mode_outcome(facts: VerdictFacts) -> str:
    if facts.stop_triggered:
        return "STOPPED"
    if facts.execution_status == "NOT_STARTED":
        return "NOT_EVALUATED"
    if (
        facts.infra_failure
        or not facts.approval_valid
        or not facts.boundary_frozen
        or not facts.lease_fence_valid
    ):
        return "BLOCKED"
    if (
        facts.business_verdict == "PASS"
        and facts.validity_status == "VALID"
        and facts.evidence_status == "COMPLETE"
        and facts.verification_status == "PASS"
    ):
        return "PASS"
    if (
        facts.business_verdict == "FAIL"
        and facts.validity_status == "VALID"
        and facts.evidence_status == "COMPLETE"
    ):
        return "FAIL"
    return "NOT_EVALUATED"


def _reason(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def derive_verdict(facts: VerdictFacts) -> dict[str, Any]:
    """Derive decision, mode outcome, failure class and pass preconditions.

    Order follows ``docs/contracts/evidence-verdict.md`` §14.2.  The first
    matching rule wins; later conditions never downgrade an earlier result.
    """

    preconditions = pass_preconditions(facts)
    mode_outcome = _mode_outcome(facts)

    if facts.mode != "formal":
        return {
            "decision": "NOT_APPLICABLE",
            "mode_outcome": mode_outcome,
            "failure_class": "none",
            "formal_pass": False,
            "pass_preconditions": preconditions,
            "denominator": {
                "eligible": False,
                "formal_denominator": False,
                "exclusion_reason": "MODE_NOT_FORMAL",
            },
            "reasons": [
                _reason(
                    "MODE_NOT_FORMAL",
                    f"mode={facts.mode} is never a formal PASS and never enters the formal denominator",
                )
            ],
        }

    decision: str
    failure_class: str
    reason: dict[str, str]
    if not facts.approval_valid or not facts.boundary_frozen:
        decision, failure_class = "BLOCKED", "blocked"
        reason = _reason(
            "APPROVAL_OR_BOUNDARY_INVALID",
            "approval or frozen boundary precondition is not satisfied",
        )
    elif not facts.lease_fence_valid:
        decision, failure_class = "BLOCKED", "blocked"
        reason = _reason(
            "LEASE_EPOCH_MISMATCH",
            "run lease or epoch does not match the current fencing token",
        )
    elif facts.execution_status == "NOT_STARTED":
        decision, failure_class = "NOT_EVALUATED", "none"
        reason = _reason("NOT_STARTED", "execution has not started")
    elif facts.stop_triggered:
        decision, failure_class = "STOPPED", "stopped"
        reason = _reason("STOP_TRIGGERED", "safety or operator stop was triggered")
    elif facts.infra_failure:
        decision, failure_class = "BLOCKED", "infra-error"
        reason = _reason("INFRA_FAILURE", "node, transport or storage infrastructure failed")
    elif facts.validity_status == "INVALID":
        decision, failure_class = "INVALID", "invalid-input"
        reason = _reason("INVALID_INPUT", "sample validity is INVALID")
    elif facts.validity_status == "BLOCKED":
        decision, failure_class = "BLOCKED", "invalid-environment"
        reason = _reason("INVALID_ENVIRONMENT", "sample validity is BLOCKED")
    elif (
        facts.evidence_status != "COMPLETE"
        or not facts.required_evidence_complete
        or not facts.digest_verified
    ):
        decision, failure_class = "BLOCKED", "invalid-evidence"
        reason = _reason(
            "INVALID_EVIDENCE",
            "required evidence is incomplete, unverified or digest-mismatched",
        )
    elif facts.verification_status != "PASS":
        decision, failure_class = "NEEDS_REVIEW", "needs-review"
        reason = _reason("LINUX_REVIEW_MISSING", "independent Linux review has not passed")
    elif not facts.no_blocking_anomaly:
        decision, failure_class = "NEEDS_REVIEW", "needs-review"
        reason = _reason("BLOCKING_ANOMALY", "an unresolved blocking anomaly exists")
    elif all(preconditions.values()):
        decision, failure_class = "PASS", "none"
        reason = _reason(
            "FORMAL_PASS",
            "required evidence verified and Linux independent review passed",
        )
    elif (
        facts.business_verdict == "FAIL"
        and facts.validity_status == "VALID"
        and facts.evidence_status == "COMPLETE"
    ):
        decision, failure_class = "FAIL", "valid-failure"
        reason = _reason("VALID_FAILURE", "business verdict failed on a valid sample")
    else:
        decision, failure_class = "NEEDS_REVIEW", "needs-review"
        reason = _reason("UNCLASSIFIED", "no automatic decision is safe")

    formal_pass = decision == "PASS" and all(preconditions.values())
    denominator = {
        "eligible": False,
        "formal_denominator": False,
        "exclusion_reason": None if formal_pass else failure_class,
    }
    if formal_pass or failure_class == "valid-failure":
        denominator = {
            "eligible": True,
            "formal_denominator": True,
            "exclusion_reason": None,
        }
    return {
        "decision": decision,
        "mode_outcome": mode_outcome,
        "failure_class": failure_class,
        "formal_pass": formal_pass,
        "pass_preconditions": preconditions,
        "denominator": denominator,
        "reasons": [reason],
    }


def exact_formal_pass_axes(facts: VerdictFacts) -> bool:
    """True only for the exact five-axis tuple, independent of prerequisites."""

    return all(facts.axes[field] == value for field, value in EXACT_FORMAL_PASS_AXES.items())


__all__ = [
    "AXIS_FIELDS",
    "DECISIONS",
    "EXACT_FORMAL_PASS_AXES",
    "FAILURE_CLASSES",
    "FORMAL_PASS_PRECONDITIONS",
    "MODE_OUTCOMES",
    "VerdictFacts",
    "derive_verdict",
    "exact_formal_pass_axes",
    "pass_preconditions",
]
