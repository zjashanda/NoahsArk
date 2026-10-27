# AI Test Platform v2

## Why

NoahsArk is a new AI test platform codebase in `https://github.com/zjashanda/NoahsArk`. It must own real task execution, leases, evidence, verdicts and archive from its first implementation; the legacy platform is a negative reference only and must not be reused as the execution or UI layer. The v2 baseline lacks a formal OpenSpec boundary for runtime model policy, active delivery, retrieval, takeover, completion integrity, UI and agent governance. Without this change, generated plans and implementation work cannot be reviewed against one stable contract, and completion could be confused with a status string or a dry run.

平台方案与知识库审计明确：以 NoahsArk 为唯一状态真相，采用全新的 Flask/Jinja/vanilla JS/SSE/SQLite 实现，不复用 the legacy platform 的 UI 或执行路径；lstest 作为工具规范层。项目知识、工具知识、失败模式和任务 playbook 必须带来源、适用边界和证据，不能把一次性脚本或 secret 污染知识库。

## What changes

- Add a formal v2 change with frozen contracts for model binding, toolchain compatibility, events/push, retrieval/playbooks, completion, takeover, agent/OpenSpec governance and the NoahsArk console UI.
- Add nine capability deltas: `model-policy`, `platform-events-push`, `knowledge-retrieval`, `task-playbook`, `completion-gate`, `takeover-session`, `toolchain-compatibility`, `agent-openspec-config`, and `ui-v2`.
- Define deterministic-plane ownership: agents propose typed artifacts; command/state/evidence/completion/archive paths alone mutate irreversible facts.
- Require real node/device/script receipts for completion. Dry-run, simulated, recorded and replay modes remain preflight/test modes only.
- Map all 11 requirements to the 81 implementation tasks in Phases 0–8. This change is documentation/specification only; it does not implement product code or modify main specs.

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
