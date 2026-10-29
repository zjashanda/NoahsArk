# NoahsArk 文档索引

> 目录：`docs/v2`
>
> 更新日期：2026-10-28（规范同步）
>
> 适用阶段：历史方案与旧 UI 参考
>
> 当前闸门：以 [NoahsArk 平台交付总计划](../../.omo/plans/noahsark-platform-delivery.md) 为准；本目录不再单独定义执行闸门

## 规范同步说明（2026-10-28，P0-03）

> **本目录自 2026-10-28 起整体转为历史参考，不再是当前事实源。** 当前唯一执行主线是 [NoahsArk 平台交付总计划](../../.omo/plans/noahsark-platform-delivery.md)，当前契约候选是 [docs/contracts/README.md](../contracts/README.md)，规范优先级见 [docs/VERSIONING.md](../VERSIONING.md)。
>
> 本轮逐项修订、冲突清单、仍属历史的内容和验证结果见 [openspec 与 docs/v2 规范同步记录](../delivery/openspec-v2-sync.md)。
>
> 已批准要点：PostgreSQL 是唯一正式数据库；判定采用五轴并区分执行、设备、证据、判定状态；已启动的冻结压测在断线/心跳过期后继续离线执行，设备保持占用，重连先处理 STOP；设备释放、证据完整性和最终判定分离；缺失 `cleanup_receipt` 只阻断设备释放确认，不自动判定整条证据链不完整；旧的 81 项任务计划与旧 UI 基线均为历史。P0-03 不构成实现、测试、部署或验收通过。

---

## 1. 先读什么

**当前阅读顺序（2026-10-28 起）**：

1. [NoahsArk 平台交付总计划](../../.omo/plans/noahsark-platform-delivery.md)：唯一执行主线，包含 Phase 0–6 与当前下一步。
2. [docs/VERSIONING.md](../VERSIONING.md)：目录与事实源优先级。
3. [docs/contracts/README.md](../contracts/README.md)：字段级候选契约；与总计划/已批准草案冲突时以更高优先级事实源为准。
4. [openspec 与 docs/v2 规范同步记录](../delivery/openspec-v2-sync.md)：本轮如何修正旧文档、哪些内容仍是历史。

**历史阅读顺序（2026-10-26 基线，仅供追溯）**：

1. `SOLUTION.md`：平台定位、总体架构与旧路线图；其中 SQLite、单一终态、81 项计划等已被取代。
2. `IMPLEMENTATION-PLAN.md`：旧 81 项实施计划，历史参考；不得作为当前施工 WBS。
3. `../../openspec/changes/ai-test-platform-v2/proposal.md` 与 `design.md`：OpenSpec 变更边界；已加同步修正，不再是 81 任务口径。
4. `../../openspec/changes/ai-test-platform-v2/specs/`：按能力查看增量规格；完成门禁已补五轴与分离状态映射。
5. `UI-DESIGN.md`：旧 v2「航次档案」UI 基线，历史参考；Apple 风格 Phase 1 基线待冻结，见 `UI-DESIGN-APPLE.md`。

只关心历史产品定位时读 `SOLUTION.md` 第 1 至 3 节。只关心旧排期时读 `IMPLEMENTATION-PLAN.md` 第 6 至 14 节与本文第 2 节。只关心历史验收时读 `SOLUTION.md` 第 5、7、12 节。当前任务范围以总计划的 Phase 0–6 为准，不以本目录的 81 项计数为准。

---

## 2. v2 文档

| 文档 | 路径 | 状态 | 说明 |
|---|---|---|---|
| 总体方案 | `SOLUTION.md` | 历史（2026-10-28 起） | 产品愿景、角色宪章、架构、主流程、模块、机制、UI 信息架构、治理、路线图、风险、需求追溯；SQLite、单一终态、81 项计划已同步标注为历史 |
| 流程图规范 | `FLOWCHART-STYLE.md` | 历史（2026-10-28 起） | 一图一问、复杂度预算、形状与颜色约定、模板、反模式、来源链接；旧终态口径仅作历史 |
| 流程图产物 | `diagrams/` | 历史（2026-10-28 起） | 图 5-1 / 5-2 的 `.mmd`、SVG、PNG 与渲染校验记录；旧流程与旧终态，待 Phase 1/3 重绘 |
| 方案 PDF | `SOLUTION.pdf` | 历史（2026-10-28 起） | 35 页旧方案，内嵌旧图；不反映 PostgreSQL/五轴/离线续跑修正 |
| 流程图 PDF | `diagrams/FLOWCHARTS.pdf` | 历史（2026-10-28 起） | 两张旧流程图独立 PDF；仅作追溯 |
| 模块级实施设计 | `../../solutions/1027V1/MODULE-DESIGN.md` | 已生成，待评审 | 13 个模块、逐步骤契约、耦合矩阵、结果传导 |
| 模块级实施 PDF | `../../solutions/1027V1/MODULE-DESIGN.pdf` | 已生成 | 37 页，内嵌 13 张业务时序图 |
| 模块时序图 | `../../solutions/1027V1/sequences/` | 已生成 | 14 个时序 `.mmd` + 1 个远程拓扑图，均含 PNG 与索引 |
| 远程节点执行方案 | `../../solutions/1027V1/REMOTE-EXECUTION.md` | 已生成，待评审 | Linux 控制面、Windows 节点、设备本地执行、长轮询、证据回传 |
| 远程执行 PDF | `../../solutions/1027V1/REMOTE-EXECUTION.pdf` | 已生成 | 远程执行架构、技术栈、协议、状态机与验收 |
| 缺口关闭方案 | `../../solutions/1027V1/GAP-CLOSURE.md` | 已生成，待评审 | 5 个缺口的契约、验收、外部输入和 5 个新任务 |
| 缺口关闭 PDF | `../../solutions/1027V1/GAP-CLOSURE.pdf` | 已生成 | 5 个缺口的补齐方式、所需内容与 86 项计划建议 |
| 评审优化建议 | `../../solutions/1027V1/REVIEW-OPTIMIZATION.md` | 已生成，待评审 | 9 项采纳、3 项调整、2 项暂缓；M13/契约/门禁优化 |
| 评审优化 PDF | `../../solutions/1027V1/REVIEW-OPTIMIZATION.pdf` | 已生成 | 对 gpt6sol 12 节评审的取舍与计划增量 |
| V1 总流程图 | `../../solutions/1027V1/NOAHSARK-V1-TOTAL-FLOW.svg` | 已生成 | 1800×1500，阶段、边界、回环、门禁与异常 |
| V1 总流程图 PNG | `../../solutions/1027V1/NOAHSARK-V1-TOTAL-FLOW.png` | 已生成 | 可直接预览 |
| V1 总流程图 PDF | `../../solutions/1027V1/NOAHSARK-V1-TOTAL-FLOW.pdf` | 已生成 | A3 横向，适合评审/打印 |
| 实施计划 | `IMPLEMENTATION-PLAN.md` | 历史（2026-10-28 起） | D1 至 D13、旧冻结契约、旧 81 个复选框、验证波次；真实施工 WBS 由 Phase 3 产出 |
| UI 设计 | `UI-DESIGN.md` | 历史（2026-10-28 起） | 旧 v2 航次档案：品牌、站点地图、逐页规格、组件、断点、可访问性、交互说明 |
| Apple 风格对比版 | `UI-DESIGN-APPLE.md` | Phase 1 候选方向（未冻结） | v3 Quiet Instrument：白/浅灰、蓝色强调、编辑型排版、胶囊导航；Phase 1 将以此为基础冻结新 UI 基线 |
| UI 评审记录 | `UI-REVIEW.md` | 历史（2026-10-28 起） | 旧 v2 自检记录；Phase 1 重新做 Apple 风格视觉 QA 与用户评审 |
| 验收报告 | `ACCEPTANCE-REPORT.md` | 历史（2026-10-28 起） | 旧方案、旧 81 项任务、15 页旧原型硬校验；不代表当前范围或验收 |
| UI 原创性审计 | `UI-ORIGINALITY.md` | 部分历史（2026-10-28 起） | 旧平台引用清零与原创来源证据仍可参考；冻结对象改为 Phase 1 Apple 风格基线 |
| UI 线框 | `../../design/wireframes/` | 已存在，待评审 | 16 页线框，P7-00 产出 |
| 架构决策记录 | `adr/` | 规划中 | D1 至 D13 的上下文、决策与后果，P0-08 产出 |
| 执行手册 | `EXECUTION-RUNBOOK.md` | 规划中 | 波次门禁、回滚、执行步骤，P0-08 产出 |
| 功能开关 | `FEATURE-FLAGS.md` | 规划中 | 开关清单、默认值、启用条件，P0-08 产出 |
| 资深测试工程师角色 | `AI-SENIOR-TEST-ENGINEER.md` | 规划中 | 12 条原则与记分卡的正式版本，P4-13 产出 |
| 方案评审模板 | `review/PLAN-REVIEW.md` | 规划中 | 覆盖、oracle、可执行性、风险，P4-09 产出 |
| 用例评审模板 | `review/CASE-REVIEW.md` | 规划中 | 用例质量与证据要求，P4-09 产出 |
| 脚本评审模板 | `review/SCRIPT-REVIEW.md` | 规划中 | 脚本边界、副作用、幂等与恢复，P4-09 产出 |
| UI 质量报告 | `UI-QA.md` | 规划中 | 可访问性、响应式、视觉检查，P7-12 产出 |
| 升级手册 | `UPGRADE-PLAYBOOK.md` | 规划中 | 快照、staging、T1/T2、影子 T3、canary、回滚，P8-02 产出 |
| 真实 E2E 说明 | `REAL-E2E.md` | 规划中 | 设备选择、真实执行、证据目录，P8-03 产出 |
| 用户指南 | `USER-GUIDE.md` | 规划中 | 任务、模型、推送、接管、知识治理，P8-09 产出 |
| API 文档 | `API.md` | 规划中 | v2 端点与权限，P8-09 产出 |
| 架构说明 | `ARCHITECTURE.md` | 规划中 | 面向维护者的架构与边界，P8-09 产出 |
| 交付说明 | `DELIVERY.md` | 规划中 | 目标、非目标、需求追溯、证据清单，P8-09 产出 |

---

## 3. OpenSpec 变更

| 文档 | 路径 | 状态 | 说明 |
|---|---|---|---|
| 变更说明 | `../../openspec/changes/ai-test-platform-v2/README.md` | 活跃变更；已加同步说明 | 需求追溯与旧任务计数；81 条仅为历史账本 |
| 提案 | `../../openspec/changes/ai-test-platform-v2/proposal.md` | 活跃变更；已加同步说明 | 为什么变更、变更什么、影响范围；SQLite 与 81 任务口径已修正 |
| 设计 | `../../openspec/changes/ai-test-platform-v2/design.md` | 活跃变更；已加同步说明 | D1 至 D13、契约、迁移、安全、验证；已补 PostgreSQL、五轴、C1–C7/L0–L5/T1–T6 映射 |
| 任务 | `../../openspec/changes/ai-test-platform-v2/tasks.md` | 活跃变更；历史任务账本 | 81 条为 2026-10-26 计划快照，不代表当前范围；Phase 3 将产出新 WBS |
| 模型策略 | `../../openspec/changes/ai-test-platform-v2/specs/model-policy/spec.md` | 已存在 | 运行时模型策略 |
| 事件与推送 | `../../openspec/changes/ai-test-platform-v2/specs/platform-events-push/spec.md` | 已存在 | 事件日志与主动推送 |
| 知识检索 | `../../openspec/changes/ai-test-platform-v2/specs/knowledge-retrieval/spec.md` | 已存在 | 证据范围内的检索 |
| 任务 playbook | `../../openspec/changes/ai-test-platform-v2/specs/task-playbook/spec.md` | 已存在 | 终态任务 playbook |
| 完成门禁 | `../../openspec/changes/ai-test-platform-v2/specs/completion-gate/spec.md` | 已存在 | 二值完成契约 |
| 接管会话 | `../../openspec/changes/ai-test-platform-v2/specs/takeover-session/spec.md` | 已存在 | 受围栏接管 |
| 工具链兼容 | `../../openspec/changes/ai-test-platform-v2/specs/toolchain-compatibility/spec.md` | 已存在 | 版本锁与冒烟 |
| Agent 治理 | `../../openspec/changes/ai-test-platform-v2/specs/agent-openspec-config/spec.md` | 已存在 | 生成配置与写入守卫 |
| UI v2 | `../../openspec/changes/ai-test-platform-v2/specs/ui-v2/spec.md` | 已存在 | 控制台 UI |

---

## 4. 输入材料

以下文档是产品意图、知识分类和方法论来源，不是当前契约。发生冲突时以 [NoahsArk 平台交付总计划](../../.omo/plans/noahsark-platform-delivery.md)、[docs/contracts/README.md](../contracts/README.md) 和已批准的 `.omo/drafts` 正文为准；旧实施计划与旧 OpenSpec 任务账本只作历史参考。

| 文档 | 路径 | 用途 |
|---|---|---|
| 平台总体方案 | `../../../laodengAi/csjh/2026-10-26/00_平台总体方案.md` | 产品定位、主流程、分层、模块、讨论插件、分阶段路线 |
| 知识库分类方案 | `../../../laodengAi/csjh/2026-10-26/01_知识库分类方案.md` | 27 个仓库审计、工具库与项目库分类、检索口径 |
| 需求到脚本 | `../../../laodengAi/knowledge/project/validation-methods/00_需求到测试到脚本落地.md` | 功能点建模、验证池匹配、门禁、回灌 |
| 脚本与工程 | `../../../laodengAi/knowledge/project/validation-methods/01_脚本与工程逻辑构建.md` | 分层、职责边界、幂等、证据、编码 |
| 验证正确性 | `../../../laodengAi/knowledge/project/validation-methods/02_验证正确性审核.md` | 证据优先级、结果状态、14 步 FAIL 收敛 |
| 验证池与工具 | `../../../laodengAi/knowledge/project/validation-methods/03_验证池与工具选择.md` | 16 个注册模块、工具选型、元数据 |
| Trisolaris 与 Polaris | `../../../laodengAi/knowledge/project/validation-methods/04_Trisolaris_Polaris_深度知识.md` | 验证池、IR、Event Runtime、Event Graph、Coverage、回灌 |
| 美的空调方法 | `../../../laodengAi/knowledge/project/validation-methods/05_美的空调项目测试方法.md` | 需求入池、矩阵、JSON 用例、质检、真机门禁 |
| 术语总表 | `../../../laodengAi/knowledge/project/glossary/00_术语总表_详细版.md` | 术语、测试焦点、状态定义、工程使用规则 |
| 实施计划镜像 | `../../../.omo/plans/ai-test-platform-v2.md` | 与 `IMPLEMENTATION-PLAN.md` 内容一致 |

---

## 5. 文档规则

1. 工程决策以 [NoahsArk 平台交付总计划](../../.omo/plans/noahsark-platform-delivery.md) 和 [docs/contracts/README.md](../contracts/README.md) 为准；`docs/v2` 与 `openspec` 中未经同步的旧表述只作历史参考。`SOLUTION.md` 负责统一叙述，不新增契约。
2. 新增或改名文档后，同步更新本索引、`SOLUTION.md` 附录 B 和 [规范同步记录](../delivery/openspec-v2-sync.md)。
3. UI 页面与视觉规格以 Phase 1 冻结的 Apple 风格基线为准；旧 `UI-DESIGN.md` 与旧线框只作历史参考，`SOLUTION.md` 不复制完整规格。
4. 所有文档使用 UTF-8 中文；命令、路径、字段名保留英文原文。
5. 不写入 secret、token、真实凭据、客户敏感数据或大体积二进制证据。
6. 状态标记统一使用：历史、活跃变更、Phase 1 候选（未冻结）、规划中、外部输入、待同步。不再使用“已存在，待评审”暗示旧文档仍是当前基线。

---

## 6. 已知缺口

| 缺口 | 影响 | 处理 |
|---|---|---|
| 旧 `UI-DESIGN.md` 已被取代 | 旧 v2 视觉基线不能作为实现依据 | Phase 1 以 `UI-DESIGN-APPLE.md` 为候选起点，完成研究、IA、设计系统、线框、原型、响应式与视觉 QA 后冻结新基线 |
| 旧 81 项计划被当作完整范围 | 任务计数与当前 1–6 阶段范围冲突 | 标记为历史；Phase 3 产出真实施工 WBS，不在 P0-03 发明新任务数 |
| C8“测试之测试”只有占位 | 测试自身有效性尚无验收标准 | 方案方向确认后由后续任务定义，当前不参与五轴判定 |
| ADR、运行手册、评审模板尚未编写 | 实现阶段缺少正式操作文档 | 按总计划 Phase 2/3 产出 |
| `tmpskill` 目录级知识审计未完成 | 首批知识摄取范围不确定 | 单独审计后再决定纳入清单 |
| 平台自我迭代未纳入当前范围 | 设置模块能力边界不完整 | 作为后续版本单独决策 |
