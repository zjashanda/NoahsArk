from types import SimpleNamespace

from noahsark.services.domain_rules import (
    attempt_denominator_eligible,
    gate_is_formal_denominator,
    lease_signal_projection,
    progress_projection,
)


def test_g4_smoke_is_never_formal_denominator():
    assert gate_is_formal_denominator("G4") is False
    assert gate_is_formal_denominator("G5") is True


def test_formal_denominator_requires_all_exact_facts():
    assert attempt_denominator_eligible(
        run_mode="formal",
        evidence_origin="real_device",
        validity_status="VALID",
        evidence_status="COMPLETE",
        execution_status="COMPLETED",
    )
    assert not attempt_denominator_eligible(
        run_mode="smoke",
        evidence_origin="real_device",
        validity_status="VALID",
        evidence_status="COMPLETE",
        execution_status="COMPLETED",
    )
    assert not attempt_denominator_eligible(
        run_mode="formal",
        evidence_origin="simulated",
        validity_status="VALID",
        evidence_status="COMPLETE",
        execution_status="COMPLETED",
    )
    assert not attempt_denominator_eligible(
        run_mode="formal",
        evidence_origin="real_device",
        validity_status="VALID",
        evidence_status="INCOMPLETE",
        execution_status="COMPLETED",
    )


def test_offline_running_occupied_granted_stays_separate():
    lease = SimpleNamespace(
        communication_state="OFFLINE",
        occupancy_state="OCCUPIED",
        execution_permit="GRANTED",
    )
    run = SimpleNamespace(execution_status="RUNNING")
    projection = lease_signal_projection(lease, run=run)
    assert projection["offline_while_active"] is True
    assert projection["signals_merged"] is False
    assert projection["communication_implies_execution_stopped"] is False
    assert projection["communication_implies_device_idle"] is False


def test_progress_only_counts_with_approved_total_exposes_percent():
    counted = progress_projection(completed=5, total=10)
    assert counted["mode"] == "COUNTS"
    assert counted["percent"] == 50.0

    unknown = progress_projection(completed=None, total=None)
    assert unknown["mode"] == "INDETERMINATE"
    assert unknown["percent"] is None

    qualitative = progress_projection(completed=3, total=None)
    assert qualitative["mode"] == "QUALITATIVE"
    assert qualitative["percent"] is None
