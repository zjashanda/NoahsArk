"""Pure W2 domain guards: gates, run/attempt, lease/occupancy, progress.

These helpers deliberately accept either ORM rows or plain mappings and never
touch a session.  They encode the invariants that routers and read models must
share so the five axes, release preconditions and gate order cannot drift
between projections.

Rules implemented here (see docs/contracts/domain.md §7.2, §9, §11 and
docs/contracts/evidence-verdict.md §13.3):

* Gates advance strictly G0 -> G7; G4 smoke never contributes to the formal
  denominator; a gate PASS is never a business PASS.
* Denominator eligibility is the exact formal + real_device + VALID + COMPLETE
  + COMPLETED tuple; retries/attempts stay separate records.
* Release requires local stop, safe cleanup, occupancy reconciliation, a
  cleanup receipt and R-05 (node reachable or on-site confirmation).  Missing
  cleanup only holds the device: it never makes the device IDLE.
* Progress percentages exist only for ``COUNTS`` with ``total > 0``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

GATE_ORDER: tuple[str, ...] = ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7")
GATE_LABELS: dict[str, str] = {
    "G0": "intake_review",
    "G1": "freeze_approval",
    "G2": "static_check",
    "G3": "resource_eligibility_and_lease",
    "G4": "real_device_smoke",
    "G5": "formal_sampling",
    "G6": "evidence_review_and_verdict",
    "G7": "report_and_knowledge",
}
NON_SKIPPABLE_GATES = frozenset({"G1", "G5", "G6"})
SMOKE_GATE = "G4"
FORMAL_GATE = "G5"
GATE_RUN_MODES: dict[str, str] = {"G2": "static", "G4": "smoke", "G5": "formal"}

RUN_LIFECYCLE_STATES: tuple[str, ...] = (
    "CREATED",
    "DISPATCHED",
    "RUNNING",
    "FINISHING",
    "COMPLETED",
    "STOPPED",
    "ABORTED",
    "BLOCKED",
)
RUN_TERMINAL_STATES = frozenset({"COMPLETED", "STOPPED", "ABORTED", "BLOCKED"})
RUN_TRANSITIONS: dict[str, frozenset[str]] = {
    "CREATED": frozenset({"DISPATCHED", "STOPPED", "ABORTED", "BLOCKED"}),
    "DISPATCHED": frozenset({"RUNNING", "STOPPED", "ABORTED", "BLOCKED"}),
    "RUNNING": frozenset({"FINISHING", "STOPPED", "ABORTED", "BLOCKED"}),
    "FINISHING": frozenset({"COMPLETED", "STOPPED", "ABORTED", "BLOCKED"}),
    "COMPLETED": frozenset(),
    "STOPPED": frozenset(),
    "ABORTED": frozenset(),
    "BLOCKED": frozenset(),
}

DENOMINATOR_RUN_MODE = "formal"
DENOMINATOR_EVIDENCE_ORIGIN = "real_device"
DENOMINATOR_EXCLUDED_FAILURES = frozenset(
    {
        "INVALID_INPUT",
        "INVALID_ENVIRONMENT",
        "INVALID_EVIDENCE",
        "BLOCKED",
        "STOPPED",
        "UNSUPPORTED",
        "INFRA_ERROR",
    }
)

LEASE_STATES: tuple[str, ...] = (
    "GRANTED",
    "HELD",
    "RELEASING",
    "RECLAIM_PENDING",
    "RELEASED",
    "QUARANTINED",
)
LEASE_TERMINAL_STATES = frozenset({"RELEASED"})
LEASE_TRANSITIONS: dict[str, frozenset[str]] = {
    "GRANTED": frozenset({"HELD", "RELEASED"}),
    "HELD": frozenset({"RELEASING", "RECLAIM_PENDING", "QUARANTINED"}),
    "RECLAIM_PENDING": frozenset({"HELD", "RELEASING", "QUARANTINED"}),
    "RELEASING": frozenset({"RELEASED", "QUARANTINED"}),
    "RELEASED": frozenset(),
    "QUARANTINED": frozenset({"HELD", "RELEASING"}),
}
RELEASE_PRECONDITION_KEYS: tuple[str, ...] = (
    "local_stop_confirmed",
    "safe_cleanup_done",
    "occupancy_reconciled",
)

PROGRESS_MODES: tuple[str, ...] = ("COUNTS", "QUALITATIVE", "INDETERMINATE")
APPROVED_DENOMINATOR_KINDS = frozenset(
    {"APPROVED_CASE_COUNT", "APPROVED_EVIDENCE_ITEM_COUNT"}
)


def _get(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _upper(value: Any, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    return str(value).upper()


def _owner(source: Any) -> Any:
    return _get(source, "blocker_owner")


def _normalise_blockers(raw: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, Mapping):
            result.append(dict(item))
        else:
            result.append({"code": str(item)})
    return result


def _blocker(code: str, message: str, owner: Any = None) -> dict[str, Any]:
    return {"code": code, "message": message, "owner": owner}


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------
def gate_is_formal_denominator(gate_code: str) -> bool:
    """G4 smoke is always excluded from the formal denominator (G-3)."""

    return gate_code != SMOKE_GATE


def gate_run_mode_blockers(gate_code: str, run_mode: str | None) -> list[dict[str, Any]]:
    expected = GATE_RUN_MODES.get(gate_code)
    if expected is None:
        return []
    actual = _upper(run_mode, "UNKNOWN").lower()
    if actual == expected:
        return []
    return [
        _blocker(
            "GATE_RUN_MODE_MISMATCH",
            f"{gate_code} requires mode={expected}, got mode={actual}",
        )
    ]


def gate_sequence(gates: Iterable[Any]) -> dict[str, Any]:
    """Return the ordered G0-G7 projection with derived blockers.

    Stored blockers are preserved verbatim.  Sequence blockers are added when a
    gate is IN_PROGRESS/PASSED before its predecessors passed, when a forbidden
    gate is SKIPPED, or when a SKIP has no recorded reason.  A gate status of
    PASSED therefore never silently becomes a business PASS.
    """

    by_code: dict[str, Any] = {}
    for gate in gates or []:
        code = _get(gate, "gate_code")
        if code in GATE_ORDER and code not in by_code:
            by_code[code] = gate

    results: list[dict[str, Any]] = []
    satisfied: set[str] = set()
    current_gate: str | None = None
    blocked = False

    for index, code in enumerate(GATE_ORDER):
        gate = by_code.get(code)
        status = _upper(_get(gate, "status"), "PENDING")
        owner = _owner(gate)
        stored = _normalise_blockers(_get(gate, "blockers", []))
        blockers: list[dict[str, Any]] = list(stored)
        missing = [predecessor for predecessor in GATE_ORDER[:index] if predecessor not in satisfied]
        sequence_valid = True

        if status in ("IN_PROGRESS", "PASSED") and missing:
            sequence_valid = False
            blockers.append(
                _blocker(
                    "GATE_PREDECESSOR_NOT_PASSED",
                    f"{code} cannot be {status} before {missing[0]} is PASSED",
                    owner,
                )
            )

        if status == "SKIPPED":
            if code in NON_SKIPPABLE_GATES:
                sequence_valid = False
                blockers.append(
                    _blocker(
                        "GATE_SKIP_NOT_ALLOWED",
                        f"{code} may not be SKIPPED",
                        owner,
                    )
                )
            if not str(_get(gate, "notes", "") or "").strip():
                sequence_valid = False
                blockers.append(
                    _blocker(
                        "GATE_SKIP_REASON_MISSING",
                        f"{code} SKIPPED requires an explicit human reason",
                        owner,
                    )
                )

        if status in ("FAILED", "BLOCKED") and not stored:
            blockers.append(
                _blocker(f"GATE_{status}", f"{code} is {status}", owner)
            )

        if status in ("PASSED", "SKIPPED") and sequence_valid:
            satisfied.add(code)

        if current_gate is None and status not in ("PASSED", "SKIPPED"):
            current_gate = code
        if blockers:
            blocked = True

        results.append(
            {
                "gate_id": _get(gate, "gate_id"),
                "display_id": _get(gate, "display_id"),
                "gate_code": code,
                "order_index": index,
                "label": GATE_LABELS[code],
                "status": status,
                "run_id": _get(gate, "run_id"),
                "entered_at": _get(gate, "entered_at"),
                "exited_at": _get(gate, "exited_at"),
                "evaluated_by": _get(gate, "evaluated_by"),
                "blocker_owner": owner,
                "blockers": blockers,
                "evidence_refs": list(_get(gate, "evidence_refs", []) or []),
                "notes": _get(gate, "notes"),
                "version": _get(gate, "version"),
                "sequence_valid": sequence_valid,
                "actionable": status in ("PENDING", "IN_PROGRESS") and sequence_valid,
                "business_verdict": None,
                "denominator_contribution": gate_is_formal_denominator(code),
            }
        )

    return {
        "order": list(GATE_ORDER),
        "gates": results,
        "current_gate": current_gate,
        "blocked": blocked,
        "gates_are_business_pass": False,
        "business_verdict": None,
        "smoke_gate": SMOKE_GATE,
        "formal_gate": FORMAL_GATE,
        "smoke_in_formal_denominator": False,
    }


def gate_can_enter(gate_code: str, gates: Iterable[Any]) -> tuple[bool, list[dict[str, Any]]]:
    projection = gate_sequence(gates)
    for gate in projection["gates"]:
        if gate["gate_code"] == gate_code:
            return gate["sequence_valid"], list(gate["blockers"])
    return False, [_blocker("GATE_UNKNOWN", f"unknown gate {gate_code}")]


# ---------------------------------------------------------------------------
# Run / Attempt
# ---------------------------------------------------------------------------
def run_transition_blockers(
    current_status: str, target_status: str
) -> list[dict[str, Any]]:
    current = _upper(current_status)
    target = _upper(target_status)
    allowed = RUN_TRANSITIONS.get(current)
    if allowed is None:
        return [
            _blocker(
                "RUN_UNKNOWN_STATE",
                f"unknown run lifecycle status {current}",
            )
        ]
    if target in allowed:
        return []
    if not allowed:
        return [
            _blocker(
                "RUN_TERMINAL_STATE",
                f"{current} is terminal and cannot transition to {target}",
            )
        ]
    return [
        _blocker(
            "RUN_INVALID_TRANSITION",
            f"{current} cannot transition to {target}",
        )
    ]


def run_transition_allowed(current_status: str, target_status: str) -> bool:
    return not run_transition_blockers(current_status, target_status)


def attempt_denominator_reasons(
    *,
    run_mode: str | None,
    evidence_origin: str | None,
    validity_status: str | None,
    evidence_status: str | None,
    execution_status: str | None,
    failure_classification: str | None = None,
) -> list[str]:
    """Reasons an attempt is outside the formal denominator (empty = eligible)."""

    reasons: list[str] = []
    if _upper(run_mode) != _upper(DENOMINATOR_RUN_MODE):
        reasons.append("RUN_MODE_NOT_FORMAL")
    if _upper(evidence_origin) != _upper(DENOMINATOR_EVIDENCE_ORIGIN):
        reasons.append("EVIDENCE_ORIGIN_NOT_REAL_DEVICE")
    if _upper(validity_status) != "VALID":
        reasons.append("VALIDITY_NOT_VALID")
    if _upper(evidence_status) != "COMPLETE":
        reasons.append("EVIDENCE_NOT_COMPLETE")
    if _upper(execution_status) != "COMPLETED":
        reasons.append("EXECUTION_NOT_COMPLETED")
    if failure_classification and _upper(failure_classification) in DENOMINATOR_EXCLUDED_FAILURES:
        reasons.append("FAILURE_CLASSIFICATION_EXCLUDED")
    return reasons


def attempt_denominator_eligible(
    *,
    run_mode: str | None,
    evidence_origin: str | None,
    validity_status: str | None,
    evidence_status: str | None,
    execution_status: str | None,
    failure_classification: str | None = None,
) -> bool:
    return not attempt_denominator_reasons(
        run_mode=run_mode,
        evidence_origin=evidence_origin,
        validity_status=validity_status,
        evidence_status=evidence_status,
        execution_status=execution_status,
        failure_classification=failure_classification,
    )


def attempt_guards(attempts: Iterable[Any]) -> dict[str, Any]:
    """Validate ordinal monotonicity, retry links and attempt independence."""

    items = list(attempts or [])
    identity = lambda item: str(_get(item, "attempt_id") or _get(item, "display_id") or id(item))
    identifiers = [identity(item) for item in items]
    merged = len(set(identifiers)) != len(identifiers)

    ordinals: dict[tuple[str, str], list[int]] = {}
    for item in items:
        key = (str(_get(item, "run_id")), str(_get(item, "case_id")))
        ordinal = _get(item, "attempt_ordinal")
        if isinstance(ordinal, int):
            ordinals.setdefault(key, []).append(ordinal)

    ordinal_blockers: list[dict[str, Any]] = []
    for key, values in ordinals.items():
        if any(value < 1 for value in values):
            ordinal_blockers.append(
                _blocker("ATTEMPT_ORDINAL_NON_POSITIVE", f"{key} has ordinal < 1")
            )
        if len(set(values)) != len(values):
            ordinal_blockers.append(
                _blocker("ATTEMPT_ORDINAL_DUPLICATE", f"{key} repeats an ordinal")
            )

    by_id = {identity(item): item for item in items}
    retry_blockers: list[dict[str, Any]] = []
    for item in items:
        retry_of = _get(item, "retry_of_attempt_id")
        if retry_of is None:
            continue
        parent = by_id.get(str(retry_of))
        if parent is None:
            retry_blockers.append(
                _blocker(
                    "ATTEMPT_RETRY_SOURCE_MISSING",
                    f"{identity(item)} retries an unknown attempt",
                )
            )
            continue
        if str(_get(parent, "run_id")) != str(_get(item, "run_id")):
            retry_blockers.append(
                _blocker(
                    "ATTEMPT_RETRY_CROSS_RUN",
                    f"{identity(item)} retries an attempt in another run",
                )
            )
        parent_ordinal = _get(parent, "attempt_ordinal")
        child_ordinal = _get(item, "attempt_ordinal")
        if (
            isinstance(parent_ordinal, int)
            and isinstance(child_ordinal, int)
            and parent_ordinal >= child_ordinal
        ):
            retry_blockers.append(
                _blocker(
                    "ATTEMPT_RETRY_ORDER",
                    f"{identity(item)} retry ordinal must exceed its source",
                )
            )

    blockers = [*ordinal_blockers, *retry_blockers]
    if merged:
        blockers.append(
            _blocker("ATTEMPT_MERGED", "attempt identities must remain distinct")
        )
    return {
        "unique_attempts": not merged,
        "attempts_merged": merged,
        "ordinals_valid": not ordinal_blockers,
        "retry_links_valid": not retry_blockers,
        "flaky_is_observation_only": True,
        "flaky_overrides_first_result": False,
        "per_attempt_results_preserved": True,
        "blockers": blockers,
    }


# ---------------------------------------------------------------------------
# Lease / release
# ---------------------------------------------------------------------------
def lease_transition_blockers(
    current_state: str,
    target_state: str,
    *,
    preconditions: Mapping[str, Any] | None = None,
    cleanup_receipt_present: bool | None = None,
    r05_satisfied: bool | None = None,
    occupancy_state: str | None = None,
) -> list[dict[str, Any]]:
    current = _upper(current_state)
    target = _upper(target_state)
    allowed = LEASE_TRANSITIONS.get(current)
    blockers: list[dict[str, Any]] = []
    if allowed is None:
        return [_blocker("LEASE_UNKNOWN_STATE", f"unknown lease state {current}")]
    if target not in allowed:
        if not allowed:
            return [
                _blocker(
                    "LEASE_TERMINAL_STATE",
                    f"{current} is terminal and cannot transition to {target}",
                )
            ]
        return [
            _blocker(
                "LEASE_INVALID_TRANSITION",
                f"{current} cannot transition to {target}",
            )
        ]

    if target == "RELEASED":
        values = {
            key: bool((preconditions or {}).get(key, False))
            for key in RELEASE_PRECONDITION_KEYS
        }
        missing = [key for key, value in values.items() if not value]
        if cleanup_receipt_present is not True:
            missing.append("cleanup_receipt")
        if r05_satisfied is not True:
            missing.append("r05_node_reachable_or_on_site_confirmed")
        if missing:
            blockers.append(
                _blocker(
                    "LEASE_RELEASE_PRECONDITION_FAILED",
                    "release requires all preconditions: " + ", ".join(missing),
                )
            )

    if (
        target == "QUARANTINED"
        and occupancy_state is not None
        and _upper(occupancy_state) != "OCCUPIED"
    ):
        blockers.append(
            _blocker(
                "LEASE_QUARANTINE_REQUIRES_OCCUPIED",
                "QUARANTINED leases must remain OCCUPIED",
            )
        )
    return blockers


def lease_transition_allowed(current_state: str, target_state: str) -> bool:
    return not lease_transition_blockers(current_state, target_state)


def lease_release_projection(
    lease: Any | None,
    *,
    run: Any | None = None,
    node: Any | None = None,
    on_site_confirmed: bool = False,
) -> dict[str, Any]:
    """Project release state from lease + the three booleans + cleanup + R-05."""

    stored = _get(lease, "release_preconditions", None) if lease is not None else None
    stored = stored or {}
    preconditions = {
        key: bool(stored.get(key, False)) for key in RELEASE_PRECONDITION_KEYS
    }
    preconditions_met = all(preconditions.values())
    cleanup_receipt_present = bool(
        run is not None and _get(run, "cleanup_receipt_id", None) is not None
    )
    r05_node_reachable = bool(
        node is not None and _upper(_get(node, "communication_state")) == "ONLINE"
    )
    r05_satisfied = r05_node_reachable or bool(on_site_confirmed)
    release_confirmed = (
        preconditions_met and cleanup_receipt_present and r05_satisfied
    )

    missing = [key for key, value in preconditions.items() if not value]
    if not cleanup_receipt_present:
        missing.append("cleanup_receipt")
    if not r05_satisfied:
        missing.append("r05_node_reachable_or_on_site_confirmed")

    state = _upper(_get(lease, "state"), "") if lease is not None else ""
    released_at = _get(lease, "released_at", None) if lease is not None else None
    lease_occupancy = _upper(_get(lease, "occupancy_state"), "") if lease is not None else ""

    if lease is None:
        release_state = "not_applicable"
        occupancy_state = "UNKNOWN"
    elif state == "QUARANTINED":
        release_state = "quarantined"
        occupancy_state = "OCCUPIED"
    elif state == "RELEASED" or released_at is not None:
        release_state = "released"
        occupancy_state = "IDLE" if release_confirmed else "OCCUPIED"
    elif state in ("RELEASING", "RECLAIM_PENDING"):
        release_state = "release_requested"
        occupancy_state = lease_occupancy or "OCCUPIED"
    elif release_confirmed and lease_occupancy == "IDLE":
        release_state = "released"
        occupancy_state = "IDLE"
    elif preconditions_met and not cleanup_receipt_present:
        release_state = "held_pending_cleanup"
        occupancy_state = "OCCUPIED"
    elif preconditions_met and cleanup_receipt_present and not r05_satisfied:
        release_state = "held_pending_reconciliation"
        occupancy_state = "OCCUPIED"
    else:
        release_state = "held"
        occupancy_state = lease_occupancy or "OCCUPIED"

    return {
        "release_state": release_state,
        "preconditions": preconditions,
        "preconditions_met": preconditions_met,
        "cleanup_receipt_present": cleanup_receipt_present,
        "r05_satisfied": r05_satisfied,
        "r05_node_reachable": r05_node_reachable,
        "on_site_confirmed": bool(on_site_confirmed),
        "release_confirmed": release_confirmed,
        "occupancy_state": occupancy_state,
        "missing": missing,
        "lease_state": state or None,
        "lease_epoch": _get(lease, "epoch", None) if lease is not None else None,
        "released_at": released_at,
        "independent_of_verdict": True,
        "cleanup_missing_is_evidence_incomplete": False,
    }


def lease_signal_projection(
    lease: Any | None,
    *,
    run: Any | None = None,
    device: Any | None = None,
) -> dict[str, Any]:
    """Keep communication, execution, occupancy and permit as separate signals."""

    communication = (
        _get(lease, "communication_state", None)
        or _get(run, "communication_state", None)
        or _get(device, "communication_state", None)
    )
    occupancy = (
        _get(lease, "occupancy_state", None)
        or _get(device, "occupancy_state", None)
        or _get(run, "occupancy_state", None)
    )
    execution_permit = (
        _get(lease, "execution_permit", None)
        or _get(run, "execution_permit", None)
    )
    execution_status = _get(run, "execution_status", None)
    offline_active = (
        _upper(communication) == "OFFLINE"
        and _upper(execution_status) == "RUNNING"
        and _upper(occupancy) == "OCCUPIED"
        and _upper(execution_permit) == "GRANTED"
    )
    return {
        "communication_state": communication,
        "occupancy_state": occupancy,
        "execution_permit": execution_permit,
        "execution_status": execution_status,
        "offline_while_active": offline_active,
        "communication_implies_execution_stopped": False,
        "communication_implies_device_idle": False,
        "expiry_releases_occupancy": False,
        "signals_merged": False,
    }


# ---------------------------------------------------------------------------
# Device / Node
# ---------------------------------------------------------------------------
def device_availability(
    *,
    pool_state: str | None,
    health_state: str | None,
    communication_state: str | None,
    occupancy_state: str | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    if _upper(pool_state) != "READY":
        reasons.append("POOL_NOT_READY")
    if _upper(health_state) != "HEALTHY":
        reasons.append("HEALTH_NOT_HEALTHY")
    if _upper(communication_state) != "ONLINE":
        reasons.append("COMMUNICATION_NOT_ONLINE")
    if _upper(occupancy_state) != "IDLE":
        reasons.append("OCCUPANCY_NOT_IDLE")
    return {
        "available": not reasons,
        "reasons": reasons,
        "offline_is_idle": False,
        "pool_health_communication_occupancy_merged": False,
    }


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------
def progress_projection(
    *,
    completed: int | None,
    total: int | None,
    denominator_kind: str = "APPROVED_CASE_COUNT",
    trusted: bool = True,
    percent_label: str = "已完成正式用例占比",
) -> dict[str, Any]:
    """Only COUNTS with a positive approved total may expose a percent."""

    counts_allowed = (
        trusted
        and denominator_kind in APPROVED_DENOMINATOR_KINDS
        and total is not None
        and total > 0
        and completed is not None
    )
    if counts_allowed and completed is not None and total is not None:
        bounded = min(max(completed / total, 0.0), 1.0)
        return {
            "mode": "COUNTS",
            "denominator_kind": denominator_kind,
            "completed": completed,
            "total": total,
            "percent": round(bounded * 100, 1),
            "percent_label": percent_label,
        }
    if trusted and completed is not None and total is None:
        return {
            "mode": "QUALITATIVE",
            "denominator_kind": denominator_kind,
            "completed": completed,
            "total": None,
            "percent": None,
            "percent_label": None,
        }
    return {
        "mode": "INDETERMINATE",
        "denominator_kind": denominator_kind,
        "completed": completed if completed is not None else None,
        "total": total if total is not None else None,
        "percent": None,
        "percent_label": None,
    }


__all__ = [
    "APPROVED_DENOMINATOR_KINDS",
    "DENOMINATOR_EXCLUDED_FAILURES",
    "FORMAL_GATE",
    "GATE_LABELS",
    "GATE_ORDER",
    "GATE_RUN_MODES",
    "LEASE_STATES",
    "LEASE_TERMINAL_STATES",
    "LEASE_TRANSITIONS",
    "NON_SKIPPABLE_GATES",
    "PROGRESS_MODES",
    "RELEASE_PRECONDITION_KEYS",
    "RUN_LIFECYCLE_STATES",
    "RUN_TERMINAL_STATES",
    "RUN_TRANSITIONS",
    "SMOKE_GATE",
    "attempt_denominator_eligible",
    "attempt_denominator_reasons",
    "attempt_guards",
    "device_availability",
    "gate_can_enter",
    "gate_is_formal_denominator",
    "gate_run_mode_blockers",
    "gate_sequence",
    "lease_release_projection",
    "lease_signal_projection",
    "lease_transition_allowed",
    "lease_transition_blockers",
    "progress_projection",
    "run_transition_allowed",
    "run_transition_blockers",
]
