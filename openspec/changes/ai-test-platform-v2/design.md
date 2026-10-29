# Design: AI Test Platform v2

## 规范同步说明（2026-10-28，P0-03）

> 本设计以下旧口径已按已批准决策修正。最高事实源为 `.omo/drafts` 已审核正文与 [NoahsArk 平台交付总计划](../../../../.omo/plans/noahsark-platform-delivery.md)；逐项冲突、精确修改与验证见 [openspec 与 docs/v2 规范同步记录](../../../../docs/delivery/openspec-v2-sync.md)。
>
> - **PostgreSQL 是唯一正式数据库。** SQLite/SQLite WAL 已取代。
> - **五轴判定 + 分离事实**取代单一终态；旧终态名只作历史别名。
> - **离线续跑、占用保留、STOP-first 重连、释放/证据/判定分离、`cleanup_receipt` 边界**写入 “Execution lifecycle, offline continuation and release”。
> - **C1–C7 与 81 项**只作历史门禁/任务账本，映射见下文与 `tasks.md`。

## Context and boundaries

NoahsArk is the canonical state holder and execution gateway. NoahsArk is a new codebase in `https://github.com/zjashanda/NoahsArk`; it does not reuse legacy platform UI, templates, database schema, execution adapters or fake-run paths. The intelligent plane (lead/planner/writers/reviewers) produces typed candidates and effects; the deterministic plane owns workflow, permissions, leases, dispatch, lstest, evidence, verdict, completion and archive. There is one workflow truth, not a second state machine. The design uses a fresh Flask + Jinja2 + vanilla ES modules + SSE + **PostgreSQL** implementation (历史/已取代 2026-10-28：原文 SQLite WAL).

## Decisions D1–D13

| ID | Decision | Consequence |
|---|---|---|
| D1 | New NoahsArk codebase; the legacy platform is a negative reference only. | Fresh UI, execution, schema and adapters; no fake-execution reuse. |
| D2 | Flask + Jinja2 + vanilla ES modules + SSE + **PostgreSQL**（历史/已取代 2026-10-28：原文 SQLite WAL）. | No new SPA/build chain; migrations are additive and idempotent. |
| D3 | Two planes, one truth. | Agents propose; command facade alone mutates irreversible facts. |
| D4 | Model binding is a versioned first-class object. | Resolve task→agent→global→compiled fallback and snapshot every run. |
| D5 | Completion is a gate object, not a status string. | Terminal writes require a hashed eligible report. |
| D6 | Event-first integration. | Append-only monotonic events feed UI, push, CLI and audit. |
| D7 | Knowledge is evidence-scoped and status-gated. | Provenance, applicability, conflicts and counterexamples are mandatory. |
| D8 | Takeover is a fenced executor-session lease, not a raw shell. | Safe pause at turn boundary, replay, input and CAS fencing. |
| D9 | OpenSpec is the change boundary; agent config is generated. | Registry is source of truth; drift and unreviewed writes fail closed. |
| D10 | Toolchain compatibility is machine-verified. | Lock + compat matrix + smoke tiers gate real execution. |
| D11 | Real-run proof is cryptographically attributable. | Signed node receipt, lease and artifact manifest are required. |
| D12 | Feature flags default off and fail closed. | Unknown/disabled v2 capability cannot silently fall back to completion. |
| D13 | Security and secrets are first-class. | Broker references only, HMAC webhooks, RBAC, redaction, SSRF and audit. |

## Frozen contracts

### Data and completion

Every artifact carries `task_id`, `execution_id` where applicable, schema/version, provenance and hash. The current verdict model is **five axes plus separated facts**: `execution_status` (`NOT_STARTED/RUNNING/COMPLETED/ABORTED/SKIPPED`), `validity_status` (`VALID/INVALID/BLOCKED/UNKNOWN`), `business_verdict` (`PASS/FAIL/EXPECTED/WARN/NEEDS_REVIEW/NOT_EVALUATED`), `evidence_status` (`COMPLETE/INCOMPLETE/CONFLICTED/UNVERIFIED`), and `verification_status` (`PASS/FAIL/NOT_RUN`). Device occupancy (`OCCUPIED/RELEASING/RELEASED/QUARANTINED`) and communication (`ONLINE/OFFLINE/STALE`) are separate facts and MUST NOT be collapsed into one status. Formal PASS requires `execution_status=COMPLETED`, `validity_status=VALID`, `evidence_status=COMPLETE`, `business_verdict=PASS` and `verification_status=PASS`; a `RUNNING` or `NOT_STARTED` execution cannot be a formal PASS.

The legacy terminal set `PASS | FAIL | BLOCKED_HUMAN | CANCELLED | STOPPED | INFRA_ERROR` is retained only as a report-compatibility alias (**历史/已取代 2026-10-28**); `WAITING_HUMAN` is non-terminal and there is no `DONE`. Legacy gates remain for traceability: C1 approved immutable plan, C2 real execution, C3 complete artifact manifest, C4 independent verdict, C5 evidence sufficiency, C6 knowledge write-back or explicit no-reusable-knowledge reason, and C7 reproducibility. They map to the five axes as follows.

| Legacy gate | Primary five-axis / separated fact |
|---|---|
| C1 方案 | `validity_status` approval boundary |
| C2 真实执行 | `execution_status=COMPLETED`, `run_mode=real`, device occupancy |
| C3 产物清单 | `evidence_status` |
| C4 独立判定 | `verification_status` |
| C5 证据充分 | `evidence_status` |
| C6 知识回写 | archive prerequisite; does not change the five-axis verdict |
| C7 可复现 | toolchain/environment fact; does not replace the five axes |

### Execution lifecycle, offline continuation and release

Execution completion, device release, evidence completeness and final verdict are separate objects. Once a frozen run has started, communication loss, heartbeat expiry or lease expiry MUST NOT stop it: it continues offline, Linux marks communication `OFFLINE/STALE` while the device remains `OCCUPIED`, and the platform MUST NOT re-dispatch, replay or re-sample. On reconnect, the node processes pending STOP first, then uploads, dedupes and reconciles; stale epoch/lease/controller messages cannot change the current run.

Device release requires confirmed local stop, safe cleanup and occupancy reconciliation; it does not wait for GB-scale log archive or the final verdict. A missing `cleanup_receipt` only blocks device-release confirmation and keeps the device `OCCUPIED`/`QUARANTINED`; it does **not** by itself make the whole evidence chain incomplete or force a business FAIL. Execution end, device release, evidence status and final verdict MUST be recorded independently.

### Model and toolchain

`aitest.model_binding.v1` records binding id, task, role, source, primary/candidates, family/capabilities, catalog and health snapshots, revision, actor and reason. Transient provider failures advance candidates; permanent auth/model/budget failures emit `MODEL_BLOCKED`; panel diversity degradation is explicit. `config/toolchain.lock.json` records opencode, OMO, plugins, skills, Python, **PostgreSQL** (历史/已取代 2026-10-28: SQLite), lstest and platform commit/hash. `compat` maps tested ranges to smoke suites and drift fails closed for real execution.

### Event and push

`aitest.event.v1` has monotonic `seq`, unique event/idempotency keys, type/severity/task/time, payload and redaction metadata. Channels are `sse|terminal|file|webhook`; delivery is at-least-once with consumer dedupe and retry 1s/5s/30s/5m/1h then dead-letter. Webhooks use timestamped HMAC-SHA256 and allowlists. `task.completed` occurs once, only after gates and archive; push failure never changes task state.

### Retrieval, playbook and knowledge

`aitest.retrieval_packet.v1` returns ranked `task_playbook|failure_case|methodology|project_fact|script_fix` hits with status, applicability, differences, warnings and citations. Statuses are candidate/corroborated/approved/disputed/stale/retracted. FTS5 plus tags and project/device/pin filters are deterministic; retrieval is untrusted context. A terminal task writes an idempotent playbook containing requirement signature, plan/case/oracle hashes, prerequisites, evidence requirements, outcome, failure modes and reuse tags. Raw logs are retained by pointer/summary and secret/PII scans reject unsafe ingestion.

### Session/takeover

Session records contain CLI kind/version, native session/project id, model binding, state, resume cursor, timestamps and attach endpoint, never credentials. Takeover targets `lead|workunit|node`, modes `observe|interactive`, uses monotonic `lease_epoch` CAS, pauses only at a turn boundary (never mid-device action), replays history, injects input through the native session, rejects duplicate effect keys, and auto-releases after 30 minutes idle.

### Agent/OpenSpec and UI

`aitest.agent_registry.v1` is `config/agents/registry.yaml`; roles declare model policy, OpenSpec context/commands, write scope, tools, skills and review requirement. It renders `.opencode/agent/*.md`, `opencode.json` and context-pack docs; drift fails CI. The UI is a read-only projection over command APIs, with tasks/detail, knowledge, nodes/devices, models, versions, push, takeover and progress. SSE uses idempotent event cursors and falls back to polling; credentials and reasoning are never shown.

## Migration and rollback

Use an additive idempotent migration runner with PostgreSQL transactions, constraints and indexes (**历史/已取代 2026-10-28**: 原文 WAL/foreign keys/busy timeout). Back up before migration; legacy tables and routes remain. Enable `NOAHSARK_V2_ENABLED` and per-capability flags only after wave gates and sign-off. Rollback disables flags, stops new v2 writes, preserves evidence/events, restores from backup only when necessary, and leaves legacy execution untouched. Toolchain drift or failed compatibility smoke blocks real execution until acknowledged. No product code or database is changed by this specification change.

## Security

Central redaction covers authorization, cookies, tokens and keys. RBAC and owner scoping apply to reads/writes; takeover actions and protected writes are audited. Webhooks require HTTPS, timestamp/HMAC validation and an SSRF allowlist; secrets remain in the provider credential broker and only `credential_ref` is persisted. KB ingestion scans secrets/PII and stores summaries/pointers rather than raw sensitive evidence. Generated files under protected paths require a review receipt and reviewer-family separation.

## Verification strategy

Phase 0 freezes schemas and runs migration/security/event gates. Later waves prove model switching, push delivery, retrieval/reuse, plan assurance, completion invariants, takeover, UI accessibility and real-device E2E. Final V1–V8 sign-off is binary: unresolved P0/P1, false completion, secret leak or non-reproducible real run blocks release.
