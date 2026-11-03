"""W8 Wave 1: simulated gate/release chain invariants (L2 only).

The tests join the existing control-plane rules to the simulated node-agent
cleanup facts. They make no real-device, production, or RPO/RTO claim.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from conftest import (
    FakeControlPlane,
    flush_receipts,
    job_item,
    lease_item,
    receipt_statuses,
    stop_item,
)
from noahsark.services.domain_rules import (
    GATE_ORDER,
    device_availability,
    gate_can_enter,
    gate_sequence,
    lease_release_projection,
    lease_signal_projection,
    lease_transition_blockers,
)
from noahsark_node.cleanup import release_preconditions


def _gate(code: str, status: str = "PENDING", **extra: object) -> SimpleNamespace:
    return SimpleNamespace(gate_code=code, status=status, **extra)


def _blocker_codes(blockers: list[dict[str, object]]) -> list[str]:
    return [str(blocker["code"]) for blocker in blockers]


def _stopped_receipt(fake: FakeControlPlane) -> dict[str, object]:
    return next(
        receipt for receipt in fake.receipts if receipt["payload"]["status"] == "stopped"
    )


def _stopped_cleanup(fake: FakeControlPlane) -> dict[str, object]:
    return _stopped_receipt(fake)["payload"]["cleanup_receipt"]


def test_gate_ordering_rejects_a_gate_passed_before_its_predecessor() -> None:
    gates = [
        _gate("G0", "PENDING"),
        _gate("G1", "PASSED"),
        _gate("G2", "PASSED"),
    ]

    projection = gate_sequence(gates)
    by_code = {gate["gate_code"]: gate for gate in projection["gates"]}

    assert projection["order"] == list(GATE_ORDER)
    assert projection["current_gate"] == "G0"
    assert projection["blocked"] is True
    assert projection["gates_are_business_pass"] is False
    assert projection["business_verdict"] is None

    for code in ("G1", "G2"):
        gate = by_code[code]
        assert gate["status"] == "PASSED"
        assert gate["sequence_valid"] is False
        assert gate["actionable"] is False
        assert _blocker_codes(gate["blockers"]) == ["GATE_PREDECESSOR_NOT_PASSED"]
        assert "G0" in gate["blockers"][0]["message"]

    allowed_g1, g1_blockers = gate_can_enter("G1", gates)
    assert allowed_g1 is False
    assert _blocker_codes(g1_blockers) == ["GATE_PREDECESSOR_NOT_PASSED"]

    allowed_g0, g0_blockers = gate_can_enter("G0", gates)
    assert allowed_g0 is True
    assert g0_blockers == []


def test_smoke_gate_never_contributes_to_the_formal_business_pass() -> None:
    gates = [_gate(code, "PASSED") for code in ("G0", "G1", "G2", "G3", "G4")]

    projection = gate_sequence(gates)
    by_code = {gate["gate_code"]: gate for gate in projection["gates"]}

    assert by_code["G4"]["status"] == "PASSED"
    assert by_code["G4"]["denominator_contribution"] is False
    assert by_code["G5"]["status"] == "PENDING"
    assert by_code["G5"]["denominator_contribution"] is True
    assert by_code["G5"]["business_verdict"] is None

    assert projection["smoke_gate"] == "G4"
    assert projection["formal_gate"] == "G5"
    assert projection["smoke_in_formal_denominator"] is False
    assert projection["gates_are_business_pass"] is False
    assert projection["business_verdict"] is None
    assert projection["current_gate"] == "G5"


def test_release_stays_held_until_all_prerequisites_and_never_self_transitions(
    make_agent, signer
) -> None:
    fake = FakeControlPlane()
    agent = make_agent(fake, signer=signer)
    fake.polls.append(
        [
            stop_item(
                signal_id="stop-w8-release",
                job_id="job-w8-release",
                lease_id="lease-w8-release",
                epoch=1,
            )
        ]
    )

    report = agent.run_cycle()

    assert report.release_confirmed is False
    assert report.blockers == ("occupancy_reconciled",)

    cleanup = _stopped_cleanup(fake)
    assert cleanup["local_stop_confirmed"] is True
    assert cleanup["safe_cleanup_done"] is True
    assert cleanup["occupancy_reconciled"] is False

    lease = SimpleNamespace(
        state="HELD",
        occupancy_state="OCCUPIED",
        epoch=1,
        release_preconditions={
            "local_stop_confirmed": cleanup["local_stop_confirmed"],
            "safe_cleanup_done": cleanup["safe_cleanup_done"],
            "occupancy_reconciled": cleanup["occupancy_reconciled"],
        },
    )
    run = SimpleNamespace(cleanup_receipt_id=cleanup["cleanup_receipt_id"])
    node = SimpleNamespace(communication_state="ONLINE")

    before = lease_release_projection(lease, run=run, node=node)
    assert before["release_confirmed"] is False
    assert before["missing"] == ["occupancy_reconciled"]
    assert before["release_state"] == "held"
    assert before["occupancy_state"] == "OCCUPIED"

    reconciled = {
        "state": "HELD",
        "occupancy_state": "OCCUPIED",
        "epoch": 1,
        "release_preconditions": {
            "local_stop_confirmed": True,
            "safe_cleanup_done": True,
            "occupancy_reconciled": True,
        },
    }
    after = lease_release_projection(reconciled, run=run, node=node)

    assert after["release_confirmed"] is True
    assert after["missing"] == []
    assert after["release_state"] == "held"
    assert after["lease_state"] == "HELD"
    assert after["occupancy_state"] == "OCCUPIED"
    assert after["released_at"] is None
    assert after["independent_of_verdict"] is True


def test_release_transition_is_fenced_by_preconditions_and_terminal_states() -> None:
    direct_release = lease_transition_blockers("HELD", "RELEASED")
    assert _blocker_codes(direct_release) == ["LEASE_INVALID_TRANSITION"]

    assert lease_transition_blockers("HELD", "RELEASING") == []

    missing = lease_transition_blockers("RELEASING", "RELEASED")
    assert _blocker_codes(missing) == ["LEASE_RELEASE_PRECONDITION_FAILED"]
    message = str(missing[0]["message"])
    for prerequisite in (
        "local_stop_confirmed",
        "safe_cleanup_done",
        "occupancy_reconciled",
        "cleanup_receipt",
        "r05_node_reachable_or_on_site_confirmed",
    ):
        assert prerequisite in message

    preconditions = {
        "local_stop_confirmed": True,
        "safe_cleanup_done": True,
        "occupancy_reconciled": True,
    }
    allowed = lease_transition_blockers(
        "RELEASING",
        "RELEASED",
        preconditions=preconditions,
        cleanup_receipt_present=True,
        r05_satisfied=True,
    )
    assert allowed == []

    terminal = lease_transition_blockers("RELEASED", "RELEASING")
    assert _blocker_codes(terminal) == ["LEASE_TERMINAL_STATE"]

    quarantined_release = lease_transition_blockers("QUARANTINED", "RELEASED")
    assert _blocker_codes(quarantined_release) == ["LEASE_INVALID_TRANSITION"]

    invalid = lease_transition_blockers("GRANTED", "RELEASING")
    assert _blocker_codes(invalid) == ["LEASE_INVALID_TRANSITION"]

    quarantine = lease_transition_blockers(
        "HELD", "QUARANTINED", occupancy_state="IDLE"
    )
    assert _blocker_codes(quarantine) == ["LEASE_QUARANTINE_REQUIRES_OCCUPIED"]


def test_stop_first_cycle_orders_the_six_contract_steps_and_executes_no_job(
    make_agent, signer
) -> None:
    fake = FakeControlPlane()
    agent = make_agent(fake, signer=signer)
    job_id = "job-w8-six-step"
    lease_id = "lease-w8-six-step"
    fake.polls.append(
        [
            job_item(job_id=job_id, lease_id=lease_id, epoch=1),
            stop_item(
                signal_id="stop-w8-six-step", job_id=job_id, lease_id=lease_id, epoch=1
            ),
        ]
    )

    stopping = agent.run_cycle()

    assert stopping.steps == [
        "register",
        "heartbeat",
        "poll",
        "stop",
        "stop_actions",
        "upload",
        "dedupe",
        "reconcile",
    ]
    assert stopping.stop_handled is True
    assert stopping.jobs_executed == 0
    assert stopping.jobs_skipped == 0
    assert "resume" not in stopping.steps
    assert receipt_statuses(fake, job_id) == ["stopped"]
    assert "started" not in receipt_statuses(fake, job_id)
    assert "completed" not in receipt_statuses(fake, job_id)
    assert fake.uploaded_order == ["stop_action", "receipt"]

    resumed = agent.run_cycle()

    assert resumed.steps == [
        "heartbeat",
        "poll",
        "upload",
        "dedupe",
        "reconcile",
        "resume",
    ]
    assert resumed.stop_handled is False
    assert resumed.jobs_executed == 0
    assert [*stopping.steps[3:], resumed.steps[-1]] == [
        "stop",
        "stop_actions",
        "upload",
        "dedupe",
        "reconcile",
        "resume",
    ]
    assert list(dict.fromkeys([*stopping.steps, *resumed.steps])) == [
        "register",
        "heartbeat",
        "poll",
        "stop",
        "stop_actions",
        "upload",
        "dedupe",
        "reconcile",
        "resume",
    ]
    assert receipt_statuses(fake, job_id) == ["stopped"]


def test_pending_job_receipts_upload_only_after_the_new_stop_action(
    make_agent, signer
) -> None:
    fake = FakeControlPlane()
    agent = make_agent(fake, signer=signer)
    lease_id = "lease-w8-backfill"
    completed_job = "job-w8-backfill-completed"
    stopped_job = "job-w8-backfill-stopped"
    fake.polls.append(
        [job_item(job_id=completed_job, lease_id=lease_id, epoch=1)]
    )

    executed = agent.run_cycle()

    assert executed.jobs_executed == 1
    assert fake.receipts == []
    assert agent.spool.count_pending() == 2

    fake.polls.append(
        [
            stop_item(
                signal_id="stop-w8-backfill",
                job_id=stopped_job,
                lease_id=lease_id,
                epoch=1,
            )
        ]
    )

    stopped = agent.run_cycle()

    assert stopped.stop_handled is True
    assert stopped.uploaded == 4
    assert agent.spool.count_pending() == 0
    assert fake.uploaded_order == ["stop_action", "receipt", "receipt", "receipt"]
    assert fake.actions[0]["job_id"] == stopped_job
    assert fake.actions[0]["local_stop_confirmed"] is True
    assert [receipt["payload"]["job_id"] for receipt in fake.receipts] == [
        stopped_job,
        completed_job,
        completed_job,
    ]
    assert [receipt["payload"]["status"] for receipt in fake.receipts] == [
        "stopped",
        "started",
        "completed",
    ]


def test_duplicate_stop_and_job_for_a_stopped_lease_are_fenced(
    make_agent, signer
) -> None:
    fake = FakeControlPlane()
    agent = make_agent(fake, signer=signer)
    lease_id = "lease-w8-duplicate"
    stopped_job = "job-w8-duplicate-stop"
    later_job = "job-w8-duplicate-later"
    fake.polls.append([lease_item(lease_id=lease_id, epoch=1)])
    agent.run_cycle()

    stop = stop_item(
        signal_id="stop-w8-duplicate",
        job_id=stopped_job,
        lease_id=lease_id,
        epoch=1,
    )
    fake.polls.append([stop, stop])

    first = agent.run_cycle()

    assert first.stop_handled is True
    assert first.uploaded == 2
    assert fake.uploaded_order == ["stop_action", "receipt"]
    assert len(fake.actions) == 1
    assert len(fake.receipts) == 1
    assert receipt_statuses(fake, stopped_job) == ["stopped"]

    fake.polls.append(
        [stop, job_item(job_id=later_job, lease_id=lease_id, epoch=1)]
    )

    replay = agent.run_cycle()

    assert replay.stop_handled is False
    assert replay.jobs_executed == 0
    assert replay.jobs_skipped == 1
    assert receipt_statuses(fake, later_job) == []
    assert len(fake.receipts) == 1


def test_late_stop_preserves_completed_receipt_history(make_agent, signer) -> None:
    fake = FakeControlPlane()
    agent = make_agent(fake, signer=signer)
    job_id = "job-w8-late-stop"
    lease_id = "lease-w8-late-stop"
    fake.polls.append([job_item(job_id=job_id, lease_id=lease_id, epoch=1)])
    agent.run_cycle()
    flush_receipts(agent, fake)

    assert receipt_statuses(fake, job_id) == ["started", "completed"]
    history = [
        (receipt["payload"]["receipt_id"], receipt["payload"]["status"])
        for receipt in fake.receipts
    ]

    fake.polls.append(
        [
            stop_item(
                signal_id="stop-w8-late", job_id=job_id, lease_id=lease_id, epoch=1
            )
        ]
    )
    delayed = agent.run_cycle()

    assert delayed.stop_handled is True
    assert receipt_statuses(fake, job_id) == ["started", "completed", "stopped"]
    assert [
        (receipt["payload"]["receipt_id"], receipt["payload"]["status"])
        for receipt in fake.receipts[:2]
    ] == history
    assert fake.receipts[2]["payload"]["job_id"] == job_id


def test_offline_signals_stay_independent_and_reconnect_never_re_executes(
    make_agent, signer
) -> None:
    signals = lease_signal_projection(
        {
            "communication_state": "OFFLINE",
            "occupancy_state": "OCCUPIED",
            "execution_permit": "GRANTED",
        },
        run={"execution_status": "RUNNING"},
    )

    assert signals["communication_state"] == "OFFLINE"
    assert signals["occupancy_state"] == "OCCUPIED"
    assert signals["execution_permit"] == "GRANTED"
    assert signals["execution_status"] == "RUNNING"
    assert signals["offline_while_active"] is True
    assert signals["communication_implies_execution_stopped"] is False
    assert signals["communication_implies_device_idle"] is False
    assert signals["expiry_releases_occupancy"] is False
    assert signals["signals_merged"] is False

    availability = device_availability(
        pool_state="READY",
        health_state="HEALTHY",
        communication_state="OFFLINE",
        occupancy_state="OCCUPIED",
    )
    assert availability["available"] is False
    assert availability["reasons"] == ["COMMUNICATION_NOT_ONLINE", "OCCUPANCY_NOT_IDLE"]
    assert availability["offline_is_idle"] is False

    fake = FakeControlPlane()
    first = make_agent(fake, signer=signer, spool_name="reconnect.sqlite3")
    job = job_item(
        job_id="job-w8-reconnect",
        lease_id="lease-w8-reconnect",
        epoch=1,
    )
    fake.polls.append([job])

    initial = first.run_cycle()

    assert initial.jobs_executed == 1
    flush_receipts(first, fake)
    assert receipt_statuses(fake, "job-w8-reconnect") == ["started", "completed"]
    first.spool.close()

    reconnected = make_agent(fake, signer=signer, spool_name="reconnect.sqlite3")
    assert reconnected.node_restart_count == 1
    fake.polls.append([job])

    replay = reconnected.run_cycle()

    assert replay.jobs_executed == 0
    assert replay.jobs_skipped == 1
    assert receipt_statuses(fake, "job-w8-reconnect") == ["started", "completed"]
    assert len(fake.receipts) == 2


def test_release_requires_control_plane_reconciliation_not_a_node_claim(
    make_agent, signer
) -> None:
    fake = FakeControlPlane()
    agent = make_agent(fake, signer=signer)
    fake.polls.append(
        [
            stop_item(
                signal_id="stop-w8-reconcile",
                job_id="job-w8-reconcile",
                lease_id="lease-w8-reconcile",
                epoch=1,
            )
        ]
    )

    held = agent.run_cycle()

    assert held.release_confirmed is False
    assert held.blockers == ("occupancy_reconciled",)
    cleanup = _stopped_cleanup(fake)
    assert cleanup["local_stop_confirmed"] is True
    assert cleanup["safe_cleanup_done"] is True
    assert cleanup["occupancy_reconciled"] is False

    node_only = release_preconditions(
        cleanup, occupancy_reconciled=bool(cleanup["occupancy_reconciled"])
    )
    assert node_only.can_confirm_release is False
    assert node_only.blockers == ("occupancy_reconciled",)

    fake.reconciled = True
    fake.polls.append([])
    confirmed = agent.run_cycle()

    assert confirmed.release_confirmed is True
    assert confirmed.blockers == ()
    assert _stopped_cleanup(fake)["occupancy_reconciled"] is False


def test_release_confirmation_never_creates_a_business_pass(
    make_agent, signer
) -> None:
    fake = FakeControlPlane()
    fake.reconciled = True
    agent = make_agent(fake, signer=signer)
    fake.polls.append(
        [
            stop_item(
                signal_id="stop-w8-release-pass",
                job_id="job-w8-release-pass",
                lease_id="lease-w8-release-pass",
                epoch=1,
            )
        ]
    )

    report = agent.run_cycle()

    assert report.release_confirmed is True
    assert report.blockers == ()
    stopped = _stopped_receipt(fake)
    outcome = stopped["payload"]["outcome"]
    assert outcome["node_observed_business_verdict"] == "NOT_EVALUATED"
    assert outcome["node_observed_verification_status"] == "NOT_RUN"
    assert outcome["used_for_decision"] is False

    gates = gate_sequence([_gate(code, "PENDING") for code in GATE_ORDER])
    assert gates["business_verdict"] is None
    assert gates["gates_are_business_pass"] is False
    assert gates["current_gate"] == "G0"
    assert all(gate["business_verdict"] is None for gate in gates["gates"])

    cleanup = _stopped_cleanup(fake)
    release = lease_release_projection(
        {
            "state": "HELD",
            "occupancy_state": "OCCUPIED",
            "epoch": 1,
            "release_preconditions": {
                "local_stop_confirmed": cleanup["local_stop_confirmed"],
                "safe_cleanup_done": cleanup["safe_cleanup_done"],
                "occupancy_reconciled": True,
            },
        },
        run={"cleanup_receipt_id": cleanup["cleanup_receipt_id"]},
        node={"communication_state": "ONLINE"},
    )
    assert release["release_confirmed"] is True
    assert release["independent_of_verdict"] is True
    assert "business_verdict" not in release


def test_gate_and_release_projections_recompute_identically_after_json_reload(
    make_agent, signer
) -> None:
    fake = FakeControlPlane()
    fake.reconciled = True
    agent = make_agent(fake, signer=signer)
    fake.polls.append(
        [
            stop_item(
                signal_id="stop-w8-reload",
                job_id="job-w8-reload",
                lease_id="lease-w8-reload",
                epoch=1,
            )
        ]
    )
    agent.run_cycle()
    cleanup = _stopped_cleanup(fake)

    gates = [_gate(code, "PASSED") for code in GATE_ORDER]
    original_gates = gate_sequence(gates)
    reloaded_gates = json.loads(
        json.dumps([{"gate_code": gate.gate_code, "status": gate.status} for gate in gates])
    )
    replayed_gates = gate_sequence([SimpleNamespace(**gate) for gate in reloaded_gates])

    assert replayed_gates == original_gates
    assert replayed_gates["business_verdict"] is None

    release_facts = {
        "lease": {
            "state": "HELD",
            "occupancy_state": "OCCUPIED",
            "epoch": 1,
            "release_preconditions": {
                "local_stop_confirmed": cleanup["local_stop_confirmed"],
                "safe_cleanup_done": cleanup["safe_cleanup_done"],
                "occupancy_reconciled": True,
            },
        },
        "run": {"cleanup_receipt_id": cleanup["cleanup_receipt_id"]},
        "node": {"communication_state": "ONLINE"},
    }
    original_release = lease_release_projection(
        release_facts["lease"],
        run=release_facts["run"],
        node=release_facts["node"],
    )
    reloaded = json.loads(json.dumps(release_facts))
    replayed_release = lease_release_projection(
        reloaded["lease"], run=reloaded["run"], node=reloaded["node"]
    )

    assert original_release["release_confirmed"] is True
    assert replayed_release == original_release

    degraded = json.loads(json.dumps(release_facts))
    degraded["lease"]["release_preconditions"]["occupancy_reconciled"] = False
    degraded_release = lease_release_projection(
        degraded["lease"], run=degraded["run"], node=degraded["node"]
    )

    assert degraded_release["release_confirmed"] is False
    assert degraded_release["missing"] == ["occupancy_reconciled"]
