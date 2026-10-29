# 契约决策独立核验：R-01 / R-02 / R-03 / C-02 / C-03

> 日期：2026-10-29 · 范围：`docs/contracts/` 只读核验。未修改契约、schema、计划、UI 或产品代码；**不声称冻结、批准、验收或生产就绪**（Phase 0 未关闭）。
> 观察到的版本标签：`frozen-candidate v1.1`，候选包 `1.1-candidate`，载荷 `schema_version` 仍为 `"1.0"`（`docs/contracts/README.md:3-4`、`README.md:53-55`、`README.md:111-113`）。
> 裁决基线：`docs/delivery/contract-adjudication-record.md:58-63`（总表）、`72-100`（R-01）、`101-125`（R-02）、`127-182`（R-03）、`184-211`（C-02）、`213-244`（C-03）。

## 0. 结论总表

| 决策 | 结论 | 一句话依据 |
|---|---|---|
| R-01 bundle 格式轴 vs 载荷 schema 版本 | **PASS** | 两个独立字段、两套支持集合、显式禁止相等比较/互相推导；错误码与 `facts` 双键齐备。 |
| R-02 cleanup 投影为超集 | **NEEDS-FIX** | 超集结构与“无省略字段”成立；但节点侧必填 `occupancy_reconciled` 与“节点不能自证、控制面独占”冲突。 |
| R-03 证据轴映射与展示型 `UNKNOWN` | **PASS** | 五张表齐全、映射由投影服务（服务端）生成；权威枚举无 `UNKNOWN`，仅 `validity_status` 例外。 |
| C-02 失败词表双向映射 | **PASS** | 8↔8 全量双向，另加 `none`（省略）与 `needs-review`（五轴）两个显式非对称项；表外 fail-closed。 |
| C-03 线协议 `lease.state` 映射与释放守卫 | **NEEDS-FIX** | 释放三守卫与“永不 free”成立；但映射不是 1:1，且多数（当前状态 × 线协议值）格未定义。 |

## 1. 执行的机械核验

- `python3 -m json.tool` × 35 个 schema：**35/35 通过**（`docs/contracts/schemas/*/*.schema.json`）。
- `Draft202012Validator.check_schema` + `$schema` 断言：**35/35 通过，0 失败**。
- `git diff --check`：无输出；**但 `docs/contracts/` 与 `docs/delivery/` 均为未跟踪目录（`??`），该检查不覆盖本次契约文件**。
- 按裁决记录，`docs/contracts/mappings/failure-class.json` **按设计未创建**（`contract-adjudication-record.md:199`；实测目录不存在）。

## 2. R-01 — PASS

| 轴 | 字段位置 | 值 | 规则 |
|---|---|---|---|
| bundle 格式标识/引用命名空间 | `schemas/security/job.schema.json:196-198`（`payload.execution_bundle.schema_version`） | `noahsark.execution-bundle/v1` | 独立支持集合 `{noahsark.execution-bundle/v1}` |
| 载荷 schema 版本 | `schemas/domain/execution-bundle.schema.json:26` | `"1.0"` | 独立支持集合 `{"1.0"}`，未知 fail-closed |

- 双向禁止表述：`domain.md:461-464`（分别校验、禁止相等、禁止互相推导、任一不支持即拒绝）；`security-node.md:479`、`security-node.md:567`、`security-node.md:880`；`README.md:66`；两份 schema 的 `description` 各自声明“另一轴不是本字段”。
- 错误表达：控制面 `SCHEMA_VERSION_UNSUPPORTED`（`domain.md:887,890`）；节点 `SCHEMA_INVALID` + `facts.bundle_format_supported` / `facts.bundle_payload_schema_supported`（`security-node.md:949-954`、`security-node.md:569`）。未新增顶层错误码，未使用 `subject`/`message` 承载机器语义。
- 未发现任何 `format == schema_version` 的规范表述，也未发现用一轴推导另一轴。
- 观察（非缺陷）：线协议字段名仍叫 `schema_version` 却承载格式标识，属遗留命名碰撞；R-01 仅靠 `description` + 支持集合约束消歧，实际实现需严格按对象位置区分。

## 3. R-02 — NEEDS-FIX

字段级超集核对（`security/receipt.schema.json:336-371` vs `domain/receipt.schema.json:180-215`）：

| 字段 | security（传输侧） | domain（最小投影） | 结论 |
|---|---|---|---|
| `cleanup_receipt_id` / `cleanup_status` / `local_stop_confirmed` / `safe_cleanup_done` / `occupancy_reconciled` / `completed_at` | 必填（6/6） | 必填（6/6） | 逐字一致 |
| `notes` | 可选 string ≤2000 | 可选 string ≤2000 | 一致 |
| `operational_detail` | 可选，仅传输期 | **不存在**（`additionalProperties:false` 拒绝） | 超集成立 |
| 被省略的 domain 字段 | — | — | **无**（domain 6 必填 + `notes` 全部被 security 覆盖） |

- `cleanup_status` 词表四处一致（5 值）：`security/receipt.schema.json` `$defs.cleanupStatus`、`domain/receipt.schema.json` `$defs.cleanupStatus`、`evidence/cleanup-receipt.schema.json` `$defs.cleanupStatus`、`security-node.md:521`、`domain.md:645`。
- 文档与历史注记齐备：`README.md:61`、`security-node.md:521-525,878`、`domain.md:655-657`、`evidence-verdict.md:714-727`；“同一最小投影”仅出现在“已被取代/历史”语境，未作为规范。
- **矛盾（需修）**：`security/receipt.schema.json` 是节点→控制面消息（`sender_role: node`），其 `cleanup_receipt.required` 含 `occupancy_reconciled`（`:337-343`），字段 `description` 自称“Control-plane reconciliation of device occupancy”（`:354-357`）；而 `evidence-verdict.md:723` 明确 `occupancy_reconciled` 来自控制面 `device-occupancy.reconciliation.result=passed`，并写“**节点不能自证**”。R-02 要求两侧必填字段“逐字一致”（`security-node.md:521`），等于强制节点断言一个控制面独占事实。
- 影响：不破坏“security ⊇ domain”的结构判定，但破坏写入方边界（B1/B2）；实现时要么节点伪造该布尔，要么该必填在节点侧恒为 `false`，两种都会退回“证据/占用对账”语义。修复需二选一：从节点回执移除该必填并由控制面派生，或重新定义该字段为节点本地事实并放弃“逐字一致”要求。

## 4. R-03 — PASS

五张投影表实际存在（`ui-report-knowledge-audit.md`）：设备占用 `:200`、通信 `:209`、门禁 `:220`、运行 `:231`、证据轴 `:247`；`report_scope` 覆盖范围表另列 `:257`。README 的“五表”声明（`README.md:64`）与实际表数一致，并有 2026-10-28 历史注记。

| 权威轴 | 权威枚举（schema） | 展示 `UNKNOWN` | 权威回写值 |
|---|---|---|---|
| `execution_status` | `run.schema.json:44` / `attempt.schema.json:44`：5 值，无 `UNKNOWN` | 允许（展示） | `NOT_STARTED` |
| `evidence_status` | 4 值，无 `UNKNOWN` | 允许（展示） | `INCOMPLETE` |
| `verification_status` | `PASS/FAIL/NOT_RUN`，无 `UNKNOWN` | 允许（展示） | `NOT_RUN` |
| `validity_status` | 含 `UNKNOWN` | 权威成员，例外 | 可写回 |

- 服务端派生：`ui-report-knowledge-audit.md:198`（“投影服务必须按下列映射从权威字段生成；UI 不得自行推断”）、`:33`（字段裁剪必须在服务端完成）、`:46`、`:192`（客户端不得乐观写入）。证据表 `:249-255` 逐值给出权威来源。
- 展示占位规则：`:108`（不得写回 `Run`/`Attempt`/`verdict.axes`）、`:255`（`UNKNOWN` 必须携带 `freshness` 与最后权威更新时间）；`report.schema.json:274` 对 `verdict_summary.axes` 重复同一约束；`verdict.decision` 枚举无 `UNKNOWN`（`verdict.schema.json` `$defs.decision`），`verdict.axes` 中三轴亦无 `UNKNOWN`（仅 `validity_status` 有）。
- 观察（非缺陷）：`report.schema.json:284,296,300` 的 `verdict_summary.axes` 允许持久化 `UNKNOWN`。它是派生报告投影而非权威状态，但“持久化投影中出现 `UNKNOWN`”仍需 P1-08 明确其生命周期；`report_scope.mode` 的 `BLOCKED`/`STOPPED` 仅为过渡兼容值，`contains_blocked`/`contains_stopped` 为可选新增（`:83-91`）。

## 5. C-02 — PASS

| domain `failure_classification`（权威 8 值） | 证据 `failure_class`（投影） | 计入正式分母 |
|---|---|---|
| `INVALID_INPUT` | `invalid-input` | 否 |
| `INVALID_ENVIRONMENT` | `invalid-environment` | 否 |
| `INVALID_EVIDENCE` | `invalid-evidence` | 否 |
| `VALID_FAILURE` | `valid-failure` | **是（唯一）** |
| `BLOCKED` | `blocked` | 否 |
| `STOPPED` | `stopped` | 否 |
| `UNSUPPORTED` | `unsupported` | 否 |
| `INFRA_ERROR` | `infra-error` | 否 |
| （省略字段，无 `NONE`） | `none` | 否 |
| （无对应枚举值） | `needs-review` | 待复核，不计入 |

- 双向表两处一致：`domain.md:385-407` 与 `evidence-verdict.md:1070-1093`；成员集大小写归一后完全相同（8↔8）。
- schema 落地：`run.schema.json:104` 与 `attempt.schema.json:112` 均为 8 个大写值；`verdict.schema.json` `$defs.failureClass` 为 10 个小写值（8 + `none` + `needs-review`）；`evidence-manifest.schema.json:595-600` 定义 `null ≡ 省略 ≡ none`。
- 无静默默认：表外值 fail-closed 为 `NEEDS_REVIEW`（`domain.md:406`、`evidence-verdict.md:1091`），且明确禁止猜测为 `valid-failure`/`none`。
- 口径澄清：本决策的两侧是“domain 持久化权威词表”与“证据/判定序列化投影”，**不是**“node-observed ↔ platform”。`security/receipt.schema.json` 不含 `failure_class`/`failure_classification`（检索 0 命中），节点回执只回传 `node_observed_*` 五轴事实。若验收语句确实要求“node-observed 词表”，则该词表不存在，需改口径而非改契约。

## 6. C-03 — NEEDS-FIX

| 线协议 `lease.state` | 领域 `Lease.state` 目标 | 占用 | 守卫 |
|---|---|---|---|
| `granted` | `GRANTED` | `OCCUPIED` | 领取确认后才 `HELD` |
| `renewed` | `HELD` | `OCCUPIED` | 当前为 `RECLAIM_PENDING` 时保持不回退 |
| `released` | `RELEASING` → `RELEASED` | `OCCUPIED` → `IDLE` | 三项 `release_preconditions` 全 `true` |
| `expired` | 不改变（`GRANTED`→`GRANTED`；`HELD`+ONLINE→`HELD`；`HELD`+STALE/OFFLINE→`RECLAIM_PENDING`） | `OCCUPIED` | 永不 `RELEASED`/`IDLE`、不判失败、不重派 |
| `revoked` | `RELEASING`（清理失败/安全事件可 `QUARANTINED`） | `OCCUPIED` | STOP-first |
| `reclaimed` | `RECLAIM_PENDING`（最终只能 `HELD` 或 `RELEASING`） | `OCCUPIED` | 不得直跳 `RELEASED` |
| 表外值 | 不改变 | 保持原值 | 审计告警；禁止新派发 |

来源：`domain.md:527-538`、`security-node.md:921-932`、`security/lease.schema.json:136-138`、`evidence-verdict.md:808`。

领域 6 状态的反向可达性：

| `Lease.state` | 线协议来源 |
|---|---|
| `GRANTED` | `granted`（`expired` 保持） |
| `HELD` | `renewed`（守卫后）、`reclaimed`/`expired` 后对账恢复 |
| `RELEASING` | `released`（守卫前）、`revoked` |
| `RECLAIM_PENDING` | `reclaimed`、`expired` + 通信离线 |
| `RELEASED` | 仅 `released` + 三守卫 |
| `QUARANTINED` | **无线协议来源**，仅控制面审计写入（`domain.md:538`、`security-node.md:929`） |

- **1:1 不成立（主要缺陷）**：6 个线协议值并不一一对应 6 个领域状态——`released` 有两段目标、`expired` 为条件恒等/条件迁移、`QUARANTINED` 无入站来源。裁决记录与 `T-C03-1`（`contract-adjudication-record.md:238`）本身也按“`expired` 断言状态保持”设计，说明 1:1 只是验收措辞与设计不一致；契约正文未声称 1:1，故非内部矛盾，但验收项按字面未达成。
- **迁移矩阵不完整**：表只覆盖少量当前状态（如 `HELD` 下的 `expired`），未定义 `(RELEASING, granted)`、`(GRANTED, renewed)`、`(RELEASED, renewed)`、`(RELEASING, expired)`、`(QUARANTINED, released)` 等格。实现无法据此构造全函数，只能依赖“表外值不改状态”，但表内值出现在未列状态时行为未定义。
- 守卫通过：`domain/lease.schema.json:120-137` 强制 `state=RELEASED` ⇒ 三项 `true` + `occupancy_state=IDLE` + `released_at`；`RELEASING` ⇒ `occupancy_state=RELEASING`；`GRANTED/HELD/RECLAIM_PENDING/QUARANTINED` ⇒ `OCCUPIED`（`:106-160`）。
- “工作仍可能运行时不得 free”通过：`expired`/`renewed`/`revoked`/`reclaimed` 全程 `OCCUPIED`；`released` 先落 `RELEASING`，仅三守卫全真才 `IDLE`；`thresholds.md:128,406` 再次禁止“到期即释放/失败”。

## 7. 未能核验 / 未覆盖

- 裁决要求的 `T-R01-1..4`、`T-R02-1..4`、`T-R03-1..5`、`T-C02-1..5`、`T-C03-1..5` 均**无实现或测试产物可执行**；本次只核验契约文本、schema 结构与文档一致性。
- 仓库无产品代码（无 `src/`/`services/` 等），故“投影服务在服务端派生”“节点校验器不含相等比较”无法做运行时验证，只能确认契约有此要求。
- `T-C03-5`（`revoked`/`reclaimed` 真机 STOP-first 时序）属 L3/L4，未执行；`U-11` 仍开放（`contract-adjudication-record.md:356`）。
- P1-08 UI 词汇与 `report_scope` 结构删除/重命名未冻结（`contract-adjudication-record.md:357`），R-03 仅候选语义。
- 因 `docs/contracts/` 未被 git 跟踪，无法与历史基线做 diff 级“已应用变更”核对；本报告基于当前工作树文本。
- 未核验 `docs/contracts/mappings/failure-class.json` 的实际机器映射表（设计上本版本不创建），C-02 的“同一张机器可读表”仍是待实现约束。
