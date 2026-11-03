# P5-W8 End-to-End Integration Evidence

**Status:** COMPLETE AT L2 SIMULATED INTEGRATION LEVEL
**Date:** 2026-10-30

## Scope

This evidence covers the execution-plan item P5-W8 (item 24): the simulated
cross-component chain from intake and approval through gate sequencing,
STOP-first handling, reconnect/recovery, occupancy reconciliation, and release
projection. It uses the real control-plane `TestClient` and PostgreSQL seed
when configured, plus the existing deterministic Node Agent `FakeControlPlane`.

The chain is L2 in-process simulation only. It does not claim real Windows
devices, TCL/lstest execution, a production Node Agent, `/node/v1/*` HTTP
endpoints, mTLS/Ed25519 production security, production backup/recovery,
RPO/RTO, or a business PASS from release confirmation.

## Requirement Matrix

| Requirement | Evidence |
| --- | --- |
| Three intake entry modes | `test_each_entry_mode_creates_a_persisted_draft` covers conversation, file, and spreadsheet with real POST/GET persistence. |
| Approval and gate ordering | `test_approval_bridge_enables_g2_only_after_g1_passes` writes an APPROVED frozen-revision approval, then proves G2 is blocked while G1 is pending and valid after G1 is passed. |
| Missing predecessor fail-closed | `test_g2_stays_fail_closed_while_g1_is_missing` asserts `GATE_PREDECESSOR_NOT_PASSED` through both projections. |
| STOP request is not completion | `test_stop_first_cycle_orders_the_six_contract_steps_and_executes_no_job` receives STOP and a job together; the job is not executed. |
| STOP-first ordering | The same test asserts the exact `register -> heartbeat -> poll -> stop -> stop_actions -> upload -> dedupe -> reconcile` sequence and subsequent `resume` only after reconciliation. |
| Pending receipt backfill | `test_pending_job_receipts_upload_only_after_the_new_stop_action` asserts `stop_action` uploads before the STOP receipt and prior started/completed receipts. |
| Duplicate STOP/job fencing | `test_duplicate_stop_and_job_for_a_stopped_lease_are_fenced` proves duplicate STOP is idempotent and a later job on the stopped lease is skipped. |
| Completed history preservation | `test_late_stop_preserves_completed_receipt_history` keeps `started`, `completed`, then appends `stopped`. |
| Disconnect/reconnect semantics | `test_offline_signals_stay_independent_and_reconnect_never_re_executes` preserves OCCUPIED/GRANTED/RUNNING while offline and proves a restarted agent does not execute a completed job again. |
| Control-plane occupancy reconciliation | `test_release_requires_control_plane_reconciliation_not_a_node_claim` keeps release blocked until the control-plane reconciliation response is true; node cleanup alone cannot satisfy occupancy reconciliation. |
| Release is not business PASS | `test_release_confirmation_never_creates_a_business_pass` keeps node verdict `NOT_EVALUATED`, verification `NOT_RUN`, and `used_for_decision=false`. |
| Projection recovery/reload | `test_gate_and_release_projections_recompute_identically_after_json_reload` recomputes gate and release projections from reloaded facts and changes only when a persisted fact changes. |

## Commands And Results

With the existing control-plane `.env` sourced without printing its values:

```text
.venv/bin/python -m pytest tests/integration -o addopts='' --disable-warnings -q
17 passed, 1 warning in 1.53s

.venv/bin/python -m pytest tests/integration/test_p5_w8_simulated_chain.py -o addopts='' --disable-warnings -q
12 passed in 0.41s

.venv/bin/python -m pytest tests/integration/test_p5_w8_write_bridge.py -o addopts='' --disable-warnings -q
5 passed in 0.64s

.venv/bin/ruff check tests/integration
All checks passed!
```

The same integration command without an exported `DATABASE_URL` produced
`12 passed, 5 skipped`; the five skips were the DB bridge cases and were due to
the shell not exporting the configured PostgreSQL URL. The supplemental run
above sourced the existing application environment and executed those cases
against PostgreSQL. No credentials or connection values were printed.

Existing baseline suites were also rerun separately:

```text
apps/node_agent: 50 passed
apps/control_plane: 141 passed
```

`basedpyright`/LSP remains unavailable because it is not installed and its
installation was previously declined. Ruff and the repository's existing
mypy checks remain the available static gates.

## Residual Findings

- The current control plane has no `/node/v1/*` HTTP endpoint. The Node Agent
  half is therefore exercised through the deterministic in-process transport.
- Recovery evidence is spool/restart and projection reload, not host/database
  disaster recovery. No RPO/RTO value is asserted.
- `gate_can_enter` returns the sequence flag rather than independently
  rejecting every stored blocker on a pending gate. These W8 tests use both
  `gate_sequence` and exact blocker assertions; hardening that admission helper
  is deferred rather than silently changed in this wave.
- W7 remains `[~]` pending its separately tracked browser evidence state; W8
  does not alter or claim W7 completion.

**Recommendation:** P5-W8 item 24 is complete for the L2 simulated integration
boundary. Real-device, HTTP node transport, and production recovery remain
explicitly outside this acceptance.
