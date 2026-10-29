# Tasks

Each checkbox is copied from the saved plan; dependencies are preserved. Product implementation is out of scope for P0-01.

> **历史/已取代（2026-10-28，P0-03）**：本文件是 2026-10-26 计划的 81 项历史账本，**不是当前施工 WBS**，也不代表当前完整范围。当前执行主线是 [NoahsArk 平台交付总计划](../../../../.omo/plans/noahsark-platform-delivery.md) 的 Phase 0–6；真实施工 WBS 由总计划 Phase 3 产出。旧 Phase → 主计划映射、C1–C7 → 五轴映射见 [README.md](./README.md)。下列复选框保留用于追溯，勾选与否不构成实现、测试、部署或验收证据。

## Legacy phase → master plan mapping

| 旧 Phase | 当前主计划对应（覆盖关系，不是一一对应） |
|---|---|
| Phase 0 Foundation | 总计划 Phase 0（P0-04..P0-11）+ P5-01 |
| Phase 1 Model Registry | 总计划 Phase 2 P2-01/P2-09 + Phase 5 P5-02/P5-10 |
| Phase 2 Active Push | 总计划 Phase 2 P2-08 + Phase 5 P5-08/P5-10 |
| Phase 3 Knowledge | 总计划 Phase 2 P2-01 + Phase 5 P5-05/P5-08 |
| Phase 4 Planning/OpenSpec | 总计划 Phase 0 P0-04/P0-07 + Phase 2 P2-03 + Phase 5 P5-02 |
| Phase 5 Completion/Verdict | 总计划 Phase 0 P0-06 + Phase 4 P4-06 + Phase 5 P5-05 |
| Phase 6 Takeover | 总计划 Phase 2 P2-03/P2-04 + Phase 5 P5-08 |
| Phase 7 UI | 总计划 Phase 1 P1-01..P1-08 + Phase 5 P5-08 |
| Phase 8 Toolchain/E2E/Final | 总计划 Phase 3 P3-03/P3-05 + Phase 5 P5-11 + Phase 6 P6-01..P6-08 |

## Phase 0 — Foundation
- [ ] P0-01 OpenSpec change and capability deltas (S) — Depends: none
- [ ] P0-02 Repo layout, module boundaries and blueprint wiring (M) — Depends: P0-01
- [ ] P0-03 Migration runner and schema v1 (M) — Depends: P0-02
- [ ] P0-04 Frozen contract schemas and validators (M) — Depends: P0-03
- [ ] P0-05 Event log, SSE replay, outbox foundation (M) — Depends: P0-03, P0-04
- [ ] P0-06 Test harness, fixtures and CI commands (S) — Depends: P0-02
- [ ] P0-07 Security baseline and command facade extension (S) — Depends: P0-03
- [ ] P0-08 ADR set and execution docs (S) — Depends: P0-01

## Phase 1 — Model Registry and Runtime Switching
- [ ] P1-01 Model catalog snapshot and capability probe (M) — Depends: P0-04, P0-06
- [ ] P1-02 Model policy resolver with precedence (M) — Depends: P1-01
- [ ] P1-03 Hot switch service and audit (M) — Depends: P1-02
- [ ] P1-04 Validation, fallback and degradation policy (M) — Depends: P1-03
- [ ] P1-05 Model APIs (S) — Depends: P1-03, P1-04
- [ ] P1-06 CLI model control (S) — Depends: P1-05
- [ ] P1-07 Binding snapshot in delivery/reproducibility (S) — Depends: P1-04

## Phase 2 — Active Push and Terminal Reporting
- [ ] P2-01 Outbox dispatcher with delivery ledger (M) — Depends: P0-05
- [ ] P2-02 SSE, file and terminal channels (M) — Depends: P2-01
- [ ] P2-03 Webhook channel with HMAC and retries (M) — Depends: P2-01, P0-07
- [ ] P2-04 Subscription CRUD, filters and test send (M) — Depends: P2-02, P2-03
- [ ] P2-05 CLI task watch and terminal notification (S) — Depends: P2-02, P2-04
- [ ] P2-06 Completion-only notification and dedupe tests (S) — Depends: P2-05, P0-04

## Phase 3 — Knowledge Base, Failure Capture and Similar-Task Retrieval
- [ ] P3-01 Unified KB schema, FTS and lifecycle (M) — Depends: P0-03, P0-04
- [ ] P3-02 Unified retrieval with ranking and citations (M) — Depends: P3-01
- [ ] P3-03 Intake retrieval packet (M) — Depends: P3-02
- [ ] P3-04 Playbook persistence after completion (M) — Depends: P3-03, P0-04
- [ ] P3-05 Failure miner and root-cause classification (L) — Depends: P3-04
- [ ] P3-06 Script-fix and tool knowledge writer (M) — Depends: P3-05
- [ ] P3-07 Document ingestion and doc-analysis tasks (M) — Depends: P3-01
- [ ] P3-08 KB APIs and retrieval metrics (S) — Depends: P3-02, P3-05
- [ ] P3-09 Backfill and stale policy for existing KB (M) — Depends: P3-01
- [ ] P3-10 Consolidation job (S) — Depends: P3-05, P3-08

## Phase 4 — Planning, Case/Oracle Generation, OpenSpec and Agent Config
- [ ] P4-01 Requirement intake v2 (M) — Depends: P0-04, P3-03
- [ ] P4-02 Functional model and validation-pool matching (M) — Depends: P4-01
- [ ] P4-03 Structured plan, case and oracle writer (M) — Depends: P4-02
- [ ] P4-04 Adversarial multi-model review (M) — Depends: P4-03, P1-04
- [ ] P4-05 Deterministic assurance gates (M) — Depends: P4-04
- [ ] P4-06 Human approval and plan freeze (M) — Depends: P4-05
- [ ] P4-07 Agent registry and config renderer (M) — Depends: P0-04
- [ ] P4-08 OpenSpec requirement workflow and write guard (M) — Depends: P4-07, P0-07
- [ ] P4-09 Review rubric and templates (S) — Depends: P4-04
- [ ] P4-10 Plan quality metrics and evaluation hook (M) — Depends: P4-05, P4-09
- [ ] P4-11 Lightweight discussion plugin (M) — Depends: P4-07, P1-02
- [ ] P4-12 Test correctness validation (placeholder, details TBD) — Depends: P4-05, P5-03
- [ ] P4-13 Senior test engineer role charter and scorecard (S) — Depends: P4-07, P4-09

## Phase 5 — Completion Contract and Verdict Integration
- [ ] P5-01 Completion report and terminal guard (M) — Depends: P0-03, P0-04, P4-06
- [ ] P5-02 Evidence requirement registry (M) — Depends: P5-01
- [ ] P5-03 Real-run proof and receipt verification (M) — Depends: P5-01, P0-07
- [ ] P5-04 Independent verdict recompute and divergence (M) — Depends: P5-01, P5-02
- [ ] P5-05 Archive and knowledge write-back gate (M) — Depends: P5-01, P3-04, P3-05
- [ ] P5-06 Completion API, UI data and invariant tests (M) — Depends: P5-03, P5-04, P5-05
- [ ] P5-07 Reproducibility manifest in delivery (S) — Depends: P1-07, P5-03

## Phase 6 — Human Takeover and Session Attach
- [ ] P6-01 Executor session registry (M) — Depends: P0-03, P0-04
- [ ] P6-02 Launcher handshake and CLI attach (M) — Depends: P6-01, P2-05
- [ ] P6-03 Takeover lease, fencing and safe pause (M) — Depends: P6-01
- [ ] P6-04 History replay and attach WebSocket (M) — Depends: P6-03
- [ ] P6-05 Input injection, resume and duplicate-effect guard (M) — Depends: P6-04, P5-03
- [ ] P6-06 Takeover APIs and permissions (S) — Depends: P6-05

## Phase 7 — UI Fully Matches the Platform
- [ ] P7-00 NoahsArk UI design system and page specs (M) — Depends: P4-13, P0-04
- [ ] P7-01 Shell, navigation, tokens and shared components (M) — Depends: P0-02, P4-07, P7-00
- [ ] P7-02 Overview page (M) — Depends: P7-01, P5-06, P2-04, P1-05
- [ ] P7-03 Tasks list and detail (M) — Depends: P7-01, P5-06, P3-03, P2-05
- [ ] P7-04 Similar tasks and playbook panels (S) — Depends: P7-03, P3-03
- [ ] P7-05 Models page (M) — Depends: P1-05, P7-01
- [ ] P7-06 Toolchain/version panel (M) — Depends: P0-04, P1-01, P7-01
- [ ] P7-07 Takeover terminal (M) — Depends: P6-06, P7-03
- [ ] P7-08 Knowledge pages (M) — Depends: P3-08, P7-01
- [ ] P7-09 Nodes and devices page (M) — Depends: P0-02, P7-01
- [ ] P7-10 Push subscriptions and delivery log (M) — Depends: P2-04, P7-01
- [ ] P7-11 SSE client hardening (S) — Depends: P7-01
- [ ] P7-12 Accessibility, responsive and visual QA (M) — Depends: P7-02..P7-10
- [ ] P7-13 UI contract and security tests (S) — Depends: P7-02..P7-12

## Phase 8 — Toolchain Upgrade Drill, Real-Run E2E and Final Verification
- [ ] P8-01 Toolchain snapshot, compat matrix and drift detector (M) — Depends: P1-01, P0-04
- [ ] P8-02 Compatibility smoke tiers and upgrade playbook (M) — Depends: P8-01
- [ ] P8-03 Real-device E2E harness (M) — Depends: P5-06, P6-06, P7-13
- [ ] P8-04 Real PASS scenario with push, completion, KB and reuse (L) — Depends: P8-03
- [ ] P8-05 Real FAIL/BLOCKED/offline scenarios (M) — Depends: P8-04
- [ ] P8-06 Takeover + model switch mid-task real scenario (M) — Depends: P8-04, P6-05
- [ ] P8-07 Upgrade drill with simulated opencode/OMO bump (M) — Depends: P8-02
- [ ] P8-08 Observability, alerts and runbooks (M) — Depends: P5-06, P2-06, P8-02
- [ ] P8-09 Documentation and operator guide (S) — Depends: P8-04..P8-08
- [ ] P8-10 Final verification wave (M) — Depends: all previous

**Count:** 81 checkboxes (8+7+6+10+13+7+6+14+10). **历史/已取代（2026-10-28）**：该计数不是当前范围；当前范围与阶段见总计划 Phase 0–6。
