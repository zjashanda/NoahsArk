# NoahsArk — AI Test Platform v2 Decision-Complete Implementation Plan

> Target file: `.omo/plans/ai-test-platform-v2.md`（历史路径；当前主计划为 `.omo/plans/noahsark-platform-delivery.md`）
> Canonical repo: **NoahsArk** (`https://github.com/zjashanda/NoahsArk`, empty public repo, `main`); local workspace: `E:\aswxStation\tmpskill\0000\noahsark`（历史工作区记录，当前工作区为 `/home/bszheng/NoahsArk`）。
> Product name: **NoahsArk**; logo concept: **an ark**.
> Execution mode: one checkbox = one atomic work unit = one commit. No checkbox is "done" without its verification command and evidence.
> Current gate: **历史闸门已取代（2026-10-28）**。当前只执行 [NoahsArk 平台交付总计划](../../.omo/plans/noahsark-platform-delivery.md) 的 Phase 0–6；本文件的 81 项复选框不是当前施工 WBS。

## 规范同步说明（2026-10-28，P0-03）

> **本文整体转为历史参考，不再是当前实施计划。** 当前执行主线是 [NoahsArk 平台交付总计划](../../.omo/plans/noahsark-platform-delivery.md)；真实施工 WBS 由 Phase 3 产出。本文已定点修正：SQLite → PostgreSQL（唯一正式数据库）；单一终态 → 五轴 + 执行/设备/证据/判定分离；租约/心跳过期不停止已启动冻结压测、不回收设备；缺 `cleanup_receipt` 仅阻断释放确认；81 项计数为历史。逐项修改与仍属历史的内容见 [openspec 与 docs/v2 规范同步记录](../delivery/openspec-v2-sync.md)。P0-03 不构成实现、测试、部署或验收通过。

---

## 1. Goal

Build NoahsArk as a **project-aware, self-accumulating AI senior test engineer platform** that:

1. Switches the primary/default model at runtime (global / per-agent / per-task) with validation, fallback and no restart.
2. Locks the versions of opencode, OMO, self-developed plugins and skills, and automatically proves compatibility after upgrades.
3. Pushes task events/results actively to a terminal subscriber, local file, HTTP webhook or the platform event bus.
4. Retrieves similar historical tasks and their plans on intake, and persists each new plan/playbook back for future retrieval.
5. Stores failures, problematic logs, root causes, script fixes and all project/tool/platform knowledge, with write-back after every task.
6. Defines "task complete" as a binary, evidence-backed contract, with no false completion possible.
7. Supports human takeover of a running task, including attaching a terminal to the CLI session that launched it, replaying history and accepting new input.
8. Ships a UI that fully matches the platform: tasks, task detail, knowledge, nodes, models, versions, push, takeover, progress bars.
9. Enforces real execution: real nodes/devices/scripts; dry-run is preflight only and can never be completion evidence.
10. Uses OpenSpec per agent context, with generated agent config files, requirement management and review gates for generated plans/cases/scripts.
11. Produces good plans/cases/oracles through retrieval + deterministic assurance + adversarial review, not prompt-only generation.

**Definition of plan success:** all Phase 8 gates pass on a real device, and a second, previously-unseen task retrieves and reuses the first task's playbook without a human re-explaining the method.

### 1.1 Role Charter — AI Senior Test Engineer

The platform is not a task runner. It must behave like a senior test engineer:

1. **Clarify before executing.** If requirement scope, acceptance, sample size, environment or oracle is ambiguous, ask and record the answer; never silently assume.
2. **Risk-based strategy.** Choose test depth, scenarios and sample sizes by project/device risk, not a uniform checklist.
3. **Knowledge-first order.** Retrieve the **project KB (how to test)** first, then the **tool KB (lstest: how to build/execute)**, then design the run.
4. **Falsifiable oracle.** Expected results must be independently checkable and bound to evidence; no circular assertion, no “the script said PASS”.
5. **Build on lstest.** Use the framework/profile/tool contracts; never fork or copy `lstest`; the script is a means, not the goal.
6. **Real execution.** Real nodes, devices, serial/audio endpoints and scripts. Dry-run/mock/replay can prepare but cannot be completion evidence.
7. **Diagnose like an engineer.** Separate product, test logic, environment, infrastructure and requirement problems; raw FAIL is converged before it becomes a final FAIL.
8. **Refuse false PASS.** Insufficient evidence → BLOCKED/WARN/TIMING_AMBIGUOUS; never please the requester with an unsupported pass.
9. **Teach the platform.** Write back playbooks, failure cases, root causes, script fixes and project/tool knowledge; dedupe, version and mark applicability.
10. **Explain decisions.** Every plan, case, oracle and verdict cites requirement, method and evidence; no unexplained conclusion.
11. **Escalate at the right time.** Human approval for ambiguous/high-risk/irreversible work; support takeover and explicit stop.
12. **Improve measurably.** Track false-pass escapes, review findings, knowledge reuse, tool-fix rate and rework; use the metrics to improve the next task.

**Role scorecard (evaluated in P4-13):** requirement clarification completeness, requirement→case traceability, oracle independence, false-pass escapes, root-cause classification accuracy, knowledge reuse rate, script/tool fix rate, review blocking findings resolved, real-run ratio.

---

## 2. Non-goals

- No rewrite to Vue/Element Plus. The existing platform is Flask + Jinja2 + vanilla JS + SSE; the plan extends that stack (see D2).
- No second workflow state machine. The existing `aitest` workflow remains the only state truth; v2 modules are contracts, projections and command producers.
- No model/agent direct writes to `aitest_runs`, leases, terminal states, approved knowledge or release state.
- No auto-promotion of candidate knowledge to `approved`; no roundtable majority vote as an acceptance gate.
- No cross-machine credential copying; provider secrets never reach nodes, KB, logs or UI.
- No "pass by mock". Mock/recorded/replay runs are allowed only in unit tests and preflight, never as completion evidence.
- No production cutover of the dry-run `V2Runtime` handlers as part of this plan; new capabilities attach to the real legacy execution path through the adapter.
- No multi-tenant SaaS, billing or internet-facing auth redesign.

---

## 3. Key Architecture Decisions

### D1. Build NoahsArk as an original platform

NoahsArk is a new codebase. The legacy platform is not a dependency: no UI, routes, templates, execution adapters, runtime, data schema, or fixtures are imported. V2 adds bounded modules under `src/noahsark/aitest/platform/` and wires them through NoahsArk's own command/state paths.

- UI: build `src/noahsark/templates/console/` with shared macros and `src/noahsark/static/aitest/` ES modules. Use the NoahsArk Console design tokens in `docs/v2/UI-DESIGN.md`.
- Backend: Flask blueprints. `server.py` is the application entry and must not grow: new routes live in `src/noahsark/aitest/platform/api.py`, registered by a thin blueprint include. CI enforces `server.py` growth <= 20 lines per change.

### D2. Stack: Flask + Jinja2 + vanilla ES modules + SSE + PostgreSQL

> **规范同步（2026-10-28）**：原标题与正文的 “SQLite WAL” 已取代。PostgreSQL 是唯一正式数据库；SQLite 只可作为历史参考或只读分析副本，不是实施依赖。

- No Node build step for the platform UI. `xterm` is bundled locally for intranet use.
- DB: PostgreSQL is the only formal database. New schema via an idempotent migration runner with transactions, constraints and indexes; migration is backup-before-apply and rollback-tested. PostgreSQL HA, replication and backup topology are frozen in the master plan Phase 2/3, not in this historical section.

### D3. Two planes, one truth
- **Intelligent plane:** Lead agent, planner, case writer, script implementer, reviewers, roundtable. Produces typed candidate artifacts and `AgentEffect`s.
- **Deterministic plane:** workflow, permission, leases, dispatch, lstest, evidence, verify, completion gate, archive. Owns all irreversible facts.
- Agents can propose; only the command facade can mutate runs, gates, leases, verdicts, approved knowledge or releases.

### D4. Model binding is a first-class, versioned object
Resolution precedence: **task override → agent override → global default → compiled fallback chain**. Every resolution yields an immutable `ModelBinding` with source, candidates, catalog version, capability snapshot and health snapshot. Switching is applied at the next turn boundary by default; `interrupt` is explicit and only at a safe checkpoint. No process restart.

### D5. Completion is a gate object, not a status string
`CompletionGate.evaluate(task)` produces a hashed report with gate-by-gate evidence references. A terminal state cannot be written without a valid report. `PASS` must additionally pass all business/evidence gates; `FAIL` must prove real execution and a firmware/requirement root cause. **历史标注（2026-10-28）**：旧单一终态口径及其 `BLOCKED_HUMAN is non-terminal` 说法已被五轴 + 执行/设备/证据/判定分离取代，仅作报告兼容别名；详见 5.1 节与 [规范同步记录](../delivery/openspec-v2-sync.md)。

### D6. Event-first integration
Every meaningful transition appends to `platform_events` (monotonic `seq`, unique `idempotency_key`). Push, UI SSE, CLI watch, retrieval metrics and audit all consume this log. Delivery is at-least-once with consumer-side dedupe; push failure never blocks a task.

### D7. Knowledge is evidence-scoped and status-gated
`candidate → corroborated → approved → stale → retracted`, plus `disputed`. Provenance is mandatory. Failure cases, bad logs, root causes and rejected plans are first-class assets. Retrieval returns provenance, applicability, conflicts and counterexamples, and is injected as untrusted evidence with citations.

### D8. Takeover is a fenced lease on an executor session, not a raw shell
A task can be observed or interactively controlled. Interactive takeover pauses the agent at a turn boundary, replays history, accepts typed input, and resumes from a checkpoint. Device actions remain behind the command facade and idempotency keys.

### D9. OpenSpec is the change boundary; agent config is generated
Requirements become OpenSpec changes. Agent roles live in one registry (`config/agents/registry.yaml`) and are rendered to `.opencode/agent/*.md` + `opencode.json`. Each role declares its OpenSpec context pack, commands, write scope, model policy, skills and review requirement. Hand-edited agent configs are drift-checked and rejected.

### D10. Toolchain compatibility is machine-verified
`config/toolchain.lock.json` is the single lock. `config/toolchain.compat.json` maps version ranges to smoke suites. Plugin/tool contract snapshots detect schema drift. Startup verifies the lock; drift runs tier-1 smoke and fails closed for real execution until acknowledged.

### D11. Real-run proof is cryptographically attributable
A run is `real` only with a node executor receipt (node id, lease id, endpoint identities, runner exit, artifact manifest hash) signed by the node agent. `dry_run`, `simulated`, `recorded` and `replay` modes are explicit and inadmissible as completion evidence.

### D12. Feature flags, default off, fail closed
`NOAHSARK_V2_ENABLED` plus per-capability flags (`MODEL_SWITCH`, `PUSH`, `RETRIEVAL`, `COMPLETION_GATE`, `TAKEOVER`, `UI_V2`). Unknown values are off. V2 tasks never silently fall back to legacy completion.

### D13. Security and secrets
Provider credentials stay in the server credential broker; only `credential_ref` is stored. Webhooks use HMAC-SHA256 with timestamp and SSRF allowlist. Takeover and admin actions are audited. KB ingestion rejects secrets/PII patterns. Generated file writes require a review receipt.

---

## 4. Execution Model for Ultrawork

- **Work unit size:** S ≤ 0.5 day, M = 1–2 days, L = 3–5 days for one focused agent.
- **TDD rule:** every code task starts by committing a failing test (red), then the minimum implementation (green), then refactor. Contract/schema tasks start with a failing schema-validation test. Docs/config-only tasks require a schema or link check instead.
- **Parallel ownership:** each track owns distinct files. Shared files (`platform/contracts.py`, `platform/db.py`, `templates/console/base.html`) are Phase 0 only, then frozen; changes require the track lead.
- **Wave gate:** a wave is complete only when `python scripts/verify_platform_gate.py --wave N` passes and evidence is appended to `.omo/evidence/ai-test-platform-v2/wave-N/`.
- **Notepad:** append learnings/issues/decisions to `.omo/notepads/ai-test-platform-v2/{learnings,issues,decisions,problems}.md`.
- **No checkbox is closed by a subagent alone:** the orchestrator verifies the command output and the evidence file before ticking it.

**Parallel tracks after Phase 0**

| Track | Scope | Files (ownership) |
|---|---|---|
| A | Models + versions | `platform/model_*.py`, `platform/toolchain_*.py`, `config/toolchain.*` |
| B | Push + events | `platform/events.py`, `platform/push_*.py`, `scripts/ark_task.py` |
| C | Knowledge + retrieval | `platform/kb_*.py`, `platform/retrieval*.py`, `platform/failure_miner.py` |
| D | Planning + OpenSpec/agents | `platform/requirements*.py`, `platform/plan_*.py`, `platform/review*.py`, `config/agents/` |
| E | Completion + takeover | `platform/completion*.py`, `platform/takeover*.py`, `platform/session_registry.py` |
| F | UI | `templates/console/**`, `static/aitest/**` |

Tracks A–E run concurrently after P0. F starts when the first API contract per page is stable; it may mock only its own data fixtures, never the backend contract.

---

## 5. Contracts (must be frozen before code)

### 5.1 Terminal states and completion gates

**Historical terminal states (superseded 2026-10-28):** `PASS | FAIL | BLOCKED_HUMAN | CANCELLED | STOPPED | INFRA_ERROR`. `WAITING_HUMAN` is non-terminal. No `DONE`. These names remain only as report-compatibility aliases; they are **not** the current verdict model.

**Current verdict model:** lstest five axes plus separated facts. A task does not have one all-purpose status.

| Axis / fact | Values | Meaning |
|---|---|---|
| `execution_status` | `NOT_STARTED / RUNNING / COMPLETED / ABORTED / SKIPPED` | Whether the run executed; not a business result |
| `validity_status` | `VALID / INVALID / BLOCKED / UNKNOWN` | Whether input/environment is valid |
| `business_verdict` | `PASS / FAIL / EXPECTED / WARN / NEEDS_REVIEW / NOT_EVALUATED` | Business conclusion |
| `evidence_status` | `COMPLETE / INCOMPLETE / CONFLICTED / UNVERIFIED` | Necessary evidence state; independent of device release |
| `verification_status` | `PASS / FAIL / NOT_RUN` | Linux independent recomputation |
| Device occupancy | `OCCUPIED / RELEASING / RELEASED / QUARANTINED` | Does not become `RELEASED` on heartbeat loss |
| Communication | `ONLINE / OFFLINE / STALE` | `OFFLINE` never means the device is free |

Formal PASS requires `execution_status=COMPLETED`, `validity_status=VALID`, `evidence_status=COMPLETE`, `business_verdict=PASS` and `verification_status=PASS`; a `RUNNING` or `NOT_STARTED` execution cannot be a formal PASS. C1–C7 below are completion/archive gates over these facts, not a replacement for the five axes.

| Gate | Requirement | Binary evidence |
|---|---|---|
| C1 Plan | Approved immutable plan revision + assurance pass + approval actor/time | `plan_revision_sha256`, `assurance_report_id`, `approval_id` |
| C2 Real execution | `run_mode=real`, non-zero runner receipt signed by node, lease id, endpoint identities | `executor_receipt` hash, `device_lease_id`, `node_id` |
| C3 Artifacts | Manifest hash matches; required files present; no traversal/truncation/extra | `artifact_manifest_sha256` + per-file hashes |
| C4 Verdict | Machine verdict independently recomputed; runner vs recompute divergence resolved; human/business policy applied | `verdict_report_id`, divergence resolution |
| C5 Evidence sufficiency | Required evidence kinds per case present; no empty capture; denominators valid | `evidence_graph_id` + per-case evidence refs |
| C6 Knowledge write-back | Task playbook + failure entries persisted, or explicit `no_reusable_knowledge` reason | `playbook_id` / `kb_candidate_ids` |
| C7 Reproducibility | Toolchain lock hash, lstest pin, model binding ids, env fingerprint | `repro_manifest_sha256` |

**Rules**
- `PASS` requires C1–C7 all pass.
- `FAIL` requires C1–C5 + C7; C6 is required before archive.
- `CANCELLED` before execution may skip C2/C3 but still requires an archive receipt and must not claim a verdict.
- `STOPPED` and `INFRA_ERROR` preserve artifacts and require C7; no product verdict.
- DB trigger rejects `terminal_state IS NOT NULL` when `completion_report_id` is null or `eligible=0`.
- A watchdog scans for violations at startup and each tick; violations emit `completion.invariant_violation`.

### 5.2 Model binding

```json
{
  "schema": "aitest.model_binding.v1",
  "binding_id": "mb-...",
  "task_id": "ait-...",
  "agent_role": "planner",
  "resolution_source": "task|agent|global|compiled_fallback",
  "primary": {"provider": "listenai", "model_id": "...", "family": "...", "capabilities": ["json_schema","tool_calling"]},
  "candidates": [{"provider": "...", "model_id": "...", "family": "...", "tier": 1}],
  "catalog_version": "cat-...",
  "health_snapshot": {"state": "healthy", "checked_at": "..."},
  "revision": 7,
  "switched_by": "user:42",
  "reason": "manual switch",
  "created_at": "..."
}
```

- Capability requirements are per use: planner → `json_schema`; script implementer → `tool_calling`; vision/document analysis → `vision`.
- Error classification: transient (`timeout`, `rate_limit`, `unavailable`, `5xx`) → next candidate; permanent (`auth`, `model_not_allowed`, `budget`) → `MODEL_BLOCKED` event + human action, no silent downgrade for multi-model panels.
- Panel diversity rule: if fewer than two families remain healthy, emit `PANEL_DEGRADED` and continue explicitly; never claim multi-model review.

### 5.3 Event and push envelope

```json
{
  "schema": "aitest.event.v1",
  "seq": 12345,
  "event_id": "evt-...",
  "idempotency_key": "task:ait-1:completed:exec-9",
  "type": "task.completed",
  "severity": "info|warning|critical",
  "task_id": "ait-...",
  "occurred_at": "2026-10-26T12:00:00Z",
  "payload": {},
  "redaction": {"applied": true, "fields": ["authorization"]}
}
```

Channels: `sse`, `terminal`, `file`, `webhook`. Delivery record: `delivery_id`, `subscription_id`, `event_id`, `attempt`, `status`, `last_error`, `next_attempt_at`. Retry schedule: 1s, 5s, 30s, 5m, 1h → dead letter. Webhook headers: `X-Ark-Event-Id`, `X-Ark-Timestamp`, `X-Ark-Signature: sha256=<hmac>`.

`task.completed` is emitted exactly once per task after C1–C7 and archive; push failure must not change task state.

### 5.4 Retrieval packet

```json
{
  "schema": "aitest.retrieval_packet.v1",
  "query": {"project_id": "...", "device_class": "...", "text": "...", "tags": []},
  "hits": [{
    "kind": "task_playbook|failure_case|methodology|project_fact|script_fix",
    "id": "...", "score": 0.82, "why_matched": ["device_class","tag:wake"],
    "status": "approved|corroborated|candidate|disputed|stale",
    "applicability": {"lstest_pin": "...", "firmware": "...", "scope": "..."},
    "reusable_blocks": ["case-set","oracle","preflight"],
    "differences": ["different firmware"],
    "warnings": ["produced by older lstest pin"],
    "citations": ["[knowledge:kb-1@3#chunk-2]"]
  }],
  "truncated": false
}
```

### 5.5 Takeover contract

```
target_kind: lead | workunit | node
mode: observe | interactive
lease_epoch: monotonic integer (CAS)
pause: at next turn boundary; never mid-device-action
input: {text, interrupt: bool}
release: resumes from checkpoint; duplicate effect keys rejected
timeout: default 30 min idle, auto-release + event
```

### 5.6 Toolchain lock

Components: `opencode` (version, commit, binary sha256), `omo` (version, git sha, entry sha256, tool-contract sha256), each self-developed plugin (`id`, version, git sha, entry sha256), each platform-used skill (`id`, `SKILL.md` sha256, source repo/commit), Python, PostgreSQL, `lstest` pin/tree sha, platform commit. `compat` block records minimum and last-tested versions. **规范同步（2026-10-28）**：原文 SQLite 条目已取代；PostgreSQL 是唯一正式数据库。

### 5.7 Agent registry and OpenSpec context

```yaml
# config/agents/registry.yaml
schema: aitest.agent_registry.v1
roles:
  planner:
    model_policy: {agent_role: planner, requires: [json_schema]}
    openspec_context: [test-plan-design, test-plan-assurance, project-material-intake]
    openspec_commands: [list, show, propose, validate]
    write_scope: [".aitest/local/plans/**"]
    review_required: true
    tools: [read, grep, glob, bash_readonly]
  case_writer: {...}
  script_implementer:
    openspec_commands: [apply, validate]
    write_scope: ["openspec/changes/<change>/tasks.md", "src/**"]
    review_required: true
  reviewer:
    openspec_commands: [show]
    write_scope: []
    tools: [read, grep, glob]
```

Rendered outputs: `.opencode/agent/<role>.md`, `opencode.json` agent entries, and `docs/agents/context-packs.md`. Drift check fails CI if rendered output differs from the registry.

---

## 6. Phase 0 — Foundation (serial, blocking)

- [ ] **P0-01 OpenSpec change and capability deltas (S)** — create the formal change before code.
  - Depends: none
  - Files: `openspec/changes/ai-test-platform-v2/{proposal.md,design.md,tasks.md,specs/*/spec.md}`
  - Acceptance: change validates with `openspec validate ai-test-platform-v2 --strict`; specs cover `runtime-model-switching`, `toolchain-compatibility`, `active-result-push`, `task-playbook-retrieval`, `failure-knowledge-base`, `completion-contract`, `human-takeover`, `platform-ui-v2`, `agent-openspec-governance`; existing main specs are referenced, not duplicated.
  - Verify: `openspec validate ai-test-platform-v2 --strict`; `openspec show ai-test-platform-v2 --json`
  - Size: S

- [ ] **P0-02 Repo layout, module boundaries and blueprint wiring (M)** — create the bounded v2 package without growing `server.py`.
  - Depends: P0-01
  - Files: `src/noahsark/aitest/platform/{__init__,api,contracts,db,events,settings}.py`, `src/noahsark/aitest/platform/migrations/`, `tests/platform/`, `scripts/verify_platform_gate.py`, `.omo/evidence/ai-test-platform-v2/`
  - Acceptance: `platform` blueprint is registered by ≤20 new lines in `server.py`; all v2 routes live under `/api/aitest/v2/**` and `/aitest/**`; import graph has no cycles; feature flags default off; a route inventory test lists every v2 route.
  - Verify: `python -m pytest tests/platform/test_layout.py tests/platform/test_routes.py -q`; `python scripts/check_server_growth.py --max-lines 20`
  - Size: M

- [ ] **P0-03 Migration runner and schema v1 (M)** — additive, idempotent, rollback-tested schema.
  - Depends: P0-02
  - Files: `src/noahsark/aitest/platform/migrations/0001_platform_core.py`, `db.py`, `tests/platform/test_migrations.py`
  - Acceptance: tables created: `platform_events`, `platform_settings`, `model_bindings`, `model_switch_audit`, `agent_profiles`, `task_model_overrides`, `push_subscriptions`, `push_deliveries`, `push_dead_letters`, `kb_entries`, `kb_revisions`, `kb_links`, `kb_feedback`, `kb_fts`, `task_playbooks`, `task_retrievals`, `executor_sessions`, `takeover_sessions`, `takeover_events`, `toolchain_lock_runs`, `toolchain_smoke_runs`, `completion_reports`, `completion_gate_evidence`, `executor_receipts`; re-running is a no-op; PostgreSQL transactions, constraints and indexes applied（2026-10-28 修正：原 WAL/foreign keys/busy timeout 为 SQLite 口径，已取代）; backup-before-migrate and rollback tested.
  - Verify: `python -m pytest tests/platform/test_migrations.py -q`; `python -m noahsark.aitest.platform.db --check`
  - Size: M

- [ ] **P0-04 Frozen contract schemas and validators (M)** — all shared types before feature code.
  - Depends: P0-03
  - Files: `src/noahsark/aitest/platform/contracts.py`, `schemas/*.json`, `tests/platform/test_contracts.py`
  - Acceptance: validators for model binding, event, push subscription/delivery, retrieval packet, playbook, failure entry, completion report, executor receipt, takeover session, toolchain lock, agent registry; invalid/missing/extra fields fail with paths; unknown schema version fails closed; golden valid/invalid fixtures cover every contract.
  - Verify: `python -m pytest tests/platform/test_contracts.py -q`
  - Size: M

- [ ] **P0-05 Event log, SSE replay, outbox foundation (M)** — one append-only truth for all v2 features.
  - Depends: P0-03, P0-04
  - Files: `src/noahsark/aitest/platform/events.py`, `api.py`, `tests/platform/test_events.py`
  - Acceptance: `append_event` is idempotent on `idempotency_key`; monotonic `seq`; `GET /api/aitest/v2/events?after=N` replays; `GET /api/aitest/v2/events/stream` sends `id: <seq>` and honors `Last-Event-ID`; duplicate append returns the original event; payload redaction applied before persistence.
  - Verify: `python -m pytest tests/platform/test_events.py -q`; `python scripts/probe_sse_v2.py --expect-replay`
  - Size: M

- [ ] **P0-06 Test harness, fixtures and CI commands (S)** — make TDD cheap and deterministic.
  - Depends: P0-02
  - Files: `tests/platform/conftest.py`, `tests/platform/factories.py`, `scripts/run_platform_tests.py`, `scripts/verify_platform_gate.py`
  - Acceptance: temp DB per test; fake clock; fake provider broker; fake node executor; fake event sink; HTTP client with auth roles 1–4; no test touches the production DB; gate script runs unit + contract + flag-off + migration checks.
  - Verify: `python scripts/verify_platform_gate.py --wave 0`
  - Size: S

- [ ] **P0-07 Security baseline and command facade extension (S)** — close the obvious abuse paths before adding power.
  - Depends: P0-03
  - Files: `src/noahsark/aitest/platform/security.py`, `tests/platform/test_security.py`
  - Acceptance: central redaction (authorization, cookies, tokens, keys); RBAC helper (`role>=N`, owner scoping); webhook URL policy (https, private-network allowlist, no loopback by default); path guard for artifact/KB reads; secret-pattern scan on KB ingest; every v2 write emits an audit event with actor/action/target/result.
  - Verify: `python -m pytest tests/platform/test_security.py -q`
  - Size: S

- [ ] **P0-08 ADR set and execution docs (S)** — record the decisions above and the upgrade/rollback rules.
  - Depends: P0-01
  - Files: `docs/v2/adr/0001..0012`, `docs/v2/EXECUTION-RUNBOOK.md`, `docs/v2/FEATURE-FLAGS.md`
  - Acceptance: D1–D13 each has an ADR with context/decision/consequences; runbook documents wave gates and rollback; no undocumented flag.
  - Verify: `python scripts/check_docs_links.py docs/v2`
  - Size: S

**Phase 0 exit gate:** `python scripts/verify_platform_gate.py --wave 0`; all contracts frozen; no feature flag enabled.

---

## 7. Phase 1 — Model Registry and Runtime Switching

- [ ] **P1-01 Model catalog snapshot and capability probe (M)** — know what models exist and what they can do.
  - Depends: P0-04, P0-06
  - Files: `src/noahsark/aitest/platform/model_catalog.py`, `tests/platform/test_model_catalog.py`
  - Acceptance: catalog sync from the existing provider broker / `opencode models listenai`; persists `catalog_version`, model family, capabilities, health, quota; stale snapshot is readable but never selectable for a new binding; no secret or raw command in the response.
  - Verify: `python -m pytest tests/platform/test_model_catalog.py -q`; `python scripts/probe_models_v2.py --json`
  - Size: M

- [ ] **P1-02 Model policy resolver with precedence (M)** — deterministic, explainable binding.
  - Depends: P1-01
  - Files: `src/noahsark/aitest/platform/model_policy.py`, `tests/platform/test_model_policy.py`
  - Acceptance: task > agent > global > compiled fallback; returns `resolution_source` and candidate chain; missing/invalid override fails without mutating settings; capability requirement mismatch rejects; two concurrent switches use revision CAS; property test covers random override combinations.
  - Verify: `python -m pytest tests/platform/test_model_policy.py -q`
  - Size: M

- [ ] **P1-03 Hot switch service and audit (M)** — no restart, no mid-action surprises.
  - Depends: P1-02
  - Files: `src/noahsark/aitest/platform/model_switch.py`, `tests/platform/test_model_switch.py`
  - Acceptance: `switch(scope, target, model, actor, validate, mode)` writes settings + audit + event; `next_turn` leaves in-flight turn untouched; `interrupt` requests a safe stop and applies after checkpoint; effective binding visible per task/agent; process start time unchanged (test asserts PID).
  - Verify: `python -m pytest tests/platform/test_model_switch.py -q`; `python scripts/probe_model_hot_switch.py`
  - Size: M

- [ ] **P1-04 Validation, fallback and degradation policy (M)** — behave correctly when a model fails.
  - Depends: P1-03
  - Files: `src/noahsark/aitest/platform/model_fallback.py`, `tests/platform/test_model_fallback.py`
  - Acceptance: transient errors advance the chain; permanent errors emit `MODEL_BLOCKED` and stop; budget/quota respected; panel family diversity enforced or explicit `PANEL_DEGRADED`; every attempt recorded in `aitest_model_usage` with binding id.
  - Verify: `python -m pytest tests/platform/test_model_fallback.py -q`
  - Size: M

- [ ] **P1-05 Model APIs (S)** — stable surface for UI/CLI.
  - Depends: P1-03, P1-04
  - Files: `src/noahsark/aitest/platform/api_models.py`, `tests/platform/test_api_models.py`
  - Acceptance: `GET /api/aitest/v2/models`, `GET /api/aitest/v2/models/bindings`, `PUT /api/aitest/v2/models/global`, `PUT /api/aitest/v2/models/agents/<role>`, `PUT /api/aitest/v2/models/tasks/<task_id>`, `POST /api/aitest/v2/models/test`; RBAC: role 3 for task, role 4 for global; 422 on validation; no restart; responses contain no secrets.
  - Verify: `python -m pytest tests/platform/test_api_models.py -q`
  - Size: S

- [ ] **P1-06 CLI model control (S)** — operate without the UI.
  - Depends: P1-05
  - Files: `scripts/ark_model.py` (entry `ark model ...`), `tests/platform/test_cli_model.py`
  - Acceptance: `ark model list|show|set --scope global|agent|task|test`; prints effective binding and source; nonzero exit on validation failure; writes audit actor `cli:<user>`.
  - Verify: `python -m pytest tests/platform/test_cli_model.py -q`; `python scripts/ark_model.py show --task ait-demo`
  - Size: S

- [ ] **P1-07 Binding snapshot in delivery/reproducibility (S)** — answer "which model produced this?".
  - Depends: P1-04
  - Files: `src/noahsark/aitest/platform/model_snapshot.py`, extend `delivery_manifest.py`, tests
  - Acceptance: delivery manifest lists every binding id, model, role, turn range; reproducibility manifest hash changes when a binding changes.
  - Verify: `python -m pytest tests/platform/test_model_snapshot.py tests/test_aitest_delivery_integrity.py -q`
  - Size: S

---

## 8. Phase 2 — Active Push and Terminal Reporting

- [ ] **P2-01 Outbox dispatcher with delivery ledger (M)** — reliable at-least-once delivery.
  - Depends: P0-05
  - Files: `src/noahsark/aitest/platform/push_dispatcher.py`, `tests/platform/test_push_dispatcher.py`
  - Acceptance: claims events with lease; retries with backoff; dead-letters after 5 attempts; consumer dedupe by `event_id`; dispatcher crash resumes without duplicate terminal notices; push failure emits a warning event but never changes task state.
  - Verify: `python -m pytest tests/platform/test_push_dispatcher.py -q`
  - Size: M

- [ ] **P2-02 SSE, file and terminal channels (M)** — the three local destinations.
  - Depends: P2-01
  - Files: `src/noahsark/aitest/platform/push_channels.py`, `tests/platform/test_push_channels.py`
  - Acceptance: SSE broadcasts with `Last-Event-ID`; file appends one JSON object per line under `var/outbox/<date>.jsonl` with fsync; terminal writes `var/run/events/<task_id>.ndjson`, emits bell/OSC-9 when a TTY; redaction applied; rotation and size caps.
  - Verify: `python -m pytest tests/platform/test_push_channels.py -q`; `python scripts/probe_push_file.py`
  - Size: M

- [ ] **P2-03 Webhook channel with HMAC and retries (M)** — external integration without leaks.
  - Depends: P2-01, P0-07
  - Files: `src/noahsark/aitest/platform/push_webhook.py`, `tests/platform/test_push_webhook.py`
  - Acceptance: signature and timestamp verified by a local sink; replay rejected; non-2xx retried per schedule; timeout bounded; URL policy enforced; secret read from env/credential ref and never logged; dead letter includes response status only.
  - Verify: `python -m pytest tests/platform/test_push_webhook.py -q`; `python scripts/push_sink.py --once` + probe
  - Size: M

- [ ] **P2-04 Subscription CRUD, filters and test send (M)** — configure what goes where.
  - Depends: P2-02, P2-03
  - Files: `src/noahsark/aitest/platform/push_api.py`, `tests/platform/test_push_api.py`
  - Acceptance: subscription has event types, min severity, project/task filter, channel, target, enabled; create/update/delete audited; role 4 for global targets; `POST /push/test` sends a synthetic `push.test` event (never a fake task result) and returns delivery id.
  - Verify: `python -m pytest tests/platform/test_push_api.py -q`
  - Size: M

- [ ] **P2-05 CLI task watch and terminal notification (S)** — the active-reporting entry users actually use.
  - Depends: P2-02, P2-04
  - Files: `scripts/ark_task.py` (`watch`, `events`, `notify-test`), `tests/platform/test_cli_watch.py`
  - Acceptance: `ark task watch <id>` streams history from `after=0` then live; prints one-line summaries; on `task.completed` prints verdict/gates/delivery path and emits bell; `--json` emits NDJSON; reconnect uses `Last-Event-ID`; Ctrl-C leaves the task untouched.
  - Verify: `python -m pytest tests/platform/test_cli_watch.py -q`; `python scripts/ark_task.py watch ait-demo --json`
  - Size: S

- [ ] **P2-06 Completion-only notification and dedupe tests (S)** — no premature "done".
  - Depends: P2-05, P0-04
  - Files: `tests/platform/test_push_completion.py`, `scripts/verify_push_contract.py`
  - Acceptance: `task.completed` is emitted only after C1–C7 + archive; duplicate completion attempts produce one notification; `BLOCKED_HUMAN`/`STOPPED` emit `task.blocked`/`task.stopped`, never `completed`; kill switch per subscription.
  - Verify: `python -m pytest tests/platform/test_push_completion.py -q`
  - Size: S

---

## 9. Phase 3 — Knowledge Base, Failure Capture and Similar-Task Retrieval

- [ ] **P3-01 Unified KB schema, FTS and lifecycle (M)** — make knowledge queryable and governable.
  - Depends: P0-03, P0-04
  - Files: `src/noahsark/aitest/platform/kb_store.py`, `kb_fts.py`, `tests/platform/test_kb_store.py`
  - Acceptance: `kb_entries` with kind/scope/status/provenance/applicability/counterexamples; revisions append-only; FTS5 trigram when available, else `unicode61` + Python CJK bigram `search_text`; CJK query recall test; status transitions validated (candidate→corroborated→approved; disputed/stale/retracted); model cannot set `approved`.
  - Verify: `python -m pytest tests/platform/test_kb_store.py -q`
  - Size: M

- [ ] **P3-02 Unified retrieval with ranking and citations (M)** — deterministic, explainable search.
  - Depends: P3-01
  - Files: `src/noahsark/aitest/platform/retrieval.py`, `tests/platform/test_retrieval.py`
  - Acceptance: searches task playbooks, failures, methodology, project facts, script fixes and ingested docs; filters project/device/firmware/pin/status/kind; bm25 × status weight × scope weight × recency × outcome; returns `why_matched`, conflicts, counterexamples, citations; stale/disputed never silently outrank approved; token budget enforced.
  - Verify: `python -m pytest tests/platform/test_retrieval.py -q`; fixture query returns expected top-1 for 10 golden cases
  - Size: M

- [ ] **P3-03 Intake retrieval packet (M)** — use history before planning.
  - Depends: P3-02
  - Files: `src/noahsark/aitest/platform/task_retrieval.py`, `tests/platform/test_task_retrieval.py`
  - Acceptance: on task create, builds query from requirement + device + tags, stores `task_retrievals.packet_json`, emits `retrieval.completed`; top-5 includes reusable blocks and warnings; planner context injection uses the packet with citations; no hits produces an explicit `no_history` packet.
  - Verify: `python -m pytest tests/platform/test_task_retrieval.py -q`
  - Size: M

- [ ] **P3-04 Playbook persistence after completion (M)** — the platform remembers how it tested.
  - Depends: P3-03, P0-04
  - Files: `src/noahsark/aitest/platform/playbooks.py`, `tests/platform/test_playbooks.py`
  - Acceptance: writes requirement signature, plan/case/oracle refs + hashes, environment prerequisites, evidence requirements, failure modes, outcome, reuse tags; idempotent per `(task, execution, plan_hash)`; only terminal tasks; emits `playbook.created`; `reusable=false` requires a reason.
  - Verify: `python -m pytest tests/platform/test_playbooks.py -q`
  - Size: M

- [ ] **P3-05 Failure miner and root-cause classification (L)** — turn bad runs into durable knowledge.
  - Depends: P3-04
  - Files: `src/noahsark/aitest/platform/failure_miner.py`, `root_cause.py`, `tests/platform/test_failure_miner.py`
  - Acceptance: consumes verify result, evidence graph, failed cases, `tool.log`, serial log signatures, model findings; classifies with the 14-step tree into `test_logic|env|device|firmware|requirement|infra|unknown`; final FAIL allowed only for firmware/requirement; signature dedupe; creates `failure_case` + `root_cause` candidates with evidence refs and log excerpts; idempotent on `(task, execution, kind, signature)`.
  - Verify: `python -m pytest tests/platform/test_failure_miner.py -q`; golden fixtures for 10 root-cause classes
  - Size: L

- [ ] **P3-06 Script-fix and tool knowledge writer (M)** — prevent repeating the same test-logic bug.
  - Depends: P3-05
  - Files: `src/noahsark/aitest/platform/tool_knowledge.py`, `tests/platform/test_tool_knowledge.py`
  - Acceptance: when root cause is `test_logic`, writes a `script_fix` candidate scoped to the tool/skill with diff, symptom, fix and evidence; links to `lstest` patch proposal when applicable; never edits a pinned tool automatically; review required before sharing.
  - Verify: `python -m pytest tests/platform/test_tool_knowledge.py -q`
  - Size: M

- [ ] **P3-07 Document ingestion and doc-analysis tasks (M)** — later document tasks are first-class.
  - Depends: P3-01
  - Files: `src/noahsark/aitest/platform/doc_ingest.py`, `doc_analysis.py`, `tests/platform/test_doc_ingest.py`
  - Acceptance: ingests md/txt/pdf-text/docx/xlsx-text with heading path, provenance, hash; chunk 800–1200 chars; dedupe by content hash; `doc_analysis` task produces structured requirement/metric/test-item extraction + open questions + KB candidates; review gate before promotion; secret/PII scan rejects.
  - Verify: `python -m pytest tests/platform/test_doc_ingest.py -q`
  - Size: M

- [ ] **P3-08 KB APIs and retrieval metrics (S)** — expose knowledge to UI and operators.
  - Depends: P3-02, P3-05
  - Files: `src/noahsark/aitest/platform/api_kb.py`, `tests/platform/test_api_kb.py`
  - Acceptance: list/search/detail/revisions/feedback/promote/retire endpoints; provenance and counterexamples in detail; promote requires review receipt and role 4; metrics: hit rate, reuse count, stale count, retrieval latency.
  - Verify: `python -m pytest tests/platform/test_api_kb.py -q`
  - Size: S

- [ ] **P3-09 Backfill and stale policy for existing KB (M)** — do not lose the existing `aitest_kb_entries`.
  - Depends: P3-01
  - Files: `scripts/backfill_kb_v2.py`, `tests/platform/test_kb_backfill.py`
  - Acceptance: maps legacy rows to `failure_case`/`task_playbook` with provenance, `lstest_pin` and original outcome; idempotent; counts reported; entries with missing provenance land as `candidate` and are excluded from auto-admission; rollback script.
  - Verify: `python -m pytest tests/platform/test_kb_backfill.py -q`; dry-run report reviewed
  - Size: M

- [ ] **P3-10 Consolidation job (S)** — "accumulate like a person" without duplicating.
  - Depends: P3-05, P3-08
  - Files: `src/noahsark/aitest/platform/consolidation.py`, `tests/platform/test_consolidation.py`
  - Acceptance: weekly job proposes merges of near-duplicate entries, stale candidates and corroboration upgrades; never auto-approves; proposals are reviewable KB candidates; job is budgeted and idempotent.
  - Verify: `python -m pytest tests/platform/test_consolidation.py -q`
  - Size: S

---

## 10. Phase 4 — Planning, Case/Oracle Generation, OpenSpec and Agent Config

- [ ] **P4-01 Requirement intake v2 (M)** — structured, sourced, uncertainty-aware.
  - Depends: P0-04, P3-03
  - Files: `src/noahsark/aitest/platform/requirements.py`, `tests/platform/test_requirements.py`
  - Acceptance: extracts project/chip/firmware/language/ports/audio devices, capability scope, default states, actions, numeric constraints, deleted/invalid items; source inventory with file/section/version; open questions; risk class A/B; requirement hash; missing critical fields → `BLOCKED_HUMAN`.
  - Verify: `python -m pytest tests/platform/test_requirements.py -q`
  - Size: M

- [ ] **P4-02 Functional model and validation-pool matching (M)** — map requirement points to reusable validation modules.
  - Depends: P4-01
  - Files: `src/noahsark/aitest/platform/functional_model.py`, `validation_pool.py`, `tests/platform/test_functional_model.py`
  - Acceptance: each functional point = intent + trigger + precondition + expected + state change + numeric constraint + evidence; tags map to validation-pool modules; multiple matching variants → `AMBIGUOUS` with probe/clarify items; unspecified dimensions never inherit old project defaults.
  - Verify: `python -m pytest tests/platform/test_functional_model.py -q`
  - Size: M

- [ ] **P4-03 Structured plan, case and oracle writer (M)** — typed artifacts, not prose.
  - Depends: P4-02
  - Files: `src/noahsark/aitest/platform/plan_writer.py`, `oracles.py`, `tests/platform/test_plan_writer.py`
  - Acceptance: emits `test_plan.v2` with coverage matrix, cases (id/title/requirement ref/preconditions/actions/expected/forbidden/evidence window/retry/assertion/evidence dir), oracles typed as `threshold|protocol_frame|log_sequence|play_id|asr|timing_window|state_transition`; each oracle binds to requirement + evidence source + denominator rules; schema valid.
  - Verify: `python -m pytest tests/platform/test_plan_writer.py -q`
  - Size: M

- [ ] **P4-04 Adversarial multi-model review (M)** — catch false PASS and unrunnable plans.
  - Depends: P4-03, P1-04
  - Files: `src/noahsark/aitest/platform/plan_review.py`, `tests/platform/test_plan_review.py`
  - Acceptance: reviewers cover coverage, oracle falsifiability, device/executability, risk; cross-family enforced or explicit degradation; findings have severity + evidence + proposed fix; blocking findings prevent approval; resolution receipt maps each finding to a change or waiver with actor.
  - Verify: `python -m pytest tests/platform/test_plan_review.py -q`
  - Size: M

- [ ] **P4-05 Deterministic assurance gates (M)** — the model cannot approve itself.
  - Depends: P4-04
  - Files: `src/noahsark/aitest/platform/assurance.py`, `tests/platform/test_assurance.py`
  - Acceptance: 100% requirement↔case↔oracle traceability; every oracle falsifiable and evidence-bound; no hardcoded project values outside config; schema valid; profile compiles; lstest preflight/fixture runs (dry-run only, no device side effects) and passes; readiness true; otherwise blocking report.
  - Verify: `python -m pytest tests/platform/test_assurance.py -q`; `python scripts/probe_assurance.py --fixture wake`
  - Size: M

- [ ] **P4-06 Human approval and plan freeze (M)** — A/B policy enforced.
  - Depends: P4-05
  - Files: `src/noahsark/aitest/platform/plan_approval.py`, `tests/platform/test_plan_approval.py`
  - Acceptance: B-class/high-risk always human; A-class auto only if assurance pass + low risk + explicit policy; approval records actor/time/scope; plan revision frozen with hash; edits after approval create a new revision and invalidate execution.
  - Verify: `python -m pytest tests/platform/test_plan_approval.py -q`
  - Size: M

- [ ] **P4-07 Agent registry and config renderer (M)** — one source of truth for agents.
  - Depends: P0-04
  - Files: `config/agents/registry.yaml`, `src/noahsark/aitest/platform/agent_config.py`, `scripts/render_agents.py`, `tests/platform/test_agent_config.py`
  - Acceptance: roles (lead, planner, case_writer, script_implementer, reviewer, oracle, device, knowledge_curator); each declares model policy, OpenSpec context/commands, write scope, tools, skills, review requirement; renders `.opencode/agent/<role>.md` + `opencode.json`; CI drift check; invalid registry fails closed.
  - Verify: `python -m pytest tests/platform/test_agent_config.py -q`; `python scripts/render_agents.py --check`
  - Size: M

- [ ] **P4-08 OpenSpec requirement workflow and write guard (M)** — generated files must be reviewed.
  - Depends: P4-07, P0-07
  - Files: `src/noahsark/aitest/platform/openspec_flow.py`, `review_receipts.py`, extend `write_guard.py`, tests
  - Acceptance: requirement → change scaffold with proposal/specs/tasks; `openspec validate --strict` before approval; apply requires tasks file + review receipt; protected paths (`openspec/**`, `config/agents/**`, `.aitest/**`, `projects/**`) reject writes without a receipt; reviewer family ≠ author family; human sign-off for protected paths.
  - Verify: `python -m pytest tests/platform/test_openspec_flow.py tests/platform/test_review_receipts.py -q`
  - Size: M

- [ ] **P4-09 Review rubric and templates (S)** — make review consistent.
  - Depends: P4-04
  - Files: `docs/v2/review/{PLAN-REVIEW.md,CASE-REVIEW.md,SCRIPT-REVIEW.md}`, `templates/plan.v2.json`, `templates/case.v2.json`
  - Acceptance: rubric items map to assurance gates; severity definitions; required evidence per item; template validates against schemas.
  - Verify: `python scripts/validate_templates.py`
  - Size: S

- [ ] **P4-10 Plan quality metrics and evaluation hook (M)** — prove the method improves.
  - Depends: P4-05, P4-09
  - Files: `src/noahsark/aitest/platform/plan_metrics.py`, `tests/platform/test_plan_metrics.py`
  - Acceptance: tracks traceability %, oracle coverage, review blocking findings, false-PASS escapes, human edit rate, retrieval reuse rate; frozen eval set with labels; metrics exposed via API for the UI.
  - Verify: `python -m pytest tests/platform/test_plan_metrics.py -q`
  - Size: M

- [ ] **P4-11 Lightweight discussion plugin (M)** — make roundtable a callable OMO plugin, not a web app.
  - Depends: P4-07, P1-02
  - Files: `src/noahsark/aitest/platform/discussion.py`, `config/agents/discussion.yaml`, `tests/platform/test_discussion.py`
  - Acceptance: `discuss(topic, roles, models, max_rounds)` returns consensus / disagreements / risks / actions with citations; reuses role packs, agenda, model routing and meeting memory from the AI Collaboration Hub design; no rooms, WebSocket or FastAPI/Vue UI; multi-family panel and `PANEL_DEGRADED` event; real model calls.
  - Verify: `python -m pytest tests/platform/test_discussion.py -q`; invoke `discuss` with 2 roles on a sample question and assert structured output + model usage records.
  - Size: M

- [ ] **P4-12 Test correctness validation (placeholder, details TBD)** — reserve the “test-the-test” step: prove the test itself is valid (oracle independence, known-good/known-bad controls, mutation detection, false-PASS checks).
  - Depends: P4-05, P5-03
  - Files: TBD after overall solution direction is confirmed
  - Acceptance: TBD after direction sign-off; do not invent criteria now
  - Verify: TBD
  - Size: TBD

> Deferred decision: the exact C8 “test validity” gate semantics are intentionally not defined yet. They will be finalized after the overall platform solution is landed and the direction is confirmed.

- [ ] **P4-13 Senior test engineer role charter and scorecard (S)** — encode the role as policy, not prompt folklore.
  - Depends: P4-07, P4-09
  - Files: `docs/v2/AI-SENIOR-TEST-ENGINEER.md`, `config/agents/roles.yaml`, `tests/platform/test_role_policy.py`
  - Acceptance: 12 role principles + scorecard; role registry covers planner / test designer / script implementer / verifier / knowledge curator; review rubric references the principles; no agent can self-approve the final verdict.
  - Verify: `python -m pytest tests/platform/test_role_policy.py -q`; schema-check `config/agents/roles.yaml`; review one sample plan against the rubric.
  - Size: S

---

## 11. Phase 5 — Completion Contract and Verdict Integration

- [ ] **P5-01 Completion report and terminal guard (M)** — make false completion impossible.
  - Depends: P0-03, P0-04, P4-06
  - Files: `src/noahsark/aitest/platform/completion.py`, migration `0002_completion_guard.py`, tests
  - Acceptance: `evaluate(task)` returns C1–C7 with evidence refs and report hash; DB trigger aborts terminal write without eligible report; workflow transition calls the gate; direct SQL update test fails; watchdog detects and emits invariant violation.
  - Verify: `python -m pytest tests/platform/test_completion.py tests/platform/test_completion_guard.py -q`
  - Size: M

- [ ] **P5-02 Evidence requirement registry (M)** — know what "enough evidence" means per case.
  - Depends: P5-01
  - Files: `src/noahsark/aitest/platform/evidence_requirements.py`, `tests/platform/test_evidence_requirements.py`
  - Acceptance: case type → required artifacts (serial log min lines/markers, audio file + hash, `tool.log`, `results.csv`, `cases.csv`, optional screenshots); empty capture invalid; denominator rules per test item; missing evidence blocks C5 with a specific list.
  - Verify: `python -m pytest tests/platform/test_evidence_requirements.py -q`
  - Size: M

- [ ] **P5-03 Real-run proof and receipt verification (M)** — reject mock/dry-run completion.
  - Depends: P5-01, P0-07
  - Files: `src/noahsark/aitest/platform/executor_receipt.py`, `tests/platform/test_executor_receipt.py`
  - Acceptance: receipt includes node, lease, serial/audio endpoint identities, runner exit, artifact manifest hash, `run_mode`; signature verified with node key; `dry_run|simulated|recorded|replay` fail C2; expired/mismatched lease fails; duplicate receipt rejected.
  - Verify: `python -m pytest tests/platform/test_executor_receipt.py -q`
  - Size: M

- [ ] **P5-04 Independent verdict recompute and divergence (M)** — do not trust runner PASS.
  - Depends: P5-01, P5-02
  - Files: `src/noahsark/aitest/platform/verdict_gate.py`, `tests/platform/test_verdict_gate.py`
  - Acceptance: recomputes machine verdict from raw artifacts + pinned oracle; compares runner verdict; divergence blocks PASS and emits `VERDICT_DIVERGENCE`; human/business dimensions follow policy; FAIL requires root-cause class 13/14; machine verdict immutable after human override.
  - Verify: `python -m pytest tests/platform/test_verdict_gate.py -q`
  - Size: M

- [ ] **P5-05 Archive and knowledge write-back gate (M)** — every terminal task teaches the platform.
  - Depends: P5-01, P3-04, P3-05
  - Files: `src/noahsark/aitest/platform/archive_gate.py`, `tests/platform/test_archive_gate.py`
  - Acceptance: archive is idempotent; creates playbook + failure candidates; `no_reusable_knowledge` requires reason + actor; partial failures resume from durable checkpoint; terminal state only after archive receipt.
  - Verify: `python -m pytest tests/platform/test_archive_gate.py -q`
  - Size: M

- [ ] **P5-06 Completion API, UI data and invariant tests (M)** — expose and police the contract.
  - Depends: P5-03, P5-04, P5-05
  - Files: `src/noahsark/aitest/platform/api_completion.py`, `tests/platform/test_api_completion.py`, `tests/platform/test_completion_invariants.py`
  - Acceptance: `GET /api/aitest/v2/tasks/<id>/completion` returns gates, evidence, report hash, blockers; no secrets; invariant tests cover PASS-without-evidence, FAIL-without-real-run, terminal-without-archive, duplicate completion.
  - Verify: `python -m pytest tests/platform/test_api_completion.py tests/platform/test_completion_invariants.py -q`
  - Size: M

- [ ] **P5-07 Reproducibility manifest in delivery (S)** — one hash to reproduce the run.
  - Depends: P1-07, P5-03
  - Files: `src/noahsark/aitest/platform/repro_manifest.py`, tests
  - Acceptance: includes toolchain lock hash, lstest pin, profile/case/oracle hashes, model binding ids, env fingerprint, node image/tool versions; stable ordering; hash changes on any input change.
  - Verify: `python -m pytest tests/platform/test_repro_manifest.py -q`
  - Size: S

---

## 12. Phase 6 — Human Takeover and Session Attach

- [ ] **P6-01 Executor session registry (M)** — persist the native CLI session, not process memory.
  - Depends: P0-03, P0-04
  - Files: `src/noahsark/aitest/platform/session_registry.py`, `tests/platform/test_session_registry.py`
  - Acceptance: records cli kind/version, model binding, native session id/project, state, resume cursor, last seen, attach endpoint; survives restart; interrupted sessions are resumable; no credentials stored.
  - Verify: `python -m pytest tests/platform/test_session_registry.py -q`
  - Size: M

- [ ] **P6-02 Launcher handshake and CLI attach (M)** — attach to the session that started the task.
  - Depends: P6-01, P2-05
  - Files: `scripts/ark_task.py` (`run`, `attach`, `say`, `release`), `tests/platform/test_cli_attach.py`
  - Acceptance: launcher writes `var/run/attach/<task_id>.json` with session key/endpoint/pid and cleans up; `attach` replays history then live; `say` injects a turn; `release` returns control; dead launcher falls back to server-side resume by native session id.
  - Verify: `python -m pytest tests/platform/test_cli_attach.py -q`; manual two-terminal probe recorded
  - Size: M

- [ ] **P6-03 Takeover lease, fencing and safe pause (M)** — one controller, no mid-action corruption.
  - Depends: P6-01
  - Files: `src/noahsark/aitest/platform/takeover.py`, `tests/platform/test_takeover.py`
  - Acceptance: `observe` unlimited readonly; `interactive` exclusive via epoch CAS; agent pauses at next turn boundary and enters `WAITING_HUMAN`; device action in progress is never paused; idle timeout auto-releases; all actions audited; stale epoch rejected.
  - Verify: `python -m pytest tests/platform/test_takeover.py -q`
  - Size: M

- [ ] **P6-04 History replay and attach WebSocket (M)** — see what happened before joining.
  - Depends: P6-03
  - Files: `src/noahsark/aitest/platform/takeover_stream.py`, `tests/platform/test_takeover_stream.py`
  - Acceptance: merges kernel messages + native session messages in order; dedupes by message id; `WS /ws/aitest/takeover/<id>` streams backlog then live; reconnect resumes from cursor; no secret/tool-argument leakage.
  - Verify: `python -m pytest tests/platform/test_takeover_stream.py -q`; `python scripts/probe_takeover_ws.py`
  - Size: M

- [ ] **P6-05 Input injection, resume and duplicate-effect guard (M)** — human input must be safe and effective.
  - Depends: P6-04, P5-03
  - Files: `src/noahsark/aitest/platform/takeover_input.py`, `tests/platform/test_takeover_input.py`
  - Acceptance: text routed to the same native session; `interrupt=true` cancels current turn at a safe boundary; resume sends checkpoint + last N messages; already-confirmed effects have idempotency keys and are not replayed; destructive device commands require confirm; role/owner checks.
  - Verify: `python -m pytest tests/platform/test_takeover_input.py -q`
  - Size: M

- [ ] **P6-06 Takeover APIs and permissions (S)** — stable integration surface.
  - Depends: P6-05
  - Files: `src/noahsark/aitest/platform/api_takeover.py`, `tests/platform/test_api_takeover.py`
  - Acceptance: acquire/release/input/state endpoints; role 2 observe, role 3 interact own task, role 4 any; 409 on lease conflict; audit event per action; no takeover of terminal tasks.
  - Verify: `python -m pytest tests/platform/test_api_takeover.py -q`
  - Size: S

---

## 13. Phase 7 — UI Fully Matches the Platform

- [ ] **P7-00 NoahsArk UI design system and page specs (M)** — design before implementation.
  - Depends: P4-13, P0-04
  - Files: `docs/v2/UI-DESIGN.md`, `design/wireframes/*.md`, `assets/brand/ark-logo.svg`, `design/design-tokens.json`
  - Acceptance: brand (NoahsArk + ark logo); sitemap; page-by-page specs for Overview / Tasks / Task Detail / Knowledge / Nodes / Models / Versions / Push / Agents / Takeover / System; loading/empty/error/blocked/stale state matrix; progress/gate/card/table/terminal components; desktop/tablet/phone; accessibility; interaction notes; user design review approved; no product code.
  - Verify: design checklist + user review; all page specs present; wireframe links resolve; logo/tokens valid.
  - Size: M

- [ ] **P7-01 Shell, navigation, tokens and shared components (M)** — one coherent console.
  - Depends: P0-02, P4-07, P7-00
  - Files: `templates/console/base.html`, `_nav.html`, `components/{voyage_ruler,gate_stamp,model_badge,status,evidence_list,empty_state}.html`, `static/aitest/{tokens.css,app.js,api.js,events.js}`
  - Acceptance: nav = Overview / Tasks / Knowledge / Nodes / Models / Push / Think / Roundtable / Agents / System; active state; breadcrumb; role-aware visibility; design tokens match the brief; no CDN dependencies; shared API client attaches CSRF + handles 401/403.
  - Verify: `python -m pytest tests/platform/test_ui_shell.py -q`; `python scripts/ui_snapshot.py --page /aitest`
  - Size: M

- [ ] **P7-02 Overview page (M)** — answer "is the platform healthy?" in one screen.
  - Depends: P7-01, P5-06, P2-04, P1-05
  - Files: `templates/console/overview.html`, `static/aitest/overview.js`, `tests/platform/test_ui_overview.py`
  - Acceptance: cards for running/blocked/completed tasks, pending humans, gate failures, push dead letters, toolchain drift, model health; progress bars; quick links; SSE updates; empty/error states; no secret fields.
  - Verify: `python -m pytest tests/platform/test_ui_overview.py -q`; snapshot
  - Size: M

- [ ] **P7-03 Tasks list and detail (M)** — the primary workspace.
  - Depends: P7-01, P5-06, P3-03, P2-05
  - Files: `tasks.html`, `task_detail.html`, `static/aitest/{tasks.js,task_detail.js}`, tests
  - Acceptance: list filters project/state/verdict/device/model; cards show requirement, project, device, progress, verdict, evidence count, model binding; detail tabs Summary / Plan & Cases / Execute / Evidence / Verdict & Gates / Knowledge / Similar / Takeover / Logs; buttons approve/start/pause/stop/takeover/export delivery with permission + confirm; progress bar reflects stages + gates; evidence links download via API.
  - Verify: `python -m pytest tests/platform/test_ui_tasks.py -q`; browser probe on a real task
  - Size: M

- [ ] **P7-04 Similar tasks and playbook panels (S)** — make reuse visible.
  - Depends: P7-03, P3-03
  - Files: `task_detail.html` section, `static/aitest/similar.js`, tests
  - Acceptance: shows top-5 with why-matched, reusable blocks, differences, warnings, citations; "apply block to plan" creates a draft revision (audited); playbook link after completion.
  - Verify: `python -m pytest tests/platform/test_ui_similar.py -q`
  - Size: S

- [ ] **P7-05 Models page (M)** — switch at three scopes without restart.
  - Depends: P1-05, P7-01
  - Files: `models.html`, `static/aitest/models.js`, tests
  - Acceptance: global default card with validate/switch; agent override table; task override table; effective binding preview with precedence source; candidate health/capabilities; test call button; audit list; clear "applies next turn" note; errors shown inline.
  - Verify: `python -m pytest tests/platform/test_ui_models.py -q`; live switch probe
  - Size: M

- [ ] **P7-06 Toolchain/version panel (M)** — know exactly what is installed.
  - Depends: P0-04, P1-01, P7-01
  - Files: `system_toolchain.html`, `static/aitest/toolchain.js`, tests
  - Acceptance: matrix of opencode/OMO/plugins/skills with installed vs locked vs compatible; drift banner; last smoke runs; "run tier-1 smoke" (admin); upgrade history; lock file download; no binary contents.
  - Verify: `python -m pytest tests/platform/test_ui_toolchain.py -q`; snapshot with simulated drift
  - Size: M

- [ ] **P7-07 Takeover terminal (M)** — attach, replay, interact.
  - Depends: P6-06, P7-03
  - Files: `takeover.html`, `static/aitest/{takeover.js,xterm.bundle.js,xterm.css}`, tests
  - Acceptance: xterm renders history + live; status banner (observe/interactive/paused); input box + interrupt; release; reconnect; audit line "controlled by"; local bundle works offline; read-only mode disables input.
  - Verify: `python -m pytest tests/platform/test_ui_takeover.py -q`; `python scripts/ui_takeover_e2e.py`
  - Size: M

- [ ] **P7-08 Knowledge pages (M)** — search, inspect, govern.
  - Depends: P3-08, P7-01
  - Files: `knowledge.html`, `knowledge_detail.html`, `static/aitest/knowledge.js`, tests
  - Acceptance: search with kind/scope/status filters; detail shows provenance, evidence, counterexamples, conflicts, revisions; promote/retire with review receipt + confirm; stale/pin badges; no secrets.
  - Verify: `python -m pytest tests/platform/test_ui_knowledge.py -q`
  - Size: M

- [ ] **P7-09 Nodes and devices page (M)** — the device layer must be visible.
  - Depends: P0-02, P7-01
  - Files: `nodes.html`, `node_detail.html`, `static/aitest/nodes.js`, tests
  - Acceptance: node cards (online/stale/running, OS, CLI versions, last heartbeat); device cards (model, firmware, serial, audio endpoint, project, lease holder); lease state; "ask agent" node task window (scoped, audited); empty/offline states.
  - Verify: `python -m pytest tests/platform/test_ui_nodes.py -q`; snapshot with fake lease
  - Size: M

- [ ] **P7-10 Push subscriptions and delivery log (M)** — operate active reporting.
  - Depends: P2-04, P7-01
  - Files: `push.html`, `static/aitest/push.js`, tests
  - Acceptance: list/create/edit/disable subscriptions; channel-specific forms; test send; delivery timeline with attempts/status/last error; dead letters with retry; filter by event type; no secret display.
  - Verify: `python -m pytest tests/platform/test_ui_push.py -q`
  - Size: M

- [ ] **P7-11 SSE client hardening (S)** — never show stale data silently.
  - Depends: P7-01
  - Files: `static/aitest/events.js`, tests
  - Acceptance: `Last-Event-ID` reconnect; dedupe by event id; 5s polling fallback on disconnect; visible "live/degraded" indicator; no duplicate DOM rows; unload cleanup.
  - Verify: `python -m pytest tests/platform/test_ui_events.py -q`; `python scripts/probe_sse_fallback.py`
  - Size: S

- [ ] **P7-12 Accessibility, responsive and visual QA (M)** — usable on desktop, tablet and phone.
  - Depends: P7-02..P7-10
  - Files: `static/aitest/responsive.css`, `tests/platform/test_ui_a11y.py`, `docs/v2/UI-QA.md`, snapshots
  - Acceptance: keyboard nav, visible focus, semantic tables/forms, ARIA labels; <768px cards and horizontal timeline; verdict/evidence/action never hidden; contrast check; empty/loading/error states for every page; screenshots at 1440/1024/390 widths.
  - Verify: `python -m pytest tests/platform/test_ui_a11y.py -q`; `python scripts/ui_visual_check.py`
  - Size: M

- [ ] **P7-13 UI contract and security tests (S)** — pages cannot lie or leak.
  - Depends: P7-02..P7-12
  - Files: `tests/platform/test_ui_contracts.py`
  - Acceptance: every route returns 200/401/403 as specified; no secret/token/provider key in HTML; every write button maps to a command facade call; response snapshots stable; route inventory matches nav.
  - Verify: `python -m pytest tests/platform/test_ui_contracts.py -q`
  - Size: S

---

## 14. Phase 8 — Toolchain Upgrade Drill, Real-Run E2E and Final Verification

- [ ] **P8-01 Toolchain snapshot, compat matrix and drift detector (M)** — lock what exists today.
  - Depends: P1-01, P0-04
  - Files: `config/toolchain.lock.json`, `config/toolchain.compat.json`, `src/noahsark/aitest/platform/toolchain.py`, `scripts/toolchain_snapshot.py`, `scripts/toolchain_verify.py`, tests
  - Acceptance: snapshots opencode version/commit/binary hash, OMO version/git sha/entry hash/tool-contract hash, every self-developed plugin, every platform-used skill (`SKILL.md` hash + source commit), Python/PostgreSQL, lstest pin, platform commit; verify detects drift and fails closed for real execution; JSON schema valid; no secrets.
  - Verify: `python scripts/toolchain_snapshot.py --check`; `python -m pytest tests/platform/test_toolchain.py -q`
  - Size: M

- [ ] **P8-02 Compatibility smoke tiers and upgrade playbook (M)** — upgrades become routine.
  - Depends: P8-01
  - Files: `scripts/toolchain_smoke.py`, `docs/v2/UPGRADE-PLAYBOOK.md`, tests
  - Acceptance: T1 startup/read-only (<60s), T2 plugin/tool contracts + event/push/retrieval offline, T3 model + device preflight + one real task; each run recorded in `toolchain_smoke_runs` with component versions and result; playbook: snapshot → staging → T1/T2 → shadow T3 → canary → approve → rollback; version pin update is a separate reviewed commit.
  - Verify: `python scripts/toolchain_smoke.py --tier 1 --json`; `python -m pytest tests/platform/test_toolchain_smoke.py -q`
  - Size: M

- [ ] **P8-03 Real-device E2E harness (M)** — test on the actual surface.
  - Depends: P5-06, P6-06, P7-13
  - Files: `tests/e2e/conftest.py`, `tests/e2e/test_real_task.py`, `scripts/e2e_real_task.py`, `docs/v2/REAL-E2E.md`
  - Acceptance: selects win009 TCL000 or TCL003 by readiness; requires `ARK_REAL=1`; verifies serial, audio, lease and firmware; captures screenshots + HTTP evidence; refuses to run with mock adapters; records evidence under `evidence/v2/<task_id>/`.
  - Verify: `python -m pytest tests/e2e -q -m real --device TCL000`
  - Size: M

- [ ] **P8-04 Real PASS scenario with push, completion, KB and reuse (L)** — the core proof.
  - Depends: P8-03
  - Files: `tests/e2e/test_real_pass_loop.py`, `scripts/e2e_pass_loop.py`
  - Acceptance: create task → retrieval (may be empty) → approved plan → preflight 10 → real execute ≥20 valid samples → independent verify → completion report all gates pass → push delivered to file + webhook sink → playbook + KB entries written → second similar task retrieves the first playbook and prefills reusable blocks. No manual DB edits, no temporary scripts, no mock.
  - Verify: `python scripts/e2e_pass_loop.py --device TCL000 --json`; inspect `evidence/v2/<task>/completion.json`
  - Size: L

- [ ] **P8-05 Real FAIL/BLOCKED/offline scenarios (M)** — no false completion in the other direction.
  - Depends: P8-04
  - Files: `tests/e2e/test_real_fail_loop.py`, `tests/e2e/test_real_blocked_loop.py`
  - Acceptance: real FAIL (oracle contradiction) is accepted only with root cause 13/14 and failure KB entry; device offline → `BLOCKED_HUMAN`/`INFRA_ERROR`, no `task.completed`; STOPPED preserves evidence and never becomes PASS; empty capture never PASSes.
  - Verify: `python -m pytest tests/e2e/test_real_fail_loop.py tests/e2e/test_real_blocked_loop.py -q -m real`
  - Size: M

- [ ] **P8-06 Takeover + model switch mid-task real scenario (M)** — prove the interactive path.
  - Depends: P8-04, P6-05
  - Files: `tests/e2e/test_real_takeover.py`
  - Acceptance: start real task; switch task model; next turn uses new binding (usage table + delivery); take over interactively; inject instruction; release; task resumes and completes; duplicate device action count is zero; audit complete.
  - Verify: `python -m pytest tests/e2e/test_real_takeover.py -q -m real`
  - Size: M

- [ ] **P8-07 Upgrade drill with simulated opencode/OMO bump (M)** — prove the compat story.
  - Depends: P8-02
  - Files: `scripts/drill_upgrade.py`, `tests/e2e/test_upgrade_drill.py`, `evidence/v2/upgrade-drill/`
  - Acceptance: simulate version drift in a staging copy; T1/T2 fail or pass as expected; platform degrades and blocks real execution; restore lock; smoke passes; rollback documented and executed; no production task affected.
  - Verify: `python scripts/drill_upgrade.py --simulate --json`
  - Size: M

- [ ] **P8-08 Observability, alerts and runbooks (M)** — operate it after delivery.
  - Depends: P5-06, P2-06, P8-02
  - Files: `src/noahsark/aitest/platform/observability.py`, `docs/v2/RUNBOOK.md`, tests
  - Acceptance: metrics for stuck tasks, gate failures, push dead letters, drift, model blocks, takeover conflicts, retrieval latency; alert events use the push bus; runbook covers task stuck, device lost, provider outage, completion violation, webhook failure, rollback.
  - Verify: `python -m pytest tests/platform/test_observability.py -q`
  - Size: M

- [ ] **P8-09 Documentation and operator guide (S)** — deliverable, not afterthought.
  - Depends: P8-04..P8-08
  - Files: `docs/v2/{USER-GUIDE.md,API.md,ARCHITECTURE.md,DELIVERY.md}`, `README.md` updates
  - Acceptance: task lifecycle, model switch, push setup, takeover, knowledge governance, upgrade, troubleshooting; every endpoint documented; screenshots current; links valid.
  - Verify: `python scripts/check_docs_links.py docs/v2`
  - Size: S

- [ ] **P8-10 Final verification wave (M)** — independent reviewers, binary sign-off.
  - Depends: all previous
  - Files: `.omo/evidence/ai-test-platform-v2/FINAL-SIGNOFF.md`
  - Acceptance: see §17; all findings resolved or explicitly waived with evidence; no open P0/P1 defect; phase gate log complete; flags enabled only per sign-off.
  - Verify: `python scripts/verify_platform_gate.py --final`
  - Size: M

---

## 15. TDD and Test Strategy

**Test pyramid**

| Layer | Location | Rules |
|---|---|---|
| Contract/unit | `tests/platform/test_*.py` | Pure functions, schema validation, fake clock/DB; fast; every branch |
| Integration | `tests/platform/test_api_*.py`, `test_ui_*.py` | Flask test client, PostgreSQL test database（2026-10-28 修正：原 sqlite temp DB 已取代）, fake provider/node, RBAC roles |
| Golden/fixture | `tests/platform/fixtures/` | Retrieval top-k, root-cause classification, plan schema, UI snapshots |
| Real E2E | `tests/e2e/` | Real device, real serial/audio, real opencode; `-m real`; never in default CI |
| Upgrade drill | `tests/e2e/test_upgrade_drill.py` | Staging copy + simulated versions |

**Rules**
- The failing test is committed before the implementation in the same work unit (two commits or one commit with test-first ordering documented in the commit body; prefer two commits: `test(...)` then `feat(...)`).
- No test may mint a completion report without real-run fixtures; completion tests use fake receipts for logic only and are labelled `contract`.
- Property tests for model precedence, retrieval ranking stability and takeover epoch CAS.
- Mutation-style checks for the completion gate: remove each gate, assert the gate blocks.
- UI tests assert content and permissions, not only status codes.
- Real E2E failures produce an evidence bundle and are never retried into a pass.

**Commands (canonical)**
```
python -m pytest tests/platform -q
python -m pytest tests -q
python -m pytest tests/e2e -q -m real --device TCL000
python scripts/verify_platform_gate.py --wave N
python scripts/toolchain_smoke.py --tier 1
ruff check src tests scripts
mypy src/noahsark/aitest/platform
python scripts/check_server_growth.py --max-lines 20
python scripts/render_agents.py --check
openspec validate ai-test-platform-v2 --strict
```
If `ruff`/`mypy` are not yet project dependencies, add them in P0-06 with pinned versions in the toolchain lock; do not introduce a second formatter.

---

## 16. Atomic Commit Strategy

**Branch:** `feat/ai-test-platform-v2` from the current release tag. No direct commits to `main`.

**Commit unit:** one checkbox, usually two commits:
1. `test(aitest-v2): add failing tests for P1-03 hot switch`
2. `feat(aitest-v2): P1-03 hot model switch with audit`

**Rules**
- Conventional Commits; scope `aitest-v2`; body includes task id, acceptance line and verification command output summary.
- Never commit with a failing test suite; never skip hooks; never force-push shared branches.
- Migrations are separate commits (`feat(db): 0001 platform core`) and always include a rollback test.
- Contract/schema changes are separate commits and require a version bump if breaking.
- Feature flags stay off in every commit until P8-10; enabling is its own reviewed commit with evidence.
- No secrets, credentials, raw audio, firmware or large evidence files. Commit manifests and small text logs only; add `.gitignore` entries in P0-02.
- Rebase locally to keep a linear history per track; merge tracks into the feature branch after each wave gate.
- Tag each wave: `v2-phase0` … `v2-phase8`; final `v2.0.0-rc1` only after sign-off.
- Rollback: each wave has a revert plan; DB migrations include `down` or a documented restore-from-backup procedure; no destructive migration without a tested backup.

**Suggested order (dependency-safe):**
`P0-01 → P0-02 → P0-03 → P0-04 → P0-05/P0-06/P0-07/P0-08 → P1/P2/P3/P4 tracks → P5 → P6 → P7 (page-by-page) → P8-01/P8-02 → P8-03 → P8-04/P8-05 → P8-06/P8-07 → P8-08/P8-09 → P8-10`.

---

## 17. Final Verification Wave

| Gate | Reviewer / surface | Pass condition |
|---|---|---|
| V1 Contracts & units | `python -m pytest tests/platform -q`; ruff; mypy | 100% pass, zero type errors in new package |
| V2 Regression | `python -m pytest tests -q` | No existing test regression; `server.py` growth check passes |
| V3 Real execution | `tests/e2e -m real` on TCL000/TCL003 | PASS, FAIL, BLOCKED, STOPPED scenarios behave per contract |
| V4 Upgrade compatibility | `scripts/drill_upgrade.py --simulate` + tier-1/2 smoke | Drift detected, real execution blocked, rollback verified |
| V5 UI/visual/a11y | `scripts/ui_visual_check.py`, `test_ui_a11y.py`, manual screenshots | All pages usable at 1440/1024/390; no hidden verdict/evidence/action |
| V6 Security | `security-research` / security-review on the v2 diff | No critical/high findings; secrets, HMAC, RBAC, SSRF, path traversal, takeover input reviewed |
| V7 Independent review | momus (plan compliance), oracle (edge cases/architecture), reviewer-agent (diff defects) | Every finding fixed or waived with evidence; no unresolved P0/P1 |
| V8 Delivery audit | `DELIVERY.md` + evidence manifest | Goal, non-goals, each requirement traceable to tasks and evidence; sign-off by owner |

**Binary sign-off rule:** any unresolved P0/P1, any false completion path, any secret leak, or any real-run scenario that cannot be reproduced blocks release. "All tests pass" alone is not a pass.

---

## 18. Traceability: Requirement → Tasks

| # | Requirement | Primary tasks | Proof |
|---|---|---|---|
| 1 | Runtime model switching (global/agent/task, validation/fallback, no restart) | P1-01..P1-07, P7-05, P8-06 | `test_model_policy`, `test_model_switch`, live switch probe, usage table |
| 2 | Version lock + upgrade compatibility smoke | P0-03, P1-01, P7-06, P8-01, P8-02, P8-07 | `toolchain.lock.json`, smoke runs, drill evidence |
| 3 | Active push/reporting to terminal/file/webhook/bus | P2-01..P2-06, P7-10, P8-04 | delivery ledger, CLI watch demo, webhook sink |
| 4 | Similar-task retrieval + persist plan for reuse | P3-02..P3-04, P7-04, P8-04 | retrieval packet, playbook row, second-task reuse |
| 5 | Failure/log/root-cause + all project knowledge, document analysis | P3-01..P3-10, P7-08, P8-05 | failure candidates, KB search, doc-analysis task |
| 6 | Definition of task complete with binary evidence gates | P0-04, P5-01..P5-07, P8-05 | completion report, DB guard test, invariant tests |
| 7 | Task takeover / CLI session attach / history / input | P6-01..P6-06, P7-07, P8-06 | takeover lease test, WS replay, real takeover |
| 8 | UI fully matches platform | P7-01..P7-13, P8-10 | route contract tests, visual QA, screenshots |
| 9 | No fake runs | P5-03, P8-03..P8-05 | executor receipt, real evidence, dry-run rejection |
| 10 | OpenSpec per agent + agent config + requirement/review process | P4-07..P4-09, P0-01 | registry render check, OpenSpec validate, write-guard receipts |
| 11 | Good plans/cases/verdicts from requirements + KB | P3-02, P4-01..P4-10, P5-04 | assurance gate, review findings, quality metrics, E2E |

---

## 19. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Monolith `server.py` keeps growing | Blueprint-only wiring + CI growth check; new code in `platform/` |
| Model switch applied mid-device-action | Apply at turn boundary; interrupt at checkpoint; takeover lease |
| Push floods / duplicate completion notices | Event taxonomy, subscription filters, idempotency key, dedupe, budget |
| Knowledge base polluted by model guesses | Status lifecycle, provenance required, candidate-only write-back, human approval |
| Retrieval injects stale/wrong history | Scope filters, pin/firmware warnings, conflict display, untrusted-evidence wrapper |
| Completion gate becomes a rubber stamp | Binary evidence, DB trigger, invariant watchdog, mutation tests |
| Takeover races / two controllers | Epoch CAS, exclusive interactive, audit, timeout |
| Upgrade breaks plugins silently | Contract snapshots, tiered smoke, fail-closed real execution |
| UI drifts from backend | Route inventory test, contract tests, generated nav, visual QA |
| Real-device time is scarce | P8 harness early; preflight vs execute separation; device lease reuse |
| Two runtimes diverge | One workflow truth; v2 produces commands/contracts, never direct state writes |

---

## 20. Open Questions (only items that need user input)

1. **Canonical repo (resolved):** **NoahsArk** (`https://github.com/zjashanda/NoahsArk`), local workspace `E:\aswxStation\tmpskill\0000\noahsark`. Remaining: confirm the push identity/token owner for the empty repo (SSH 22/443 currently resets; `GITHUB_TOKEN` is present). No product code until solution + UI design are approved.
2. **Push destinations:** provide the webhook URL + shared secret owner, and the preferred terminal notification path (CLI watch is built-in; do you also want desktop `notify-send`?).
3. **Default model policy:** confirm the primary model and at least one fallback family for global default after switch; confirm whether `listenai` quota should hard-block or degrade panels.
4. **Real-device window:** confirm which of TCL000/TCL003 is available for Phase 8, the maintenance window, and permission for power cycling/offline simulation.
5. **Retention/privacy:** how long to keep raw audio, serial logs and model transcripts; whether any project data is not allowed into the KB.
6. **Upgrade authority:** who approves opencode/OMO/lstest pin changes, and whether a change freeze applies during acceptance.

Everything else (stack, schema, page structure, gate semantics, commit policy) is decided above and does not need confirmation.

---

## 21. Plan Exit Criteria

The plan is complete when:

- All Phase 0–8 checkboxes are closed with evidence.
- A real task passes all completion gates and a second task reuses its playbook.
- A real FAIL is correctly preserved as FAIL with a failure-KB root cause, and a real offline run is BLOCKED, never PASS.
- A task can be taken over from the CLI/UI, history is replayed, input is accepted, and the task resumes.
- A model switch takes effect on the next turn without restart and is recorded in delivery.
- A simulated opencode/OMO upgrade is detected, smoke-tested, and rolled back with evidence.
- Security and independent reviews have no unresolved critical/high findings.
- `docs/v2/DELIVERY.md` and `.omo/evidence/ai-test-platform-v2/FINAL-SIGNOFF.md` are complete.
