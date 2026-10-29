# 契约裁决记录：R-01..R-03 与 C-01..C-06（Contract Adjudication Record）

> 版本：v1.0（2026-10-29）
> 状态：**owner-authorized candidate adjudication**。本文件记录所有者授权的技术裁决，形成 `docs/contracts/` 的 `frozen-candidate v1.1` 候选基线。
> **不是契约冻结，不是批准，不是验收，不构成实现/测试/部署/发布授权。**
> **not production-frozen; Phase 0 not closed.**
> 输入：`docs/delivery/contract-resolution-proposal.md`、`docs/delivery/contract-residual-followup.md`、`docs/contracts/`（原 `frozen-candidate v1`）。
> 输出边界：仅修改 `docs/contracts/**` 与本文件；未修改 `.omo` 计划、根 `plan.md`、`docs/v2`、`openspec`、UI 源文件、环境文档、产品代码、迁移、OpenAPI，未提交、未推送。

---

## 1. 授权、方法与非声明

### 1.1 授权

所有者明确授权助手就以下 9 项技术契约作出裁决，并把结果作为 Phase 2 及后续实现的**候选基线**。该授权不等于冻结或批准；候选基线在冻结前必须经过独立核验（字段、映射、schema、失败关闭行为），冻结决定与 Phase 0 关闭仍由 Orchestrator/所有者作出。

### 1.2 方法

1. 对 9 项**全部采用提案 §3 的推荐选项**；未采用任何被提案拒绝的备选。
2. 权威边界（§2）保持不变；所有改动只落在字段语义、映射表、`description` 与两处“首次冻结前”收紧。
3. 所有枚举/ID 映射均写成**双向表**，并明确“未知值不升权 / fail-closed”。
4. 被取代的旧表述以**带日期的历史注记**保留，不静默删除。
5. 不新增 schema 文件，不删除 schema；全包仍为 35 个 schema。

### 1.3 版本路径裁决（对应提案 U-04 / U-09、§8）

| 项 | 裁决 | 理由 |
|---|---|---|
| 目录/候选包版本 | `1.1-candidate` | 9 项裁决合为一个候选修订，可独立复核。 |
| 载荷 `schema_version` | 保持 `"1.0"` | 当前**无已冻结修订、无已接收证据**；C-01/C-05/C-06 的类型/枚举/收紧变更按“首次冻结前 v1 修正”处理。 |
| 未来同类变更 | 冻结后必须按 `README.md` §3.4 升 `2.0` | 一旦存在冻结修订或已接收证据，历史回放与 `1.x` 解析器保留成为硬约束。 |
| 被拒备选 | 立即升 `2.0` | 会在没有任何历史对象需要保护时人为分叉版本，并让 9 项候选无法作为一个可复核基线落地。 |

**限制**：该“首次冻结前 v1 修正”认定是本记录的核心裁决之一；若独立核验认为不成立，C-01/C-05/C-06（以及 C-04 的结构部分）必须改走 `2.0`。

---

## 2. 保持不变的所有者边界

| # | 边界 | 本裁决的落实 |
|---|---|---|
| B1 | Linux 控制面独占生成、冻结、审核、修复、版本化与**最终判定** | 所有映射只由 Linux 写入；节点只回传事实。R-01/C-02/C-06 未改变写入方。 |
| B2 | Windows Node Agent 只执行冻结 Bundle 并回传事实；`used_for_decision=false` | R-01 的版本校验属节点“拒绝”动作，不产生判定；E-05 明确节点错误码闭集。 |
| B3 | **PostgreSQL 是唯一正式数据库**；SQLite 仅历史/只读 | 未引入第二事实源、本地库或迁移。 |
| B4 | 离线续跑：已启动冻结压测断线继续；设备保持 `OCCUPIED`；不重派/重播/重复采样 | C-03 的 `expired` 映射明确“不降级、不升级、永不释放”。 |
| B5 | STOP-first 重连：待 STOP → 停止后续动作 → 补传 → 去重 → 对账 → 恢复领取 | C-03 的 `revoked`/`reclaimed` 不得绕过 STOP-first 直释放。 |
| B6 | 设备释放 / 证据完整性 / 最终判定三平面分离；缺 `cleanup_receipt` ≠ 证据不完整 | R-02/C-03/C-05 只改投影与状态映射，未合并三平面。 |
| B7 | 五轴独立；正式 PASS 五条件同时成立；烟测/模拟/回放永不进入正式分母 | R-03/C-02/C-06 未改派生顺序与分母规则。 |
| B8 | 未知枚举 fail-closed；未知值不得当 PASS | 所有新映射表均补“未知值不升权”规则。 |

---

## 3. 裁决总表

| ID | 裁决（采用提案推荐选项） | 兼容分类 | 主要 changed files | 必需测试 |
|---|---|---|---|---|
| R-01 | 区分 bundle 格式标识 `noahsark.execution-bundle/v1` 与载荷 `schema_version: "1.0"`；禁止相等比较；分别校验；节点用 `SCHEMA_INVALID` + `facts` 两键 | 文档 + `description`，`1.x` | `docs/contracts/README.md`、`security-node.md`、`domain.md`、`schemas/security/job.schema.json`、`schemas/domain/execution-bundle.schema.json` | T-R01-1..4 |
| R-02 | security `cleanup_receipt` 是 domain 最小投影的**超集**；domain 拒绝 `operational_detail`；补 `cleanup_status`/`notes` 映射 | 文档 + `description`，`1.x` | `README.md`、`security-node.md`、`evidence-verdict.md`、`domain.md`、`schemas/{security,domain}/receipt.schema.json` | T-R02-1..4 |
| R-03 | 补 evidence 第五张投影表；`UNKNOWN` 仅展示占位；`report_scope.mode` 改为覆盖范围语义，新增可选 `contains_blocked`/`contains_stopped` | 文档 + `description` + 可选字段，`1.x`；结构删除待 P1-08 | `ui-report-knowledge-audit.md`、`README.md`、`schemas/experience/report.schema.json` | T-R03-1..5 |
| C-01 | mode 全层只有 `static`/`smoke`/`formal`；`static_check` 仅 action/job_kind；读侧只读别名 | 枚举成员变更；按**首次冻结前 v1 修正**；冻结后为 `2.0` | 3 个 evidence schema、`evidence-verdict.md`、`domain.md`、`README.md` | T-C01-1..4 |
| C-02 | domain 8 大写值为权威；证据小写为投影；`none` 用省略；`needs-review` 用五轴；未知 fail-closed | 文档 + `description`，`1.x` | `domain.md`、`evidence-verdict.md`、`schemas/domain/{run,attempt}.schema.json`、`schemas/evidence/{evidence-manifest,verdict}.schema.json`、`README.md` | T-C02-1..5 |
| C-03 | 线协议 6 值 `lease.state` → 领域 `Lease.state`/`occupancy_state` 固定映射 + 守卫 + 表外不升权 | 文档 + `description`，`1.x`；行为验证 L3/L4 | `security-node.md`、`domain.md`、`evidence-verdict.md`、`schemas/security/lease.schema.json`、`README.md` | T-C03-1..5 |
| C-04 | 拆分 `endpoint_kind`（能力类）与 `endpoint_set`（身份集合）；音频别名双向归一；身份参与占用键 | 别名/文档 `1.x`；结构拆分延后 `2.0` | `security-node.md`、`domain.md`、`evidence-verdict.md`、4 个 security schema、3 个 domain schema、`schemas/evidence/device-occupancy.schema.json`、`README.md` | T-C04-1..5 |
| C-05 | 占用三层；四值历史词投影；`QUARANTINED → OCCUPIED` 不变量 | 文档 `1.x` + schema 收紧；按**首次冻结前 v1 修正** | `domain.md`、`evidence-verdict.md`、`schemas/domain/lease.schema.json`、`README.md` | T-C05-1..4 |
| C-06 | `case_version` 全层 `integer ≥ 1`；字符串仅显式兼容读入；连接键整数比较 | 类型变更；按**首次冻结前 v1 修正**；冻结后为 `2.0` | `schemas/evidence/{evidence-manifest,verdict}.schema.json`、`evidence-verdict.md`、`domain.md`、`README.md` | T-C06-1..5 |

---

## 4. 逐项裁决

### R-01 Execution Bundle 版本语义分裂

**裁决**：采纳提案 §4 R-01 全部 PROPOSED 项。

1. 两个互不比较的版本轴：
   - `noahsark.execution-bundle/v1` = bundle 格式标识 / 引用命名空间；
   - `schema_version: "1.0"` = 载荷 schema 版本。
2. 节点分别校验两个支持集合；任一不支持 → 拒绝、保留原值、不猜测、不回退。
3. 禁止 `format == schema_version` 形式的比较，也禁止互相推导。
4. 错误表达：控制面复用 `SCHEMA_VERSION_UNSUPPORTED`；节点回执复用 `SCHEMA_INVALID`，并在 `facts` 固定写 `bundle_format_supported`、`bundle_payload_schema_supported`（boolean）。不新增顶层错误码、不使用 `subject`、不用 `message` 承载机器语义。

**理由**：两个 const 语义不同；原契约只写“未知 bundle 版本”，无法区分“信封/命名空间未知”与“载荷字段语义未知”。R-01 在不改任何 `const` 的前提下消除误判。

**拒绝的备选**：把 `job.execution_bundle.schema_version` 改成 `"1.0"`（让两个轴重合，正是冲突成因）；新增 `BUNDLE_FORMAT_UNSUPPORTED` 等顶层码（与既有码重复，且节点 `error.code` 是另一闭集）。

**Changed files**：`docs/contracts/README.md`（§2.3 第 10 条、§2.3 第 18 条）、`docs/contracts/security-node.md`（§10.1、§11 补充规则 6、§19.1 第 6 条、§19.2 错误词表）、`docs/contracts/domain.md`（§10 版本轴、§18 注）、`docs/contracts/schemas/security/job.schema.json`（`description`）、`docs/contracts/schemas/domain/execution-bundle.schema.json`（`description`）。

**兼容分类**：文档 + `description`，`1.x`；不改变任何校验结果。若未来格式标识升 `v2`，按 `README.md` §3.7 复制旧 schema。

**必需测试**：
- `T-R01-1`（T2）：`format=v1` + `payload=1.0` 通过；`format=v1` + `payload=9.9` 拒绝且 `facts.bundle_payload_schema_supported=false`、`bundle_format_supported=true`；`format=v9` + `payload=1.0` 两键取值相反。
- `T-R01-2`（T1）：节点校验器不含 `format == schema_version` 比较（代码断言或变异测试）。
- `T-R01-3`（L0）：README、security-node、domain 三处说明互相指回且一致。
- `T-R01-4`（T2）：两个 schema 的 `description` 变更不改变 `const` 快照。

**残余阻塞**：无外部事实阻塞。

---

### R-02 cleanup `operational_detail` 投影不对称

**裁决**：采纳提案 §4 R-02。

1. README 与 security-node 统一为“security 是 domain 超集”，domain 以 `additionalProperties: false` 拒绝 `operational_detail`。
2. 两条不变量：共享必填字段与 `cleanup_status` 词表逐字一致；详细运维字段唯一权威位置是 `schemas/evidence/cleanup-receipt.schema.json`，security 侧 `operational_detail` 仅传输期载体、入域前裁剪。
3. §12.1.1 映射表补 `cleanup_status` 与 `notes` 两行。

**理由**：在 domain 增加 `operational_detail` 会产生第二个运维明细存放点，并让 domain 投影不再“最小”；当前 schema 本就拒绝该字段，本裁决把既有行为写成规则。

**拒绝的备选**：在 domain 增加可选 `operational_detail`。

**Changed files**：`README.md`（§2.3 第 5 条 + 历史注记）、`security-node.md`（§10.5、§19.1 第 4 条）、`evidence-verdict.md`（§12.1.1）、`domain.md`（§12.1 注）、`schemas/security/receipt.schema.json`（`description`）、`schemas/domain/receipt.schema.json`（`description`）。

**兼容分类**：文档 + `description`，`1.x`；不改变现有校验结果。

**必需测试**：
- `T-R02-1`（T2）：domain `cleanup_receipt` 带 `operational_detail` → 失败；security 同结构 → 通过。
- `T-R02-2`（T2）：security 投影去掉 `operational_detail` 后通过 domain 同一 schema。
- `T-R02-3`（T1）：§12.1.1 映射覆盖 domain/security 全部必填字段（含 `cleanup_status`）。
- `T-R02-4`（L0）：文档检查禁止再出现“同一最小投影”作为规范表述。

**残余阻塞**：无外部事实阻塞。

---

### R-03 UI 证据轴映射缺失与投影 `UNKNOWN`

**裁决**：采纳提案 §4 R-03 的推荐选项。

1. §2.7 新增第五张 evidence 轴映射表；`UNKNOWN` 明确为“无权威对应值”的展示占位，必须携带 `freshness` 与最后权威更新时间。
2. `execution_status`/`evidence_status`/`verification_status` 的 `UNKNOWN` 不得写回权威；未知分别用 `NOT_STARTED`/`INCOMPLETE`/`NOT_RUN`。`validity_status` 的 `UNKNOWN` 是权威成员，例外。
3. `report_scope.mode` 定义为报告覆盖范围（`SMOKE`/`FORMAL`/`MIXED`）；`BLOCKED`/`STOPPED` 保留为过渡兼容值并加 `description`；新增可选 `contains_blocked`/`contains_stopped`（`1.x`）。
4. `verdict_summary.axes` 增加 `description` 标注 `UNKNOWN` 展示占位。
5. README 的 §2.7 覆盖声明与实际表数一致（现为五表），并以日期注记保留“曾提前声称五表”的历史。

**理由**：原 §2.7 只有四表却被 README 声称覆盖五项；`UNKNOWN` 若写入权威会削弱 fail-closed；`report_scope.mode` 的 `BLOCKED`/`STOPPED` 是结果/终态，不是运行模式。

**拒绝的备选**：给权威枚举增加 `UNKNOWN`；立即重命名 `report_scope.mode` 或删除 `BLOCKED`/`STOPPED`（结构性变更，须等 P1-08 与 `2.0`）。

**Changed files**：`ui-report-knowledge-audit.md`（§2.3、§2.7）、`README.md`（§2.3 第 8、11 条 + 历史注记）、`schemas/experience/report.schema.json`（`description` + 两个可选布尔）。

**兼容分类**：映射表/`description`/可选字段为 `1.x`；删除或重命名枚举属破坏性，本版本不主张。

**必需测试**：
- `T-R03-1`（T2）：展示 `evidence_status=UNKNOWN` 必带 `freshness`；投影服务拒绝对 `verdict.axes` 写 `UNKNOWN`。
- `T-R03-2`（T1）：五张映射表对每个权威值都有条目，缺项记录为 `UNKNOWN`。
- `T-R03-3`（T2）：`report_scope.mode` 取值说明与结构一致；`BLOCKED/STOPPED` 不被渲染为运行模式。
- `T-R03-4`（L0）：README 覆盖声明与 §2.7 实际表数一致（脚本计数）。
- `T-R03-5`（L2）：投影构建失败显示“不可用/陈旧”，不回退旧卡片。

**残余阻塞**：最终 UI 展示词汇与 `report_scope` 结构归 **P1-08**（提案 U-03/U-12）；本裁决只固定候选语义，不宣称 UI 已冻结。

---

### C-01 `mode` 词汇：`static_check` vs `static`

**裁决**：采纳提案 §5 C-01。

1. 运行模式在所有层只有 `static`/`smoke`/`formal`。
2. `static_check` 只保留为 `job.action` 与 `Receipt.job_kind`。
3. `evidence-manifest`、`verdict`、`report-evidence-index` 的 `$defs.mode` 已收敛为三值。
4. 读侧允许把 `static_check` 作为 `static` 的只读别名并记录兼容告警；写出方只写 `static`。
5. 关联校验比较归一后的 mode；未知值 fail-closed，不得当成 `static`。

**理由**：`security-node.md` §19.2 与 `domain.md` §12.3 已固定 `static_check`（action）→ `static`（Run.mode），但三份 evidence schema 仍把 `static_check` 当 mode，形成双重事实。

**拒绝的备选**：把 `Run.mode` 改成含 `static_check`（污染已批准三值运行模式）；只在文档说明“两者不同”（不消除误比较风险）。

**Changed files**：`schemas/evidence/evidence-manifest.schema.json`、`schemas/evidence/verdict.schema.json`、`schemas/evidence/report-evidence-index.schema.json`（`$defs.mode` + `description`）、`evidence-verdict.md`（§4.1 + 历史注记）、`domain.md`（§12.3）、`README.md`（§2.3 第 12、18 条）。

**兼容分类**：删除/替换枚举成员按 `README.md` §3.4 属破坏性；因无冻结修订/已接收证据，按**首次冻结前 v1 修正**处理。冻结后同类变更必须 `2.0` 并保留 `1.x` 只读解析器。

**必需测试**：
- `T-C01-1`（T2）：三份 schema 对 `static` 通过；`static_check` 仅在显式兼容模式通过且归一为 `static`。
- `T-C01-2`（T1）：`Run.mode`、`Attempt.run_mode`、归一后证据 mode 三者相等。
- `T-C01-3`（T2）：未知 mode（如 `diagnostics`）在证据层拒绝，不落入 `static`。
- `T-C01-4`（T2）：三份 `$defs.mode` 完全相同；`grep static_check` 仅出现在 action/job_kind 语境。

**残余阻塞**：无外部事实阻塞；版本路径认定须独立复核。

---

### C-02 `failure_classification` 与 `failure_class` 词表分裂

**裁决**：采纳提案 §5 C-02。

1. 以 domain 8 个大写值为唯一权威词表；证据侧 8 个小写值为显式投影。
2. `none` 用**省略 `failure_classification`** 表达，不新增 `NONE`；`null` ≡ 省略 ≡ `none`（E-02）。
3. `needs-review` 用 `business_verdict=NEEDS_REVIEW` + `verification_status!=PASS` 表达，不塞进 domain 枚举。
4. 双向转换共享同一张机器可读映射表（候选路径 `docs/contracts/mappings/failure-class.json`，本版本不创建）。
5. 表外值 fail-closed 为 `NEEDS_REVIEW`；只有 `valid-failure` ↔ `VALID_FAILURE` 计入正式分母。

**理由**：domain 值是持久化实体字段且已绑定分母规则；小写值是判定产物序列化约定，不应成为第二套分类学。改 domain 为小写破坏面最大；把 verdict 改大写会破坏 §14.2 的派生顺序。

**拒绝的备选**：把 domain 改成小写；把 verdict 改成大写并删除 `none`/`needs-review`；把 `needs-review` 映射为 `BLOCKED`（丢失“待复核 vs 硬阻塞”区别）。

**Changed files**：`domain.md`（§9.4 双向表 + 规则）、`evidence-verdict.md`（§15.1 双向表 + 规则）、`schemas/domain/run.schema.json`、`schemas/domain/attempt.schema.json`（`description`）、`schemas/evidence/evidence-manifest.schema.json`、`schemas/evidence/verdict.schema.json`（`description` + `null` 语义）、`README.md`（§2.3 第 13 条）。

**兼容分类**：文档 + `description`，`1.x`；成员集未变。

**必需测试**：
- `T-C02-1`（T2）：8 个权威值 ↔ 8 个投影值一一对应；`none`/`needs-review` 返回“无字段/由五轴表达”而非抛错。
- `T-C02-2`（T1）：`decision=NEEDS_REVIEW` 时 domain 不出现 `VALID_FAILURE`；缺失 `failure_classification` 时报告不显示失败类。
- `T-C02-3`（T2）：表外值 → `NEEDS_REVIEW`，不进入正式分母。
- `T-C02-4`（T1）：`valid-failure` ↔ `VALID_FAILURE` 仍计入正式分母；其余 7 值不计入。
- `T-C02-5`（L0）：两份契约的 8 个成员集大小写归一后完全相同。

**残余阻塞**：`needs-review` 的 domain 表达方式（提案 U-05）按推荐选项固定为“省略 + 五轴”；若所有者未来要求可查询失败原因，需另行走兼容扩展并说明分母。

---

### C-03 线协议 `lease.state` 缺少领域映射

**裁决**：采纳提案 §5 C-03 的固定映射 + 守卫 + 未知值规则。

| 线协议 | 领域 `Lease.state` | `occupancy_state` | 守卫 |
|---|---|---|---|
| `granted` | `GRANTED` | `OCCUPIED` | 领取确认后才 `HELD`。 |
| `renewed` | `HELD` | `OCCUPIED` | 只延长 `expires_at`；`RECLAIM_PENDING` 不恢复。 |
| `released` | `RELEASING` → `RELEASED` | `OCCUPIED` → `IDLE` | 三项前置条件全真才落 `RELEASED`。 |
| `expired` | 不降级不升级 | `OCCUPIED` | 永不映射 `RELEASED`/`IDLE`、不判失败、不重派。 |
| `revoked` | `RELEASING` | `OCCUPIED` | STOP-first；清理失败/安全事件可 `QUARANTINED`。 |
| `reclaimed` | `RECLAIM_PENDING` | `OCCUPIED` | 不得直接跳 `RELEASED`。 |
| 表外值 | 不改变 | 保持原值 | 审计告警；不释放、不重派、禁止新派发。 |

补充：`QUARANTINED` 无线协议值，只能控制面审计后写入；映射只在控制面生效；三处文档（security-node §19.2、domain §11.2/§12.3、evidence-verdict §13.1）保持一致。

**理由**：原 §19 只写“字段对齐但不互相替代”，没有映射，导致“传输事实”与“所有权事实”可能被实现者合并，直接威胁 B4/B5。

**拒绝的备选**：给领域增加 `RENEWED`/`EXPIRED`/`REVOKED`/`RECLAIMED` 同名状态；`released → RELEASED` 无条件直通。

**Changed files**：`security-node.md`（§10.2、§19.1 第 2 条、§19.2 映射表）、`domain.md`（§11.1、§11.2 接收映射）、`evidence-verdict.md`（§13.1 交叉引用）、`schemas/security/lease.schema.json`（`state`/`endpoint_set` `description`）、`README.md`（§2.3 第 14 条）。

**兼容分类**：文档 + `description`，`1.x`；不改变 `lease.schema.json` 枚举。行为收紧（`released` 必须满足三项前置条件）属实现层，需在 P2-02/P2-04 体现。

**必需测试**：
- `T-C03-1`（T2 表驱动）：6 值各生成期望状态；`HELD` 下 `expired` 于 `ONLINE`/`STALE` 分别断言 `HELD`/`RECLAIM_PENDING`；`GRANTED` 下 `expired` 不升级；`occupancy_state` 恒 `OCCUPIED`。
- `T-C03-2`（T1）：`released` 但任一前置条件 false → 停在 `RELEASING` + `LEASE_RELEASE_PRECONDITION_FAILED`。
- `T-C03-3`（T1）：`expired` + run `RUNNING` → run 状态、`execution_permit`、设备分配均不变。
- `T-C03-4`（T2）：表外值不改状态、不释放、不派发、产生审计事件。
- `T-C03-5`（L3/L4 真机）：`revoked` 期间实际停止/释放时序符合 STOP-first。

**残余阻塞**：`T-C03-5` 需真机窗口（提案 U-06/U-11）；`revoked` 与 `QUARANTINED` 的最终阈值仍归 P0-04 + 安全责任人。

---

### C-04 端点类型词汇与身份语义

**裁决**：采纳提案 §5 C-04 的**最小先行方案**，并完成双向映射文档：

1. 概念拆分：`endpoint_kind` = 能力类别（`audio_capture`/`audio_playback`/`serial`/`usb`/`gpio`）；`endpoint_set` = **端点身份集合**（`endpoint_id` / `endpoint_<32hex>`），用于占用键与证据归属。
2. 音频别名双向：`audio_input ↔ audio_capture`、`audio_output ↔ audio_playback`；domain 词汇权威，线协议旧词仅入站别名，入域前归一，写出方只发权威词。
3. `network`/`display` 仅节点能力标识；V0.0.1 不作为可占用 kind，除非 T-10 证实存在可占用实例。`gpio` 为 domain 能力标识，线协议暂无；新增需 T-10。
4. 未知 kind/未知端点身份 fail-closed。
5. 占用键 `(node_id, device_id, endpoint_set)` 的 `endpoint_set` 为身份集合；kind 不参与，避免同类多端点误判冲突。
6. 因结构拆分（domain `endpoint_set` 从 kind 枚举改为 ID 字符串）属 `2.0`，本版本**不改变 schema 类型**，只在 `description` 与文档中明确“字段名是历史遗留、元素语义按层区分”。

**理由**：原契约把“端点类别”和“端点身份”压在同一个 `endpoint_set` 名下，比较严重的是 wire 侧是身份、domain 侧是 kind，占用键因此存在层级混用。最小方案先消除语义误用，避免在没有迁移设计时改类型。

**拒绝的备选**：一次性把 wire 4 个 schema 改成 `audio_capture/audio_playback`（仍未解决身份问题）；只在 API 边界做字符串替换而不拆分概念。

**Changed files**：`security-node.md`（§10.2、§10.3、§11 规则 7、§19.1、§19.2 别名与身份表）、`domain.md`（§11.1、§11.3、§12.3）、`evidence-verdict.md`（§13.1）、`schemas/security/lease.schema.json`、`heartbeat.schema.json`、`node-identity.schema.json`、`node-enrollment.schema.json`（`description`）、`schemas/domain/lease.schema.json`、`device.schema.json`、`execution-bundle.schema.json`（`description`）、`schemas/evidence/device-occupancy.schema.json`（占用键 `description`）、`README.md`（§2.3 第 15 条）。

**兼容分类**：别名归一 + `description` 为 `1.x`；domain `endpoint_set` 类型变更与新增 wire `gpio` 属破坏性/扩展，须版本裁定（提案 U-07）。

**必需测试**：
- `T-C04-1`（T2）：音频别名双向；未知 kind 拒绝。
- `T-C04-2`（T1）：同设备两个不同 `endpoint_id` 的 `audio_capture` 不冲突；仅 ID 重叠冲突。
- `T-C04-3`（T2）：写出侧只产生权威词（4 份 security schema 的 writer 负例）。
- `T-C04-4`（T2）：`required_kinds` 与 receipt artifacts kind 值域与 domain 能力类一致。
- `T-C04-5`（L3/L4 真机）：真实音频/串口/GPIO 端点清单与命名。

**残余阻塞**：`T-C04-5` 与 `network`/`display`/`gpio` 可占用性需 **T-10 真机事实**（提案 U-07/U-10）。

---

### C-05 设备占用枚举命名分歧（SR-14）

**裁决**：采纳提案 §5 C-05 的三层模型与固定投影，并加入 `QUARANTINED → occupancy_state=OCCUPIED` 的 schema 收紧。

1. L1 权威：`Lease.state`（6 值）+ `Device.pool_state`（8 值）+ `release_preconditions`。
2. L2 粗投影：`occupancy_state` ∈ {`IDLE`,`OCCUPIED`,`RELEASING`}。
3. L3 历史/展示：`docs/v2`/`openspec` 四值；`device-occupancy.state` 十值细化。
4. 四值 → 三值/权威固定投影：`RELEASED → IDLE` 仅当三项前置条件全真且 `release_state=released`，否则 `OCCUPIED`；`QUARANTINED → OCCUPIED` + `pool_state=QUARANTINED` + `Lease.state=QUARANTINED`。
5. 禁止新增第四值；`RELEASED`/`QUARANTINED` 不是 occupancy 值。
6. `schemas/domain/lease.schema.json` 新增 `allOf` 条件：`state=QUARANTINED → occupancy_state=OCCUPIED`。

**理由**：把释放确认和隔离压进占用枚举会违反 B6 与 D-5；仅写“语义等价”会让 SR-14 继续开放，实现可能按旧四值建表。

**拒绝的备选**：把 `occupancy_state` 扩成四值；保留四值并只写语义等价。

**Changed files**：`domain.md`（§11.3 三层 + 投影 + D-6）、`evidence-verdict.md`（§13.1 历史词说明）、`schemas/domain/lease.schema.json`（新增 `allOf` 条件）、`README.md`（§2.3 第 16 条）。

**兼容分类**：投影表/说明为 `1.x`；`allOf` 收紧会改变合法对象集合（原 `QUARANTINED`+`IDLE` 由合法变非法），按**首次冻结前 v1 修正**处理。冻结后同类收紧需 `2.0`。

**必需测试**：
- `T-C05-1`（T2）：`occupancy_state` 只接受三值；`RELEASED`/`QUARANTINED` 即失败。
- `T-C05-2`（T1）：四值历史词按表投影；`RELEASED` 前置条件不全时投影为 `OCCUPIED`。
- `T-C05-3`（T2）：`Lease.state=QUARANTINED` → `occupancy_state=OCCUPIED`。
- `T-C05-4`（L0）：`docs/v2`/`openspec` 已标注四值为历史/兼容词，且 SR-14 状态与实际一致。

**残余阻塞**：SR-14 关闭与 `docs/v2`/`openspec` 回写属 **P0-03 后续同步批次**（提案 U-08/U-14），本版本仍开放，不得声称“占用枚举已统一”。

---

### C-06 evidence manifest `case_version` 类型不一致

**裁决**：采纳提案 §5 C-06。

1. `case_version` 在所有层为 `integer, minimum 1`；manifest 与 verdict 已从 `string` 改为整数。
2. 它是 `run_id + case_id + case_version + attempt` 连接键；比较/排序/哈希前不得静默 `parseInt`。
3. 展示层只能 `String(case_version)` 格式化；如需持久化标签必须独立字段并标注非连接键。
4. 条件性兼容读入：仅显式兼容模式接受 `^[1-9][0-9]{0,8}$` 字符串并归一，记录 `legacy_case_version_coerced` 告警；拒绝 `"0"`、`"01"`、`"1.0"`、`"+1"`、`" v1 "` 等。
5. `verdict.cases[].case_version` 必须与对应 `attempt.case_version` 整数相等，否则 `CASE_CONTENT_MISMATCH`。

**理由**：`case_version` 参与递增与 `supersedes_case_version` 比较；domain 三个实体已一致为整数。保留两套类型会让 verdict 消费者继续把字符串当连接键。

**拒绝的备选**：把 domain 改成 string（前导零/排序歧义 + 破坏三处一致）；保留两套类型并写“仅展示投影”（verdict 是判定产物，不是纯展示）。

**Changed files**：`schemas/evidence/evidence-manifest.schema.json`、`schemas/evidence/verdict.schema.json`（类型 + `description`）、`evidence-verdict.md`（§5.1 示例 + §4.1/§15.1 相关说明）、`domain.md`（§12.3 类型说明）、`README.md`（§2.3 第 17 条）。

**兼容分类**：`string → integer` 属 `README.md` §3.4 破坏性变更；因无冻结修订/已接收证据，按**首次冻结前 v1 修正**处理。冻结后必须 `2.0` 并保留 `1.x` 只读解析器。

**必需测试**：
- `T-C06-1`（T2）：`case_version: 1` 通过；`"1"` 严格模式失败、兼容模式通过且归一为 `1`。
- `T-C06-2`（T2 负例）：`"0"`、`"01"`、`"1.0"`、`"+1"`、`" 1 "`、`1.5` 全部失败。
- `T-C06-3`（T1）：`verdict.cases[].case_version` 与 `attempt.case_version` 整数相等；`"1"` vs `1` 不得被判为相等后继续。
- `T-C06-4`（T1）：复合键跨 manifest/verdict/attempt 三处一致。
- `T-C06-5`（L0）：`grep case_version` 在所有契约中只剩整数类型与展示说明。

**残余阻塞**：无外部事实阻塞；版本路径认定须独立复核。

---

## 5. 新增/对齐的映射表位置

| 映射 | 权威位置 | 备注 |
|---|---|---|
| Bundle 格式标识 vs 载荷 schema 版本 | `README.md` §2.3 第 10 条、`domain.md` §10、`security-node.md` §19.2 | 禁止相等比较 |
| failure_classification ↔ failure_class | `domain.md` §9.4、`evidence-verdict.md` §15.1 | 双向 8+2 行 |
| 线协议 lease.state → 领域 Lease.state/occupancy_state | `security-node.md` §19.2、`domain.md` §11.2 | 6 值 + 表外 |
| endpoint kind ↔ 入站别名 / endpoint identity | `security-node.md` §19.2、`domain.md` §11.1/§11.3 | 双向别名 + 身份规则 |
| 四值历史占用词 → 三值/权威 | `domain.md` §11.3、`evidence-verdict.md` §13.1 | `RELEASED`/`QUARANTINED` 非 occupancy |
| 最小 cleanup 投影 → 权威 cleanup receipt | `evidence-verdict.md` §12.1.1 | 含 `cleanup_status`、`notes` |
| evidence 五轴投影 | `ui-report-knowledge-audit.md` §2.7 | 第五张 evidence 表 |
| report_scope.mode 覆盖范围 | `ui-report-knowledge-audit.md` §2.7、`report.schema.json` | `BLOCKED`/`STOPPED` 过渡值 + 可选布尔 |

---

## 6. 仍需外部事实或阶段门关闭的事项

| ID | 未决/阻塞 | 本记录的处理 |
|---|---|---|
| U-10 | 真机端点能力与命名（C-04） | 未关闭；`network`/`display`/`gpio` 可占用性待 T-10；文档明确“当前不可占用”。 |
| U-11 | `revoked`/`reclaimed` 的 L3/L4 真机时序（C-03） | 未执行；`T-C03-5` 登记为后续真机窗口。 |
| U-12 | P1 UI 候选核验与 P1-08 冻结（R-03） | 未关闭；本版本只固定候选语义，`report_scope` 结构删除/重命名待 P1-08。 |
| U-13 | Phase 0 归档 open-blocker T-23 | 未关闭；本记录不宣称 Phase 0 可关闭。 |
| U-14 | `docs/v2`/`openspec` 四值回写与 SR-14 关闭（C-05） | 未执行；属 P0-03 后续同步批次，SR-14 仍开放。 |
| — | 节点/控制面错误码全量映射（E-05） | 仅固定 R-01 局部做法；完整两套词表映射为后续登记项。 |
| — | `docs/contracts/mappings/failure-class.json` | 未创建；候选路径由所有者决定。 |

---

## 7. 变更文件清单

### 7.1 文档

- `docs/contracts/README.md`
- `docs/contracts/domain.md`
- `docs/contracts/security-node.md`
- `docs/contracts/evidence-verdict.md`
- `docs/contracts/ui-report-knowledge-audit.md`
- `docs/contracts/thresholds.md`（仅状态/版本抬头，无语义改动）
- `docs/delivery/contract-adjudication-record.md`（本文件，新增）

### 7.2 JSON Schema（仅 `description`、枚举/类型或条件约束）

- `docs/contracts/schemas/domain/run.schema.json`
- `docs/contracts/schemas/domain/attempt.schema.json`
- `docs/contracts/schemas/domain/execution-bundle.schema.json`
- `docs/contracts/schemas/domain/lease.schema.json`
- `docs/contracts/schemas/domain/device.schema.json`
- `docs/contracts/schemas/domain/receipt.schema.json`
- `docs/contracts/schemas/evidence/evidence-manifest.schema.json`
- `docs/contracts/schemas/evidence/verdict.schema.json`
- `docs/contracts/schemas/evidence/report-evidence-index.schema.json`
- `docs/contracts/schemas/evidence/device-occupancy.schema.json`
- `docs/contracts/schemas/security/job.schema.json`
- `docs/contracts/schemas/security/lease.schema.json`
- `docs/contracts/schemas/security/heartbeat.schema.json`
- `docs/contracts/schemas/security/node-identity.schema.json`
- `docs/contracts/schemas/security/node-enrollment.schema.json`
- `docs/contracts/schemas/security/receipt.schema.json`
- `docs/contracts/schemas/experience/report.schema.json`

**未修改**：`schemas/evidence/cleanup-receipt.schema.json`、`schemas/evidence/evidence-item.schema.json`、`schemas/evidence/verification-record.schema.json`、`schemas/domain/task|revision|approval|gate|case|node.schema.json`、`schemas/experience/{access-policy,audit-event,knowledge-candidate,knowledge-item,task-card}.schema.json`、`schemas/security/{anomaly-event,log-query,stop}.schema.json`、`schemas/config/thresholds.schema.json`。

---

## 8. 验证证据（执行记录）

在仓库根目录执行：

```bash
python3 - <<'PY'
import glob, json
from jsonschema import Draft202012Validator
paths = sorted(glob.glob("docs/contracts/schemas/*/*.schema.json"))
for p in paths:
    with open(p, encoding="utf-8") as fh:
        s = json.load(fh)
    assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema", p
    Draft202012Validator.check_schema(s)
print("schemas_ok", len(paths))
PY
```

预期：`schemas_ok 35`，无异常。

```bash
# 不得再把 static_check 当 mode
python3 - <<'PY'
import json
for p in ["docs/contracts/schemas/evidence/evidence-manifest.schema.json",
          "docs/contracts/schemas/evidence/verdict.schema.json",
          "docs/contracts/schemas/evidence/report-evidence-index.schema.json"]:
    d=json.load(open(p)); assert d["$defs"]["mode"]["enum"]==["static","smoke","formal"], p
print("mode_ok")
PY

# 规范 schema 中 case_version 不得为 string
python3 - <<'PY'
import json
for p,defname in [("docs/contracts/schemas/evidence/evidence-manifest.schema.json","caseEntry"),
                  ("docs/contracts/schemas/evidence/verdict.schema.json","caseResult")]:
    d=json.load(open(p))["$defs"][defname]["properties"]["case_version"]
    assert d["type"]=="integer" and d["minimum"]==1, (p,d)
print("case_version_ok")
PY

# lease_expired 不得作为所有权到期语义
grep -RIn "lease_expired" docs/contracts/ || true

git diff --check
```

实际结果记录于交付回复；本文件不预填“通过”结论。

---

## 9. 非声明

1. 本记录**不**宣称 9 项契约已冻结、已批准或已实现。
2. 本记录**不**宣称 Phase 0 可关闭、A-0 可通过、Phase 2 可启动。
3. 本记录**不**宣称 UI 词汇已定稿；R-03 的展示词汇仍归 P1-08。
4. 本记录**不**宣称 `docs/v2`/`openspec` 的旧四值枚举已失效；SR-14 仍开放。
5. 本记录不包含密钥、凭据、真实节点值、真实设备序列号或原始证据。
6. 本文件未提交（commit）或推送（push）。
