# NoahsArk 核心领域契约 v1.1（domain）

> 状态：`frozen-candidate v1.1`，等待 Orchestrator/所有者评审；不是已批准契约。**not production-frozen; Phase 0 not closed**。
> 契约版本：`1.0`。所有载荷必须携带 `schema_version: "1.0"`。
> 权威来源：已批准的需求基线、已确认的架构/模块/字段级评审记录。本文只做字段化表达；冲突时以已批准来源为准。
> 数据库：PostgreSQL 是唯一正式数据库。本文不出现 SQLite、ORM 私有类型或供应商锁定结构。

## 1. 范围与一致性

本文定义 NoahsArk V0.0.1 的核心领域对象：

`Task`、`Revision`、`Approval`、`Gate`、`Case`、`Run`、`Attempt`、`ExecutionBundle`、`Lease`、`Device`、`Node`、`Receipt`。

每个对象给出：字段表、类型、必填性、枚举、状态机、转移守卫、不变量。跨对象规则、五轴判定、离线续跑、STOP-first 重连、设备释放、错误码、幂等键和并发规则在后续章节统一给出。JSON Schema 位于 `schemas/domain/`，与本文同名对象一一对应。

**字段命名规则**：JSON 使用 `snake_case`；布尔字段使用 `is_`/`has_` 前缀或明确动词；时间字段以 `_at` 结尾；摘要字段以 `_digest` 结尾；标识字段以 `_id` 结尾；集合字段使用复数。字段名在 `1.x` 内保持稳定。

## 2. 规范约定

| 项 | 规则 |
|---|---|
| 标识符 | UUID（RFC 9562，规范小写）。`task_id`、`revision_id`、`run_id`、`case_id`、`attempt_id`、`bundle_id`、`node_id`、`device_id`、`lease_id`、`receipt_id`、`approval_id`、`gate_id`、`evidence_id`、`cleanup_receipt_id` 全部为 UUID。`job_id`、`event_id`、`scope_digest` 等由平台生成，同样使用 UUID 或带前缀摘要。 |
| `lead_agent_id` | UUID，引用平台内唯一的 lead agent 记录；一个任务恰好一个，不允许数组。 |
| 时间 | RFC 3339 UTC，必须以 `Z` 结尾（允许小数秒，最多 9 位）。本地时区时间不得进入契约。所有 `*_at` 字段均为 UTC。 |
| 摘要 | `sha256:<64 位小写十六进制>`。v1 只允许 `sha256`；新增算法必须提升 `digest_algorithm` 枚举并保持前缀可区分。 |
| `schema_version` | 字符串常量 `"1.0"`，每个实体载荷必填。缺失或未知版本按 fail-closed 拒绝。 |
| 空值 | 可选字段在缺失时**省略**，不使用 `null`。数组字段缺失等价于空数组仅在明确允许时成立；必填数组必须出现。 |
| 整数 | 非负整数，除明确允许负值的字段外。 |
| 精度 | 金额、比率、阈值不在本契约冻结；以任务级批准和 `P0-08` 为准。 |
| 枚举未知值 | 消费者必须映射为 `UNKNOWN`/`NEEDS_REVIEW`，不得猜测成 PASS 或继续正式分母。 |
| 扩展性 | 所有对象 `additionalProperties: false`。扩展必须新增可选字段或提升主版本，不得塞入自由字典。 |
| 追加性 | 事件、证据、回执、审计只追加；纠错产生新记录并保留原文。 |
| 时区基准 | 审计与状态时间统一 UTC；`tool.log` 等节点本地产物可保留本地时间，但回执必须带 UTC 采集时间和时钟偏移说明。 |

**明确禁止**：SQLite 作为正式数据库、把 SQLite 文件当作控制面事实源、把 ORM 类型写入契约、以设备本地时间替代 UTC 审计时间、以自由文本字段承载判定结论。

## 3. 实体关系

```text
Task (1) ──< Revision (n) ──1 Approval（每个 revision 至多一个有效批准）
  │                │
  │                └──1 ExecutionBundle（冻结后不可变）
  │
  ├──< Gate (n)
  ├──< Run (n) ──< Attempt (n) ──1 Receipt（每次 job/attempt 至多一个最终回执）
  │        │              │
  │        │              └──> Case(case_id, case_version)
  │        └──> Lease (0..1) ──> Device ──> Node
  │
  └──< Case (n, 随 revision 冻结 case_version)
```

- 一个 `task_id` 可以有多个 `revision_id`；同一时刻只有一个 `current_revision_id`。
- 一个 `revision_id` 对应一个冻结 `bundle_id`；修复必须产生新 revision/bundle，不覆盖已执行版本。
- 一个 `run_id` 只属于一个 revision；`static`/`smoke`/`formal` 是互斥模式。
- 一个 `attempt_id` 只属于一个 run 和一个 case version。
- 一个设备在同一时刻至多有一个有效 lease；lease 的 `(node_id, device_id, endpoint_set)` 是占用键。
- `Receipt` 只证明节点事实，不是 `Verdict`。

## 4. Task

### 4.1 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | 常量 `"1.0"`。 |
| `task_id` | uuid | 是 | 长期任务身份，创建后不变。恢复会话、重连、派生修订都不得新建 task。 |
| `task_category` | enum | 是 | V0.0.1 仅 `voice_interaction`。声明其他类别必须拒绝，不得把未运营类别写成已支持。 |
| `title` | string | 是 | 1–200 字符。 |
| `objective` | string | 是 | 1–4000 字符；可观察目标。 |
| `entry_mode` | enum | 是 | `conversation` / `file` / `spreadsheet` / `form` / `template`。 |
| `origin` | object | 是 | 原始输入与来源，见 4.2。原始输入只追加，不覆盖。 |
| `status` | enum | 是 | 见 4.3。 |
| `lead_agent_id` | uuid | 是 | **恰好一个** assigned lead agent。禁止数组、禁止空值。 |
| `lead_session_id` | uuid | 是 | 稳定任务会话；可恢复，但不构成执行授权。 |
| `project_id` | uuid | 否 | 项目范围；用于知识/画像检索，不替代 task 身份。 |
| `current_revision_id` | uuid | 否 | 当前审阅/执行中的 revision；未创建修订时省略。 |
| `revision_ids` | array<uuid> | 是 | 修订谱系，按创建顺序；不得重复。 |
| `created_at` | timestamp | 是 | UTC。 |
| `updated_at` | timestamp | 是 | UTC；状态投影更新时间，不覆盖历史事件。 |

**禁止字段**：`successor_task_id`、`parent_task_id`、`merged_from_task_ids`。范围变化一律在同一 `task_id` 下派生新 revision，不创建 successor 任务。

### 4.2 `origin`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `raw_input_refs` | array<object> | 是（≥1） | 每项含 `ref_id`(uuid)、`kind`(`conversation`/`file`/`spreadsheet`/`form`/`template`)、`digest`(sha256)、`captured_at`。可含 `locator`（不含凭据）。 |
| `submitted_by` | uuid | 是 | 提交者身份。 |
| `submitted_at` | timestamp | 是 | UTC。 |
| `normalization_digest` | digest | 是 | 归一化结果摘要；用于创建幂等。 |

### 4.3 状态机

`DRAFT → REVIEW → APPROVED → EXECUTING → VERIFYING → REPORTED → CLOSED`

异常：任意非终态可进入 `BLOCKED` 或 `STOPPED`；`BLOCKED` 在阻塞解除后可回到进入前的非终态；`STOPPED` 只能由人/安全停止触发，不能自动恢复执行；`ARCHIVED` 为终态，只读。

| 转移 | 守卫 |
|---|---|
| `DRAFT → REVIEW` | 必填关键事实齐备；冲突已显式呈现；未决决策已由人处理。 |
| `REVIEW → APPROVED` | 至少存在一个 `FROZEN` revision，且该 revision 有唯一有效 `APPROVED` approval。 |
| `APPROVED → EXECUTING` | 门禁顺序已到 G2；当前 revision 未 superseded；无阻塞停止请求。 |
| `EXECUTING → VERIFYING` | 对应 run 已结束执行（不要求 PASS）；证据已开始接收。 |
| `VERIFYING → REPORTED` | 报告版本已生成；五轴状态已持久化；未完成证据仍标 `UNVERIFIED`。 |
| `REPORTED → CLOSED` | 设备已释放或已进入隔离；经验条目已生成；审计已落库。 |
| `* → BLOCKED` | 缺批准/指标/资源/必要证据/关联，或范围变化需人审。保留已完成事实。 |
| `* → STOPPED` | 人工停止或设备级安全停止；记录操作者/原因/时间；不伪造完成。 |
| `CLOSED/ARCHIVED → *` | 禁止。归档只读。 |

不变量：

- **T-1**：一个 `task_id` 终身唯一，不因会话恢复、重连、刷新或派生修订而改变。
- **T-2**：一个任务恰好一个 `lead_agent_id`；lead 会话不能替代任务状态或执行授权。
- **T-3**：`status` 变化必须写追加事件（before/after/reason/actor）。
- **T-4**：任务卡/报告只能投影权威状态，不得反向修改 task。

## 5. Revision

### 5.1 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `revision_id` | uuid | 是 | 修订身份；创建后不变。 |
| `task_id` | uuid | 是 | 所属任务。 |
| `revision_number` | integer | 是 | ≥1；同一 task 内单调递增，展示为 `R-<n>`。 |
| `parent_revision_id` | uuid | 否 | 初始修订省略；否则指向派生来源。 |
| `change_kind` | enum | 是 | `initial` / `clarification` / `scope_change` / `repair` / `regeneration` / `knowledge_update`。 |
| `change_reason` | string | 是 | 非 `initial` 必填且非空；记录差异与原因。 |
| `origin` | object | 是 | `original_requirements_digest`、`delta_refs[]`（每项 `ref_id`/`digest`/`kind`）。范围变化必须保留原始需求 + 差量。 |
| `status` | enum | 是 | `DRAFT` / `FROZEN` / `APPROVED` / `SUPERSEDED` / `REJECTED`。 |
| `immutable` | boolean | 是 | `FROZEN`/`APPROVED`/`SUPERSEDED` 时必须为 `true`；`DRAFT` 可为 `false`。 |
| `content_digest` | digest | 是 | 对 `frozen_scope` + `parent_revision_id` + `change_kind` + `origin` 的规范化 JSON 计算。冻结后不变。 |
| `frozen_scope` | object | 是 | 见 5.2；冻结边界。 |
| `frozen_at` | timestamp | 否 | `FROZEN` 及之后必填。 |
| `approved_at` | timestamp | 否 | 唯一有效 approval 生效时写入。 |
| `approval_id` | uuid | 否 | 绑定的有效 approval。 |
| `bundle_id` | uuid | 否 | 冻结执行包；`FROZEN` 后必填。 |
| `superseded_by_revision_id` | uuid | 否 | 同 task 内更新的修订；不是 successor task。 |
| `created_at` | timestamp | 是 | UTC。 |

### 5.2 `frozen_scope`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `scope_digest` | digest | 是 | 整个冻结边界的摘要，审批快照引用此值。 |
| `test_plan_digest` | digest | 是 | 测试方案（步骤、顺序、输入、预期）摘要。 |
| `case_refs` | array<object> | 是 | 每项 `case_id`、`case_version`、`content_digest`。 |
| `oracle_set_digest` | digest | 是 | 判定规则/oracle 集合摘要。 |
| `device_action_set_digest` | digest | 是 | 允许的设备动作集合摘要。 |
| `budget_digest` | digest | 是 | 任务级预算摘要（样本、时长、重试、成本）；具体数值由任务级批准。 |
| `evidence_requirement_digest` | digest | 是 | 必需证据集与脱敏（redaction）策略摘要。 |
| `artifact_refs` | array<object> | 是 | 每项 `artifact_id`、`kind`、`digest`、`size_bytes`。 |
| `anomaly_rule_set_digest` | digest | 是 | 冻结异常规则集摘要。 |
| `dependency_versions` | array<object> | 是 | 每项 `name`、`version`、`digest`；公共底座/适配层/工具版本。 |

### 5.3 状态机与转移守卫

| 转移 | 守卫 |
|---|---|
| `DRAFT → FROZEN` | `frozen_scope` 完整；`content_digest` 已计算；无未决关键冲突；`immutable` 置 `true`；`frozen_at` 写入。 |
| `FROZEN → APPROVED` | 存在唯一有效 approval，且 `approval.scope_snapshot.revision_content_digest == revision.content_digest`；`approval.decision == APPROVED` 且已生效。 |
| `FROZEN → REJECTED` | 审批拒绝或人审拒绝；保留原因；不得执行。 |
| `APPROVED → SUPERSEDED` | 同 task 创建了更新的 revision；旧 revision 与旧 run/证据保持原样。 |
| `DRAFT → DRAFT` | 仅允许修改未冻结内容；每次修改记录新的 `content_digest` 候选。 |
| `FROZEN/APPROVED/SUPERSEDED → 内容修改` | **禁止**。任何内容变化必须新建 revision。 |

不变量：

- **R-1**：冻结后内容不可变；`content_digest`、`frozen_scope`、`origin` 不得原地修改。
- **R-2**：一个 revision 至多一个有效批准；重复批准返回首次结果，不产生第二份有效批准。
- **R-3**：旧 revision 的 run 与证据永不并入新 revision 的分母。
- **R-4**：范围变化必须记录 `parent_revision_id`、原始需求摘要和差量引用。
- **R-5**：平台在 Linux 侧自动修复脚本/音频/规则时也生成新 revision + 新 bundle，不覆盖已执行版本。

## 6. Approval

### 6.1 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `approval_id` | uuid | 是 | 审批记录身份。 |
| `task_id` | uuid | 是 | 所属任务。 |
| `revision_id` | uuid | 是 | 必须指向 `FROZEN` revision。 |
| `submitter_id` | uuid | 是 | 任务提交者；用于自审策略判断。 |
| `approver_id` | uuid | 是 | 审批者。V0.0.1 允许等于 `submitter_id`。 |
| `decision` | enum | 是 | `PENDING` / `APPROVED` / `REJECTED` / `WITHDRAWN` / `SUPERSEDED`。 |
| `comment` | string | 是 | 1–4000 字符；所有决定都必须有意见。 |
| `revision_content_digest` | digest | 是 | 被批准的冻结内容摘要；必须等于 revision 的 `content_digest`。 |
| `scope_snapshot` | object | 是 | `scope_digest`、`case_ids[]`、`oracle_set_digest`、`device_action_set_digest`、`budget_digest`、`evidence_requirement_digest`。 |
| `self_approval` | boolean | 是 | `approver_id == submitter_id` 时为 `true`。 |
| `prevent_self_review` | boolean | 是 | 策略开关；V0.0.1 默认 `false`。开启时自审不得为 `APPROVED`。 |
| `wait_timer_seconds` | integer | 是 | ≥0；生效前等待。 |
| `effective_at` | timestamp | 否 | `APPROVED` 时写入；等于 `decided_at + wait_timer_seconds`，可为未来时间。`now < effective_at` 时审批尚未生效。 |
| `decided_at` | timestamp | 否 | 决定时间；`PENDING` 时省略。 |
| `withdrawn_reason` | string | 否 | `WITHDRAWN` 时必填。 |
| `superseded_by_approval_id` | uuid | 否 | 后续审批取代本条时使用。 |
| `idempotency_key` | string | 是 | 见第 12 节；格式受约束。 |

### 6.2 状态机

`PENDING → APPROVED`（记录决定，`effective_at` 到时生效） / `PENDING → REJECTED` / `PENDING → WITHDRAWN` / `PENDING → SUPERSEDED`

超时**不自动拒绝**：`PENDING` 保持，按策略提醒/升级。`effective_at` 在 `APPROVED` 时写入（`decided_at + wait_timer_seconds`）；`now < effective_at` 时审批只记录为待生效，不得用于执行。

| 转移 | 守卫 |
|---|---|
| `PENDING → APPROVED` | `revision.status == FROZEN`；`revision_content_digest` 匹配；`prevent_self_review=false` 或 `approver_id != submitter_id`；写入 `effective_at = decided_at + wait_timer_seconds`；该 revision 尚无其他有效 `APPROVED`。 |
| `PENDING → REJECTED` | 审批者明确拒绝；必须写 `comment`。 |
| `PENDING → WITHDRAWN` | 审批者撤回；必须写 `withdrawn_reason`。 |
| `PENDING → SUPERSEDED` | 新 revision/新审批取代；旧记录保留。 |
| `APPROVED → *` | 禁止原地修改；如需变更走新 approval（旧记录 superseded）。 |

不变量：

- **A-1**：approval 绑定的是**冻结 revision 的内容摘要 + 范围快照**，不是笼统的任务同意。
- **A-2**：每个 revision 至多一个有效 `APPROVED`；并发批准只有一个生效，其余返回首次结果。
- **A-3**：一次有效批准覆盖正常路径的静态检查 → 资源资格/租约 → 真机烟测 → 正式采样，不需要逐门禁重复人工点击。
- **A-4**：批准不改变冻结范围；范围/判据/设备动作/预算/必需证据变化必须新 revision + 新审批。
- **A-5**：V0.0.1 允许 `approver_id == submitter_id`；`approver != submitter` 只是可选策略，不是当前阻塞项。
- **A-6**：拒绝、撤回、超时、重复批准全部记录操作者、时间、对象、范围、原因，可审计。

## 7. Gate

### 7.1 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `gate_id` | uuid | 是 | 门禁记录身份。 |
| `task_id` / `revision_id` | uuid | 是 | 所属任务与冻结修订。 |
| `run_id` | uuid | 否 | G3–G6 关联的运行；G0–G2 可省略。 |
| `gate_code` | enum | 是 | `G0`…`G7`。 |
| `order_index` | integer | 是 | 0–7，必须与 `gate_code` 一致。 |
| `status` | enum | 是 | `PENDING` / `IN_PROGRESS` / `PASSED` / `FAILED` / `BLOCKED` / `SKIPPED`。 |
| `entered_at` | timestamp | 是 | 进入时间。 |
| `exited_at` | timestamp | 否 | `PASSED`/`FAILED`/`BLOCKED` 时必填。 |
| `evaluated_by` | string | 是 | 系统服务或操作者标识。 |
| `blocker_owner` | string | 否 | 阻塞责任方；`BLOCKED` 时必填。 |
| `blockers` | array<object> | 是 | 每项 `code`、`message`、可选 `owner`。 |
| `evidence_refs` | array<object> | 是 | 每项 `evidence_id`、`digest`、`kind`。 |
| `version` | integer | 是 | 乐观并发版本，≥1。 |
| `notes` | string | 否 | 补充说明，不得替代结构化状态。 |

### 7.2 顺序与守卫

固定顺序：

```text
G0 受理审阅 → G1 冻结批准 → G2 静态检查 → G3 资源资格与租约
→ G4 真机烟测 → G5 正式采样 → G6 证据复核与判定 → G7 报告/知识
```

| 规则 | 说明 |
|---|---|
| 顺序 | `G<n>` 只能在 `G<n-1>` 为 `PASSED` 后进入 `IN_PROGRESS`。`SKIPPED` 仅允许由人显式记录原因，且不得跳过 G1/G5/G6。 |
| 烟雾 | G4 必须使用独立 `run_id`（`mode=smoke`）；G4 的样本永不进入正式分母；G5 只能用 `mode=formal`。 |
| 重新检查 | G3 与 G5 前必须重新执行资源资格与占用检查，不能复用过期结论。 |
| 失败 | `FAILED`/`BLOCKED` 停止推进；修复产生新 revision 或新 run，不原地复活。 |
| 留痕 | 每次进入/退出/失败都写追加事件；`gate.version` 用于并发控制。 |

不变量：

- **G-1**：门禁不可跳序，不可用 UI/报告投影替代门禁事实。
- **G-2**：G1 的批准必须绑定当前 revision 的冻结内容摘要。
- **G-3**：G4 的烟测结果不得作为 G5 的正式结果，也不得进入正式分母。
- **G-4**：G6 的正式 PASS 必须同时满足五轴条件（见第 9 节）。

> `G2.0/G2.1/G2.2`（插件资格、config-only 断言、profile 静态检查）是 G2 的子检查，记录在 `G2.evidence_refs`/`blockers` 中，不新增顶层 `gate_code`，避免与已批准的 G0–G7 序列冲突。

## 8. Case

### 8.1 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `case_id` | uuid | 是 | 稳定用例身份；同名不等于同一用例。 |
| `task_id` | uuid | 是 | 所属任务。 |
| `project_id` | uuid | 否 | 项目范围。 |
| `name` | string | 是 | 人类可读名称；不参与身份判断。 |
| `case_version` | integer | 是 | ≥1；内容变化必须递增，不覆盖旧版。 |
| `content_digest` | digest | 是 | 用例内容摘要。 |
| `status` | enum | 是 | `ACTIVE` / `SUPERSEDED` / `RETIRED`。 |
| `steps` | array<object> | 是 | 每项 `step_index`(≥0)、`action`、`input`、`expected_observable_result`。 |
| `required_inputs` | array<object> | 是 | 每项 `input_id`、`kind`、`digest`（如适用）。 |
| `validity_conditions` | array<string> | 是 | 有效输入/环境条件；不满足即 `INVALID`。 |
| `required_evidence` | array<object> | 是 | 每项 `kind`、`required`(bool)。 |
| `assertion_refs` | array<object> | 是 | 每项 `oracle_id`、`oracle_version`、`digest`。 |
| `frozen_by_revision_id` | uuid | 否 | 首次冻结该版本的 revision。 |
| `supersedes_case_version` | integer | 否 | 被替代版本号。 |
| `created_at` | timestamp | 是 | UTC。 |

不变量：

- **C-1**：`case_id` 稳定；步骤/输入/预期/判据变化产生新 `case_version`。
- **C-2**：每次结果绑定具体 `run_id` + `case_id` + `case_version` + 证据。
- **C-3**：跨修订/项目/设备比较必须显示 `case_version` 与适用条件；内容不同不得只凭名称合并通过率。
- **C-4**：smoke、formal、retry 分别保留 run/attempt 记录，重试不覆盖首次。

## 9. Run 与 Attempt 的五轴判定

### 9.1 五轴字段（Run 与 Attempt 都独立保存，禁止折叠为单一布尔）

| 字段 | 枚举 | 含义 |
|---|---|---|
| `execution_status` | `NOT_STARTED` / `RUNNING` / `COMPLETED` / `ABORTED` / `SKIPPED` | 动作是否执行完毕。`COMPLETED` 只表示执行结束，不等于 PASS。 |
| `validity_status` | `VALID` / `INVALID` / `BLOCKED` / `UNKNOWN` | 输入、环境、样本是否有效。 |
| `business_verdict` | `PASS` / `FAIL` / `EXPECTED` / `WARN` / `NEEDS_REVIEW` / `NOT_EVALUATED` | 业务/任务断言结果；只由 Linux 判定服务写入。 |
| `evidence_status` | `COMPLETE` / `INCOMPLETE` / `CONFLICTED` / `UNVERIFIED` | 必需证据是否齐全、摘要与关联是否一致。 |
| `verification_status` | `PASS` / `FAIL` / `NOT_RUN` | Linux 独立复核结果；正式 PASS 的必要条件。 |

### 9.2 Run 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `run_id` | uuid | 是 | 一次独立执行。 |
| `task_id` / `revision_id` / `bundle_id` | uuid | 是 | 归属与冻结执行包。 |
| `mode` | enum | 是 | `static` / `smoke` / `formal`。模拟不是 run mode。 |
| `lifecycle_status` | enum | 是 | `CREATED` / `DISPATCHED` / `RUNNING` / `FINISHING` / `COMPLETED` / `STOPPED` / `ABORTED` / `BLOCKED`。 |
| `execution_status` / `validity_status` / `business_verdict` / `evidence_status` / `verification_status` | enum | 是 | 见 9.1；未评估时用对应 `NOT_*`/`UNKNOWN`，不得省略。 |
| `node_id` / `device_id` / `lease_id` | uuid | 否 | `static` 必须省略；`smoke`/`formal` 必填。 |
| `lease_epoch` | integer | 否 | ≥1；与 lease 一致。 |
| `communication_state` | enum | 是 | `ONLINE` / `STALE` / `OFFLINE`；独立于占用和运行状态。 |
| `occupancy_state` | enum | 是 | `IDLE` / `OCCUPIED` / `RELEASING`；独立于通信状态。 |
| `execution_permit` | enum | 是 | `GRANTED` / `NOT_GRANTED` / `SUSPENDED`；已启动 run 在通信离线时仍可为 `GRANTED`。 |
| `formal_denominator_eligible` | boolean | 是 | 服务端派生：仅 `mode=formal` 且有效的正式样本为 `true`。客户端不得自行置真。 |
| `attempt_ids` | array<uuid> | 是 | 本 run 的尝试；不得重复。 |
| `cleanup_receipt_id` | uuid | 否 | 与设备释放/清理关联；缺失不自动等于证据不完整。 |
| `evidence_manifest_id` | uuid | 否 | 证据清单引用（清单 schema 由 P0-06 冻结）。 |
| `stop_requested_at` | timestamp | 否 | 停止请求时间；断联期间保持待送达语义。 |
| `stop_reason` | string | 否 | `stop_requested_at` 存在时必填。 |
| `failure_classification` | enum | 否 | `INVALID_INPUT` / `INVALID_ENVIRONMENT` / `INVALID_EVIDENCE` / `VALID_FAILURE` / `BLOCKED` / `STOPPED` / `UNSUPPORTED` / `INFRA_ERROR`。见 9.4 守卫。 |
| `error_code` | string | 否 | 见第 13 节；只用于操作/校验错误，不替代五轴。 |
| `started_at` / `finished_at` | timestamp | 否 | UTC；`RUNNING` 后 `started_at` 必填。 |
| `last_heartbeat_at` | timestamp | 否 | 仅可观测性；不得据此改 run 状态或释放设备。 |
| `created_at` / `updated_at` | timestamp | 是 | UTC。 |

运行为 `static` 时：`node_id`、`device_id`、`lease_id`、`lease_epoch` 必须省略，`formal_denominator_eligible` 必须为 `false`。
运行为 `smoke` 时：`formal_denominator_eligible` 必须为 `false`；证据进入 smoke 证据集，不进入 formal 分母。
运行为 `formal` 时：只能使用 `evidence_origin=real_device` 的 attempt 计入分母；`smoke`/`simulated`/`replay` 证据不得混入。

### 9.3 Attempt 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `attempt_id` | uuid | 是 | 一次用例尝试。 |
| `run_id` | uuid | 是 | 所属 run。 |
| `case_id` / `case_version` | uuid / integer | 是 | 绑定具体用例版本。 |
| `run_mode` | enum | 是 | 与所属 run 的 `mode` 一致。 |
| `attempt_ordinal` | integer | 是 | ≥1；同一 run + case 内单调递增。 |
| `execution_status` / `validity_status` / `business_verdict` / `evidence_status` / `verification_status` | enum | 是 | 见 9.1。 |
| `evidence_origin` | enum | 是 | `real_device` / `simulated` / `replay` / `imported`。 |
| `denominator_eligible` | boolean | 是 | 服务端派生；仅 `run_mode=formal` + `evidence_origin=real_device` + `validity=VALID` + `evidence=COMPLETE` + `execution=COMPLETED` 时为 `true`。 |
| `retry_of_attempt_id` | uuid | 否 | 重试来源；重试不覆盖首次。 |
| `flaky_suspect` | boolean | 是 | 重试通过/行为不稳定时由 Linux 标记；不得因此覆盖首次结果。 |
| `node_id` / `device_id` | uuid | 否 | `static` 省略；`smoke`/`formal` 必填。 |
| `receipt_id` | uuid | 否 | 关联节点回执。 |
| `evidence_ids` | array<uuid> | 是 | 关联证据；可空数组。 |
| `anomaly_event_ids` | array<uuid> | 是 | 关联异常事件；可空数组。 |
| `facts` | array<object> | 是 | 节点事实，见 9.5；不含最终判定。 |
| `failure_classification` | enum | 否 | 同 run；见 9.4。 |
| `started_at` / `finished_at` | timestamp | 否 | UTC。 |
| `created_at` | timestamp | 是 | UTC。 |

### 9.4 `failure_classification` 守卫

| 值 | 允许产生的条件 | 是否进入正式分母 |
|---|---|---|
| `INVALID_INPUT` | 输入不满足用例有效性条件 | 否 |
| `INVALID_ENVIRONMENT` | 无交互会话、端点缺失、环境不满足 | 否 |
| `INVALID_EVIDENCE` | 摘要/关联/完整性失败 | 否 |
| `VALID_FAILURE` | 有效输入下未达预期 | **是**（计入 valid-failure） |
| `BLOCKED` | 缺批准/指标/资源/冲突/必要证据 | 否 |
| `STOPPED` | 人工停止或安全停止 | 否 |
| `UNSUPPORTED` | 超出 V0.0.1 范围 | 否 |
| `INFRA_ERROR` | **仅在对账确认节点/传输/存储故障后** | 否 |

**强约束**：心跳超时、通信离线或 `lease.expires_at` 到期本身**不得**产生 `INFRA_ERROR`、不得停止已启动的冻结压测、不得释放设备。`INFRA_ERROR` 必须有对账记录或独立故障证据支撑。

**与证据侧 `failure_class` 的双向映射（C-02，2026-10-29 裁决）**

本表是唯一映射；大小写不是两套分类学。上表 8 个大写值是**权威持久化词表**，证据侧小写值是**序列化投影**。

| 权威 domain `failure_classification` | 证据投影 `failure_class` | 含义锚点 |
|---|---|---|
| `INVALID_INPUT` | `invalid-input` | 本节 / `evidence-verdict.md` §15.1 |
| `INVALID_ENVIRONMENT` | `invalid-environment` | 同上 |
| `VALID_FAILURE` | `valid-failure` | 唯一进入正式分母的失败类 |
| `BLOCKED` | `blocked` | 前置条件/资源/授权阻塞 |
| `STOPPED` | `stopped` | 安全/人工停止，不是 FAIL |
| `INVALID_EVIDENCE` | `invalid-evidence` | 证据链失败 |
| `UNSUPPORTED` | `unsupported` | 超出 V0.0.1 范围 |
| `INFRA_ERROR` | `infra-error` | 仅对账确认后使用（D-C-14） |
| （省略字段） | `none` | 无失败分类；`null`、省略与 `none` 三者等价（E-02） |
| （无对应枚举值） | `needs-review` | 由 `business_verdict=NEEDS_REVIEW` + `verification_status!=PASS` 表达，不写入 `failure_classification` |

规则：

1. 双向转换必须使用同一张机器可读映射表；实现不得各自硬编码词串。候选路径 `docs/contracts/mappings/failure-class.json` 由所有者决定是否建立，本版本不创建。
2. `none` 不得写成 domain `NONE`；`needs-review` 不得写成 domain `NEEDS_REVIEW`（除非未来另行走 §3.6 兼容扩展并明确不计入分母）。
3. 表外值一律 fail-closed 为 `NEEDS_REVIEW`，不得猜测成 `valid-failure` 或 `none`，不得进入正式分母。
4. 只有 `valid-failure` ↔ `VALID_FAILURE` 计入正式分母；其余 7 类与 `none`/`needs-review` 均不计入。

### 9.5 `facts` 元素

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `fact_id` | uuid | 是 | 事实身份。 |
| `name` | string | 是 | 稳定事实名（如 `audio_playback_started`）。 |
| `value_type` | enum | 是 | `string` / `number` / `boolean`。 |
| `value` | string/number/boolean | 是 | 与 `value_type` 一致。 |
| `unit` | string | 否 | 单位。 |
| `observed_at` | timestamp | 是 | 节点本地采集后换算 UTC。 |
| `source` | enum | 是 | `node_agent` / `lstest_adapter` / `device` / `linux_log_read`。 |

## 10. ExecutionBundle

### 10.1 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `bundle_id` | uuid | 是 | 冻结执行包身份。 |
| `task_id` / `revision_id` | uuid | 是 | 所属任务与修订。 |
| `status` | enum | 是 | `FROZEN` / `SUPERSEDED` / `REVOKED`。 |
| `digest` | digest | 是 | 对除 `digest`/`created_at` 外全部业务字段的规范化 JSON 计算。 |
| `approval_snapshot` | object | 是 | `approval_id`、`revision_id`、`revision_content_digest`、`scope_digest`、`approved_by`、`approved_at`。 |
| `layers` | object | 是 | `common_base`、`project_adapter`、`task_definition`；每层含 `layer_version`、`content_digest`、`source_refs[]`。 |
| `artifacts` | array<object> | 是 | 每项 `artifact_id`、`kind`、`relative_path`、`digest`、`size_bytes`、`required`、`executable`。 |
| `anomaly_rules` | object | 是 | `rule_set_id`、`version`、`digest`、`required`。B-5 要求执行包必须包含异常规则。 |
| `evidence_requirements` | object | 是 | `required_evidence_set_digest`、`redaction_policy_digest`。 |
| `device_requirements` | object | 是 | `capability_ids[]`、`endpoint_set[]`、可选 `equivalence_group_id`、`runtime_binding`（`os`、`python_version`、`lstest_version`、`adapter_version`）。 |
| `run_constraints` | object | 是 | `allowed_modes[]`、`budget_digest`、`timeout_policy_digest`、`retry_policy_digest`。 |
| `created_at` / `frozen_at` | timestamp | 是 | UTC。 |
| `superseded_by_bundle_id` | uuid | 否 | 新 bundle 取代时使用。 |

工件路径规则：必须是 run 内相对路径；禁止绝对路径、盘符、`..`、UNC 路径和符号链接逃逸。`executable` 仅对 `script`/`adapter` 可为 `true`。

不变量：

- **B-1**：bundle 由 Linux 生成、审核、版本化、冻结；Windows Node Agent 只校验和执行。
- **B-2**：`digest`、`approval_snapshot`、`layers`、`artifacts`、`anomaly_rules` 冻结后不可变；修复产生新 bundle/revision。
- **B-3**：工件缺失、摘要不符、任一版本轴不受支持时节点拒绝启动并回传原因。两个版本轴分别校验，不得互相推导或要求相等（R-01，见下）。
- **B-4**：`allowed_modes` 必须包含 `formal` 才能执行正式采样；`smoke` 不得混入正式分母。
- **B-5**：`anomaly_rules` 不能为空；节点只能按已冻结规则观察、上报和执行预定义安全动作。

**版本轴（R-01，2026-10-29 裁决）**

Execution Bundle 有两个**互不比较**的版本轴：

| 轴 | 位置 | 值 | 语义 |
|---|---|---|---|
| Bundle 格式标识 / 引用命名空间 | `security/job.schema.json` → `payload.execution_bundle.schema_version` | `noahsark.execution-bundle/v1` | 该引用句柄按哪套信封与工件命名规则解析。 |
| 载荷 schema 版本 | `domain/execution-bundle.schema.json` → `schema_version` | `"1.0"` | 载荷字段语义版本，遵循 `README.md` §3.2；未知即 fail-closed。 |

- 节点必须**分别**校验：格式标识 ∈ 当前支持集合 `{noahsark.execution-bundle/v1}`；载荷 `schema_version` ∈ 当前支持集合 `{"1.0"}`。
- 禁止把 `"noahsark.execution-bundle/v1" != "1.0"` 判为不兼容；禁止用任一轴推导另一轴。
- 任一轴不受支持 → 拒绝执行，保留原始值，不猜测、不回退。
- 控制面错误表达复用 `SCHEMA_VERSION_UNSUPPORTED`；节点回执的错误码闭集见 `security-node.md` §19.2，节点侧不得假设存在 `subject` 字段。

## 11. Lease、Device、Node

### 11.1 Lease 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `lease_id` | uuid | 是 | 租约身份。 |
| `node_id` / `device_id` | uuid | 是 | 占用资源。 |
| `endpoint_set` | array<enum> | 是 | ≥1，唯一；域内元素是 `endpoint_kind` 能力类：`audio_capture` / `audio_playback` / `serial` / `usb` / `gpio`。字段名为历史遗留；线协议 `lease.endpoint_set` 与占用键中的 `endpoint_set` 是 `endpoint_id` 身份集合，两者不得混用（C-04，见 §11.2 与 `security-node.md` §19.2）。 |
| `task_id` / `revision_id` / `run_id` | uuid | 是 | 占用的任务与运行。 |
| `job_id` | uuid | 否 | 当前作业。 |
| `epoch` | integer | 是 | ≥1；每次重新获取/重新对账递增；旧 epoch 不得恢复执行权。 |
| `state` | enum | 是 | `GRANTED` / `HELD` / `RELEASING` / `RECLAIM_PENDING` / `RELEASED` / `QUARANTINED`。 |
| `occupancy_state` | enum | 是 | `OCCUPIED` / `RELEASING` / `IDLE`；与通信状态分离。 |
| `communication_state` | enum | 是 | `ONLINE` / `STALE` / `OFFLINE`；仅表示可见性。 |
| `execution_permit` | enum | 是 | `GRANTED` / `NOT_GRANTED` / `SUSPENDED`；已启动 run 断线仍可为 `GRANTED`。 |
| `acquired_at` / `renewed_at` | timestamp | 是 / 否 | UTC。 |
| `expires_at` | timestamp | 是 | **仅表示续约截止时间，不是所有权到期**；到期不释放占用、不停止已启动 run。 |
| `last_heartbeat_at` | timestamp | 否 | 可观测性。 |
| `release_preconditions` | object | 是 | `local_stop_confirmed`、`safe_cleanup_done`、`occupancy_reconciled`（均 boolean）。 |
| `released_at` | timestamp | 否 | `RELEASED` 时必填。 |
| `release_reason` / `reclaim_reason` | string | 否 | 释放/回收原因。 |
| `error_code` | string | 否 | 校验/操作错误码。 |
| `version` | integer | 是 | 乐观并发版本。 |
| `idempotency_key` | string | 是 | 见第 12 节。 |

### 11.2 Lease 状态机

```text
GRANTED → HELD → RELEASING → RELEASED
   │        │
   │        ├── COMMUNICATION LOST → RECLAIM_PENDING → HELD（对账恢复）
   │        │                                   └── RELEASING（确认停止+清理+对账）
   │        └── 持续故障/清理失败 → QUARANTINED
   └── 未确认领取 → RELEASED
```

| 转移 | 守卫 |
|---|---|
| `GRANTED → HELD` | 节点确认领取；`epoch` 匹配；工件校验通过；无待送达 STOP。 |
| `HELD → RECLAIM_PENDING` | 心跳失联或通信 stale；**保持 `occupancy_state=OCCUPIED`**；不重派。 |
| `RECLAIM_PENDING → HELD` | 重连完成补传、去重、对账；epoch 未失效或已显式递增。 |
| `HELD/RECLAIM_PENDING → RELEASING` | 本地停止确认；安全清理完成；开始占用对账。 |
| `RELEASING → RELEASED` | 三项 `release_preconditions` 全部 `true`；`released_at` 写入。 |
| `HELD → QUARANTINED` | 清理失败、设备失控或达隔离阈值；人工核验后恢复。 |
| `RELEASED → *` | 禁止；重跑必须新 run/attempt。 |

不变量：

- **L-1**：占用键 `(node_id, device_id, endpoint_set)` 在任一端点集合上不得并发分配。
- **L-2**：`communication_state != ONLINE` **不等于**设备空闲、run 停止或租约失效。
- **L-3**：`expires_at` 到期只触发续约告警/`RECLAIM_PENDING`，不自动释放、不自动判 run 失败、不自动重派。
- **L-4**：旧 `epoch` 的消息可作为历史证据保留，但不得取得当前执行权或覆盖当前状态。
- **L-5**：设备释放独立于证据定稿、GB 级日志归档和最终判定；只需本地停止、安全清理、占用对账。
- **L-6**：缺少 `cleanup_receipt` 只表示无法确认设备释放，设备保持占用；**不直接等同于 `evidence_status=INCOMPLETE`**。

**线协议 `lease.state` 接收映射（C-03，2026-10-29 裁决）**

本表只由控制面在接收线协议消息时执行；节点不得自行映射（§19 原则）。

| 线协议 `lease.state` | 领域 `Lease.state` | `occupancy_state` | 守卫/说明 |
|---|---|---|---|
| `granted` | `GRANTED` | `OCCUPIED` | 仅表示已授予；节点确认领取（`GRANTED→HELD` 守卫）后才 `HELD`。 |
| `renewed` | `HELD` | `OCCUPIED` | 只延长 `expires_at`；若当前为 `RECLAIM_PENDING`，**保持** `RECLAIM_PENDING` 直到补传/去重/对账完成；`renewed` 本身不恢复 `HELD`。 |
| `released` | `RELEASING` →（守卫通过后）`RELEASED` | `OCCUPIED` → `IDLE` | 线协议 `released` 只是**释放主张**；三项 `release_preconditions` 全 `true` 才落 `RELEASED`，否则停在 `RELEASING` 并返回 `LEASE_RELEASE_PRECONDITION_FAILED`，占用保持 `OCCUPIED`。 |
| `expired` | 不降级、不升级：`GRANTED`→`GRANTED`；`HELD`+通信 `ONLINE`→`HELD`；`HELD`+通信 `STALE`/`OFFLINE`→`RECLAIM_PENDING` | `OCCUPIED` | **永不**映射到 `RELEASED`/`IDLE`，不判 run 失败，不重派（L-3 / B-4）。`GRANTED` 未经领取确认不得因 `expired` 变 `HELD`。 |
| `revoked` | `RELEASING` | `OCCUPIED` | 对应 `on_explicit_revoke=stop_safe`；先 STOP-first 安全停止。清理失败/安全事件 → `QUARANTINED`。 |
| `reclaimed` | `RECLAIM_PENDING` | `OCCUPIED` | 表示控制面发起回收；最终只能进入 `HELD`（对账后确认仍持有）或 `RELEASING`，**不得**直接跳 `RELEASED`。 |
| 表外值 | 不改变当前状态 | 保持原值 | 记录审计 + 告警；不停止已启动 run、不释放、不重派；该租约不得用于新派发，直到人工确认。 |

- `revoked`/`reclaimed` 在重连未完成对账前只能停留在 `RELEASING`/`RECLAIM_PENDING`，不得绕过 STOP-first（B5）。
- `QUARANTINED` **没有**线协议对应值，只能由控制面在审计后写入。
- 本表必须与 `security-node.md` §19.2、`evidence-verdict.md` §13.1 保持一致，不得出现第二套取值。

### 11.3 Device 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `device_id` | uuid | 是 | 设备身份。 |
| `node_id` | uuid | 是 | 所属节点。 |
| `identity` | object | 是 | `manufacturer`、`model`、`hardware_revision`、`serial_number_masked`、`identity_digest`。禁止明文真实序列号进入契约示例。 |
| `capabilities` | array<string> | 是 | 能力标识；稳定字符串。 |
| `endpoints` | array<object> | 是 | 每项 `endpoint_id`、`kind`（同 lease 枚举）、`binding`、`available`。 |
| `firmware_version` | string | 是 | 固件/软件版本。 |
| `config_digest` | digest | 是 | 配置摘要。 |
| `adapter_version` | string | 是 | 项目-lstest 适配版本。 |
| `project_scope` | array<uuid> | 是 | 适用项目。 |
| `pool_state` | enum | 是 | `DISCOVERED` / `READY` / `RESERVED` / `ATTACHED` / `DRAINING` / `QUARANTINED` / `OFFLINE` / `RETIRED`。 |
| `health_state` | enum | 是 | `HEALTHY` / `DEGRADED` / `UNHEALTHY` / `UNKNOWN`。 |
| `communication_state` | enum | 是 | `ONLINE` / `STALE` / `OFFLINE`。 |
| `occupancy_state` | enum | 是 | `IDLE` / `OCCUPIED` / `RELEASING`。 |
| `current_lease_id` | uuid | 否 | 当前有效租约。 |
| `equivalence` | object | 否 | `equivalence_group_id`、`conditions_digest`、`verified_at`、`verified_by`；任务批准前不得跨组替代。 |
| `provenance` | object | 是 | `source`、`verified_at`、`verified_by`。 |
| `last_seen_at` | timestamp | 否 | 可观测性。 |
| `created_at` / `updated_at` | timestamp | 是 | UTC。 |
| `error_code` | string | 否 | 最近一次校验/健康错误。 |

不变量：

- **D-1**：设备目录记录来源、版本、最近核验时间；能力/版本/端点/健康/占用任一不满足即不得进入候选。
- **D-2**：`pool_state` 为 `RESERVED`/`ATTACHED` 时必须 `occupancy_state=OCCUPIED`。
- **D-3**：通信离线可与 `OCCUPIED` 并存；不得把 `OFFLINE` 映射成 `IDLE`。
- **D-4**：跨型号/等价组替代必须由任务级批准并记录原因；单设备结果不外推。
- **D-5**：`DRAINING` 不再接新任务；`QUARANTINED` 必须人工授权恢复并留审计。
- **D-6（C-05，2026-10-29）**：`Lease.state=QUARANTINED` 时 `occupancy_state` 必须为 `OCCUPIED`（不可再分配）；该约束已在 `schemas/domain/lease.schema.json` 的 `allOf` 中表达。

**设备占用三层（C-05，2026-10-29 裁决）**

| 层 | 内容 | 权威性 |
|---|---|---|
| L1 权威 | `Lease.state`（6 值）+ `Device.pool_state`（8 值）+ `release_preconditions` | 唯一事实源 |
| L2 粗投影 | `occupancy_state` ∈ {`IDLE`,`OCCUPIED`,`RELEASING`} | 服务端派生写入 |
| L3 展示/历史 | `docs/v2`/`openspec` 的四值枚举；`device-occupancy.state` 的 10 值细化 | 展示/证据细化，不是新权威 |

**四值历史词 → 三值/权威投影**：

- `OCCUPIED → OCCUPIED`
- `RELEASING → RELEASING`
- `RELEASED → IDLE` **仅当**三项 `release_preconditions` 全 `true` 且 `device-occupancy.release_state=released`；否则 `OCCUPIED`（视为 `held_pending_cleanup`）
- `QUARANTINED → occupancy_state=OCCUPIED`（不可再分配）+ `pool_state=QUARANTINED` + `Lease.state=QUARANTINED`

`RELEASED` 与 `QUARANTINED` **不是** occupancy 值；不得扩展 `occupancy_state` 为第四值。`docs/v2`/`openspec` 的四值回写属 P0-03 后续同步批次，SR-14 在本版本中仍为**开放**，不得声称“占用枚举已统一”。

### 11.4 Node 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `node_id` | uuid | 是 | 节点身份。 |
| `hostname` | string | 是 | 节点主机名。 |
| `identity` | object | 是 | 证书指纹/主题/链 ID、签发/到期时间、轮换代数；可选撤销时间与原因。具体算法由 P0-05 冻结。 |
| `agent_version` | string | 是 | Node Agent 版本。 |
| `os` | object | 是 | `name`、`version`、`build`。 |
| `runtime` | object | 是 | `python_version`、`lstest_version`、`adapter_version`。 |
| `communication_state` | enum | 是 | `ONLINE` / `STALE` / `OFFLINE`。 |
| `last_heartbeat_at` | timestamp | 否 | 可观测性。 |
| `heartbeat_interval_seconds` | integer | 是 | ≥1；仅参数占位，数值由 P0-08。 |
| `status` | enum | 是 | `ACTIVE` / `DRAINING` / `QUARANTINED` / `RETIRED`。 |
| `interactive_session` | object | 是 | `state`（`AVAILABLE`/`UNAVAILABLE`/`LOCKED`）、可选 `session_id`、`checked_at`。无会话即 `BLOCKED`，不降级。 |
| `work_dir` | object | 是 | `drive`（如 `D:`）、`root`、`capacity_bytes`、`free_bytes`、`warn_threshold_bytes`、`protect_threshold_bytes`。 |
| `spool` | object | 是 | `state`（`NORMAL`/`WARN`/`PROTECT`/`BLOCKED`）、`used_bytes`、阈值、可选 `oldest_message_at`。 |
| `capabilities` | array<string> | 是 | 节点能力。 |
| `endpoint_ids` | array<string> | 是 | 节点可见端点。 |
| `quarantine_reason` | string | 否 | `status=QUARANTINED` 时必填。 |
| `registered_at` / `updated_at` | timestamp | 是 | UTC。 |
| `error_code` | string | 否 | 最近一次注册/心跳/校验错误。 |

不变量：

- **N-1**：节点只出站注册/领取/回传；不接受任意 Shell/PowerShell/SSH 命令。
- **N-2**：无交互会话时音频/串口/GUI 任务必须 `BLOCKED`，不得在 Session 0 降级执行。
- **N-3**：节点心跳消失只改变 `communication_state`，不改设备占用、不停止已启动 run、不释放 lease。
- **N-4**：证书撤销/轮换必须审计；旧回执可验签，但撤销后新连接不得接受。
- **N-5**：spool 达 `WARN` 禁止启动新 case；达 `PROTECT` 本地安全停止并保全证据。
- **N-6**：D: 完整大日志默认留在节点；Linux 按白名单按需读取；远程可读不等于异机备份。

## 12. Receipt

### 12.1 字段

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `schema_version` | string | 是 | `"1.0"`。 |
| `receipt_id` | uuid | 是 | 回执身份。 |
| `job_id` | uuid | 是 | 作业身份。 |
| `attempt` | integer | 是 | ≥1；同一 job 的尝试序号。 |
| `job_kind` | enum | 是 | `static_check` / `smoke` / `formal` / `stop_safe` / `diagnostics` / `cleanup`。`cleanup` 与 `diagnostics` 是辅助作业，不改变 `Run.mode`；映射见 §12.3。 |
| `task_id` / `revision_id` / `run_id` / `bundle_id` | uuid | 是 | 关联链。 |
| `bundle_digest` | digest | 是 | 被执行的冻结包摘要。 |
| `node_id` | uuid | 是 | 产生事实的节点。 |
| `device_id` | uuid | 否 | `static_check`/`diagnostics` 可省略；`smoke`/`formal` 必填。 |
| `lease_id` / `lease_epoch` | uuid / integer | 否 | 设备作业必填。 |
| `execution_status` | enum | 是 | 仅执行轴：`NOT_STARTED` / `RUNNING` / `COMPLETED` / `ABORTED` / `SKIPPED`。 |
| `node_facts` | array<object> | 是 | 结构同 9.5；只含事实。 |
| `anomaly_event_ids` | array<uuid> | 是 | 节点按冻结规则上报的异常。 |
| `evidence_manifest_ref` | object | 否 | `manifest_id`、`manifest_digest`、可选 `relative_path`。 |
| `cleanup_receipt` | object | 否 | `cleanup_receipt_id`、`cleanup_status`（`completed` / `completed_with_warnings` / `failed` / `not_required` / `unknown`）、`local_stop_confirmed`、`safe_cleanup_done`、`occupancy_reconciled`、`completed_at`、可选 `notes`。`smoke`/`formal` 结束回执必填。 |
| `sequence` | integer | 是 | ≥0；同一 node+job 单调递增。 |
| `previous_receipt_digest` | digest | 否 | 链式防篡改。 |
| `signature` | object | 是 | `algorithm`、`key_id`、`nonce`、`signed_payload_digest`、`signature_value`、`signed_at`。算法由 P0-05。 |
| `chain_status` | enum | 是 | `RECEIVED` / `VALIDATED` / `RECONCILED` / `REJECTED`。 |
| `received_at` / `validated_at` | timestamp | 否 | Linux 接收/校验时间。 |
| `error_code` | string | 否 | 校验错误码。 |

**禁止字段（必须不存在）**：`business_verdict`、`verification_status`、`final_verdict`、`pass`、`fail`、`platform_verdict`。回执只证明事实；最终判定由 Linux 控制面独占写入。

> **cleanup 细节归属**：详细清理回执（步骤、资源、`cleanup_status`、signature 等）以 P0-06 的 `schemas/evidence/cleanup-receipt.schema.json` 为准。本节 `cleanup_receipt` 只是设备释放前置条件的**最小投影**：`local_stop_confirmed` / `safe_cleanup_done` / `occupancy_reconciled` 必须与该权威回执及控制面占用对账结果一致；两处不得互相矛盾。
>
> **R-02 更正（2026-10-29）**：security 侧 `cleanup_receipt` 是本节最小投影的**超集**，其 `operational_detail` 仅为传输期便捷载体；domain 侧以 `additionalProperties: false` **显式拒绝** `operational_detail`，不做承载。跨侧转换必须按 `evidence-verdict.md` §12.1.1 逐字段进行，未知字段丢弃并审计。本日之前的“同一最小释放投影”表述不再作为规范，保留为历史记录。

### 12.2 回执状态机

`RECEIVED → VALIDATED → RECONCILED`；任一步可 `→ REJECTED`（签名/摘要/关联/序号失败）。重复 `job_id + attempt` 幂等返回首次结果，不创建第二份最终回执。

不变量：

- **P-1**：`job_id + attempt` 唯一；重复送达不重复播放、采样或执行。
- **P-2**：回执签名覆盖规范化回执、`manifest_digest`、`bundle_digest`、`job_id`、`attempt`、`lease_id`、`epoch`、`node_id`、`sequence`、时间基准。
- **P-3**：旧 `epoch` 回执只能作为历史证据，不得改写当前 run/占用。
- **P-4**：`cleanup_receipt` 缺失 → `occupancy_reconciled=false`，设备保持占用；不等于证据不完整，也不自动阻断非必要日志缺失。
- **P-5**：回执不得包含最终业务判定；违反即拒绝。

### 12.3 协议 action/mode 与领域词汇映射

线协议 `Job.action`/`Job.mode` 与领域 `Receipt.job_kind`/`Run.mode` 的显式映射以 `security-node.md` §19.2 为准；领域侧摘要如下。

| 协议 `action` | 领域 `Receipt.job_kind` | 领域 `Run.mode` | 说明 |
|---|---|---|---|
| `static_check` | `static_check` | `static` | 静态检查运行。 |
| `smoke` | `smoke` | `smoke` | 烟测独立 run，不计入正式分母。 |
| `formal` | `formal` | `formal` | 正式采样运行。 |
| `diagnostics` | `diagnostics` | 不改变 | 辅助作业。 |
| `cleanup` | `cleanup` | 不改变 | 辅助清理作业；不新建或改写 Run。 |
| STOP 路径 | `stop_safe` | 不改变 | STOP 指令或本地安全停止，不是 cleanup。 |

- `Run.mode` 仍只有 `static`/`smoke`/`formal`；`cleanup`/`diagnostics` 仅作为 `Receipt.job_kind` 存在。
- 节点回执 `status` 是线协议生命周期，不是 `chain_status` 或最终判定；evidence 投影映射见 `security-node.md` §19.2 与 `evidence-verdict.md` §12.5。
- **证据侧 mode 归一（C-01，2026-10-29）**：`evidence-manifest`、`verdict`、`report-evidence-index` 的 `mode` 只允许 `static`/`smoke`/`formal`；`static_check` 只存在于 `job.action` 与 `Receipt.job_kind`。读侧若接受旧值 `static_check`，只能作为 `static` 的只读别名并记录兼容告警；写出方必须只写 `static`。关联校验比较归一后的 mode，未知值 fail-closed，不得当成 `static`。
- **`case_version` 类型（C-06，2026-10-29）**：所有层的 `case_version` 均为 `integer ≥ 1`；domain 三实体（Case/Attempt/Revision）与 evidence 侧（manifest/verdict）一致。字符串只允许显式兼容读入并归一，不得作为连接键。

## 13. 跨实体不变量（摘要）

| ID | 不变量 |
|---|---|
| I-01 | 一个 `task_id` 是长期权威身份；不创建 successor task。 |
| I-02 | 一个 task 恰好一个 lead agent；lead 会话只是交互上下文。 |
| I-03 | revision 冻结后不可变；内容变化派生新 revision。 |
| I-04 | 一个 revision 至多一个有效批准；批准绑定冻结内容摘要与范围快照。 |
| I-05 | 门禁严格按 G0→G7；G4 烟测不进入正式分母。 |
| I-06 | 五轴状态分别保存；正式 PASS 需五轴同时满足。 |
| I-07 | 烟测/模拟/回放证据永不进入正式分母。 |
| I-08 | 已启动冻结压测断线继续；通信离线不等于设备空闲或 run 停止。 |
| I-09 | 重连先处理待 STOP，再补传、去重、对账；旧 epoch 不能取得执行权。 |
| I-10 | 设备释放只依赖本地停止、安全清理、占用对账；不依赖证据定稿/大日志归档/最终判定。 |
| I-11 | 缺 `cleanup_receipt` 表示占用未对账，不等于 `evidence_status=INCOMPLETE`。 |
| I-12 | 回执只含事实，不含最终判定。 |
| I-13 | 每个 run/attempt 的证据独立；旧证据不并入新 revision/分母。 |
| I-14 | 重试产生新 attempt，首次结果不覆盖；重试通过标 `FLAKY_SUSPECT`。 |
| I-15 | 原始事件/证据/判定只追加；归档只改 locator，不改 `evidence_id`/digest。 |
| I-16 | 所有时间 UTC；所有 ID UUID；所有摘要 sha256 前缀。 |
| I-17 | 校验失败 fail-closed；未知枚举不得当 PASS。 |
| I-18 | PostgreSQL 是唯一正式数据库；禁止 SQLite 作为事实源。 |

## 14. 五轴判定与正式 PASS

正式 `PASS` 的必要条件（全部满足，缺一不可）：

```text
execution_status == COMPLETED
AND validity_status == VALID
AND business_verdict == PASS
AND evidence_status == COMPLETE
AND verification_status == PASS
```

派生规则：

| 场景 | 五轴表达 | 正式分母 |
|---|---|---|
| 正常通过 | COMPLETED / VALID / PASS / COMPLETE / PASS | 计入 |
| 有效失败 | COMPLETED / VALID / FAIL / COMPLETE / PASS | 计入 |
| 输入无效 | COMPLETED/ABORTED / INVALID / NOT_EVALUATED / COMPLETE 或 INCOMPLETE / NOT_RUN | 不计入 |
| 环境阻断 | ABORTED/BLOCKED / BLOCKED / NOT_EVALUATED / UNVERIFIED / NOT_RUN | 不计入 |
| 证据不完整 | COMPLETED / VALID 或 UNKNOWN / NOT_EVALUATED / INCOMPLETE / NOT_RUN | 不计入 |
| 停止 | ABORTED / UNKNOWN / NOT_EVALUATED / 视情况 / NOT_RUN | 不计入 |
| 重试通过 | 新 attempt 五轴通过，首次 attempt 保留 | 首次不计入；重试标 `FLAKY_SUSPECT` |
| 烟测 | 独立 run，`mode=smoke` | **永不**计入 |
| 模拟 | `evidence_origin=simulated` | **永不**计入 |

`business_verdict` 与 `verification_status` 只能由 Linux 控制面写入；节点回执、UI、Lead 会话均不得直接写最终判定。

## 15. 离线续跑、STOP-first 重连、设备释放

### 15.1 三个独立状态

| 维度 | 字段 | 含义 |
|---|---|---|
| 通信可见性 | `communication_state` | 节点是否可达；`OFFLINE`/`STALE` 只影响可见性。 |
| 设备独占 | lease `occupancy_state` / `state` | 设备是否仍被当前 run 占用；失联不改变占用。 |
| 作业执行许可 | `execution_permit` | 已启动作业是否可继续本地执行；断线不自动撤销。 |

### 15.2 断线规则

1. 已启动的冻结压测在通信中断、心跳不可达、`expires_at` 到期后**继续执行**。
2. Linux 将设备/节点标为 `OFFLINE`/`STALE`，但保持 `OCCUPIED` 和 `execution_permit=GRANTED`。
3. 断线期间**不得**启动新 case、不得领取新 job、不得重派、不得重播、不得重复采样。
4. 节点本地持久保存进度、异常、日志、证据；spool 达阈值按 N-5 处理。
5. 正常停止路径：节点侧人工停止、Linux 下发停止指令。Linux 指令在断线期间保持待送达。
6. 设备级安全停止（失控、死机、预设危险状态）由节点本地独立生效，不依赖 Linux 在线。

### 15.3 重连顺序（STOP-first）

```text
1. 识别并优先处理待送达 STOP
2. 停止后续测试动作（已执行动作保持历史）
3. 补传本地消息/日志/异常/证据
4. 按 event/evidence/receipt 标识去重
5. 核对 run 位置、设备状态、lease/epoch、占用
6. 对账完成后才恢复正常同步/领取新 job
```

- 对账完成前设备保持占用，不重派。
- 旧 epoch 消息可作历史事实，但不得改变当前运行或取得执行权。
- 迟到的 STOP 不改写已执行动作历史。
- 重传不得触发重复执行；再次执行必须由 Linux 显式创建新 attempt/run。

### 15.4 设备释放前置条件

释放设备必须同时满足：

1. `local_stop_confirmed = true`（本地执行已停止）。
2. `safe_cleanup_done = true`（设备已安全清理）。
3. `occupancy_reconciled = true`（占用已对账）。

释放**不需要**：完整 GB 级日志归档、证据最终定稿、正式判定完成。三者独立跟踪。

释放后的证据仍可继续上传/校验；`evidence_status` 与 `verification_status` 独立更新。清理失败或占用不确定时保持占用并进入 `QUARANTINED`，不得重派。

## 16. 幂等键

| 操作 | 幂等键格式 | 唯一范围 | 重复行为 |
|---|---|---|---|
| 创建任务 | `task-create:{submitter_id}:{normalization_digest}` | 全局 | 返回首次 `task_id`，不新建。 |
| 创建修订 | `revision-create:{task_id}:{parent_revision_id_or_none}:{change_digest}` | task 内 | 返回首次 revision。 |
| 冻结修订 | `revision-freeze:{revision_id}:{content_digest}` | revision | 返回首次冻结结果。 |
| 审批 | `approval:{revision_id}:{approver_id}:{scope_snapshot_digest}` | revision+approver | 返回首次决定；并发只有一个生效。 |
| 派发作业 | `dispatch:{run_id}:{attempt}:{job_kind}` | run+attempt+kind | 同一 `job_id`；重复送达不重播。 |
| 停止请求 | `stop:{run_id}:{stop_request_id}` | run | 返回首次停止请求；断线保持待送达。 |
| 回执提交 | `receipt:{job_id}:{attempt}` | job+attempt | 返回首次回执；附加 sequence 更新同一回执链。 |
| 证据上传 | `evidence:{run_id}:{evidence_id}:{chunk_index}:{content_digest}` | run+evidence+chunk | 幂等去重；locator 可更新，ID/digest 不变。 |
| 领取租约 | `lease:{node_id}:{device_id}:{endpoint_set_digest}:{run_id}` | 占用键 | 冲突返回 `LEASE_CONFLICT`。 |
| 释放设备 | `release:{lease_id}:{epoch}` | lease+epoch | 返回首次释放；旧 epoch 拒绝。 |
| 断线补传 | `backfill:{node_id}:{message_id}` | node+message | 去重，不重复生成事件。 |
| 门禁推进 | `gate:{run_id}:{gate_code}:{from_status}:{to_status}` | run+gate+transition | 返回首次结果；版本冲突重读。 |

幂等键规则：

- 同一键 + 相同 payload → 返回首次结果（HTTP 语义可为 200/201，由 API 层定）。
- 同一键 + 不同 payload → `IDEMPOTENCY_KEY_REUSED`，拒绝且不产生副作用。
- 幂等键必须在权威写入的同一事务内持久化；不得只存内存。

## 17. 并发与 PostgreSQL 规则

1. **唯一权威**：PostgreSQL 是控制面唯一正式数据库；证据文件在内容寻址存储，数据库保存索引与摘要。禁止 SQLite 参与正式状态。
2. **租约原子领取**：对占用键 `(node_id, device_id, endpoint_set)` 使用唯一约束/部分唯一索引；冲突即失败。队列式领取查询可使用 `SELECT ... FOR UPDATE SKIP LOCKED`，但**仅限领取查询**，不用于一般读取。
3. **修订冻结**：`UPDATE ... WHERE revision_id = ? AND status = 'DRAFT' AND version = ?` 比较并交换；失败返回首次冻结结果。
4. **审批并发**：每个 `revision_id` 只允许一个有效 `APPROVED`（部分唯一索引/事务判定）；并发批准一个成功，其余读取首次结果。
5. **作业派发**：唯一 `(run_id, attempt, job_kind)`；重复派发返回同一 `job_id`。
6. **回执与序号**：唯一 `(job_id, attempt)`；`sequence` 单调递增；缺口进入 `RECEIPT_SEQUENCE_GAP`，先补传/对账，不猜测缺失。
7. **证据**：唯一 `evidence_id`；内容摘要不可变；重复上传按 `(evidence_id, chunk_index, content_digest)` 去重；归档只更新 locator。
8. **事件排序**：按 `(node_id, sequence)` 或 `(run_id, sequence)` 排序；去重键 `(node_id, message_id)`；旧 epoch 不参与当前状态变更。
9. **门禁并发**：`gate.version` 乐观锁；非法跳序/倒退拒绝。
10. **隔离级别**：默认 `READ COMMITTED` + 行锁/唯一约束；跨对象一致性（revision + approval + gate）在单事务内完成。需要快照读时使用 `REPEATABLE READ`，但不得以此替代唯一约束。
11. **时钟**：数据库 `timestamptz` 存储 UTC；应用不得写入本地时区；节点时钟偏差超限触发 `CLOCK_SKEW_EXCEEDED`。
12. **不可变审计**：事件/审计表只允许 INSERT；纠错写新事件并引用被纠正事件。

## 18. 错误码注册表

错误码用于操作/校验结果，**不替代五轴判定**。未登记错误码按 fail-closed 处理。

| 错误码 | 类别 | 触发条件 | 可重试 | 默认影响 |
|---|---|---|---|---|
| `TASK_NOT_FOUND` | 资源 | task 不存在或无权访问 | 否 | 拒绝 |
| `TASK_ID_CONFLICT` | 身份 | 归一化冲突或幂等载荷不一致 | 否 | 拒绝 |
| `REVISION_NOT_FOUND` | 资源 | revision 不存在 | 否 | 拒绝 |
| `REVISION_IMMUTABLE` | 状态 | 试图修改冻结 revision | 否 | 拒绝 |
| `REVISION_NOT_FROZEN` | 门禁 | 审批/执行前 revision 未冻结 | 否 | 拒绝 |
| `REVISION_NOT_APPROVED` | 门禁 | 无有效批准 | 否 | `BLOCKED` |
| `REVISION_SUPERSEDED` | 状态 | 使用已被取代的 revision | 否 | 拒绝 |
| `APPROVAL_REQUIRED` | 门禁 | 缺审批 | 否 | `BLOCKED` |
| `APPROVAL_SCOPE_MISMATCH` | 审批 | 批准范围/摘要与 revision 不符 | 否 | 拒绝 |
| `APPROVAL_SELF_REVIEW_FORBIDDEN` | 审批 | `prevent_self_review=true` 且自审 | 否 | 拒绝 |
| `APPROVAL_NOT_EFFECTIVE` | 审批 | 等待期未过或状态非 APPROVED | 是（等待后） | `BLOCKED` |
| `APPROVAL_CONFLICT` | 并发 | 并发批准已被其他记录生效 | 是（读首次结果） | 返回首次 |
| `GATE_OUT_OF_ORDER` | 门禁 | 跳过前置门禁 | 否 | 拒绝 |
| `GATE_PREREQUISITE_FAILED` | 门禁 | 前置门禁未 PASSED | 否 | `BLOCKED` |
| `GATE_VERSION_CONFLICT` | 并发 | 乐观锁版本冲突 | 是 | 重读 |
| `CASE_VERSION_NOT_FROZEN` | 用例 | 用例版本未随 revision 冻结 | 否 | 拒绝 |
| `CASE_CONTENT_MISMATCH` | 用例 | `case_version` 与摘要不符 | 否 | 拒绝 |
| `BUNDLE_NOT_FROZEN` | 执行包 | bundle 非 `FROZEN` | 否 | 拒绝 |
| `BUNDLE_DIGEST_MISMATCH` | 完整性 | bundle/工件摘要不符 | 否 | 阻断执行 |
| `BUNDLE_ARTIFACT_MISSING` | 完整性 | 必需工件缺失 | 否 | 阻断执行 |
| `BUNDLE_VERSION_INCOMPATIBLE` | 兼容 | Python/lstest/适配器/OS 不匹配 | 否 | 阻断执行 |
| `BUNDLE_PATH_UNSAFE` | 完整性 | 绝对路径/`..`/UNC/链接逃逸 | 否 | 拒绝 |
| `LEASE_CONFLICT` | 并发 | 占用键已被其他 lease 持有 | 是（稍后） | 拒绝 |
| `LEASE_EPOCH_STALE` | 并发 | 旧 epoch 试图写当前状态 | 否 | 仅存历史 |
| `LEASE_RECLAIM_PENDING` | 状态 | 通信失联，占用待对账 | 是（重连） | 保持占用，不重派 |
| `LEASE_RELEASE_PRECONDITION_FAILED` | 释放 | 本地停止/清理/对账未完成 | 是（完成后） | 保持占用 |
| `DEVICE_OCCUPIED` | 资源 | 设备被其他任务占用 | 是（稍后） | 拒绝候选 |
| `DEVICE_QUARANTINED` | 资源 | 设备隔离中 | 否（需授权） | 拒绝候选 |
| `DEVICE_DRAINING` | 资源 | 设备停止接新单 | 是（恢复后） | 拒绝候选 |
| `DEVICE_ENDPOINT_MISSING` | 资源 | 必需端点缺失 | 否 | `BLOCKED` |
| `DEVICE_EQUIVALENCE_UNAPPROVED` | 资源 | 未批准的跨设备替代 | 否 | 拒绝 |
| `DEVICE_FIRMWARE_MISMATCH` | 资源 | 固件/配置不匹配 | 否 | `BLOCKED` |
| `NO_INTERACTIVE_SESSION` | 环境 | 无交互式会话 | 是（会话恢复） | `BLOCKED` |
| `COMMUNICATION_OFFLINE` | 通信 | 节点不可达 | 是 | 仅标记；不停止已启动 run |
| `HEARTBEAT_STALE` | 通信 | 心跳超阈值 | 是 | 仅可观测性；不改占用/判定 |
| `STOP_PENDING` | 停止 | 存在待送达停止指令 | 是（重连） | 不启动新动作 |
| `RUN_NOT_STARTED` | 状态 | 停止一个未启动 run | 否 | 拒绝/幂等 |
| `RUN_ALREADY_CLOSED` | 状态 | run 已终态 | 否 | 拒绝 |
| `RECEIPT_DUPLICATE` | 幂等 | 重复 `job_id+attempt` | 是（读首次） | 返回首次 |
| `RECEIPT_UNKNOWN_JOB` | 回执 | 回执无对应作业 | 否 | 拒绝 |
| `RECEIPT_SEQUENCE_GAP` | 回执 | 序号缺口 | 是（补传） | 待对账 |
| `RECEIPT_SIGNATURE_INVALID` | 安全 | 签名校验失败 | 否 | 拒绝 |
| `RECEIPT_FORBIDDEN_VERDICT_FIELD` | 安全 | 回执包含判定字段 | 否 | 拒绝 |
| `NONCE_REPLAYED` | 安全 | nonce 重放 | 否 | 拒绝 |
| `NODE_CERT_REVOKED` | 安全 | 节点证书撤销 | 否 | 拒绝连接 |
| `CLOCK_SKEW_EXCEEDED` | 安全 | 时钟偏差超限 | 是（校时后） | 拒绝/待核验 |
| `EVIDENCE_DIGEST_MISMATCH` | 证据 | 摘要重算不符 | 否 | `INVALID_EVIDENCE` |
| `EVIDENCE_MISSING_REQUIRED` | 证据 | 必需证据缺失 | 是（补传） | `INCOMPLETE`，不得 PASS |
| `EVIDENCE_PATH_UNSAFE` | 证据 | 路径越界 | 否 | 拒绝 |
| `EVIDENCE_CONFLICTED` | 证据 | 同 ID 摘要冲突 | 否 | 待复核 |
| `CLEANUP_RECEIPT_MISSING` | 释放 | 缺 cleanup 回执 | 是（补传） | 保持占用；不判证据不完整 |
| `OCCUPANCY_UNRECONCILED` | 释放 | 占用未对账 | 是（对账） | 保持占用 |
| `SPOOL_WARN_THRESHOLD` | 存储 | spool 达预警 | 是 | 禁止新 case |
| `SPOOL_PROTECT_THRESHOLD` | 存储 | spool 达保护阈值 | 否 | 本地安全停止 |
| `PROFILE_CONTRACT_INVALID` | 静态 | lstest preflight/profile 契约失败 | 否 | `BLOCKED_PROFILE_CONTRACT` |
| `IDEMPOTENCY_KEY_REUSED` | 幂等 | 同键不同载荷 | 否 | 拒绝 |
| `SCHEMA_VERSION_UNSUPPORTED` | 契约 | 未知 `schema_version` 或未知 bundle 格式标识 | 否 | fail-closed |
| `INTERNAL_ERROR` | 内部 | 未分类内部错误 | 是 | 记录，不伪造 PASS |

> **R-01/E-05 补充（2026-10-29）**：`SCHEMA_VERSION_UNSUPPORTED` 同时覆盖“载荷 `schema_version` 不在支持集合”与“bundle 格式标识不在支持集合”。节点侧 `security/receipt.schema.json` 的 `error.code` 是独立闭集（`additionalProperties: false`、无 `subject`），控制面错误码不得直接搬进节点回执。节点回执统一使用已登记的 `SCHEMA_INVALID`，并在 `facts` 中固定写 `bundle_format_supported`、`bundle_payload_schema_supported` 两个 boolean；两套错误词表的完整映射为后续登记项。


## 19. 已批准规则映射

| 已批准规则 | 契约落点 | 守卫/证据 |
|---|---|---|
| 一个 `task_id` | Task `task_id` 必填且终身不变；无 `successor_task_id`；`revision.parent_revision_id` 仅表修订谱系 | T-1、R-4、AC-6 |
| 一个 lead agent | Task `lead_agent_id` 单个 uuid，必填；`lead_session_id` 不替代执行授权 | T-2、A-6 |
| 不可变 revision | Revision `content_digest` + `immutable` + `frozen_at`；冻结后内容禁止修改 | R-1、R-2 |
| 一份审批绑定冻结 revision | Approval `revision_content_digest` + `scope_snapshot`；每 revision 至多一个有效 `APPROVED` | A-1、A-2、G-2 |
| 门禁顺序 | Gate `gate_code` G0–G7 + `order_index`；严格顺序与 G4/G5 分离 | G-1..G-4 |
| 五轴判定 | Run/Attempt 五个独立字段；正式 PASS 五条件全满足 | 第 9、14 节 |
| 离线续跑 | `communication_state`、`occupancy_state`、`execution_permit` 三分离；`expires_at` 非所有权到期 | L-2、L-3、I-08、第 15 节 |
| STOP-first 重连 | 重连顺序固定；`STOP_PENDING`；旧 epoch 仅历史 | I-09、P-3、第 15.3 节 |
| 设备释放独立于证据/判定 | Lease `release_preconditions` 三项；`cleanup_receipt` 与 `evidence_status`/`verification_status` 分离 | L-5、L-6、P-4、I-10、I-11 |
| 正式分母不含烟测/模拟 | Run `mode`、Attempt `evidence_origin`、`denominator_eligible` 派生规则 | I-07、14 节 |
| Linux 独占最终判定 | Receipt 禁止判定字段；`business_verdict`/`verification_status` 仅 Linux 写 | P-5、9.1、12.1 |

## 20. 受委托做出的决定

以下决定是在任务授权范围内做出的；若与已批准来源冲突，以已批准来源为准，并在 Orchestrator 评审时覆盖。

| ID | 决定 | 理由 | 任务级覆盖点 |
|---|---|---|---|
| D-C-01 | 把单一生命周期拆为 `Task.status`、`Revision.status`、`Run.lifecycle_status` 三层 | 已批准文档把任务、修订、运行混在同一串状态里，字段化后必须分离，否则多修订/多 run 会互相污染 | 可保留展示层合并串，但权威字段仍分离 |
| D-C-02 | `lease.expires_at` 只表示续约截止，不产生 `lease_expired` 状态或错误 | 直接执行已批准的离线续跑规则；旧文档的“到期即 `lease_expired`”与已批准规则冲突 | `P0-08` 定续约/心跳数值；语义不可回退 |
| D-C-03 | Receipt 明确禁止 `business_verdict`/`verification_status`/`final_verdict` | 执行“节点只回传事实、Linux 独占判定” | 如节点需自检，只能写 `execution_status` 与 facts |
| D-C-04 | 缺 `cleanup_receipt` 只影响占用对账，不影响 `evidence_status` | 执行 S5-3 对旧“缺 cleanup 等同证据不完整”的修正 | 无 |
| D-C-05 | 不设 `successor_task_id`；只允许 `parent_revision_id`/`superseded_by_revision_id` | 执行“同一 task 派生新修订、不创建 successor” | 无 |
| D-C-06 | 默认允许自审；`prevent_self_review` 为可选开关 | 执行需求基线 2.2 与已确认决定 B | 未来权限策略可开启；不影响字段 |
| D-C-07 | 模拟不是 run mode；`evidence_origin` 区分 `simulated`/`replay` | 防止“模拟正式 run”绕过分母规则 | 如需模拟 UI，新增只读标记，不新增 run mode |
| D-C-08 | 顶层 `gate_code` 只保留 G0–G7；G2.0–G2.2 作为 G2 子检查 | 避免与已批准门禁序列冲突，同时保留插件检查 | 可在 `G2.blockers` 记录子检查 |
| D-C-09 | `task_category` v1 仅 `voice_interaction` | 防止把未运营类别写成已支持 | 新类别需新版本契约 |
| D-C-10 | 所有摘要 v1 仅 `sha256:` 前缀 | 与架构/证据规则一致，便于独立重算 | 新算法必须带前缀并提升契约 |
| D-C-11 | `denominator_eligible`/`formal_denominator_eligible` 为服务端派生字段 | 防止客户端自报进入正式分母 | API 可只读暴露；不得接受客户端赋值 |
| D-C-12 | `lead_agent_id`、`project_id` 使用 UUID | 统一标识规则；便于跨服务引用 | 若 agent 注册表使用字符串 ID，增加映射字段而非改类型 |
| D-C-13 | Task 状态不含 `FROZEN`；冻结属于 Revision | 一个 task 可同时有已批准旧修订与新草稿修订 | 展示层可显示“当前修订已冻结” |
| D-C-14 | `INFRA_ERROR` 仅在对账确认后使用 | 防止心跳超时被误判为基础设施故障 | 通信异常用 `COMMUNICATION_OFFLINE`/`HEARTBEAT_STALE` |
| D-C-15 | 错误码注册表可追加，未知码 fail-closed | 兼容演进且不静默放行 | 新错误码需在本文登记 |
| D-C-16 | Bundle 格式标识与载荷 `schema_version` 是两个独立版本轴，禁止相等比较 | 消除 R-01 的语义分裂，节点分别校验两个支持集合 | 格式标识升 v2 时复制旧 schema，不原地覆盖 |
| D-C-17 | 运行 mode 全层统一为 `static`/`smoke`/`formal`；`static_check` 只作 action/job_kind | 消除 C-01 词汇冲突；读侧别名仅为兼容 | 证据 schema 枚举已同步；旧值仅只读归一 |
| D-C-18 | 失败分类以 domain 8 个大写值为权威，证据侧小写为投影；`none` 用省略表达，`needs-review` 用五轴表达 | 避免两套分类学；保持分母规则不变 | 映射表双向；表外值 fail-closed |
| D-C-19 | 线协议 `lease.state` 按固定 6 值表映射到领域状态，`expired` 永不释放 | 执行 B4/B5；到期不等于所有权到期 | 行为验证属 L3/L4 真机，见交接 |
| D-C-20 | 拆分 `endpoint_kind` 与 `endpoint_set`；音频旧词仅作入站别名 | 消除 C-04 的“类别 vs 身份”混用 | `network`/`display`/`gpio` 可占用性待 T-10 |
| D-C-21 | 设备占用只保留 L1 权威 / L2 三值投影 / L3 历史展示三层；`QUARANTINED` 必须 `OCCUPIED` | 关闭 SR-14 的枚举分歧并守住 B6 | `docs/v2`/`openspec` 回写为后续同步 |
| D-C-22 | `case_version` 全层为 `integer ≥ 1`；字符串仅显式兼容读入 | 保证连接键与追溯一致 | 兼容读需开关与 `legacy_case_version_coerced` 审计 |

## 21. 未决问题与交接

| ID | 问题 | 归属 |
|---|---|---|
| Q-01 | 节点证书算法、证书链、轮换/撤销、签名载荷规范化 | P0-05 |
| Q-02 | nonce/sequence/epoch 窗口、时钟偏差阈值 | P0-05 |
| Q-03 | 心跳、续约、审批提醒、spool/磁盘阈值、预算与样本量 | P0-08 |
| Q-04 | evidence manifest 完整 schema、必要证据集、摘要算法扩展 | P0-06 |
| Q-05 | `evidence_id` 分配权威（节点生成 vs Linux 生成）与分片上传协议 | P0-06 |
| Q-06 | 任务卡投影字段、刷新/stale 阈值、进度公式 | P0-07 |
| Q-07 | 报告模板、知识候选条目、审计查询契约 | P0-07 |
| Q-08 | 设备等价字段与跨型号替代批准流程 | P0-10 / 任务级 |
| Q-09 | `G2.0–G2.2` 子检查是否需要独立表 | P0-05/P0-06 |
| Q-10 | 审批等待期默认值与升级链路 | P0-08 |

## 22. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0-candidate.1 | 2026-10-28 | 首次形成 12 个核心实体的字段级候选契约；固定 ID/时间/摘要约定；显式解决 SQLite、`lease_expired`、`INFRA_ERROR`、`cleanup_receipt`、`successor`、`approver != submitter` 冲突。 |
| 1.1-candidate.1 | 2026-10-29 | 所有者授权裁决 R-01..R-03、C-01..C-06（见 `docs/delivery/contract-adjudication-record.md`）：新增 bundle 双版本轴、失败分类双向映射、`lease.state` 接收映射、端点 kind/身份拆分、占用三层投影、`case_version` 整数统一；证据侧 mode 收敛为 static/smoke/formal。仍为候选，未冻结、未批准，Phase 0 未关闭。 |
