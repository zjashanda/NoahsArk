# Supervisor Binding Verification — tsk-bdf40444

**Date:** 2026-10-30
**Task:** `tsk-bdf40444` (`bdf40444-21d3-4849-87e0-463576ddcfe3`), title `Supervisor binding task`
**Question:** does task creation produce a durable `PENDING` supervisor binding?
**Verdict:** **PASS.** The task, its first revision and a `PENDING` supervisor
binding were committed in one transaction at the same statement timestamp, the
`PENDING` creation state is preserved in the append-only audit chain, and an
independent probe on a private PostgreSQL cluster shows the row remains
`PENDING` and readable by a separate process after the creator exits.

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
  absent from both the supervisor row and `task_revisions.content`.
- Three append-only audit events are written in the same transaction:
  `TASK_CREATED`, `TASK_REVISION_CREATED`, `SUPERVISOR_SESSION_CREATED`
  (the last records `state=PENDING`, `remote_session_id=null`).

### 2. Live rows and audit chain for this task

Read-only queries against the configured PostgreSQL database:

| Fact | Value |
|---|---|
| Task | `tsk-bdf40444`, status `DRAFT`, created `2026-10-30T07:13:02.578934Z` |
| Binding | `sup-2780db44` (`2780db44-bec3-4b1b-819b-c09bff345e3d`), same `created_at` |
| Revision | `rev-c6e49892` (`c6e49892-9bac-4202-b7ca-e6a69f54bfc0`), revision 1 |
| Creation audit | `SUPERVISOR_SESSION_CREATED` at `07:13:02.585867Z` with `state=PENDING`, `remote_session_id=null` |
| Prompt record | `sha256:c56b6a3f…fd93`, `35` bytes (identical in binding and revision) |
| Current state | `RUNNING`, remote session set, dispatch at `07:20:42.674440Z`, heartbeat `07:23:03Z` |
| Side effects | 0 runs, 0 verdicts |

Creation timestamps are identical across task, revision and binding
(`07:13:02.578934Z`), and the audit events follow 3.5 ms / 2.1 ms / 1.4 ms later.
The `35`-byte digest matches `prompt_digest` on the revision, and
`task_revisions.content` holds only
`title`, `objective`, `entry_mode`, `prompt_digest`, `prompt_bytes` — no raw
prompt key. Because the raw creation prompt was never persisted, its digest is
not independently recomputable from stored data; the binding↔revision digest
equality is the verifiable link.

This row was created by the live API probe of the preceding verification run
(35-byte prompt, `07:13:02Z`), not by the pytest fixture whose prompt is
57 bytes. The `PENDING` state is therefore the actual creation state, and the
later `RUNNING` state is the result of the independent supervisor worker
claiming the committed row ~7 minutes 40 seconds after creation (`PENDING →
BINDING → READY → DISPATCHED → RUNNING`), i.e. the row was durable and readable
before any dispatch.

### 3. Durability across processes (isolated private cluster)

The shared PostgreSQL server did not grant the `noahsark` role `CREATEDB`, so a
throw-away cluster was initialised instead of a scratch database:

1. `initdb -D /tmp/naverify_bdf40444/data -U noahsark --auth-host=trust
   --auth-local=trust`, `listen_addresses=127.0.0.1`, port `55432`; the dev
   database was never touched.
2. `alembic upgrade head` → `f6a2c8d41e07`.
3. Process A seeded the schema, posted a task through the real FastAPI app, got
   HTTP 201 for `tsk-56b2188c` / `sup-5ddda4a7` with
   `supervisor_state=PENDING`, `prompt_bytes=57`, and exited.
4. Process B then opened a **new** process and connection and read:
   `state=PENDING`, `remote_session_id=NULL`,
   `created_at == updated_at` (`2026-10-30T07:22:51.422151Z`), plus the
   three-event audit chain ending in `SUPERVISOR_SESSION_CREATED` with
   `state=PENDING`, `remote_session_id=null`.

A row that was never claimed therefore remained durably `PENDING` and readable
by another process after the creator terminated.

### 4. Isolated-database regression run

The supervisor suite was run only against the private cluster:

```bash
cd /home/bszheng/NoahsArk/apps/control_plane
DATABASE_URL=postgresql+asyncpg://noahsark@127.0.0.1:55432/noahsark_verify \
  python -m pytest tests/test_task_supervisor.py -q
```

Result: **9 passed**. Post-run scratch state: 4 untouched creations left exactly
one `PENDING` binding each with `remote_session_id IS NULL`; 1 `BINDING` and
1 `COMPLETED` row reflected test manipulation (one task carried both a terminal
history row and a new `PENDING` row). The development database was snapshotted
before and after: **9 tasks / 12 revisions / 8 bindings / 26 audit events /
4 runs / 0 verdicts, unchanged**. The cluster was stopped and deleted; only the
development cluster remains.

### 5. Database-enforced invariants (live schema, head `f6a2c8d41e07`)

- `ck_supervisor_sessions_state_closed` restricts state to the nine declared
  lifecycle values.
- `ck_supervisor_sessions_prompt_bytes_non_negative`.
- FKs to `tasks(task_id)` and `task_revisions(revision_id)`.
- Unique `display_id`, unique `remote_session_id`, primary key
  `supervisor_session_id`.
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id`
  `WHERE state IN ('PENDING','BINDING','READY','DISPATCHED','RUNNING','STOP_REQUESTED')`,
  so at most one active binding exists per task while terminal rows remain as
  history.

### 6. Read projection does not leak internals

`GET /api/v1/tasks/tsk-bdf40444/supervisor` returned HTTP 200 with:

- `state: RUNNING`, `state_is_terminal: false`;
- `remote_session_id: "ses_***x8Pv"` with `remote_session_id_masked: true`;
- prompt exposed only as `{digest, bytes}`;
- `binding.one_active_session_per_task: true`, `binding.stable: true`,
  `binding.remote_session_stored_separately: true`;
- no `lease` / `dispatch` / `worker` / `token` / `transcript` fields, and
  `result.available: false`.

## Caveat / finding (not a defect in the creation path)

The creation path is correct and durable. The operational hazard recorded for
`tsk-49b4be2c` still applies: `tests/test_task_supervisor.py` calls
`seed_database(reset=True)`, which issues `TRUNCATE … CASCADE`; pointing that
suite at the development database would delete live bindings. This run kept the
suite on a private cluster. Verification-probe tasks (such as this one) are
posted to the development database and do enter the live supervisor queue by
design.

## Boundary statement

This evidence covers the control-plane creation path, cross-process durability,
database constraints and the isolated regression suite. It does not claim
production readiness, hardware execution, a frozen contract, or any change to
code, migrations or configuration.
