# Supervisor Binding Verification — tsk-96012e57

**Date:** 2026-10-30
**Task:** `tsk-96012e57` (`96012e57-26f2-478c-bac6-65a9e5b2724e`), title `Supervisor binding task`
**Question:** does this task's creation produce a durable `PENDING` supervisor binding?
**Verdict:** **PASS for the creation path.** The binding row was written with
`state='PENDING'` and `remote_session_id=NULL` in the same transaction as the
task and its first revision, was committed, and was later claimed and advanced
by a separate supervisor worker process. One operational caveat is recorded at
the end: this task itself is a pytest fixture written to the live development
database.

## What was checked

### 1. Single write path

`apps/control_plane/noahsark/services/supervision.py::create_task_with_supervisor`
(line 115) is the only write path behind `POST /api/v1/tasks` (router
`api/writes.py:152`, wrapped by `services/writes.py::execute_idempotent`). It
builds `Task` → `TaskRevision` → `SupervisorSession` in FK order, sets
`SUPERVISOR_STATE_ON_CREATE = "PENDING"` and `remote_session_id=None`
(supervision.py:39, 199-215), flushes them (216-223), appends
`TASK_CREATED` / `TASK_REVISION_CREATED` / `SUPERVISOR_SESSION_CREATED` audit
events (225-289), and `execute_idempotent` commits the transaction
(services/writes.py:113). The file mtime is `2026-10-30 16:29:51 +08`, before
this task's creation at `16:32:45 +08`, so the current code produced this row.
`git`/file inspection found no other supervisor-creation call site.

### 2. Task, revision and binding were written in one transaction

Live rows in the development database `noahsark` (read-only queries):

| Object | Display id | Created at (UTC) |
|---|---|---|
| Task | `tsk-96012e57` | `2026-10-30T08:32:45.551104Z` |
| Revision | `rev-3ec6feb9` (`revision_number=1`, `change_kind=initial`) | `2026-10-30T08:32:45.551104Z` |
| Binding | `sup-013fde61` (`013fde61-79bd-4bb8-b75a-be1d916d17f5`) | `2026-10-30T08:32:45.551104Z` |

All three share the same `created_at` to the microsecond. Task status is
`DRAFT`; `current_revision_id` equals the binding `revision_id`; the
`task_id` and `revision_id` foreign keys hold. Exactly one `supervisor_sessions`
row and one `task_revisions` row exist for this task.

### 3. Initial state was `PENDING`

The row is now `RUNNING` because it was claimed after creation, so the initial
state is taken from the append-only audit chain and the persisted idempotent
response rather than inferred from the current row:

- `SUPERVISOR_SESSION_CREATED` at `2026-10-30T08:32:45.560151Z`,
  `object_id=sup-013fde61`, `after.state="PENDING"`,
  `after.remote_session_id=null`, `after.prompt_bytes=57`,
  `after.prompt_digest="sha256:0f1f7c60…c7778"`,
  `reason="Supervisor binding created in PENDING state"`.
- Audit order in the same transaction/correlation
  (`5247beb2884d40dfa9a4b807e3027abd`, actor role `ADMIN`):
  `TASK_CREATED` `08:32:45.556338Z` → `TASK_REVISION_CREATED`
  `08:32:45.558109Z` → `SUPERVISOR_SESSION_CREATED` `08:32:45.560151Z`.
- The persisted idempotency response (`idempotency_keys`, scope
  `POST /api/v1/tasks`, key `test-supervisor-10ba587b5c894d26b8f2cd4f3854c748`,
  `status_code=201`, `request_hash=sha256:c62b6f12…02ac98`) contains
  `"created": true`, `"status": "DRAFT"`, `"supervisor_state": "PENDING"`,
  and the same `task_id` / `supervisor_session_id` / `current_revision_id`.

### 4. Durability across processes

- The creation transaction committed at `08:32:45.551104Z`; the creating process
  (the test process) exited afterwards.
- A separate supervisor worker (`python -m noahsark.supervisor`, PID `206093`,
  started `15:12:12 +08`, i.e. ~80 minutes before the task) read and claimed the
  row through `SqlSupervisorRepository.claim_next`
  (`FOR UPDATE SKIP LOCKED`, `supervisor/repository.py:149-178`), which promotes
  `PENDING → BINDING` and then advances it.
- The live row now has `state=RUNNING`,
  `remote_session_id=ses_e740f59c4ffeEpPQM0FIhUKZcg`,
  `result_updated_at=2026-10-30T16:32:46.674250+08`,
  `updated_at=2026-10-30T16:33:19.369729+08`.
- Therefore the `PENDING` row existed durably and was readable by a different
  process before any dispatch happened.

### 5. Database-enforced invariants (live schema)

`\d supervisor_sessions` on the live database shows:

- `state` default `'PENDING'` (column default and server default);
- `ck_supervisor_sessions_state_closed` — nine declared lifecycle values only;
- `ck_supervisor_sessions_prompt_bytes_non_negative`;
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id` where
  state is one of `PENDING, BINDING, READY, DISPATCHED, RUNNING, STOP_REQUESTED`
  (at most one active binding per task; terminal rows remain history);
- unique `display_id` and unique `remote_session_id`;
- FKs to `tasks(task_id)` and `task_revisions(revision_id)`.

Migration `f6a2c8d41e07_supervisor_sessions.py` is the current head (revises
`b2f1a4c7d902`) and creates exactly these objects.

### 6. Prompt stored as digest only; no execution rows

Revision content is
`{"title", "objective", "entry_mode", "prompt_bytes": 57, "prompt_digest": "sha256:0f1f7c60…c7778"}`.
`sha256("Open the task and prepare a plan. Never echo this prompt.")` equals the
stored digest and its UTF-8 length is 57 bytes. A `LIKE` search of the revision
content for the raw prompt returns 0 rows. Task creation produced `runs=0`,
`verdicts=0`, `evidence_items=0`.

### 7. Read projection

`GET /api/v1/tasks/tsk-96012e57/supervisor` (role `OBSERVER`) returned HTTP 200:

- `state=RUNNING`, `state_is_terminal=false`;
- `remote_session_id="ses_***KZcg"`, `remote_session_id_masked=true`;
- prompt exposed only as `{digest, bytes}`;
- `binding.one_active_session_per_task=true`, `binding.stable=true`,
  `binding.remote_session_stored_separately=true`;
- `read_only=true`, `meta.mock=false`, `meta.server_authoritative=true`;
- no lease, dispatch, worker, token or transcript fields.

### 8. Isolated regression

- Scratch database `noahsark_verify_96012e57` created via `postgres`,
  `alembic upgrade head` → `f6a2c8d41e07`.
- `pytest tests/test_task_supervisor.py -q` → **9 passed** (PostgreSQL, not
  skipped).
- Post-run scratch state: 4 untouched `PENDING` rows, all with
  `remote_session_id IS NULL`; 1 `BINDING`; 1 `COMPLETED`; 0 tasks with more
  than one active binding.
- Scratch database dropped. Development database counts were unchanged before
  and after (`tasks=8`, `task_revisions=11`, `supervisor_sessions=7`,
  `audit_events=23`, `runs=4`, `verdicts=0`).

## Caveat / operational finding (not a defect in the creation path)

This task is a pytest fixture, not a user-created task: its title and objective
equal `tests/test_task_supervisor.py::_body()` verbatim, its 57-byte prompt
digest matches `_body()`, and its idempotency key has the `test-supervisor-`
prefix. `tests/test_task_supervisor.py` resolves `DATABASE_URL` from settings
and its `seeded_database` fixture calls `seed_database(reset=True)`, which
issues `TRUNCATE … CASCADE`. Running that suite against the configured
development database therefore:

1. creates real `PENDING` bindings that the live supervisor worker claims and
   dispatches (as happened here), and
2. deletes in-flight bindings and their audit rows on the next reseed.

The creation path itself is correct and durable; the isolation gap is in the
test/operations setup. DB tests should run against a dedicated database/schema
(as done for the scratch regression above), or the supervisor worker should be
stopped around DB-resetting test runs.

## Boundary statement

This evidence covers the control-plane creation path, database constraints,
the read projection, and cross-process claim behaviour for `tsk-96012e57`. It
claims no production readiness, no hardware execution, no frozen contract, and
no change to code, migrations or configuration. Verification was read-only
against the development database; the only write was the throwaway scratch
database used for regression, which was dropped.
