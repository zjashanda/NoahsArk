# NoahsArk 任务卡、报告、知识与审计契约（v1.1）

> 状态：`frozen-candidate v1.1`，等待 Orchestrator/所有者评审。**不是已批准契约**，不构成 UI、服务端、测试、部署或发布授权。**not production-frozen; Phase 0 not closed**。
> 契约版本：`1.0`（全部 schema 的 `schema_version` 常量为 `"1.0"`）。
> 形成日期：2026-10-28。
> 适用产品版本：NoahsArk V0.0.1。
> 对应交付任务：`P0-07 冻结任务卡、报告、知识与审计契约`。

## 0. 文档地位与权威层级

本契约把已评审的需求、架构与模块业务规则收敛为 UI 和服务端共同消费的字段级候选契约。它只描述字段、状态、生命周期、访问规则和展示边界，不描述应用代码、数据库 DDL、API 路由、UI 组件或测试实现。

冲突时的事实源优先级从高到低：

1. `.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md`（已批准需求基线）。
2. `.omo/plans/noahsark-platform-delivery.md` 与根 `plan.md` 中已确认的架构/模块/字段级评审记录。
3. `.omo/drafts/01-design/`、`.omo/drafts/02-delivery/` 中已同步批准边界的正文。
4. 本目录（`docs/contracts/`）的字段化表达；与 1–3 冲突时以 1–3 为准。
5. `docs/v2/`、`openspec/`、`solutions/`：同步前只作历史参考，不得把其中的 SQLite、租约到期即停止、证据全量上传后才释放等旧表述带入本契约。

### 0.1 权威状态与投影的区分

| 类别 | 对象 | 写入方（唯一权威） | 是否可直接驱动 UI 写操作 | 说明 |
|---|---|---|---|---|
| 权威状态 | Task、TaskRevision、Approval、Gate | Linux 控制面 | 否 | 任务、修订、批准和门禁的唯一事实。 |
| 权威状态 | Run、Attempt、Case、CaseResult、Verdict | Linux 控制面 | 否 | 五轴判定由 Linux 独占写入；节点只回传事实。 |
| 权威状态 | Lease、Device、Node | Linux 控制面 | 否 | 节点可回传节点/设备事实，但不能改占用或最终判定。 |
| 权威状态 | EvidenceSet、EvidenceItem | Linux 控制面校验后入库 | 否 | 证据身份由内容摘要决定，locator 可变、身份不可变。 |
| 权威状态 | KnowledgeCandidate、KnowledgeItem | Linux 控制面知识服务 | 否 | 候选可自动生成，条目只能人工批准后生成。 |
| 权威状态 | AuditEvent | Linux 控制面审计服务 | 否 | 仅追加、不可更新、不可删除。 |
| 投影 | **TaskCard** | 从权威事件派生，可重建 | 否 | 独立于 lead 会话的持久进度面；不得成为第二事实源。 |
| 投影 | Report 的默认披露视图 | 从冻结报告裁剪 | 否 | 默认只暴露摘要和证据索引元数据。 |
| 投影 | UI 知识卡片/审计列表 | 从权威对象裁剪 | 否 | 字段裁剪必须在服务端完成。 |

**Lead 会话规则（已批准）**：lead 会话可恢复，但只是交互上下文，不是执行授权，也不是任务状态。恢复会话不得创建新任务、不得重复执行、不得合并运行或证据、不得批准修订。任务卡是独立投影，会话关闭或刷新不影响其真实性。

## 1. 通用约束

1. **标识**：`task_id`、`revision_id`、`run_id`、`node_id`、`device_id`、`evidence_id`、`candidate_id`、`knowledge_id`、`report_id`、`event_id` 均使用 `^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$`，不得复用或回收。
2. **时间**：所有时间为 RFC 3339 `date-time`，统一 UTC；`occurred_at`（实际发生）与 `recorded_at`（记录时间）必须分开。
3. **版本**：`schema_version` 是载荷的一部分。缺失或未知版本按 fail-closed 处理，不得猜测字段语义。
4. **未知值**：未知计数必须为 `null` 并显示“未知”，不得用 `0`、空白或估算值冒充。
5. **禁止内容**：任何默认载荷不得包含原始音频、原始日志正文、密钥/令牌/凭据、PII、绝对存储路径。需要原始材料时必须走受控访问和审计。
6. **人工补充**：人工记录可以存在，但不得产生自动 PASS，不得计入自动化结果，不得伪装成自动化检查。
7. **不可变**：冻结修订、冻结报告、已接收证据、审计事件和已推广知识版本不得原地覆盖；更正通过新版本、补偿事件或撤回状态表达。
8. **服务端裁剪**：UI 可见字段由服务端按访问策略裁剪后再下发；客户端隐藏不构成访问控制。

## 2. 任务卡投影契约

### 2.1 定位

任务卡是**派生只读投影**，不是权威状态，不是执行授权，也不是 lead 会话视图。它必须：

- 在没有人打开 lead 会话时仍显示真实进展。
- 关闭会话、刷新页面、重新登录后保持同一 `task_id` 的状态。
- 可从权威事件和已校验回执重建，重建不产生新的运行或证据。
- 只展示服务端给出的字段和状态，不在客户端推导 PASS/FAIL、完成百分比或设备空闲。

### 2.2 必填字段

对应 `schemas/experience/task-card.schema.json`。

| 字段 | 含义 | 权威来源 | 展示要求 |
|---|---|---|---|
| `task_id` | 长期任务身份 | Task | 可复制、可深链；不得被会话 ID 替代。 |
| `revision_id` | 当前不可变修订 | TaskRevision | 必须显示当前修订；切换修订需明确说明。 |
| `run_id` | 当前运行尝试，未运行为 `null` | Run | `null` 只表示尚未运行，不表示完成。 |
| `stage` | 主生命周期阶段与序号 | Gate/编排事件 | 显示阶段文字 + 阶段序号；不得把阶段序号当完成百分比。 |
| `run_state.state` | 执行状态 | Run/编排事件 | 与通信状态分开显示。 |
| `status_display` | 单一主状态标签与颜色/文本 | 服务端投影 | 颜色不得作为唯一状态载体，必须同时有文字与 `aria_text`。 |
| `gates` | G0–G7 门禁结果与当前门禁 | Gate | 七枚离散印章，各自 PASS/FAIL/PENDING/BLOCKED/NOT_APPLICABLE/UNKNOWN。 |
| `resources.node` | 实际节点 | Node/Lease | `actual=true` 时必须有 `node_id`；不得显示计划候选冒充实际节点。 |
| `resources.device` | 实际设备 | Device/Lease | `actual=true` 时必须有 `device_id`；显示设备身份与池状态。 |
| `resources.occupancy_state` | 设备占用 | Lease/Device | 不得由通信状态推断；离线时仍可能 `OCCUPIED`。 |
| `blocker.owner` | 阻塞责任方 | 编排/审批/门禁事件 | 必须回答“卡在谁那里”；阻塞时 owner 不得为 `NONE`。 |
| `progress` | 计数、未知项、可选百分比 | 运行/证据/用例事件 | 总量未知时 `percent` 必须为 `null`。 |
| `freshness` | 投影是否陈旧及原因 | 投影服务 | `is_stale=true` 时必须有至少一个 `stale_reasons`。 |
| `communication` | 节点↔控制面通信状态 | 心跳/事件流 | 与执行、占用、新鲜度分开显示。 |
| `last_authoritative_update` | 最后一次权威状态变更 | 权威事件 | 显示时间、来源；与 `last_known_at` 分开。 |
| `last_known_at` | 最后收到任何可信事实的时间 | 投影服务 | 可晚于权威更新时间；不得冒充权威更新时间。 |
| `access_level` | 投影最大展示级别 | 访问策略 | UI 不得提升，只能降级或隐藏。 |

### 2.3 阶段与状态展示

**主生命周期**（用于任务卡阶段和门禁投影）：

```text
DRAFT → REVIEW → FROZEN → APPROVED → STATIC → LEASED → SMOKE → FORMAL
→ VERIFYING → REPORTED → CLOSED
```

异常态：`BLOCKED`、`STOPPED`、`INVALID`、`QUARANTINED`、`INFRA_ERROR`、`AWAITING_CORRECTION`。异常态沿用其发生时所处的正常阶段序号，不额外增加伪造进度。

**结果五轴**（独立于主生命周期，不得折叠进 `stage`）：

```text
execution_status / validity_status / business_verdict / evidence_status / verification_status
```

| 轴 | 允许值 |
|---|---|
| `execution_status` | `NOT_STARTED` / `RUNNING` / `COMPLETED` / `ABORTED` / `SKIPPED` / `UNKNOWN` |
| `validity_status` | `VALID` / `INVALID` / `BLOCKED` / `UNKNOWN` |
| `business_verdict` | `PASS` / `FAIL` / `EXPECTED` / `WARN` / `NEEDS_REVIEW` / `NOT_EVALUATED` |
| `evidence_status` | `COMPLETE` / `INCOMPLETE` / `CONFLICTED` / `UNVERIFIED` / `UNKNOWN` |
| `verification_status` | `PASS` / `FAIL` / `NOT_RUN` / `UNKNOWN` |

**`UNKNOWN` 的权威边界（R-03，2026-10-29 裁决）**：`execution_status`、`evidence_status`、`verification_status` 的 `UNKNOWN` 是**展示占位**，不得写回 `Run`/`Attempt`/`verdict.axes`。权威枚举没有这些值；展示未知时应分别写 `NOT_STARTED` / `INCOMPLETE` / `NOT_RUN`（缺失语义），或显示“投影未读取/不可用”。`validity_status` 的 `UNKNOWN` 是权威枚举成员，可写回。该规则与 `evidence-verdict.md` §14.1 一致。

**显示优先级**：`status_display.primary_state` 是呈现选择，不得删除其他信号。

1. 先展示主阶段 `stage` 和 `run_state`。
2. `blocker.is_blocked=true` 时，主状态显示 `BLOCKED`，并显示 `blocker.owner` 与 `awaiting_action`。
3. `run_state` 为 `STOPPED`/`COMPLETED`/`FAILED` 时显示对应终态。
4. `communication.state=OFFLINE` 时**追加**离线徽章，不得把运行中任务显示为“已停止”或“设备空闲”。
5. `freshness.is_stale=true` 时**追加**陈旧徽章，不得用旧数据伪装实时。
6. `business_verdict=NEEDS_REVIEW` 或复核未通过时显示 `NEEDS_REVIEW`。
7. 其余运行中状态显示 `RUNNING`。

`status_display` 不能替代五轴；任务详情和报告必须完整展示五轴。

### 2.4 进度规则

`progress.mode` 只有三种合法模式：

| 模式 | 使用条件 | 展示 | `percent` |
|---|---|---|---|
| `COUNTS` | 分母权威可知且已批准 | `已完成 / 总数`，并显示度量名称 | 可为数字 |
| `QUALITATIVE` | 有部分可信计数，但总量未知 | 显示已知计数 + “未知”标记 | 必须为 `null` |
| `INDETERMINATE` | 没有可靠计数 | 只显示阶段、门禁和状态 | 必须为 `null` |

**唯一允许的百分比公式**：

```text
percent = round(clamp(completed / total × 100, 0, 100), 1)
```

前提全部满足：

1. `mode = COUNTS`。
2. `denominator_kind` 为 `APPROVED_CASE_COUNT` 或 `APPROVED_EVIDENCE_ITEM_COUNT`。
3. `total` 是对应权威对象的已批准数量，且 `total > 0`。
4. `completed` 只统计已完成且状态明确的项，不把烟测、无效、阻断或停止项混入正式分母。
5. `percent_label` 必须说明语义，例如“已完成用例占比”，不得写成“任务完成度”。

**禁止**：

- 用耗时、消息数、文件字节数、token 消耗、日志行数推算百分比。
- 未知总量时显示 0%、99%、“即将完成”等暗示。
- 把阶段序号（如 7/11）冒充分母百分比。
- 把烟测样本计入正式进度。
- 把 `evidence_items_received` 当作 `evidence_items_verified`。

**证据进度**必须同时展示 `evidence_items_expected`、`evidence_items_received`、`evidence_items_verified`。任一未知为 `null`，UI 显示“未知”。未通过 Linux 校验的证据只能算“已接收”，不得算“已核验”。

### 2.5 Stale 与断连语义

四个信号相互独立，禁止合并：

| 信号 | 字段 | 含义 | 不得推断 |
|---|---|---|---|
| 通信 | `communication.state` | 节点与 Linux 是否可见 | 不得推断执行已停止或设备空闲。 |
| 执行 | `run_state.state` | 运行是否仍在进行 | 不得因心跳丢失自动改为 STOPPED。 |
| 占用 | `resources.occupancy_state` | 设备是否被当前任务占用 | 不得因通信离线而释放或重派。 |
| 新鲜度 | `freshness` | 任务卡数据是否过期 | 不得用旧数据冒充实时。 |

**状态组合规则**：

| 通信 | 执行 | 必须展示 | 不得展示 |
|---|---|---|---|
| `LIVE` | `RUNNING` | 运行中 + 实时 | 完成百分比（除非 `progress.mode=COUNTS`） |
| `DEGRADED` | `RUNNING` | 降级轮询/事件延迟 + 运行中 | “正常实时” |
| `OFFLINE` | `RUNNING` | 通信离线 + 执行可能继续 + 设备保持占用 + 最后已知时间 | “已停止”“设备空闲”“可重派” |
| `OFFLINE` | `STOPPED`/`COMPLETED` | 离线 + 最后一次权威终态 + 离线开始时间 | 把离线当作终态原因而不说明 |
| `UNKNOWN` | 任意 | 未知 + 最后权威更新 + 陈旧标记 | 把未知渲染为正常 |
| 任意 | `RUNNING`，但 `freshness.is_stale=true` | 旧数据 + 陈旧原因 | 用旧进度暗示实时 |

**离线续跑（已批准）**：已启动的冻结压测不因通信中断、心跳不可达或通信租约无法续期而自动停止；节点继续执行并在本地持久化进度、异常、日志和证据。Linux 标记通信离线但设备保持占用，不新派、不重播、不重复采样。重连后先处理待 STOP，再补传、去重和对账。`communication.offline_continuation_expected` 与 `device_occupancy_held` 必须为 `true`。

**陈旧阈值**：`freshness.stale_after_seconds` 由服务端从 P0-08 配置解析后写入投影；UI 不得硬编码阈值。缺失阈值时服务端必须按 fail-closed 标记 `is_stale=true` 或拒绝下发，不得默认“新鲜”。

**时间语义**：

- `last_authoritative_update.at`：最后一次权威状态变更（批准、门禁、租约、判定、已校验回执）。
- `last_known_at`：投影最后收到任何可信事实的时间，可包含尚未成为权威状态的节点事实。
- UI 必须分别显示“最后权威更新”和“最后已知活动”；不得把两者合并成一个模糊的“更新时间”。

### 2.6 刷新与重建

1. 每个权威事件写入后，投影服务更新任务卡；投影更新必须幂等。
2. 传输优先 SSE/事件流，断线后降级轮询；降级必须可见，不得静默。
3. 客户端不得乐观写入状态；所有状态变更以服务端返回为准。
4. 任务卡可由权威事件和已校验回执重建；重建不得改变 `task_id`、`revision_id`、`run_id` 或历史证据归属。
5. 投影构建失败时必须显示“投影不可用/陈旧”，不得回退到旧卡片冒充当前状态。

### 2.7 投影词汇与权威字段映射

任务卡的展示枚举是**派生词汇**，不是新的权威状态。投影服务必须按下列映射从权威字段生成；UI 不得自行推断。任何无法映射的值一律 fail-closed 为 `UNKNOWN`，不得回退到旧卡片或猜测为正常状态。

**设备占用（`resources.occupancy_state`）**

| 任务卡值 | 权威来源 | 规则 |
|---|---|---|
| `OCCUPIED` | Lease.`occupancy_state=OCCUPIED`（含 `RELEASING`） | `RELEASING` 仍视为占用，直到 `occupancy_reconciled=true`；通信 `OFFLINE`/`STALE` 不改变该值。 |
| `RESERVED` | Device.`pool_state=RESERVED`，或 Lease.`state` ∈ {`GRANTED`,`HELD`,`RECLAIM_PENDING`} 且尚未 `OCCUPIED` | 仅表示已保留，不得显示为可重派。 |
| `FREE` | Lease.`occupancy_state=IDLE` 且 Device.`pool_state=READY` 且 Lease.`state=RELEASED` | 必须由权威释放事实确认。**通信 `OFFLINE`/`STALE`/`DEGRADED` 一律不得映射为 `FREE` 或 `IDLE`。** |
| `UNKNOWN` | 缺失/不可判定 | 显示未知，保持占用语义。 |

**通信（`communication.state` 与 `resources.node.online_state`）**

| 任务卡值 | 权威来源 | 禁止推断 |
|---|---|---|
| `LIVE` / `ONLINE` | Node.`communication_state=ONLINE` | 不代表执行正常或设备空闲。 |
| `DEGRADED` | `STALE`（心跳/事件延迟） | 不得推断执行已停止。 |
| `OFFLINE` | `OFFLINE` | **不得推断 `STOPPED`、`FREE`、`IDLE` 或可重派。** |
| `UNKNOWN` | 缺失/不可判定 | 不得渲染为正常。 |

设备/节点离线的完整组合规则见 §2.5；本表不得覆盖 §2.5 的“追加徽章、不改写执行/占用”要求。

**门禁（`gates[].status`）**

| 任务卡值 | 权威 Gate.status |
|---|---|
| `PASS` | `PASSED` |
| `FAIL` | `FAILED` |
| `PENDING` | `PENDING` 或 `IN_PROGRESS`（显示进行中标签，不得提前显示 PASS） |
| `BLOCKED` | `BLOCKED` |
| `NOT_APPLICABLE` | `SKIPPED`（仅当权威明确标记不适用/跳过；不得用 `UNKNOWN` 冒充） |
| `UNKNOWN` | 缺失/不可判定 |

**运行（`run_state.state`）**

| 任务卡值 | 权威来源 |
|---|---|
| `NOT_STARTED` | Run.`lifecycle_status` ∈ {`CREATED`,`DISPATCHED`}（`DISPATCHED` 需显示“已派发/未开始”） |
| `RUNNING` | `RUNNING`，或无待处理 STOP 的 `FINISHING` |
| `STOPPING` | `RUNNING`/`FINISHING` 且存在未完成 STOP 请求或安全停止流程；仅为展示态 |
| `BLOCKED` | `BLOCKED` |
| `STOPPED` | `STOPPED` |
| `COMPLETED` | `COMPLETED` |
| `FAILED` | `ABORTED` 或执行轴 `execution_status=ABORTED`；业务 FAIL 只能来自五轴 `business_verdict`，不得折叠进 `run_state` |
| `UNKNOWN` | 缺失/不可判定 |

- `status_display.primary_state` 只是呈现选择，不得删除或改写上述信号；`run_state`、`occupancy_state`、`communication.state` 与 `business_verdict` 必须分开展示。
- 本表是 `experience/task-card.schema.json` 展示枚举的唯一映射口径；若新增投影枚举，必须先在此登记权威来源与禁止推断。

**证据轴（`evidence_status`，R-03 第五张表，2026-10-29 补齐）**

| 任务卡/报告展示值 | 权威来源 `evidence_status` | 规则 |
|---|---|---|
| `COMPLETE` | `COMPLETE` | 直接透传，不重新计算。 |
| `INCOMPLETE` | `INCOMPLETE` | 直接透传。 |
| `CONFLICTED` | `CONFLICTED` | 直接透传，不得改写成 `INCOMPLETE`。 |
| `UNVERIFIED` | `UNVERIFIED` | 直接透传，不得改写成 `INCOMPLETE`。 |
| `UNKNOWN` | **无对应权威值** | 仅表示“投影尚未读取/不可用”；必须同时携带 `freshness` 与最后权威更新时间，且**不得写回** `verdict.axes.evidence_status`。 |

**报告覆盖范围（`report_scope.mode`，R-03，2026-10-29）**

`report_scope.mode` 表示**报告覆盖范围**，不是运行模式；`Run.mode` 仍只有 `static`/`smoke`/`formal`。

| 展示值 | 含义 | 说明 |
|---|---|---|
| `SMOKE` | 报告仅覆盖烟测运行 | 不进入正式分母。 |
| `FORMAL` | 报告仅覆盖正式运行 | 不合并烟测分母。 |
| `MIXED` | 报告同时覆盖烟测与正式运行 | 分母仍分开计算。 |
| `BLOCKED` | 覆盖集包含阻断运行（过渡词） | 不是 mode；新生产者应改用 `contains_blocked`。 |
| `STOPPED` | 覆盖集包含停止运行（过渡词） | 不是 mode；新生产者应改用 `contains_stopped`。 |
| `UNKNOWN` | 覆盖范围无法判定 | 显示未知。 |

`experience/report.schema.json` 新增可选 `report_scope.contains_blocked` / `contains_stopped`（`1.x` 兼容）。`BLOCKED`/`STOPPED` 枚举值保留用于历史兼容，但任何界面都不得把它们渲染成运行模式。删除这两个值或重命名 `mode` 属结构性变更，须等 P1-08 UI 词汇冻结后按 `2.0` 评估；本版本不主张。

## 3. 报告契约

对应 `schemas/experience/report.schema.json`。

### 3.1 报告定位

报告是**绑定单一不可变修订**的交付物，可覆盖多个独立运行（`run_ids`），但不得把不同修订或不同设备的结果静默合并。报告冻结后不可原地修改；更正通过新版本、`SUPERSEDED` 状态或勘误事件表达。

### 3.2 必需章节

报告必须包含以下章节；即使某类记录不适用，也必须出现该分类并标记 `EMPTY` 或 `NOT_APPLICABLE`，避免读者误以为漏项。

| 顺序 | `category` | 内容 | `record_kind` | 默认可见性 |
|---|---|---|---|---|
| 1 | `summary` | 测试摘要、范围、结论摘要 | `MIXED` | `SUMMARY` |
| 2 | `automated_checks` | 静态检查、preflight、契约检查 | `AUTOMATED_CHECK` | `SUMMARY`（明细 `RESTRICTED`） |
| 3 | `smoke` | 有界真机烟测 | `SMOKE` | `SUMMARY`（明细 `RESTRICTED`） |
| 4 | `formal_records` | 正式采样与逐用例结果 | `FORMAL` | `SUMMARY`（明细 `RESTRICTED`） |
| 5 | `human_supplements` | 人工喊测、主观体验、补充说明 | `HUMAN_SUPPLEMENT` | `SUMMARY`，必须标注“非自动判定” |
| 6 | `deviations` | 与计划不符之处 | `MIXED` | `SUMMARY` |
| 7 | `completion_assessment` | 完成评估 | `MIXED` | `SUMMARY` |
| 8 | `blockers` | 阻塞因素与未解决项 | `MIXED` | `SUMMARY` |
| 9 | `metrics` | 分母、通过率、有效性统计 | `MIXED` | `SUMMARY` |
| 10 | `residual_risks` | 残余风险 | `MIXED` | `SUMMARY` |
| 11 | `deliverables_reusable_assets` | 交付物与可复用资产 | `MIXED` | `SUMMARY` |
| 12 | `lessons_learned` | 经验教训 | `MIXED` | `SUMMARY` |
| 13 | `evidence_index` | 证据索引（身份、摘要、大小、访问级别） | `MIXED` | `INDEX` |
| 14 | `unresolved_items` | 未解决事项 | `MIXED` | `SUMMARY` |

### 3.3 四类记录必须分离

| 记录类型 | 是否可产生自动 PASS | 是否进入正式分母 | 默认展示 |
|---|---|---|---|
| 自动化检查 | 否（只是门禁输入） | 否 | 摘要 + 检查项计数 |
| 烟测 | 否 | **永不进入** | 摘要 + “烟测独立运行”标识 |
| 正式记录 | 是，但必须同时满足五轴与证据完整 | 是（仅有效样本） | 摘要 + 分母 + 逐设备/逐用例结果 |
| 人工补充 | **否** | 否 | 摘要，明确标注“人工补充，非自动判定” |

硬约束（schema 常量）：

- `record_separation.smoke_in_formal_denominator = false`
- `record_separation.human_supplement_counts_as_automated = false`
- `verdict_summary.automated_pass_source = AUTOMATED_REPLAY_OBJECTIVE_EVIDENCE`
- `verdict_summary.human_supplement_can_produce_pass = false`
- `verdict_summary.fail_closed = true`

### 3.4 分母口径

报告首页必须声明分母口径：

```text
分母 = 有效正式样本
排除：烟测、INVALID_*、BLOCKED、STOPPED、基础设施失败、证据不完整样本
重试通过：单独标记 FLAKY_SUSPECT，不覆盖首次结果
```

`denominator` 必须提供总量与 `per_device`、`per_case` 分解；未知计数为 `null`。不得用“执行数”替代“有效数”，不得把烟测拼进正式分母。

### 3.5 默认披露与受限内容

| 内容 | 默认报告 | 需要额外访问 |
|---|---|---|
| 摘要、结论摘要、分母、残余风险 | 是 | 否 |
| 证据索引（`evidence_id`、kind、digest、size、collected_at、access_level、display_path_hint） | 是 | 否 |
| 原始音频 | **否** | 是，`EVIDENCE_AUTHORIZED` |
| 原始日志正文 | **否** | 是，`EVIDENCE_AUTHORIZED` |
| 绝对存储路径 | **否** | 否，任何级别都不得进入默认载荷 |
| 密钥、令牌、凭据 | **否** | 否，永不进入报告 |
| PII | **否** | 否，永不进入默认报告；确需展示时须脱敏并单独授权 |
| 受限章节明细 | 否 | 是，按章节声明 |

`disclosure` 中 `raw_audio_included`、`raw_logs_included`、`secrets_included`、`pii_included` 在 V0.0.1 报告中必须为 `false`。

### 3.6 人工补充规则

1. 人工补充只能进入 `human_supplements` 或明确标记为人工的条目。
2. 人工补充不得写入 `automated_checks`、`formal_records` 的自动结果字段。
3. 人工补充不得产生自动 PASS；报告必须同时显示“自动判定”和“人工补充”来源。
4. 人工补充的结论可以建议复核，但不得覆盖 Linux 的五轴判定。

### 3.7 报告中的判定汇总

`verdict_summary` 必须同时展示五轴和 `overall_business_verdict`。`overall_business_verdict` 只是业务轴汇总，不得替代其余四轴。任何缺证据、缺批准、缺指标、缺追溯或复核未通过时，`fail_closed` 生效，不得给 PASS。

## 4. 知识候选与知识条目

对应 `schemas/experience/knowledge-candidate.schema.json` 与 `schemas/experience/knowledge-item.schema.json`。

### 4.1 候选生成时机

每次任务结束都必须从本次任务提取并持久保存经验，覆盖正常完成、人工停止、阻断、安全停止和失败；不得只在重大异常时提取。

- 正常完成、人工停止、阻断或安全停止后立即整理候选。
- 离线压测不因失联提前视为结束；重连补传并对账完成后再整理。
- 每次实际操作先保留可追溯事实，再形成候选。
- 候选必须回到原 `task_id`、`revision_id`、`run_id`、设备身份、项目、硬件、动作、观察结果和证据。
- 一条经验可以同时按项目、硬件型号/具体设备、固件/配置版本、测试能力、操作步骤、正常/异常/误报、处置和复测结果分类。

### 4.2 候选必填字段

| 字段 | 含义 | 约束 |
|---|---|---|
| `candidate_id` | 候选身份 | 不复用。 |
| `status` | 生命周期状态 | 见 4.3。 |
| `created_by` | 生成者类型/身份/角色 | Agent 可生成，但不能自动推广。 |
| `source` | 任务/修订/运行/模式/终态/项目/节点/设备/固件/配置/执行包/时间 | 不得出现无来源候选。 |
| `classification` | 正常/异常/误报/处置/复测/流程等 | 不得只收录成功案例。 |
| `content` | 标题、观察、预期、实际、建议、局限 | 建议不是已批准规则。 |
| `applicability` | 项目、硬件、设备、固件、配置、lstest 版本、能力、条件、排除项 | 未复核或条件不符只能作线索。 |
| `evidence_refs` | 证据身份、类型、摘要、访问级别、关系 | 只引用，不内嵌原始内容。 |
| `review` | 审阅状态、审阅人、角色、时间、决定、理由、条件 | 未审阅不得推广。 |
| `promotion` | 自动推广硬约束、目标、所需权限、决定、条目 ID、事件 | `automatic_allowed=false`、`requires_human_review=true`。 |
| `dedupe` | 去重键、重复对象、相关候选、相似性检查 | 相似不得自动合并。 |
| `status_history` | 状态变更历史 | 仅追加。 |
| `access_level` | 候选最大展示级别 | 默认 `SUMMARY_INDEX`，证据受限时提升。 |

### 4.3 候选生命周期

```text
PROPOSED → UNDER_REVIEW → NEEDS_INFO → UNDER_REVIEW
UNDER_REVIEW → APPROVED → PROMOTED
UNDER_REVIEW → REJECTED
UNDER_REVIEW → DUPLICATE
任意非终态 → WITHDRAWN
APPROVED/PROMOTED/REJECTED → SUPERSEDED（出现更新候选时）
```

| 迁移 | 执行者 | 权限 | 审计动作 |
|---|---|---|---|
| 创建 `PROPOSED` | Agent/System | 自动提取 | `KNOWLEDGE_CANDIDATE_CREATE` |
| `PROPOSED → UNDER_REVIEW` | 人类审阅者 | `REVIEW_KNOWLEDGE_CANDIDATE` | `KNOWLEDGE_CANDIDATE_REVIEW` |
| `UNDER_REVIEW → NEEDS_INFO` | 人类审阅者 | 同上 | `KNOWLEDGE_CANDIDATE_REVIEW` |
| `NEEDS_INFO → UNDER_REVIEW` | 候选提交者/人类审阅者 | 同上或提交权限 | `KNOWLEDGE_CANDIDATE_REVIEW` |
| `UNDER_REVIEW → APPROVED` | 人类审阅者 | 目标库对应权限 + 审阅权限 | `KNOWLEDGE_CANDIDATE_REVIEW` |
| `APPROVED → PROMOTED` | 人类审阅者 | 目标库对应权限 | `KNOWLEDGE_PROMOTE` |
| `UNDER_REVIEW → REJECTED` | 人类审阅者 | 审阅权限 | `KNOWLEDGE_CANDIDATE_REVIEW` |
| `UNDER_REVIEW → DUPLICATE` | 人类审阅者 | 审阅权限 | `KNOWLEDGE_CANDIDATE_REVIEW` |
| 任意非终态 → `WITHDRAWN` | 生成者/管理员 | 自身候选或管理权限 | `KNOWLEDGE_CANDIDATE_REVIEW` |

**硬不变量**：`PROPOSED`、`UNDER_REVIEW`、`NEEDS_INFO` 状态下 `promoted_knowledge_item_id` 必须为 `null`；`PROMOTED` 状态下 `promotion.decision` 必须为 `APPROVED` 且条目 ID 非空。不存在 `PROPOSED → PROMOTED` 的捷径。

### 4.4 推广规则

推广指把候选合入通用知识库、工具知识库或转化为可复用异常规则。必须全部满足：

1. **人工决定**：只能由有权限的人类审阅者批准；Agent 和 System 不能推广。
2. **权限匹配目标**：
   - 通用知识库：`KNOWLEDGE_MERGE_COMMON`。
   - 工具知识库：`KNOWLEDGE_MERGE_TOOL`。
   - 可复用异常规则：`KNOWLEDGE_PROMOTE_ANOMALY`。
3. **来源完整**：候选必须关联任务、修订、运行、设备、项目、证据和适用条件。
4. **冲突/重复检查**：必须记录相似性检查、冲突对象和处理结论；相似不得自动合并。
5. **审阅独立性**：Agent/System 生成的候选必须由人类审阅；生成者不得是唯一批准者。人类自生成候选的自审必须由 `SUPER_ADMIN` 执行并记录理由。
6. **条目创建**：推广生成新的 `KnowledgeItem` 版本，保留 `source_candidate_ids`、`approval_ids` 和 `promotion_event_id`。
7. **不改变历史**：推广不得修改已冻结修订、执行包、历史判定或旧运行证据；只影响未来任务的检索与引用。
8. **不自动套用**：已批准知识进入新冻结执行包前，仍需检查对当前任务、设备、固件和配置的适用性。
9. **频率不构成批准**：重复次数、出现频次或“多数案例”不得自动改变阈值、脚本、判据或已冻结执行包。
10. **可撤回**：知识条目可被标记 `STALE`、`DISPUTED`、`RETRACTED` 或 `SUPERSEDED`，但不得删除历史版本和来源链。

### 4.5 知识条目状态

| 状态 | 含义 | UI 行为 |
|---|---|---|
| `APPROVED` | 已人工批准，可作为参考 | 正常展示，仍需适用性检查。 |
| `CORROBORATED` | 多来源相互印证 | 正常展示，标注印证来源。 |
| `DISPUTED` | 存在冲突证据或反例 | 显式警告，不得静默排在 `APPROVED` 前。 |
| `STALE` | 版本/环境漂移或复核过期 | 灰虚线 + 原因 + “仍可阅读，不自动套用”。 |
| `RETRACTED` | 已撤回 | 删除线/明显警告，保留历史与来源。 |
| `SUPERSEDED` | 被新版本取代 | 指向新版本，保留旧版本。 |
| `EXPIRED` | 超过有效期 | 标记过期，不得自动套用。 |

条目的 `staleness`、`conflict`、`lifecycle`、`review` 和 `source_provenance` 均为必填；`automatic=false`、`conflict_check=true`、`applicability_check=true` 为硬约束。

### 4.6 知识展示规则

1. 知识卡片必须显示状态徽章、类型、标题、匹配理由、适用性、差异/警告和引用。
2. `stale`/`disputed` 必须在标题行可见，不能只在详情里。
3. `approved` 不得被 `stale`/`disputed` 静默压过；排序规则必须可解释。
4. “应用到计划”只创建草案修订，需审计与再次审批，不得直接修改冻结执行包或判据。
5. 未复核候选必须显示“未复核”，不得与已批准知识使用相同视觉权重。

## 5. 审计契约

对应 `schemas/experience/audit-event.schema.json`。

### 5.1 事件模型

审计事件是不可变、仅追加的事实记录。每次关键动作和每次访问决策（允许或拒绝）都必须产生事件。

必填内容：

| 内容 | 字段 | 说明 |
|---|---|---|
| 操作者 | `actor.actor_id`、`actor_type`、`role`、`auth_method` | 区分人、Agent、System、Node Agent。 |
| 角色 | `actor.role` | 记录动作发生时的角色，不随后续角色变更重写。 |
| 动作 | `action.action_code`、`category` | 来自固定目录。 |
| 对象 | `object.object_type`、`object_id`、`object_version` | 明确被操作对象。 |
| 变更前后 | `change.before`、`change.after`、`changed_fields` | 变更类事件必须提供；已脱敏。 |
| 原因 | `reason.reason_code`、`reason_text` | 必须非空。 |
| 时间 | `occurred_at`、`recorded_at` | 实际发生与记录分开。 |
| 任务关联 | `scope.task_id`、`revision_id`、`run_id` | 键必须存在；非任务事件可为 `null`。 |
| 访问决策 | `access_decision.decision`、`resource_class`、`required_access_level`、`granted_access_level`、`policy_id`、`matched_rule_id`、`denial_reason` | 每次动作都附带。 |
| 完整性 | `integrity.previous_event_hash`、`event_hash`、`hash_algorithm`、`immutable`、`append_only` | 哈希链，防篡改。 |
| 保留 | `retention.class`、`disposition` | 审计与记录同寿命。 |

### 5.2 动作目录

| 类别 | 动作码 | before/after | 备注 |
|---|---|---|---|
| 任务 | `TASK_CREATE`、`TASK_UPDATE`、`TASK_CLOSE` | CREATE 需 after；UPDATE 需 before+after | 任务身份不复用。 |
| 修订 | `REVISION_CREATE`、`REVISION_FREEZE`、`REVISION_SUPERSEDE` | CREATE/FREEZE 需 after；SUPERSEDE 需 before+after | 冻结后不可改。 |
| 审批 | `APPROVAL_REQUEST`、`APPROVAL_DECIDE`、`APPROVAL_TIMEOUT` | DECIDE 需 after；TIMEOUT 需 before+after | 记录意见、范围快照、时间。 |
| 门禁 | `GATE_ENTER`、`GATE_PASS`、`GATE_FAIL`、`GATE_BLOCK` | 状态迁移需 before+after | 逐门禁可追溯。 |
| 运行 | `RUN_START`、`RUN_STOP_REQUEST`、`RUN_STOP`、`RUN_COMPLETE`、`RUN_ABORT`、`RUN_RECONCILE` | 状态迁移需 before+after | 烟测/正式独立。 |
| 租约 | `LEASE_ACQUIRE`、`LEASE_RENEW`、`LEASE_RELEASE`、`LEASE_EXPIRE` | ACQUIRE/RELEASE 需 after；EXPIRE 需 before+after | 通信与占用分离。 |
| 设备 | `DEVICE_STATE_CHANGE`、`DEVICE_QUARANTINE`、`DEVICE_RECOVER` | 需 before+after | 隔离需人工恢复。 |
| 证据 | `EVIDENCE_UPLOAD`、`EVIDENCE_VERIFY`、`EVIDENCE_ACCESS`、`EVIDENCE_ARCHIVE`、`EVIDENCE_DELETE_REQUEST` | UPLOAD/VERIFY/ACCESS 需 after；ARCHIVE 需 before+after | 访问拒绝必须留痕；不得删除原始事件。 |
| 判定 | `VERDICT_WRITE`、`RESULT_OVERRIDE` | 需 before+after | Linux 独占；记录理由与任务/修订。 |
| 报告 | `REPORT_GENERATE`、`REPORT_FREEZE`、`REPORT_EXPORT`、`REPORT_RETRACT` | GENERATE/FREEZE 需 after；RETRACT 需 before+after | 冻结后不可改。 |
| 知识 | `KNOWLEDGE_CANDIDATE_CREATE`、`KNOWLEDGE_CANDIDATE_REVIEW`、`KNOWLEDGE_PROMOTE`、`KNOWLEDGE_REVOKE`、`KNOWLEDGE_STALE_MARK`、`KNOWLEDGE_CONFLICT_RESOLVE` | 需 before+after | 记录候选、目标库、权限和理由。 |
| 访问 | `ACCESS_DECISION` | after 记录决策；拒绝必须有 `denial_reason` | 允许与拒绝都审计。 |
| 身份 | `ROLE_CHANGE` | 需 before+after | 角色变更不重写历史事件。 |
| 会话 | `SESSION_RESTORE`、`SESSION_REVOKE` | 需 after；REVOKE 需 before+after | 恢复不授权执行。 |
| 节点 | `NODE_REGISTER`、`NODE_ROTATE_CREDENTIAL`、`NODE_REVOKE`、`NODE_DRAIN` | 需 before+after | 记录节点身份与原因。 |
| 执行包 | `BUNDLE_GENERATE`、`BUNDLE_FREEZE` | 需 after；FREEZE 需 before+after | 绑定修订与摘要。 |
| 配置 | `SETTINGS_CHANGE`、`DATA_RETENTION_CHANGE`、`SYSTEM_CLOCK_CHANGE` | 需 before+after | 系统时间变更必须审计。 |
| 停止 | `STOP_REQUEST` | 需 after | 区分节点人工停止与 Linux 停止指令。 |
| 审计 | `AUDIT_EXPORT` | 需 after | 导出本身也是敏感动作。 |

**禁止的动作码**：任何 `AUDIT_UPDATE`、`AUDIT_DELETE`、`AUDIT_OVERWRITE`。审计纠正只能通过新的补偿事件表达。

### 5.3 访问决策与拒绝

1. 每个事件必须带 `access_decision`；内部系统事件可为 `ALLOW`，但不得省略。
2. 拒绝必须记录 `decision=DENY`、`resource_class`、`required_access_level`、`granted_access_level`、`policy_id`、`matched_rule_id` 和 `denial_reason`。
3. 原始音频/日志访问无论允许或拒绝都必须审计。
4. 拒绝事件必须对任务授权者可见（至少显示“访问被拒绝”与原因分类），但不得泄露受限内容本身。
5. 审计事件不得包含被拒绝访问的原始内容。

### 5.4 不可变与更正

- `integrity.immutable=true`、`append_only=true` 为硬约束。
- `previous_event_hash` 指向前一事件；首事件可为 `null`。
- 任何更新或删除都会破坏哈希链，必须被检测和告警。
- 更正通过新的补偿事件（新的 `event_id`、引用原事件）表达；不得覆盖原事件。
- 审计记录保留期与记录同寿命；原始音频/日志按 30 天热保留，但审计事件不随原始材料删除而消失。

## 6. 访问级别与字段可见性

对应 `schemas/experience/access-policy.schema.json`。

### 6.1 访问级别

| 级别 | 含义 | 典型资源 | 是否含原始材料 | 默认 |
|---|---|---|---|---|
| `PUBLIC_SUMMARY` | 非敏感摘要，预留 | 未来公开摘要 | 否 | 保留，V0.0.1 不默认使用 |
| `SUMMARY_INDEX` | 摘要 + 证据索引元数据 | 报告默认视图、证据索引 | 否 | **报告默认** |
| `TASK_AUTHORIZED` | 任务关系内的详情 | 任务卡、任务详情、任务范围审计 | 否 | 任务成员/审批者/提交者/观察者 |
| `EVIDENCE_AUTHORIZED` | 受控原始材料 | 原始音频、原始日志、证据文件 | 是 | 仅显式证据读者 |
| `ADMIN_ONLY` | 管理与高敏操作 | 设置、角色、审计导出、节点控制 | 可能 | 仅超级管理员 |
| `DENY` | 显式拒绝 | 任意 | 否 | 拒绝并审计 |

### 6.2 角色与任务关系

| 角色 | 说明 | 默认能力 |
|---|---|---|
| `OBSERVER` | 只读观察者 | 摘要、任务详情、证据索引；无原始材料。 |
| `TERMINAL_OPERATOR` | 终端执行/观察接管 | 观察、部分证据读取（需关系）、运行烟测。 |
| `SESSION_MANAGER` | 会话管理 | 新建任务、审批（被指派时）、停止自己的任务、会话管理。 |
| `SUPER_ADMIN` | 超级管理员 | 角色、设置、知识推广、审计导出、节点控制。 |
| `SYSTEM` | 控制面内部 | 受控系统动作；不得绕过审计。 |
| `NODE_AGENT` | Windows 节点代理 | 领取作业、回传事实、读取白名单日志；无最终判定。 |
| `AGENT` | AI 代理 | 生成候选、提交草案；无推广权。 |

| 任务关系 | 含义 | 说明 |
|---|---|---|
| `SUBMITTER` | 任务提交者 | 可批准自己的冻结边界（V0.0.1 允许）。 |
| `MEMBER` | 任务成员 | 可查看任务详情和摘要。 |
| `APPROVER` | 被指派审批者 | 可审批，不等于可读全部原始材料。 |
| `VIEWER` | 只读查看者 | 摘要/索引级别。 |
| `EVIDENCE_READER` | 显式证据读者 | 可读任务原始材料，需显式授予。 |
| `NONE` | 无任务关系 | 默认拒绝。 |
| `ANY` | 不要求任务关系 | 仅用于受控管理规则，不用于原始材料。 |

### 6.3 求值顺序

```text
1. 显式 DENY
2. 显式 ALLOW
3. 默认 DENY
```

- 拒绝优先于允许。
- 未知资源、未知角色、未知关系、缺失策略一律 `DENY`。
- 服务端裁剪字段后再下发；客户端过滤不算访问控制。
- 不可执行动作在 UI 中以 disabled + 原因展示，不隐藏页面本身。

### 6.4 默认规则矩阵

| 资源类 | 允许角色 | 任务关系 | 能力 | 访问级别 |
|---|---|---|---|---|
| `TASK_CARD` | 全部 4 个 UI 角色 | `SUBMITTER/MEMBER/APPROVER/VIEWER` | `VIEW_TASK_DETAIL` | `TASK_AUTHORIZED` |
| `REPORT_SUMMARY` | 全部 4 个 UI 角色 | `SUBMITTER/MEMBER/APPROVER/VIEWER` | `VIEW_SUMMARY` | `SUMMARY_INDEX` |
| `EVIDENCE_INDEX` | 全部 4 个 UI 角色 | `SUBMITTER/MEMBER/APPROVER/VIEWER` | `VIEW_EVIDENCE_INDEX` | `SUMMARY_INDEX` |
| `RAW_AUDIO` | `TERMINAL_OPERATOR/SESSION_MANAGER/SUPER_ADMIN` | `EVIDENCE_READER/SUBMITTER/APPROVER` | `READ_RAW_EVIDENCE` | `EVIDENCE_AUTHORIZED` |
| `RAW_LOG` | 同上 | 同上 | `READ_RAW_EVIDENCE` | `EVIDENCE_AUTHORIZED` |
| `EVIDENCE_FILE` | 同上 | 同上 | `READ_RAW_EVIDENCE` | `EVIDENCE_AUTHORIZED` |
| `KNOWLEDGE_CANDIDATE` | 全部 4 个 UI 角色 | `ANY` | 无（读）；审阅需 `REVIEW_KNOWLEDGE_CANDIDATE` | `SUMMARY_INDEX` |
| `KNOWLEDGE_ITEM` | 全部 4 个 UI 角色 | `ANY` | 无 | `SUMMARY_INDEX` |
| `AUDIT_EVENT` | 全部 4 个 UI 角色 | `SUBMITTER/MEMBER/APPROVER/VIEWER` | `VIEW_AUDIT` | `TASK_AUTHORIZED` |
| `AUDIT_EXPORT` | `SUPER_ADMIN` | `ANY` | `EXPORT_AUDIT` | `ADMIN_ONLY` |
| `SETTINGS` | `SUPER_ADMIN` | `ANY` | `MANAGE_SETTINGS` | `ADMIN_ONLY` |
| `USER_ROLE` | `SUPER_ADMIN` | `ANY` | `MANAGE_ROLES` | `ADMIN_ONLY` |
| `NODE_CONTROL` | `SESSION_MANAGER/SUPER_ADMIN` | `ANY` | `MANAGE_NODES` | `ADMIN_ONLY` |
| `DEVICE_CONTROL` | `SESSION_MANAGER/SUPER_ADMIN` | `ANY` | `CONTROL_DEVICE` | `ADMIN_ONLY` |

显式拒绝规则（优先于允许）：

- `OBSERVER` 读取 `RAW_AUDIO`/`RAW_LOG`/`EVIDENCE_FILE` → `DENY`，即使被授予 `EVIDENCE_READER`。
- `AGENT`/`NODE_AGENT` 读取 `SETTINGS`/`USER_ROLE`/`AUDIT_EXPORT` → `DENY`。
- 任何角色读取无任务关系且非 `ANY` 规则覆盖的原始材料 → 默认 `DENY`。

### 6.5 UI 可见 vs 服务端专用

| 对象 | UI 可见 | 受限（按级别） | 服务端专用 |
|---|---|---|---|
| TaskCard | 阶段、运行状态、门禁、实际节点/设备、阻塞方、进度、陈旧/离线状态、最后更新时间 | 无 | `server_metadata.*`、投影构建游标、原始快照引用 |
| Report | 摘要、分母、五轴汇总、四类记录计数、证据索引 | 受限章节明细、受限证据条目 | 报告签名、冻结事件 ID、内部审计引用 |
| KnowledgeCandidate | 标题、分类、适用性、审阅状态、推广状态、警告 | 受限来源的观察/实际结果 | 生成者/审阅者内部 ID、推广事件 ID、状态历史 actor ID |
| KnowledgeItem | 标题、摘要、状态、适用性、冲突/陈旧、版本 | 受限来源的摘要 | 推广人/事件、审阅人 ID |
| AuditEvent | 时间、角色、动作、对象、变更字段、原因、访问决策 | `change.before`/`after` | actor ID、session ID、请求/追踪 ID、IP 哈希、哈希链 |
| AccessPolicy | 级别、角色、关系、规则、字段可见性 | 规则条件 | 策略优先级、被替代策略引用 |

**永不暴露**：原始音频、原始日志正文、密钥、令牌、凭据、PII、绝对存储路径。该规则适用于所有对象和所有访问级别。

## 7. 屏幕到字段映射（未来 UI）

> Intake、Review/Approval、Run Monitor 的专用领域对象（任务草稿、审批单、运行尝试）由 `P0-04`/`P0-06` 领域契约定义；本节只映射本契约拥有的投影和只读字段，不重新定义这些对象。

| 屏幕 | 主要对象 | 可展示字段 | 受限/服务端专用 | 默认访问级别 |
|---|---|---|---|---|
| **Mission Control** | TaskCard 列表/聚合 | `task_id`、`task_title`、`stage`、`status_display`、`run_state`、`blocker.owner`、`progress`（仅计数/标签）、`resources`（节点/设备摘要）、`communication.state`、`freshness.is_stale`、`last_authoritative_update.at`、`last_known_at` | 不展示 `server_metadata`；不展示原始证据；不展示内部投影游标 | `TASK_AUTHORIZED` |
| **Task Detail** | TaskCard + 领域详情 | 全部 TaskCard 字段、`gates.items` 七门禁、五轴、revision/approval 摘要、证据索引计数、阻塞方与下一步、离线/陈旧原因 | 原始证据需跳转 Evidence Browser 并二次鉴权；不展示内部 ID/签名 | `TASK_AUTHORIZED` |
| **Intake** | TaskCard（`stage=DRAFT`）+ 领域草稿 | 入口来源、抽取/继承/推导标记、冲突/缺口、关键事实清单、当前阻塞方、审阅状态；来自 TaskCard 的 `stage`、`blocker`、`freshness` | 代理内部推理、未脱敏原始上传内容、服务端会话游标 | `TASK_AUTHORIZED` |
| **Review/Approval** | TaskCard + Approval/Gate 领域对象 | 修订与范围快照、待审差量、审批人/意见/时间、门禁状态、`blocker.owner`、审批后的 `stage`；相关审计事件 | 审批人内部 ID、策略优先级、原始证据（按需另授权） | `TASK_AUTHORIZED`（审批动作需 `APPROVE_TASK`） |
| **Run Monitor** | TaskCard + Run/Attempt 领域对象 | `run_state`、`stage`、实际节点/设备、`occupancy_state`、`communication`、`freshness`、`progress.counts`、证据接收/核验计数、最近审计事件 | 原始日志正文、绝对路径、节点 spool 内部状态 | `TASK_AUTHORIZED` |
| **Evidence Browser** | Report.evidence_index + EvidenceItem 领域对象 | `evidence_id`、kind、digest、size、collected_at、access_level、`display_path_hint`、核验状态、关联用例/运行 | 原始音频/日志/文件内容仅在 `EVIDENCE_AUTHORIZED` 下按需加载；绝对路径、存储凭据永不展示 | `SUMMARY_INDEX`（元数据）；原始内容 `EVIDENCE_AUTHORIZED` |
| **Reports** | Report | `summary`、`metrics`、`verdict_summary` 五轴、`denominator`、`record_separation`、`blockers`、`residual_risks`、`evidence_index`、`lifecycle_state` | 受限章节明细、报告签名、冻结事件 ID | `SUMMARY_INDEX` |
| **Knowledge** | KnowledgeCandidate + KnowledgeItem | `status`、`item_type`/`classification`、标题、摘要、适用性、冲突/陈旧、审阅/推广状态、警告徽章、来源任务引用 | 受限来源的观察/实际结果、审阅人内部 ID、推广事件 ID | `SUMMARY_INDEX` |
| **Audit** | AuditEvent | `occurred_at`、`recorded_at`、`actor.role`、`action`、`object`、`scope`、`change.change_type`/`changed_fields`、`reason`、`access_decision`、`retention` | `change.before`/`after` 明细（受限）、actor ID、session ID、请求/追踪 ID、哈希链 | `TASK_AUTHORIZED`（任务范围）；导出 `ADMIN_ONLY` |
| **Settings** | AccessPolicy + 系统配置 | 访问级别、角色、任务关系、能力目录、规则摘要、字段可见性、审计设置、策略版本/生效时间 | 策略优先级、被替代策略、密钥/证书、任何凭据 | `ADMIN_ONLY` |

### 7.1 跨屏展示规则

1. Mission Control 只显示投影摘要，不显示原始材料。
2. Task Detail 必须同时显示“最后权威更新”和“最后已知活动”，以及通信/陈旧两个独立徽章。
3. Run Monitor 在通信离线但运行继续时，必须显示“执行可能继续，设备保持占用”，不得显示“设备空闲”。
4. Evidence Browser 的元数据默认可见；点击原始内容必须触发服务端鉴权和审计，拒绝时显示原因分类。
5. Reports 默认只渲染 `summary`、`metrics`、`verdict_summary`、`evidence_index`、`blockers`、`residual_risks`；受限章节以“需要授权”占位，不预先加载内容。
6. Knowledge 的 `stale`/`disputed` 必须在列表行可见；治理动作必须填写理由并留审计。
7. Audit 列表默认按任务范围过滤；跨任务导出需要 `ADMIN_ONLY` 与 `AUDIT_EXPORT`，且导出本身产生 `AUDIT_EXPORT` 事件。
8. Settings 永不显示密钥、证书私钥、原始凭据；只显示策略和脱敏配置。

## 8. Schema 与验证

| 文件 | 对象 | 状态 |
|---|---|---|
| `schemas/experience/task-card.schema.json` | 任务卡投影 | frozen-candidate v1.1 |
| `schemas/experience/report.schema.json` | 报告 | frozen-candidate v1.1 |
| `schemas/experience/knowledge-candidate.schema.json` | 知识候选与生命周期 | frozen-candidate v1.1 |
| `schemas/experience/knowledge-item.schema.json` | 已推广知识条目 | frozen-candidate v1.1 |
| `schemas/experience/audit-event.schema.json` | 不可变审计事件 | frozen-candidate v1.1 |
| `schemas/experience/access-policy.schema.json` | 访问级别、规则与字段可见性 | frozen-candidate v1.1 |

验证命令（仓库根目录）：

```bash
for f in docs/contracts/schemas/experience/*.schema.json; do
  python3 -m json.tool "$f" > /dev/null || exit 1
done

python3 - <<'PY'
import glob, json
from jsonschema import Draft202012Validator
for path in sorted(glob.glob("docs/contracts/schemas/experience/*.schema.json")):
    with open(path, encoding="utf-8") as fh:
        schema = json.load(fh)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema", path
    Draft202012Validator.check_schema(schema)
    print("OK", path)
PY
```

验收口径：

- 6 个 schema 全部存在。
- 每个文件可被 `python3 -m json.tool` 解析。
- 每个文件通过 `Draft202012Validator.check_schema`。
- 每个 schema 的 `x-ui-field-policy` 明确列出 `ui_safe`、`server_only` 和 `never_expose`。
- `grep -RIn "raw_audio_included.*true\|raw_logs_included.*true" docs/contracts/schemas/experience/` 不得有结果。

## 9. 已作出的决策

| ID | 决策 | 理由 | 被拒绝的替代方案 | 代价/后果 |
|---|---|---|---|---|
| D-01 | 任务卡是派生只读投影，不是权威状态。 | 需求要求任务卡独立于会话，同时架构要求单一事实源；投影可重建，避免第二事实源。 | 让任务卡直接持久化状态并接受写操作。 | 投影服务必须可靠；构建失败要显式降级。 |
| D-02 | 未知总量时 `percent=null`，只显示计数/阶段/未知标记。 | 需求明确禁止伪造百分比；显示 0% 或估算值会暗示不存在的完成证据。 | 用耗时/消息数/字节数估算百分比。 | UI 需要更多定性表达，不能只靠一根进度条。 |
| D-03 | 通信、执行、占用、新鲜度四信号分离。 | 已批准的离线续跑规则要求“通信离线 ≠ 停止 ≠ 设备空闲”；旧“租约过期即停止”规则被明确替代。 | 单一 `offline=true` 标志或租约到期自动停止。 | 任务卡和 Run Monitor 必须展示四个独立状态。 |
| D-04 | 主生命周期与五轴判定分离，禁止压成单一 PASS。 | 需求要求 fail-closed 和可追溯；lstest 五轴是平台结果模型。 | 单一 `status: PASS/FAIL` 枚举。 | 报告和任务详情必须并排展示五轴。 |
| D-05 | 报告章节按四类记录强分离，人工补充永不计入自动结果。 | 需求明确人工补充不能产生自动 PASS；ISO 29119-3 要求完成报告结构完整。 | 把人工记录合并进自动化章节或只给总分。 | 报告更长，但可审计性更高。 |
| D-06 | 候选自动生成、永不自动推广；推广需人类 + 目标权限 + 审计。 | 需求与 B-6 均要求 Agent 只能生成候选；频次不能改变已冻结判据。 | 高频候选自动合入或“多数案例自动转正”。 | 知识沉淀需要人工治理成本。 |
| D-07 | 审计事件仅追加、哈希链、不可更新/删除；更正走补偿事件。 | 21 CFR 11 与 NIST AU-11 要求旧记录不可遮蔽、审计与记录同寿命。 | 允许 UPDATE 审计行或物理删除。 | 存储增长；需要归档与哈希校验。 |
| D-08 | 默认报告 `SUMMARY_INDEX`；原始材料仅任务授权证据读者可见；拒绝也审计。 | 需求要求默认摘要/索引、原始材料限任务授权角色；访问拒绝必须可追溯。 | “登录即可看全部”或只在客户端隐藏。 | 需要显式任务关系与证据授权流程。 |
| D-09 | UI 安全/服务端专用字段在 schema 与策略中显式声明，服务端裁剪后再下发。 | 防止把原始路径、签名、内部 ID 泄露给浏览器；客户端过滤不构成访问控制。 | 前端拿到全量数据后自行隐藏。 | 服务端需要按对象裁剪与测试。 |
| D-10 | 报告冻结后不可原地覆盖；更正通过新版本/撤回/勘误事件。 | 报告是交付证据；冻结后修改会破坏审批链和审计链。 | 直接编辑已发布报告。 | 需要版本化与旧版本保留。 |
| D-11 | `last_authoritative_update` 与 `last_known_at` 分开。 | 节点事实可能先到但尚未成为权威状态；合并会掩盖权威延迟。 | 单一“更新时间”。 | UI 需要展示两个时间。 |
| D-12 | 未知计数用 `null`，禁止用 0 冒充；缺阈值按 fail-closed 标记陈旧。 | 真实性要求；0 会被误读为“没有工作”或“已完成”。 | 缺省 0 / 缺省“新鲜”。 | 需要前端显式“未知”状态。 |
| D-13 | `schema_version` 属于载荷，未知版本 fail-closed。 | 防止新旧字段语义混用；历史证据按自身版本解释。 | 无版本或按最新 schema 强解旧载荷。 | 消费者需要版本分支。 |
| D-14 | 知识条目可有 `STALE`/`DISPUTED`/`RETRACTED`，但不得删除历史。 | 知识是参考库，不是永远正确的规则库；过期/冲突必须显式。 | 直接删除过期条目。 | 需要治理队列和排序规则。 |

## 10. 开放问题

以下问题不阻塞本契约的字段结构，但在实现或策略冻结前必须有明确结论：

1. **陈旧/心跳阈值**：`freshness.stale_after_seconds`、心跳周期、投影刷新间隔、离线判定窗口的具体数值由 `P0-08` 冻结；本契约只要求服务端解析后写入投影。
2. **主进度度量**：正式任务默认以“已批准用例数”还是“已批准证据项数”作为主 `percent` 分母，需要 UI 与验收共同确认；本契约允许两者，但要求单一标签。
3. **阻塞方语义**：`blocker.owner` 优先显示具体人还是角色；当前 schema 同时允许 `PERSON`/`ROLE`，需要产品确认默认。
4. **观察者审计范围**：本契约允许角色 1 查看任务范围审计；是否应进一步限制为管理员，需要安全评审确认。
5. **烟测候选的推广资格**：建议烟测/静态检查产生的候选只能作为低置信线索，不得直接推广为正式知识；需要所有者确认。
6. **自动提取的默认适用范围**：建议自动候选默认限定在项目/硬件范围，跨项目推广必须人工提升；需要确认。
7. **报告冻结签名**：schema 要求 `FROZEN` 报告有签名；若签名基础设施尚未就绪，需要明确“未签名冻结”的临时策略或延后该约束。
8. **多运行报告的分母合并**：同一修订下多个正式 `run_id` 的报告如何合并分母、如何处理重试/补传，需要与 `P0-06` 证据契约对齐。
9. **显式证据授权的存储**：`EVIDENCE_READER` 的任务级授权记录属于身份/权限领域，本契约只消费结果，未定义授权表和审批流。
10. **审计导出格式与保留**：审计导出是否需要 WORM/不可变存储、导出保留期和脱敏规则，需要与 `P0-08`/备份方案对齐。
11. **`PUBLIC_SUMMARY` 是否启用**：V0.0.1 当前没有公开摘要场景；保留级别但不默认使用，需要产品确认是否删除。
12. **知识条目冲突排序**：`sort_weight` 的具体算法和“approved 不被 stale 压过”的排序规则需要 UI 设计与知识治理共同确认。

## 11. 变更记录与非声明

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0-candidate.1 | 2026-10-28 | 首次形成任务卡投影、报告、知识候选/条目、审计和访问策略字段级候选契约；显式区分权威状态与投影；固定未知进度、离线续跑、四信号分离、人工补充不产生自动 PASS、知识不自动推广、审计仅追加等规则。 |
| 1.1-candidate | 2026-10-29 | R-03 裁决：§2.3 明确 `UNKNOWN` 仅展示占位；§2.7 补 evidence 第五张映射表；`report_scope.mode` 改为报告覆盖范围语义，新增可选 `contains_blocked`/`contains_stopped`（`1.x`）；`BLOCKED`/`STOPPED` 保留为过渡兼容值。仍为候选，未冻结、未批准，Phase 0 未关闭。 |

**非声明**：

- 本文是 `frozen-candidate v1.1`，不是已批准契约，不构成实现、测试、部署或发布授权。**not production-frozen; Phase 0 not closed**。
- 本文不宣称任何 UI、服务端、节点、数据库、知识库或审计功能已经实现。
- 本文不替代 `P0-04` 领域契约、`P0-05` 节点安全契约、`P0-06` 证据契约或 `P0-08` 阈值契约。
- 本文不宣称所有者已批准；批准须由所有者或指定评审者单独记录。
