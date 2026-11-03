# Supervisor Binding Verification — tsk-4279578f

**Date:** 2026-10-30
**Task:** `tsk-4279578f` (`4279578f-b933-4405-92d1-8cad360ee061`), title `Active binding invariant`
**Question:** does task creation produce a durable `PENDING` supervisor binding?
**Verdict:** **PASS** for the creation path. The binding is written as `PENDING`
in the same committed transaction as the task and its first revision, is visible
to a separate process after the creating process exits, and only then moves
through the supervisor lifecycle. The read API for this particular task now
resolves the *test-inserted* second binding (see §2.3), which is a fixture data
hygiene artifact, not a creation-path defect.

## 1. Creation path

`apps/control_plane/noahsark/services/supervision.py::create_task_with_supervisor`
(reached from `POST /api/v1/tasks` via `api/writes.py` →
`services/writes.execute_idempotent`):

- `SUPERVISOR_STATE_ON_CREATE = "PENDING"`; the row is created with
  `remote_session_id=None`.
- Rows are flushed in FK order in one transaction: `Task` → `TaskRevision` →
  `SupervisorSession` (mappers declare no ORM relationships, so ordering is
  explicit).
- Only `prompt_digest` (sha256) and `prompt_bytes` are persisted; the raw prompt
  is absent from the binding and from `task_revisions.content`.
- Three append-only audit events are written in the same transaction:
  `TASK_CREATED`, `TASK_REVISION_CREATED`, `SUPERVISOR_SESSION_CREATED` (the last
  records `state=PENDING`, `remote_session_id=null`).

## 2. Live rows for this task

### 2.1 Task and revision

| Fact | Value |
|---|---|
| Task | `tsk-4279578f`, status `DRAFT`, created `2026-10-30T15:12:54.497717+08` |
| Revision | `rev-4ac776e4`, `revision_number=1`, `change_kind=initial`, status `DRAFT` |
| Revision content | `prompt_digest=sha256:0f1f7c60…c7778`, `prompt_bytes=57`, no `prompt` key |
| Side effects of creation | 0 runs, 0 verdicts, 0 evidence items |

The digest and byte count match the suite fixture `_body()` prompt used by
`test_one_active_supervisor_session_per_task`, i.e. this task is that fixture.

### 2.2 Bindings

| Binding | Created | State | Remote session | Digest / bytes |
|---|---|---|---|---|
| `sup-700580d1` | `15:12:54.497717+08` (same statement as Task) | `COMPLETED` | `NULL` | `sha256:0f1f7c60…c7778` / 57 |
| `sup-8e01aec9` | `15:12:54.542159+08` | `RUNNING` | `ses_e7452e3a…H4uv` | `sha256:next` / 1 |

- `sup-700580d1` is the creation binding produced by `POST /api/v1/tasks`.
- `sup-8e01aec9` is inserted directly by
  `test_one_active_supervisor_session_per_task` with a synthetic
  `prompt_digest='sha256:next'`, `prompt_bytes=1` to prove terminal history
  frees the active slot. The live supervisor worker then claimed that committed
  `PENDING` row (`remote_session_id` set at `15:19:08.727678Z`), which is
  further independent evidence that a committed `PENDING` row is durably
  readable and dispatchable by another process.

### 2.3 Audit chain

| occurred_at (UTC) | action | object | recorded state | remote |
|---|---|---|---|---|
| `07:12:54.502052Z` | `TASK_CREATED` | `tsk-4279578f` | — | — |
| `07:12:54.504063Z` | `TASK_REVISION_CREATED` | `rev-4ac776e4` | — | — |
| `07:12:54.505992Z` | `SUPERVISOR_SESSION_CREATED` | `sup-700580d1` | `PENDING` | `null` |

All three events post-date the row `created_at` (`07:12:54.497717Z`) and precede
commit, confirming a single-transaction append-only chain.

### 2.4 Read projection

`GET /api/v1/tasks/tsk-4279578f/supervisor` (role `OBSERVER`, read-only) returns

- `supervisor_display_id=sup-8e01aec9`, `state=RUNNING`, `state_is_terminal=false`
- `remote_session_id=ses_***H4uv` (masked), `remote_session_id_masked=true`
- `prompt={digest: "sha256:next", bytes: 1}` — from the test-inserted row
- `binding.one_active_session_per_task=true`, `read_only=true`
- no lease, dispatch, worker, token or transcript fields

The projection orders active bindings before terminal ones, so for this fixture
task the API surfaces the synthetic test binding rather than the `COMPLETED`
creation binding. That is expected given the rows present; it does not affect
the creation path. It does mean fixture data written into the development
database is visible through the read API (see §5).

## 3. Cross-process durability (isolated scratch database)

Scratch database `noahsark_verify_4279578f` (owner `noahsark`), `alembic upgrade
head` → `f6a2c8d41e07`.

1. **Process A** ran `seed_database(reset=True)` then `POST /api/v1/tasks` via
   the real FastAPI app and exited:
   `201`, `tsk-2616b053` / `sup-62cf985a`, `supervisor_state=PENDING`,
   `prompt_bytes=53`, created `2026-10-30T07:19:54.079206Z`.
2. **Process B** opened a brand-new `asyncpg` connection after A terminated and
   read: `state=PENDING`, `remote_session_id=NULL`,
   `created_at == updated_at == 07:19:54.079206Z`, task status `DRAFT`, plus the
   three-event chain ending in `SUPERVISOR_SESSION_CREATED` with
   `state=PENDING`, `remote_session_id=null`.

An unclaimed creation therefore stays durably `PENDING` and readable by another
process after the creator exits.

## 4. Isolated regression run

```bash
cd apps/control_plane
DATABASE_URL=postgresql+asyncpg://…/noahsark_verify_4279578f \
  python -m pytest tests/test_task_supervisor.py -q
```

Result: **9 passed** (PostgreSQL reachable, suite not skipped).

Post-run scratch state (6 bindings): four untouched creations still `PENDING`
with `remote_session_id IS NULL`; the active-binding test task has one
`COMPLETED` + one `PENDING`; the projection test task has one `BINDING` with a
remote id.

Development database snapshot before and after the whole verification:
**8 tasks / 11 revisions / 7 bindings / 23 audit events / 4 runs / 0 verdicts**,
unchanged. All reads against it were read-only; `sup-8e01aec9.updated_at` moved
between snapshots because the live supervisor worker is heartbeating that row,
not because of this verification. Scratch database dropped afterwards; only
`noahsark` remains.

## 5. Database-enforced invariants (live schema)

- `ck_supervisor_sessions_state_closed`: state ∈ {`PENDING`,`BINDING`,`READY`,
  `DISPATCHED`,`RUNNING`,`COMPLETED`,`FAILED`,`STOP_REQUESTED`,`STOPPED`}.
- `ck_supervisor_sessions_prompt_bytes_non_negative`.
- FKs to `tasks(task_id)` and `task_revisions(revision_id)`.
- Unique `display_id` and unique `remote_session_id`.
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id`
  `WHERE state IN ('PENDING','BINDING','READY','DISPATCHED','RUNNING','STOP_REQUESTED')`,
  so at most one active binding exists per task while terminal rows remain as
  history.

## Boundary statement

This evidence covers the control-plane creation path, the live rows and audit
chain of `tsk-4279578f`, cross-process durability on an isolated database,
database constraints, and the supervisor regression suite. It does not claim
production readiness, hardware execution, a frozen contract, or any change to
code, migrations or configuration. As recorded for `tsk-49b4be2c` and
`tsk-1772bb81`, DB-resetting tests must stay on a dedicated database/schema;
this run followed that rule. The recurring hygiene issue remains: fixture tasks
and their synthetic bindings are committed to the development database and are
picked up by the running supervisor worker.
