# Supervisor Binding Verification — tsk-49b4be2c

**Date:** 2026-10-30
**Task:** `tsk-49b4be2c` (`49b4be2c-c763-45d8-92b5-dc333389102b`)
**Question:** does task creation produce a durable `PENDING` supervisor binding?
**Verdict:** **PASS for the creation path.** One caveat is recorded below:
durability does not survive a development-database reseed, and the test suite
that performs that reseed is currently pointed at the database used by the live
supervisor worker.

## What was checked

### 1. Write path is one transaction with an explicit `PENDING` initial state

`apps/control_plane/noahsark/services/supervision.py::create_task_with_supervisor`
(used by `POST /api/v1/tasks` through `services/writes.execute_idempotent`):

- `SUPERVISOR_STATE_ON_CREATE = "PENDING"` is written on the `SupervisorSession`
  row together with `remote_session_id=None`.
- Rows are flushed in FK order: `Task` → `TaskRevision` → `SupervisorSession`.
- The row stores only `prompt_digest` (sha256) and `prompt_bytes`; the raw prompt
  is not persisted in the supervisor row or in revision content.
- Three append-only audit events are written in the same transaction:
  `TASK_CREATED`, `TASK_REVISION_CREATED`, `SUPERVISOR_SESSION_CREATED`
  (the last one records `state: PENDING`, `remote_session_id: null`).

### 2. The live row and audit chain for this task

Read-only queries against the configured PostgreSQL database:

| Fact | Value |
|---|---|
| Task | `tsk-49b4be2c`, status `DRAFT`, created `2026-10-30T07:12:54.269258Z` |
| Binding | `sup-6e372e80` (`6e372e80-9a16-4689-9511-88b9efa4c58a`) |
| Binding created | `2026-10-30T07:12:54.269258Z` (same statement/timestamp as the task) |
| Current state | `RUNNING` (it was claimed after creation, see §3) |
| Prompt record | `sha256:0f1f7c60…c7778`, `57` bytes |
| Audit | `TASK_CREATED` 07:12:54.277318Z → `TASK_REVISION_CREATED` .279805Z → `SUPERVISOR_SESSION_CREATED` .282410Z with `state=PENDING` |

The stored digest equals `sha256("Open the task and prepare a plan. Never echo
this prompt.")` (57 bytes), matching the revision's `prompt_digest`; the raw
prompt text is absent from `task_revisions.content`.

### 3. Durability is demonstrated across processes, not just within a request

The binding was created by the process that ran the task-creation call and was
later claimed by the **separate** supervisor worker process
(`python -m noahsark.supervisor`, independent PID). Claiming promoted
`PENDING → BINDING` durably (`supervisor/repository.py::claim_next`), created a
remote OpenCode session, and moved the row to `RUNNING` at
`07:13:20.746Z`. This is the behaviour under verification: the `PENDING` binding
was committed and readable by another process before any dispatch happened.

### 4. Database-enforced invariants (live schema)

From `pg_indexes` / `pg_constraint` on `supervisor_sessions`:

- `ck_supervisor_sessions_state_closed` — state is restricted to the nine
  declared lifecycle values.
- `ck_supervisor_sessions_prompt_bytes_non_negative`.
- FKs to `tasks(task_id)` and `task_revisions(revision_id)`.
- Unique `display_id` and unique `remote_session_id`.
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id`
  `WHERE state IN ('PENDING','BINDING','READY','DISPATCHED','RUNNING','STOP_REQUESTED')`,
  i.e. at most one active binding per task while terminal rows remain as history.

### 5. Read projection does not leak internals

`GET /api/v1/tasks/tsk-49b4be2c/supervisor` at `07:13:36Z` returned HTTP 200:

- `state: RUNNING`, `state_is_terminal: false`;
- `remote_session_id: "ses_***s2UD"` with `remote_session_id_masked: true`;
- prompt exposed only as `{digest, bytes}`;
- `binding.one_active_session_per_task: true`, `binding.stable: true`;
- no `lease` / `dispatch` / `worker` / `token` / `transcript` fields.

### 6. Isolated-database regression run (no dev-DB writes)

A scratch database `noahsark_verify_49b4be2c` was created (owner `noahsark`),
migrated with `alembic upgrade head` (head `f6a2c8d41e07`), and the suite was run
against it:

```bash
cd /home/bszheng/NoahsArk/apps/control_plane
DATABASE_URL=postgresql+asyncpg://…/noahsark_verify_49b4be2c \
  python -m pytest tests/test_task_supervisor.py -q
```

Result: **9 passed**. Post-run scratch state showed the expected pattern: the
untouched creations left exactly one `PENDING` binding with
`remote_session_id IS NULL` (`tsk-ac468ee5`, `tsk-d2855e77`, `tsk-e764b295`),
the completed-in-test task had one `COMPLETED` plus one new `PENDING` history
row (`tsk-8fe63705`), and zero `runs`/`verdicts` were created by task creation.
The scratch database was then dropped. The development database was snapshotted
before and after: **8 tasks / 7 bindings, unchanged**.

## Caveat / finding (not a defect in the creation path)

`seed_database(reset=True)` issues `TRUNCATE … CASCADE`, which deletes
`supervisor_sessions` rows. That is why the earlier in-flight binding
`tsk-2ae1f9b0` disappeared. The same reseed happened at
`2026-10-30T07:12:54Z`, and the fixtures it created were immediately visible to
the running supervisor worker:

| Task | Title | State |
|---|---|---|
| `tsk-49b4be2c` | Supervisor binding task | `RUNNING` (this task) |
| `tsk-00f469e9` | Idempotent supervisor task | `PENDING` |
| `tsk-1772bb81` | Original | `PENDING` |
| `tsk-4279578f` | Active binding invariant | `PENDING` (+ 1 `COMPLETED` history) |
| `tsk-e05d9e29` | Projection redaction | `BINDING` |
| `tsk-bdf40444` | Supervisor binding task | `PENDING` |

So the tests that prove the binding invariant were run against the database the
live worker consumes, and their fixtures entered the supervisor queue. This
task itself (`tsk-49b4be2c`) is one of those fixtures: its title/objective equal
`tests/test_task_supervisor.py::_body()` and its digest matches that fixture's
prompt. Each dispatched verification task can create further fixtures if it
runs the same suite, so the queue can amplify.

**Recommendation:** run `tests/test_task_supervisor.py` only against a dedicated
database/schema (as done in §6), or stop the supervisor worker around
DB-resetting test runs. The creation path itself is correct and durable; the
isolation gap is in the test/operations setup.

## Boundary statement

This evidence covers the control-plane creation path, database constraints, the
read projection, and cross-process claim behaviour. It does not claim production
readiness, hardware execution, a frozen contract, or any change to code,
migrations, or configuration.
