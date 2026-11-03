# Supervisor Binding Verification — tsk-1243cdb9

**Date:** 2026-10-30
**Task:** `tsk-1243cdb9` (`1243cdb9-63b7-4031-9f60-2b1f414e191e`), title `Supervisor binding task`
**Question:** does task creation produce a durable `PENDING` supervisor binding?
**Verdict:** **PASS.** Task, revision 1 and the `PENDING` binding were committed in
one transaction at the same statement timestamp; the append-only audit chain
records `state=PENDING`, `remote_session_id=null`; and on a private PostgreSQL
cluster a never-claimed binding was read back as `PENDING` with
`remote_session_id IS NULL` and `created_at == updated_at` by a separate process
after the creator exited.

## What was verified

### 1. Creation path (code review, unchanged since previous verification)

`apps/control_plane/noahsark/services/supervision.py::create_task_with_supervisor`
(reached from `POST /api/v1/tasks` via `api/writes.py` →
`services/writes.execute_idempotent`):

- `SUPERVISOR_STATE_ON_CREATE = "PENDING"`, `remote_session_id=None`.
- Flush order inside one transaction: `Task` → `TaskRevision` → `SupervisorSession`.
- Only `prompt_digest` (sha256) and `prompt_bytes` are stored; the raw prompt is
  absent from the binding row and from `task_revisions.content`.
- Three append-only audit events in the same transaction: `TASK_CREATED`,
  `TASK_REVISION_CREATED`, `SUPERVISOR_SESSION_CREATED` (last one records
  `state=PENDING`, `remote_session_id=null`).

`supervision.py` mtime `2026-10-30 14:45:39 +08` predates the previous
verification run and has no local modifications beyond the working-tree state
already covered by earlier evidence.

### 2. Live rows and audit chain for this task (read-only queries)

| Fact | Value |
|---|---|
| Task | `tsk-1243cdb9`, status `DRAFT`, created `2026-10-30T07:44:27.114379Z` |
| Binding | `sup-5af457ba` (`5af457ba-ac3f-4e36-a6d4-6eb1a91df971`), same `created_at` |
| Revision | `rev-bf945281` (`bf945281-87fa-4bbf-a1f0-ad1668c703a2`), revision 1, `DRAFT` |
| Creation audit | `SUPERVISOR_SESSION_CREATED` at `07:44:27.131137Z` with `state=PENDING`, `remote_session_id=null` |
| Prompt record | `sha256:0f1f7c60…c7778`, `57` bytes (identical on binding and revision) |
| Current state | `RUNNING`; `result_updated_at=07:44:32.067983Z`, heartbeat `updated_at=07:46:15.996753Z` |
| Side effects | 0 runs, 0 verdicts, 0 evidence items |

Task, revision and binding share the identical microsecond `created_at`, and the
three audit events follow 9.5 ms / 3.1 ms / 4.2 ms later. `task_revisions.content`
contains only `title`, `objective`, `entry_mode`, `prompt_digest`, `prompt_bytes`
— no raw prompt key; the binding row contains no prompt text either.

The 57-byte prompt digest matches `tests/test_task_supervisor.py::_body()`
(`"Open the task and prepare a plan. Never echo this prompt."`, 57 bytes,
`sha256:0f1f7c60…c7778`). This task was therefore created by the pytest suite
against the development database at `07:44:27Z`, claimed by the running
supervisor worker `pid 206093` ~5 s later (`result_updated_at`), and then
dispatched as this verification session.

Commit-before-claim argument: the `SUPERVISOR_SESSION_CREATED` audit row and the
binding were written in the same transaction, so the audit row existing implies
the transaction committed; the worker claim is a compare-and-set on a committed
row. The `PENDING` creation state is also reconstructed from the audit payload
rather than the mutable current state.

### 3. Durability across processes (private cluster, never-claimed row)

`initdb -D /tmp/opencode/naverify_1243cdb9/data -U noahsark --auth-local=trust
--auth-host=trust`, `127.0.0.1:55433` (scratch only, dev DB untouched),
`createdb noahsark_verify`, `alembic upgrade head` → `f6a2c8d41e07`.

1. **Process A** (separate interpreter): `seed_database(reset=True)` then a real
   `POST /api/v1/tasks` through the FastAPI app. Response HTTP 201 for
   `tsk-44a03d9f` / `sup-22d30620`: `supervisor_state=PENDING`,
   `prompt_digest=sha256:4ca78309…04a2`, `prompt_bytes=67`. Process exits.
2. **Process B** (new process, new connection) read:
   - `state=PENDING`, `remote_session_id=NULL`,
     `created_at == updated_at == 2026-10-30T07:46:00.886023Z`,
     `result_summary=NULL`, `result_updated_at=NULL`;
   - three-event audit chain ending in `SUPERVISOR_SESSION_CREATED` with
     `state=PENDING`, `remote_session_id=null`;
   - `task_revisions.content` holding only digest/bytes.
3. Digest recomputed independently from the probe prompt equals the stored
   `sha256:4ca78309…04a2`; raw prompt text produced **0 hits** in
   `supervisor_sessions` and **0 hits** in `task_revisions`.

A row that was never claimed therefore stayed durably `PENDING` and readable by
another process after its creator terminated.

### 4. Isolated-database regression

```bash
cd /home/bszheng/NoahsArk/apps/control_plane
DATABASE_URL=postgresql+asyncpg://noahsark@127.0.0.1:55433/noahsark_verify \
  python -m pytest tests/test_task_supervisor.py -q
```

Result: **9 passed**. Post-run scratch state: 4 `PENDING` rows, all with
`remote_session_id IS NULL`, all `created_at == updated_at`; plus 1 `BINDING` and
1 `COMPLETED` produced by test manipulation. The cluster was stopped and deleted;
no scratch artifacts remain.

### 5. Database-enforced invariants (head `f6a2c8d41e07`)

- `ck_supervisor_sessions_state_closed` — nine declared lifecycle values.
- `ck_supervisor_sessions_prompt_bytes_non_negative`.
- FKs to `tasks(task_id)` and `task_revisions(revision_id)`.
- Unique `display_id`, unique `remote_session_id`, PK `supervisor_session_id`.
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id`
  `WHERE state IN ('PENDING','BINDING','READY','DISPATCHED','RUNNING','STOP_REQUESTED')`,
  so at most one active binding per task while terminal rows remain history.

### 6. Read projection

`GET /api/v1/tasks/tsk-1243cdb9/supervisor` (live API on `127.0.0.1:8000`)
returned HTTP 200 with `state=RUNNING`, `state_is_terminal=false`,
`remote_session_id="ses_***11eD"` (`remote_session_id_masked=true`), prompt only
as `{digest, bytes}`, `binding.one_active_session_per_task/stable/
remote_session_stored_separately=true`, `result.available=false`, and no
`lease` / `dispatch` / `worker` / `token` / `transcript` fields.

## Dev-database observation (not caused by this verification)

All writes in this run went to the private cluster. Dev DB counts were
`8 tasks / 11 revisions / 7 bindings / 23 audits / 4 runs` at the first read and
`9 / 12 / 8 / 26 / 4` at the second read; the increase corresponds to a
concurrently created task (`tsk-2bcaafc2`, title `test001`, `07:45:31Z`), not to
this verification. The recurring hazard remains: DB-backed pytest runs against
the development database `TRUNCATE … CASCADE` seeded tables and enqueue fixture
tasks that the live worker really dispatches — this verification task is itself
one of those fixtures.

## Boundary statement

This evidence covers the control-plane creation path, cross-process durability,
database constraints and an isolated regression run. It does not claim
production readiness, hardware execution, a frozen contract, or any change to
code, migrations or configuration.
