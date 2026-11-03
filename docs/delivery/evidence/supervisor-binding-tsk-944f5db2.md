# UI Intake Form → Supervisor Binding Verification — tsk-944f5db2

**Date:** 2026-10-30
**Round:** `tsk-3abf37a9` (UI intake live 2026-10-30T07:44:37)
**Task created:** `tsk-944f5db2` (`944f5db2-2e0c-423e-aafa-95f15557fcb5`),
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
| Browser | Playwright driver 1.64.1 (`playwright` 1.64.1 from the npx cache), Chromium build 1223 (`chrome-linux64/chrome`, `executablePath`), headless, viewport 1440×1100 |
| URL | `http://127.0.0.1:8100/?api=1#/console/intake/new` |
| Data source | `localStorage.naa-api=1`, `localStorage.naa-role=ADMIN` set via `addInitScript` before page scripts; `sessionStorage.naa-session` removed |
| Form | `#new-task-form[data-api-mode="true"]`, field `textarea#new-task-description[name="task_description"]` (maxlength 20000), submit button had no `disabled` attribute |
| Input | `Reply with the single word PONG and nothing else. (UI intake wiring proof 2026-10-30T15:56:19+0800)` |
| Submission | one click on the form submit button |
| Network | `GET /api/v1/intake/drafts` → 200 (route load); exactly 1 × `POST http://127.0.0.1:8100/api/v1/tasks` → **201**; `GET /api/v1/tasks/944f5db2-2e0c-423e-aafa-95f15557fcb5/supervisor` → **200** |
| Console | 0 console errors, 0 page errors |
| Screenshot | `/tmp/opencode/intake-submit.png` |
| Raw capture | `/tmp/opencode/intake-proof.json` |

The form converted the single description into the API body: `deriveTaskTitle`
truncated the title to 60 characters while `objective` and `prompt` carry the
full description. `entry_mode="conversation"` and `task_category` was filled by
the data-source layer as `voice_interaction`. The result panel received the new
task id (`dataset.taskId = 944f5db2-…`) without navigating away.

## 2. Wiring path

Browser form submit
→ delegated submit listener in `design/ui-app/src/app.js` →
`app.js::submitNewTask` (guards `dataset.submitting`, reads `FormData`, calls
`createTask`)
→ `design/ui-app/src/data-source.js::createTask` → `buildTaskCreate` →
`apiPost("/tasks")` (mints `Idempotency-Key`)
→ `design/ui-app/src/pages/intake.js::quickStartForm` markup
→ same-origin `design/ui-app/checks/serve.mjs` proxy
→ control plane `apps/control_plane/noahsark/api/writes.py::post_task`
(`require_idempotency_key`, `require_capability(CAP_CREATE_TASK)`)
→ `services/writes.execute_idempotent`
→ `services/supervision.py::create_task_with_supervisor` (one transaction:
`Task` → `TaskRevision` → `SupervisorSession` + 3 audit events, single commit)
→ UI `startIntakePolling` → `loadTaskSupervisor` → `GET /tasks/{id}/supervisor`.

The form is rendered only when route meta is `server_authoritative`; in fixture
mode `data-api-mode="false"` and submission is blocked. In this run the form
reported API mode and was enabled.

## 3. POST observed by the browser

```http
POST /api/v1/tasks HTTP/1.1
X-NoahsArk-Role: ADMIN
X-NoahsArk-Actor: demo-admin
Idempotency-Key: 9eff6d34-1848-4c6d-a7fb-e46b24da7813
Content-Type: application/json
```

```json
{
  "title": "Reply with the single word PONG and nothing else. (UI intake",
  "objective": "Reply with the single word PONG and nothing else. (UI intake wiring proof 2026-10-30T15:56:19+0800)",
  "entry_mode": "conversation",
  "task_category": "voice_interaction",
  "lead_agent_id": "agt-planner",
  "lead_session_id": "1b28b09a-24f9-4fb4-a167-bdb2e52d2e86",
  "prompt": "Reply with the single word PONG and nothing else. (UI intake wiring proof 2026-10-30T15:56:19+0800)"
}
```

Response `201`, `meta.source="control-plane"`, `meta.mock=false`,
`meta.server_authoritative=true`,
`meta.correlation_id=e155d0b2f8bd40889a8f40fe621e56bd`:

```json
{
  "task_id": "944f5db2-2e0c-423e-aafa-95f15557fcb5",
  "display_id": "tsk-944f5db2",
  "status": "DRAFT",
  "lead_agent_id": "f9b49965-74a8-53d0-88bc-d3f349c56f05",
  "lead_agent_display_id": "agt-planner",
  "current_revision_id": "932512cc-e88c-4c86-8523-bf1e10e9d288",
  "revision_display_id": "rev-932512cc",
  "supervisor_session_id": "48f22c94-30e5-476c-8110-5132ad64c785",
  "supervisor_display_id": "sup-48f22c94",
  "supervisor_state": "PENDING",
  "prompt_digest": "sha256:75965d165f7b81eb81e97785562d261ac40ea92f32728c618c2127bde249e5ef",
  "prompt_bytes": 99,
  "created_at": "2026-10-30T07:56:20.269396Z",
  "created": true
}
```

## 4. Live rows and audit chain

Read-only queries against the configured PostgreSQL database
(`127.0.0.1:5432/noahsark`):

| Fact | Value |
|---|---|
| Task | `tsk-944f5db2`, `DRAFT`, `conversation`, `voice_interaction`, created `2026-10-30 15:56:20.269396+08` (= `07:56:20.269396Z`) |
| Origin | `submitted_by=demo-admin`, `entry_mode=conversation`, `correlation_id=e155d0b2f8bd40889a8f40fe621e56bd` |
| Revision | `rev-932512cc`, revision 1, `initial`, `DRAFT`, `content_digest=sha256:160bb62b844925ef78b9d243e652c34e98d20ad5e00fa923f47f2902e2af1833` |
| Binding | `sup-48f22c94`, `PENDING`, `remote_session_id=NULL`, `result_summary=NULL`, `error_code=NULL`, `result_updated_at=NULL` |
| Timestamps | task = revision = binding = `2026-10-30 15:56:20.269396+08` |
| Prompt record | `sha256:75965d165f7b81eb81e97785562d261ac40ea92f32728c618c2127bde249e5ef`, `99` bytes — identical on revision content and binding |
| Revision content keys | `title`, `objective`, `entry_mode`, `prompt_bytes`, `prompt_digest`; **no** `prompt` key |
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

| Occurred (UTC) | Offset vs create | Action | Object | Creation-state payload |
|---|---|---|---|---|
| 07:56:20.275088 | +5.7 ms | `TASK_CREATED` | `tsk-944f5db2` | `status=DRAFT` |
| 07:56:20.277432 | +8.0 ms | `TASK_REVISION_CREATED` | `rev-932512cc` | `revision_number=1`, `change_kind=initial`, digest/bytes |
| 07:56:20.279468 | +10.1 ms | `SUPERVISOR_SESSION_CREATED` | `sup-48f22c94` | `state=PENDING`, `remote_session_id=null`, `prompt_bytes=99` |

The binding is therefore not a later side effect of dispatch: it was committed
with the task, and its creation event records the unclaimed `PENDING` state.

## 5. Read projection and UI panel

`GET http://127.0.0.1:8100/api/v1/tasks/944f5db2-2e0c-423e-aafa-95f15557fcb5/supervisor`
returned HTTP 200 (issued by the page poll and re-issued by curl as
`X-NoahsArk-Role: OBSERVER`):

- `state=PENDING`, `state_is_terminal=false`;
- `supervisor_display_id=sup-48f22c94`;
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
task_id            944f5db2-2e0c-423e-aafa-95f15557fcb5
display_id         tsk-944f5db2
supervisor_state   PENDING
remote_session_id  —
查看任务详情
```

The panel text was unchanged after the supervisor poll (binding still
`PENDING`), confirming the panel renders server data rather than fixture data —
the same task id appears in the POST response, the database row and the panel.

### 5.1 Post-capture lifecycle (outside the creation proof)

About 74 seconds after creation, the independent supervisor worker claimed the
binding and completed it. A later read-only query shows:

| Fact | Value |
|---|---|
| State | `COMPLETED`, `state_is_terminal=true` |
| Remote session | `ses_e742f9bd2ffeiVSSqmkxKjKn7z` (stored in `supervisor_sessions`, not exposed raw) |
| Result | `summary="PONG"`, `error_code=NULL`, `result_updated_at=2026-10-30T07:57:34.702133Z` |
| Timestamps | `created_at=07:56:20.269396Z`, `updated_at=07:57:34.702133Z` |

`GET /api/v1/tasks/tsk-944f5db2/supervisor` (display id, `OBSERVER`) then
returned 200 with `state=COMPLETED`, `remote_session_id="ses_***Kn7z"`
(masked), and `result.available=true, summary="PONG"`, while the creation audit
events remain unchanged at `PENDING`. This confirms the binding created by the
UI submission is the same row later claimed and executed by the supervisor
worker. It is reported here as corroboration only; the acceptance claim is the
creation-time behaviour in sections 1–5.

## 6. Non-mutating UI regression checks

```bash
cd design/ui-app && npm run check
```

Result: **123 passed, 0 failed** (contract) and **358 passed, 0 failed**
(smoke). These assert the form markup, submit wiring, `/tasks` POST path,
response polling, masked supervisor id, and no fixture fallback. No
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
supervisor worker had claimed it yet. The same row was later claimed by the
worker and reached `COMPLETED` with `summary="PONG"` (section 5.1); that
lifecycle is corroboration and is not the acceptance claim.

The round task `tsk-3abf37a9` itself is a prior live UI-origin submission
(created 2026-10-30T07:44:37.784827Z); its binding already reached `STOPPED`,
which shows the same wiring end-to-end but no longer exposes the creation-time
`PENDING` state. The fresh submission above is used to capture that state.

No code, migration or configuration was modified for this verification.
