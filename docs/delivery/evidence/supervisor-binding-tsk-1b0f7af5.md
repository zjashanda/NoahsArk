# Supervisor Binding Verification — tsk-1b0f7af5

**Date:** 2026-10-30
**Task:** `tsk-1b0f7af5` (`1b0f7af5-d191-4ad3-b13a-5d0e0e9562d5`), title `Idempotent supervisor task`
**Question:** does this task's creation produce a durable `PENDING` supervisor binding?
**Verdict:** **PASS for the creation path.** The binding was written `PENDING`
inside the creating transaction, committed, and later claimed by a separate
supervisor worker process. One operational caveat is recorded at the end: the
test suite that created this fixture still points at the live development
database, so test fixtures enter the real supervisor queue.

## What was checked

### 1. Task, revision and binding were created in one write

`apps/control_plane/noahsark/services/supervision.py::create_task_with_supervisor`
is the single write path behind `POST /api/v1/tasks` (via
`services/writes.execute_idempotent`). It creates, in FK order:
`Task` → `TaskRevision` → `SupervisorSession`, with
`SUPERVISOR_STATE_ON_CREATE = "PENDING"` and `remote_session_id=None`.

Live rows (read-only queries, database `noahsark`):

| Object | Display id | Created at (UTC) |
|---|---|---|
| Task | `tsk-1b0f7af5` | `2026-10-30T07:44:27.235038Z` |
| Revision | `rev-1a5fb589` (`revision_number=1`, `change_kind=initial`) | `2026-10-30T07:44:27.235038Z` |
| Binding | `sup-9b83976d` (`9b83976d-a482-4d23-82ac-0b4256704ea4`) | `2026-10-30T07:44:27.235038Z` |

Task status is `DRAFT`; `current_revision_id` equals the binding `revision_id`;
both FKs (`task_id`, `revision_id`) hold.

### 2. Initial state was `PENDING`, recorded independently of the current row

The binding row is now `RUNNING` because it was claimed after creation, so the
initial state is read from the append-only audit chain and the stored
idempotent response, not inferred from the current row:

- Audit `SUPERVISOR_SESSION_CREATED` at `07:44:27.246269Z`,
  `object_id=sup-9b83976d`, `after.state="PENDING"`,
  `after.remote_session_id=null`,
  `reason="Supervisor binding created in PENDING state"`.
- Audit order in the same transaction: `TASK_CREATED` `07:44:27.241452Z` →
  `TASK_REVISION_CREATED` `07:44:27.244067Z` →
  `SUPERVISOR_SESSION_CREATED` `07:44:27.246269Z`.
- The persisted idempotency response for the create call contains
  `"supervisor_state": "PENDING"`, `"status": "DRAFT"`, and the same
  `task_id` / `supervisor_session_id` / `current_revision_id`.

### 3. Idempotent replay did not create a second binding

The task was created by
`tests/test_task_supervisor.py::test_idempotent_replay_returns_same_binding`,
which issues the same `POST /api/v1/tasks` twice with one `Idempotency-Key`.
The live database shows exactly one of each:

| Count | Value |
|---|---|
| `supervisor_sessions` for this task | 1 |
| `task_revisions` for this task | 1 |
| `TASK_CREATED` audit rows for `tsk-1b0f7af5` | 1 |
| `idempotency_keys` for this task | 1 |
| `runs` / `verdicts` / `evidence_items` for this task | 0 / 0 / 0 |

The idempotency row is `scope="POST /api/v1/tasks"`,
`key="test-supervisor-e03e353b540f4548aa60cd7362f028ab"`, `status_code=201`,
`request_hash="sha256:44f2c72e2bfbcc6f242d95e7fcfa8112be21caad4def183718a0eb0d66fc92e0"`.
Recomputing `request_fingerprint("/api/v1/tasks", payload)` from the task fields
(`title`, `objective`, `entry_mode`, `task_category`, `lead_agent_id`,
`lead_session_id`, `prompt`, `project_id=None`) reproduces that hash exactly, so
the replay key is bound to this precise payload and the second POST returned the
stored response instead of inserting.

### 4. Durability across processes

- The binding was committed by the task-creation process at `07:44:27Z`; the
  test process exited afterwards.
- A separate, already-running supervisor worker
  (`python -m noahsark.supervisor`, PID `206093`, started `15:12` local) read
  and claimed the `PENDING` row, transitioning
  `PENDING → BINDING → READY → DISPATCHED → RUNNING`
  (`apps/control_plane/noahsark/supervisor/repository.py::claim_next` uses
  `FOR UPDATE SKIP LOCKED`, then compare-and-set transitions).
- The worker stored `remote_session_id=ses_e743931d2ffehhqDLgZTctKK92` and
  `result_updated_at=2026-10-30T07:47:04.402099Z`.

This is the behaviour under verification: the `PENDING` binding existed durably
and was readable by another process before any dispatch happened.

### 5. Database-enforced invariants (live schema)

`\d supervisor_sessions` on the live database shows:

- `state` default `'PENDING'`;
- `ck_supervisor_sessions_state_closed` — nine declared lifecycle values only;
- `ck_supervisor_sessions_prompt_bytes_non_negative`;
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id` where
  state is one of `PENDING, BINDING, READY, DISPATCHED, RUNNING, STOP_REQUESTED`,
  i.e. at most one active binding per task while terminal rows remain history;
- unique `display_id` and unique `remote_session_id`;
- FKs to `tasks(task_id)` and `task_revisions(revision_id)`.

### 6. Prompt is stored as digest only; no execution rows

The revision content is
`{"title", "objective", "entry_mode", "prompt_bytes": 57, "prompt_digest": "sha256:0f1f7c60…c7778"}`.
`sha256("Open the task and prepare a plan. Never echo this prompt.")` equals the
stored digest and its UTF-8 length is 57 bytes. A search of the revision content
for the raw prompt text returns 0 rows, and task creation produced no run,
verdict or evidence row.

### 7. Read projection (read-only GET)

`GET /api/v1/tasks/tsk-1b0f7af5/supervisor` returned HTTP 200 with
`state: RUNNING`, `state_is_terminal: false`,
`remote_session_id: "ses_***KK92"`, `remote_session_id_masked: true`, prompt
exposed only as `{digest, bytes}`, `binding.one_active_session_per_task: true`,
`binding.stable: true`, and `read_only: true`; no lease, dispatch, worker, token
or transcript fields.

## Caveat / operational finding (not a defect in the creation path)

This task is a pytest fixture, not a user-created task. Its title/objective equal
`tests/test_task_supervisor.py::_body()` (with `title` overridden) and its digest
matches that fixture's 57-byte prompt. `tests/test_task_supervisor.py` resolves
`DATABASE_URL` from settings, and its `seeded_database` fixture calls
`seed_database(reset=True)`, which issues `TRUNCATE … CASCADE`. Running that
suite against the configured development database therefore:

1. creates real `PENDING` bindings that the live supervisor worker immediately
   claims and dispatches (as happened here), and
2. deletes in-flight bindings and their audit rows on the next reseed.

The creation path itself is correct and durable; the isolation gap is in the
test/operations setup. Run DB tests only against a dedicated database/schema
(as done in the earlier `noahsark_verify_6623a9dc` run), or stop the supervisor
worker around DB-resetting test runs.

## Boundary statement

This evidence covers the control-plane creation path, the idempotent replay
path, database constraints, the read projection, and cross-process claim
behaviour for `tsk-1b0f7af5`. It claims no production readiness, no hardware
execution, no frozen contract, and no change to code, migrations or
configuration. Verification was read-only except for the `GET` projection call.
