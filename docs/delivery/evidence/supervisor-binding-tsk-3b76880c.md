# Supervisor Binding Verification — tsk-3b76880c

**Date:** 2026-10-30
**Task:** `tsk-3b76880c` (`3b76880c-ce08-486f-8017-e7144261789d`), title `Active binding invariant`
**Question:** does task creation produce a durable `PENDING` supervisor binding?
**Verdict:** **PASS** for the creation path. Task + first revision + `PENDING`
binding + three audit events commit in one transaction; the committed `PENDING`
row is readable by a different process after the creator exits; only afterwards
does any worker transition it. No run, verdict or evidence row is implied.

## 1. Creation path

`apps/control_plane/noahsark/services/supervision.py::create_task_with_supervisor`
(reached from `POST /api/v1/tasks` via `api/writes.py` →
`services/writes.execute_idempotent`):

- `SUPERVISOR_STATE_ON_CREATE = "PENDING"`; the binding is constructed with
  `remote_session_id=None`, `result_summary=None`, `error_code=None`,
  `result_updated_at=None`.
- Rows are flushed explicitly in FK order inside the single transaction:
  `Task` → `TaskRevision` → `SupervisorSession` (the mappers declare no ORM
  relationships, so ordering cannot be inferred).
- Only `prompt_digest` (sha256) and `prompt_bytes` are persisted; the raw prompt
  is absent from the binding and from `task_revisions.content`.
- Three append-only audit events are appended before commit: `TASK_CREATED`,
  `TASK_REVISION_CREATED`, `SUPERVISOR_SESSION_CREATED` (the last records
  `state=PENDING`, `remote_session_id=null`).

The read path (`get_task_supervisor` → `GET /api/v1/tasks/{id}/supervisor`) only
selects; it orders active bindings before terminal ones, masks the remote
session id and exposes no lease/dispatch/worker/token/transcript fields.

## 2. Live rows for this task

### 2.1 Task and revision

| Fact | Value |
|---|---|
| Task | `tsk-3b76880c`, status `DRAFT`, source `control-plane` |
| Created | `2026-10-30T07:44:27.403666Z` (`updated_at` identical) |
| Revision | `rev-ceb790dc`, `revision_number=1`, `change_kind=initial`, status `DRAFT` |
| Revision content | `{title, objective, entry_mode: conversation, prompt_digest: sha256:0f1f7c60…c7778, prompt_bytes: 57}` — no `prompt` key |
| Side effects of creation | 0 runs, 0 verdicts, 0 evidence items |

The 57-byte digest matches `tests/test_task_supervisor.py::_body()`, and the
title/objective match the `_create(_body(title="Active binding invariant"))`
call in `test_one_active_supervisor_session_per_task`, i.e. this task is that
test's fixture committed to the development database.

### 2.2 Bindings

| Binding | Created (UTC) | State | Remote session | Digest / bytes |
|---|---|---|---|---|
| `sup-1595a680` | `07:44:27.403666` (same statement as Task) | `COMPLETED` | `NULL` | `sha256:0f1f7c60…c7778` / 57 |
| `sup-90a3d87b` | `07:44:27.454337` | `RUNNING` | `ses_e7435de7…a26g` | `sha256:next` / 1 |

- `sup-1595a680` is the creation binding produced by `POST /api/v1/tasks`. The
  test then ran its own `UPDATE supervisor_sessions SET state='COMPLETED'`
  (`updated_at 07:44:27.440456Z`, ~37 ms later, no remote session, no result) to
  free the active slot — so its terminal state is test behavior, not dispatch.
- `sup-90a3d87b` is inserted directly by the same test with a synthetic
  `prompt_digest='sha256:next'`, `prompt_bytes=1` to prove that terminal history
  permits a new active binding. The running supervisor worker later claimed that
  committed `PENDING` row (`result_updated_at 07:50:42.328645Z`,
  `remote_session_id` then set), which independently shows a committed
  `PENDING` binding is durable across processes and dispatchable.

### 2.3 Audit chain

| occurred_at (UTC) | action | object | recorded state | remote |
|---|---|---|---|---|
| `07:44:27.408094Z` | `TASK_CREATED` | `tsk-3b76880c` | `status=DRAFT` | — |
| `07:44:27.409986Z` | `TASK_REVISION_CREATED` | `rev-ceb790dc` | `status=DRAFT` | — |
| `07:44:27.412027Z` | `SUPERVISOR_SESSION_CREATED` | `sup-1595a680` | `PENDING` | `null` |

All three events post-date the row `created_at` (`07:44:27.403666Z`) and
precede commit, confirming a single-transaction append-only chain.

### 2.4 Read projection

`GET /api/v1/tasks/tsk-3b76880c/supervisor` (role `OBSERVER`, read-only) → `200`:

- `supervisor_display_id=sup-90a3d87b`, `state=RUNNING`, `state_is_terminal=false`
- `remote_session_id=ses_***a26g`, `remote_session_id_masked=true`
- `prompt={digest: "sha256:next", bytes: 1}` — from the test-inserted row
- `binding.one_active_session_per_task=true`, `stable=true`,
  `remote_session_stored_separately=true`, `read_only=true`
- no lease, dispatch, worker, token or transcript fields

Because the projection orders active bindings first, this fixture task displays
the synthetic test binding rather than the `COMPLETED` creation binding. That is
expected given the rows present; it does not affect the creation path.

## 3. Cross-process durability (isolated scratch database)

Private PostgreSQL 16 cluster under `/tmp` on `127.0.0.1:55434` (trust auth,
no access to the development database), database `noahsark_verify_3b76880c`,
`alembic upgrade head` → `f6a2c8d41e07`.

1. **Process A** POSTed through the real FastAPI app and exited:
   `201`, `tsk-abe70fb1` / `sup-8933bc17`, `supervisor_state=PENDING`,
   `prompt_bytes=59`, digest `sha256:58afb7d4…5912`, created
   `2026-10-30T07:52:04.175683Z`.
2. **Process B** opened a brand-new `asyncpg` connection after A terminated and
   read: `state=PENDING`, `remote_session_id=NULL`,
   `created_at == updated_at == 07:52:04.175683Z`, task status `DRAFT`,
   0 runs / 0 verdicts / 0 evidence, zero hits for the raw prompt in
   `task_revisions.content`, plus the complete three-event chain ending in
   `SUPERVISOR_SESSION_CREATED` with `state=PENDING`, `remote_session_id=null`.

An unclaimed creation therefore stays durably `PENDING` and readable by another
process after the creator exits. (An earlier identical probe,
`tsk-a60493b0` / `sup-ce6295d9`, was erased by the regression run's
`seed_database(reset=True)`; that reset semantics is why DB-resetting tests must
not share a database with live data.)

## 4. Isolated regression run

```bash
cd apps/control_plane
DATABASE_URL=…/noahsark_verify_3b76880c python -m pytest tests/test_task_supervisor.py -q
```

Result: **9 passed** (PostgreSQL reachable, suite not skipped).

Post-run scratch state: 7 tasks / 10 revisions / 6 bindings. Four untouched
creations remain `PENDING` with `remote_session_id IS NULL` and
`created_at == updated_at`; the active-binding test task has one `COMPLETED`
creation binding plus its synthetic `PENDING` row; the projection test task has
one `BINDING` row with a remote id. No task has more than one active binding
(`ACTIVE_CHECK = 0`). The scratch cluster was stopped and deleted afterwards.

Development database reads for this verification were read-only. Concurrent
UI-intake PONG tasks (`tsk-f834352b`, `tsk-2e78f29c`, created
`07:50:55–07:50:56Z`) appeared in the window from other activity; no row was
created by this verification itself.

## 5. Database-enforced invariants (live schema)

- `ck_supervisor_sessions_state_closed`: state ∈ {`PENDING`,`BINDING`,`READY`,
  `DISPATCHED`,`RUNNING`,`COMPLETED`,`FAILED`,`STOP_REQUESTED`,`STOPPED`}.
- `ck_supervisor_sessions_prompt_bytes_non_negative` (`prompt_bytes >= 0`).
- FKs `fk_supervisor_sessions_task_id_tasks` → `tasks(task_id)` and
  `fk_supervisor_sessions_revision_id_task_revisions` →
  `task_revisions(revision_id)`.
- Unique `uq_supervisor_sessions_display_id` and
  `uq_supervisor_sessions_remote_session_id`.
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id`
  `WHERE state IN ('PENDING','BINDING','READY','DISPATCHED','RUNNING','STOP_REQUESTED')`,
  so at most one active binding exists per task while terminal rows remain as
  history.

## Boundary statement

This evidence covers the control-plane creation path, the live rows and audit
chain of `tsk-3b76880c`, cross-process durability on an isolated database,
database constraints, and the supervisor regression suite. It does not claim
production readiness, hardware execution, a frozen contract, or any change to
code, migrations or configuration. The recurring hygiene issue remains: fixture
tasks and their synthetic bindings are committed to the development database and
are picked up by the running supervisor worker; DB-resetting tests must stay on
a dedicated database/schema.
