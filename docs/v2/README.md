# NoahsArk 文档索引

> 目录：`docs/v2`
>
> 更新日期：2026-10-26
>
> 适用阶段：方案与 UI 设计评审期
>
> 当前闸门：方案与 UI 设计获批前，不进入产品实现

---

## 1. 先读什么

建议按以下顺序阅读。

入口文档：[`SOLUTION.md`](./SOLUTION.md)、[`IMPLEMENTATION-PLAN.md`](./IMPLEMENTATION-PLAN.md)、[`UI-DESIGN.md`](./UI-DESIGN.md)（已存在，待评审）。

1. `SOLUTION.md`：先看平台为什么存在、角色宪章、总体架构、主流程和路线图。
2. `IMPLEMENTATION-PLAN.md`：再看决策完整版实施计划，确认契约、门禁、任务和验收方式。
3. `../../openspec/changes/ai-test-platform-v2/proposal.md` 与 `design.md`：确认变更边界和 D1 至 D13。
4. `../../openspec/changes/ai-test-platform-v2/specs/`：按能力查看增量规格。
5. `UI-DESIGN.md`：查看品牌、站点地图、逐页规格、组件、断点和可访问性。

只关心产品定位时读 `SOLUTION.md` 第 1 至 3 节。只关心实现排期时读 `IMPLEMENTATION-PLAN.md` 第 6 至 14 节与本文第 2 节。只关心验收时读 `SOLUTION.md` 第 5、7、12 节。

---

## 2. v2 文档

| 文档 | 路径 | 状态 | 说明 |
|---|---|---|---|
| 总体方案 | `SOLUTION.md` | 已生成，待评审 | 产品愿景、角色宪章、架构、主流程、模块、机制、UI 信息架构、治理、路线图、风险、需求追溯 |
| 流程图规范 | `FLOWCHART-STYLE.md` | 已生成，待评审 | 一图一问、复杂度预算、形状与颜色约定、模板、反模式、来源链接 |
| 流程图产物 | `diagrams/` | 已生成 | 图 5-1 / 5-2 的 `.mmd`、SVG、PNG 与渲染校验记录 |
| 方案 PDF | `SOLUTION.pdf` | 已生成 | 35 页完整方案，内嵌图 5-1 / 5-2，不依赖 Mermaid 渲染器 |
| 流程图 PDF | `diagrams/FLOWCHARTS.pdf` | 已生成 | 两张流程图独立 PDF，适合直接投屏/评审 |
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
| 实施计划 | `IMPLEMENTATION-PLAN.md` | 已存在，决策基线 | D1 至 D13、冻结契约、81 个复选框、验证波次 |
| UI 设计 | `UI-DESIGN.md` | 已存在，待评审 | v2 航次档案：品牌、站点地图、逐页规格、组件、断点、可访问性、交互说明 |
| Apple 风格对比版 | `UI-DESIGN-APPLE.md` | 已生成，待用户评审 | v3 Quiet Instrument：白/浅灰、蓝色强调、编辑型排版、胶囊导航；独立 15 页原型 |
| UI 评审记录 | `UI-REVIEW.md` | 已生成自检，待用户评审 | 用户评审结论、修改项与批准记录，P7-00 配套 |
| 验收报告 | `ACCEPTANCE-REPORT.md` | 已生成 | 方案、81 项任务、15 页原型、浏览器与知识检索硬校验 |
| UI 原创性审计 | `UI-ORIGINALITY.md` | 已生成，待复核 | 旧平台引用清零、原创设计来源与 grep 证据 |
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
| 变更说明 | `../../openspec/changes/ai-test-platform-v2/README.md` | 已存在 | 需求追溯与任务计数 |
| 提案 | `../../openspec/changes/ai-test-platform-v2/proposal.md` | 已存在 | 为什么变更、变更什么、影响范围 |
| 设计 | `../../openspec/changes/ai-test-platform-v2/design.md` | 已存在 | D1 至 D13、冻结契约、迁移、安全、验证 |
| 任务 | `../../openspec/changes/ai-test-platform-v2/tasks.md` | 已存在，已同步 | 81 条，与实施计划一致 |
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

以下文档是产品意图、知识分类和方法论来源，不是 v2 契约。发生冲突时以实施计划和 OpenSpec 为准。

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

1. 工程决策以 `IMPLEMENTATION-PLAN.md` 和 OpenSpec 为准。`SOLUTION.md` 负责统一叙述，不新增契约。
2. 新增或改名文档后，同步更新本索引和 `SOLUTION.md` 附录 B。
3. UI 页面与视觉规格只在 `UI-DESIGN.md` 和线框中维护，`SOLUTION.md` 不复制完整规格。
4. 所有文档使用 UTF-8 中文；命令、路径、字段名保留英文原文。
5. 不写入 secret、token、真实凭据、客户敏感数据或大体积二进制证据。
6. 状态标记统一使用：已存在、已生成待评审、并行编写中、规划中、外部输入、待同步。

---

## 6. 已知缺口

| 缺口 | 影响 | 处理 |
|---|---|---|
| `UI-DESIGN.md` 已落盘，用户评审未完成 | P7 仍不能启动 | 完成用户评审并批准 `UI-REVIEW.md`；16 页线框、原型、tokens、logo 已落盘待验 |
| C8“测试之测试”只有占位 | 测试自身有效性尚无验收标准 | 方案方向确认后由 P4-12 定义，当前不参与 PASS/FAIL |
| ADR、运行手册、评审模板尚未编写 | 实现阶段缺少正式操作文档 | 按 Phase 0 与 Phase 4 任务产出 |
| `tmpskill` 目录级知识审计未完成 | 首批知识摄取范围不确定 | 单独审计后再决定纳入清单 |
| 平台自我迭代未纳入 v2 任务 | 设置模块能力边界不完整 | 作为后续版本单独决策 |
