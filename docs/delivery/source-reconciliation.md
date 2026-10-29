# P0-02 事实源冲突登记与规范优先级

> 任务：P0-02 建立事实源优先级并登记全部已知冲突（Retry）
> 执行日期：2026-10-28（Asia/Shanghai）
> 状态：**P0-02 文档产物完成**。本文件是冲突登记与规范优先级的唯一登记表；P0-02 不构成契约冻结、实现、测试、部署、验收或发布授权。
> 边界：只修改 `docs/VERSIONING.md`、`README.md` 的入口链接和本文件。未修改 `docs/v2/`、`openspec/`、`docs/contracts/`、`.omo/`、`plan.md` 或 `docs/ssh.txt`；未提交、未推送、未改产品代码。
> 冲突计数：**21 个冲突类（SR-01 至 SR-21）**。同一冲突在多份文档中的重复出现不重复编号，全部已知位置见 §4 位置索引。
> 状态回填：2026-10-29 按独立复核 [`source-sync-followup-verification.md`](./source-sync-followup-verification.md) F-01 回填 SR-10、SR-11、SR-12 及 §1.3 速览的陈旧状态，原文与历次处置记录保留（见 §1.4）。Phase 0 未关闭，本表不构成契约冻结或实施授权。

## 1. 规范优先级摘要

完整规则见 [`docs/VERSIONING.md`](../VERSIONING.md) §2。发生冲突时按以下顺序处理，序号越小效力越高；同一层内再按“已冻结 > 已批准 > 待评审 > 草案”判定。

| 层级 | 来源 | 效力 |
|---|---|---|
| 1 | 已批准需求基线；已评审的架构/模块/施工验收/测试策略/优化边界；`docs/contracts/` 中标记 `frozen` 的契约；阶段 1 UI、阶段 2 落地方案、阶段 3 施工方案、阶段 4 验收方案的冻结件 | 对各自范围具有约束力。未冻结的评审结论只是“已批准（用于规划）”。 |
| 2 | 仓库根 `plan.md` | 评审决策日志，证明批准发生过；不是冻结件的替代物。只存在于 `plan.md` 的决定不能单独作为字段、阈值或验收契约。 |
| 3 | `docs/VERSIONING.md`、`README.md`、各目录索引 | 导航，不产生需求、契约或验收标准。 |
| 4 | `docs/v2/`、`openspec/` | P0-03 完成同步后为“与已批准边界一致的实现参考”；P0-03 之前为历史参考。与第 1 层冲突时以第 1 层为准。 |
| 5 | `.omo/drafts/99-history/`、`solutions/1027V1/`、`docs/v2/` 中标注“已取代”的章节 | 只读历史证据，不得据其恢复旧规则。 |

### 1.1 草案正文与批准记录的关系

`.omo/drafts/01-design/` 和 `.omo/drafts/02-delivery/` 的正文可能仍保留旧条文或旧状态标签。此时：

1. 以根 `plan.md` 中更晚的批准记录为准（例如 B-1 至 B-7、M-01 至 M-21、A-0 至 A-9、S5-1 至 S5-4、第六步优化审核）。
2. 不得因为草案正文未改写就恢复旧规则；也不得因为某条批准记录存在就宣称草案正文已同步、契约已冻结或产品已实现。
3. 草案正文的修订登记在本表 `SR-10`、`SR-11`、`SR-13` 等条目，由后续文档同步或契约任务处理；P0-02 不直接修改 `.omo/`。

### 1.2 阶段门后的事实源切换

| 阶段门 | 冻结产物 | 通过后的事实源地位 |
|---|---|---|
| Phase 0：P0-04 至 P0-08 + P0-11 | 领域、节点安全、证据判定、任务卡/报告/知识、运行阈值契约包及冻结归档 | 字段、枚举、状态机、错误码和阈值的唯一实施契约来源；当前仍为 `frozen-candidate` |
| Phase 1：P1-08 | Apple 风格平台整体 UI 设计冻结包 | 唯一 UI/视觉实现基线；旧 v2/v3 UI 材料全部降为历史参考 |
| Phase 2：P2-09 | 整体落地方案冻结包 | 服务端与 UI 实现的架构、模块边界和部署事实源 |
| Phase 3：P3-07 | 施工方案冻结包 | 施工 WBS、依赖顺序和质量门的唯一来源；旧 81 项账本只作历史追溯 |
| Phase 4：P4-08 | 验收方案冻结包 | 验收范围、L0-L5/T1-T6 和判定门槛的唯一来源 |

截至 2026-10-28，上述阶段门均未执行；`docs/contracts/` 仍为 `frozen-candidate`。冻结只表示内容锁定，不表示已实现、已测试、已验收或已发布。

### 1.3 关键冲突速览（六项）

下表是 §3 完整登记的摘要，只覆盖本任务要求的六项关键冲突。详细位置、验证命令和全部 21 个冲突类以 §3 为准。

| 主题 | 主要来源路径 | 已批准规则 | 解决方式 | 状态 |
|---|---|---|---|---|
| SQLite / PostgreSQL | `docs/v2/SOLUTION.md`、`docs/v2/IMPLEMENTATION-PLAN.md`、`docs/v2/UI-DESIGN.md`、`openspec/...`（SR-02） | PostgreSQL 是唯一正式数据库；SQLite 仅作历史参考或只读分析副本 | P0-03 已改写并保留“历史/已取代（2026-10-28）”原文 | 已闭环（历史标注） |
| 租约 / 心跳 / 离线续跑 | `docs/v2/SOLUTION.md` §5.3-5.4、`docs/v2/IMPLEMENTATION-PLAN.md` §5.1/§5.6、`docs/v2/UI-DESIGN.md`（SR-03） | 已启动冻结压测断线/心跳过期/租约过期后继续；设备保持 `OCCUPIED`，不新派/重派；重连 STOP-first | P0-03 已改写文档侧；源草案旧条留待 P0-09（SR-10）（2026-10-29 回填：源草案已由 `approved-draft-reconciliation.md` 修正，见 SR-10） | 已闭环（历史标注） |
| 清理回执 `cleanup_receipt` | `docs/v2/SOLUTION.md` §5.4/§7.6、`docs/v2/UI-DESIGN.md`、`docs/v2/IMPLEMENTATION-PLAN.md` §5.1（SR-09） | 缺失只阻断“设备释放确认”，设备保持占用；不自动等同证据不完整或业务 FAIL | P0-03 已改写；源草案 I-21 留待 P0-09（SR-11）（2026-10-29 回填：源草案已由 `approved-draft-reconciliation.md` 修正，见 SR-11） | 已闭环（历史标注） |
| 五轴判定 / C1-C7 | `docs/v2/SOLUTION.md` §5.4、`docs/v2/UI-DESIGN.md`、`openspec/.../specs/completion-gate/spec.md`（SR-07、SR-08） | 当前判定为 `execution_status`/`validity_status`/`business_verdict`/`evidence_status`/`verification_status` 五轴并分离；C1-C7 仅为旧完成/归档门禁，映射到五轴事实 | P0-03 已加旧门禁映射与历史标签 | 已闭环（历史标注） |
| 旧 81 项任务范围 | `docs/v2/IMPLEMENTATION-PLAN.md` 全文、`docs/v2/ACCEPTANCE-REPORT.md`、`docs/v2/SOLUTION.md` §11.2、`openspec/.../tasks.md`（SR-06） | 当前范围是总计划 Phase 0–6；真实施工 WBS 由 Phase 3 P3-01..P3-07 产出；81 项只作历史账本 | P0-03 已标历史并加旧 Phase → 主计划映射 | 已闭环（历史标注）；新 WBS 等待 P3-07 |
| 旧 UI 基线 | `docs/v2/UI-DESIGN.md`、`docs/v2/UI-REVIEW.md`、`docs/v2/UI-DESIGN-APPLE.md`、`design/wireframes/`（SR-05） | 新 Apple 风格整体 UI 由 Phase 1 P1-01..P1-08 产出并在 P1-08 冻结；当前无已冻结 UI 基线 | 旧 UI 已标历史参考；新基线等待 P1-08 | 等待阶段冻结（P1-08） |

### 1.4 状态回填记录（2026-10-29）

独立复核 [`source-sync-followup-verification.md`](./source-sync-followup-verification.md) §4.3 判定本文件 NEEDS-FIX，原因是 SR-10、SR-11、SR-12 与 §1.3 速览的状态未随 2026-10-29 已完成的后续修复回填。本节只记录回填前后的锚点，不删除任何原始处置文字。

| 位置 | 回填前（2026-10-28 记录） | 回填后（2026-10-29） | 依据 |
|---|---|---|---|
| §1.3 速览「租约 / 心跳 / 离线续跑」 | “源草案旧条留待 P0-09（SR-10）” | 保留原句，追加“源草案已由 `approved-draft-reconciliation.md` 修正” | `architecture-proposal.md:379-389` R-3；`module-design.md:385-391` R-2/R-3 |
| §1.3 速览「清理回执」 | “源草案 I-21 留待 P0-09（SR-11）” | 保留原句，追加“源草案已由 `approved-draft-reconciliation.md` 修正” | `architecture-proposal.md:91,379-383` R-1；`module-design.md:385-391` R-1 |
| §3 SR-10 | 开放项，Owner 为 P0-09 | `已闭环（后续修复回填，2026-10-29；原状态：开放-P0-09）` | `architecture-proposal.md:126`（§7 规则 4）、`:387`（R-3）；`module-design.md:101-114,203` |
| §3 SR-11 | 开放项，Owner 为 P0-09 | `已闭环（后续修复回填，2026-10-29；原状态：开放-P0-09）` | `architecture-proposal.md:91`（I-21）、`:379-383`（R-1） |
| §3 SR-12 | 开放项，Owner 为 P0-05 | `已闭环（README 已修；映射另见 C-03）（2026-10-29 回填；原状态：开放-P0-05）` | `docs/contracts/README.md:58`；`phase0-contract-remediation-verification.md:109` F-11 |
| §4 SR-10、SR-11、SR-12「当前处置」 | “待 P0-09 文档同步”“草案正文待同步”“待 P0-05 修订 README” | 改为指向已完成的修复，并保留 schema `expired` 与映射残项的说明 | 同上 |

回填口径说明：

1. 状态词新增“后续修复回填”，含义是本表原判定的开放项已由 `approved-draft-reconciliation.md`（源草案）与 `phase0-contract-remediation-verification.md`（契约 README）关闭，本表只补记结论。
2. SR-12 的 `lease.schema.json` `state` 闭集仍含 `expired`。该枚举本身不是缺陷，仅表示续约截止；`security.lease.state → domain Lease.state` 的逐值映射仍由 `contract-residual-followup.md` C-03 跟踪，不在本次回填范围。
3. 本节不改变任何已批准语义：PostgreSQL 唯一正式库、Linux 权威判定、Windows 仅事实、离线续跑、STOP-first、释放/证据/最终判定分离。

## 2. 状态口径

| 状态 | 含义 |
|---|---|
| `已闭环（本任务）` | P0-02 已建立规则或补齐产物。 |
| `已闭环（历史标注）` | P0-03 已改写当前口径并保留旧原文，旧文带有“历史/已取代（2026-10-28）”标签。 |
| `已闭环（后续修复回填，2026-10-29）` | 原登记为开放项，已由后续任务修正；本表于 2026-10-29 回填结论，原文与历次处置记录保留。 |
| `开放—P0-05` | 需要 P0-05 节点身份/消息安全契约同步。 |
| `开放—P0-09` | 需要 P0-09 决策登记册对账或草案正文同步。 |
| `开放—P0-04/P0-06` | 需要领域或证据判定契约冻结时统一。 |
| `等待阶段冻结（P1-08/P3-07）` | 只能由对应阶段冻结包关闭，P0-02 不提前宣称。 |
| `只读历史（不处置）` | 历史归档只保留追溯，不参与当前规范。 |
| `已登记（不阻断）` | 已知差异已登记，不阻断当前阶段。 |

## 3. 冲突登记表

| ID | 冲突主题 | 精确来源路径/章节 | 冲突表述（旧口径） | 已批准规则与权威来源 | 解决路径 | Owner | 状态 | 验证命令 |
|---|---|---|---|---|---|---|---|---|
| SR-01 | 旧事实源优先级 | `docs/VERSIONING.md` §2.2 | 2026-10-27 旧顺序把 `openspec/` 排第 1、`docs/v2/IMPLEMENTATION-PLAN.md` 排第 2 | 现 §2：需求基线/已评审边界/冻结契约/冻结执行计划为第 1 层；`plan.md` 为决策日志；`docs/v2`、`openspec` 降为第 4 层 | 保留旧顺序原文并标“历史/已取代（2026-10-28）”；P0-02 写入新优先级 | P0-02 | 已闭环（本任务） | `grep -n "历史/已取代" docs/VERSIONING.md` |
| SR-02 | SQLite vs PostgreSQL | `docs/v2/SOLUTION.md` §4.8、§7.2、附录 D2；`docs/v2/IMPLEMENTATION-PLAN.md` D2、§5.1、§5.6、P0-03、P8-01、§15；`docs/v2/UI-DESIGN.md` 头部、工具链页、系统存储区块；`openspec/.../proposal.md`、`design.md`、`specs/toolchain-compatibility/spec.md`、`README.md` | SQLite WAL 是数据层/正式库；PostgreSQL 只是后续选项；工具链锁含 SQLite | PostgreSQL 是唯一正式数据库；SQLite 只能作历史参考或只读分析副本 | P0-03 已改写 PostgreSQL 并在旧文处加“历史/已取代（2026-10-28）”；本表登记剩余历史位置 | P0-03 | 已闭环（历史标注） | `grep -rn "SQLite" docs/v2 openspec --include=*.md` |
| SR-03 | 租约/心跳/离线续跑 | `docs/v2/SOLUTION.md` §5.3、§5.4、§7.2；`docs/v2/IMPLEMENTATION-PLAN.md` §5.1、§5.6；`docs/v2/UI-DESIGN.md` 执行页与流程页 | 心跳/租约过期即停止、回收设备或判 `INFRA_ERROR`；通信离线等于设备空闲 | 已启动冻结压测断线/心跳过期/租约过期后继续；设备保持 `OCCUPIED`，不新派/重派/重播/重复采样；重连 STOP-first | P0-03 已在 `docs/v2`/`openspec` 改写并加历史标签；源草案旧条见 SR-10 | P0-03 | 已闭环（历史标注） | `grep -rn "断线\|心跳过期\|租约过期" docs/v2/SOLUTION.md docs/v2/IMPLEMENTATION-PLAN.md docs/v2/UI-DESIGN.md` |
| SR-04 | 契约索引的优先级排序 | `docs/contracts/README.md` §1 | 把 `plan.md` 与 `.omo/plans` 排第 2，把已同步草案正文排第 3，与 `docs/VERSIONING.md` §2 的层级顺序不同 | `docs/VERSIONING.md` §2 是规范优先级唯一来源；契约索引只作导航 | P0-05/P0-04 评审时把 §1 改为引用 `docs/VERSIONING.md` §2，不再自建排序 | P0-05 | 开放—P0-05 | `grep -n "事实源优先级" docs/contracts/README.md` |
| SR-05 | 旧 UI 基线 | `docs/v2/UI-DESIGN.md` 全文；`docs/v2/UI-REVIEW.md` 头部；`docs/v2/UI-DESIGN-APPLE.md` 头部；`design/wireframes/` | 旧 v2「航次档案」是当前 UI 基线；UI-REVIEW 等待 P7-00 评审；Apple 版只是对比候选 | 新 Apple 风格整体 UI 由 Phase 1 P1-01..P1-08 产出并在 P1-08 冻结；当前无已冻结 UI 基线 | 旧 UI 已标历史；新基线等待 P1-08，P0-02 不提前宣称冻结 | P1-08 | 等待阶段冻结（P1-08） | `grep -n "历史参考\|历史评审记录\|设计对比候选" docs/v2/UI-DESIGN.md docs/v2/UI-REVIEW.md docs/v2/UI-DESIGN-APPLE.md` |
| SR-06 | 81 项任务范围 | `docs/v2/IMPLEMENTATION-PLAN.md` 全文与 81 个复选框；`docs/v2/ACCEPTANCE-REPORT.md` §1、§9；`docs/v2/SOLUTION.md` §11.2、§14；`docs/v2/README.md` §2；`openspec/.../tasks.md`、`README.md` Task accounting、`proposal.md` Why/What changes | 81 项是当前完整任务数/当前 WBS | 当前范围是总计划 Phase 0–6；真实施工 WBS 由 Phase 3 P3-01..P3-07 产出；81 项只作历史账本 | P0-03 已标历史并加旧 Phase → 主计划映射；新 WBS 等待 P3-07 | P0-03 / P3-07 | 已闭环（历史标注）；新 WBS 等待 P3-07 | `grep -rn "81" docs/v2/IMPLEMENTATION-PLAN.md docs/v2/ACCEPTANCE-REPORT.md openspec/changes/ai-test-platform-v2/tasks.md` |
| SR-07 | C1–C7 仍是当前完成门禁 | `docs/v2/SOLUTION.md` §5.4、§7.6；`docs/v2/UI-DESIGN.md` 全文门禁印列；`docs/v2/IMPLEMENTATION-PLAN.md` §5.1；`openspec/.../README.md` Legacy C1–C7 gates；`openspec/.../design.md` | C1–C7 是当前完成契约，PASS 需 C1–C7 全过 | 当前判定为五轴并分离执行/设备/证据/最终判定；C1–C7 仅旧完成/归档门禁，映射到五轴事实 | P0-03 已加旧门禁映射与历史标签；旧 UI 文案保留但不再作为当前契约 | P0-03 | 已闭环（历史标注） | `grep -rn "C1" docs/v2/UI-DESIGN.md openspec/changes/ai-test-platform-v2/README.md` |
| SR-08 | 单一终态枚举 | `docs/v2/SOLUTION.md` §5.4；`docs/v2/IMPLEMENTATION-PLAN.md` §5.1；`docs/v2/UI-DESIGN.md` Verdict 表；`docs/v2/FLOWCHART-STYLE.md` §“为什么没有加 stateDiagram-v2”；`openspec/.../specs/completion-gate/spec.md` | `PASS / FAIL / BLOCKED_HUMAN / CANCELLED / STOPPED / INFRA_ERROR` 是当前单一终态 | 当前为 `execution_status`、`validity_status`、`business_verdict`、`evidence_status`、`verification_status` 五轴；旧枚举仅报告兼容别名 | P0-03 已把旧枚举降为历史别名/兼容词；五轴写入 `docs/v2` 与 `openspec` | P0-03 | 已闭环（历史标注） | `grep -rn "BLOCKED_HUMAN" docs/v2/SOLUTION.md docs/v2/FLOWCHART-STYLE.md openspec/changes/ai-test-platform-v2/specs/completion-gate/spec.md` |
| SR-09 | 清理回执语义 | `docs/v2/SOLUTION.md` §5.4、§7.6；`docs/v2/UI-DESIGN.md` 头部；`docs/v2/IMPLEMENTATION-PLAN.md` §5.1 | 缺 `cleanup_receipt` 等于证据不完整/自动业务失败 | 缺 `cleanup_receipt` 只阻断“设备释放确认”，设备保持占用；不自动等同证据不完整，也不自动业务 FAIL | P0-03 已改写 `docs/v2`/`openspec`；源草案 I-21 见 SR-11 | P0-03 | 已闭环（历史标注） | `grep -rn "cleanup_receipt" docs/v2/SOLUTION.md docs/v2/UI-DESIGN.md` |
| SR-10 | 源草案租约/心跳旧规则 | `.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` §7 租约规则第 4 条；`.omo/drafts/01-design/noahsark-v0.0.1-module-design.md` §2.6、§4.2 M-05 | “失联：`lease_expired` → 运行 `INFRA_ERROR` → 先对账再重派”；“心跳超时 → 租约过期 → run=INFRA_ERROR”；“到期即 `lease_expired`” | 已启动冻结压测离线继续、设备保持占用、不重派；心跳/租约到期不是所有权事件 | P0-03 不修改 `.omo`；`docs/v2`/`openspec` 已不采用旧表述；后续文档同步修正草案正文。**2026-10-29 回填：草案正文已由 `approved-draft-reconciliation.md` 修正（§7 规则 4、模块 §2.6/§4.2，原文保留在各文件修订说明表），本条关闭** | P0-09 | 已闭环（后续修复回填，2026-10-29；原状态：开放-P0-09） | `grep -n "lease_expired\|INFRA_ERROR" .omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` |
| SR-11 | 源草案清理回执旧不变量 | `.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` §5.2 I-21；§7 租约规则第 6 条 | “运行结束必须产出 `cleanup_receipt`，缺失视为证据不完整” | 缺失回执只影响释放确认；证据完整性独立计算；清理失败进入异常/隔离 | P0-06 契约已按新语义表达；草案正文后续同步修正，P0-02 不改 `.omo`。**2026-10-29 回填：草案 I-21 与 §7 规则 6 已由 `approved-draft-reconciliation.md` 修正（原文保留在修订说明表），本条关闭** | P0-09 / P0-06 | 已闭环（后续修复回填，2026-10-29；原状态：开放-P0-09） | `grep -n "I-21" .omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` |
| SR-12 | 契约租约措辞/枚举 | `docs/contracts/README.md` §2.3.2；`docs/contracts/security-node.md` §10.2、§10.3、§13.1；`docs/contracts/schemas/security/lease.schema.json` `state` | README 称 `security-node.md` 仍有“租约到期后进入 `lease_expired`”旧措辞；`lease.schema.json` 的 `state` 闭集含 `expired` | `expires_at` 只是续约截止，不是所有权到期；`expired` 仅线协议事实，设备保持 `OCCUPIED` | 实际 `security-node.md` 已写明正确语义；P0-05 修订 README 的过期陈述并统一 schema 说明，不得据 `expired` 重派。**2026-10-29 回填：README 过期陈述已由 P0-05 修订（`README.md:58`，F-11 已关闭）；schema `expired` 枚举本身正确，逐值映射另见 `contract-residual-followup.md` C-03** | P0-05 | 已闭环（README 已修；映射另见 C-03）（2026-10-29 回填；原状态：开放-P0-05） | `grep -n "lease_expired\|expired" docs/contracts/README.md docs/contracts/schemas/security/lease.schema.json` |
| SR-13 | 审批超时语义 | `.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` §6 审批表、§5.2 I-20；`.omo/drafts/01-design/noahsark-v0.0.1-module-design.md` §4.1 M-03；`docs/contracts/README.md` §2.3.7；`.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md` §3.2 | 超时为“提醒 → 升级 → 拒绝”，可配置拒绝 | 超时保持待处理并提醒/升级，不自动拒绝；`thresholds.md` 与测试策略一致 | P0-05/P0-09 同步草案措辞；当前以测试策略 §3.2 和 `docs/contracts/thresholds.md` 为准 | P0-05 / P0-09 | 开放—P0-05/P0-09 | `grep -n "升级 → 拒绝\|不自动拒绝" .omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md .omo/drafts/01-design/noahsark-v0.0.1-module-design.md .omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md` |
| SR-14 | 设备占用枚举命名 | `docs/contracts/domain.md` §9.2、§11.1、§11.2；`openspec/.../README.md` 规范同步说明；`openspec/.../design.md`；`docs/v2/SOLUTION.md` §5.4 | 契约使用 `IDLE/OCCUPIED/RELEASING`；`docs/v2`/`openspec` 使用 `OCCUPIED/RELEASING/RELEASED/QUARANTINED` | 语义一致：占用与通信/释放/隔离分离；名称需统一后才能冻结 | P0-04/P0-06 契约冻结时统一枚举；P0-02 只登记，不改契约 | P0-04 / P0-06 | 已登记（不阻断） | `grep -n "occupancy_state" docs/contracts/domain.md openspec/changes/ai-test-platform-v2/README.md docs/v2/SOLUTION.md` |
| SR-15 | 领域 UUID 与线协议前缀 ID | `docs/contracts/README.md` §2.3.1；`docs/contracts/security-node.md` §4.5 | 领域契约要求 canonical UUID；线协议使用 `node_<hex>`、`job_<hex>`、`lease_<hex>` 前缀字符串 | 同一对象不得在两个契约中拥有不同身份；须在 API 边界建立一对一映射或统一 | P0-04/P0-05 冻结前解决；当前不影响字段语义，但阻断“已冻结”声明 | P0-04 / P0-05 | 已登记（不阻断） | `grep -n "领域 UUID\|node_<hex>" docs/contracts/README.md docs/contracts/security-node.md` |
| SR-16 | `solutions/1027V1` 历史方案冲突 | `solutions/1027V1/MODULE-DESIGN.md` §2.3、§M0、§M9、§5.1；`solutions/1027V1/REMOTE-EXECUTION.md` §2.1、§5、§8；`solutions/1027V1/GAP-CLOSURE.md` §0、§7；`solutions/1027V1/REVIEW-OPTIMIZATION.md` §5；`solutions/1027V1/references/noahsark-review-12-sections.md` | SQLite WAL 为唯一事实源；81/86/89 项任务；C1–C7 为完成门禁；旧 UI/长轮询方案 | `solutions/1027V1/` 是历史方案迭代附录，只读证据；不得据其恢复 SQLite、旧任务数或旧门禁 | VERSIONING §2 第 5 层与 §4 已标只读；不修改归档正文；P0-11 归档时保留原样 | P0-02 / P0-11 | 只读历史（不处置） | `grep -rn "SQLite\|81\|86\|89" solutions/1027V1 --include=*.md` |
| SR-17 | C8 占位未定义 | `docs/v2/SOLUTION.md` §11.5；`docs/v2/ACCEPTANCE-REPORT.md` §9；`docs/v2/IMPLEMENTATION-PLAN.md` §P4-12；`docs/v2/UI-DESIGN.md` C8 说明 | C8“测试之测试”被预留为完成门禁，但没有验收标准 | 当前五轴判定不以 C8 占位为依据；C8 语义待后续方案确认 | 保留占位并标历史/待定；不把 C8 写入当前 PASS 条件 | P0-09 / P4 | 已登记（不阻断） | `grep -rn "C8" docs/v2/SOLUTION.md docs/v2/ACCEPTANCE-REPORT.md docs/v2/IMPLEMENTATION-PLAN.md` |
| SR-18 | 旧 PDF/位图/图源未重绘 | `docs/v2/SOLUTION.pdf`；`docs/v2/diagrams/*.svg`、`*.png`；`docs/v2/diagrams/FLOWCHARTS.pdf` | 图中仍反映旧终态、旧 C1–C7、旧 SQLite 流程 | Markdown 源已同步；二进制图示在 Phase 1/3 重绘前不得作为当前图示依据 | P1-08/P3-07 重绘并归档；P0-02 不修改二进制文件 | P1-08 / P3-07 | 开放—P1/P3 重绘 | `ls -l docs/v2/SOLUTION.pdf docs/v2/diagrams docs/v2/FLOWCHARTS.pdf` |
| SR-19 | 优化路线正文状态标签 | `.omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md` 头部 | “状态：规划提案 v2，待评审。不是已批准路线图。” | 根 `plan.md` 2026-10-28 已确认第六步优化边界与版本路线；该确认是“用于规划的已批准”，不是冻结 | 以 `plan.md` 批准记录为准确认优化边界；P0-09 同步草案状态标签，不提前声称冻结 | P0-09 | 开放—P0-09 | `grep -n "待评审" .omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md` |
| SR-20 | VERSIONING 冲突表链接缺失 | `docs/VERSIONING.md` §2.4、§9；`docs/delivery/source-reconciliation.md` | P0-03 报告登记：VERSIONING 多处链接目标文件不存在 | 冲突必须有唯一登记表；链接目标必须存在 | 本任务创建本文件；VERSIONING 链接已可解析 | P0-02 | 已闭环（本任务） | `test -s docs/delivery/source-reconciliation.md` |
| SR-21 | `SOLUTION.md` 内部任务计数自相矛盾 | `docs/v2/SOLUTION.md` §11.2（“77 还是 81”）与 §11.4 Q9（“已同步：81 项，任务 ID 无缺失”） | 同一文档一处说 81 已历史取代，另一处说 81 已同步且无缺失 | 81 项是 2026-10-26 历史快照，不是当前范围；以总计划 Phase 0–6 为准 | 保留两处原文；以 §11.2 的历史结论和 §14 总计划链接为准，P0-03 不再改写旧 Q9 | P0-03 | 已闭环（历史标注） | `grep -n "任务计数：77 还是 81\|已同步" docs/v2/SOLUTION.md` |

## 4. 位置索引（同一冲突的全部已知位置）

> 本节列出重复出现位置，避免读者只在主表看到一处就误以为其他地方已同步。历史归档中的重复出现只作追溯。

| ID | 全部已知位置 | 当前处置 |
|---|---|---|
| SR-01 | `docs/VERSIONING.md` §2.2 | 旧顺序原文保留，标“历史/已取代（2026-10-28）”。 |
| SR-02 | `docs/v2/SOLUTION.md` §4.8、§7.2、附录 D2；`docs/v2/IMPLEMENTATION-PLAN.md` D2、§5.1、§5.6、P0-03、P8-01、§15；`docs/v2/UI-DESIGN.md` 头部、工具链页、系统存储区块；`openspec/.../README.md` 同步说明、`proposal.md`、`design.md`、`specs/toolchain-compatibility/spec.md`；`solutions/1027V1` 多处 | `docs/v2`/`openspec` 已改写并加标签；`solutions` 只读历史。 |
| SR-03 | `docs/v2/SOLUTION.md` §5.3、§5.4、§7.2；`docs/v2/IMPLEMENTATION-PLAN.md` §5.1、§5.6；`docs/v2/UI-DESIGN.md` 第 1623、2383 行附近；`docs/v2/FLOWCHART-STYLE.md` 旧终态段 | 已加历史标签；当前以 `delivery-acceptance` §2.1-3、`test-strategy` §3.8 和 `plan.md` 批准记录为准。 |
| SR-04 | `docs/contracts/README.md` §1 | 待 P0-05 改为引用 VERSIONING §2。 |
| SR-05 | `docs/v2/UI-DESIGN.md` 全文；`docs/v2/UI-REVIEW.md` 头部；`docs/v2/UI-DESIGN-APPLE.md` 头部；`design/wireframes/`、`design/ui-prototype.html` | 旧 UI 标历史；新 Apple 基线等待 P1-08。 |
| SR-06 | `docs/v2/IMPLEMENTATION-PLAN.md` 全文；`docs/v2/ACCEPTANCE-REPORT.md` §1、§9；`docs/v2/SOLUTION.md` §11.2、§11.4 Q9、§14、附录；`docs/v2/README.md` §2；`openspec/.../tasks.md`、`README.md` Task accounting、`proposal.md`；`solutions/1027V1/GAP-CLOSURE.md`、`REVIEW-OPTIMIZATION.md`、`MODULE-DESIGN.md` | 当前范围以总计划 Phase 0–6 为准；81 只作历史账本。 |
| SR-07 | `docs/v2/SOLUTION.md` §5.4、§7.6；`docs/v2/UI-DESIGN.md` C1–C7 门禁印列、任务详情、系统页；`docs/v2/IMPLEMENTATION-PLAN.md` §5.1；`docs/v2/ACCEPTANCE-REPORT.md`；`openspec/.../README.md` Legacy C1–C7 gates、`design.md`、`specs/completion-gate/spec.md` | 旧门禁保留追溯；五轴映射已写入 `openspec`/`docs/v2`。 |
| SR-08 | `docs/v2/SOLUTION.md` §5.4；`docs/v2/IMPLEMENTATION-PLAN.md` §5.1；`docs/v2/UI-DESIGN.md` Verdict 表；`docs/v2/FLOWCHART-STYLE.md`；`docs/v2/ACCEPTANCE-REPORT.md`；`openspec/.../specs/completion-gate/spec.md` | 旧枚举降为兼容别名；五轴为当前判定。 |
| SR-09 | `docs/v2/SOLUTION.md` §5.4、§7.6；`docs/v2/UI-DESIGN.md` 头部；`docs/v2/IMPLEMENTATION-PLAN.md` §5.1；`.omo/drafts/01-design/...architecture-proposal.md` I-21 | 文档侧已改写；草案正文见 SR-11。 |
| SR-10 | `.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` §7 规则 4；`.omo/drafts/01-design/noahsark-v0.0.1-module-design.md` §2.6、§4.2 | 2026-10-29 已由 `approved-draft-reconciliation.md` 修正；当前不采用旧规则。 |
| SR-11 | `.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` §5.2 I-21、§7 规则 6；`docs/contracts/evidence-verdict.md` §12、§13（替代语义） | 契约侧已正确；草案正文已于 2026-10-29 同步（`approved-draft-reconciliation.md`）。 |
| SR-12 | `docs/contracts/README.md` §2.3.2；`docs/contracts/security-node.md` §10.2、§10.3、§13.1；`docs/contracts/schemas/security/lease.schema.json` | README 过期陈述已由 P0-05 修订（`README.md:58`，F-11）；schema `expired` 语义正确，逐值映射另见 C-03。 |
| SR-13 | `.omo/drafts/01-design/...architecture-proposal.md` §6、§5.2 I-20；`.omo/drafts/01-design/...module-design.md` §4.1；`docs/contracts/README.md` §2.3.7；`.omo/drafts/02-delivery/...test-strategy.md` §3.2 | 当前以测试策略和 `thresholds.md` 为准；草案待同步。 |
| SR-14 | `docs/contracts/domain.md` §9.2、§11.1、§11.2；`openspec/.../README.md`、`design.md`；`docs/v2/SOLUTION.md` §5.4 | P0-04/P0-06 冻结时统一命名。 |
| SR-15 | `docs/contracts/README.md` §2.3.1；`docs/contracts/security-node.md` §4.5 | P0-04/P0-05 冻结前建立映射或统一。 |
| SR-16 | `solutions/1027V1/MODULE-DESIGN.md` §2.3、§M0、§M9；`REMOTE-EXECUTION.md` §2.1、§5、§8；`GAP-CLOSURE.md` §0、§7；`REVIEW-OPTIMIZATION.md` §5；`references/noahsark-review-12-sections.md` | 只读历史，不参与当前规范。 |
| SR-17 | `docs/v2/SOLUTION.md` §11.5；`docs/v2/ACCEPTANCE-REPORT.md` §9；`docs/v2/IMPLEMENTATION-PLAN.md` P4-12；`docs/v2/UI-DESIGN.md` C8 说明 | 保留占位；不进入当前五轴 PASS 条件。 |
| SR-18 | `docs/v2/SOLUTION.pdf`；`docs/v2/diagrams/*.svg`、`*.png`；`docs/v2/diagrams/FLOWCHARTS.pdf` | 待 P1-08/P3-07 重绘。 |
| SR-19 | `.omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md` 头部 | 以 `plan.md` 批准记录为准；待 P0-09 同步标签。 |
| SR-20 | `docs/VERSIONING.md` §2.4、§9；本文件 | 已补齐。 |
| SR-21 | `docs/v2/SOLUTION.md` §11.2、§11.4 Q9 | 以 §11.2 历史结论和 §14 总计划链接为准。 |

## 5. 验证命令与结果

### 5.1 本任务改动范围

```bash
cd /home/bszheng/NoahsArk
git status --short
git diff --stat
git diff --check
```

预期：只出现 `docs/VERSIONING.md`、`README.md`、`docs/delivery/source-reconciliation.md` 的改动；`git diff --check` 无输出、退出码 0。未修改 `docs/v2/`、`openspec/`、`docs/contracts/`、`.omo/`、`plan.md`、`docs/ssh.txt`。

### 5.2 产物存在性与行数

```bash
test -s docs/delivery/source-reconciliation.md
wc -l docs/VERSIONING.md docs/delivery/source-reconciliation.md
grep -c "^| SR-" docs/delivery/source-reconciliation.md
```

预期：`test` 退出码 0；`grep -c` 输出 `42`（§3 主表 21 行 + §4 位置索引 21 行）。冲突类数量以 §3 的 SR-01 至 SR-21 为准。

### 5.3 旧口径带标签检查

```bash
grep -rn "SQLite" docs/v2 openspec --include=*.md
grep -rn "81" docs/v2/IMPLEMENTATION-PLAN.md docs/v2/ACCEPTANCE-REPORT.md openspec/changes/ai-test-platform-v2/tasks.md
grep -rn "C1" docs/v2/UI-DESIGN.md openspec/changes/ai-test-platform-v2/README.md
```

人工核对：每处命中必须带“历史/已取代”“历史参考”“legacy”“仅追溯”等标签，或明确写“不得使用/不是当前”。P0-03 报告 §8.2/§8.3 已给出无残留结论；本任务只做复核，不重复改写。

### 5.4 链接目标检查

```bash
test -f docs/VERSIONING.md
test -f docs/delivery/openspec-v2-sync.md
test -f docs/delivery/source-reconciliation.md
test -f .omo/plans/noahsark-platform-delivery.md
test -f docs/contracts/README.md
```

预期：全部退出码 0。

### 5.5 规范优先级关键句检查

```bash
grep -n "已批准需求基线\|已评审的架构、模块与交付边界\|冻结契约包\|已冻结的执行计划\|评审决策日志\|同步后的实现参考\|历史归档＝只读证据" docs/VERSIONING.md
grep -n "阶段门后的事实源切换\|P1-08\|P2-09\|P3-07\|P4-08" docs/VERSIONING.md
grep -n "PostgreSQL 是唯一正式数据库\|五轴\|STOP-first\|cleanup_receipt\|81" docs/delivery/source-reconciliation.md
```

预期：关键句存在且数量与正文一致。

## 6. 结论与后续

1. **优先级已显式化**：`docs/VERSIONING.md` §2 的五层顺序覆盖需求基线、已评审架构/模块/施工验收/测试策略/优化边界、冻结契约、冻结执行计划、`plan.md`、导航、`docs/v2`/`openspec` 和历史归档。
2. **阶段门后切换已写明**：新计划、契约、UI/落地/施工/验收冻结件在对应阶段门通过后成为实现事实源；通过前不得声称冻结或实现。
3. **冲突已登记**：21 个冲突类覆盖 SQLite/PostgreSQL、租约/心跳/离线续跑、清理回执、五轴/C1–C7、81 项任务、旧 UI 基线、审批超时、占用枚举、ID 表示、历史归档、C8、旧图示、优化状态标签和缺失链接。
4. **未越界**：未修改 `docs/v2`、`openspec`、`docs/contracts`、`.omo`、`plan.md`、`docs/ssh.txt`；未实现产品代码、未提交、未推送、未勾选 `plan.md` 复选框。
5. **未声称批准**：`docs/contracts/` 仍是 `frozen-candidate`；P1-08、P2-09、P3-07、P4-08 尚未执行；P0-02 只完成规范优先级与冲突登记。

后续动作按状态执行：P0-05 修正契约索引与租约措辞；P0-09 同步草案旧条与优化状态标签；P0-04/P0-06 统一占用枚举与 ID 映射；P1-08/P3-07 冻结新 UI 与施工方案并重绘旧图示；P0-11 归档本表与哈希清单。

> 2026-10-29 回填注记：上述后续动作中“P0-05 租约措辞”已随 F-11 完成（见 SR-12），“P0-09 同步草案旧条”已随 `approved-draft-reconciliation.md` 完成（见 SR-10、SR-11）。其余动作（P0-05 契约索引、P0-09 优化状态标签、P0-04/P0-06 枚举与 ID、P1-08/P3-07 冻结与重绘）仍开放。本注记不改变 Phase 0 未关闭、A-0 未通过、契约为 `frozen-candidate` 的结论。
