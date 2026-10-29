# NoahsArk UI 基线差距分析（UI Baseline Gap Analysis）

> 版本：v0.2（2026-10-29 按独立核验 F1–F9 修正事实与引用；仍为分析稿，不是 UI 批准）
> 状态：分析稿，供 Phase 1 UI 基线与 P1-02 信息架构评审使用。不是 UI 设计冻结件，不是实施授权，也不代表最终 UI 评审通过。修正记录见 [`ui-baseline-gap-verification.md`](./ui-baseline-gap-verification.md) 第 7 节。
> 范围：现有 `design/`、`docs/v2/UI-DESIGN*.md`、`docs/v2/UI-REVIEW.md`、线框与烟测证据，对照已评审的第一至第六步方案与当前字段级候选契约，给出旧 15 路由 / 11 导航 IA 的处置意见、新的 10 至 12 区域 IA、屏幕清单、状态模型、追溯、可访问性与风险。
> 非授权边界：本文不修改 `design/` 或 `docs/v2/`，不写产品代码，不修改 `.omo` 状态、`plan.md`、契约或 `docs/ssh.txt`，不提交、不推送，不宣称任何 UI 已实现、已测试或已通过验收。
> 事实源优先级：按 [`docs/VERSIONING.md`](../VERSIONING.md) 第 2 节执行。`docs/v2/` 自 2026-10-28 起整体为历史参考；UI 新基线尚未冻结。

---

## 0. 一页结论

1. **旧 UI 不是从零推翻，而是“视觉可继承、IA 必须重组”**。`design/` 已经提供可用的设计令牌、外壳、15 页线框、两套可点击原型和冒烟证据；但旧 IA 以“单状态 + C1–C7”表达任务，和当前“五轴 + 分离事实 + task/revision/run/case/attempt”的模型存在结构性缺口。
2. **旧 11 个一级导航过宽、任务详情 11 个页签过碎**。旧导航把“思考、推送、Agent、圆桌”都提升为一级入口，却没有给“运行、证据、报告、审计/恢复”独立位置；任务详情把审批、门禁、结论、知识、相似、接管、日志并列，导致核心主线被工具页淹没。
3. **建议新 IA 为 12 个区域**：Mission Control、Intake & Revisions、Tasks、Runs & Attempts、Evidence & Verdict、Devices & Nodes、Reports & Delivery、Knowledge、Runtime & Toolchain、Agents & Reviews、Audit & Recovery、Settings & Access。任务详情从 11 页签收敛为 8 个子视图，审批与门禁、运行与尝试、证据清单、结论与设备释放分别可见。
4. **状态不是六类，而是十二类**。除 loading / empty / error / blocked / stale / offline 外，必须显式定义 partial-evidence、no-permission、draining、quarantined、reconciling、unknown-progress。尤其 offline 不得被渲染为“已停止”或“设备空闲”。
5. **现有证据只证明静态渲染与导航可达**。两套原型均明确是 MOCK DATA，未接 API；没有十二类状态 fixture，没有真实屏幕阅读器、axe、200% 缩放、高对比度、全局深色模式或真实设备证据。
6. **最大风险不是视觉，而是语义**：如果 UI 继续用单一状态徽章、旧 C1–C7 或“已接收 = 已核验”“离线 = 空闲”“释放 = 通过”的措辞，会直接违反 fail-closed、证据隔离和 AC-10 至 AC-13。
7. **本文不给出最终 UI 批准**。它给出的是可评审的 IA 与差距清单；Phase 1 仍需冻结设计令牌、导航、页面规格、状态 fixture、可访问性与深色模式决策。

---

## 1. 阅读范围与事实源

### 1.1 已读来源

| 类别 | 路径 | 用途 |
|---|---|---|
| 执行主线 | [`../../.omo/plans/noahsark-platform-delivery.md`](../../.omo/plans/noahsark-platform-delivery.md) | Phase 0–6、P1-02/P1-04 页面范围、当前闸门 |
| 评审决策日志 | [`../../plan.md`](../../plan.md) | AC-1 至 AC-14、环境/交付/恢复/五轴/离线续跑批准记录 |
| 需求基线 | [`../../.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md`](../../.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md) | REQ-01..REQ-16、角色、任务/修订/运行、证据与判定 |
| 架构 | [`../../.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md`](../../.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md) | CP-01..CP-13、五轴、门禁、租约、审计 |
| 模块设计 | [`../../.omo/drafts/01-design/noahsark-v0.0.1-module-design.md`](../../.omo/drafts/01-design/noahsark-v0.0.1-module-design.md) | M-01..M-21、Case 管理、会话桥 |
| 技术雷达 | [`../../.omo/drafts/01-design/noahsark-v0.0.1-tech-radar.md`](../../.omo/drafts/01-design/noahsark-v0.0.1-tech-radar.md) | 控制面、节点、证据、审计选型 |
| 施工与验收 | [`../../.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md`](../../.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md) | A-0..A-9、L0–L5、AC-1..AC-14 |
| 测试策略 | [`../../.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md`](../../.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md) | T1–T6、异常与恢复矩阵、语音判定 |
| 优化路线 | [`../../.omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md`](../../.omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md) | P0–P3、可观测性、恢复、技术债 |
| 候选契约 | [`../contracts/domain.md`](../contracts/domain.md) | Task / Revision / Approval / Gate / Case / Run / Attempt / Lease / Receipt |
| 候选契约 | [`../contracts/evidence-verdict.md`](../contracts/evidence-verdict.md) | manifest、证据状态、清理回执、设备占用与释放、五轴 |
| 候选契约 | [`../contracts/ui-report-knowledge-audit.md`](../contracts/ui-report-knowledge-audit.md) | TaskCard、报告、知识候选/条目、审计、访问级别 |
| 旧 UI 规范 | [`../v2/UI-DESIGN.md`](../v2/UI-DESIGN.md) | 15 页规格、11 导航、11 页签、C1–C7、旧状态矩阵 |
| Apple 候选 | [`../v2/UI-DESIGN-APPLE.md`](../v2/UI-DESIGN-APPLE.md) | Quiet Instrument 视觉层、同路由对照 |
| UI 自检 | [`../v2/UI-REVIEW.md`](../v2/UI-REVIEW.md) | v2 渲染、交互、可访问性与缺口 |
| 原创性 | [`../v2/UI-ORIGINALITY.md`](../v2/UI-ORIGINALITY.md) | 旧平台复用声明与原创证据 |
| 验收报告 | [`../v2/ACCEPTANCE-REPORT.md`](../v2/ACCEPTANCE-REPORT.md) | 旧 UI 硬校验与“未验收事项” |
| 旧方案 UI | [`../v2/SOLUTION.md`](../v2/SOLUTION.md) | 第 8 节旧 UI 概览；第 5.4 节五轴同步说明 |
| 旧实施计划 | [`../v2/IMPLEMENTATION-PLAN.md`](../v2/IMPLEMENTATION-PLAN.md) | P7-00..P7-13 旧 UI 任务与验收 |
| 线框 | [`../../design/wireframes/README.md`](../../design/wireframes/README.md) | 15 页线框索引与全局外壳 |
| 原型与证据 | `design/` 目录 | 令牌、原型、截图、烟测 JSON |

### 1.2 “已评审的第一至第六步”指什么

本文把 `plan.md` 中已逐项确认的六步方案作为“已评审 1–6 方案”：

1. 第一步：已批准需求基线（`.omo/drafts/00-baseline`）。
2. 第二步：架构方案与 B-1..B-7 边界（`.omo/drafts/01-design`）。
3. 第三步：模块业务逻辑 M-01..M-21、字段级契约第 1–5 项。
4. 第四步：施工与验收 A-0..A-9、AC-1..AC-14、L0–L5/T1–T6。
5. 第五步：测试策略 S5-1..S5-4 与补充测试组。
6. 第六步：优化边界、可观测性、运维恢复、版本路线、技术债与批准门。

这些记录说明“方案与验收准则已评审”，不表示 UI 已设计冻结、契约已冻结、功能已实现或测试已执行。`docs/v2/` 的 81 项计划、SQLite、单一终态和旧 UI 基线均为历史参考。

### 1.3 本文使用的判断口径

- **权威状态 vs 投影**：Task、Revision、Approval、Gate、Run、Attempt、Case、Verdict、Lease、Evidence、Knowledge、Audit 由 Linux 控制面权威写入；TaskCard、UI 列表、报告默认视图是投影，不得成为第二事实源。
- **五轴优先**：`execution_status` / `validity_status` / `business_verdict` / `evidence_status` / `verification_status` 独立显示，禁止折叠成一个状态。
- **分离事实**：执行状态、通信状态、设备占用、证据完整性、设备释放、最终判定分别建模、分别展示。
- **fail-closed**：缺批准、缺指标、缺必要证据、缺追溯、缺独立复核时，UI 不得显示 PASS 或“完成”。
- **未知即未知**：总量未知时 `percent=null`，显示“未知”，不得用 0%、99% 或阶段序号冒充。

---

## 2. 现有 UI 资产清单

### 2.1 `design/` 目录

| 资产 | 路径 | 规模/内容 | 当前价值 | 限制 |
|---|---|---|---|---|
| v2 设计令牌 | [`../../design/design-tokens.json`](../../design/design-tokens.json) | 12 个顶层分组；浅色“航次档案”基线 | 可映射为 `--na-*`；颜色/间距/字号完整 | 只有浅色；旧品牌色；未覆盖五轴和设备状态 |
| v2 原型 | [`../../design/ui-prototype.html`](../../design/ui-prototype.html) | 单文件；15 路由；11 导航；11 任务页签；mock | 可点击验证旧 IA；无 CDN | 静态 mock；C1–C7 与单状态口径 |
| v2 线框 | `design/wireframes/01-overview.md` 至 `15-system.md` + `README.md` | 16 个文件；ASCII 结构 + 状态 + 响应式 | 页面结构、状态说明、全局图例 | 旧 IA；未覆盖 revision/run/attempt/manifest |
| v2 截图 | `design/preview/*.png` | overview / task-detail 与视口外壳（desktop-1440、tablet-768、phone-390）共 7 张；不含 models | 视觉基线对照 | 不代表真实数据或全部页面 |
| v2 烟测 | [`../../design/preview/ui-smoke-result.json`](../../design/preview/ui-smoke-result.json) | 11 nav + 4 detail 可达；响应式外壳覆盖 3 视口；0 console/page error；0 外链；0 溢出 | 证明静态渲染与导航可达 | 逐路由三视口明细未保存在该 JSON；无状态 fixture、无 API、无 a11y 实测 |
| Apple 令牌 | [`../../design/apple/design-tokens.json`](../../design/apple/design-tokens.json) | `--naa` 语义令牌；白/浅灰 + 单蓝 | Phase 1 候选视觉方向 | 只有浅色；与 v2 令牌并存 |
| Apple 原型 | [`../../design/apple/ui-prototype.html`](../../design/apple/ui-prototype.html) | 与 v2 同 15 路由/11 导航；只换视觉与外壳 | 可并排比较；交互 22 项通过 | 仍是 mock；未改旧 IA |
| Apple 截图 | `design/apple/preview/*.png` | overview/task-detail/models 的 7 张 | 视觉对照 | 同上 |
| Apple 烟测 | [`../../design/apple/ui-smoke-result.json`](../../design/apple/ui-smoke-result.json) | `routeCount=15`、`navCount=11`；45/45 通过；0 error/external/overflow | 最完整的静态烟测证据 | 无真实状态与 API |
| 品牌标识 | [`../../assets/brand/ark-logo.svg`](../../assets/brand/ark-logo.svg) | 64×64 原创 SVG | 可复用 | 需在新外壳中重新校色 |

### 2.2 `docs/v2/UI-DESIGN*.md` 与评审文档

| 文档 | 规模 | 状态 | 对本文的作用 |
|---|---|---|---|
| [`../v2/UI-DESIGN.md`](../v2/UI-DESIGN.md) | 约 181 KB | 历史/已取代（2026-10-28） | 旧 IA 的权威描述：15 页、11 导航、11 页签、C1–C7、旧状态矩阵 |
| [`../v2/UI-DESIGN-APPLE.md`](../v2/UI-DESIGN-APPLE.md) | 约 33 KB | Phase 1 候选方向（未冻结） | 视觉层候选；明确“不重写 IA、不减少事实” |
| [`../v2/UI-REVIEW.md`](../v2/UI-REVIEW.md) | 约 16 KB | 历史/已取代 | v2 自检：36 次渲染、交互、可访问性缺口、P0/P1 已知问题 |
| [`../v2/UI-ORIGINALITY.md`](../v2/UI-ORIGINALITY.md) | 约 9 KB | 部分历史 | 原创性声明仍可参考；冻结对象改为 Phase 1 Apple 基线 |
| [`../v2/ACCEPTANCE-REPORT.md`](../v2/ACCEPTANCE-REPORT.md) | 约 7 KB | 历史/已取代 | 旧 UI 硬校验与“明确未验收事项” |
| [`../v2/SOLUTION.md`](../v2/SOLUTION.md) | 约 86 KB | 历史参考 | 第 8 节旧页面职责；第 5.4 节五轴同步说明 |
| [`../v2/IMPLEMENTATION-PLAN.md`](../v2/IMPLEMENTATION-PLAN.md) | 约 80 KB | 历史参考 | P7-00..P7-13 旧 UI 任务与验收口径 |
| [`../v2/wireframes/README.md`](../v2/wireframes/README.md) | 25 行 | 指针 | 指回 `design/wireframes/`，避免两份线框漂移 |

### 2.3 线框清单

| # | 线框 | 旧路由 | 旧一级导航 | 新 IA 去向 |
|---|---|---|---|---|
| 01 | `01-overview.md` | `/aitest` | 总览 | MC-01 |
| 02 | `02-tasks.md` | `/aitest/tasks` | 任务 | TK-01 |
| 03 | `03-task-detail.md` | `/aitest/tasks/<id>` | 任务 | TK-02..TK-09 |
| 04 | `04-think.md` | `/aitest/think` | 思考 | IN-01..IN-03 |
| 05 | `05-knowledge.md` | `/aitest/knowledge` | 知识 | KN-01 |
| 06 | `06-knowledge-detail.md` | `/aitest/knowledge/<id>` | 知识 | KN-02 |
| 07 | `07-nodes.md` | `/aitest/nodes` | 节点与设备 | DV-01 |
| 08 | `08-node-detail.md` | `/aitest/nodes/<id>` | 节点与设备 | DV-03（设备详情另设 DV-02） |
| 09 | `09-models.md` | `/aitest/models` | 模型 | RT-01 |
| 10 | `10-toolchain.md` | `/aitest/system/toolchain` | 工具链与版本 | RT-02 |
| 11 | `11-push.md` | `/aitest/push` | 推送 | ST-03（降级为设置子页） |
| 12 | `12-agents.md` | `/aitest/agents` | Agent | AG-01/AG-02 |
| 13 | `13-roundtable.md` | `/aitest/roundtable` | 圆桌 | AG-03（评审会话） |
| 14 | `14-takeover.md` | `/aitest/tasks/<id>/takeover` | 接管（详情） | TK-08 全屏模式 |
| 15 | `15-system.md` | `/aitest/system` | 系统 | AU-01..AU-03 + ST-01..ST-04 |

### 2.4 烟测与截图证据

| 证据 | 路径 | 已证明 | 未证明 |
|---|---|---|---|
| v2 烟测 | `design/preview/ui-smoke-result.json` | 11 个导航 + 4 个详情可达；响应式外壳覆盖 3 视口（`responsive` 数组记录 desktop/tablet/phone 的 `scrollWidth`/`hOverflow`/导航状态）；0 console/page error；0 外部请求；0 横向溢出 | 逐路由三视口数据未保存在该 JSON；页面状态、真实 API、a11y、深色模式、性能 |
| Apple v3 烟测 | `design/apple/ui-smoke-result.json` | 15 路由 × 3 视口 = 45/45；0 error/external/overflow；截图 7 张 | 同上；另未覆盖 12 类状态 |
| v2 评审记录 | `docs/v2/UI-REVIEW.md` | 交互 10 项（导航、手机抽屉、接管模式、任务页签、模型切换、版本漂移、推送测试、批准计划、命令面板、实时状态）；页面覆盖 15；状态部分覆盖；可访问性自查 | 屏幕阅读器、axe、高对比度、200% 缩放；其中“12 条主路由 × 3 视口 = 36 次渲染”是文档声明，未在 v2 烟测 JSON 中留逐路由明细 |
| Apple 说明 | `docs/v2/UI-DESIGN-APPLE.md` 第 12 节 | 22 项交互检查、45/45 冒烟、7 张截图 | WCAG AA 认证、深色模式、真实后端 |
| 旧验收报告 | `docs/v2/ACCEPTANCE-REPORT.md` | 旧 UI 硬校验与未验收事项 | 当前范围与当前验收 |

**证据一致性问题**：`UI-REVIEW.md` 2.2 写“12 条主路由、36 次渲染”，而 `design/preview/ui-smoke-result.json` 记录 11 个 nav + 4 个 detail，且三者不是同一计数口径：JSON 的 `navResults`/`detailResults` 是单次记录、无 `viewport` 字段，只有 `responsive` 数组记录 desktop/tablet/phone 三档外壳；因此“36 次渲染”是文档声明，不能由该 JSON 复核。`ACCEPTANCE-REPORT.md` 写 15 页。Phase 1 必须统一“路由清单 = 导航项 + 详情路由”的机器可读清单，并把视口维度写入每条结果，否则“全部通过”不可复核。

### 2.5 资产处置总原则

- **可继承**：设计令牌结构、外壳高度节奏、桌面/平板/手机断点、门禁印章、任务卡、证据列表、知识治理侧栏（候选/争议/陈旧/待合并计数与“不自动批准”文案）、空/错误/加载状态、烟测脚本方法、原创 SVG 资产。
- **必须重写**：IA、导航分组、任务详情页签、状态模型、五轴矩阵、运行/尝试视图、证据 manifest 视图、设备释放/对账视图、审计/恢复视图。
- **不得继承**：把 C1–C7 当作当前判定模型；用单一状态徽章表达任务；把“预检通过”或“mock”当作完成证据；把 11 个入口固定为不可变结构。

---

## 3. 旧 15 路由 / 11 导航 IA 评估

### 3.1 旧结构

旧 IA 为：

```text
11 个一级导航：总览 / 任务 / 思考 / 知识 / 节点与设备 / 模型 / 工具链与版本 / 推送 / Agent / 圆桌 / 系统
15 个路由：上述 11 个 + 任务详情 / 知识详情 / 节点详情 / 接管
任务详情 11 个页签：概要 / 计划 / 用例 / 执行 / 证据 / 结论 / 门禁 / 知识 / 相似 / 接管 / 日志
```

旧模型的核心表达是“任务阶段 + 单一状态徽章 + C1–C7 门禁”。它与当前模型的结构性差距如下。

### 3.2 结构性差距

| 维度 | 旧 IA | 当前模型 | UI 后果 |
|---|---|---|---|
| 身份 | 以任务为中心 | Task → Revision → Run → Case → Attempt | 旧页面没有修订谱系、运行与尝试层级；用例页签混合了计划与结果 |
| 判定 | 单一状态 + C1–C7 | 五轴 + 分离事实 | 旧“通过/不通过”徽章会掩盖 validity/evidence/verification |
| 审批 | “批准计划”动作 | Approval 绑定冻结修订与范围快照 | 缺少审批意见、范围快照、超时/升级、审批人身份 |
| 运行 | “执行”页签 | static / smoke / formal 独立 run；attempt 独立 | 烟测与正式可能被同一视图混淆，分母不可解释 |
| 证据 | “证据”页签 | EvidenceSet / manifest / item / 摘要 / 部分上传 | 缺少 manifest 结构、部分证据、已接收 vs 已核验、访问级别 |
| 设备 | 节点/租约 | Node / Device / Lease / occupancy / draining / quarantined | 缺少设备释放前置、占用对账、离线仍占用、隔离恢复 |
| 断线 | 全局“降级/离线” | offline continuation + STOP-first + reconcile | 旧 UI 没有待 STOP 队列、补传/去重/对账、旧 epoch 语义 |
| 报告 | 隐含在“结论/导出” | 冻结报告 + 14 章节 + 分母口径 + 访问分级 | 缺少报告版本、默认披露、证据索引、受限材料 |
| 知识 | 知识页 + 详情 | Candidate → Review → Promote/Reject → Item 生命周期 | 旧 UI 已有治理侧栏（“候选 24 / 有争议 3 / 陈旧 18 / 待合并 5”）、“候选不会自动 approved”文案（`design/ui-prototype.html:2270`）与“需要人处理，不自动批准”“需角色 4 + 理由 + review receipt”约束（同文件 `:2394`、`:2421`）；但没有独立的候选生命周期页（PROPOSED→UNDER_REVIEW→APPROVED→PROMOTED），也没有完整的权限/状态机 |
| 审计/恢复 | 系统设置内的审计 + 存储卡备份入口 | 不可变审计 + 恢复顺序 + 备份演练 | 旧 UI 只有设置内的审计与备份按钮，没有恢复顺序、恢复演练和占用对账页 |
| 导航 | 11 个平级入口 | 任务主线、证据主线、设备主线、知识主线、治理主线 | 运行、证据、报告、审计没有一级位置；思考/推送/圆桌占用一级注意力 |

### 3.3 旧 15 页逐项处置

| # | 旧页面 | 旧路由 | 处置 | 新落点 | 理由 |
|---|---|---|---|---|---|
| 1 | 总览 | `/aitest` | **复用骨架 + 合并 + 扩展** | MC-01 | 保留“平台健康 + 待决断”结构；增加离线运行、待 STOP、对账中、隔离设备、证据不完整 |
| 2 | 任务列表 | `/aitest/tasks` | **复用 + 重排列** | TK-01 | 任务行必须显示 revision、run mode、五轴摘要、占用、证据进度；不再只有一个状态 |
| 3 | 任务详情 | `/aitest/tasks/<id>` | **复用外壳 + 重组页签** | TK-02..TK-09 | 11 页签收敛为 8 子视图；审批/门禁/运行/证据/结论分离；相似并入知识 |
| 4 | 思考/受理台 | `/aitest/think` | **复用表单 + 改名** | IN-01..IN-03 | “思考”不是领域对象；改为 Intake & Revisions，承接三入口、草稿、修订种子 |
| 5 | 知识检索 | `/aitest/knowledge` | **复用 + 扩展** | KN-01 | 保留检索/过滤/冲突/陈旧与侧栏治理队列；把侧栏治理队列提升为 KN-03 独立页并补齐生命周期 |
| 6 | 知识详情 | `/aitest/knowledge/<id>` | **复用 + 扩展** | KN-02 | 增加来源链、候选晋升、引用格式、自动推广禁止说明；旧详情已有溯源（来源任务/作者/证据/评审回执）与治理动作，可在其上扩展而非从零建设 |
| 7 | 节点与设备 | `/aitest/nodes` | **复用 + 扩展** | DV-01 | 增加 occupancy、lease、draining、quarantined、待对账、释放确认 |
| 8 | 节点详情 | `/aitest/nodes/<id>` | **复用 + 拆分** | DV-03 / DV-02 | 节点（Session 0、spool、心跳）与设备（端点、占用、释放）分开 |
| 9 | 模型 | `/aitest/models` | **合并** | RT-01 | 模型绑定与运行时同属“谁在执行”；减少一级入口 |
| 10 | 工具链与版本 | `/aitest/system/toolchain` | **合并** | RT-02 | 与模型同属 Runtime & Toolchain；保留 lock/drift/smoke |
| 11 | 推送 | `/aitest/push` | **降级/延后** | ST-03 | 推送是通知配置，不是任务主线；V0.0.1 先保留设置子页 |
| 12 | Agent | `/aitest/agents` | **复用 + 合并** | AG-01/AG-02 | 保留注册表、模型策略、写范围、审查 |
| 13 | 圆桌 | `/aitest/roundtable` | **合并 + 延后** | AG-03 | 圆桌是评审模式，不是独立业务模块；先作为 Review session |
| 14 | 接管 | `/aitest/tasks/<id>/takeover` | **复用 + 内嵌** | TK-08 | 保留全屏专注模式；作为任务 live 视图，不再占一级入口 |
| 15 | 系统设置 | `/aitest/system` | **拆分 + 扩展** | AU-01..AU-03 / ST-01..ST-04 | 审计、恢复、备份从“设置”独立；角色/保留/通知归设置 |

### 3.4 旧导航的复用/删除/合并/延后

| 决策 | 对象 | 说明 |
|---|---|---|
| **复用** | 总览、任务列表、任务详情外壳、知识、节点/设备、Agent、接管、系统设置 | 保留页面职责、组件、断点、令牌结构与烟测方法 |
| **合并** | 结论 + 门禁 → Verdict & Gates；模型 + 工具链 → Runtime & Toolchain；相似 → Knowledge；圆桌 → Reviews；推送 → Settings/Notifications | 减少一级入口与重复页面 |
| **拆分** | 任务详情 → 8 子视图；系统 → Audit & Recovery + Settings；节点详情 → Node + Device | 让实体边界与权威状态清晰 |
| **延后** | 全局深色模式、打印/PDF 报告 UI、推送投递中心、趋势图、多语言、引导、非语音任务类别 | 不阻塞 V0.0.1 可信闭环；不得用延后掩盖状态与可访问性缺口 |
| **删除/不再作为一级** | “思考”作为独立领域名、11 个固定编号导航、11 个任务页签、C1–C7 作为当前判定模型、单一状态徽章 | 与当前领域模型冲突 |

---

## 4. 新 IA：12 个区域

### 4.1 区域地图

| 区域 | 代号 | 回答的问题 | 主要实体 | 主/辅 |
|---|---|---|---|---|
| Mission Control | MC | 平台现在健康吗？哪里需要我？ | TaskCard、Run、Lease、Evidence、Alert、Reconcile | 主 |
| Intake & Revisions | IN | 需求如何变成可审阅的修订？ | Task、TaskRevision、Draft、SourceArtifact | 主 |
| Tasks | TK | 这个任务发生了什么？ | Task、Revision、Approval、Case、Run、Attempt、Verdict | 主 |
| Runs & Attempts | RN | 哪些运行在跑、停了、断线、待对账？ | Run、Attempt、StopRequest、Lease、Communication | 主 |
| Evidence & Verdict | EV | 证据够不够？结论能不能信？ | EvidenceSet、EvidenceItem、Manifest、Verdict | 主 |
| Devices & Nodes | DV | 在哪里执行？设备是否可用、被谁占用、能否释放？ | Node、Device、Lease、Occupancy、CleanupReceipt | 主 |
| Reports & Delivery | RP | 交付了什么？分母和披露范围是什么？ | Report、ReportVersion、EvidenceIndex | 辅 |
| Knowledge | KN | 平台知道什么？是否可信、能否推广？ | KnowledgeCandidate、KnowledgeItem、Conflict | 辅 |
| Runtime & Toolchain | RT | 谁在执行？工具链是否锁定、漂移？ | ModelBinding、ToolchainLock、Drift | 治理 |
| Agents & Reviews | AG | 谁负责什么？评审是否完成？ | AgentRegistry、ReviewSession、Plugin | 治理 |
| Audit & Recovery | AU | 谁做了什么？恢复/对账进行到哪？ | AuditEvent、AccessDecision、Reconcile、Backup | 治理 |
| Settings & Access | ST | 平台如何配置、授权、保留、通知？ | Role、TaskRelation、FeatureFlag、Retention | 治理 |

### 4.2 导航模型

- **桌面/平板一级入口 8 个**：Mission Control、Intake、Tasks、Runs & Attempts、Evidence & Verdict、Devices & Nodes、Reports & Delivery、Knowledge。
- **治理组 4 个**：Runtime & Toolchain、Agents & Reviews、Audit & Recovery、Settings & Access，收进 “Operations” 菜单/第二行，不参与任务主线的第一视觉层。
- **全局动作**：搜索/命令面板、新建任务、环境与连接状态、用户与角色、实时/降级/离线指示。
- **移动端**：底部 5 项为 Mission Control、Tasks、Runs、Devices、More；More 打开 12 区域全量抽屉。任务详情子视图为横向滚动 sticky tabs。
- **URL**：新基线建议 `/console/*`；旧 `/aitest/*` 在实现期提供 301/兼容别名，避免旧深链断裂。路由、筛选、页签、详情对象均可深链。
- **导航规则**：一级入口只放“持续运营对象”；一次性流程（Intake）用主按钮进入；详情对象不占一级；不新增未登记入口。

### 4.3 屏幕清单

> 状态列列出该屏**必须**准备的差异状态；通用 loading/empty/error/no-permission 对所有屏都适用。所有屏幕均不得用 mock 数据冒充真实状态。

| ID | 路由 | 屏幕 | 回答的问题 | 主要实体 | 关键状态 |
|---|---|---|---|---|---|
| MC-01 | `/console` | Mission Control | 平台健康吗？哪里需要我？ | TaskCard、Run、Lease、Evidence、Reconcile | loading / empty / error / blocked / stale / offline / reconciling / unknown-progress |
| IN-01 | `/console/intake` | Intake hub | 从哪种入口开始？ | Task、Draft、SourceArtifact | empty / error / no-permission |
| IN-02 | `/console/intake/new` | New task（对话/文件/表单三入口） | 需求如何结构化？ | Draft、SourceArtifact、Conflict | loading / error / blocked / partial-evidence |
| IN-03 | `/console/intake/:draftId` | Draft review & revision seed | 哪些事实缺失/冲突？能否生成修订？ | Task、TaskRevision、Conflict | empty / blocked / stale / no-permission |
| TK-01 | `/console/tasks` | Task list | 有哪些任务？进展如何？ | Task、TaskCard、Revision、Run | loading / empty / error / stale / unknown-progress |
| TK-02 | `/console/tasks/:taskId/overview` | Task overview / TaskCard | 这个任务现在到哪？ | Task、TaskCard、Block、Progress | loading / blocked / stale / offline / unknown-progress |
| TK-03 | `/console/tasks/:taskId/revisions` | Revisions & approval | 哪个修订被批准？范围是什么？ | TaskRevision、Approval、Diff | empty / blocked / stale / no-permission |
| TK-04 | `/console/tasks/:taskId/plan` | Plan & cases | 用例、oracle、证据要求是什么？ | Case、CaseVersion、Oracle、Assertion | loading / empty / blocked / partial-evidence |
| TK-05 | `/console/tasks/:taskId/runs` | Runs & attempts | 哪些 run/attempt 执行过？五轴如何？ | Run、Attempt、FiveAxis、Denominator | loading / empty / error / offline / reconciling / unknown-progress |
| TK-06 | `/console/tasks/:taskId/evidence` | Evidence manifest | 证据收齐了吗？manifest 是否一致？ | EvidenceSet、EvidenceItem、Manifest | loading / empty / partial-evidence / error / no-permission |
| TK-07 | `/console/tasks/:taskId/verdict` | Verdict & gates | 能否 PASS？门禁卡在哪？ | Gate、Verdict、Verification、Release | blocked / partial-evidence / quarantined / reconciling / no-permission |
| TK-08 | `/console/tasks/:taskId/live` | Takeover & logs | 当前执行/接管/日志是什么？ | Run、Attempt、Lease、AuditEvent | loading / offline / blocked / no-permission |
| TK-09 | `/console/tasks/:taskId/knowledge` | Knowledge & similar | 本次沉淀了什么？能否复用？ | KnowledgeCandidate、KnowledgeItem、Similarity | empty / stale / no-permission |
| RN-01 | `/console/runs` | Run board | 哪些运行在跑/停/断线/待对账？ | Run、Attempt、StopRequest、Communication | loading / empty / error / offline / reconciling / unknown-progress |
| RN-02 | `/console/runs/:runId` | Run detail | 这次运行的状态、进度、释放是什么？ | Run、Attempt、Lease、CleanupReceipt | loading / blocked / offline / partial-evidence / reconciling |
| RN-03 | `/console/runs/:runId/attempts/:attemptId` | Attempt detail | 这个用例尝试的事实与五轴是什么？ | Attempt、Case、Evidence、Facts | loading / empty / error / partial-evidence |
| EV-01 | `/console/evidence` | Evidence index | 证据在哪里？完整/冲突/未核验？ | EvidenceItem、Manifest、AccessLevel | loading / empty / partial-evidence / error / no-permission |
| EV-02 | `/console/evidence/:evidenceId` | Evidence item / manifest | 这个证据的身份、摘要、访问级别？ | EvidenceItem、Manifest、Digest、AuditEvent | loading / error / partial-evidence / no-permission / quarantined |
| EV-03 | `/console/verdicts` | Verdict review queue | 哪些结论待独立复核/有分歧？ | Verdict、Verification、Conflict | loading / empty / blocked / partial-evidence |
| DV-01 | `/console/devices` | Devices & nodes | 哪些节点/设备在线、占用、隔离？ | Node、Device、Lease、Occupancy、Reconcile | loading / empty / error / draining / quarantined / reconciling |
| DV-02 | `/console/devices/:deviceId` | Device detail | 设备被谁占用？能否释放？ | Device、Lease、Occupancy、CleanupReceipt | loading / blocked / draining / quarantined / reconciling |
| DV-03 | `/console/nodes/:nodeId` | Node detail | 节点心跳、会话、端点、spool 如何？ | Node、Heartbeat、Session、Endpoint | loading / offline / stale / draining / error |
| RP-01 | `/console/reports` | Reports list | 有哪些冻结/草稿/被取代的报告？ | Report、ReportVersion | loading / empty / error / no-permission |
| RP-02 | `/console/reports/:reportId` | Report detail | 摘要、分母、五轴、证据索引是什么？ | Report、Denominator、Verdict、EvidenceIndex | loading / empty / partial-evidence / blocked / no-permission |
| KN-01 | `/console/knowledge` | Knowledge search | 平台知道什么？是否适用？ | KnowledgeItem、Search、Applicability | loading / empty / error / stale |
| KN-02 | `/console/knowledge/:knowledgeId` | Knowledge item | 来源、证据、反例、状态是什么？ | KnowledgeItem、Provenance、Conflict | loading / stale / no-permission |
| KN-03 | `/console/knowledge/candidates` | Candidate review & promotion | 哪些候选待审？能否推广？ | KnowledgeCandidate、Review、Promotion | loading / empty / blocked / no-permission |
| RT-01 | `/console/runtime/models` | Models & bindings | 谁在思考？绑定是否生效？ | ModelBinding、Catalog、Health | loading / empty / error / stale |
| RT-02 | `/console/runtime/toolchain` | Toolchain & drift | 工具链是否锁定？哪里漂移？ | ToolchainLock、Drift、Smoke | loading / empty / error / blocked |
| AG-01 | `/console/agents` | Agent registry | 谁负责什么？写范围是什么？ | AgentRegistry、Policy | loading / empty / error / stale |
| AG-02 | `/console/agents/:agentId` | Agent detail | 模型策略、上下文、审查、审计？ | Agent、ModelBinding、Review | loading / stale / no-permission |
| AG-03 | `/console/reviews` | Review sessions | 评审共识/分歧/风险/行动？ | ReviewSession、Finding、Citation | empty / blocked / no-permission |
| AU-01 | `/console/audit` | Audit search | 谁做了什么？允许/拒绝？ | AuditEvent、AccessDecision | loading / empty / error / no-permission |
| AU-02 | `/console/audit/:eventId` | Audit event detail | before/after、原因、哈希链？ | AuditEvent、Integrity | loading / error / no-permission |
| AU-03 | `/console/recovery` | Recovery & reconcile | 恢复/对账/STOP-first 进行到哪？ | Reconcile、Backup、StopRequest | loading / blocked / reconciling / offline |
| ST-01 | `/console/settings` | Settings overview | 平台如何配置？ | FeatureFlag、Setting | loading / empty / no-permission |
| ST-02 | `/console/settings/access` | Roles & task relationships | 谁能看/批/释放/导出？ | Role、TaskRelation、Policy | loading / empty / no-permission |
| ST-03 | `/console/settings/notifications` | Notifications / push | 结果送到哪里？ | Subscription、Delivery、DeadLetter | loading / empty / error / no-permission |
| ST-04 | `/console/settings/retention` | Retention & data handling | 保留/归档/删除边界？ | RetentionPolicy、Archive、Audit | loading / blocked / no-permission |

### 4.4 任务详情 8 个子视图

旧 11 页签 → 新 8 子视图：

1. **Overview**（TK-02）：TaskCard、阶段、当前 run、五轴摘要、阻塞方、实际节点/设备、通信/占用/新鲜度、最后权威更新与最后已知活动。
2. **Revisions & Approval**（TK-03）：修订谱系、冻结范围、差异、审批意见/审批人/时间、超时/升级、旧修订只读。
3. **Plan & Cases**（TK-04）：计划、Case 版本、步骤、oracle、有效性条件、必需证据、覆盖率、冲突。
4. **Runs & Attempts**（TK-05）：static/smoke/formal 分离、run 列表、attempt 矩阵、五轴、失败分类、重试/FLAKY_SUSPECT、分母资格。
5. **Evidence**（TK-06）：manifest、证据项、已期望/已接收/已核验、部分/冲突/未核验、访问级别、摘要校验。
6. **Verdict & Gates**（TK-07）：G0–G7、五轴、Linux 独立复核、fail-closed 原因、设备释放状态、报告生成入口。
7. **Live**（TK-08）：运行中事件、接管（observe/interactive）、待 STOP、日志、重连/对账状态；全屏模式保留。
8. **Knowledge & Similar**（TK-09）：本次候选、相似任务/可复用块、应用为草案修订、知识状态与来源。

被移出任务详情的内容：旧“相似”独立页签并入 Knowledge；旧“门禁”并入 Verdict；旧“接管”并入 Live；旧“日志”并入 Live；旧“结论”与“门禁”合并展示但五轴仍逐项展开。

### 4.5 实体到屏幕覆盖

| 实体 | 主要屏幕 | 必须可见的字段/事实 |
|---|---|---|
| Task | TK-01、TK-02、MC-01 | task_id、origin、当前 revision、owner、status projection |
| TaskRevision | TK-03、IN-03 | revision_id、parent、frozen_scope、hash、approval |
| Approval | TK-03 | approver、scope snapshot、comment、time、timeout/escalation |
| Gate | TK-07、TK-02 | G0–G7、PASS/FAIL/PENDING/BLOCKED/NOT_APPLICABLE/UNKNOWN |
| Case | TK-04、RN-02 | case_id、case_version、steps、oracle、required_evidence |
| Run | TK-05、RN-01、RN-02 | run_id、mode、lifecycle、communication、occupancy、permit |
| Attempt | TK-05、RN-03 | attempt_id、ordinal、五轴、evidence_origin、denominator_eligible、flaky_suspect |
| EvidenceSet/Item | TK-06、EV-01、EV-02 | manifest id、digest、kind、size、collected_at、access_level |
| Verdict | TK-07、EV-03、RP-02 | 五轴、verification、fail-closed 原因、分母 |
| Lease/Device/Node | DV-01..DV-03、RN-02 | lease_id、epoch、occupancy、draining/quarantined、release preconditions |
| Report | RP-01、RP-02 | report_id/version、denominator、record separation、disclosure |
| KnowledgeCandidate/Item | KN-01..KN-03、TK-09 | candidate status、promotion、source、applicability、conflict |
| AuditEvent | AU-01、AU-02 | actor、action、object、before/after、reason、hash chain |
| TaskCard | MC-01、TK-02 | stage、run_state、gates、resources、blocker、progress、freshness |

---

## 5. 关键流程到屏幕

### 5.1 任务 / 修订 / 运行 / 用例 / 尝试

```text
Intake 草稿
  → Task + TaskRevision draft
  → 人工审阅 / 冻结
  → Approval（绑定修订与范围）
  → static run
  → smoke run（独立 run_id）
  → formal run（独立 run_id）
  → Attempt（每 case 每次尝试）
  → 五轴 Verdict
  → Report
```

| 步骤 | 屏幕 | UI 必须表达 | 禁止 |
|---|---|---|---|
| 三入口归一 | IN-01/IN-02 | 来源、字段来源、冲突、缺口 | 静默选一个来源继续 |
| 修订冻结 | IN-03/TK-03 | 冻结范围、父修订、差异、哈希 | 冻结后原地编辑 |
| 审批 | TK-03 | 审批人、意见、范围快照、时间、超时 | 审批后改变范围 |
| 静态/烟测/正式 | TK-05/RN-01 | mode 标签、独立 run、烟测不入分母 | 把烟测拼进正式分母 |
| 用例/尝试 | TK-04/RN-03 | case_version、attempt_ordinal、retry_of | 用名称合并不同版本 |
| 五轴 | TK-07/EV-03 | 五轴逐项 + 复核 + fail-closed 原因 | 单一 PASS/FAIL 覆盖五轴 |

### 5.2 审批与门禁

| 门禁 | 屏幕 | 通过条件摘要 | 失败/阻塞展示 |
|---|---|---|---|
| G0 受理 | IN-02/IN-03 | 来源、关键事实、冲突处理 | 缺口清单 + 责任人 |
| G1 冻结批准 | TK-03 | 不可变修订 + 审批 + 范围快照 | 缺审批/审批过期/自审策略 |
| G2 静态 | TK-05/RT-02 | preflight、schema、契约、工具链锁 | 具体失败项 + 重试/新修订 |
| G3 资源租约 | DV-01/DV-02 | 能力、在线、健康、端点、未占用 | 占用/隔离/离线原因 |
| G4 烟测 | TK-05/RN-02 | 独立 smoke run + 清理回执 | 烟测失败/无交互会话 |
| G5 正式 | TK-05/RN-02 | 批准样本、有效输入、证据采集 | 预算/样本/设备不满足 |
| G6 证据判定 | TK-06/TK-07/EV-03 | manifest 完整、五轴、独立复核 | 部分证据/冲突/未核验 |
| G7 报告/知识 | RP-02/TK-09/KN-03 | 报告冻结、候选生成、人工推广 | 报告缺章节/候选未审 |

### 5.3 五轴判定

每个 Run 与 Attempt 必须独立显示：

每轴都区分**权威枚举**（Linux 控制面可写入，见 [`../contracts/domain.md`](../contracts/domain.md) 第 9.1 节，第 305-313 行）与 **UI 投影占位**。`UNKNOWN` 只在投影层表示“尚未读取/尚未加载”；按 [`../contracts/evidence-verdict.md`](../contracts/evidence-verdict.md) 第 880 行，`verdict.axes.evidence_status` 不得写入 `UNKNOWN`（未核验写 `UNVERIFIED`，缺失写 `INCOMPLETE`，冲突写 `CONFLICTED`）。允许投影占位的依据是 [`../contracts/ui-report-knowledge-audit.md`](../contracts/ui-report-knowledge-audit.md) 第 102-106 行。

| 轴 | 权威枚举（`domain.md` 9.1） | UI 投影占位 | UI 位置 | 不可推断 |
|---|---|---|---|---|
| execution_status | NOT_STARTED / RUNNING / COMPLETED / ABORTED / SKIPPED | 可显示 `UNKNOWN`（尚未读取） | TK-05、RN-02/03 | 执行完成 ≠ PASS |
| validity_status | VALID / INVALID / BLOCKED / UNKNOWN | 同上（`UNKNOWN` 本身即为权威值） | TK-05、RN-03 | 无效执行 ≠ 产品失败 |
| business_verdict | PASS / FAIL / EXPECTED / WARN / NEEDS_REVIEW / NOT_EVALUATED | 可显示 `UNKNOWN`（尚未读取） | TK-07、RP-02 | 节点自报 ≠ 平台判定 |
| evidence_status | COMPLETE / INCOMPLETE / CONFLICTED / UNVERIFIED | 可显示 `UNKNOWN`（尚未读取）；**不得写入 verdict axes** | TK-06、EV-01/02 | 已接收 ≠ 已核验 |
| verification_status | PASS / FAIL / NOT_RUN | 可显示 `UNKNOWN`（尚未读取） | TK-07、EV-03 | 未复核 ≠ 可 PASS |

正式 PASS 的 UI 条件：五轴同时满足 `execution_status=COMPLETED + validity_status=VALID + business_verdict=PASS + evidence_status=COMPLETE + verification_status=PASS`，且批准/门禁/证据关联齐全；该五值集合与 [`../contracts/domain.md`](../contracts/domain.md) 第 620-627 行一致，任一轴缺失都不构成 PASS。任一缺失时，UI 只显示 `BLOCKED`、`NEEDS_REVIEW` 或具体无效分类，不显示绿色“通过”。`UNKNOWN` 只是“尚未读取”的展示占位，不能用于满足上述任一条件。

### 5.4 离线续跑、STOP-first、设备释放

| 场景 | 屏幕 | 必须展示 | 必须禁止 |
|---|---|---|---|
| 断线但已启动冻结压测 | MC-01、RN-01、TK-02、DV-01 | 通信 `OFFLINE`、执行 `RUNNING`、占用 `OCCUPIED`、`execution_permit=GRANTED`、最后已知时间、离线开始时间 | “已停止”“设备空闲”“可重派”“完成百分比” |
| 待 STOP 队列 | RN-01、RN-02、AU-03 | 待送达 STOP、请求时间、原因、目标 run/device、当前状态 | 把 STOP 请求当作已执行 |
| 重连 | AU-03、RN-02、DV-01 | STOP-first 顺序：处理 STOP → 停止后续动作 → 补传 → 去重 → 对账 → 恢复领取 | 先补传/先恢复派发；旧 epoch 改变当前运行 |
| 对账中 | MC-01、DV-01、AU-03 | `RECONCILING`、对账范围、未确认占用、禁止新派发 | 对账完成前重新分配设备 |
| 设备释放 | DV-02、RN-02 | 本地停止、安全清理、占用对账三项前置；`RELEASING/RELEASED` | 缺 `cleanup_receipt` 就显示“已释放”；释放 = 通过 |
| 清理失败 | DV-02、EV-03 | `QUARANTINED`、保持占用、人工恢复入口 | 自动重派或自动判 FAIL |
| 大日志未归档 | TK-06、RP-02 | 证据可继续上传/核验；归档状态独立 | 把“未归档”显示为证据不完整或判定失败 |

### 5.5 证据、报告、知识、审计

| 能力 | 屏幕 | 必须表达 | 禁止 |
|---|---|---|---|
| 证据 manifest | TK-06、EV-02 | schema、digest、size、kind、collected_at、node receipt、per-device/per-case 分母、`partial` | 只显示“文件数”；把未校验当完整 |
| 部分证据 | TK-06、EV-01、RP-02 | expected / received / verified 三列；未知为“未知” | 用 received 替代 verified |
| 报告 | RP-01/RP-02 | 14 章节、分母口径、四类记录分离、披露级别、版本/冻结 | 默认暴露原始音频/日志/路径 |
| 知识候选 | KN-03、TK-09 | PROPOSED..PROMOTED、来源、适用性、冲突、人工审阅 | 自动推广、候选当已批准 |
| 知识条目 | KN-01/KN-02 | APPROVED/CORROBORATED/DISPUTED/STALE/RETRACTED/SUPERSEDED | 静默压过冲突/过期 |
| 审计 | AU-01/AU-02 | actor、action、object、before/after、reason、access decision、hash chain | 可编辑/可删除审计；拒绝无记录 |
| 恢复 | AU-03 | 数据库 → manifest/摘要 → task/revision/run → node/device/lease 对账；备份分开验证 | 未演练声称 RPO/RTO；远程读取当备份 |

---

## 6. 状态模型

### 6.1 十二类状态定义

| 状态 | 触发条件 | UI 表现 | 允许动作 | 禁止声明 | 权威来源 |
|---|---|---|---|---|---|
| **loading** | 首次加载/切换筛选/打开详情 | 保留标题与操作位置的骨架；>1s 显示文字进度；不要空白闪烁 | 取消/返回 | 用旧缓存冒充新结果 | 请求状态 |
| **empty** | 无对象或无匹配 | 标题 + 解释 + 主动作；说明是“没有”还是“无权限” | 清除筛选/新建/返回 | 把无权限显示成空 | 查询结果 + 访问策略 |
| **error** | 请求失败/投影失败/摘要失败 | 页内错误卡或横幅；影响 + 重试 + 请求 ID；保留上下文 | 重试/复制 ID/返回 | 只写“出错了”；把堆栈/SQL/路径给普通用户 | API/投影/存储 |
| **blocked** | 缺批准、缺指标、资源冲突、门禁失败、人工决定 | 阻塞横幅/卡片；原因 + 解除条件 + `blocker.owner` + 下一步 | 补信息/请求审批/释放冲突/停止 | 自动继续；把阻塞当失败 | Gate/Approval/Orchestration |
| **stale** | 投影超过服务端阈值、事件延迟、缓存回退 | 灰虚线 + “陈旧” + 最后权威更新/最后已知活动 + 刷新 | 刷新/查看来源 | 用旧数据称“实时”；把 stale 当 offline | TaskCard freshness |
| **offline** | 节点↔控制面通信中断/心跳不可达 | 离线徽章；执行可能继续、设备保持占用、最后已知时间；不改变运行态 | 查看/等待重连/提交 STOP | “已停止”“设备空闲”“可重派” | communication_state |
| **partial-evidence** | 部分上传/部分校验/必要证据缺失/冲突 | 期望/已接收/已核验三列；逐 case 缺口；`INCOMPLETE/CONFLICTED/UNVERIFIED` | 补传/重试校验/查看 manifest | 显示 PASS；“已接收”当“已核验” | evidence_status |
| **no-permission** | 服务端 DENY/角色不足/任务关系缺失 | 页面保留只读摘要；禁用动作 + 原因；不泄露受限内容 | 请求授权/返回 | 隐藏整页；客户端过滤当访问控制 | access policy |
| **draining** | 设备/节点连续失败或运维排空 | “排空中/不再接新单”；已有 run 继续；不新派 | 等待完成/查看占用/人工恢复 | 立即重派；把 draining 当 quarantined | Device/Node state |
| **quarantined** | 清理失败/危险状态/连续失败 | “隔离中”；保持占用；恢复条件与责任人 | 人工恢复/查看证据/导出审计 | 自动恢复；自动重派；判 PASS/FAIL | Device/Node state |
| **reconciling** | 重连/控制面恢复/占用不确定 | “对账中”；STOP-first 步骤；未确认占用；禁止新派 | 查看对账进度/处理 STOP | 对账完成前释放/重派；旧 epoch 改当前运行 | Reconcile/Orchestration |
| **unknown-progress** | 总量未知/计数不可靠 | 只显示阶段、门禁、已知计数 + “未知”；`percent=null` | 查看阶段/证据/事件 | 0%、99%、“即将完成”、阶段序号冒充百分比 | TaskCard progress |

### 6.2 关键组合矩阵

| 组合 | 必须同时展示 | 不得展示 |
|---|---|---|
| offline + running + occupied | 通信离线 + 执行可能继续 + 设备占用 + 最后已知时间 | 已停止/设备空闲/可重派 |
| offline + completed/stopped | 离线 + 最后权威终态 + 离线开始时间 | 把离线当终态原因 |
| stale + running | 旧数据 + 陈旧原因 + 最后权威更新 | 用旧进度暗示实时 |
| partial-evidence + business PASS | 业务轴 PASS 但证据轴 INCOMPLETE；整体不可 PASS | 绿色“通过” |
| reconciling + pending STOP | STOP 待处理 + 对账步骤 + 禁止新派 | 已处理/已恢复 |
| draining + running | 排空中 + 当前 run 继续 + 不再接新单 | 已隔离/已释放 |
| quarantined + occupied | 隔离 + 占用 + 人工恢复条件 | 可重派/已释放 |
| no-permission + write action | 只读页面 + disabled + 原因 | 隐藏页面/静默失败 |
| unknown-progress + COUNTS 请求 | “未知” + 已知计数 + 度量名称 | 数字百分比 |

### 6.3 禁止的声明

以下文案不得出现在任何屏幕、报告或导出：

- “已完成”用于未通过门禁与归档的任务。
- “PASS”用于缺批准、缺指标、缺必要证据、缺追溯、未独立复核的结果。
- “设备空闲/可重派”用于 `OFFLINE` 但 `OCCUPIED` 的设备。
- “已释放”用于缺 `cleanup_receipt` 或未完成占用对账的设备。
- “已核验”用于仅“已接收”的证据。
- “已推广”用于 `PROPOSED/UNDER_REVIEW/NEEDS_INFO` 的知识候选。
- “实时”用于降级轮询/陈旧投影。
- “100%”“即将完成”“零误判”等无证据的绝对表述。
- 把 mock、dry-run、replay、烟测描述为真实执行或正式样本。

### 6.4 状态 fixture 要求

Phase 1 冻结前，每个屏幕至少需要：

- 通用：loading、empty、error、no-permission。
- 任务主线：blocked、stale、offline、partial-evidence、unknown-progress。
- 运行/设备：draining、quarantined、reconciling。
- 组合：offline+running+occupied、stale+running、partial-evidence+PASS、reconciling+STOP、quarantined+occupied。

实现阶段必须用服务端可构造的 fixture 或契约 mock 生成，不得只做静态截图。每张 fixture 必须标注 `source`、`schema_version`、`server_authoritative=true/false`，防止把 mock 当真实状态。

---

## 7. 密度策略：刻意克制 vs 信息密集

| 区域 | 密度 | 原因 | 渐进披露 |
|---|---|---|---|
| Mission Control（MC-01） | **克制** | 一屏回答“健康吗/哪里需要我”；不是全量监控墙 | 只放异常、待决断、离线/对账/隔离；明细下钻 |
| Intake（IN-01..03） | **克制** | 一次只处理一个需求；降低输入焦虑 | 三步：来源 → 澄清 → 修订种子；高级字段折叠 |
| Tasks 列表（TK-01） | 中等 | 需要扫描但不需要全量字段 | 默认列：任务/修订/阶段/五轴摘要/占用/证据/更新；列设置 |
| Task overview（TK-02） | **克制** | 首屏只给判断与阻断点 | 五轴摘要 + 阻塞方 + 资源；明细进子视图 |
| Plan & Cases（TK-04） | **密集** | 用例、步骤、oracle、证据要求必须可审 | 用例表 + 详情抽屉；覆盖矩阵可折叠 |
| Runs & Attempts（TK-05/RN-01） | **高密集** | 多 run/attempt、五轴、分母、重试必须并排比较 | 矩阵 + 筛选 + 行详情；手机转卡片 |
| Evidence（TK-06/EV-01/02） | **高密集** | manifest、摘要、大小、时间、访问级别 | 按 case/设备分组；原始内容走受控访问 |
| Devices & Nodes（DV-01..03） | **高密集** | 心跳、端点、租约、占用、隔离、spool | 节点卡 + 设备表 + 详情；危险动作二次确认 |
| Reports（RP-02） | **克制（默认）** | 默认读者只看摘要/索引/分母 | 14 章节可展开；受限章节按权限显示 |
| Knowledge（KN-01..03） | 中等 | 检索要快，候选审阅要聚焦 | 结果卡 + 详情；候选队列单列 |
| Runtime（RT-01/02） | **高密集** | 绑定链、lock、compat、drift 需要精确 | 作用域分段 + 矩阵 + diff |
| Agents & Reviews（AG-01..03） | 中等 | 注册表与评审记录 | 表格 + 详情 + 评审摘要 |
| Audit & Recovery（AU-01..03） | **高密集** | 审计不可变、对账步骤必须精确 | 事件表 + before/after + 对账时间线 |
| Settings（ST-01..04） | **克制** | 配置不是高频运营 | 分区 + 表单；危险区二次确认 |

原则：**克制不等于省略安全事实**。Mission Control 可以少放图，但不能不显示“离线仍占用”“待 STOP”“证据不完整”“隔离设备”。信息密集区可以用分组、筛选、列设置、详情抽屉降低认知负担，但不能把关键事实藏到二级页面才显示。

---

## 8. 需求到屏幕追溯

### 8.1 REQ 追溯

| REQ | 需求摘要 | 主要屏幕 | 关联 AC |
|---|---|---|---|
| REQ-01 范围 | 三入口、语音域、排除项 | IN-01..03、TK-04 | AC-1 |
| REQ-02 角色 | 提交者/审批者/Lead/参与者/管理员 | TK-03、ST-02、AG-01 | AC-1、AC-2 |
| REQ-03 任务身份/修订/运行 | 不可变修订、独立运行、追溯 | TK-01..05、RN-01..03 | AC-3、AC-6 |
| REQ-04 Intake | 检索、来源、冲突、审阅 | IN-01..03、TK-03 | AC-1 |
| REQ-05 语音域 | 能力、用例、有效输入、可观察结果 | TK-04、RN-03 | AC-4、AC-9 |
| REQ-06 资源与安全 | 能力/健康/占用/端点、替代、释放 | DV-01..03、RN-02 | AC-5、AC-11..13 |
| REQ-07 Lead 会话 | 稳定会话、恢复、不授权执行 | TK-02、TK-08 | AC-2、AC-6 |
| REQ-08 任务卡 | 独立进度、stale、未知不编造 | MC-01、TK-02 | AC-2、AC-10 |
| REQ-09 生命周期/门禁 | 静态/烟测/正式、修复/停止 | TK-05、TK-07、RN-01 | AC-3、AC-4 |
| REQ-10 证据/判定 | manifest、fail-closed、设备隔离 | TK-06、TK-07、EV-01..03 | AC-4、AC-9 |
| REQ-11 报告/审批 | 摘要、索引、四类记录、自动/人工 | RP-01/02 | AC-7、AC-9 |
| REQ-12 隐私/保留/知识 | 访问审计、30 天、候选不自动推广 | EV-02、KN-03、ST-04 | AC-7、AC-8 |
| REQ-13 非功能 | 可追溯、真实、隔离、恢复、安全、隐私、可审阅 | 全域 | AC-10..14 |
| REQ-14 排除项 | 不宣称未运营能力 | 全域文案 | AC-9、AC-10 |
| REQ-15 验收 | 10 项验收场景 | 全域 | AC-1..10 |
| REQ-16 后续决策 | 状态名、权限、阈值、归档等 | ST-02/04、AU-03 | — |

### 8.2 AC 追溯

| AC | 验收摘要 | 屏幕证据面 | 当前差距 |
|---|---|---|---|
| AC-1 | 三入口 → 草稿 → 审阅 → 冻结 → 一次批准 | IN-01..03、TK-03 | 旧 Think 没有修订谱系/审批快照 |
| AC-2 | 单 Lead、可恢复会话、独立任务卡、stale | TK-02、TK-08 | 旧任务卡只有阶段/进度，缺 freshness/communication/occupancy |
| AC-3 | 静态/烟测/正式分离；烟测不入分母 | TK-05、RN-01/02 | 旧“执行”页签混合；无 smoke/formal 分栏 |
| AC-4 | 无效分类；缺证据 fail-closed | TK-07、EV-03 | 旧单一状态掩盖 validity/evidence |
| AC-5 | 设备替代受等价条件约束；结果隔离 | DV-01..03、RN-02 | 旧节点页无替代原因/等价字段 |
| AC-6 | 新范围同任务派生新修订；旧证据不并入 | IN-03、TK-03 | 旧详情无修订谱系/差异 |
| AC-7 | 默认摘要；原始材料受限；到期不删 | RP-02、EV-02、ST-04 | 旧报告无披露分级；无归档状态 |
| AC-8 | 知识候选需审阅；第二任务可复用 | KN-01..03、TK-09 | 旧知识页只有侧栏治理队列与“不自动批准”文案，没有候选生命周期页（PROPOSED→UNDER_REVIEW→APPROVED→PROMOTED）与推广权限 |
| AC-9 | 自动 PASS 仅来自自动回放与客观证据 | TK-07、RP-02 | 旧规范已把“AI 已确认”列为禁止文案（[`../v2/UI-DESIGN.md`](../v2/UI-DESIGN.md) §10.6，第 2613 行），不是旧 UI 的既有文案；旧 UI 已有“机器复算 vs runner”“不信任 runner 自报 PASS”（`design/ui-prototype.html:2252`、`:2796`），方向与 AC-9 一致，但仍缺五轴与 evidence/verification 的逐项展示 |
| AC-10 | UI 与后端状态/五轴/证据一致；离线不误报 | MC-01、TK-02/07、RN-01 | 旧 UI 单状态；无五轴 |
| AC-11 | 断线继续；设备保持占用；不重派/重播/重复采样 | RN-01/02、DV-01、AU-03 | 旧 UI 无离线续跑视图 |
| AC-12 | STOP-first 重连；旧 epoch 不改当前运行 | RN-02、AU-03、DV-01 | 旧 UI 无待 STOP/对账 |
| AC-13 | 释放独立于归档/判定；执行/释放/证据/判定分别记录 | DV-02、RN-02、RP-02 | 旧 UI 把释放与结论混在“完成” |
| AC-14 | 恢复顺序；未演练不声称 RPO/RTO | AU-03 | 旧系统设置只有审计与备份入口（“存储”卡有最近备份时间与“备份数据库”按钮，`design/ui-prototype.html:2683`），没有恢复顺序、恢复演练和占用对账页面 |

---

## 9. 可访问性与深色模式差距

### 9.1 现有证据

| 项 | v2 | Apple v3 | 结论 |
|---|---|---|---|
| 对比度 | `UI-REVIEW.md` 列出自查比率 | `UI-DESIGN-APPLE.md` 称脚本复测 0 失败 | 均为设计自查，不是 WCAG AA 审计 |
| 键盘 | 声称 Tab/Esc/Ctrl+K/方向键 | 声称焦点环、Esc、方向键 | 未做真实键盘走查记录 |
| 屏幕阅读器 | 未实测（NVDA） | 未实测 | 缺口 |
| axe-core | 未运行 | 未运行 | 缺口 |
| 200% 缩放 | 有策略，未截图回归 | 有策略，未实测 | 缺口 |
| 高对比度 | 未验证 | 未验证 | 缺口 |
| 44px 触控 | 部分按钮 22–26px | 声称主要交互 ≥44px | 需逐项核对 |
| 焦点陷阱 | 未完整实现 | 明确未实现完整 trap | 缺口 |
| 终端文本替代 | 设计有，原型无独立文本视图 | 有“复制可见文本/下载日志” | 需实现 |
| 深色模式 | 只有局部深色终端 | `color-scheme` 固定 light | 无全局深色 |
| 减少动效 | 支持 | 支持 | 可继承 |
| 打印/PDF | 延后 | 未覆盖 | 报告区需补 |

### 9.2 P0 缺口（进入实现前必须解决）

1. **五轴矩阵的语义**：表格必须有 caption、th scope、行/列标题；五轴不能用颜色块堆叠；每个轴要有文字与 `aria-label`。
2. **offline/reconciling 的 live region**：离线、待 STOP、对账进度必须用 `aria-live=polite` 合并播报，不能每秒打断。
3. **状态不只靠颜色**：gate/五轴/占用/证据状态必须同时有文字、形状或图标。
4. **禁用原因**：no-permission/blocked/draining/quarantined 的 disabled 动作必须 `aria-describedby` 解释，不能只降透明度。
5. **焦点管理**：任务详情 8 子视图切换、抽屉、命令面板、全屏接管必须有焦点进入/归还；不能困住键盘。
6. **200% 缩放**：密集矩阵/表格在 200% 下不得丢失五轴/证据/释放事实；允许局部横向滚动，但不能裁切结论。
7. **44px 触控**：手机上的 gate 瓦片、五轴 chip、证据行操作、设备释放按钮必须 ≥44×44。
8. **真实屏幕阅读器与 axe**：Phase 1 至少一次 NVDA + Edge/Chrome + axe 本地运行记录；不能只写“已设计”。

### 9.3 新 IA 特有风险

- **8 个子视图 + 12 区域**增加导航层级；必须提供命令面板、面包屑、返回路径与 URL 深链，避免键盘用户迷路。
- **Attempt 矩阵**列多、行多；手机必须转卡片或分组，不能把五轴压成 5 个窄列。
- **Evidence manifest** 有长哈希、长路径、长 ID；必须 `overflow-wrap:anywhere` + 复制完整值，不能截断语义。
- **Audit event** 的 before/after 是结构化 diff；必须提供文本摘要与表格替代，不能只靠颜色。
- **报告默认视图**是摘要；受限章节的“无权限”必须解释访问级别，而不是假装不存在。
- **知识候选**的“未复核”必须与“已批准”有不同视觉权重，且屏幕阅读器可区分。

### 9.4 深色模式

当前事实：v2 只有浅色全局主题 + 局部深色终端；Apple v3 `color-scheme` 固定 light，未设计全局深色。`UI-DESIGN.md` 第 16.1 明确“浅色为唯一全局主题”。

差距：

- 没有 `prefers-color-scheme` 分支；没有深色语义 token 对（canvas/raised/ink/accent/status）。
- 状态色（ok/warn/danger/disputed）只在浅色背景校准；深色下对比度与语义映射未验证。
- 终端、证据查看器、五轴矩阵、gate 印章在深色下的边界/焦点/禁用态未定义。
- 高对比度（forced-colors）与深色是两件事，均未验证。
- 打印/PDF 报告是第三套表面，不能用屏幕深色 token 直接套。

建议（待 Phase 1 决策，不在本文批准）：

- **方案 A（推荐用于 V0.0.1）**：声明 light-first，深色模式延后到 V0.0.2；但必须在设计令牌中预留语义层，禁止在组件里写死浅色值。
- **方案 B**：Phase 1 内完成深色 token + 对比度 + 状态色 + 终端 + 高对比度验证；成本更高，但避免实现期返工。
- 无论选哪个，**不得**用 CSS filter 反色或简单交换黑白来伪造深色模式。

---

## 10. 假设

| ID | 假设 | 影响 | 验证方式 |
|---|---|---|---|
| A-01 | `docs/contracts/` 的 frozen-candidate 会在 Phase 1 前冻结为字段基线 | 屏幕字段名、枚举、权限 | Orchestrator 冻结评审 |
| A-02 | 五轴是唯一判定表达；C1–C7 只作历史/门禁追溯 | 任务详情、报告、状态徽章 | 契约 + AC-10 |
| A-03 | TaskCard 由服务端投影，UI 不推导状态/百分比 | 任务卡、Mission Control | 投影契约 + fixture |
| A-04 | offline 期间节点继续执行且设备保持占用 | 运行/设备/恢复页面 | AC-11/12 + 真机证据 |
| A-05 | 设备释放独立于证据归档与最终判定 | 设备详情、报告 | AC-13 + 清理回执 |
| A-06 | 报告默认只暴露摘要与证据索引 | 报告详情、导出 | 访问策略 + AC-7 |
| A-07 | 知识推广必须人工批准，Agent 不能自动推广 | 知识候选页 | 契约 + AC-8 |
| A-08 | 12 区域可以落在桌面 8 一级 + 4 治理组，不强行塞进 11 个平级入口 | 导航、移动端 | IA 评审 + 可用性测试 |
| A-09 | 旧 `/aitest` 深链可在实现期重定向到 `/console` | 迁移、书签 | 路由测试 |
| A-10 | Phase 1 仍以 Apple v3 视觉方向为基础，但 IA 重写 | 令牌、组件、页面 | 用户评审 |
| A-11 | 全局深色模式在 V0.0.1 可延后，但需明确声明 | 设计令牌、验收 | Phase 1 决策 |
| A-12 | 现有烟测脚本可复用为路由/溢出/控制台检查 | 视觉 QA | 脚本改造 |

---

## 11. 风险与缓解

| ID | 风险 | 影响 | 缓解 | 触发信号 |
|---|---|---|---|---|
| R-01 | 12 区域比旧 11 导航更碎，用户找不到“运行/证据” | 认知负担、误操作 | 8 一级 + 4 治理组；命令面板；Mission Control 深链 | 可用性测试找不到关键页面 |
| R-02 | 任务详情仍有 8 个子视图，页签疲劳 | 关键事实被折叠 | 首屏 TaskCard 给五轴/阻塞/资源；子视图带计数与状态点 | 用户反复切换页签 |
| R-03 | 旧文档仍被实现者当作当前基线 | 误用 C1–C7/单状态/旧令牌 | 本文 + VERSIONING 标注；Phase 1 冻结新基线；旧文件保留但加历史标记 | 代码/设计引用旧 C1–C7 |
| R-04 | 契约未冻结，字段/枚举漂移 | 返工 | Phase 1 先对齐 `docs/contracts/`；用 schema 生成 fixture | 页面字段与契约不一致 |
| R-05 | 离线/对账 UI 误报“已停止/空闲/可释放” | 双任务抢设备、证据污染 | 四信号分离；组合矩阵；fixture；文案禁令 | 出现“离线=空闲”文案 |
| R-06 | 部分证据被当成完整证据 | 假 PASS | expected/received/verified 三列；fail-closed；报告分母声明 | 证据页只显示文件数 |
| R-07 | 设备释放与判定混淆 | 过早释放、证据丢失 | 三项释放前置；释放状态独立；清理回执 | “已释放”早于 cleanup |
| R-08 | 知识候选被自动推广 | 错误知识进入判定 | 候选/条目分离；人工批准；禁止自动 | 候选显示“已生效” |
| R-09 | 审计/恢复页信息过密 | 关键事件被淹没 | 默认筛选拒绝/失败/对账；保存视图；导出受限 | 审计页首屏无异常 |
| R-10 | 可访问性与密度冲突 | 键盘/读屏不可用 | 语义表格、文本替代、200% 测试、axe/NVDA | 只靠颜色/悬停 |
| R-11 | 深色模式延后导致返工 | 实现期重做令牌 | 语义 token 先行；组件禁止硬编码；Phase 1 决策 | 组件出现 `#fff` 硬编码 |
| R-12 | 旧烟测计数口径不一致 | “全部通过”不可复核 | 统一路由清单；机器可读 route manifest | 文档/JSON 路由数不一致 |
| R-13 | 报告/导出泄露原始材料 | 隐私事故 | 默认摘要；服务端裁剪；访问审计；导出二次确认 | 报告出现音频/日志正文 |
| R-14 | Push/Roundtable 降级后无人承接 | 旧 P7 任务悬空 | 明确归入 ST-03/AG-03；Phase 2 再评估 | 需求追溯出现空行 |
| R-15 | 没有真实 API fixture，状态页无法验证 | 上线后状态错误 | Phase 1 用契约 mock + 状态矩阵；实现期换真 fixture | 只有静态默认态 |

---

## 12. 未决问题

| ID | 问题 | 需要谁决定 | 影响 |
|---|---|---|---|
| Q-01 | 新基线采用 v2 Voyage Ledger、Apple v3 Quiet Instrument，还是混合？ | 用户/Phase 1 评审 | 令牌、组件、视觉 |
| Q-02 | 12 区域是否收敛为 10（合并 Reports→Tasks、Agents→Settings）？ | IA 评审 | 导航复杂度 |
| Q-03 | 路由前缀用 `/console` 还是保留 `/aitest`？ | 实现架构 | 迁移/深链 |
| Q-04 | 全局深色模式：V0.0.1 做还是明确延后？ | 用户/Phase 1 | 令牌、验收 |
| Q-05 | Push 是否保留独立设置子页，还是并入通知中心？ | 产品 | ST-03 范围 |
| Q-06 | Roundtable 是否作为 AG-03 评审会话，还是任务详情内嵌？ | 产品/架构 | AG-03 |
| Q-07 | Reports 是否提供打印/PDF 样式表？ | 交付 | RP-02、paged media |
| Q-08 | 审计/恢复是否仅 SUPER_ADMIN 可见？ | 权限 | AU-01..03 |
| Q-09 | TaskCard 的 stale 阈值由哪个配置提供？ | P0-08 契约 | 状态显示 |
| Q-10 | 旧 `/aitest` 路由的兼容期多长？ | 实现/运维 | 重定向策略 |

---

## 13. 验证与边界

### 13.1 本文完成的验证

- 已读 `plan.md`、`.omo/plans/noahsark-platform-delivery.md`、`.omo/drafts/00-baseline`、`.omo/drafts/01-design`、`.omo/drafts/02-delivery`。
- 已读 `docs/v2/UI-DESIGN.md`、`docs/v2/UI-DESIGN-APPLE.md`、`docs/v2/UI-REVIEW.md`、`docs/v2/UI-ORIGINALITY.md`、`docs/v2/ACCEPTANCE-REPORT.md`、`docs/v2/SOLUTION.md` 第 8 节、`docs/v2/IMPLEMENTATION-PLAN.md` Phase 7。
- 已盘点 `design/` 下令牌、原型、15 个线框、14 张截图、2 份烟测 JSON。
- 已读 `docs/contracts/domain.md`、`docs/contracts/evidence-verdict.md`、`docs/contracts/ui-report-knowledge-audit.md` 的实体/状态/报告/知识/审计章节。
- 本文 v0.2 只修改 `docs/delivery/ui-baseline-gap-analysis.md` 与本目录的 `ui-baseline-gap-verification.md` 第 7 节（修正记录）；未修改 `design/`、`docs/v2/`、`.omo`、`plan.md`、契约或 `docs/ssh.txt`；未写产品代码；未提交/推送。
- 验证命令：本文为未跟踪文件（`git status` 显示 `?? docs/delivery/`），`git diff --check` 不检查未跟踪内容，因此退出 0 不能作为本文的空白检查证据；实际用 `grep -nP '[ \t]+$' docs/delivery/ui-baseline-gap-analysis.md` 复核，0 行尾空白（等价替代：`git diff --no-index --check /dev/null <file>`）。文档内 42 处相对链接（去重 30 个目标）全部可解析（0 缺失）。Markdown LSP 未配置，因此无 LSP 诊断可报告。
- 工作区中 `docs/v2/*` 的已存在修改来自其他工作单元（P0-03 文档同步），不属本任务；本任务只新增本文件。

### 13.2 明确未完成

- 未做用户可用性测试、视觉评审或最终 UI 批准。
- 未冻结新 IA、设计令牌、页面规格或路由。
- 未运行 axe、NVDA、200% 缩放、高对比度、深色模式审计。
- 未接真实 API；所有状态讨论是设计/契约层，不是运行证据。
- 未证明任何 AC 已通过；AC 追溯只说明“应由哪些屏幕承载”。

### 13.3 下一步建议

1. 由 Orchestrator/用户裁决 Q-01 至 Q-10，尤其是视觉方向、区域数、深色模式。
2. Phase 1 在本文基础上产出冻结版 IA：路由 manifest、12 区域页面规格、8 个子视图、状态 fixture 矩阵。
3. 把 `docs/contracts/` 的 frozen-candidate 字段映射到屏幕字段清单，先冻结字段名/枚举/权限，再画高保真。
4. 用旧烟测脚本改造出“路由 + 溢出 + 控制台 + 状态 fixture”四类检查；补 axe/NVDA/200%/高对比度。
5. 在 Phase 1 评审通过前，不进入 P5-08 UI 实现，不声称 UI 已验收。
