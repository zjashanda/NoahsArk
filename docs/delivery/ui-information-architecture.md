# NoahsArk UI 信息架构（IA）— Phase 1 / P1-02 提案

> 版本：v0.3（2026-10-29）。状态：**Phase 1 IA 候选（decision-ready draft），供 P1-02 评审裁决**。不是 UI 设计冻结件，不是实施授权，不表示任何 UI 已实现、已测试或已通过验收。
> 范围：角色与访问、三端导航、12 个产品区域、39 条路由、四条关键旅程、密度策略、12 类必需状态、逐屏状态最低集与来源追溯。
> 边界：本文只修改本文件；不修改 `design/`、`docs/v2/`、`docs/contracts/`、`.omo` 状态、`plan.md` 或产品代码；不提交、不推送。
> 事实源优先级：按 [`docs/contracts/README.md`](../contracts/README.md) §1 与 [`docs/VERSIONING.md`](../VERSIONING.md) 第 2 节执行。本文件是 UI 信息架构候选；字段/枚举以 `docs/contracts/` 为准，屏幕实现细节以 [`ui-screen-specification.md`](./ui-screen-specification.md) 为准，视觉令牌以 [`ui-design-system.md`](./ui-design-system.md) 为准。

---

## 0. 一页结论

1. 旧 UI 的令牌、外壳与组件可继承；**导航与状态语义必须重组**。旧 11 个平级入口、15 路由、任务详情 11 页签不作为目标结构；目标为 **12 个区域、39 条路由、任务详情 8 个子视图**。
2. 新 IA 为 **12 个区域**：8 个主入口（Mission Control、Intake、Tasks、Runs & Attempts、Evidence & Verdict、Devices & Nodes、Reports & Delivery、Knowledge）+ 4 个治理入口（Operations）。**Intake 是唯一流程入口**：它保留在导航中以便发现，但主路径由全局“新建任务”按钮进入，不按持续运营对象设计。
3. 任务主线的约定标签为 **Task → Revision → Run → Case → Attempt**；实体依赖实际为 **Task → Revision → Case（随修订冻结）→ Run → Attempt**（Run 只消费已冻结的 `case_version`，UI 以依赖顺序呈现）。任务详情收敛为 **8 个子视图**，审批、运行、证据、判定分别可见。
4. 状态不折叠：**五轴独立**，通信、占用、执行许可、释放、新鲜度分别建模；离线不得渲染为“已停止/空闲/可重派”。
5. UI 只读消费 Linux 投影；**PostgreSQL 是唯一正式数据库**，Windows 节点只回传事实，不写最终判定。
6. 本文把可评审的 IA 决定与仍需裁决的问题分开记录（§10）：**12 区域、8 子视图、`/console/*` 基线、三端导航骨架、12 类状态、密度策略为建议冻结项**；视觉方向、区域收敛、深色模式、审计可见性、RT/AG 访问级别仍待裁决。评审通过前不得声称 UI 冻结或进入 P5-08 实现。

---

## 1. 权威边界与状态分离

| 层 | 职责 | UI 关系 |
|---|---|---|
| PostgreSQL | 控制面唯一正式数据库；保存权威状态、索引与摘要 | 不直连、不写；禁止 SQLite 参与正式状态 |
| Linux 控制面 | 唯一权威写入方：Task、Revision、Approval、Gate、Case、Run、Attempt、Lease、Device、Node、五轴判定 | UI 只读投影；不得反向写 |
| Windows Node Agent | 领取冻结工件、执行、采集并回传 receipt **事实**；`used_for_decision=false` | 只展示“节点观察事实”，不得展示为平台判定 |
| UI / 投影 | TaskCard、列表、报告默认视图、状态徽章 | 可重建、幂等、可降级；不是第二事实源 |

状态分离（任一维不可由另一维推断）：

| 维度 | 字段/来源 | 禁止推断 |
|---|---|---|
| 执行 | `execution_status` | 执行完成 ≠ PASS |
| 有效性 | `validity_status` | 无效执行 ≠ 产品失败 |
| 业务判定 | `business_verdict` | 节点自报 ≠ 平台判定 |
| 证据 | `evidence_status` | 已接收 ≠ 已核验 |
| 独立复核 | `verification_status` | 未复核 ≠ 可 PASS |
| 通信 | `communication_state` | OFFLINE ≠ 已停止/空闲 |
| 占用 | lease `occupancy_state` | 失联不改变占用 |
| 执行许可 | `execution_permit` | 断线不自动撤销 |
| 释放 | `cleanup_receipt` + `local_stop_confirmed` + `safe_cleanup_done` + `occupancy_reconciled` | 释放 ≠ 通过；缺回执 ≠ 证据不完整 |

正式 PASS 必须同时满足 `COMPLETED / VALID / PASS / COMPLETE / PASS`（[`domain.md`](../contracts/domain.md) §14）。任一未知枚举按 fail-closed 显示 `UNKNOWN`/`NEEDS_REVIEW`，不得猜 PASS。

### 1.1 节点事实与平台判定的显示边界

1. Windows 回执中的 `outcome` 只以 `node_observed_*` 展示，并固定标注 `used_for_decision=false`；不得渲染成 `business_verdict`、`verification_status` 或“平台判定”。
2. 节点事实与 Linux 判定在同一屏必须**分栏或分行**出现，标签分别为“节点观察事实”和“Linux 平台判定”；颜色、图标、排序均不得暗示二者等价。
3. 设备释放、证据完整性、最终判定是三个独立平面：缺 `cleanup_receipt` 表示“释放无法确认、设备保持占用”，**不等于** `evidence_status=INCOMPLETE`，也不单独否决 PASS；但该 PASS 不授权设备释放或复用，报告必须同时显示“释放未确认”（[`evidence-verdict.md`](../contracts/evidence-verdict.md) §12.3、§13）。

---

## 2. 角色与访问

| 角色 | 默认能力 | 不得 |
|---|---|---|
| `OBSERVER` | 摘要、任务详情、证据索引 | 读原始音频/日志/证据文件（显式 DENY 优先） |
| `TERMINAL_OPERATOR` | 观察、按任务关系读部分证据、运行烟测 | 管理设置、推广知识 |
| `SESSION_MANAGER` | 新建任务、被指派时审批、停止自己的任务、会话管理、节点/设备控制（与 SUPER_ADMIN 共享） | 管理设置、审计导出、角色管理 |
| `SUPER_ADMIN` | 角色、设置、知识推广（需目标库权限 + 审计）、审计导出、节点/设备控制 | 绕过审计、改写历史事件 |

非 UI 主体：`SYSTEM`（受控系统动作）、`NODE_AGENT`（领取作业、回传事实）、`AGENT`（生成候选/草案，无推广权）。
任务关系：`SUBMITTER` / `MEMBER` / `APPROVER` / `VIEWER` / `EVIDENCE_READER` / `NONE` / `ANY`（`ANY` 仅用于受控管理规则，不用于原始材料）。求值顺序 **显式 DENY → 显式 ALLOW → 默认 DENY**；未知角色/关系/策略一律 DENY。
访问级别：`PUBLIC_SUMMARY`（保留，V0.0.1 不默认使用）、`SUMMARY_INDEX`（报告与证据索引默认）、`TASK_AUTHORIZED`（任务详情默认）、`EVIDENCE_AUTHORIZED`（原始材料）、`ADMIN_ONLY`（设置/角色/审计导出/节点控制）、`DENY`（显式拒绝并审计）。UI 只能降级字段或禁用动作，不得提升，也不得用隐藏整页代替拒绝原因。
无权限时保留**只读摘要 + disabled 动作 + 原因**，不隐藏整页；客户端过滤不算访问控制。

### 2.1 区域默认访问级别（IA 级）

> 本表把 [`ui-report-knowledge-audit.md`](../contracts/ui-report-knowledge-audit.md) §6.4 的资源规则映射到 12 个区域；具体路由仍需服务端按对象裁剪。标“待裁决”的项在契约中无默认规则，不得由 UI 自行补全。

| 区域 | 默认访问 | 受限/提升条件 |
|---|---|---|
| MC | `TASK_AUTHORIZED` | 仅投影摘要，不含原始材料 |
| IN | `TASK_AUTHORIZED` | 提交者/成员/审批者/观察者；跨任务无关系默认 DENY |
| TK | `TASK_AUTHORIZED` | 审批动作另需 `APPROVE_TASK`；原始证据跳 EV 并二次鉴权 |
| RN | `TASK_AUTHORIZED` | 原始日志/终端正文需 `EVIDENCE_AUTHORIZED` |
| EV | 元数据 `SUMMARY_INDEX`；原始 `EVIDENCE_AUTHORIZED` | 拒绝也审计；`OBSERVER` 对原始材料显式 DENY |
| DV | 元数据 `TASK_AUTHORIZED`；控制 `ADMIN_ONLY` | `SESSION_MANAGER`/`SUPER_ADMIN` 控制；序列号脱敏 |
| RP | `SUMMARY_INDEX` | 受限章节明细按 `TASK_AUTHORIZED`/章节声明 |
| KN | `SUMMARY_INDEX` | 审阅/推广需 `REVIEW_KNOWLEDGE_CANDIDATE` 与目标库权限 |
| RT | **待裁决** | 候选：只读 `TASK_AUTHORIZED`、写入 `ADMIN_ONLY` |
| AG | **待裁决** | 候选：注册表只读 `TASK_AUTHORIZED`、治理动作 `ADMIN_ONLY` |
| AU | 任务范围 `TASK_AUTHORIZED` | 跨任务导出 `ADMIN_ONLY` + `EXPORT_AUDIT` |
| ST | `ADMIN_ONLY` | 仅 `SUPER_ADMIN`；永不显示密钥/凭据 |

---

## 3. 三端导航

| 视口 | 结构 |
|---|---|
| 桌面 ≥1200 | 左侧固定导航：8 个主入口（含 Intake 流程入口）+ “Operations” 分组展开 4 个治理区域；顶部为搜索/命令面板、新建任务、环境与连接状态、用户与角色 |
| 平板 1024–1199 | 左侧图标轨道（可展开标签），分组与顺序不变；详情页保持主子视图同屏 |
| 平板 768–1023 | 图标轨道 + 覆盖式抽屉；详情页单列，上下文区移到主内容下方；任务子视图仍为 sticky tabs |
| 手机 <768 | 底部 5 项：Mission Control、Tasks、Runs、Devices、More；More 打开 12 区域全量抽屉；任务子视图为横向滚动 sticky tabs |

规则：
1. 一级入口以“持续运营对象”为主；**Intake 是唯一流程例外**：保留在导航中用于发现，但主路径由全局“新建任务”进入，不按监控/运营首页设计。
2. 详情对象（task/run/evidence/report/knowledge/agent/node/device）不占一级。
3. 治理区域不得挤入任务主线第一视觉层；不新增未登记入口。
4. 路由、筛选、页签、详情对象均可深链；基线 `/console/*`，旧 `/aitest/*` 仅作实现期兼容别名。
5. 全局指示器固定四项且互不替代：连接（实时/降级/离线）、待 STOP、对账中、陈旧。
6. IA 级可访问性：导航使用 `nav` 地标与“跳到主内容”链接；Tab 顺序等于阅读顺序；当前区域用 `aria-current`；状态同时有文字/图标/形状，颜色只作第三通道；抽屉、命令面板、全屏接管必须焦点进入与归还；手机触控目标 ≥44×44。
7. 本节固定的是**导航层级与可达性**，不是像素尺寸。P1-03 的 [`ui-design-system.md`](./ui-design-system.md) §7 若仍写横排导航，须按本节回写；在回写前以本节为 IA 契约。

---

## 4. 十二个产品区域与必需状态

> 通用状态（loading / empty / error / no-permission）适用于所有区域，下表只列**差异状态**。状态语义见 §8。

| # | 区域 | 代号 | 回答的问题 | 主要实体 | 差异状态 | 层 |
|---|---|---|---|---|---|---|
| 1 | Mission Control | MC | 平台健康吗？哪里需要我？ | TaskCard、Run、Lease、Evidence、Reconcile | blocked / stale / offline / reconciling / unknown-progress | 一级 |
| 2 | Intake & Revisions | IN | 需求如何变成可审阅的修订？ | Task、TaskRevision、Draft、SourceArtifact | blocked / stale / partial-evidence | 一级（流程入口） |
| 3 | Tasks | TK | 这个任务发生了什么？ | Task、Revision、Approval、Case、Run、Attempt、Verdict | blocked / stale / offline / partial-evidence / unknown-progress | 一级 |
| 4 | Runs & Attempts | RN | 哪些运行在跑、停了、断线、待对账？ | Run、Attempt、StopRequest、Lease、Communication | offline / reconciling / unknown-progress / partial-evidence / blocked | 一级 |
| 5 | Evidence & Verdict | EV | 证据够不够？结论能不能信？ | EvidenceSet、EvidenceItem、Manifest、Verdict | partial-evidence / quarantined / reconciling / blocked | 一级 |
| 6 | Devices & Nodes | DV | 在哪里执行？谁占用？能否释放？ | Node、Device、Lease、Occupancy、CleanupReceipt | draining / quarantined / reconciling / offline / stale | 一级 |
| 7 | Reports & Delivery | RP | 交付了什么？分母与披露范围？ | Report、ReportVersion、EvidenceIndex | partial-evidence / blocked | 一级 |
| 8 | Knowledge | KN | 平台知道什么？可信吗？能推广吗？ | KnowledgeCandidate、KnowledgeItem、Conflict | stale / blocked | 一级 |
| 9 | Runtime & Toolchain | RT | 谁在执行？工具链锁定还是漂移？ | ModelBinding、ToolchainLock、Drift | blocked / stale | Operations |
| 10 | Agents & Reviews | AG | 谁负责什么？评审完成了吗？ | AgentRegistry、ReviewSession、Plugin、Policy | blocked / stale | Operations |
| 11 | Audit & Recovery | AU | 谁做了什么？恢复/对账到哪一步？ | AuditEvent、AccessDecision、Reconcile、Backup | reconciling / blocked / offline | Operations |
| 12 | Settings & Access | ST | 如何配置、授权、保留、通知？ | Role、TaskRelation、FeatureFlag、Retention | blocked | Operations |

任务详情 8 子视图：Overview、Revisions & Approval、Plan & Cases、Runs & Attempts、Evidence、Verdict & Gates、Live（含接管与日志）、Knowledge & Similar。旧“相似/门禁/接管/日志”不再单列。

> §4 的差异状态是**区域聚合**，不能替代逐屏 fixture。每个屏幕的最低状态集见 [附录 A](#附录-a逐屏最低差异状态)，fixture 必须逐屏准备并标注 `source`/`schema_version`/`server_authoritative`。

---

## 5. 路由清单

| 区域 | 路由（ID） |
|---|---|
| MC | `/console`（MC-01） |
| IN | `/console/intake`（IN-01）、`/console/intake/new`（IN-02）、`/console/intake/:draftId`（IN-03） |
| TK | `/console/tasks`（TK-01）、`/console/tasks/:taskId/{overview,revisions,plan,runs,evidence,verdict,live,knowledge}`（TK-02..TK-09） |
| RN | `/console/runs`（RN-01）、`/console/runs/:runId`（RN-02）、`/console/runs/:runId/attempts/:attemptId`（RN-03） |
| EV | `/console/evidence`（EV-01）、`/console/evidence/:evidenceId`（EV-02）、`/console/verdicts`（EV-03） |
| DV | `/console/devices`（DV-01）、`/console/devices/:deviceId`（DV-02）、`/console/nodes/:nodeId`（DV-03） |
| RP | `/console/reports`（RP-01）、`/console/reports/:reportId`（RP-02） |
| KN | `/console/knowledge`（KN-01）、`/console/knowledge/:knowledgeId`（KN-02）、`/console/knowledge/candidates`（KN-03） |
| RT | `/console/runtime/models`（RT-01）、`/console/runtime/toolchain`（RT-02） |
| AG | `/console/agents`（AG-01）、`/console/agents/:agentId`（AG-02）、`/console/reviews`（AG-03） |
| AU | `/console/audit`（AU-01）、`/console/audit/:eventId`（AU-02）、`/console/recovery`（AU-03） |
| ST | `/console/settings`（ST-01）、`/console/settings/{access,notifications,retention}`（ST-02..ST-04） |

口径：**39 条路由（MC 1 + IN 3 + TK 9 + RN 3 + EV 3 + DV 3 + RP 2 + KN 3 + RT 2 + AG 3 + AU 3 + ST 4）**；路由清单 = 导航项 + 详情路由，P1-04 必须产出机器可读 manifest。每条状态/视口结果必须记录视口维度（桌面/平板/手机）与状态 fixture 版本，否则“全部通过”不可复核。默认访问级别见 §2.1；旧 `/aitest/*` 只做兼容别名，不进入新导航。

---

## 6. 四条关键旅程

### J1 Intake → 审批 → 门禁

`IN-01 → IN-02（G0 受理；对话/文件/表单）→ IN-03 草案评审（G0 完成）→ 冻结 → TK-03 审批（G1）→ TK-05/RT-02 静态（G2）→ DV-01/02 资源资格/租约（G3）→ TK-05/RN-02 烟测（G4）→ TK-05/RN-02 正式（G5）→ TK-06/07/EV-03 证据判定（G6）→ RP-02/KN-03（G7）`

必须显示：三入口来源与字段来源、冲突与缺口、冻结范围、父修订、差异、哈希、审批人/意见/范围快照/生效时间、G0–G7 顺序与当前阻塞方（每枚门禁显示 `PENDING/IN_PROGRESS/PASSED/FAILED/BLOCKED/SKIPPED` 与 `blocker.owner`；投影缺失才显示 `UNKNOWN`）。
禁止：静默择一来源；冻结后原地编辑；审批后改范围；超时自动拒绝（正确行为是只提醒与升级，永不自动拒绝）；烟测计入正式分母。

### J2 Task / Revision / Run / Case / Attempt（依赖顺序：Case 随修订冻结，先于 Run）

`TK-01 → TK-02 Overview / TK-03 Revisions → TK-04 Plan & Cases → TK-05 Runs & Attempts → RN-02 Run detail → RN-03 Attempt`

必须显示：`task_id`、`current_revision_id`、修订谱系与父修订；`run_id` 与互斥 `mode`（static/smoke/formal）；稳定 `case_id` + 随修订冻结的 `case_version`；`attempt_ordinal`、`retry_of_attempt_id`、失败分类、五轴逐项、`denominator_eligible`、`FLAKY_SUSPECT`；节点回执事实与 Linux 判定分栏。
禁止：按用例名称合并不同 `case_version`；合并多次 attempt；旧证据并入新修订；烟测/模拟/重放样本进正式分母；把节点回执当平台判定。

### J3 离线续跑 → STOP-first 重连 → 对账

`MC-01 / RN-01 / TK-02 / TK-08 / DV-01 呈现离线组合 → RN-02 运行详情（待 STOP）→ AU-03 恢复与对账`

必须同时显示：`communication=OFFLINE/STALE`、执行可能 `RUNNING`、占用 `OCCUPIED`、`execution_permit=GRANTED`、离线开始时间、最后已知活动、待送达 STOP 的目标与原因。
固定顺序：处理待送达 STOP → 停止后续动作 → 补传 → 去重 → 核对 run/设备/lease/epoch/占用 → 对账完成后恢复领取。
禁止：“已停止”“设备空闲”“可重派”；对账完成前释放或重派；旧 epoch 改写当前运行；重传触发重复执行。

### J4 证据 → Linux 判定 → 报告

`TK-06 / EV-01 / EV-02 证据与 manifest → TK-07 / EV-03 Linux 五轴复核 → RP-01 / RP-02 报告`

必须显示：manifest schema、`expected / received / verified` 三列、digest、kind、size、`collected_at`、按设备/用例分母、访问级别、部分/冲突/未核验；五轴逐项 + `verification_status` + fail-closed 原因；报告 14 章节、分母口径、四类记录分离、披露级别、版本与冻结状态。
节点回执只作“节点观察事实”列（`node_observed_*`、`used_for_decision=false`），不得与 Linux 判定同列或同色；缺 `cleanup_receipt` 只显示“释放未确认、保持占用”，不得据此改 `evidence_status` 或单独判 FAIL。
禁止：已接收即已核验；缺必要证据仍显示 PASS；缺 `cleanup_receipt` 即判证据不完整；默认暴露原始音频/日志/路径/PII；把人工补充记录表述为自动 PASS；把节点自报写成平台判定。

---

## 7. 密度策略：克制 vs 密集

| 区域/屏幕 | 密度 | 理由 | 渐进披露 |
|---|---|---|---|
| MC-01 | **克制** | 一屏回答“健康吗/哪里需要我”，不是监控墙 | 只放异常、待决断、离线/对账/隔离；明细下钻 |
| IN-01..03 | **克制** | 一次处理一个需求，降低输入焦虑 | 三步：来源 → 澄清 → 修订种子；高级字段折叠 |
| TK-01 任务列表 | 中等 | 需要扫描，不需全量字段 | 默认列：任务/修订/阶段/五轴摘要/占用/证据/更新 |
| TK-02 Overview | **克制** | 首屏只给判断与阻断点 | 五轴摘要 + 阻塞方 + 资源；明细进子视图 |
| TK-04 Plan & Cases | **密集** | 用例、步骤、oracle、证据要求必须可审 | 用例表 + 详情抽屉；覆盖矩阵可折叠 |
| TK-05 / RN-01 | **高密集** | 多 run/attempt、五轴、分母、重试需并排比较 | 矩阵 + 筛选 + 行详情；手机转卡片 |
| TK-06 / EV-01/02 | **高密集** | manifest、摘要、大小、时间、访问级别 | 按用例/设备分组；原始内容走受控访问 |
| DV-01..03 | **高密集** | 心跳、端点、租约、占用、隔离、spool | 节点卡 + 设备表 + 详情；危险动作二次确认 |
| RP-02 | **克制（默认）** | 默认读者只看摘要/索引/分母 | 14 章节可展开；受限章节按权限显示 |
| KN-01..03 | 中等 | 检索要快，候选审阅要聚焦 | 结果卡 + 详情；候选队列单列 |
| RT-01/02 | **高密集** | 绑定链、lock、兼容、drift 需精确 | 作用域分段 + 矩阵 + diff |
| AG-01..03 | 中等 | 注册表与评审记录 | 表格 + 详情 + 评审摘要 |
| AU-01..03 | **高密集** | 审计不可变、对账步骤需精确 | 事件表 + before/after + 对账时间线 |
| ST-01..04 | **克制** | 配置不是高频运营 | 分区 + 表单；危险区二次确认 |

原则：**克制不等于省略安全事实**。Mission Control 可以少放图，但不能不显示“离线仍占用”“待 STOP”“证据不完整”“隔离设备”。密集区可用分组、筛选、列设置、抽屉降低负担，但关键事实不得藏到二级页面才出现。

---

## 8. 十二类必需状态

| 状态 | 触发 | 必须 | 禁止 |
|---|---|---|---|
| loading | 首次加载/切筛选/开详情 | 保留标题与动作位的骨架；>1s 给文字进度 | 用旧缓存冒充新结果 |
| empty | 无对象或无匹配 | 说明“没有”还是“无权限”，给主动作 | 把无权限显示成空 |
| error | 请求/投影/摘要失败 | 影响 + 重试 + 请求 ID，保留上下文 | 仅写“出错了”；暴露堆栈/SQL/路径 |
| blocked | 缺批准/指标/资源/门禁失败 | 原因 + 解除条件 + `blocker.owner` + 下一步 | 自动继续；把阻塞当失败 |
| stale | 投影超阈值/事件延迟/缓存回退 | 灰虚线 + 原因 + 最后权威更新 + 最后已知活动 | 用旧数据称“实时” |
| offline | 节点↔控制面通信中断 | 离线徽章 + 执行可能继续 + 保持占用 + 时间 | “已停止”“设备空闲”“可重派” |
| partial-evidence | 部分上传/部分校验/必要证据缺失 | expected/received/verified 三列 + 逐用例缺口 | 显示 PASS；已接收当已核验 |
| no-permission | 服务端 DENY/关系缺失 | 只读摘要 + disabled + 原因 | 隐藏整页；客户端过滤当鉴权 |
| draining | 连续失败/运维排空 | 排空中，不再接新单，已有 run 继续 | 立即重派；等同 quarantined |
| quarantined | 清理失败/危险状态/连续失败 | 隔离 + 保持占用 + 恢复条件与责任人 | 自动恢复/重派；判 PASS/FAIL |
| reconciling | 重连/控制面恢复/占用不确定 | 对账步骤 + 未确认占用 + 禁止新派 | 对账前释放/重派；旧 epoch 改现状 |
| unknown-progress | 总量未知/计数不可靠 | 只给阶段、门禁、已知计数 + “未知”；`percent=null` | 0%、99%、“即将完成”、阶段序号当百分比 |

必须同时成立的组合：`offline + running + occupied`、`stale + running`、`partial-evidence + business PASS`（整体仍不可 PASS）、`reconciling + pending STOP`、`quarantined + occupied`、`draining + running`、`unknown-progress + counts 请求`。

Phase 1 冻结前，每屏至少准备通用四态；任务主线另备 blocked/stale/offline/partial-evidence/unknown-progress；运行与设备另备 draining/quarantined/reconciling。fixture 必须标注 `source`、`schema_version`、`server_authoritative`，不得用静态截图冒充。逐屏最低集见附录 A。

### 8.1 状态的 IA 级可访问性约束

1. **不只靠颜色**：12 类状态与五轴必须同时有文字、图标/形状、颜色；颜色遮住后仍可区分 PASS/FAIL/BLOCKED/PENDING/UNKNOWN/OFFLINE/STALE/QUARANTINED/RECONCILING/RELEASED/NO ACCESS。
2. **语义结构**：五轴矩阵、门禁时间线、证据分母、释放前置必须用带 `caption`/`th scope` 的语义表格或等价结构；移动端不得把五轴压成 5 个窄列。
3. **动态播报**：离线、待 STOP、对账进度用 `aria-live="polite"` 合并播报，只在语义变化时播报，不得每秒打断。
4. **焦点与缩放**：8 子视图切换、抽屉、命令面板、全屏接管必须有焦点进入/归还；200% 缩放下五轴、证据分母、释放前置不得被裁切，允许局部横向滚动。
5. **禁用原因**：`no-permission`/`blocked`/`draining`/`quarantined` 的 disabled 动作必须用 `aria-describedby` 或可见文本解释，不能只降透明度。

---

## 9. 来源追溯

| 本文内容 | 来源 |
|---|---|
| 12 区域、8 子视图、导航、路由、密度、离线/STOP/释放旅程、12 状态 | [`ui-baseline-gap-analysis.md`](./ui-baseline-gap-analysis.md) §4–7；[`ui-screen-specification.md`](./ui-screen-specification.md) §0–2 |
| PostgreSQL 唯一正式库与全部权威写入方 | [`domain.md`](../contracts/domain.md) §17 第 1 条；[`README.md`](../contracts/README.md) §4 |
| 五轴枚举、正式 PASS 五条件、租约/断线/STOP-first/释放前置 | [`domain.md`](../contracts/domain.md) §9、§14、§15 |
| 五轴与设备释放/证据/判定的三平面分离；缺回执精确语义 | [`evidence-verdict.md`](../contracts/evidence-verdict.md) §2、§12.3、§13、§14 |
| Receipt 只含事实、节点不得写判定 | [`domain.md`](../contracts/domain.md) §12；[`README.md`](../contracts/README.md) §4 |
| 角色、任务关系、访问级别、求值顺序、区域访问映射 | [`ui-report-knowledge-audit.md`](../contracts/ui-report-knowledge-audit.md) §6 |
| TaskCard 投影、stale/断连、投影词汇 | [`ui-report-knowledge-audit.md`](../contracts/ui-report-knowledge-audit.md) §2、§7 |
| 报告 14 章节、四类记录、分母、披露 | [`ui-report-knowledge-audit.md`](../contracts/ui-report-knowledge-audit.md) §3 |
| 知识候选/条目生命周期、审计不可变 | [`ui-report-knowledge-audit.md`](../contracts/ui-report-knowledge-audit.md) §4–5 |
| 三入口、审批、烟测/正式分离、fail-closed、报告默认摘要 | [`requirements-baseline`](../../.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md) §1–15 |
| M-01..M-21、Case 管理、设备池、会话桥 | [`module-design`](../../.omo/drafts/01-design/noahsark-v0.0.1-module-design.md) §1–4 |
| G0–G7 落点、五轴/门禁/状态视觉通道、断点与密度 | [`ui-design-system.md`](./ui-design-system.md) §5、§7 |
| AC-1..AC-14、L0–L5、离线/释放/恢复验收 | [`delivery-acceptance`](../../.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md) §2–4 |
| P1-02/P1-04 范围、UI 阶段闸门 | [`noahsark-platform-delivery.md`](../../.omo/plans/noahsark-platform-delivery.md) Phase 1 |

---

## 10. 决策记录、未决与出口标准

### 10.1 建议在 P1-02 冻结的 IA 决策

| ID | 决策 | 可复核证据 |
|---|---|---|
| D-IA-01 | 采用 12 区域：8 个主入口 + 4 个 Operations 治理入口 | §0、§4；与差距分析 A-08 一致 |
| D-IA-02 | Intake 作为唯一流程入口保留导航，但主路径由全局“新建任务”进入 | §0、§3 规则 1 |
| D-IA-03 | 任务详情固定 8 子视图，旧 11 页签不再作为目标 | §4、§5 |
| D-IA-04 | 路由基线 `/console/*`，共 39 条；旧 `/aitest/*` 只作实现期兼容别名 | §5 |
| D-IA-05 | 三端导航骨架：桌面左侧固定、平板图标轨道（两个子区间）、手机底部 5 项 | §3；P1-03 需回写设计系统 §7 |
| D-IA-06 | 五轴不折叠；通信/占用/执行许可/释放/新鲜度独立显示 | §1、§8 组合矩阵 |
| D-IA-07 | 采用 12 类必需状态与逐屏最低集 | §8、附录 A |
| D-IA-08 | 密度策略：MC/Intake/Overview/Reports 默认/Settings 克制，运行/证据/设备/Runtime/Audit 高密集 | §7 |
| D-IA-09 | 权限 fail-closed；默认访问级别按 §2.1，UI 只降级不提升 | §2、§2.1 |

### 10.2 仍需裁决的问题

| ID | 问题 | 需要谁决定 | 影响 |
|---|---|---|---|
| Q-01 | 视觉方向：v2 Voyage Ledger、Apple v3 Quiet Instrument，还是混合？ | 用户/P1-02 | 令牌、组件、视觉 |
| Q-02 | 12 区域是否收敛为 10（Reports→Tasks、Agents→Settings）？ | IA 评审 | 导航复杂度；若收敛，路由与权限矩阵同步改 |
| Q-03 | `/aitest/*` 兼容期多长、是否 301？ | 实现/运维 | 深链与迁移 |
| Q-04 | 全局深色模式 V0.0.1 做还是延后？ | 用户/P1-02 | 令牌、验收 |
| Q-05 | Push 是否保留 ST-03 独立子页？ | 产品 | ST-03 范围 |
| Q-06 | Roundtable 归 AG-03 还是任务详情内嵌？ | 产品/架构 | AG-03 与 TK 子视图 |
| Q-07 | Reports 是否提供打印/PDF 表面？ | 交付 | RP-02、分页规则 |
| Q-08 | 审计/恢复是否仅 SUPER_ADMIN 可见？ | 权限/安全 | AU-01..03 默认访问 |
| Q-09 | RT/AG 默认访问级别未在契约 §6.4 定义；候选见 §2.1 | 权限/架构 | RT、AG 的读写动作 |
| Q-10 | `blocker.owner` 默认显示具体人还是角色？ | 产品 | 全部 blocked 状态 |
| Q-11 | 设计系统 §7 的横排导航/断点描述与本节左侧导航冲突 | P1-03 | 断点与外壳实现 |
| Q-12 | `PUBLIC_SUMMARY` 保留还是删除？ | 产品/安全 | 访问级别枚举 |

### 10.3 Phase 1 出口标准（P1-02 评审用）

- [ ] 12 区域、8 子视图、39 条路由逐项确认，无未登记入口。
- [ ] 三端导航层级与断点确认；P1-03 已接受按 §3 回写设计系统 §7。
- [ ] §2.1 区域访问级别确认，尤其 Q-08/Q-09。
- [ ] 附录 A 逐屏最低状态集确认，并能映射到可构造 fixture。
- [ ] 四条旅程的每一步都有屏幕落点与禁止声明。
- [ ] 与 `docs/contracts/` 无字段/枚举冲突；冲突项已登记而非在 UI 内猜测。
- [ ] 未决 Q-01..Q-12 有明确 owner 与截止点；未决项不得被实现方自行补全。

### 10.4 边界与下一步

- 本文**不**冻结设计令牌、视觉方向、色板、字体、动效（P1-03）；**不**提供状态 fixture、截图或 a11y 实测（P1-05..P1-07）。
- 本文**不**批准契约：`docs/contracts/` 仍为 `frozen-candidate v1`；契约冻结前，字段名与枚举以契约为准。
- 下一步：P1-02 按 §10.3 评审角色/导航/区域边界/访问级别；通过后进入 P1-03 设计系统与 P1-04 线框。评审通过前不得声称 UI 冻结或进入 P5-08 实现。

---

## 附录 A：逐屏最低差异状态

> 通用 `loading / empty / error / no-permission` 对所有屏适用，下表只列**差异状态**。行是屏幕族的最低覆盖集；族内每屏按 [`ui-baseline-gap-analysis.md`](./ui-baseline-gap-analysis.md) §4.3 的具体屏幕状态分配，不得用族级聚合替代逐屏 fixture。

| 屏幕族 | 路由 ID | 必须覆盖的差异状态 |
|---|---|---|
| Mission Control | MC-01 | blocked、stale、offline、reconciling、unknown-progress |
| Intake | IN-01..IN-03 | blocked、stale、partial-evidence |
| Task 列表/概览/修订/计划/知识 | TK-01..TK-04、TK-09 | blocked、stale、offline、partial-evidence、unknown-progress |
| Run Monitor | TK-05、TK-08、RN-01..RN-03 | offline、reconciling、unknown-progress、partial-evidence、blocked |
| Evidence Browser | TK-06、EV-01..EV-02 | partial-evidence、quarantined |
| Verdict & Report | TK-07、EV-03、RP-01..RP-02 | blocked、partial-evidence、quarantined、reconciling |
| Devices & Nodes | DV-01..DV-03 | draining、quarantined、reconciling、offline、stale |
| Knowledge | KN-01..KN-03 | stale、blocked |
| Runtime & Toolchain | RT-01..RT-02 | blocked、stale |
| Agents & Reviews | AG-01..AG-03 | blocked、stale |
| Audit & Recovery | AU-01..AU-03 | reconciling、blocked、offline |
| Settings & Access | ST-01..ST-04 | blocked |
