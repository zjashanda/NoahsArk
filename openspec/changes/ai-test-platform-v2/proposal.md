# AI Test Platform v2

## 规范同步说明（2026-10-28，P0-03）

> 本变更的以下旧表述已按已批准决策修正，最高事实源为 `.omo/drafts` 已审核正文与 [NoahsArk 平台交付总计划](../../../../.omo/plans/noahsark-platform-delivery.md)。逐项冲突与验证见 [openspec 与 docs/v2 规范同步记录](../../../../docs/delivery/openspec-v2-sync.md)。
>
> - PostgreSQL 是唯一正式数据库；原文 SQLite 已取代。
> - 判定采用五轴并分离执行/设备/证据/最终判定；原文单一终态已取代。
> - 已启动冻结压测断线/心跳过期继续执行且设备保持占用；重连 STOP-first；设备释放、证据完整性和最终判定分离；缺 `cleanup_receipt` 只阻断释放确认。
> - 原文 81 项任务只作历史账本；当前范围是总计划 Phase 0–6。

## Why

NoahsArk is a new AI test platform codebase in `https://github.com/zjashanda/NoahsArk`. It must own real task execution, leases, evidence, verdicts and archive from its first implementation; the legacy platform is a negative reference only and must not be reused as the execution or UI layer. The v2 baseline lacks a formal OpenSpec boundary for runtime model policy, active delivery, retrieval, takeover, completion integrity, UI and agent governance. Without this change, generated plans and implementation work cannot be reviewed against one stable contract, and completion could be confused with a status string or a dry run.

平台方案与知识库审计明确：以 NoahsArk 为唯一状态真相，采用全新的 Flask/Jinja/vanilla JS/SSE + **PostgreSQL** 实现（历史/已取代 2026-10-28：原文 SQLite），不复用 the legacy platform 的 UI 或执行路径；lstest 作为工具规范层。项目知识、工具知识、失败模式和任务 playbook 必须带来源、适用边界和证据，不能把一次性脚本或 secret 污染知识库。

## What changes

- Add a formal v2 change with frozen contracts for model binding, toolchain compatibility, events/push, retrieval/playbooks, completion, takeover, agent/OpenSpec governance and the NoahsArk console UI.
- Add nine capability deltas: `model-policy`, `platform-events-push`, `knowledge-retrieval`, `task-playbook`, `completion-gate`, `takeover-session`, `toolchain-compatibility`, `agent-openspec-config`, and `ui-v2`.
- Define deterministic-plane ownership: agents propose typed artifacts; command/state/evidence/completion/archive paths alone mutate irreversible facts.
- Require real node/device/script receipts for completion. Dry-run, simulated, recorded and replay modes remain preflight/test modes only.
- Map all 11 requirements to the legacy 81-item task ledger in Phases 0–8 for traceability only. **历史/已取代（2026-10-28）**：81 项不再代表当前范围或施工 WBS；当前范围是 [NoahsArk 平台交付总计划](../../../../.omo/plans/noahsark-platform-delivery.md) 的 Phase 0–6，Phase 3 产出新 WBS。This change is documentation/specification only; it does not implement product code or modify main specs.

## Requirements covered

1. Runtime model switching with validation, fallback and no restart.
2. Version locks and machine-proven compatibility after upgrades.
3. Active task/result push to terminal, file, webhook and event bus.
4. Similar-task retrieval and playbook persistence.
5. Failure, log, root-cause, script-fix and project/tool/platform knowledge write-back.
6. Binary evidence-backed completion with no false completion.
7. Human takeover with CLI attach, replay and input.
8. Full platform UI for tasks, knowledge, nodes, models, versions, push, takeover and progress.
9. Real execution only; dry-run cannot be completion evidence.
10. OpenSpec-per-agent context, generated config, requirement and review gates.
11. Retrieval + deterministic assurance + adversarial review for plans/cases/oracles.

## Scope and non-goals

This change creates the new NoahsArk codebase; it does not create a second workflow engine, reuse legacy platform UI or execution adapters, copy credentials to nodes, auto-approve knowledge, or use a dry-run runtime as completion evidence. Existing main specs are referenced by name only and remain unchanged.

## Impact

Implementation is expected in the new NoahsArk repo under `app/`, new NoahsArk templates/static assets, `config/agents/`, toolchain lock files and tests. No legacy platform directories or templates are imported. Phase 0 freezes shared contracts before feature tracks. Migration is additive and feature flags default off.
