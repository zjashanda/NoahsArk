# NoahsArk Phase 1 屏幕与线框规格包（Screen / Wireframe Specification）

> 版本：v0.2（2026-10-29）
> 状态：**Phase 1 屏幕规格候选（decision-ready draft）**，供 P1-02/P1-04 评审与线框使用。**不是 UI 设计冻结件，不是实现授权，也不代表视觉截图 QA 已执行或通过。**
> 范围：与 IA v0.3 对齐的 12 个区域 / 39 条路由 / 任务详情 8 子视图；11 个屏幕族 + RT/AG Operations adjunct 的逐屏目的、动作、数据、状态、响应式、证据与权限边界；G0–G7 屏幕落点；AC-1..AC-14 与 L0–L5/T1–T6 追溯；本文决策与未决项。
> 事实源：`docs/delivery/ui-information-architecture.md`（IA v0.3）、`docs/delivery/ui-design-system.md`、`docs/delivery/ui-baseline-gap-analysis.md` §4–§5、`docs/contracts/domain.md`、`docs/contracts/ui-report-knowledge-audit.md`、`docs/contracts/evidence-verdict.md`、`.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md`、`.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md`、`.omo/plans/noahsark-platform-delivery.md` Phase 1。
> 非授权边界：只改本文件与 `docs/delivery/progress/ui-screens.progress.md`；不修改 `design/`、`docs/v2/`、契约、`.omo` 状态、`plan.md` 或产品代码；不提交、不推送；不宣称 UI 冻结、实现完成或视觉 QA 通过。

---

## 0. 判读规则（所有屏幕共用）

1. **Linux 权威、Windows 只报事实**：Task/Revision/Approval/Gate/Run/Attempt/Case/Verdict/Lease/Device/Node/Evidence 由 Linux 控制面唯一权威写入。Windows 回执只以 `node_observed_*` + `used_for_decision=false` 展示，**不得渲染为 `business_verdict`、`verification_status` 或平台 PASS/FAIL**；节点事实与平台判定必须分栏/分行、异色异形。
2. **五轴不折叠**：`execution_status` / `validity_status` / `business_verdict` / `evidence_status` / `verification_status` 逐项显示。正式 PASS 仅当五轴为 `COMPLETED / VALID / PASS / COMPLETE / PASS`；任一不满足即不得显示正式 PASS，按权威值显示具体轴值或 `BLOCKED`/`NEEDS_REVIEW`/无效分类。`COMPLETED`、`SKIPPED`、`EXPECTED`、设备 `RELEASED` 都不是 PASS。
3. **四信号 + 新鲜度分离**：`communication_state`、`occupancy_state`、`execution_permit`、`execution_status` 及投影 `freshness` 分别显示；`OFFLINE` 不得渲染为“已停止”“设备空闲”“可重派”。`STALE` 附原因与最后权威更新，阈值由服务端下发，UI 不写死。
4. **离线 / STOP-first / 对账**：已启动冻结压测断线继续；重连顺序固定为“处理待 STOP → 停止后续动作 → 补传 → 去重 → 对账 → 恢复领取”。对账完成前保持占用、禁止新派发；旧 `epoch` 只作历史事实，不得改变当前运行。
5. **释放 / 证据 / 判定分离**：释放仅依赖 `local_stop_confirmed` + `safe_cleanup_done` + `occupancy_reconciled`，并须满足节点可达或现场确认（R-05）；不等待大日志归档或最终判定。缺 `cleanup_receipt` = 占用未对账、保持占用，**不等于 `evidence_status=INCOMPLETE`**；PASS 与 `release_state=held` 可并存；释放 ≠ 通过。
6. **未知即未知**：`progress.mode` 仅 `COUNTS / QUALITATIVE / INDETERMINATE`。仅 `COUNTS` 且已批准分母可出 `percent`；其余显示“未知”，禁止 0%、99%、“即将完成”、阶段序号冒充百分比。`percent_label` 不得写成“任务完成度”。
7. **权限 fail-closed**：求值顺序 `显式 DENY → 显式 ALLOW → 默认 DENY`；未知角色/关系/策略一律 DENY。服务端裁剪后才下发；无权限保留只读摘要 + disabled 动作 + 原因，不隐藏整页；客户端隐藏不构成访问控制。
8. **状态集合**：通用 `loading / empty / error / no-permission` 适用于所有屏；差异状态按族列出，逐屏最低集以 IA 附录 A 为准。fixture 必须标注 `source`、`schema_version`、`server_authoritative`，静态截图不算 fixture。
9. **响应式四档**：≥1200 左侧固定导航（8 主入口 + Operations 4 治理入口）；1024–1199 图标轨道可展开；768–1023 图标轨道 + 覆盖式抽屉、详情单列；<768 底部 5 项（MC/Tasks/Runs/Devices/More）。主滚动区唯一；导航、顶栏、状态条、底部 Tab 固定。
10. **危险动作**（释放、隔离、恢复、推广、冻结、删除/保留变更）必须二次确认、写结果动词、显示前置条件与不可用原因。禁止文案：把 mock/dry-run/replay/烟测写成真实执行或正式样本；把“已接收”写成“已核验”；把未演练恢复写成达到 RPO/RTO。

---

## 1. 路由矩阵（39 条，IA v0.3 §5）

| 区域 | 路由 ID 与路径 | 详细规格 | 默认访问 | 主要读者 |
|---|---|---|---|---|
| Mission Control | MC-01 `/console` | §2.1 | `TASK_AUTHORIZED` | 全部角色 |
| Intake | IN-01 `/console/intake`、IN-02 `/console/intake/new`、IN-03 `/console/intake/:draftId` | §2.2 | `TASK_AUTHORIZED` | Submitter、Session Manager |
| Tasks | TK-01 `/console/tasks`、TK-02..TK-09 `/console/tasks/:taskId/{overview,revisions,plan,runs,evidence,verdict,live,knowledge}` | §2.3–§2.9 | `TASK_AUTHORIZED`；审批另需 `APPROVE_TASK` | 全部角色 |
| Runs & Attempts | RN-01 `/console/runs`、RN-02 `/console/runs/:runId`、RN-03 `/console/runs/:runId/attempts/:attemptId` | §2.5 | `TASK_AUTHORIZED`；原始日志 `EVIDENCE_AUTHORIZED` | 全部角色 |
| Evidence | EV-01 `/console/evidence`、EV-02 `/console/evidence/:evidenceId`、EV-03 `/console/verdicts` | §2.7、§2.8 | 元数据 `SUMMARY_INDEX`；原始 `EVIDENCE_AUTHORIZED` | 全部角色；原始仅授权读者 |
| Devices & Nodes | DV-01 `/console/devices`、DV-02 `/console/devices/:deviceId`、DV-03 `/console/nodes/:nodeId` | §2.6 | 元数据 `TASK_AUTHORIZED`；控制 `ADMIN_ONLY`（`NODE_CONTROL`/`DEVICE_CONTROL`） | Operator、Admin |
| Reports | RP-01 `/console/reports`、RP-02 `/console/reports/:reportId` | §2.8 | `SUMMARY_INDEX`；明细 `TASK_AUTHORIZED` | 全部角色 |
| Knowledge | KN-01 `/console/knowledge`、KN-02 `/console/knowledge/:knowledgeId`、KN-03 `/console/knowledge/candidates` | §2.9 | `SUMMARY_INDEX`；治理另需能力 | 全部角色 |
| Runtime & Toolchain | RT-01 `/console/runtime/models`、RT-02 `/console/runtime/toolchain` | §2.12 | **待裁决 Q-09**（候选读 `TASK_AUTHORIZED`、写 `ADMIN_ONLY`） | Admin、Operator |
| Agents & Reviews | AG-01 `/console/agents`、AG-02 `/console/agents/:agentId`、AG-03 `/console/reviews` | §2.12 | **待裁决 Q-09**（候选同上） | Admin、Approver |
| Audit & Recovery | AU-01 `/console/audit`、AU-02 `/console/audit/:eventId`、AU-03 `/console/recovery` | §2.10 | 任务范围 `TASK_AUTHORIZED`；导出 `ADMIN_ONLY` | 全部角色；导出仅 Admin |
| Settings & Access | ST-01 `/console/settings`、ST-02 `/console/settings/access`、ST-03 `/console/settings/notifications`、ST-04 `/console/settings/retention` | §2.11 | `ADMIN_ONLY` | Super Admin |

> 口径：39 条 = MC 1 + IN 3 + TK 9 + RN 3 + EV 3 + DV 3 + RP 2 + KN 3 + RT 2 + AG 3 + AU 3 + ST 4。P1-04 必须据此生成机器可读 manifest；路由、筛选、页签、详情对象均可深链。旧 `/aitest/*` 只作实现期兼容别名；本文旧版 `/:taskId/*` 短路径作废，不得进入实现。

---

## 2. 屏幕规格

### 2.1 MC-01 Mission Control `/console`

- **目的**：一屏回答“平台健康吗、哪里需要我”；只呈现异常、待决断、离线、对账中、隔离设备，不做全量监控墙。
- **主/次动作**：主 = 打开阻塞任务 / 处理待 STOP / 查看对账；次 = 按区域筛选、下钻任务/运行/设备、确认告警。
- **关键数据**：TaskCard 的 `task_id`、`task_title`、`stage`、`run_state`、`gates[].status`、`blocker.owner`、`progress.mode/percent/counts`、`resources.occupancy_state`、`communication.state`、`freshness.is_stale`、`last_authoritative_update.at`、`last_known_at`；待 STOP 队列；`RECONCILING` 范围；隔离设备数。
- **必备状态**：`blocked` / `stale` / `offline` / `reconciling` / `unknown-progress`（+ 通用四态）。
- **响应式**：≥1200 三栏（需我处理 / 运行中 / 平台健康）；1024–1199 两栏；768–1023 单列，上下文区下移；<768 单列卡片 + 底部导航。
- **证据/权限边界**：仅投影摘要，无原始证据；离线/陈旧徽章追加而非改写执行/占用；无权限保留只读摘要 + disabled 原因；不显示 `server_metadata` 或投影游标。

### 2.2 IN-01..IN-03 Intake `/console/intake/*`

- **目的**：把对话/文件/表单三入口归一为任务草稿（`entry_mode` 全枚举以 domain §4.1 为准），显式呈现抽取、继承、推导、冲突与缺口，再生成可审阅修订种子。
- **主/次动作**：主 = 创建草稿、提交审阅、生成修订种子；次 = 附加来源、比较来源、丢弃草稿。
- **关键数据**：`entry_mode`、`origin.raw_input_refs`（含 digest）、字段来源标记、冲突/缺口清单、`normalization_digest`、`task_id`、`stage=DRAFT`、`blocker.owner`、`freshness`。
- **必备状态**：族级 `blocked` / `stale` / `partial-evidence`；逐屏另需：IN-01 `empty`/`error`/`no-permission`，IN-02 `loading`/`error`/`partial-evidence`，IN-03 `empty`/`blocked`/`stale`/`no-permission`。
- **响应式**：三步向导（来源 → 澄清 → 修订种子）；≥1200 来源与表单并排；1024–1199 保持并排收窄；768–1023 单列；<768 一步一屏 + sticky 下一步。
- **证据/权限边界**：`TASK_AUTHORIZED`；跨任务无关系默认 DENY；不展示代理内部推理或未脱敏原文；冲突不得静默择一继续；不展示服务端会话游标。

### 2.3 TK-01..TK-04、TK-09 Task / Revision

- **目的**：呈现任务身份、修订谱系、冻结范围、差量、计划与用例；列表用于扫描，详情用于判断“现在到哪、谁在卡”。
- **主/次动作**：主 = 打开当前修订、请求审批、派生新修订；次 = 比较修订、筛选、导出只读摘要。
- **关键数据**：稳定 `task_id`、`current_revision_id`、`revision_number`（R-n）、`parent_revision_id`、`change_kind`、`frozen_scope` 与 `content_digest`、审批绑定、`case_id`/`case_version`、oracle、`required_evidence`、`blocker.owner`。
- **必备状态**：`blocked` / `stale` / `offline` / `partial-evidence` / `unknown-progress`；旧修订强制只读。
- **响应式**：≥1200 任务表 + 8 个固定子视图（Overview、Revisions & Approval、Plan & Cases、Runs & Attempts、Evidence、Verdict & Gates、Live、Knowledge & Similar）；1024–1199 同构收窄；768–1023 单列 + sticky tabs；<768 任务卡 + 横向滚动 sticky tabs。
- **证据/权限边界**：`TASK_AUTHORIZED`；审批意见可见，原始证据只给索引与跳转（EV 二次鉴权）；冻结后禁止原地编辑，范围变化派生同任务新修订；不展示内部 ID/签名。

### 2.4 Approval & Gates（TK-03 审批区 + 全屏门禁落点）

- **目的**：展示绑定冻结内容摘要与范围快照的**唯一有效审批**，以及 G0→G7 顺序门禁、当前阻塞方与 fail-closed 原因。
- **主/次动作**：主 = 批准/拒绝（意见必填）、请求解除阻塞（服务端执行）；次 = 查看范围快照、差量、审计链、请求重新检查。
- **关键数据**：`approver_id`、`decision`、`comment`、`revision_content_digest`、`scope_snapshot`、`effective_at`（wait timer）、`self_approval` / `prevent_self_review`、超时提醒/升级（永不自动拒绝）；`gate_code`、`order_index`、`status`、`blocker_owner`、`evidence_refs`；G4 独立 `mode=smoke` run。
- **必备状态**：`blocked` / `stale` / `offline` / `partial-evidence` / `unknown-progress` / `no-permission` / `reconciling` / `quarantined`（G3/G5 重检）。
- **响应式**：≥1200 门禁时间轴 + 侧栏详情；1024–1199 双列收窄；768–1023 单列；<768 纵向 stepper / 折叠面板，瓦片触控 ≥44×44。
- **证据/权限边界**：`TASK_AUTHORIZED` + `APPROVE_TASK`；门禁只由 Linux 写入，UI 不得据投影标记 PASS；`PASSED ≠ business PASS`；`SKIPPED` 需真人原因且 G1/G5/G6 不得跳过；G4 烟测永不进入正式分母。

### 2.5 TK-05 / TK-08 / RN-01..RN-03 Run Monitor

- **目的**：显示哪些 run/attempt 在运行、停止、离线、待对账；每个 run/attempt 的五轴、分母资格、重试与接管事实。
- **主/次动作**：主 = 打开 run、请求 STOP、查看 attempt；次 = 按 mode/lifecycle 筛选、只读事件回放、查看重连/对账状态。
- **关键数据**：`run_id`、`mode`（static/smoke/formal）、`lifecycle_status`、五轴、`communication_state`、`occupancy_state`、`execution_permit`、`formal_denominator_eligible` / `denominator_eligible`、`attempt_ordinal`、`retry_of_attempt_id`、`flaky_suspect`、`stop_requested_at`、`last_heartbeat_at`；节点事实与 Linux 判定分列。
- **必备状态**：`offline` / `reconciling` / `unknown-progress` / `partial-evidence` / `blocked`。
- **响应式**：≥1200 run×attempt 矩阵；1024–1199 精简列；768–1023 run 卡 + 行详情；<768 run 卡 → attempt 列表；Live 日志独立全屏。
- **证据/权限边界**：`TASK_AUTHORIZED`；原始日志需 `EVIDENCE_AUTHORIZED`；`OFFLINE + RUNNING + OCCUPIED + permit GRANTED` 必须同时可见；待 STOP 不得显示为已执行；未知总量不显示百分比；烟测/模拟/回放不进入正式分母。

### 2.6 DV-01..DV-03 Devices & Nodes

- **目的**：回答在哪里执行、设备是否可用/被谁占用/能否释放；节点心跳、会话、端点、spool 与设备池状态分开展示。
- **主/次动作**：主 = 请求释放（三项前置 + R-05 全真时）、隔离/恢复（控制能力）、重新健康检查；次 = 查看 lease/epoch、端点集、spool、心跳、占用。
- **关键数据**：`node_id` / `device_id`、`pool_state`、`health_state`、`communication_state`、`occupancy_state`、`current_lease_id` / `epoch`、`release_preconditions`（`local_stop_confirmed`、`safe_cleanup_done`、`occupancy_reconciled`）、`cleanup_receipt_id`、`spool.state`、`interactive_session.state`、`last_heartbeat_at`。
- **必备状态**：`draining` / `quarantined` / `reconciling` / `offline` / `stale`。
- **响应式**：≥1200 节点卡 + 设备表；1024–1199 精简列；768–1023 单列；<768 设备列表；危险动作二次确认并逐项展示前置条件。
- **证据/权限边界**：元数据 `TASK_AUTHORIZED`；控制 `ADMIN_ONLY` + `NODE_CONTROL`/`DEVICE_CONTROL`（`SESSION_MANAGER` 或 `SUPER_ADMIN`）；序列号脱敏；`OFFLINE ≠ IDLE`；缺 `cleanup_receipt` 保持 `OCCUPIED` 且拒绝确认释放；R-05 = 节点可达或现场确认；释放状态与判定状态分开显示。

### 2.7 TK-06 / EV-01 / EV-02 Evidence Browser

- **目的**：浏览证据索引与 manifest 元数据，显示期望/已接收/已核验三列、digest、采集时间与访问级别；原始内容按需鉴权。
- **主/次动作**：主 = 打开 manifest、请求原始访问、重试校验；次 = 按 case/设备/kind 过滤、复制 digest、查看访问审计。
- **关键数据**：`evidence_id`、`manifest_id`、`kind`、`size`、`collected_at`、`digest`、节点回执引用、`access_level`、`expected/received/verified`、`evidence_status` 四值 `COMPLETE/INCOMPLETE/CONFLICTED/UNVERIFIED`、证据项状态（`declared→uploading→partial→complete→verified`；旁支 `conflicted/unavailable/quarantined`）、`display_path_hint`。
- **必备状态**：`partial-evidence` / `quarantined`（+ 通用四态）。
- **响应式**：≥1200 三列计数 + manifest 表；1024–1199 精简列；768–1023 按 case 分组；<768 按 case 分组卡片；原始查看器独立全屏。
- **证据/权限边界**：TK-06 元数据 `TASK_AUTHORIZED`；EV-01/02 元数据 `SUMMARY_INDEX`；原始 `EVIDENCE_AUTHORIZED` 且允许/拒绝均审计；`OBSERVER` 对原始材料显式 DENY；永不展示绝对路径、凭据、原始音视频于默认载荷；“已接收”≠“已核验”；大日志未归档独立标注、不阻断证据上传。

### 2.8 TK-07 / EV-03 / RP-01..RP-02 Verdict & Report

- **目的**：回答“能否 PASS、卡在哪”，并呈现冻结报告的 14 章节、分母口径、四类记录分离与披露级别。
- **主/次动作**：主 = 复核五轴与 fail-closed 原因、生成/冻结报告、打开证据索引；次 = 筛选复核队列、导出摘要（Admin + 审计）、比较报告版本。
- **关键数据**：五轴、`verification_status`、fail-closed 原因、`denominator`（总量 + `per_device` / `per_case`）、`record_separation` 常量、`disclosure` 四类标志、报告版本/lifecycle、14 个 `category`、`evidence_index`、`release_state`。
- **必备状态**：`blocked` / `partial-evidence` / `quarantined` / `reconciling`。
- **响应式**：≥1200 verdict 头部 + 章节 TOC；1024–1199 双列；768–1023 单列；<768 摘要优先、章节折叠、证据索引转卡片。
- **证据/权限边界**：TK-07 明细 `TASK_AUTHORIZED`；EV-03/RP-01/02 默认 `SUMMARY_INDEX`；受限章节占位不预加载；原始材料 `EVIDENCE_AUTHORIZED`；报告冻结后不可原地改，更正走新版本；五轴或批准/门禁/证据缺一不得 PASS；设备释放独立于报告；缺清理回执可 PASS 但必须同时显示“释放未确认”。

### 2.9 KN-01..KN-03、TK-09 Knowledge

- **目的**：检索已批准知识，并审阅候选的来源、适用性、冲突与状态；候选与条目视觉权重必须区分。
- **主/次动作**：主 = 审阅候选（approve / reject / needs info）、人工推广（目标库权限）；次 = 检索过滤、应用到草案修订、标记 stale/disputed。
- **关键数据**：候选 `status`（`PROPOSED → UNDER_REVIEW ↔ NEEDS_INFO → APPROVED → PROMOTED`；另有 `REJECTED`/`DUPLICATE`/`WITHDRAWN`/`SUPERSEDED`）、来源链、`applicability`、`review`、`promotion.automatic_allowed=false`、`promotion.requires_human_review=true`；条目状态 `APPROVED/CORROBORATED/DISPUTED/STALE/RETRACTED/SUPERSEDED/EXPIRED`。
- **必备状态**：`stale` / `blocked`（+ 通用四态）。
- **响应式**：≥1200 结果 + 详情侧栏；1024–1199 同构收窄；768–1023 列表 → 详情；<768 列表 → 详情；候选治理队列单列。
- **证据/权限边界**：TK-09 `TASK_AUTHORIZED`；KN-01..03 `SUMMARY_INDEX`；推广必须人类 + 目标库权限（`KNOWLEDGE_MERGE_COMMON`/`KNOWLEDGE_MERGE_TOOL`/`KNOWLEDGE_PROMOTE_ANOMALY`）+ 审计，无 `PROPOSED → PROMOTED` 捷径；生成者不得是唯一批准者；“应用到计划”只生成草案修订，需再次审批；stale/disputed 必须在列表行可见。

### 2.10 AU-01..AU-03 Audit & Recovery

- **目的**：回答谁做了什么、允许/拒绝、before/after 与哈希链；并显示恢复、对账与 STOP-first 进度。
- **主/次动作**：主 = 检索事件、打开事件详情、执行恢复演练（Admin）；次 = 按任务范围过滤、导出（Admin + `EXPORT_AUDIT`）、查看对账时间线。
- **关键数据**：`occurred_at` / `recorded_at`、`actor.role`、`action`、`object`、`change.before/after`（受限）、`reason`、`access_decision`、`integrity` 哈希链；对账六步；备份演练结论。
- **必备状态**：`reconciling` / `blocked` / `offline`。
- **响应式**：≥1200 事件表 + 详情；1024–1199 双列；768–1023 列表 → 详情；<768 列表 → 详情；恢复时间线纵向排列。
- **证据/权限边界**：任务范围 `TASK_AUTHORIZED` + `VIEW_AUDIT`；跨任务导出 `ADMIN_ONLY` + `EXPORT_AUDIT`，导出本身产生审计；审计不可编辑/删除，更正走补偿事件；未演练不得声称 RPO/RTO；恢复顺序固定 数据库 → manifest/摘要 → 任务/运行 → 设备占用对账。

### 2.11 ST-01..ST-04 Settings & Access

- **目的**：配置角色、任务关系、能力、保留与通知；展示策略与字段可见性，但不暴露密钥。
- **主/次动作**：主 = 编辑设置、分配角色/关系、修改保留策略；次 = 查看策略版本/生效时间、通知投递与死信、跳转审计。
- **关键数据**：role、task relation、`access_level`、capability、`policy_id` / 版本 / `effective_at`、retention policy、feature flag、delivery/dead-letter、脱敏配置。
- **必备状态**：`blocked`（+ 通用四态）。
- **响应式**：≥1200 分区导航 + 表单；1024–1199 双列；768–1023 单列；<768 折叠面板；危险区（保留/删除/角色）二次确认。
- **证据/权限边界**：`ADMIN_ONLY` + `MANAGE_SETTINGS`/`MANAGE_ROLES`；永不显示私钥、证书、令牌或真实凭据；变更写 `SETTINGS_CHANGE` / `ROLE_CHANGE` / `DATA_RETENTION_CHANGE` 审计；客户端隐藏不构成访问控制。

### 2.12 RT-01/02、AG-01..03 Operations adjunct（IA 级，细节延后）

- **目的**：RT 回答运行时/工具链是否锁定、哪里漂移；AG 回答 Agent 职责、评审共识与风险。
- **主/次动作**：只读查看绑定链、lock、drift、注册表、评审记录；任何写入动作按 §1 待裁决访问级别执行。
- **关键数据**：`ModelBinding`、`ToolchainLock`、`Drift`；`AgentRegistry`、`ReviewSession`、`Plugin`、`Policy`。字段级契约未在本目录冻结，UI 不得自造枚举。
- **必备状态**：`blocked` / `stale`。
- **响应式**：高密集矩阵/表格，按四档断点降级；768–1023 单列；<768 列表 → 详情。
- **证据/权限边界**：IA §2.1 标记 **待裁决 Q-09**；只读候选 `TASK_AUTHORIZED`、写入候选 `ADMIN_ONLY`，裁决前不得实现写入。本族只登记路由与屏幕责任，逐屏字段/动作留给 P1-04 backlog，**不是静默删减**。

---

## 3. G0–G7 门禁落点

| 门禁 | 名称 | 屏幕落点 | 必须显示 | 禁止 |
|---|---|---|---|---|
| G0 | 受理审阅 | IN-02 / IN-03 | 三入口来源、字段来源、冲突/缺口、`blocker.owner` | 静默择一来源；未审阅即冻结 |
| G1 | 冻结批准 | TK-03 | 冻结内容摘要、范围快照、审批人/意见/生效时间、wait timer | 审批后改范围；超时自动拒绝 |
| G2 | 静态检查 | TK-05 / RT-02 | `mode=static` run、检查项、失败分类 | 用静态检查声称真机可用 |
| G3 | 资源资格与租约 | DV-01 / DV-02 | lease/epoch、占用、端点、健康、隔离 | 到期即释放；离线当空闲 |
| G4 | 真机烟测 | TK-05 / RN-02 | 独立 `mode=smoke` run、烟测证据标识 | 进入正式分母；产生正式 PASS |
| G5 | 正式采样 | TK-05 / RN-02 | `mode=formal`、分母资格、逐设备结果 | 拼入烟测/模拟/回放样本 |
| G6 | 证据复核与判定 | TK-06 / TK-07 / EV-03 | 五轴、`verification_status`、fail-closed 原因 | 未复核即 PASS；已接收当已核验 |
| G7 | 报告/知识 | RP-02 / TK-09 / KN-03 | 14 章节、分母、记录分离、候选状态 | 候选自动推广；报告原地改 |

> 权威状态只有 `PENDING / IN_PROGRESS / PASSED / FAILED / BLOCKED / SKIPPED`；投影缺失才显示 `UNKNOWN`。**没有任何单一屏幕“拥有”G0–G7**；门禁瓦片按 §2.4 呈现，落点按本表。

---

## 4. AC-1..AC-14 追溯

| AC | 验收要点 | 关键屏幕 | 规格落点 | 证明层级 | 测试层 |
|---|---|---|---|---|---|
| AC-1 | 三入口归一、审阅、冻结、一次批准 | IN-01..03、TK-03 | §2.2、§2.4 | L1 + L5 | T2/T3/T5 |
| AC-2 | 单 lead、可恢复会话、独立任务卡、stale | MC-01、TK-02 | §2.1、§2.3 | L2 + L5 | T3/T4 |
| AC-3 | static/smoke/formal 分离、烟测不入分母、逐设备结果 | TK-05、RN-01..03 | §2.5 | L2 + L4 | T1/T4/T6 |
| AC-4 | 无效分类、缺证据 fail-closed | TK-04、TK-06、EV-03 | §2.3、§2.7、§2.8 | L2 + L4 | T1/T4 |
| AC-5 | 设备替代受等价条件约束、结果隔离 | DV-01..03、RN-01 | §2.5、§2.6 | L2 + L4 | T3/T5/T6 |
| AC-6 | 范围变化派生同任务新修订、旧证据不并入 | TK-03、TK-05 | §2.3、§2.5 | L2 + L5 | T1/T3 |
| AC-7 | 默认摘要、原始受限、到期不删 | RP-02、EV-01/02、ST-04 | §2.7、§2.8、§2.11 | L2 + L5 | T3/T4 |
| AC-8 | 知识候选需审阅、第二任务可复用 | KN-01..03、TK-09 | §2.9 | L5 | T3/T4 |
| AC-9 | 自动 PASS 仅来自自动回放与客观证据 | TK-07、EV-03、RP-02 | §2.8 | L2 + L4 | T1/T4/T6 |
| AC-10 | 展示与后端状态一致 | MC-01、TK-02、RN-02、AU-01 | §2.1、§2.3、§2.5、§2.10 | L5 | T2/T4 |
| AC-11 | 断线续跑、保持占用、不重派/重播/重采 | MC-01、RN-01、TK-08、DV-01/02 | §2.1、§2.5、§2.6 | L2 + L3 | T3/T4/T5 |
| AC-12 | STOP-first 重连、补传/去重/对账、旧 epoch | AU-03、RN-02、DV-01 | §2.5、§2.6、§2.10 | L2 + L3 | T3/T4/T5 |
| AC-13 | 释放独立于归档与判定、四事分离 | DV-02、RN-02、TK-07、EV-02 | §2.5–§2.8 | L2 + L4 | T1/T3/T6 |
| AC-14 | 恢复顺序、未演练不声称 RPO/RTO | AU-03 | §2.10 | L2 + L4 | T3/T6 |

---

## 5. L0–L5 与 T1–T6 追溯

### 5.1 证据层级 L0–L5（证明什么 ≠ 测试怎么做）

| 层 | 含义 | 本规格的屏幕落点/可见证据 | 不得声称 |
|---|---|---|---|
| L0 | 文档与契约一致 | 本规格、§1 路由矩阵、§3 门禁落点、§4 AC 表 | 系统可运行 |
| L1 | 静态验证 | TK-05 `mode=static`、RT-02 检查项与失败分类 | 设备可用 |
| L2 | 模拟链路 | MC-01、TK-05、RN-01、AU-03 的可构造 fixture | 真实音频/设备可用 |
| L3 | 真机烟测 | RN-02、DV-02、TK-08；烟测证据标识 | 正式判定有效、进入正式分母 |
| L4 | 正式采样 | TK-05、TK-07、RP-02、EV-02 的正式证据与分母 | 其他设备成立 |
| L5 | 端到端场景 | MC-01、IN、TK、KN、RP 的业务闭环与第二任务复用 | 长期稳定、已通过验收 |

> 禁止用 L0–L2 证据声称 L3–L5 完成；禁止用 L3 样本拼 L4 分母；屏幕展示不自动产生对应层级证据。

### 5.2 测试层 T1–T6（证据如何产生）

| 层 | 含义 | 对应规格 |
|---|---|---|
| T1 | 单元：判定规则、分母、状态机 | §2.4、§2.5、§2.8 |
| T2 | 契约：TaskCard、manifest、审计 schema | §2.1、§2.3、§2.7、§2.10 |
| T3 | 集成：控制面模块协作 | §2.5、§2.6、§2.10 |
| T4 | 端到端（模拟）：全链路假节点 | §2.1、§2.5、§2.8 |
| T5 | 真机烟测：节点 + 设备链路 | §2.5、§2.6 |
| T6 | 正式验收：语音任务正式证据与判定 | §2.7、§2.8、§2.9 |

> L 层描述“证据能证明什么”，T 层描述“测试如何产生证据”；T5 ≠ T6，T5 样本不得计入 T6 分母。屏幕通过不等于测试层通过。

---

## 6. 本文决策、未决与出口标准

### 6.1 本文固定（可在 P1-02/P1-04 评审冻结）

| ID | 决策 | 依据 |
|---|---|---|
| D-SCR-01 | 采用 IA v0.3 的 12 区域 / 39 路由；11 个屏幕族逐屏细化，RT/AG 以 §2.12 登记并延后细节 | §1、§2.12 |
| D-SCR-02 | 任务详情固定 8 子视图（TK-02..TK-09）；旧 11 页签不再作为目标 | §2.3、IA §4 |
| D-SCR-03 | 响应式四档：≥1200 / 1024–1199 / 768–1023 / <768 | §0.9、IA §3、设计系统 §7 |
| D-SCR-04 | G0–G7 按 §3 分布到 IN/TK/DV/RN/EV/RP/KN，不由单一屏幕拥有 | §3 |
| D-SCR-05 | 节点事实固定 `node_observed_*` + `used_for_decision=false`，与 Linux 判定分栏；五轴逐项 | §0.1–§0.2 |
| D-SCR-06 | 释放、证据完整性、最终判定三平面分离；缺清理回执 ≠ 证据不完整 | §0.5、§2.6、§2.8 |
| D-SCR-07 | 逐族差异状态采用 IA 附录 A；通用四态适用于所有屏 | §0.8、IA 附录 A |
| D-SCR-08 | 权限按 §1 默认级别 + 能力；无权限保留只读摘要 + disabled 原因 | §0.7、§1 |

### 6.2 未决（不在本文自行补全）

1. 视觉令牌、深浅色、组件像素规范：P1-03 / IA Q-01、Q-04、Q-11；本文只约束结构与状态语义。
2. 状态 fixture 的构造数据与 `source`/`schema_version`/`server_authoritative` 标注：P1-05；静态截图不算 fixture。
3. 审批超时、陈旧阈值、心跳周期、spool 阈值、报告签名：P0-08 / P0-06；本文不写死数值。
4. RT/AG 默认访问级别 Q-09；`blocker.owner` 显示粒度 Q-10；`/aitest/*` 兼容期 Q-03；报告打印/PDF Q-07。完整 Q-01..Q-12 见 IA §10.2。
5. P1-05 原型与 P1-07 视觉 QA 尚未执行；本文件不构成截图证据、视觉验收或 UI 冻结。

### 6.3 Phase 1 屏幕规格出口标准

- [ ] §1 的 39 条路由逐条确认，无未登记入口；P1-04 manifest 与本表一致。
- [ ] §2 的 11 个屏幕族 + §2.12 均具备目的/动作/数据/状态/响应式/证据与权限边界六项。
- [ ] §2.4 与 §3 对 G0–G7 落点、状态枚举、禁止声明无冲突。
- [ ] §4 的 AC-1..AC-14 均有屏幕落点、L 层、T 层；§5 的 L/T 口径与交付验收、测试策略一致。
- [ ] §6.2 未决项均有 owner 或下一道门；截止点由 Phase 1 评审排期，不得由实现方自行补全。
- [ ] 与 `docs/contracts/` 无字段/枚举冲突；冲突项登记而非在 UI 内猜测。
- [ ] 明确声明：本文不是 UI 冻结、不是实现授权、未做视觉 QA。

> 本文件为 Phase 1 屏幕规格候选，**不构成视觉冻结、UI 实施批准或图像/浏览器 QA 结论**；未运行真实界面、axe、屏幕阅读器或性能测试。
