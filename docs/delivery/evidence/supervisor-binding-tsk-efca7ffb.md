# UI Intake Form → Supervisor Binding Verification — tsk-4bcabe4b

**Date:** 2026-10-30
**Round:** `tsk-efca7ffb` (UI intake live 2026-10-30T07:53:51)
**Task created:** `tsk-4bcabe4b` (`4bcabe4b-65a7-433c-b48d-c26240c37cc5`),
title `Reply with the single word PONG and nothing else. (UI intake`
**Question:** does submitting the real Intake form in the candidate UI create a
task and its supervisor binding through the control plane?
**Verdict:** **PASS.** A headless Chromium session filled and submitted
`#new-task-form` on the live candidate UI at `127.0.0.1:8100`; the form handler
issued exactly one `POST /api/v1/tasks` (HTTP 201) through the same-origin
proxy, and the control plane committed the task, its first revision and a
`PENDING` supervisor binding in one transaction with the three-event audit
chain. The page then polled `GET /tasks/{id}/supervisor` and rendered the
returned `PENDING` projection.

## 1. What the browser actually did

| Item | Value |
|---|---|
| Browser | Playwright driver 1.64.1 (`playwright` 1.64.1 from the npx cache), Chromium build 1223 (`chrome-linux64`), headless, viewport 1440×1100 |
| URL | `http://127.0.0.1:8100/?api=1#/console/intake/new` |
| Data source | `localStorage.naa-api=1`, `localStorage.naa-role=ADMIN` set via `addInitScript` before page scripts |
| Form | `#new-task-form[data-api-mode="true"]`, field `textarea[name="task_description"]` (maxlength 20000), submit enabled, label `开始任务` |
| Input | `Reply with the single word PONG and nothing else. (UI intake live 2026-10-30T07:53:51)` |
| Submission | one click on `开始任务` |
| Network | `GET /api/v1/intake/drafts` → 200 (route load); exactly 1 × `POST http://127.0.0.1:8100/api/v1/tasks` → **201**; `GET /api/v1/tasks/{id}/supervisor` → **200** |
| Console | 0 console messages, 0 page errors |
| Screenshot | `/tmp/opencode/ui-intake-proof.png` |

The form converted the single description into the API body: `deriveTaskTitle`
truncated the title to 60 characters while `objective` and `prompt` carry the
full description (trimmed). `entry_mode="conversation"`.

## 2. Wiring path

Browser form submit
→ `design/ui-app/src/app.js::submitNewTask` (guards `dataset.submitting`, reads
`FormData`, calls `createTask`)
→ `design/ui-app/src/data-source.js::createTask` → `buildTaskCreate` →
`apiPost("/tasks")`
→ `design/ui-app/src/pages/intake.js::quickStartForm` markup
→ same-origin `design/ui-app/checks/serve.mjs` proxy
→ control plane `apps/control_plane/noahsark/api/writes.py::post_task`
→ `services/writes.execute_idempotent`
→ `services/supervision.py::create_task_with_supervisor` (one transaction:
`Task` → `TaskRevision` → `SupervisorSession` + 3 audit events)
→ UI `startIntakePolling` → `loadTaskSupervisor` → `GET /tasks/{id}/supervisor`.

The form is rendered only when route meta is `server_authoritative`; in fixture
mode `data-api-mode="false"` and submission is blocked. In this run the form
reported API mode and was enabled.

## 3. POST observed by the browser

```http
POST /api/v1/tasks HTTP/1.1
X-NoahsArk-Role: ADMIN
X-NoahsArk-Actor: demo-admin
Idempotency-Key: 5b3a8618-7765-4def-8ec2-f104b924c6f1
Content-Type: application/json
```

```json
{
  "title": "Reply with the single word PONG and nothing else. (UI intake",
  "objective": "Reply with the single word PONG and nothing else. (UI intake live 2026-10-30T07:53:51)",
  "entry_mode": "conversation",
  "task_category": "voice_interaction",
  "lead_agent_id": "agt-planner",
  "lead_session_id": "800a3368-f535-4b3e-97e4-51f2df68fce4",
  "prompt": "Reply with the single word PONG and nothing else. (UI intake live 2026-10-30T07:53:51)"
}
```

Response `201`, `meta.source="control-plane"`, `meta.mock=false`,
`meta.server_authoritative=true`,
`meta.correlation_id=af307452b9764100bc7b080d6bdbd60b`:

```json
{
  "task_id": "4bcabe4b-65a7-433c-b48d-c26240c37cc5",
  "display_id": "tsk-4bcabe4b",
  "status": "DRAFT",
  "lead_agent_display_id": "agt-planner",
  "current_revision_id": "0455013d-7d9f-4ef7-a6ea-d35584a9e2f6",
  "revision_display_id": "rev-0455013d",
  "supervisor_session_id": "b4ba61de-92a6-4759-a06b-b28fac31b9c7",
  "supervisor_display_id": "sup-b4ba61de",
  "supervisor_state": "PENDING",
  "prompt_digest": "sha256:d43a681e26551f3a59514864803aeb92a7d8e6cc6b6267512cc56f050367835a",
  "prompt_bytes": 86,
  "created_at": "2026-10-30T07:56:23.820393Z",
  "created": true
}
```

## 4. Live rows and audit chain

Read-only queries against the configured PostgreSQL database
(`127.0.0.1:5432/noahsark`):

| Fact | Value |
|---|---|
| Task | `tsk-4bcabe4b`, `DRAFT`, `conversation`, `voice_interaction`, created `2026-10-30 15:56:23.820393+08` (= `07:56:23.820393Z`) |
| Origin | `submitted_by=demo-admin`, `correlation_id=af307452b9764100bc7b080d6bdbd60b` |
| Revision | `rev-0455013d`, revision 1, `initial`, `DRAFT`, `content_digest=sha256:a1eacff3…d6feb9` |
| Binding | `sup-b4ba61de`, `PENDING`, `remote_session_id=NULL`, `result_summary=NULL`, `error_code=NULL`, `result_updated_at=NULL` |
| Timestamps | task = revision = binding = `2026-10-30 15:56:23.820393+08` |
| Prompt record | `sha256:d43a681e…67835a`, `86` bytes — identical on revision digest and binding |
| Revision content keys | `title`, `objective`, `entry_mode`, `prompt_bytes`, `prompt_digest`; **no** `prompt` key (`content ? 'prompt' = false`) |
| Side effects | 0 runs / 0 verdicts / 0 evidence items |

The raw prompt text appears only as `objective` (the operator-authored task
description); the supervisor binding row stores only the digest and byte count
and contains no raw prompt text.

Binding invariants verified in one query:

```text
bindings=1  revision_matches_current=t  digest_matches_revision=t
bytes_match_revision=t  same_created_ts=t  remote_unset=t  state_pending=t
```

Audit chain, all `result=SUCCESS`, same correlation id:

| Occurred (UTC+8) | Offset vs create | Action | Object | Creation-state payload |
|---|---|---|---|---|
| 15:56:23.823369 | +3.0 ms | `TASK_CREATED` | `tsk-4bcabe4b` | `status=DRAFT` |
| 15:56:23.824563 | +4.2 ms | `TASK_REVISION_CREATED` | `rev-0455013d` | `revision_number=1`, `change_kind=initial`, digest/bytes |
| 15:56:23.826052 | +5.7 ms | `SUPERVISOR_SESSION_CREATED` | `sup-b4ba61de` | `state=PENDING`, `remote_session_id=null` |

The binding is therefore not a later side effect of dispatch: it was committed
with the task, and its creation event records the unclaimed `PENDING` state.

## 5. Read projection and UI panel

`GET http://127.0.0.1:8100/api/v1/tasks/4bcabe4b-65a7-433c-b48d-c26240c37cc5/supervisor`
returned HTTP 200 (issued by the page poll and re-issued by curl):

- `state=PENDING`, `state_is_terminal=false`;
- `supervisor_display_id=sup-b4ba61de`;
- `remote_session_id=null` with `remote_session_id_masked=true`;
- prompt exposed only as `{digest, bytes}`;
- `binding.one_active_session_per_task=true`, `binding.stable=true`,
  `binding.remote_session_stored_separately=true`;
- `read_only=true`; no lease/dispatch/worker/token/transcript fields;
- `result.available=false`.

The rendered result panel (`#new-task-result[data-task-id]`) on the Intake page
showed:

```text
任务执行结果

只读投影；remote_session_id 由服务端掩码返回，界面不还原完整会话 ID。

会话执行中…
task_id            4bcabe4b-65a7-433c-b48d-c26240c37cc5
display_id         tsk-4bcabe4b
supervisor_state   PENDING
remote_session_id  —
查看任务详情
```

The panel text was unchanged after the supervisor poll (binding still
`PENDING`), confirming the panel renders server data rather than fixture data —
the same task id appears in the POST response, the database row and the panel.

## 6. Non-mutating UI regression checks

```bash
cd design/ui-app && node checks/contract-check.mjs && node checks/smoke-check.mjs
```

Result: **123 passed, 0 failed** (contract) and **358 passed, 0 failed**
(smoke). These assert the form markup, submit wiring, `/tasks` POST path,
response navigation/polling, masked supervisor id, and no fixture fallback. No
database-resetting test was run; the live database was only read after the
browser submission.

## 7. Database constraints (live schema)

- `ck_supervisor_sessions_state_closed` — nine lifecycle values;
- `ck_supervisor_sessions_prompt_bytes_non_negative`;
- FKs to `tasks(task_id)` and `task_revisions(revision_id)`;
- unique `display_id`, unique `remote_session_id`, PK
  `supervisor_session_id`;
- `uq_supervisor_sessions_active_task` — partial unique index on `task_id`
  `WHERE state IN ('PENDING','BINDING','READY','DISPATCHED','RUNNING','STOP_REQUESTED')`.

This task holds exactly one active binding; terminal history rows are not
blocked by the index.

## Boundary statement

This evidence covers the candidate UI form → same-origin proxy → control-plane
creation path for one live submission, the committed rows and audit chain, the
read-only supervisor projection, and the non-mutating UI checks. It does not
claim that the binding was dispatched: at capture time the binding remained
`PENDING` with `remote_session_id=NULL` and `created_at == updated_at`, i.e. no
supervisor worker had claimed it yet. A later claim (`PENDING → BINDING →
READY`) is expected, out-of-band behaviour and is not part of this proof.

No code, migration or configuration was modified for this verification.
