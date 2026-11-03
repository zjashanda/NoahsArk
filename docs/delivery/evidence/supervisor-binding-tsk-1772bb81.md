# Supervisor Binding Verification — tsk-1772bb81

**Date:** 2026-10-30
**Task:** `tsk-1772bb81` (`1772bb81-73f6-447c-b4dc-c34eb59be818`), title `Original`
**Question:** does task creation produce a durable `PENDING` supervisor binding?
**Verdict:** **PASS.** The binding is written as `PENDING` in the same committed
transaction as the task and its first revision, is visible to a separate
process after the creating process exits, and only then transitions through the
supervisor lifecycle.

## What was checked

### 1. Creation path is one transaction with an explicit `PENDING` state

`apps/control_plane/noahsark/services/supervision.py::create_task_with_supervisor`
(reached from `POST /api/v1/tasks` via `api/writes.py` →
`services/writes.execute_idempotent`):

- `SUPERVISOR_STATE_ON_CREATE = "PENDING"`; the row is created with
  `remote_session_id=None`.
- Rows are flushed in FK order inside one transaction: `Task` → `TaskRevision` →
  `SupervisorSession`.
- Only `prompt_digest` (sha256) and `prompt_bytes` are stored; the raw prompt is
  absent from the supervisor row and from `task_revisions.content`.
- Three append-only audit events are written in the same transaction:
  `TASK_CREATED`, `TASK_REVISION_CREATED`, `SUPERVISOR_SESSION_CREATED`
  (the last records `state=PENDING`, `remote_session_id=null`).

### 2. Live rows and audit chain for this task

Read-only queries against the configured PostgreSQL database:

| Fact | Value |
|---|---|
| Task | `tsk-1772bb81`, status `DRAFT`, created `2026-10-30T07:12:54.450055Z` |
| Binding | `sup-e5d1af85` (`e5d1af85-8286-4b32-8ca7-012cab32d74c`), same `created_at` |
| Creation audit | `SUPERVISOR_SESSION_CREATED` at `07:12:54.456609Z` with `state=PENDING`, `remote_session_id=null` |
| Current state | `RUNNING`; remote OpenCode session set; `updated_at` `07:17:14.025618Z` |
| Prompt record | `sha256:0f1f7c60…c7778`, `57` bytes |
| Side effects | 0 runs, 0 verdicts, 0 evidence items |

This task was produced by the fixture `test_same_key_with_different_payload_conflicts`
(title `Original`). The `PENDING` state is the creation state; the later
`RUNNING` state is the expected result of the separate supervisor worker
claiming the committed row, not a missing binding.

### 3. Durability across processes (isolated probe)

On a scratch database (never the dev database):

1. Process A seeded the schema and posted a task through the real FastAPI app;
   the response reported `supervisor_state=PENDING`,
   `prompt_digest=sha256:f0b529…`, `prompt_bytes=54`.
2. Process A exited. Process B then opened a **new** connection and read:
   `tsk-e3939c5f` / `sup-d2325f0e`, `state=PENDING`,
   `remote_session_id=NULL`, `created_at == updated_at`
   (`2026-10-30T07:18:15.971449Z`), plus the three-event audit chain ending in
   `SUPERVISOR_SESSION_CREATED` with `state=PENDING`.

A row that was never claimed therefore remained durably `PENDING` and readable
by another process after the creator terminated.

### 4. Isolated-database regression run

A scratch database `noahsark_verify_1772bb81` was created (owner `noahsark`),
migrated with `alembic upgrade head` (head `f6a2c8d41e07`), and the supervisor
suite was run against it:

```bash
cd /home/bszheng/NoahsArk/apps/control_plane
DATABASE_URL=postgresql+asyncpg://…/noahsark_verify_1772bb81 \
  python -m pytest tests/test_task_supervisor.py -q
```

Result: **9 passed**. Post-run scratch state: 4 untouched creations left one
`PENDING` binding each with `remote_session_id IS NULL`; 1 `BINDING` and 1
`COMPLETED` row reflected test manipulation. The development database was
snapshotted before and after: **8 tasks / 7 bindings / 23 audit events,
unchanged**. The scratch database was then dropped; only `noahsark` remains.

### 5. Database-enforced invariants (live schema)

- `ck_supervisor_sessions_state_closed` restricts state to the nine declared
  lifecycle values.
- `ck_supervisor_sessions_prompt_bytes_non_negative`.
- FKs to `tasks(task_id)` and `task_revisions(revision_id)`.
- Unique `display_id` and unique `remote_session_id`.
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id`
  `WHERE state IN ('PENDING','BINDING','READY','DISPATCHED','RUNNING','STOP_REQUESTED')`,
  so at most one active binding exists per task while terminal rows remain as
  history.

## Boundary statement

This evidence covers the control-plane creation path, cross-process durability,
database constraints and the isolated regression suite. It does not claim
production readiness, hardware execution, a frozen contract, or any change to
code, migrations or configuration. As recorded for `tsk-49b4be2c`, DB-resetting
tests must stay on a dedicated database/schema; this run followed that rule.
