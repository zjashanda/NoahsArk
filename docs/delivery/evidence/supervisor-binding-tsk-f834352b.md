# UI Intake Form → Supervisor Binding Verification — tsk-f834352b

**Date:** 2026-10-30
**Task:** `tsk-f834352b` (`f834352b-7ac0-4018-a572-30702e7a2f50`),
title `Reply with the single word PONG and nothing else. (UI intake`
**Question:** does submitting the real Intake form in the candidate UI create a
task and its supervisor binding through the control plane?
**Verdict:** **PASS.** A headless Chromium session filled and submitted
`#new-task-form` on the live candidate UI; the form handler issued exactly one
`POST /api/v1/tasks` (HTTP 201) through the same-origin proxy, and the control
plane committed the task, its first revision and a `PENDING` supervisor binding
in one transaction with the three-event audit chain. The same page then polled
`GET /tasks/{id}/supervisor` and rendered the returned `PENDING` projection.

## 1. What the browser actually did

| Item | Value |
|---|---|
| Browser | Playwright 1.64.1, Chromium 1223, headless, viewport 1440×1100 |
| URL | `http://127.0.0.1:8100/?api=1#/console/intake/new` |
| Data source | `localStorage.naa-api=1`, `localStorage.naa-role=ADMIN` set before page scripts |
| Form | `#new-task-form[data-api-mode="true"]`, field `task_description`, submit enabled |
| Input | `Reply with the single word PONG and nothing else. (UI intake live 2026-10-30T07:50:55)` |
| Submission | one click on 开始任务 |
| Network | exactly 1 × `POST http://127.0.0.1:8100/api/v1/tasks` → 201; subsequent `GET .../supervisor` → 200 |
| Console | 0 errors, 0 page errors |

The UI converts the single description into the API body: `deriveTaskTitle`
truncates the title to 60 characters, while `objective` and `prompt` carry the
full description (trimmed). At submission time the working tree used
`entry_mode="conversation"`; the captured POST and stored row agree.

## 2. Wiring path

Browser form submit
→ `design/ui-app/src/app.js::submitNewTask` (guards `dataset.submitting`, reads
`FormData`, calls `createTask`)
→ `design/ui-app/src/data-source.js::createTask` → `buildTaskCreate` →
`apiPost("/tasks")`
→ `design/ui-app/src/pages/intake.js::quickStartForm` markup
→ same-origin `design/ui-app/checks/serve.mjs` proxy
→ control plane `apps/control_plane/noahsark/api/writes.py::create_task`
→ `services/writes.execute_idempotent`
→ `services/supervision.py::create_task_with_supervisor`.

The form is rendered only when the route meta is `server_authoritative`; in
fixture mode `data-api-mode="false"` and submission is blocked. In this run the
form reported API mode and was enabled.

## 3. POST observed by the browser

```http
POST /api/v1/tasks HTTP/1.1
X-NoahsArk-Role: ADMIN
X-NoahsArk-Actor: demo-admin
Idempotency-Key: <fresh uuid per submission>
Content-Type: application/json
```

```json
{
  "title": "Reply with the single word PONG and nothing else. (UI intake",
  "objective": "Reply with the single word PONG and nothing else. (UI intake live 2026-10-30T07:50:55)",
  "entry_mode": "conversation",
  "task_category": "voice_interaction",
  "lead_agent_id": "agt-planner",
  "lead_session_id": "2928b7fc-7a8e-447a-bb62-5b3936beb45d",
  "prompt": "Reply with the single word PONG and nothing else. (UI intake live 2026-10-30T07:50:55)"
}
```

Response `201`, `meta.source="control-plane"`, `meta.mock=false`,
`meta.server_authoritative=true`, `meta.correlation_id=43a6130bb1494770bc4768733afe7887`:

```json
{
  "task_id": "f834352b-7ac0-4018-a572-30702e7a2f50",
  "display_id": "tsk-f834352b",
  "status": "DRAFT",
  "lead_agent_display_id": "agt-planner",
  "current_revision_id": "444608c8-bc5e-4418-a461-0cfe7163d62e",
  "revision_display_id": "rev-444608c8",
  "supervisor_session_id": "24129b8c-42d7-4fcc-9106-27ef42caacf8",
  "supervisor_display_id": "sup-24129b8c",
  "supervisor_state": "PENDING",
  "prompt_digest": "sha256:653f2e4a094add3f026586c2510db234345e0907dc4c19b1fda39d2fd5f34983",
  "prompt_bytes": 86,
  "created_at": "2026-10-30T07:50:56.876698Z",
  "created": true
}
```

## 4. Live rows and audit chain

Read-only queries against the configured PostgreSQL database:

| Fact | Value |
|---|---|
| Task | `tsk-f834352b`, `DRAFT`, entry_mode `conversation`, created `2026-10-30 07:50:56.876698+00:00` |
| Origin | `submitted_by=demo-admin`, `correlation_id=43a6130bb1494770bc4768733afe7887` |
| Revision | `rev-444608c8` (`444608c8-bc5e-4418-a461-0cfe7163d62e`), revision 1, `initial`, `DRAFT` |
| Binding | `sup-24129b8c` (`24129b8c-42d7-4fcc-9106-27ef42caacf8`), `PENDING`, `remote_session_id=NULL` |
| Timestamps | task = revision = binding = `07:50:56.876698Z` |
| Prompt record | `sha256:653f2e4a…f34983`, `86` bytes — identical on revision and binding |
| Revision content | only `title`, `objective`, `entry_mode`, `prompt_digest`, `prompt_bytes`; no raw `prompt` key |
| Side effects | 0 runs / 0 verdicts for this task |

Audit chain, all `result=SUCCESS`, same correlation id:

| Offset | Action | Object | Creation-state payload |
|---|---|---|---|
| +5.6 ms | `TASK_CREATED` | `tsk-f834352b` | `status=DRAFT` |
| +8.8 ms | `TASK_REVISION_CREATED` | `rev-444608c8` | `revision_number=1`, digest/bytes |
| +12.0 ms | `SUPERVISOR_SESSION_CREATED` | `sup-24129b8c` | `state=PENDING`, `remote_session_id=null` |

The binding was therefore not a later side effect of dispatch: it was committed
with the task, and its creation event records the unclaimed `PENDING` state.

## 5. Read projection and UI panel

`GET http://127.0.0.1:8100/api/v1/tasks/f834352b-7ac0-4018-a572-30702e7a2f50/supervisor`
returned HTTP 200 (the UI polled it twice before the capture ended):

- `state=PENDING`, `state_is_terminal=false`;
- `supervisor_display_id=sup-24129b8c`;
- `remote_session_id=null` with `remote_session_id_masked=true`;
- prompt exposed only as `{digest, bytes}`;
- `binding.one_active_session_per_task=true`, `binding.stable=true`,
  `binding.remote_session_stored_separately=true`;
- `read_only=true`; no lease/dispatch/worker/token/transcript fields;
- `result.available=false`.

The rendered result panel on the Intake page showed:

```text
任务执行结果
只读投影；remote_session_id 由服务端掩码返回，界面不还原完整会话 ID。
会话执行中…
task_id            f834352b-7ac0-4018-a572-30702e7a2f50
display_id         tsk-f834352b
supervisor_state   PENDING
remote_session_id  —
查看任务详情
```

This is the server projection, not fixture data: the same task id appears in the
POST response, the database row and the panel.

## 6. Non-mutating UI regression checks

```bash
cd design/ui-app && npm run check
```

Result: **118 passed, 0 failed** (`contract-check.mjs`) and **343 passed,
0 failed** (`smoke-check.mjs`). These checks assert the form markup, submit
wiring, `/tasks` POST path, response navigation/polling, masked supervisor id,
and no fixture fallback. No database-resetting test was run; the live database
was only read after the browser submission.

## 7. Database constraints (live schema)

- `ck_supervisor_sessions_state_closed` — nine lifecycle values;
- `ck_supervisor_sessions_prompt_bytes_non_negative`;
- FKs to `tasks(task_id)` and `task_revisions(revision_id)`;
- unique `display_id`, unique `remote_session_id`, primary key
  `supervisor_session_id`;
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id`
  `WHERE state IN ('PENDING','BINDING','READY','DISPATCHED','RUNNING','STOP_REQUESTED')`.

This task holds exactly one active binding; terminal history rows are not
blocked by the index.

## Boundary statement

This evidence covers the candidate UI form → same-origin proxy → control-plane
creation path for one live submission, the committed rows and audit chain, the
read-only supervisor projection, and the non-mutating UI checks. It does not
claim that the binding was dispatched: at capture time the single supervisor
worker was already polling an earlier long-running session, so this binding
remained `PENDING`. It also does not claim production readiness, a frozen
contract, or any change to code, migrations or configuration.

Note: the earlier probe row `tsk-55fdc771` was deleted by a database-resetting
test run (`seed_database(reset=True)`) before this verification; this document
therefore records the UI-created replacement `tsk-f834352b`, whose POST was
issued by the form handler rather than by a direct API probe.
