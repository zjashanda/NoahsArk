# Supervisor Binding Verification — tsk-844c214e

**Date:** 2026-10-30
**Task:** `tsk-844c214e` (`844c214e-c047-46b1-ae08-8c0d4533e955`), title `Original`
**Question:** does this task's creation produce a durable `PENDING` supervisor binding?
**Verdict:** **PASS for the creation path.** Task, initial revision and binding were
written in one transaction with `state=PENDING` and `remote_session_id NULL`,
committed, and later claimed by a separate, already-running supervisor worker
process. The operational caveat from earlier runs still applies: the test suite
that created this row points at the live development database.

## What was checked

### 1. Task, revision and binding share one write

`apps/control_plane/noahsark/services/supervision.py::create_task_with_supervisor`
is the single write path behind `POST /api/v1/tasks` (via
`services/writes.execute_idempotent`). It creates, in FK order,
`Task` → `TaskRevision` → `SupervisorSession`, with
`SUPERVISOR_STATE_ON_CREATE = "PENDING"` and `remote_session_id=None`.

Read-only rows from the live database `noahsark`:

| Object | Display id | Created at (local, +08) | Created at (UTC) |
|---|---|---|---|
| Task | `tsk-844c214e` | `2026-10-30T15:44:27.337457` | `2026-10-30T07:44:27.337457Z` |
| Revision | `rev-3d6e25ca` (`revision_number=1`, `change_kind=initial`, `status=DRAFT`) | `2026-10-30T15:44:27.337457` | `2026-10-30T07:44:27.337457Z` |
| Binding | `sup-56e3cb64` | `2026-10-30T15:44:27.337457` | `2026-10-30T07:44:27.337457Z` |

Identical `created_at` across all three rows shows a single `now = datetime.now(UTC)`
from the creating transaction. Task status is `DRAFT`, `source=control-plane`,
`seed=false`, and `current_revision_id` equals the binding `revision_id`
(`3d6e25ca-211a-4f79-8758-2239dda6bcab`); both FKs (`task_id`, `revision_id`)
hold. Task `origin.correlation_id` is `0a55f50da2c8406eab9e9a4339ce72cf`.

### 2. Initial state was `PENDING`, evidenced independently of the current row

The binding row is now `RUNNING` because it was claimed after creation, so the
creation state is read from the append-only audit chain and from the persisted
idempotent response, not inferred from the current row:

| Order | Audit action | Object | Occurred at (local) | Key payload |
|---|---|---|---|---|
| 1 | `TASK_CREATED` | `tsk-844c214e` | `15:44:27.341765` | `status=DRAFT` |
| 2 | `TASK_REVISION_CREATED` | `rev-3d6e25ca` | `15:44:27.343659` | `revision_number=1`, `change_kind=initial`, `prompt_bytes=57` |
| 3 | `SUPERVISOR_SESSION_CREATED` | `sup-56e3cb64` | `15:44:27.345271` | `state=PENDING`, `remote_session_id=null` |

The `SUPERVISOR_SESSION_CREATED` event carries
`reason="Supervisor binding created in PENDING state"` and
`after={"state": "PENDING", "remote_session_id": null, ...}`. All three events
share correlation id `0a55f50da2c8406eab9e9a4339ce72cf`.

The stored idempotent response for the create call also records
`"supervisor_state": "PENDING"` with the same `task_id`
(`844c214e-…`), `supervisor_session_id` (`56e3cb64-…`) and `revision_id`
(`3d6e25ca-…`).

### 3. Idempotency key is bound to this exact payload

`idempotency_keys` holds exactly one row for this create:

| Field | Value |
|---|---|
| `scope` | `POST /api/v1/tasks` |
| `key` | `test-supervisor-6b1f7654e9b441aa885f63cc164894d1` |
| `status_code` | `201` |
| `request_hash` | `sha256:0a2fa4dc5b7ac35d3b4a642f6a067c5656a03412607df4551808b2efe8de32ef` |
| `created_at` | `2026-10-30T15:44:27.347308+08` |
| `response.supervisor_state` | `PENDING` |

Recomputing `request_fingerprint("/api/v1/tasks", payload)` from the task fields
(`title`, `objective`, `entry_mode`, `lead_agent_id`, `lead_session_id`,
`prompt`, `task_category="voice_interaction"`, `project_id=None`) reproduces the
stored hash exactly (`0a2fa4dc…`), so the key is pinned to this payload. The
task was produced by
`tests/test_task_supervisor.py::test_same_key_with_different_payload_conflicts`
(title `Original`, then a second POST with title `Changed` expecting `409
IDEMPOTENCY_CONFLICT`); the conflicting POST added no second task or binding.

### 4. No duplicate rows were created

| Count | Value |
|---|---|
| `supervisor_sessions` for this task | 1 total / 1 active |
| `task_revisions` for this task | 1 (`revision_number=1`) |
| `TASK_CREATED` audit rows | 1 |
| `idempotency_keys` for this task | 1 |
| `runs` / `verdicts` / `evidence_items` | 0 / 0 / 0 |

### 5. Durability across processes

- The row was committed by the task-creation process at `15:44:27` local and is
  readable from independent `psql` connections (separate processes).
- A supervisor worker process (`python -m noahsark.supervisor`, PID `206093`,
  started `2026-10-30 15:12:12` local — **before** this task existed) selected
  the row via `SupervisorRepository.claim_next` (`FOR UPDATE SKIP LOCKED`,
  priority `PENDING=1`, compare-and-set state writes) and advanced it
  `PENDING → BINDING → READY → DISPATCHED → RUNNING`.
- The worker wrote `remote_session_id=ses_e743758a4ffes40geP97Lsu4rj` and
  `result_updated_at=2026-10-30T15:49:05.529719+08`
  (`2026-10-30T07:49:05.529719Z`).

That a process which started 32 minutes earlier could pick up the row, and that
the row survived the creating process's exit, is the durability property under
test: the `PENDING` binding existed durably before any dispatch.

### 6. Database-enforced invariants (live schema)

`\d supervisor_sessions`:

- `state` server default `'PENDING'::character varying`;
- `ck_supervisor_sessions_state_closed` — nine declared lifecycle values only;
- `ck_supervisor_sessions_prompt_bytes_non_negative`;
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id`
  where state ∈ `PENDING, BINDING, READY, DISPATCHED, RUNNING, STOP_REQUESTED`;
- unique `display_id`, unique `remote_session_id`;
- FKs `fk_supervisor_sessions_task_id_tasks` and
  `fk_supervisor_sessions_revision_id_task_revisions`.

Negative probes (each in a rolled-back transaction, row count unchanged at 1):

- inserting a second `PENDING` binding for the same task →
  `ERROR: duplicate key value violates unique constraint "uq_supervisor_sessions_active_task"`;
- inserting `state='BOGUS'` →
  `ERROR: violates check constraint "ck_supervisor_sessions_state_closed"`.

### 7. Prompt is stored as digest only; no execution rows

Revision `rev-3d6e25ca` content is
`{"title": "Original", "objective": "Verify the task creates a durable PENDING supervisor binding.", "entry_mode": "conversation", "prompt_bytes": 57, "prompt_digest": "sha256:0f1f7c6039b4f32ce0214a911ef52dd0d04f7a1fb920f3e81d01e25c11dc7778"}`.
The digest is the sha256 of the 57-byte fixture prompt
(`Open the task and prepare a plan. Never echo this prompt.`). Searching all
revision content for the raw prompt text returns 0 rows. Task creation produced
no run, verdict or evidence row.

### 8. Read projection (read-only GET)

`GET /api/v1/tasks/tsk-844c214e/supervisor` → HTTP `200` with:
`state="RUNNING"`, `state_is_terminal=false`,
`remote_session_id="ses_***u4rj"`, `remote_session_id_masked=true`,
prompt exposed only as `{"digest": "sha256:0f1f7c60…c7778", "bytes": 57}`,
`binding.one_active_session_per_task=true`, `binding.stable=true`,
`binding.remote_session_stored_separately=true`, `read_only=true`,
`meta.mock=false`, `meta.server_authoritative=true`. No lease, dispatch, worker,
token or transcript fields are exposed.

## Caveat / operational finding (not a defect in the creation path)

This row is a pytest fixture created by
`tests/test_task_supervisor.py`, which resolves `DATABASE_URL` from settings and
whose `seeded_database` fixture calls `seed_database(reset=True)`
(`TRUNCATE … CASCADE`). Running the suite against the configured development
database therefore:

1. creates real `PENDING` bindings that the live supervisor worker immediately
   claims and dispatches (as happened here — the task started executing this
   verification prompt), and
2. deletes in-flight bindings and their audit rows at the next reseed.

Earlier runs (`tsk-2ae1f9b0`, `tsk-6623a9dc`) lost their rows this way. The
creation path itself is correct and durable; the isolation gap is in the
test/operations setup. DB tests must target a dedicated database/schema (as in
the `noahsark_verify_6623a9dc` run) or stop the supervisor worker around
DB-resetting runs.

## Boundary statement

This evidence covers the control-plane creation path, the idempotent replay
path, database constraints, the read projection, and cross-process claim
behaviour for `tsk-844c214e`. It claims no production readiness, no hardware
execution and no frozen contract. No code, migration or configuration was
changed; verification was read-only except for the `GET` projection call and
rolled-back constraint probes.
