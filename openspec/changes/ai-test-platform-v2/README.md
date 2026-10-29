# ai-test-platform-v2 OpenSpec change

P0-01 documentation/specification deliverable for the AI Test Platform v2 plan. No product code, database, existing main spec or unrelated file is changed by this draft.

## 规范同步说明（2026-10-28，P0-03）

> 本变更保留为 active OpenSpec change，但下列内容以已批准决策为最高事实源：`.omo/drafts/00-baseline`、`01-design`、`02-delivery` 已审核正文，以及 [NoahsArk 平台交付总计划](../../../../.omo/plans/noahsark-platform-delivery.md)。逐项冲突、精确修改与验证见 [openspec 与 docs/v2 规范同步记录](../../../../docs/delivery/openspec-v2-sync.md)。
>
> 1. **PostgreSQL 是唯一正式数据库。** 原文 SQLite/SQLite WAL 口径已取代；SQLite 只可作为历史参考或只读分析副本，不得作为正式数据库或契约结构来源。
> 2. **判定采用五轴**：`execution_status`、`validity_status`、`business_verdict`、`evidence_status`、`verification_status`，并分离执行状态、设备占用（`OCCUPIED/RELEASING/RELEASED/QUARANTINED`）、通信状态（`ONLINE/OFFLINE/STALE`）、证据完整性和最终判定。旧 `PASS | FAIL | BLOCKED_HUMAN | CANCELLED | STOPPED | INFRA_ERROR` 仅作历史别名。
> 3. **离线续跑与占用保留**：已启动的冻结压测在通信中断或心跳/租约过期后继续执行；Linux 标记通信离线，但设备保持占用，不新派、不重派、不重播、不重复采样。
> 4. **STOP-first 重连**：任何重连先处理待 STOP，再补传、去重和对账；旧 epoch/旧租约不得改变当前运行。
> 5. **释放与判定分离**：执行结束、设备释放、证据完整性、最终判定分别建模。确认本地停止、安全清理和占用对账后可释放设备，不等待大日志归档或最终判定。
> 6. **`cleanup_receipt` 语义**：缺失只阻断“设备释放确认”，设备保持占用；不自动判定整条证据链不完整，也不自动构成业务 FAIL。
> 7. **任务范围**：旧 81 项与 C1–C7 是历史账本/门禁，只作追溯；当前范围是总计划 Phase 0–6，真实施工 WBS 由 Phase 3 产出。
>
> P0-03 不构成实现、测试、部署或验收通过。

## Traceability

| Requirement | Capability delta | Primary tasks |
|---|---|---|
| 1 Model switching | `model-policy` | P1-01..P1-07, P7-05, P8-06 |
| 2 Version/upgrade compatibility | `toolchain-compatibility` | P0-03, P1-01, P7-06, P8-01, P8-02, P8-07 |
| 3 Active push | `platform-events-push` | P2-01..P2-06, P7-10, P8-04 |
| 4 Similar retrieval/playbook | `knowledge-retrieval`, `task-playbook` | P3-02..P3-04, P7-04, P8-04 |
| 5 Failure and knowledge write-back | `knowledge-retrieval`, `task-playbook` | P3-01..P3-10, P7-08, P8-05 |
| 6 Completion contract | `completion-gate` | P0-04, P5-01..P5-07, P8-05 |
| 7 Human takeover | `takeover-session` | P6-01..P6-06, P7-07, P8-06 |
| 8 Platform UI | `ui-v2` | P7-00..P7-13, P8-10 |
| 9 Real execution | `completion-gate`, `toolchain-compatibility` | P5-03, P8-03..P8-05 |
| 10 OpenSpec/agent governance | `agent-openspec-config` | P4-07..P4-09, P0-01 |
| 11 Quality plans/cases/oracles | `knowledge-retrieval`, `completion-gate` | P3-02, P4-01..P4-10, P5-04 |

## Task accounting

`tasks.md` contains the plan's 81 checkbox items, grouped Phase 0–8, with dependencies preserved. Count: 8 + 7 + 6 + 10 + 13 + 7 + 6 + 14 + 10 = 81.

**历史/已取代（2026-10-28）**：81 项是 2026-10-26 计划快照，不再代表当前完整范围，也不是当前施工 WBS。当前范围与阶段以 [NoahsArk 平台交付总计划](../../../../.omo/plans/noahsark-platform-delivery.md) 的 Phase 0–6 为准；Phase 3 产出真实施工 WBS。旧 81 项只用于追溯当时的需求覆盖。

### Legacy phase → master plan mapping

| 旧 OpenSpec Phase | 旧内容 | 当前主计划对应（覆盖关系，不是一一对应） |
|---|---|---|
| Phase 0 Foundation | 仓库骨架、迁移、契约、事件、CI、安全、ADR | 总计划 Phase 0（P0-04..P0-11）+ Phase 5 P5-01 |
| Phase 1 Model Registry | 模型目录、策略解析、热切换、降级 | 总计划 Phase 2 P2-01/P2-09 + Phase 5 P5-02/P5-10 |
| Phase 2 Active Push | outbox、SSE、webhook、订阅、通知 | 总计划 Phase 2 P2-08 + Phase 5 P5-08/P5-10 |
| Phase 3 Knowledge | KB schema、检索、playbook、失败挖掘 | 总计划 Phase 2 P2-01 + Phase 5 P5-05/P5-08 |
| Phase 4 Planning/OpenSpec | 需求受理、方案/用例/oracle、审批、Agent 配置 | 总计划 Phase 0 P0-04/P0-07 + Phase 2 P2-03 + Phase 5 P5-02 |
| Phase 5 Completion/Verdict | 完成报告、证据注册、真实回执、独立复核、归档 | 总计划 Phase 0 P0-06 + Phase 4 P4-06 + Phase 5 P5-05 |
| Phase 6 Takeover | 会话注册、attach、租约、回放、输入 | 总计划 Phase 2 P2-03/P2-04 + Phase 5 P5-08 |
| Phase 7 UI | 设计系统、页面、响应式、可访问性 | 总计划 Phase 1 P1-01..P1-08 + Phase 5 P5-08 |
| Phase 8 Toolchain/E2E/Final | 工具链兼容、真机 E2E、升级演练、最终验证 | 总计划 Phase 3 P3-03/P3-05 + Phase 5 P5-11 + Phase 6 P6-01..P6-08 |

### Legacy C1–C7 gates

C1–C7 是旧完成/归档门禁，不是五轴的替代。当前映射：C1 方案 → `validity_status` 的前置批准边界；C2 真实执行 → `execution_status=COMPLETED`、`run_mode=real` 与设备占用事实；C3/C5 → `evidence_status`；C4 → `verification_status`；C6/C7 → 归档与可复现，不改变五轴结论。详见 `design.md` 的 “Legacy completion gates vs five-axis verdict”。

## Validation

Run from the canonical repository: `openspec validate ai-test-platform-v2 --strict` and, if supported, `openspec show ai-test-platform-v2 --json`.
