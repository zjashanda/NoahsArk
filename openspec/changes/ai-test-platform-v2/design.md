# Design: AI Test Platform v2

## Context and boundaries

NoahsArk is the canonical state holder and execution gateway. NoahsArk is a new codebase in `https://github.com/zjashanda/NoahsArk`; it does not reuse legacy platform UI, templates, database schema, execution adapters or fake-run paths. The intelligent plane (lead/planner/writers/reviewers) produces typed candidates and effects; the deterministic plane owns workflow, permissions, leases, dispatch, lstest, evidence, verdict, completion and archive. There is one workflow truth, not a second state machine. The design uses a fresh Flask + Jinja2 + vanilla ES modules + SSE + SQLite WAL implementation.

## Decisions D1–D13

| ID | Decision | Consequence |
|---|---|---|
| D1 | New NoahsArk codebase; the legacy platform is a negative reference only. | Fresh UI, execution, schema and adapters; no fake-execution reuse. |
| D2 | Flask + Jinja2 + vanilla ES modules + SSE + SQLite WAL. | No new SPA/build chain; migrations are additive and idempotent. |
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

Every artifact carries `task_id`, `execution_id` where applicable, schema/version, provenance and hash. Terminal states are `PASS | FAIL | BLOCKED_HUMAN | CANCELLED | STOPPED | INFRA_ERROR`; `WAITING_HUMAN` is non-terminal and there is no `DONE`. Gates are C1 approved immutable plan, C2 real execution, C3 complete artifact manifest, C4 independent verdict, C5 evidence sufficiency, C6 knowledge write-back or explicit no-reusable-knowledge reason, and C7 reproducibility. PASS requires C1–C7; FAIL requires C1–C5 and C7, with C6 before archive. DB trigger/watchdog rejects terminal state without an eligible report.

### Model and toolchain

`aitest.model_binding.v1` records binding id, task, role, source, primary/candidates, family/capabilities, catalog and health snapshots, revision, actor and reason. Transient provider failures advance candidates; permanent auth/model/budget failures emit `MODEL_BLOCKED`; panel diversity degradation is explicit. `config/toolchain.lock.json` records opencode, OMO, plugins, skills, Python, SQLite, lstest and platform commit/hash. `compat` maps tested ranges to smoke suites and drift fails closed for real execution.

### Event and push

`aitest.event.v1` has monotonic `seq`, unique event/idempotency keys, type/severity/task/time, payload and redaction metadata. Channels are `sse|terminal|file|webhook`; delivery is at-least-once with consumer dedupe and retry 1s/5s/30s/5m/1h then dead-letter. Webhooks use timestamped HMAC-SHA256 and allowlists. `task.completed` occurs once, only after gates and archive; push failure never changes task state.

### Retrieval, playbook and knowledge

`aitest.retrieval_packet.v1` returns ranked `task_playbook|failure_case|methodology|project_fact|script_fix` hits with status, applicability, differences, warnings and citations. Statuses are candidate/corroborated/approved/disputed/stale/retracted. FTS5 plus tags and project/device/pin filters are deterministic; retrieval is untrusted context. A terminal task writes an idempotent playbook containing requirement signature, plan/case/oracle hashes, prerequisites, evidence requirements, outcome, failure modes and reuse tags. Raw logs are retained by pointer/summary and secret/PII scans reject unsafe ingestion.

### Session/takeover

Session records contain CLI kind/version, native session/project id, model binding, state, resume cursor, timestamps and attach endpoint, never credentials. Takeover targets `lead|workunit|node`, modes `observe|interactive`, uses monotonic `lease_epoch` CAS, pauses only at a turn boundary (never mid-device action), replays history, injects input through the native session, rejects duplicate effect keys, and auto-releases after 30 minutes idle.

### Agent/OpenSpec and UI

`aitest.agent_registry.v1` is `config/agents/registry.yaml`; roles declare model policy, OpenSpec context/commands, write scope, tools, skills and review requirement. It renders `.opencode/agent/*.md`, `opencode.json` and context-pack docs; drift fails CI. The UI is a read-only projection over command APIs, with tasks/detail, knowledge, nodes/devices, models, versions, push, takeover and progress. SSE uses idempotent event cursors and falls back to polling; credentials and reasoning are never shown.

## Migration and rollback

Use an additive idempotent migration runner with WAL, foreign keys and busy timeout. Back up before migration; legacy tables and routes remain. Enable `NOAHSARK_V2_ENABLED` and per-capability flags only after wave gates and sign-off. Rollback disables flags, stops new v2 writes, preserves evidence/events, restores from backup only when necessary, and leaves legacy execution untouched. Toolchain drift or failed compatibility smoke blocks real execution until acknowledged. No product code or database is changed by this specification change.

## Security

Central redaction covers authorization, cookies, tokens and keys. RBAC and owner scoping apply to reads/writes; takeover actions and protected writes are audited. Webhooks require HTTPS, timestamp/HMAC validation and an SSRF allowlist; secrets remain in the provider credential broker and only `credential_ref` is persisted. KB ingestion scans secrets/PII and stores summaries/pointers rather than raw sensitive evidence. Generated files under protected paths require a review receipt and reviewer-family separation.

## Verification strategy

Phase 0 freezes schemas and runs migration/security/event gates. Later waves prove model switching, push delivery, retrieval/reuse, plan assurance, completion invariants, takeover, UI accessibility and real-device E2E. Final V1–V8 sign-off is binary: unresolved P0/P1, false completion, secret leak or non-reproducible real run blocks release.
