# P5-W5 Windows Node Agent Evidence

- Date: 2026-10-30
- Status: IMPLEMENTED AND VERIFIED AT NODE-AGENT SIMULATOR/TEST LEVEL
- Scope: W5 only (`apps/node_agent/`, its tests, this note). No W6 device adapter, no W7 integration, no UI/frontend, no SSH bootstrap, no control-plane route changes, no deployment, no real-device or Phase 6 acceptance.
- Plan item `21` is **not** marked complete here; the orchestrator owns the checkbox after independent review.

## Delivered

### Outbound-only cycle and CLI

- `noahsark_node/__main__.py` adds the missing `python -m noahsark_node` / `noahsark-node` entry point (`main`, `--once`, `--interval`, `--version`, clean spool close).
- `NodeAgent.run_cycle()` performs `register -> heartbeat -> poll -> STOP -> stop actions -> upload -> dedupe -> reconcile -> resume`.
- No inbound socket, bind, listener, shell, argv, or remote-command surface exists in the package.

### Lease/epoch fencing

- `LeaseTracker.observe()` rejects a lower epoch and rejects a different lease reusing the current epoch; a genuinely newer lease must bump the epoch.
- STOP for a stale epoch is ignored; STOP does not reset the epoch.
- The current lease/epoch fence is persisted in the spool `agent_state` table, so a restarted process cannot execute a stale job from before the restart.
- Jobs for a lease/epoch that already received STOP are refused even if the control plane redelivers them.

### STOP-first and cleanup

- All new STOPs in one poll are handled before any job in the same poll; jobs are deferred to a later poll.
- Spool replay order is enforced by priority: local STOP action (`0`) -> stop receipt (`5`) -> job receipts (`10`).
- STOP receipt IDs are deterministic per `(node, signal_id)`, so a crash/restart/redelivery dedupes instead of creating duplicate STOP facts.
- Cleanup receipt IDs are deterministic per `(node, job, attempt, lease, epoch)`; repeated cleanup for the same lease is idempotent.
- `receipt.cleanup_receipt` is now projected onto the R-02 minimum release shape (`cleanup_receipt_id`, `cleanup_status`, `local_stop_confirmed`, `safe_cleanup_done`, `occupancy_reconciled`, `completed_at`, optional `notes`). Detailed steps/resources remain local/evidence-side.
- The node never claims control-plane occupancy reconciliation; release requires `local_stop_confirmed` + `safe_cleanup_done` + `occupancy_reconciled`.
- The simulator executor no longer reports `local_stop_confirmed`/`safe_cleanup_done` for normal job completion; those facts come only from an actual cleanup pass.

### Artifact verification

- Every artifact requires SHA-256/size match, a present signature/key id, and a successful signature verifier before execution.
- Digest mismatch, missing content, missing signature, and invalid signature produce a `rejected` receipt with `ARTIFACT_MISMATCH`, `node_observed_execution_status=NOT_STARTED`, `node_observed_validity_status=INVALID`, and no device execution.
- The production Ed25519 verifier remains a hook; tests use the development-only HMAC verifier.

### Spool durability, retry bounds, restart

- SQLite spool persists entries, uploaded ACKs, executed job claims, and agent state across `close()`/reopen.
- `message_id` is the idempotency key; duplicate enqueue and duplicate ACK are safe.
- Temporary control-plane unavailability (`UploadDeferred`) stops the drain at the first entry and preserves order for the next cycle.
- Permanent rejection (`UploadRejected`, e.g. non-retryable 4xx) is dead-lettered (`state=rejected`) and does not block later STOP-first entries.
- Job execution spools a deterministic `started` receipt before claiming the job, then a deterministic terminal receipt.
- Restart restores: lease/epoch fence, handled STOP ids, stopped leases, boot UUID/restart count, and the last cleanup projection.

### Session 0-safe service wrapper

- `service.py` imports pywin32 only behind a guard; it is importable on Linux.
- `run_service()`/`install_service()` fail closed with the documented NSSM fallback when pywin32 is unavailable.
- The service loop now logs a crashed cycle and retries on the next interval instead of silently killing the worker thread.
- No GUI, interactive desktop, console window, or inbound IPC is created by this package.

### Receipt facts-only boundary

- `receipt.payload.outcome` contains exactly the five `node_observed_*` fields plus `used_for_decision=false`; `node_observed_verification_status` is fixed to `NOT_RUN`.
- `assert_facts_only` rejects platform-owned keys (`business_verdict`, `verification_status`, `execution_status`, `validity_status`, `evidence_status`, `platform_verdict`, `release_status`) anywhere in the receipt, including nested `facts`.
- Receipt `node_boot_id` is a canonical UUID and is no longer the invalid `dev-boot` placeholder.

## Verification commands and results

```bash
cd /home/bszheng/NoahsArk/apps/node_agent
../../.venv/bin/python -m pytest -o addopts='' --disable-warnings -q
# 49 passed in 0.95s (focused W5 suite)

cd /home/bszheng/NoahsArk/apps/node_agent
../../.venv/bin/ruff check noahsark_node tests
# All checks passed!

cd /home/bszheng/NoahsArk/apps/node_agent
../../.venv/bin/mypy noahsark_node
# Success: no issues found in 12 source files

cd /home/bszheng/NoahsArk/apps/control_plane
../../.venv/bin/python -m pytest -o addopts='' --disable-warnings -q
# 139 passed, 1 warning in 12.96s (full control-plane suite; PostgreSQL paths executed)

cd /home/bszheng/NoahsArk/apps/node_agent
../../.venv/bin/python -c "import noahsark_node, noahsark_node.__main__, noahsark_node.service; print(noahsark_node.__version__)"
# 0.1.0

cd /home/bszheng/NoahsArk/apps/node_agent
../../.venv/bin/python -m noahsark_node --help
# usage: noahsark-node [-h] [--version] [--once] [--interval SECONDS]
```

Offline smoke (control plane intentionally unreachable; spool in `/tmp`, no repo files):

```bash
cd /home/bszheng/NoahsArk/apps/node_agent
NOAHSARK_CONTROL_PLANE_URL=http://127.0.0.1:9 \
NOAHSARK_SPOOL_PATH=/tmp/noahsark-w5-smoke.sqlite3 \
NOAHSARK_ARTIFACT_CACHE_DIR=/tmp/noahsark-w5-artifacts \
../../.venv/bin/python -m noahsark_node --once
# exit 0; JSON report shows register/heartbeat/poll unavailable,
# "skipped_reason": "<urlopen error [Errno 111] Connection refused>",
# no crash, no job execution, spool left consistent.
```

## Regression coverage added

`apps/node_agent/tests/` (49 tests):

- `test_protocol_lease_receipt.py` — stale epoch, same-epoch lease conflict, epoch round-trip after restart, exact facts-only outcome, platform-key rejection, `used_for_decision=true` rejection, extra outcome key rejection, UUID boot id, deterministic replay IDs.
- `test_artifact_verification.py` — valid signed artifact executes; digest mismatch, missing content, missing signature, invalid signature are refused and reported.
- `test_spool.py` — durability across reopen, message-id idempotence, STOP-first priority order, duplicate ACK persistence, transient stop-at-first, permanent dead-letter without blocking, one-time job claim, agent-state round-trip, malformed state fail-closed.
- `test_stop_first.py` — STOP before job in the same poll, STOP action uploaded before STOP receipt, stopped lease not executed later, stale STOP ignored, all STOPs handled first, minimal cleanup projection, release gated on control-plane reconciliation, STOP does not regress epoch.
- `test_restart.py` — epoch fence survives restart, handled STOP not replayed, pending receipt replays, last cleanup projection survives, boot id/restart count.
- `test_cleanup.py` — deterministic cleanup receipt id, failure blocks release even with occupancy, missing occupancy blocks release, transport projection shape, malformed receipt rejection.
- `test_runtime_cli.py` — signature verifier selection, runtime wiring, one-cycle CLI, entry point callable, Linux service refusal, Linux service constructor safety.

## Verification-gate defects found and fixed

1. **Missing module entry point** — `pyproject.toml` declared `noahsark_node.__main__:main` and the README documented `python -m noahsark_node`, but no `__main__.py` existed. Added the CLI.
2. **Invalid `node_boot_id`** — receipts defaulted to `"dev-boot"`, which is not a UUID. Now generated per boot and validated as UUID.
3. **Wrong cleanup projection** — the full local cleanup receipt was embedded in `receipt.cleanup_receipt`, but the transport contract requires the minimum R-02 projection. Added `project_cleanup_receipt()`.
4. **Stopped lease could be re-executed** — `_stopped_leases` was populated but never consulted by `_maybe_execute`. Now jobs on a stopped lease/epoch are refused.
5. **Epoch was not restart-safe** — the fence was in-memory only, so a restart could accept stale work. Persisted and hydrated.
6. **Permanent control-plane rejection retried forever** — non-retryable 4xx was treated as transient. Now dead-lettered; transient unreachability still preserves priority order.
7. **Same-epoch lease switch accepted** — a different lease could reuse the current epoch. Now rejected; a new lease must bump the epoch.
8. **Executor claimed cleanup it never performed** — normal completion emitted `local_stop_confirmed=true`/`safe_cleanup_done=true`. Removed; cleanup facts come only from the cleanup pass.

## Limitations / not claimed

- **No real Windows hardware is accepted by these simulator tests.** Session 0 service activation, pywin32 SCM lifecycle, Windows event log, ACL/DPAPI key storage, named-pipe isolation, and interactive-session detection are **not** exercised here.
- **No TCL/lstest, audio, serial, USB, or power-control execution is claimed.** The executor is a simulator and records `simulated=true`, `executed_on_device=false`.
- **No mTLS/Ed25519 signed-envelope conformance is claimed.** Receipt `signature`/`key_id` envelope fields are not emitted; the HMAC verifier is development-only. Full signed-envelope conformance remains pending under the G-NODE decision.
- **No real control-plane `/node/v1/*` endpoints exist yet.** The outbound client is verified against a deterministic fake transport; real long-poll behavior, nonce replay cache, clock-skew handling, and server-side idempotency belong to W7+.
- **No remote artifact fetch/download.** Verification consumes simulated inline `content_b64`; the artifact cache directory is not populated.
- **Spool size limits / overflow backpressure** are not implemented; bounded retry here means transient drain stops at the first deferred entry and permanent rejections are dead-lettered.
- **No production readiness, W6 device adaptation, W7 integration, UI, or Phase 6 acceptance** is claimed. Positive verdict/release flows still depend on the control plane and real-device evidence.
