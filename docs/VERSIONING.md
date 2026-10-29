# NoahsArk 版本与目录指南

本文是方案资料的目录、版本和事实源优先级规则。不把现有目录追溯性地改名，也不把历史材料宣称为已经发布的产品版本。

本文只负责“哪个文件可以约束工程决定”。文件之间的具体冲突、解决动作和责任方登记在 [`docs/delivery/source-reconciliation.md`](delivery/source-reconciliation.md)。

## 1. 目录状态

仓库中的材料按以下三种状态理解：

| 状态 | 含义 | 决策效力 |
|---|---|---|
| **规范** | 已被第 2 节第 1 层列入，并且已批准或已冻结的材料。 | 对各自范围具有约束力。冲突时优先按第 2 节顺序处理。 |
| **建议** | 方案、设计或未来工作建议，已评审但尚未冻结为契约。 | 供评审和后续版本采纳，不单独改变实现行为。 |
| **参考** | 历史基线、视觉比较、生成物、外部输入，以及 `docs/v2/`、`openspec/` 在 P0-03 同步前的全部内容。 | 只用于追溯、对照和实现参考，不作为当前需求或契约。 |

当前仓库仍是设计与规格交付包，尚未实现产品后端，也没有可据此声称的既有产品语义版本发布记录。文档被批准或冻结，只表示“可作为规划依据”，不表示功能已实现、测试已执行、验收已通过或已部署。

## 2. 当前规范来源优先级（自 2026-10-28 起）

发生冲突时按以下顺序处理，序号越小效力越高。同一层内再按“已冻结 > 已批准 > 待评审 > 草案”判定。

1. **已批准的规范基线与冻结件**，对各自范围具有约束力：
   1. **已批准需求基线**：`.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md`（2026-10-27 批准，覆盖第 1 至 16 节）。
   2. **已评审的架构、模块与交付边界**：`.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md`、`.omo/drafts/01-design/noahsark-v0.0.1-module-design.md`、`.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md`、`.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md`、`.omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md` 中经根 `plan.md` 评审记录确认的边界（架构 B-1 至 B-7、模块 M-01 至 M-21、字段级契约评审第 1 至 5 项、施工与验收 A-0 至 A-9、测试策略 S5-1 至 S5-4、优化边界与版本路线）。同一事项若存在更晚的批准记录，以较新记录为准；被更晚记录改写的旧条文按第 5 层处理。草案正文若仍保留旧状态标签或旧条文，以 `plan.md` 的批准记录和本文第 2.3 节为准，并登记到冲突表。
   3. **冻结契约包**：`docs/contracts/` 中标记为已冻结（`frozen`）的契约与 schema。标记为 `frozen-candidate` 的文件只是候选，冻结评审通过前不具备约束力。
   4. **已冻结的执行计划**：阶段 1 UI 设计、阶段 2 落地方案、阶段 3 施工方案、阶段 4 验收方案各自的冻结件（对应 `.omo/plans/noahsark-platform-delivery.md` 的 P1-08、P2-09、P3-07、P4-08）。这些阶段尚未冻结时，只有已批准的评审结论，不存在冻结件；冻结后的切换规则见第 2.3 节。
2. **`plan.md`（仓库根）＝评审决策日志**：逐条记录批准、修订、待决和边界。它是“某项决定确实发生过”的证据来源，但不是冻结件的替代物。引用契约、字段或阈值时必须落到第 1 层的基线或冻结件；`plan.md` 只用于说明该决定的来源、日期和批准范围。如果某决定只存在于 `plan.md` 而没有对应的已批准基线或冻结件，它最多是“用于规划的已批准决定”，不能单独作为字段、阈值或验收契约。
3. **`docs/VERSIONING.md` 与各索引文件＝导航**：`README.md`、`docs/v2/README.md`、`openspec/changes/*/README.md`、`docs/contracts/README.md` 等只说明目录结构、状态和阅读顺序，不产生需求、契约或验收标准。索引里的一句话不能覆盖第 1 至 2 层的决定。
4. **`docs/v2/` 与 `openspec/`＝同步后的实现参考**：P0-03 完成同步前，两者的全部内容（包括 `docs/v2/IMPLEMENTATION-PLAN.md`、`docs/v2/SOLUTION.md`、`openspec/changes/ai-test-platform-v2/`）一律视为历史参考，不得作为当前需求、契约、任务范围或验收依据，也不得覆盖第 1 至 2 层的已批准决定。P0-03 完成同步后（本仓库已于 2026-10-28 完成，证据见 [`docs/delivery/openspec-v2-sync.md`](delivery/openspec-v2-sync.md)），它们降为“与已批准边界和冻结件一致的实现参考”；一旦与第 1 层冲突，仍以第 1 层为准。已知冲突见 [`docs/delivery/source-reconciliation.md`](delivery/source-reconciliation.md)。
5. **历史归档＝只读证据**：`.omo/drafts/99-history/`、`solutions/1027V1/`，以及 `docs/v2/` 中被标注“已取代”的章节，只用于追溯审批链与方案演进，不是当前规范来源。不得据其恢复旧规则，也不得把其中的旧任务数、旧状态机或旧技术选型当作现行依据。

本次没有迁移已有方案基线：`docs/v2/`、`solutions/1027V1/`、`design/` 和 `openspec/` 均保留原位置。OpenSpec 继续使用仓库根目录的标准位置 `openspec/`，不复制到版本目录。

### 2.1 审批状态与实现状态必须分开表述

| 状态 | 含义 | 可以声称 | 不可以声称 |
|---|---|---|---|
| 草案 | 正在编写，未经评审。 | 有草稿 | 任何批准或约束力 |
| 待评审 | 已提交评审，结论未出。 | 有评审输入 | 已批准 |
| 已批准（用于规划） | 所有者/评审者确认了范围与边界。 | 可作为后续设计与规划依据 | 契约已冻结、已实现、已测试 |
| 已冻结 | 内容锁定，变更需新版本或新修订。 | 对范围内工程决定有约束力 | 已实现、已验证、已发布 |
| 已验证 / 已实现 | 有可复算证据证明行为正确。 | 实现了某能力并有证据 | 超出证据范围的能力 |

截至 2026-10-28，本仓库只有“已批准（用于规划）”和“已冻结候选”两类材料，没有任何“已验证 / 已实现”结论。

### 2.2 历史/已取代：2026-10-27 的旧优先级

> 状态：**历史/已取代**（2026-10-28，P0-02 起由第 2 节正文取代）。保留原文只用于追溯当时的判断，不得再据其确定规范来源。取代原因与冲突编号见 [`docs/delivery/source-reconciliation.md`](delivery/source-reconciliation.md) 的 SR-01。

```text
1. openspec/ 中保持 OpenSpec 标准结构的变更和规格，定义变更边界。
2. docs/v2/IMPLEMENTATION-PLAN.md，作为 v2 方案阶段的实施决策基线。
3. docs/v2/SOLUTION.md，负责统一叙述，不新增与实施计划冲突的契约。
4. docs/v2/ 其余文档，按各自状态使用。
5. solutions/1027V1/、design/ 和外部输入，仅在本文标注的范围内作为建议或参考。
```

上述顺序的问题：它把 `openspec/` 和 `docs/v2/` 放在最高层，而这两处仍是 SQLite、81 项任务、C1-C7 二值完成等未同步的旧口径，会直接覆盖已批准的需求基线、架构边界和 PostgreSQL 决策。新顺序已把这两处降到第 4 层并加上“P0-03 同步后才能作为实现参考”的前置条件。

### 2.3 阶段门后的事实源切换

总计划 `.omo/plans/noahsark-platform-delivery.md` 是当前唯一执行主线，但它本身不是冻结的实施契约。下表列出的冻结包在对应阶段门通过后，成为其范围内的实现事实源；通过前，只有已批准的评审结论可作为规划依据，不得声称已冻结、已实现或已验收。

| 阶段门 | 冻结产物 | 通过后的事实源地位 | 通过前 |
|---|---|---|---|
| Phase 0：P0-04 至 P0-08 + P0-11 | 领域、节点安全、证据判定、任务卡/报告/知识、运行阈值契约包及冻结归档 | 对应字段、枚举、状态机、错误码和阈值的唯一实施契约来源 | `docs/contracts/` 仅 `frozen-candidate`，不得声称已冻结 |
| Phase 1：P1-08 | Apple 风格平台整体 UI 设计冻结包（含设计系统、原型、视觉 QA 与评审记录） | 唯一 UI/视觉实现基线；旧 `docs/v2/UI-DESIGN.md`、`UI-REVIEW.md`、`UI-DESIGN-APPLE.md` 和 `design/` 线框全部降为历史参考 | 现有 UI 材料均为候选或历史，不存在已冻结 UI 基线 |
| Phase 2：P2-09 | 整体落地方案冻结包（服务端架构、数据模型、API、Node Agent、部署与灾备） | 服务端与 UI 实现的架构、模块边界和部署事实源；覆盖 `docs/v2/IMPLEMENTATION-PLAN.md` 的旧实施口径 | 只有已批准的架构/模块评审边界，不是可施工冻结方案 |
| Phase 3：P3-07 | 施工方案冻结包（WBS、依赖、环境、质量门、风险回滚） | 施工任务范围、依赖顺序和质量门的唯一来源；旧 81 项账本只作历史追溯 | 施工方案尚未冻结，不得据旧任务账本开工 |
| Phase 4：P4-08 | 验收方案冻结包（需求映射、L0-L5/T1-T6、判定与证据规则、执行手册） | 验收范围、证据层级和判定门槛的唯一来源 | 只有验收准则评审结论，不得声称验收已执行或通过 |

补充规则：

1. 阶段门通过后，冻结包正文优先于总计划的路线描述和索引摘要；总计划保留排期、依赖和状态记录，但不得用其 TODO 复选框替代冻结契约。
2. “已冻结”只表示内容锁定并可作为实施依据，不表示功能已实现、测试已执行、验收已通过或已部署；任何实现/验收声明必须有可复算证据。
3. 新冻结包与旧材料冲突时，旧材料必须按第 5 层标注“历史/已取代（日期）”，并在 [`docs/delivery/source-reconciliation.md`](delivery/source-reconciliation.md) 登记；不得静默覆盖或删除旧表述。
4. 本规则不提前宣称任何阶段门已经通过：截至 2026-10-28，P1-08、P2-09、P3-07、P4-08 均未执行，`docs/contracts/` 仍为候选。

### 2.4 P0-03 同步后的六项规则（导航摘要）

本节把 P0-03 要求同步到 `docs/v2`、`openspec` 与本文的六项已批准规则集中登记，便于读者从版本指南直接核对。**本节只作导航摘要，规范效力仍来自第 1 层已批准基线/冻结件与根 `plan.md` 批准记录**（见第 2 节优先级），不新增需求、契约或验收标准。逐项证据见 [`docs/delivery/openspec-v2-sync.md`](delivery/openspec-v2-sync.md)；与 `docs/v2`/`openspec` 的冲突登记见 [`docs/delivery/source-reconciliation.md`](delivery/source-reconciliation.md)。

| # | 规则 | 必须保持的语义 | 在同步对象中的落点 |
|---|---|---|---|
| 1 | **PostgreSQL 唯一正式库** | PostgreSQL 是唯一正式数据库；SQLite 只能作为历史参考或只读分析副本，不得作为正式库、正式存储或工具链锁组件。 | `docs/v2/SOLUTION.md` §4.8/§7.2、`docs/v2/IMPLEMENTATION-PLAN.md` D2/§5.6、`openspec/.../design.md` Data and completion、`specs/toolchain-compatibility/spec.md` |
| 2 | **五轴判定** | 判定由 `execution_status`、`validity_status`、`business_verdict`、`evidence_status`、`verification_status` 五轴组成；旧单一终态 `PASS / FAIL / BLOCKED_HUMAN / CANCELLED / STOPPED / INFRA_ERROR` 仅作历史别名。正式 PASS 必须同时满足 `execution_status=COMPLETED`、`validity_status=VALID`、`evidence_status=COMPLETE`、`business_verdict=PASS`、`verification_status=PASS`。 | `docs/v2/SOLUTION.md` §5.4、`docs/v2/IMPLEMENTATION-PLAN.md` §5.1、`openspec/.../design.md`、`specs/completion-gate/spec.md` Formal PASS |
| 3 | **离线续跑** | 已启动的冻结压测在通信中断、心跳过期或租约过期后继续离线执行；Linux 标记通信 `OFFLINE/STALE`，设备保持 `OCCUPIED`，不新派、不重派、不重播、不重复采样。 | `docs/v2/SOLUTION.md` §5.3、`openspec/.../design.md` Execution lifecycle、`specs/completion-gate/spec.md` Offline continuation |
| 4 | **STOP-first 重连** | 任何重连先处理待 STOP，再补传、去重和对账；旧 epoch/旧租约/旧控制者不得改变当前运行。 | `docs/v2/SOLUTION.md` §5.3-10、`openspec/.../design.md`、`specs/completion-gate/spec.md` Reconnect after offline continuation |
| 5 | **释放 / 证据 / 判定分离** | 执行结束、设备释放、证据完整性和最终判定分别建模；确认本地停止、安全清理和占用对账后可释放设备，不等待 GB 级日志归档或最终判定。 | `docs/v2/SOLUTION.md` §5.3-11、`openspec/.../design.md`、`specs/completion-gate/spec.md` Device release and evidence verdict separation |
| 6 | **`cleanup_receipt` 语义** | 缺失只阻断“设备释放确认”，设备保持 `OCCUPIED`/`QUARANTINED`；不自动判定整条证据链不完整，也不自动构成业务 FAIL。 | `docs/v2/SOLUTION.md` §5.3-12、`openspec/.../design.md`、`specs/completion-gate/spec.md` Missing cleanup receipt |

## 3. 完整的目标目录

下面的树表示推荐的仓库组织。它只列出当前存在的入口和已明确的未来承载位置，不预建大量空目录。带有“未来”的路径在对应材料产生前不需要创建。

```text
NoahsArk/
├── README.md                         # 仓库总入口，导航
├── plan.md                           # 评审决策日志，非冻结件
├── docs/
│   ├── VERSIONING.md                 # 本文，目录、版本与事实源优先级
│   ├── delivery/                     # 交付过程证据（分诊、进度、冲突登记）
│   │   ├── workspace-triage.md       # P0-01 工作区安全分诊
│   │   ├── construction-progress.md  # 施工进度表
│   │   └── source-reconciliation.md  # P0-02 事实源冲突登记
│   ├── contracts/                    # 领域契约包；frozen 后才具约束力
│   │   ├── README.md
│   │   └── schemas/                  # task/revision/approval/gate/lease/... schema
│   ├── references/                   # 跨版本资料，非正式契约
│   │   ├── README.md
│   │   └── diagrams/
│   │       └── 自动化生成测试用例流程图.svg
│   └── v2/                           # 历史 v2 方案基线，整体保留；P0-03 同步后为实现参考
│       ├── README.md                 # v2 文档索引
│       ├── SOLUTION.md               # v2 总体方案
│       ├── IMPLEMENTATION-PLAN.md    # v2 实施决策基线
│       ├── UI-DESIGN.md              # v2 UI 设计
│       ├── UI-DESIGN-APPLE.md        # Apple 风格 v3 对比材料
│       ├── UI-REVIEW.md              # UI 评审记录
│       └── ...                       # 其余 v2 文档、图表和报告
├── solutions/
│   ├── 1027V1/                       # 历史方案迭代，整体保留
│   │   ├── README.md
│   │   ├── CHANGELOG.md
│   │   ├── MODULE-DESIGN.md
│   │   ├── REMOTE-EXECUTION.md
│   │   ├── GAP-CLOSURE.md
│   │   ├── REVIEW-OPTIMIZATION.md
│   │   └── ...                       # PDF、流程图、sequences 和 references
│   └── V0.1.1/                       # 未来首次采用新编号时才创建
│       ├── README.md                 # 基线、适用范围、审批状态与目录地图
│       ├── CHANGELOG.md              # 相对前一版的变化与未关闭缺口
│       ├── solution/                 # 本版更新的总体方案（有变化时才建）
│       ├── implementation/           # 本版更新的模块/执行方案（有变化时才建）
│       ├── ui/                       # 本版更新的 UI 设计（有变化时才建）
│       ├── diagrams/                 # 本版更新的流程图源与渲染件（有变化时才建）
│       ├── sequences/                # 本版更新的时序图（有变化时才建）
│       └── review/                   # 本版评审与验收证据（有变化时才建）
├── design/                           # 现有 UI 基线和比较原型，路径保留
│   ├── design-tokens.json
│   ├── ui-prototype.html
│   ├── preview/                      # v2 截图与冒烟记录
│   ├── wireframes/                   # 15 个页面及索引
│   └── apple/                        # v3 候选：原型/令牌/截图/冒烟
├── openspec/                         # 历史变更记录；P0-03 同步后为实现参考
│   ├── config.yaml
│   └── changes/
│       └── <change-name>/
│           ├── README.md
│           ├── proposal.md
│           ├── design.md
│           ├── tasks.md
│           └── specs/
└── assets/
    └── brand/ark-logo.svg            # v2 与 UI 候选共享的方舟品牌资产
```

原仓库根目录的 SVG 已原样迁入 `docs/references/diagrams/`，只作为流程参考；它不是 V1 正式总流程图。

## 4. 历史材料映射

### `docs/v2/`：历史 v2 基线（P0-03 同步后为实现参考）

`docs/v2/` 是方案和 UI 设计评审阶段的历史基线。目录内容保持原样，不移动、不重命名、不覆盖。

> **历史/已取代**（2026-10-28，P0-03 同步完成后登记）：原文称“`docs/v2/` 是方案和 UI 设计评审阶段的历史基线。它可以作为 v2 方案的参考和部分规范来源，具体以 `IMPLEMENTATION-PLAN.md` 与 OpenSpec 为准。”该表述已失效。自 2026-10-28 起，`docs/v2/` 全部内容按第 2 节第 4 层处理：P0-03 同步完成后只作与已批准边界一致的实现参考，不得覆盖需求基线、已评审架构/模块边界或 PostgreSQL 决策。冲突明细见 [`docs/delivery/source-reconciliation.md`](delivery/source-reconciliation.md) SR-02、SR-03、SR-06、SR-07、SR-08、SR-09。

其中的 `UI-DESIGN.md`（v2 航次档案）和 `UI-DESIGN-APPLE.md`（v3 Quiet Instrument）都只是 UI 候选材料。当前没有任何 UI 基线被冻结；新的 Apple 风格平台整体 UI 由阶段 1 的 P1-01 至 P1-08 产出并在 P1-08 冻结。v2、v3 以及可能被讨论的混合方向都不等于已批准基线。

### `solutions/1027V1/`：历史方案迭代附录（只读证据）

`solutions/1027V1/` 是 M0 设计评审版的模块级实施、远程执行、缺口关闭和评审优化材料。它是 v2 基线的方案附录和历史评审证据，不是已经上线的 V1 产品实现，也不属于第 2 节第 1 层。

目录中的 `README.md`、`CHANGELOG.md` 和流程图只描述该方案目录的内容。它们不能证明仓库已经采用了完整的 `VMAJOR.MINOR.PATCH` 发布版本。

### `design/`：设计参考

`design/` 保存线框、原型、设计令牌和 Apple 风格比较材料。它属于设计参考或建议，除非被第 2 节第 1 层的冻结件明确引用，否则不直接产生工程契约。

### `openspec/`：历史变更记录（P0-03 同步后为实现参考）

`openspec/` 保持根目录标准位置。`openspec/config.yaml` 使用 `spec-driven` schema，当前变更位于 `openspec/changes/ai-test-platform-v2/`。OpenSpec 变更不迁入 `docs/v2/` 或任何版本目录。

自 2026-10-28 起，`openspec/` 按第 2 节第 4 层处理：P0-03 同步完成后，其中的 `design.md`、`tasks.md` 与 `specs/` 是与已批准边界一致的实现参考，仍不得作为当前契约或任务范围依据，也不得覆盖第 1 层。已确认的冲突包括 SQLite（SR-02）、81 项任务（SR-06）、C1-C7 二值完成（SR-07）、单一终态枚举（SR-08）。

## 5. 版本号规则

以后每次方案迭代都使用 `V主版本.部分版本.小修订`，例如 `V0.1.1`、`V0.2.1`、`V1.0.1`。这是**方案**版本目录规则，不代表产品已上线，也不是对现有 `docs/v2` 或 `1027V1` 的追溯改名。

| 变更类型 | 递增规则 | 典型情况 |
|---|---|---|
| 主版本 | 主版本 +1，后两位重置为 `0.1`，如 `V0.2.3 → V1.0.1` | 总体架构、核心流程、边界或方案方向的大版本优化。 |
| 部分版本 | 中间位 +1，末位重置为 `1`，如 `V0.1.3 → V0.2.1` | 某个模块、专题或方案部分的修改优化。 |
| 小修订 | 最后一位 +1，如 `V0.1.1 → V0.1.2` | 小功能、局部规则、图示或文字修改优化。 |

规则补充：

- 新方案首次采用三段式编号时可使用 `V0.1.1`；不是给现有历史资料自动补一个版本号。
- 每次方案内容发生更新都新增**一个独立版本目录**，旧版保留；不得在原版本目录覆盖内容。
- 版本号与审批状态分开记录：草案、待评审、已批准、已取代。编号本身不证明产品已经实现或方案已批准。
- OpenSpec 变更、工具链版本与 UI 风格比较版各有自己的标识，不冒充方案版本号。

## 6. 每个未来迭代目录的规则

每次新的方案迭代只创建一个独立目录，例如 `solutions/V0.1.1/`，后续按上表依次递增。不要覆盖旧目录，也不要把多个迭代混放在同一目录。现有 `solutions/1027V1/` 原样保留为历史评审包，不改名、不伪装成 `V1.0.1`。

每个迭代目录至少包含：

1. `README.md`，说明基线、目标、差异、状态和未关闭缺口。
2. `CHANGELOG.md`，记录新增、修改、未采纳建议和验证范围。
3. 该迭代自己的方案正文、图表、PDF、时序图或其他交付物；按 `solution/`、`implementation/`、`ui/`、`diagrams/`、`sequences/`、`review/` 归类，**只建立实际用到的子目录**。未改动的历史材料通过稳定路径引用，不复制成多份“最新基线”。

每版 README 应写明所依据的方案和 OpenSpec 变更、修改范围、验证结果及审批状态；涉及实施约束变化时，须先同步正式实施计划和 OpenSpec，不能仅靠新目录宣称契约生效。

## 7. 发布不可变性

方案版本形成后，旧版本目录及其内容作为历史快照保留：

- 不删除、覆盖或原地修订已发布文件。
- 修正或补充必须按相应的主/部分/小修订规则创建新目录，并保留对旧版本的引用。
- 发布清单应记录文件路径、内容哈希、OpenSpec 变更、工具链锁定信息和验证结果。
- 发布材料可以被读取和引用，但不能把后续评审意见直接写回旧发布目录。
- 未经发布的工作应放在新的迭代目录、变更分支或明确的候选状态中，不与不可变发布内容混合。

## 8. 提交边界

本次整理保留 `docs/v2/`、`solutions/1027V1/`、`design/` 和 `openspec/` 的现有内容与路径，仅把无其他入站引用的根目录参考图移入 `docs/references/diagrams/`。不添加凭据、会话原文或其他敏感数据。

P0-02 只改本文件、`README.md` 的链接和 `docs/delivery/source-reconciliation.md`。`docs/v2/`、`openspec/`、`.omo/`、`plan.md`、`docs/contracts/` 的内容同步属于 P0-03 及后续契约任务，不在本文件范围内。

## 9. 事实源冲突登记

1. 冲突的唯一登记表是 [`docs/delivery/source-reconciliation.md`](delivery/source-reconciliation.md)。任何代理在引用 `docs/v2/`、`openspec/`、历史归档或旧评审记录前，必须先核对该表。
2. 发现新的冲突时，先登记（编号、位置、已批准规则、解决动作、责任方），再改文档；不得静默删除旧表述，必须标注“历史/已取代”、日期和取代它的决定。
3. 索引文件（`README.md`、`docs/v2/README.md`、`openspec/changes/*/README.md`）只负责导航。索引与第 2 节冲突时，以第 2 节为准。
4. 状态口径：`已批准（用于规划）`不等于`已冻结`；`已冻结`不等于`已实现`；`已实现`不等于`已验证`。任何报告都必须写清处于哪一档。
