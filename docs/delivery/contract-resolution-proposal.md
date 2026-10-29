# 契约残余解决方案提案（Contract Resolution Proposal）

> 版本：v0.1（2026-10-29）
> 状态：**非权威提案 / 只读准备稿**。不是契约评审结论，不是冻结，不是批准，不构成实现、测试、部署、验收或发布授权，**不能关闭 Phase 0**。
> 输入：`docs/delivery/contract-residual-followup.md`（9 项残余/冲突）、`docs/contracts/`（全部 `frozen-candidate v1`）、`docs/delivery/phase2-input-map.md`、已评审验收/测试边界与主计划。
> 输出边界：本文件**只新增自身**；未修改 `docs/contracts/`、schema、`.omo` 计划、`plan.md`、`docs/v2`、`openspec`、UI 文件、产品代码、迁移或 OpenAPI。
> 并行关系：本文件是 **P1 UI 候选核验之外的并行准备车道**；不声称 UI 已核验、契约已冻结、Phase 0 已关闭或 Phase 2 已启动。

---

## 0. 文件性质

本文把残余审计中 9 项发现（R-01..R-03、C-01..C-06）逐项转成**可裁决的候选方案**。对每一项给出：

1. 只读证据（`EVIDENCED`，可复现）；
2. 建议的规范口径（`PROPOSED`，不生效）；
3. 被拒绝的备选与理由；
4. 受影响候选文件；
5. 迁移/兼容影响（按 `docs/contracts/README.md` §3 版本规则判断）；
6. 所需测试（沿用已评审 L0–L5 / T1–T6 词汇）；
7. 是否必须由真实环境或用户输入才能定案（`BLOCKED` 指向项）。

**关键定位**：即使本文 9 项全部被所有者接受，也只表示“契约候选内容可以改”，不表示契约已冻结、字段已实现、Phase 0 可归档或 Phase 2 可开工。

---

## 1. 标记与证据约定

| 标记 | 含义 | 约束 |
|---|---|---|
| **EVIDENCED** | 本次只读观察到的文件、行号、枚举、类型；命令可复现 | 只证明“当前工作区文本是这样”，不证明契约已评审/已冻结/已实现 |
| **PROPOSED** | 本文建议的规范口径、映射表、守卫与测试 | **未生效**；不得被引用为已冻结规则、已批准契约或实现依据 |
| **BLOCKED** | 必须由契约所有者裁决、或依赖外部事实（T-09/T-10/T-11/T-12/T-23）、或依赖 P1-08 才能关闭 | 在关闭前不得写成既成事实；不得用默认值填充 |

补充规则：

- `EVIDENCED` 与 `PROPOSED` 必须分段书写，禁止在同一句里把建议写成事实。
- 本文不把任何条目标为“已冻结”“已批准”“已解决”。即使某项看似无争议，也只能写“建议由所有者确认”。
- 事实源优先级保持 `docs/VERSIONING.md` §2 不变：已批准需求基线 > 已评审架构/模块/验收/测试边界 > 已同步草案正文 > `docs/contracts/` 字段化表达 > `docs/v2`/`openspec`/`solutions/` 历史参考。
- 本文的提案位于第 4 层以下的“候选规划输入”，不得反向覆盖第 1–3 层。

---

## 2. 提案不得改动的已批准边界

下列边界在 `docs/delivery/phase2-input-map.md` §3、`docs/VERSIONING.md` §2.4 与根 `plan.md` 批准记录中已确认为 **F（已批准/已评审约束）**。本文所有提案都在这些边界之内，若与任何一条冲突，则该提案作废。

| # | 边界 | 权威来源 | 本文提案的落点 |
|---|---|---|---|
| B1 | Linux 控制面独占生成、冻结、审核、修复、版本化与**最终判定** | 需求基线；B-4/B-5；`domain.md` §19 | R-01/C-02/C-06 只改字段与词表，不改写入方 |
| B2 | Windows Node Agent 只执行冻结 Bundle 并**回传事实**；`used_for_decision=false` | B-4；`security-node.md` §10.5/§19.1 | R-01 的格式/载荷版本校验属节点侧“拒绝”动作，仍不产生判定 |
| B3 | **PostgreSQL 是唯一正式数据库**，SQLite 仅历史/只读 | B-6；SR-02；`domain.md` §17.1 | 全部提案不引入第二事实源或本地库 |
| B4 | 离线续跑：已启动冻结压测断线继续；设备保持 `OCCUPIED`；不重派/重播/重复采样 | B-3/A-3；`domain.md` §15.2 | C-03 的 `expired` 映射必须保持“到期 ≠ 所有权到期” |
| B5 | STOP-first 重连：待 STOP → 停止后续动作 → 补传 → 去重 → 对账 → 恢复领取 | `domain.md` §15.3；`security-node.md` §13.3 | C-03 `revoked`/`reclaimed` 不得绕过 STOP-first 直释放 |
| B6 | **设备释放 / 证据完整性 / 最终判定三平面分离**；缺 `cleanup_receipt` ≠ 证据不完整 | `evidence-verdict.md` §12.3/§13；`thresholds.md` TH-L-08 | R-02/C-03/C-05 只改投影与状态映射，不合并三平面 |
| B7 | 五轴独立；正式 PASS 五条件同时成立；烟测/模拟/回放永不进入正式分母 | `domain.md` §14；`evidence-verdict.md` §14 | R-03/C-02/C-06 不改派生顺序与分母规则 |
| B8 | 未知枚举 fail-closed；未知值不得当 PASS | `domain.md` I-17；`README.md` §3.6 | 全部新映射表都补“未知值不升权”规则 |

---

## 3. 提案总览

共 **9 项提案**（3 项承接既有残余 R-01..R-03，6 项承接新确认冲突 C-01..C-06）。另在 §6 登记 **5 项只读范围补充**，它们不是新提案，但会扩大 R-01/C-04/C-06/R-02 的受影响文件清单。

| ID | 一句话提案 | 兼容级别（按 README §3） | 需所有者裁决 | 需真机/用户证据 |
|---|---|---|---|---|
| R-01 | 明确“bundle 格式标识”与“载荷 `schema_version`”是两个独立版本轴，禁止相等比较 | 文档级（1.x 兼容） | 是 | 否 |
| R-02 | 把 README 的“同一最小投影”改为“security 是 domain 的超集”；domain 继续不接受 `operational_detail` | 文档级（1.x 兼容） | 是 | 否 |
| R-03 | §2.7 增补 evidence 轴映射；`UNKNOWN` 定为“仅展示占位、不写回权威”；拆分 `report_scope.mode` 的“模式”与“结果”语义 | 文档级 + schema `description`（1.x 兼容）；词汇冻结依赖 P1-08 | 是 | 否（UI 词汇由 P1-08 定，非真机） |
| C-01 | 全层统一 `mode = static/smoke/formal`；`static_check` 只保留为 `job.action`/`Receipt.job_kind`；读侧接受旧值并归一 | 改枚举成员 → 破坏性（2.0），或在首次冻结前作 v1 修正 | 是（含版本路径选择） | 否 |
| C-02 | 建立唯一权威失败词表（domain 大写 8 值）+ 证据侧显式投影；`none` 用“省略字段”表达，`needs-review` 用五轴表达 | 文档级映射（1.x）；若改成员集则破坏性 | 是（含 `needs-review` 表达方式） | 否 |
| C-03 | 增补 `lease.state`（6 值）→ 领域 `Lease.state`（6 值）固定映射 + 守卫 + 未知值不升权 | 文档级映射（1.x）；若加约束则收紧 | 是 | 映射本身否；行为验证属 L3/L4 |
| C-04 | 区分 `endpoint_kind`（能力类）与 `endpoint_set`（端点身份）；音频 kind 统一为 `audio_capture/audio_playback`，`audio_input/audio_output` 仅为入站别名 | 别名归一为 1.x；统一枚举为破坏性或 v1 修正 | 是 | **部分是**：枚举统一否；真实端点清单需 T-10 |
| C-05 | 明确三层：权威 `Lease.state`+`Device.pool_state` / 粗投影 `occupancy_state`（3 值）/ 历史四值枚举降为兼容词 | 文档级（1.x）；回写 `docs/v2`/`openspec` 属 P0-03 后续 | 是 | 否 |
| C-06 | `case_version` 全层统一为 `integer ≥1`；字符串仅允许显式兼容读入，不得作为连接键 | 改类型 → 破坏性（2.0），或 v1 修正 | 是（含版本路径与兼容读策略） | 否 |

> 表中“兼容级别”是**按现行规则推断**的结果，不是所有者的版本裁定。实际归入 `1.x`、`2.0` 还是“首次冻结前 v1 修正”，必须由契约所有者在评审记录中显式写明（见 §8 U-01）。

---

## 4. 重点候选残余提案（R-01..R-03）

### R-01 Execution Bundle 版本语义分裂

**EVIDENCED**

- `docs/contracts/schemas/security/job.schema.json:196-198`：`payload.execution_bundle.schema_version` 为 `const: "noahsark.execution-bundle/v1"`。
- `docs/contracts/schemas/domain/execution-bundle.schema.json:26`：`schema_version` 为 `const: "1.0"`。
- `docs/contracts/security-node.md:518` 已为 evidence manifest 建立同类区分（`predicate_type: noahsark.test-evidence/v1` 只版本化 predicate 词汇，**不是**载荷 schema 版本）；但 Bundle 没有对应说明。
- `docs/contracts/security-node.md:561` 只写“未知 bundle 版本 → 拒绝并审计”，未区分“格式标识未知”与“载荷版本未知”。
- `docs/contracts/domain.md` §10 未出现 `noahsark.execution-bundle/v1` 字样。
- `docs/delivery/phase0-contract-remediation-verification.md:128` 将本条列为“低，信息”级非阻断遗留。

**PROPOSED**

1. 定义两个**互不比较**的版本轴：
   - `noahsark.execution-bundle/v1` = **bundle 格式标识 / 引用命名空间**。它回答“这份引用句柄按哪套信封与工件命名规则解析”，随句柄结构演进。
   - `schema_version: "1.0"` = **负载 schema 版本**。它是载荷字段语义的版本，遵循 `README.md` §3.2（`schema_version` 属于载荷，未知即 fail-closed）。
2. 禁止规则（写入 `README.md` §2.3 与 `security-node.md` §11 补充规则）：节点**不得**要求两者相等，也不得用其一推导另一个；任何实现若把 `"noahsark.execution-bundle/v1" != "1.0"` 判为不兼容，即违反本契约。
3. 校验规则：节点必须分别校验
   - 格式标识 ∈ 支持集合（当前 `{noahsark.execution-bundle/v1}`）；
   - 载荷 `schema_version` ∈ 支持集合（当前 `{"1.0"}`）；
   - 两者任一不在支持集合 → 拒绝执行，保留原始值，不猜测、不回退。
4. 错误表达（**注意两层词表不同**，见 §6 E-05）：
   - 控制面侧复用 `domain.md` §18 已登记的 `SCHEMA_VERSION_UNSUPPORTED`（类别“契约”，fail-closed），不新增顶层码。
   - 节点侧 `security/receipt.schema.json:231-264` 的 `error.code` 是**独立闭集**（`SCHEMA_INVALID`、`ARTIFACT_MISMATCH` 等），且 `additionalProperties: false`、**没有** `subject` 字段。因此第一版提案**不得**假设可写 `subject`。
   - 推荐做法：节点回执用已登记的 `SCHEMA_INVALID`，把“哪一轴不支持”放进 `facts`（该对象 `additionalProperties: true`，上限 256 键），固定两个键：`bundle_format_supported`、`bundle_payload_schema_supported`（均 boolean）。
   - 若所有者认为需要一等错误码，只能走 `error.code` 的**枚举扩展**（`1.x` 兼容，`README.md` §3.6），并同步控制面映射；不得借 `message` 文本表达机器语义。
5. 三处文档引用同一段说明：`README.md` §2.3（跨契约对齐）、`security-node.md` §10.1/§11（节点校验点）、`domain.md` §10 不变量 B-3（Linux 侧解释）。

**被拒绝的备选**

- **把 `job.execution_bundle.schema_version` 改成 `"1.0"`**：会让线上句柄失去“格式命名空间”，同名字段在信封与载荷两层语义重合，正是本条冲突的成因。
- **新增 `BUNDLE_FORMAT_UNSUPPORTED` / `SCHEMA_VERSION_UNSUPPORTED` 两个顶层码**：与已存在码重复，且未冻结前扩大注册表无收益。注意节点侧 `error.code` 是另一套闭集，两个“顶层码”更不能直接塞进回执。

**受影响候选文件**

`docs/contracts/README.md`（§2.3 增补）、`docs/contracts/security-node.md`（§10.1/§11/§19.1）、`docs/contracts/domain.md`（§10 不变量 B-3 说明）、`docs/contracts/schemas/security/job.schema.json`（仅 `description`，不改 `const`）、`docs/contracts/schemas/domain/execution-bundle.schema.json`（仅 `description`）；若所有者选择一等错误码，另需 `docs/contracts/schemas/security/receipt.schema.json`（`error.code` 枚举扩展）。

**迁移/兼容影响**

- 纯文档 + `description`：`1.x` 兼容，不改变任何校验结果。
- 新增“禁止相等比较”是**解释性约束**，不收紧 schema；对历史对象无影响。
- 若将来格式标识升到 `v2`，按 `README.md` §3.7 复制旧 schema 而非原地覆盖。

**所需测试**

- `T-R01-1`（T2 契约测试）：正例 `format=v1` + `payload=1.0` 通过；反例 `format=v1` + `payload=9.9` 拒绝且 `facts.bundle_payload_schema_supported=false`、`facts.bundle_format_supported=true`；反例 `format=v9` + `payload=1.0` 拒绝且两键取值相反。
- `T-R01-2`（T1 单元）：断言节点校验器**不含** `format == schema_version` 形式的比较（可用变异测试或代码断言）。
- `T-R01-3`（L0 文档一致性）：三处文档说明文本一致，且 `grep` 任一文件都能互相指回。
- `T-R01-4`（T2）：`job.schema.json` 与 `execution-bundle.schema.json` 的 `description` 不改变 `const` 值（快照对比）。

**是否需真实环境/用户证据**：**否**。只需契约所有者裁决与评审记录。

**状态**：`PROPOSED`；依赖 §8 U-01。

---

### R-02 cleanup `operational_detail` 投影不对称

**EVIDENCED**

- `docs/contracts/README.md:61`（§2.3.5）称 security 与 domain 的 `cleanup_receipt` “是同一最小释放投影”，并称“详细运维字段只允许放在……可选 `operational_detail` 下”。
- `docs/contracts/schemas/security/receipt.schema.json:370-405`：`cleanup_receipt.operational_detail` 为可选对象（`residual_processes`、`disk_freed_bytes`、`actions`、`failure_code`）。
- `docs/contracts/schemas/domain/receipt.schema.json:180-215`：domain `cleanup_receipt` 为 `additionalProperties: false`，**无** `operational_detail`。
- 三处 `cleanup_status` 枚举一致（`completed/completed_with_warnings/failed/not_required/unknown`）。
- `docs/contracts/evidence-verdict.md:713-723`（§12.1.1）给出最小投影 ← 权威回执的映射表，但该表**未列 `cleanup_status`**；而 `cleanup_status` 在 domain 与 security 两侧都是必填字段（见 §6 补充 E-04）。

**PROPOSED**

1. 采纳审计首选方案：把 `README.md:61` 改为——**security 的 `cleanup_receipt` 是 domain 最小释放投影的超集**；domain 只承载最小释放事实，且以 `additionalProperties: false` **显式拒绝** `operational_detail`。
2. 明确三条不变量，写入 `README.md` §2.3.5 与 `security-node.md:519`：
   - 两侧共享的必填字段与 `cleanup_status` 词表**必须逐字一致**（这是“投影”成立的唯一条件）。
   - 详细运维字段的**唯一权威位置**是 `schemas/evidence/cleanup-receipt.schema.json`；security 侧 `operational_detail` 只是传输期便捷载体，入域前必须裁剪，**不得**回写 domain。
   - 消费方不得假设两侧可互相反序列化；跨侧转换必须按 §12.1.1 映射表逐字段进行，未知字段丢弃并审计。
3. 补齐 §12.1.1 映射表的缺项：增加 `cleanup_status ← 权威回执 cleanup_status`（同名词表映射，非推断）与 `notes ← 权威回执 notes`（可为 `null`）。

**被拒绝的备选**

- **在 domain 增加可选 `operational_detail`**：会产生两个运维明细存放点，与“权威 cleanup receipt 是唯一清理事实来源”冲突（`README.md` §2.3.5 自身、`security-node.md:519`、`evidence-verdict.md:713`），并使 domain 投影不再“最小”，放大后续 API/迁移面。

**受影响候选文件**

`docs/contracts/README.md`（§2.3.5 措辞）、`docs/contracts/security-node.md`（§10.5 补充）、`docs/contracts/evidence-verdict.md`（§12.1.1 映射表补两行）、`docs/contracts/domain.md`（§12.1 cleanup 字段说明可选补一句“不接受运维明细”）。**不修改**任何 schema 结构。

**迁移/兼容影响**

- 纯文档：`1.x` 兼容；不改变现有 schema 校验结果（domain 现在就已经拒绝 `operational_detail`）。
- 若早期实现曾向 domain 写入 `operational_detail`，该写入在当前 schema 下本就应失败；本条只是把既有行为写成规则。

**所需测试**

- `T-R02-1`（T2 契约测试）：domain `cleanup_receipt` 带 `operational_detail` → 校验失败；security 同结构 → 通过。
- `T-R02-2`（T2）：security 投影去掉 `operational_detail` 后，能通过与 domain 同一 schema 校验（证明超集关系可裁剪）。
- `T-R02-3`（T1 单元）：§12.1.1 映射表覆盖 domain/security 全部必填字段（含 `cleanup_status`），缺一即失败。
- `T-R02-4`（L0）：`README.md` 用语检查脚本，禁止再出现“同一最小投影”表述。

**是否需真实环境/用户证据**：**否**。

**状态**：`PROPOSED`；依赖 §8 U-01。

---

### R-03 UI 证据轴映射缺失与投影 `UNKNOWN`

**EVIDENCED**

- `docs/contracts/ui-report-knowledge-audit.md:194-243`（§2.7）只有 occupancy、communication、gate、run **四张**映射表。
- `docs/contracts/README.md:64` 称 §2.7 覆盖 “occupancy/communication/gate/run/evidence” 五项。
- `docs/contracts/ui-report-knowledge-audit.md:100-106` 的五轴允许值中，`execution_status`、`evidence_status`、`verification_status` 含 `UNKNOWN`；`domain.md:309-313` 与 `schemas/domain/run.schema.json`、`attempt.schema.json` 的权威枚举中这三轴**无** `UNKNOWN`（仅 `validity_status` 有）。
- `docs/contracts/schemas/experience/report.schema.json:271-289` 的 `verdict_summary.axes` 同样允许上述 `UNKNOWN`。
- `report.schema.json:66-68` 的 `report_scope.mode` 为 `SMOKE/FORMAL/MIXED/BLOCKED/STOPPED/UNKNOWN`，未在 §2.7 登记权威来源；`BLOCKED`/`STOPPED` 是结果/终态而非运行模式。
- `ui-report-knowledge-audit.md:243` 自定规则：“若新增投影枚举，必须先在此登记权威来源与禁止推断”——evidence 轴与 report mode 均未满足。
- `docs/contracts/evidence-verdict.md:882` 已写明“展示层可用 `UNKNOWN` 占位，但 `verdict.axes.evidence_status` 不得写 `UNKNOWN`”，但 UI 契约未引用该句。

**PROPOSED**

1. **补 evidence 轴映射表**（§2.7 第五张表），权威来源为五轴字段本身：

   | 任务卡/报告展示值 | 权威来源 `evidence_status` | 规则 |
   |---|---|---|
   | `COMPLETE` | `COMPLETE` | 直接透传，不重新计算。 |
   | `INCOMPLETE` | `INCOMPLETE` | 直接透传。 |
   | `CONFLICTED` | `CONFLICTED` | 直接透传，不得改写成 `INCOMPLETE`。 |
   | `UNVERIFIED` | `UNVERIFIED` | 直接透传，不得改写成 `INCOMPLETE`。 |
   | `UNKNOWN` | **无对应权威值** | 仅表示“投影尚未读取/不可用”；必须同时携带 `freshness` 与最后权威更新时间。 |

2. **`UNKNOWN` 的越权禁止**（写入 §2.7 表尾规则）：`execution_status`、`validity_status`、`evidence_status`、`verification_status` 的 `UNKNOWN` 一律为**展示占位**，不得写回 `Run`/`Attempt`/`verdict.axes`；写回路径只接受权威枚举值。未知应分别写 `NOT_STARTED`/`UNVERIFIED`/`INCOMPLETE`/`NOT_RUN`（`validity_status` 例外，其权威枚举本身含 `UNKNOWN`）。
3. **修正 `README.md:64`**：把“已覆盖五项”改成与事实同步的两段式表述——
   - 在 evidence 表写入前：读作“§2.7 当前覆盖 occupancy / communication / gate / run 四表；evidence 轴待登记”；
   - evidence 表写入后：才可改为“五表”。
   - 硬规则：README 的覆盖声明必须与 §2.7 实际表数一致，禁止提前宣称。
4. **`report_scope.mode` 语义拆分**（首选）：
   - 保留字段，但把它定义为**报告覆盖范围**，不是运行模式；`RUN.mode` 仍是 `static/smoke/formal`。
   - `SMOKE`/`FORMAL`/`MIXED` 表示覆盖范围（`MIXED` = 同时覆盖烟测与正式运行）。
   - `BLOCKED`/`STOPPED` 不是 mode，改为独立布尔/数组表达：`report_scope.contains_blocked: boolean`、`report_scope.contains_stopped: boolean`（新增可选字段，`1.x` 兼容）。
   - `UNKNOWN` 仅当覆盖范围无法判定。
   - 过渡期（不改结构的最小方案）：保留 `BLOCKED`/`STOPPED` 值，但在 `report.schema.json` 该字段 `description` 中写明“表示报告覆盖的运行含阻断/停止，不是 Run.mode”，并在 §2.7 登记。
   - 在 `report.schema.json` 的 `verdict_summary.axes.*` 增加 `description`，标注 `UNKNOWN` 为展示占位、不得写回权威。

**被拒绝的备选**

- **给权威枚举增加 `UNKNOWN`（含 execution/evidence/verification）**：会让 `UNKNOWN` 成为可持久化事实，削弱 fail-closed，并直接违反 `evidence-verdict.md:882`。
- **把 `report_scope.mode` 直接重命名为 `scope_mode` 且立即改值**：属结构破坏性变更，且最终 UI 词汇归 P1-08，提案阶段不宜先改。

**受影响候选文件**

`docs/contracts/ui-report-knowledge-audit.md`（§2.3/§2.7）、`docs/contracts/README.md`（§2.3.8 与 §2.7 覆盖声明）、`docs/contracts/schemas/experience/report.schema.json`（仅 `description`，或可选新增 `contains_blocked`/`contains_stopped`）、`docs/contracts/schemas/experience/task-card.schema.json`（若展示层需要同样的 `description` 声明）。

**迁移/兼容影响**

- 映射表与 `description`：`1.x` 兼容。
- 新增可选 `contains_blocked`/`contains_stopped`：`1.x` 兼容（`README.md` §3.3）。
- 删除 `BLOCKED`/`STOPPED` 值或重命名字段：**破坏性**，须 `2.0`，且必须等 P1-08 的 UI 词汇冻结后再评估。**本提案不主张现在做**。

**所需测试**

- `T-R03-1`（T2）：任务卡/报告 `evidence_status=UNKNOWN` 必带 `freshness`，且投影服务拒绝对 `verdict.axes` 写入 `UNKNOWN`。
- `T-R03-2`（T1）：映射表驱动测试——四张既有表 + evidence 表对每个权威值都有条目，缺项即 `UNKNOWN` 且被记录。
- `T-R03-3`（T2）：`report_scope.mode` 取值说明与实际结构一致；若采用过渡方案，`BLOCKED/STOPPED` 不被渲染为运行模式。
- `T-R03-4`（L0 文档一致性）：`README.md` 的 §2.7 覆盖声明与 §2.7 实际表数一致（脚本计数）。
- `T-R03-5`（L2 投影测试）：投影构建失败时展示“投影不可用/陈旧”，不回退旧卡片（`ui-report` §2.6）。

**是否需真实环境/用户证据**：**否（真机）**；但最终 UI 展示词汇与 `report_scope` 结构归 **P1-08 UI 冻结**，属用户/设计裁决，不是设备事实。

**状态**：`PROPOSED`；结构性部分 `BLOCKED` 于 §8 U-03（P1-08）。

---

## 5. 新确认冲突提案（C-01..C-06）

### C-01 `mode` 词汇：`static_check` vs `static`

**EVIDENCED**

- `evidence/evidence-manifest.schema.json:331-335` `$defs.mode` = `["static_check","smoke","formal"]`（顶层 `mode` 于 `:57-58` 引用它）。
- `evidence/verdict.schema.json:544-548` `$defs.mode` 同上（顶层 `mode` 于 `:54-55` 引用）。
- `evidence/report-evidence-index.schema.json:100-107` `$defs.mode` 同为 `["static_check","smoke","formal"]`。
- `domain/run.schema.json:35-37` `mode` = `["static","smoke","formal"]`；`domain/attempt.schema.json` `run_mode` 同。
- `security/job.schema.json:147` `payload.mode` = `["static","smoke","formal","diagnostics","cleanup"]`；`payload.action` = `["static_check",...]`。
- `security-node.md:879-881`（§19.2）已固定 `job.action=static_check` → `Receipt.job_kind=static_check` → **`Run.mode=static`**。
- `domain.md:599-601`（§12.3）同一映射摘要。

**PROPOSED**

1. 单一规范：**运行模式（mode）在所有层只有三个值：`static` / `smoke` / `formal`**。
2. `static_check` 只作为两个非 mode 词汇存在：`job.action` 与 `Receipt.job_kind`（静态检查作业种类）。它**不**是 `mode` 的合法值。
3. 因此 `evidence-manifest` / `verdict` / `report-evidence-index` 的 `$defs.mode` 应收敛为 `["static","smoke","formal"]`。
4. 读侧兼容（若所有者选择分阶段）：解析器可把 `static_check` 识别为 `static` 的**只读别名**，归一后入库；写出方**必须**只写 `static`。别名识别必须记录一条兼容告警，且不得反向把 `static` 写成 `static_check`。
5. 关联校验：证据 manifest/verdict 与 `Run` 关联时，比较的是归一后的 mode，**不是**原始字符串；未知 mode 一律 fail-closed（不得当成 `static`）。

**被拒绝的备选**

- **把 `Run.mode` 改成含 `static_check`**：会污染已批准的三值运行模式，并让 `Run.mode` 与 `job.action` 混为一谈，违反 `security-node.md:888` “Run.mode 仍只有 static/smoke/formal”。
- **只在文档里说明“两者不同但不影响”**：不消除误比较风险，且与 `security-node.md` §19.2 已存在的映射重复表达两种事实。

**受影响候选文件**

`docs/contracts/schemas/evidence/evidence-manifest.schema.json`、`docs/contracts/schemas/evidence/verdict.schema.json`、`docs/contracts/schemas/evidence/report-evidence-index.schema.json`、`docs/contracts/evidence-verdict.md`（§4.1 措辞 + 新增别名规则）、`docs/contracts/domain.md`（§12.3 补“证据侧 mode 归一”）、`docs/contracts/README.md`（§2.3 增补一条）。

**迁移/兼容影响**

- 删除/替换枚举成员属 `README.md` §3.4 的**破坏性变更**，理论需 `2.0` + 保留 `1.x` 只读解析器。
- 但当前 `docs/contracts/` 全体为 `frozen-candidate v1`、无已冻结修订、无已接收证据；若所有者在评审记录中把本条认定为“**首次冻结前的 v1 修正**”，则无需 `2.0`。该认定**必须显式记录**，否则按 `2.0` 处理。当前 `BLOCKED`（§8 U-04）。
- 分阶段方案（读侧别名 + 写侧唯一）可在不破坏历史解析的前提下先行，属 `1.x`。

**所需测试**

- `T-C01-1`（T2）：manifest/verdict/report-index 对 `mode="static"` 通过；对 `"static_check"` 仅在显式兼容模式下通过，且归一结果为 `static`。
- `T-C01-2`（T1）：`Run.mode`、`Attempt.run_mode`、归一后证据 mode 三者对同一静态运行相等。
- `T-C01-3`（T2）：未知 mode（如 `"diagnostics"`）在证据层被拒绝，不得落入 `static`。
- `T-C01-4`（T2 文档/schema 一致性）：三份 evidence schema 的 `$defs.mode` 完全相同；`grep static_check` 只出现在 action/job_kind 语境。

**是否需真实环境/用户证据**：**否**。

**状态**：`PROPOSED`；版本路径 `BLOCKED` 于 §8 U-04。

---

### C-02 `failure_classification` 与 `failure_class` 词表分裂

**EVIDENCED**

- `domain/run.schema.json:104-116` 与 `domain/attempt.schema.json:112-124`：`failure_classification` 为 8 个大写值（`INVALID_INPUT`、`INVALID_ENVIRONMENT`、`INVALID_EVIDENCE`、`VALID_FAILURE`、`BLOCKED`、`STOPPED`、`UNSUPPORTED`、`INFRA_ERROR`），无 `NEEDS_REVIEW`、无 `NONE`；该字段可选。
- `evidence/verdict.schema.json:599-614` `$defs.failureClass`：10 个小写值，另含 `none`、`needs-review`。
- `evidence/evidence-manifest.schema.json:592` `caseEntry.failure_class` 复用同一 10 值集合，且枚举含 `null`（见 §6 E-02）。
- `domain.md:370-383`（§9.4）给出大写值的守卫与分母影响；`evidence-verdict.md:1047-1058`（§15.1）给出小写值语义；`evidence-verdict.md:884-915`（§14.2）的派生顺序使用小写 `failure_class`。

**PROPOSED**

1. **单一权威词表**（成员集）：以 domain 8 值为权威，因为它是持久化实体字段、且 §9.4 已绑定分母规则。词表为：

   | 权威（domain `failure_classification`） | 证据投影（`failure_class`） | 含义锚点 |
   |---|---|---|
   | `INVALID_INPUT` | `invalid-input` | `domain.md` §9.4 / `evidence-verdict.md` §15.1 |
   | `INVALID_ENVIRONMENT` | `invalid-environment` | 同上 |
   | `INVALID_EVIDENCE` | `invalid-evidence` | 同上 |
   | `VALID_FAILURE` | `valid-failure` | 唯一进入正式分母的失败类 |
   | `BLOCKED` | `blocked` | 前置条件/资源/授权阻塞 |
   | `STOPPED` | `stopped` | 安全/人工停止，不是 FAIL |
   | `UNSUPPORTED` | `unsupported` | 超出 V0.0.1 范围 |
   | `INFRA_ERROR` | `infra-error` | 必须在对账确认后使用（D-C-14） |
   | （无字段 = 无失败） | `none` | 用**省略 `failure_classification`** 表达，不新增 `NONE` 值 |
   | （无字段；由五轴表达） | `needs-review` | 用 `business_verdict=NEEDS_REVIEW` + `verification_status!=PASS` 表达 |

2. **大小写定位**：大写是 **domain 持久化词表**；小写是 **verdict 产物的序列化约定**，不是第二套分类学。二者只能通过上表转换；实现必须共享**同一张机器可读映射表**（建议未来路径 `docs/contracts/mappings/failure-class.json`，由所有者决定是否建立；本提案不创建该文件）。
3. **`none` 的表达**：domain 侧不新增 `NONE`。语义为“无失败或未评估”，由 `failure_classification` 缺失 + 五轴实际值表达。理由：`domain.md` §9.4 的每个值都带“允许产生的条件”，`none` 不是一种“失败分类”。
4. **`needs-review` 的表达**：domain 侧**不**把它塞进 `failure_classification`；它是判定路由（`decision=NEEDS_REVIEW`），由 `evidence-verdict.md:905-908` 的两条派生规则（复核未过、存在未处置阻断异常）产生，在 domain 侧体现为 `business_verdict=NEEDS_REVIEW` 且 `verification_status` 不一定 `PASS`。
   - 备选（若所有者认为 domain 需要可查询的失败原因）：把 `needs-review` 映射为 domain 的 `failure_classification=BLOCKED` **并禁止**——这会丢失“待复核”与“硬阻塞”的区别，**不推荐**。
   - 备选（枚举扩展）：向 domain 增加 `NEEDS_REVIEW` 值，属 `README.md` §3.6 的兼容扩展（`1.x`）。若所有者选此路径，必须同时说明它不进入正式分母（与 `evidence-verdict.md:1058` 一致）。
5. **跨层禁止透传**：报告/UI 不得直接透传任一层的原始词串；必须先归一为显示词汇（见 R-03 五轴投影），且 `needs-review`/`none` 不得显示为失败类计数。
6. **未知值**：任一层出现表外值 → fail-closed，标 `NEEDS_REVIEW`，不得猜测为 `valid-failure` 或 `none`。

**被拒绝的备选**

- **把 domain 改成小写**：改的是持久化实体字段，破坏面最大（P0-04 实体 + P0-07 报告 + 未来迁移），收益仅是对齐序列化风格。
- **把 verdict 改成大写并删除 `none`/`needs-review`**：会让 `decision=NEEDS_REVIEW`/`PASS` 失去失败类表达，且 `evidence-verdict.md` §14.2 的 13 步派生顺序全部要改。

**受影响候选文件**

`docs/contracts/domain.md`（§9.4 增补“与证据侧映射”与 `needs-review` 表达）、`docs/contracts/evidence-verdict.md`（§15.1 增补映射列/说明）、`docs/contracts/schemas/domain/run.schema.json`、`attempt.schema.json`（仅当选择枚举扩展时改枚举，否则仅 `description`）、`docs/contracts/schemas/evidence/verdict.schema.json`、`evidence-manifest.schema.json`（`description`；若选统一大小写则改枚举）、`docs/contracts/README.md`（§2.3 增补一条）。

**迁移/兼容影响**

- 纯映射表 + `description`：`1.x` 兼容，不改变任何已存在值的解释。
- 统一大小写或删除 `none`/`needs-review`：破坏性，需 `2.0` 或“首次冻结前 v1 修正”裁定。
- 向 domain 增加 `NEEDS_REVIEW`：兼容扩展（`1.x`），但需分母说明。

**所需测试**

- `T-C02-1`（T2 映射表双向）：8 个权威值 ↔ 8 个投影值一一对应；`none` 与 `needs-review` 无 domain 对应，且转换函数对它们返回“无字段/由五轴表达”而不是抛错。
- `T-C02-2`（T1 派生）：`decision=NEEDS_REVIEW` 时 domain 侧不出现 `failure_classification=VALID_FAILURE`；`business_verdict=NEEDS_REVIEW` 且 `failure_classification` 缺失时，报告不显示“失败类”。
- `T-C02-3`（T2 fail-closed）：表外值（如 `"timeout"`）→ `NEEDS_REVIEW`，不进入正式分母。
- `T-C02-4`（T1 分母）：`valid-failure` ↔ `VALID_FAILURE` 仍计入正式分母；其余 7 值不计入。
- `T-C02-5`（L0）：`grep` 检查两份契约的 8 个成员集完全相同（大小写归一后）。

**是否需真实环境/用户证据**：**否**。

**状态**：`PROPOSED`；`needs-review` 表达方式 `BLOCKED` 于 §8 U-05。

---

### C-03 线协议 `lease.state` 缺少领域 `Lease.state` 映射

**EVIDENCED**

- `security/lease.schema.json:135-137` `payload.state` = `granted / renewed / released / expired / revoked / reclaimed`。
- `domain/lease.schema.json:51-54` 与 `domain.md:441` `Lease.state` = `GRANTED / HELD / RELEASING / RECLAIM_PENDING / RELEASED / QUARANTINED`。
- `security-node.md:858-871`（§19）只写“字段对齐但不互相替代”；§19.2 只给 `receipt.status` 与 action/mode 映射，**没有** lease.state 映射。
- `domain.md:455-474`（§11.2）给出领域状态机与守卫；`thresholds.md:141/406` 明确 `expired` 仅是续约截止事实。
- `evidence-verdict.md:785-800`（§13.1）已存在“细化 `state` → `occupancy_state`”投影，但那是**证据侧**细化状态，不是线协议 `lease.state`。

**PROPOSED**（固定映射 + 守卫 + 未知值规则）

| 线协议 `lease.state` | 领域 `Lease.state` | `occupancy_state` | 守卫/说明 |
|---|---|---|---|
| `granted` | `GRANTED` | `OCCUPIED` | 仅表示控制面已授予；节点确认领取（`domain.md` §11.2 `GRANTED→HELD` 守卫）后才 `HELD`，该确认不是线协议状态值。 |
| `renewed` | `HELD` | `OCCUPIED` | 只延长 `expires_at`。若当前为 `RECLAIM_PENDING`，**保持** `RECLAIM_PENDING`，直到补传/去重/对账完成（B5）；`renewed` 本身不恢复 `HELD`。 |
| `released` | `RELEASING` →（守卫通过后）`RELEASED` | `OCCUPIED` → `IDLE` | 线协议 `released` 只是**释放主张**。只有 `release_preconditions` 三项全 `true`（`domain.md` §11.2）才落 `RELEASED`；否则保持 `RELEASING` + `LEASE_RELEASE_PRECONDITION_FAILED`，占用保持 `OCCUPIED`。 |
| `expired` | **不降级、不升级**：`GRANTED`→`GRANTED`；`HELD` 且通信 `ONLINE`→`HELD`；`HELD` 且通信 `STALE`/`OFFLINE`→`RECLAIM_PENDING` | `OCCUPIED` | **永不**映射到 `RELEASED`/`IDLE`、不判 run 失败、不重派（B4；`thresholds.md` D-TH-01）。`GRANTED` 未经领取确认不得因 `expired` 变成 `HELD`。 |
| `revoked` | `RELEASING` | `OCCUPIED` | 对应 `stop_policy.on_explicit_revoke=stop_safe`：先 STOP-first 安全停止；清理失败/安全事件 → `QUARANTINED`（见下行）。 |
| `reclaimed` | `RECLAIM_PENDING` | `OCCUPIED` | 表示控制面发起回收；最终进入 `HELD`（对账后确认仍持有）或 `RELEASING`（确认停止+清理+对账）；**不得**直接跳 `RELEASED`。 |
| 表外值 | **不改变当前状态** | 保持原值 | 记录审计 + 告警；不停止已启动 run、不释放、不重派；该租约不得用于新派发，直到人工确认。 |

补充规则（写入 `security-node.md` §19.2 或 §10.2 与 `domain.md` §11.2 交叉引用）：

1. `revoked` 与安全事件导致清理失败/设备失控时，领域状态可为 `QUARANTINED`；`QUARANTINED` **没有**线协议对应值，只能由控制面在审计后写入。
2. 任何映射都**不得**绕过 STOP-first 重连顺序（B5）：`revoked`/`reclaimed` 在重连未完成对账前只能停留在 `RELEASING`/`RECLAIM_PENDING`。
3. 映射只在控制面生效；节点**不得**自行把线协议状态映射为领域状态（沿用 `security-node.md:889` 的同一条原则）。
4. 映射表必须在 `security-node.md` §19.2、`domain.md` §11.2/§12.3、`evidence-verdict.md` §13.1 三处保持一致，不得出现第二套取值。

**被拒绝的备选**

- **给领域增加 `RENEWED`/`EXPIRED`/`REVOKED`/`RECLAIMED` 六个同名状态**：会把“传输事实”和“所有权事实”合并，直接违反 B4（到期≠所有权到期）与 §19“协议消息不替代领域实体”。
- **`released → RELEASED` 无条件直通**：会让线协议消息单方面突破三项释放前置条件（B6），并使“缺 cleanup 回执仍保持占用”失效。

**受影响候选文件**

`docs/contracts/security-node.md`（§19.2 增补 lease 映射表 + §10.2 引用）、`docs/contracts/domain.md`（§11.2 增补接收侧规则）、`docs/contracts/evidence-verdict.md`（§13.1 增补“与线协议 lease.state 的关系”交叉引用）、`docs/contracts/README.md`（§2.3 增补一条）。**不修改** `lease.schema.json` 枚举。

**迁移/兼容影响**

- 纯文档映射：`1.x` 兼容；不改变现有 schema。
- 若进一步把 `released` 的落库行为收紧为“必须三项前置条件”，属**行为收紧**（实现层面），不改变契约字段；需在 P2-02/P2-04 方案中体现，不属本提案可授权范围。
- 若未来给 `domain/lease.schema.json` 增加 `QUARANTINED → occupancy_state=OCCUPIED` 的 `allOf` 约束（见 C-05），属收紧 → 需版本裁定。

**所需测试**

- `T-C03-1`（T2 表驱动）：6 个线协议值各生成期望领域状态；在 `HELD` 前提下，`expired` 于 `ONLINE` 与 `STALE`/`OFFLINE` 分别断言 `HELD` / `RECLAIM_PENDING`；在 `GRANTED` 前提下断言 `expired` 不升级为 `HELD`；`occupancy_state` 恒为 `OCCUPIED`。
- `T-C03-2`（T1 守卫）：`released` 但 `release_preconditions` 任一为 `false` → 停在 `RELEASING`，返回 `LEASE_RELEASE_PRECONDITION_FAILED`。
- `T-C03-3`（T1 离线续跑）：`expired` + run `RUNNING` → run 状态不变、`execution_permit` 不变、设备不重派（回归 B4）。
- `T-C03-4`（T2 fail-closed）：表外值不改变状态、不释放、不派发，且产生审计事件。
- `T-C03-5`（L3/L4 真机）：`revoked` 期间设备实际停止与释放时序符合 STOP-first；**需真机窗口**，故本条只能登记为后续验证，不能在本提案阶段执行。

**是否需真实环境/用户证据**：映射与守卫**否**；`revoked`/`reclaimed` 的实际设备释放时序验证属 **L3/L4，需真机**（§8 U-06）。

**状态**：`PROPOSED`；行为验证 `BLOCKED` 于真机与 A-0。

---

### C-04 端点类型词汇不一致

**EVIDENCED**

- domain 侧（kind）：`domain/device.schema.json:63`、`domain/lease.schema.json:39`、`domain/execution-bundle.schema.json:145` = `audio_capture / audio_playback / serial / usb / gpio`。
- security 侧（`endpoints[].kind`）：`security/lease.schema.json:191`、`security/heartbeat.schema.json:209` = `audio_input / audio_output / serial / usb / network / display`。
- security 侧**第三种**变体（capabilities）：`security/node-identity.schema.json:152`、`security/node-enrollment.schema.json:149` = `audio_capture / audio_playback / serial / usb / network / display`。
- `security/job.schema.json:408`（`evidence_policy.required_kinds`）与 `security/receipt.schema.json:436`（artifacts）使用 `audio_capture`。
- `security/lease.schema.json:113-120`：`payload.endpoint_set` 的 items 为 `^endpoint_[0-9a-f]{32}$`，即**端点标识**；`domain/lease.schema.json:33-39` 的 `endpoint_set` 是**kind 枚举**。`domain.md:478`（L-1）与 `evidence-verdict.md` 的占用键 `(node_id, device_id, endpoint_set)` 因此存在“标识 vs 类别”的层级混用（见 §6 E-03）。
- `security-node.md` §10.2/§10.3 未解释该差异。

**PROPOSED**

1. **拆分两个概念**（这是本条的核心，不只是改名）：
   - `endpoint_kind` = 能力类别，用于能力匹配、`required_kinds`、租约资格判断。规范集合：`audio_capture / audio_playback / serial / usb / gpio`（domain 侧为准）。
   - `endpoint_set` = **端点身份集合**，用于占用键与证据归属。元素必须是稳定 `endpoint_id`（对应 `domain/device.schema.json` 的 `endpoint_id` 与线协议 `endpoint_<32hex>`），**不得**是 kind。
2. **音频 kind 归一**：`audio_input → audio_capture`、`audio_output → audio_playback`，1:1 双向映射；**domain 词汇为权威**，线协议旧词只作为**入站别名**接受，入域前立即归一；写出方必须只发权威词。
3. **`network` / `display`**：仅作为**节点能力标识**保留；在 V0.0.1 中**不**作为可占用 endpoint kind，除非 T-10 真实端点清单证实存在可占用实例。若确认存在，按 `README.md` §3.6 走兼容枚举扩展（`1.x`）。
4. **`gpio`**：domain 有、wire 无。V0.0.1 先按“domain 能力标识，不可占用”处理；新增线协议值同样需 T-10 事实。
5. **未知 kind / 未知端点身份**：fail-closed，不得授予占用、不得生成租约、不得把未知 kind 归入任一已知类别。
6. **占用键**：明确 `(node_id, device_id, endpoint_set)` 的 `endpoint_set` 为 `endpoint_id` 集合；kind 不参与占用键（否则同设备同类两个端点会被误判为同一占用）。

**被拒绝的备选**

- **在线协议侧统一改成 `audio_capture/audio_playback`（一次性换枚举）**：会改动 4 个 security schema 的枚举，且 `lease.endpoint_set` 的标识语义问题仍未解决。
- **在 API 边界做“kind 字符串替换”而不拆分概念**：会把 `endpoint_set` 继续当作 kind 集合使用，占用键仍然无法区分同类多端点。

**受影响候选文件**

`docs/contracts/security-node.md`（§10.2/§10.3/§19.2）、`docs/contracts/domain.md`（§11.1/§11.3 端点语义 + L-1 键定义）、`docs/contracts/evidence-verdict.md`（§13.1 占用键说明）、`docs/contracts/schemas/security/lease.schema.json`、`heartbeat.schema.json`、`node-identity.schema.json`、`node-enrollment.schema.json`（枚举或 `description`）、`docs/contracts/schemas/domain/lease.schema.json`、`device.schema.json`、`execution-bundle.schema.json`（若采纳“endpoint_set = id 集合”则结构变更）、`docs/contracts/README.md`（§2.3 增补一条）。

**迁移/兼容影响**

- **最小方案（推荐先行）**：只写别名归一表 + 明确“endpoint_set 是身份集合”，schema 不动 → `1.x` 文档级。
- **统一枚举**：删除 `audio_input/audio_output`、或新增 `gpio` → 破坏性或兼容扩展，取决于是“删除旧值”还是“新增值”，须版本裁定。
- **把 domain `endpoint_set` 从 kind 枚举改为 `endpoint_id` 字符串**：**破坏性**（改类型/含义），需 `2.0` 或 v1 修正；会直接影响未来迁移与索引设计（P2-02）。
- 任何一项都**不得**改变 B4/B6：端点未释放不阻止“停止+清理+对账”的释放判定，但端点身份必须一致才能完成对账。

**所需测试**

- `T-C04-1`（T2 别名表）：`audio_input↔audio_capture`、`audio_output↔audio_playback` 双向；未知 kind 拒绝。
- `T-C04-2`（T1 占用键）：同一设备两个 `audio_capture` 端点（不同 `endpoint_id`）不产生 `LEASE_CONFLICT`；只有 `endpoint_id` 重叠才冲突。
- `T-C04-3`（T2）：写出侧只产生权威词（对 security 4 份 schema 的 writer 样例做负例断言）。
- `T-C04-4`（T2）：`job.evidence_policy.required_kinds` 与 receipt artifacts 的 kind 值域与 domain 能力类一致。
- `T-C04-5`（L3/L4，真机）：真实设备的音频/串口/GPIO 端点清单与命名；**需 T-10**。

**是否需真实环境/用户证据**：**部分是**。枚举归一与占用键定义**否**；`network`/`display`/`gpio` 是否属于 V0.0.1 可占用端点、真实端点清单与命名**必须由 T-10 真机事实确认**（§8 U-07）。

**状态**：`PROPOSED`；`network/display/gpio` 范围 `BLOCKED` 于 T-10。

---

### C-05 设备占用枚举命名分歧（SR-14）

**EVIDENCED**

- `domain.md:442/499/502` 与 `domain/lease.schema.json`、`device.schema.json`：`occupancy_state` = `IDLE / OCCUPIED / RELEASING`；`pool_state` 独立 8 值（`DISCOVERED/READY/RESERVED/ATTACHED/DRAINING/QUARANTINED/OFFLINE/RETIRED`）；`Lease.state` 6 值。
- `docs/v2/SOLUTION.md:533` 与 `openspec/changes/ai-test-platform-v2/README.md` 规范同步说明第 2 条：设备占用写为 `OCCUPIED / RELEASING / RELEASED / QUARANTINED`（四值）。
- `evidence/device-occupancy.schema.json` 另有 10 个细化 `state` 值，并通过 §13.1 投影到三值 `occupancy_state`。
- `docs/delivery/source-reconciliation.md` SR-14 登记为“已登记（不阻断）”，处置写为“P0-04/P0-06 契约冻结时统一枚举”。

**PROPOSED**

明确三层，并只允许一层权威：

| 层 | 内容 | 权威性 |
|---|---|---|
| L1 权威 | `Lease.state`（6 值）+ `Device.pool_state`（8 值）+ `release_preconditions` | 唯一事实源 |
| L2 粗投影 | `occupancy_state` ∈ {`IDLE`,`OCCUPIED`,`RELEASING`} | 派生，服务端写入 |
| L3 展示/历史 | `docs/v2`/`openspec` 的四值枚举；`device-occupancy.state` 的 10 值细化 | 展示/证据细化，不是新权威 |

1. **四值枚举降级**：`RELEASED` 与 `QUARANTINED` **不是** occupancy 值。`RELEASED` 属 `Lease.state`/`device-occupancy.release_state`；`QUARANTINED` 属 `Device.pool_state`/`Lease.state`。
2. **四值 → 三值/权威的固定投影**（供 `docs/v2`/`openspec` 回写用）：
   - `OCCUPIED → OCCUPIED`
   - `RELEASING → RELEASING`
   - `RELEASED → IDLE` **仅当**三项 `release_preconditions` 全 `true` 且 `device-occupancy.release_state=released`；否则 `OCCUPIED`（视为 `held_pending_cleanup`）
   - `QUARANTINED → occupancy_state=OCCUPIED`（不可再分配）+ `pool_state=QUARANTINED` + `Lease.state=QUARANTINED`
3. **补一条 `QUARANTINED` 不变量**（候选）：`Lease.state=QUARANTINED` 时 `occupancy_state` 必须为 `OCCUPIED`。依据 `evidence-verdict.md:790`（`quarantined → OCCUPIED`）与“不可再分配”语义。注意这是**收紧**，见兼容影响。
4. **`docs/v2`/`openspec` 回写**：在 SR-14 关闭前，禁止声称“占用枚举已统一”。回写属 P0-03 后续文档同步，不得在本次提案中执行。
5. **禁止新增第四值**：任何“已释放”“已隔离”的展示需求，必须从 `Lease.state`/`pool_state`/`release_state` 取，不得扩展 `occupancy_state`。

**被拒绝的备选**

- **把 `occupancy_state` 扩成四值以迁就 `docs/v2`**：会把“释放确认”和“隔离”压进占用枚举，违反 B6（释放/证据/判定分离）与 `domain.md` D-5（`QUARANTINED` 属池状态、需人工授权恢复）。
- **保留四值并只写“语义等价”**：SR-14 仍然开放，实现会按旧四值建表/建枚举。

**受影响候选文件**

`docs/contracts/domain.md`（§11.2/§11.3 增补投影与不变量）、`docs/contracts/evidence-verdict.md`（§13.1 增补“四值历史词 → 三值”说明）、`docs/contracts/schemas/domain/lease.schema.json`（若采纳收紧则不变量）、`docs/contracts/README.md`（§2.3 增补）、`docs/delivery/source-reconciliation.md`（SR-14 处置说明，属后续同步）、`docs/v2/SOLUTION.md`、`openspec/.../README.md`（后续回写，本次不改）。

**迁移/兼容影响**

- 投影表与历史词说明：`1.x` 兼容。
- 新增 `QUARANTINED → OCCUPIED` 的 `allOf` 约束：**收紧**，现有合法对象若把隔离设备标为 `IDLE` 会变非法；须版本裁定（§8 U-08）。
- `docs/v2`/`openspec` 回写：不改变契约效力，但属“阶段门后同步”范畴，须在 P0-03 后续批次执行并留记录。

**所需测试**

- `T-C05-1`（T2）：`occupancy_state` 只接受三值；出现 `RELEASED`/`QUARANTINED` 即失败。
- `T-C05-2`（T1 投影）：四值历史词按上表投影；`RELEASED` 在 `release_preconditions` 不全时投影为 `OCCUPIED`。
- `T-C05-3`（T2 不变量，若采纳）：`Lease.state=QUARANTINED` → `occupancy_state=OCCUPIED`。
- `T-C05-4`（L0 文档一致性）：`grep` 断言 `docs/v2`/`openspec` 已带“四值为历史/兼容词”标注，且 SR-14 状态与实际一致。

**是否需真实环境/用户证据**：**否**。

**状态**：`PROPOSED`；SR-14 关闭 `BLOCKED` 于契约所有者 + 文档同步批次（§8 U-08）。

---

### C-06 evidence manifest `case_version` 类型不一致

**EVIDENCED**

- `evidence/evidence-manifest.schema.json:551-553` `$defs.caseEntry.case_version` = `"type": "string"`。
- `evidence/verdict.schema.json:696-698` `$defs.caseResult.case_version` = `"type": "string"`（审计原文只列 manifest，此处为**范围补充**，见 §6 E-01）。
- `domain/case.schema.json:32`、`domain/attempt.schema.json:34`、`domain/revision.schema.json:106` 均为 `integer, minimum 1`。
- `domain.md:284`（`Case.case_version` integer ≥1）、`domain.md:353`（`Attempt.case_version` integer）。
- `evidence-verdict.md:204` 示例写 `"case_version": "1"`（字符串）。
- `domain.md:769` 的 `CASE_CONTENT_MISMATCH` 依赖 `case_version` 与摘要一致——类型不一致会削弱该守卫。

**PROPOSED**

1. **唯一权威类型**：`case_version` 在所有层为 **`integer ≥1`**。理由：它是比较/递增/连接键（`run_id + case_id + case_version + attempt`），且 domain 三个实体已一致。
2. **证据侧改造**：`evidence-manifest` 与 `verdict` 的 `case_version` 改为 `integer, minimum 1`；`evidence-verdict.md` §5 示例改为 `1`。
3. **展示投影**：若 UI/报告需要字符串展示，只能是**展示期格式化**（`String(case_version)`），不得持久化；如确需持久化标签，必须用**独立字段**（如 `case_version_label`）且标注“非连接键、不得反解析”。
4. **兼容读入（过渡期，条件性）**：只有在显式兼容模式下，读取方可接受符合 `^[1-9][0-9]{0,8}$` 的字符串并归一为整数，同时记录一条 `legacy_case_version_coerced` 告警；必须拒绝 `"0"`、`"01"`、`"1.0"`、`"+1"`、`" v1 "` 等任何非规范十进制。
5. **禁止隐式转换**：默认严格模式拒绝字符串；不得在比较/排序/哈希前静默 `parseInt`。
6. **一致性守卫**：`verdict.cases[].case_version` 必须与对应 `attempt.case_version` 整数相等；不相等 → `CASE_CONTENT_MISMATCH`。

**被拒绝的备选**

- **把 domain 改成 string**：`case_version` 参与递增与 `supersedes_case_version` 比较（`case.schema.json:103-120`），字符串会引入排序/前导零歧义，且破坏三处已一致的类型。
- **保留两套类型并写“仅展示投影”**：`verdict.cases` 是判定产物而非纯展示，仍会被消费者当连接键使用；风险不消失。

**受影响候选文件**

`docs/contracts/schemas/evidence/evidence-manifest.schema.json`、`docs/contracts/schemas/evidence/verdict.schema.json`、`docs/contracts/evidence-verdict.md`（§5.1 示例 + §14/§15 相关示例）、`docs/contracts/README.md`（§2.3 增补一条）、`docs/contracts/domain.md`（§8 增补“证据侧必须为整数”）。若存在其他 evidence 产物引用（`report-evidence-index`），一并核对。

**迁移/兼容影响**

- `string → integer` 属 `README.md` §3.4 的**破坏性变更**（改类型），理论需 `2.0` + 保留 `1.x` 只读解析器。
- 因无已冻结修订/已接收证据，所有者可认定为“首次冻结前 v1 修正”；**必须显式记录**（§8 U-09），否则按 `2.0`。
- 兼容读入只用于历史产物回放，不得成为写入路径；须有开关与审计。

**所需测试**

- `T-C06-1`（T2）：`case_version: 1` 通过；`"1"` 在严格模式失败；在兼容模式通过且归一为 `1`。
- `T-C06-2`（T2 负例）：`"0"`、`"01"`、`"1.0"`、`"+1"`、`" 1 "`、`1.5` 全部失败。
- `T-C06-3`（T1 连接键）：`verdict.cases[].case_version` 与 `attempt.case_version` 整数相等；`"1"` vs `1` 不得被判为相等后再继续。
- `T-C06-4`（T1 追溯）：`run_id + case_id + case_version + attempt` 复合键在跨 manifest/verdict/attempt 三处一致。
- `T-C06-5`（L0）：`grep case_version` 在所有契约中只剩整数类型与展示说明。

**是否需真实环境/用户证据**：**否**。

**状态**：`PROPOSED`；版本路径 `BLOCKED` 于 §8 U-09。

---

## 6. 只读范围补充（扩大受影响文件，但不是新提案）

以下 5 项为本次复读时新确认的事实，审计原文未列出或只部分列出。它们不单独构成第 10 项提案，但必须并入对应条目的文件清单，否则提案会漏改。

| ID | 事实（EVIDENCED） | 并入 | 影响 |
|---|---|---|---|
| E-01 | `evidence/verdict.schema.json:696-698` 的 `caseResult.case_version` 同样是 `string` | C-06 | 若不改，manifest 改完仍会在 verdict 侧断开；verdict 是判定产物，风险高于 manifest |
| E-02 | `evidence-manifest.schema.json:592-614` 的 `failure_class` 枚举含 `null`，而 `verdict.$defs.failureClass` 不含 | C-02 | 需明确 `null` 的语义（建议等价于“省略”，即 `none`），否则同一字段在三处有三种可空性 |
| E-03 | `security/lease.schema.json:113-120` 的 `endpoint_set` 是 `endpoint_<32hex>` 标识集合；`domain/lease.schema.json:33-39` 是 kind 枚举 | C-04 | 占用键 `(node_id, device_id, endpoint_set)` 在两层的元素语义不同，比“词汇不一致”更严重 |
| E-04 | `evidence-verdict.md:713-723`（§12.1.1）映射表未列 `cleanup_status` 与 `notes`，但两者在 domain/security 投影中分别必填/可选 | R-02 | “最小投影 → 权威回执”映射不完整；消费方无法据表还原 `cleanup_status` |
| E-05 | `security/receipt.schema.json:231-264` 的 `error.code` 是节点侧独立闭集（`SCHEMA_INVALID`/`ARTIFACT_MISMATCH`/…），`additionalProperties: false`，无 `subject`，也不含控制面 `SCHEMA_VERSION_UNSUPPORTED` | R-01 | 不能假定“错误载荷有 subject”或“控制面错误码可直接用于回执”；两套错误词表需显式映射 |

补充说明：

- E-01 与 E-03 会**扩大**兼容影响：E-01 使 C-06 的改动面从 1 个 schema 变 2 个；E-03 使 C-04 从“词表对齐”变为“身份模型对齐”，可能触及 P2-02 的索引/唯一约束设计（本提案不做该设计）。
- E-02 的 `null` 若被解释为“不适用”，会与 C-02 的 `none` 表达冲突；本提案建议统一为“`null` ≡ 省略 ≡ 无失败”，并在 C-02 的映射表中显式写一行。
- E-04 属“文档漏项”，修正成本最低，但没有所有者裁决前不得改写 `docs/contracts`。
- E-05 让 R-01 的错误表达只能走“复用节点侧已有码 + `facts` 键”或“枚举扩展”，不存在第三条捷径；它同时提示节点/控制面错误码映射本身是后续待登记项（不在本次 9 项内）。

---

## 7. 建议的裁决与实施批次（不构成授权）

即使全部被接受，也应分批处理，避免一次改动横跨过多契约而无法复核。批次只是**建议顺序**，不代表已排期。

| 批次 | 内容 | 理由 | 前置 |
|---|---|---|---|
| B-0（纯文档，零 schema 结构变更） | R-01、R-02、C-03 映射表、C-05 投影说明、E-04 补行 | 不改枚举/类型，风险最低，可先消除“读者误判”风险 | 所有者 U-01 |
| B-1（schema `description` + 文档表） | R-03 的 `UNKNOWN` 声明与 evidence 映射表；C-02 映射表；C-01 的“读侧别名”规则 | 只加说明与映射，不改成员集 | B-0；R-03 结构部分需 P1-08 |
| B-2（枚举/类型变更，需版本裁定） | C-01 收敛 `$defs.mode`、C-06 `case_version` 改整数、C-04 统一 kind、C-05 加 `QUARANTINED` 约束 | 均属破坏性或收紧，必须走 `README.md` §3.4 或“首次冻结前 v1 修正”裁定 | U-04/U-07/U-08/U-09 |
| B-3（跨文档回写） | `docs/v2`/`openspec` 四值枚举标注、SR-14 关闭、`source-reconciliation.md` 状态更新 | 属 P0-03 后续同步，不是契约变更 | B-2 定案 + 文档同步批次 |

**不建议**把 B-0 与 B-2 合并：B-2 会触发版本路径争议，若与低风险文档修正绑在一起，会让整个提案无法先落地。

---

## 8. 明确仍未最终确定的事项（Non-final Decisions）

以下事项在本提案中**全部未定**。任何一项在关闭前，本文件都不得被称为“已解决”“已冻结”或“已批准”。

### 8.1 所有者裁决类（9 项）

| ID | 未决事项 | 为什么现在不能定 | 谁来决定 | 关闭后解锁 |
|---|---|---|---|---|
| U-01 | R-01..R-03、C-01..C-06 全部提案是否接受、部分接受或否决 | 契约仍为 `frozen-candidate v1`；本文件只是提案，无评审效力 | Orchestrator / 契约所有者（P0-04..P0-08） | 任何后续契约编辑 |
| U-02 | R-01 的错误表达：控制面复用 `SCHEMA_VERSION_UNSUPPORTED` + 节点侧 `SCHEMA_INVALID` + `facts` 两键，还是扩展节点 `error.code` 闭集 | 节点侧 `error.code` 是独立闭集且无 `subject`（E-05）；扩展枚举虽兼容但会增加长期词表 | P0-04/P0-05 所有者 | R-01 定稿 |
| U-03 | R-03 的最终 UI 投影词汇与 `report_scope` 结构（保留四值过渡 vs 拆出 `contains_blocked/stopped`） | 属 UI 词汇冻结，依赖 P1-08；本文件无权替 UI 决定 | P1-08 + P0-07 | R-03 结构部分 |
| U-04 | C-01 走 `2.0`、`1.x` 读侧别名，还是“首次冻结前 v1 修正” | 影响版本号、历史解析器保留策略与未来迁移 | P0-04/P0-06 + 版本规则责任人 | C-01 定稿 |
| U-05 | C-02 中 `needs-review` 的 domain 表达：省略 + 五轴 vs 新增 `NEEDS_REVIEW` 枚举值 | 两种方案对分母查询与报告口径影响不同 | P0-04 + P0-07 | C-02 定稿 |
| U-06 | C-03 中 `revoked`/`reclaimed` 的最终落点（`RELEASING` vs `QUARANTINED` 的判定阈值） | 涉及安全事件与设备失控的实际处置口径 | P0-04 + 安全责任人 | C-03 行为实现 |
| U-07 | C-04 中 `network`/`display`/`gpio` 是否属于 V0.0.1 可占用端点 | 只有真实设备端点清单能确认；文档不能替真机事实 | T-10 + A-0 环境准入 | C-04 枚举定稿 |
| U-08 | C-05 是否把 `QUARANTINED → occupancy_state=OCCUPIED` 写成 schema 约束 | 属收紧，会改变现有合法对象集合 | P0-04 + 版本责任人 | C-05 schema 定稿 |
| U-09 | C-06 的版本路径（`2.0` vs v1 修正）与兼容读入开关是否保留 | 改类型属破坏性；保留兼容读会引入长期分支 | P0-04/P0-06 + 版本责任人 | C-06 定稿 |

### 8.2 外部事实 / 阶段门阻塞类（5 项）

| ID | 未决/阻塞 | 为什么不能由本提案关闭 | 所需输入 | 关联 |
|---|---|---|---|---|
| U-10 | 真机端点能力与命名（C-04 部分） | 实际有哪些音频/串口/GPIO 端点、如何命名，只能由设备事实确认 | T-10 设备型号/固件/端点清单；A-0 | `p0-09-decision-reconciliation.md` |
| U-11 | `revoked`/`reclaimed` 的 L3/L4 真机时序验证（C-03 部分） | 需要真实节点与设备执行 STOP/释放 | T-09/T-10；真机窗口 | `environment-inputs.md` |
| U-12 | P1 UI 候选核验与 P1-08 冻结（R-03 依赖） | 独立核验 `ui-candidate-verification.md` 缺失；UI 词汇未冻结 | 独立核验 PASS、P1-05..P1-08 | `restart-handoff-20261029.md` |
| U-13 | Phase 0 归档 open-blocker T-23 | Phase 0 关闭不由本提案决定；本提案也不能替代归档评审 | Orchestrator 指定负责人 | `phase2-input-map.md` §13.3/§13.4 |
| U-14 | `docs/v2`/`openspec` 四值枚举与 SR-14 回写 | 属 P0-03 后续文档同步批次，且 SR-14 关闭需契约冻结为前提 | 契约冻结 + 同步批次 | `source-reconciliation.md` SR-14 |

### 8.3 本文件明确不主张的事项

1. 本文件**不**主张 9 项提案已被接受、已冻结、已批准或已实现。
2. 本文件**不**主张 Phase 0 可关闭、A-0 可通过、Phase 2 可启动。
3. 本文件**不**主张任何 UI 词汇已定稿；R-03 的展示词汇仍归 P1-08。
4. 本文件**不**主张 `docs/v2`/`openspec` 的旧四值枚举已失效；只登记“应在冻结时统一”，并保留 SR-14 开放状态。
5. 本文件**不**提供实现方案、DDL、OpenAPI、迁移脚本或测试代码；§3/§4/§5 的测试项只是候选验收输入，不是已编写测试。

---

## 9. 只读复现与自检

```bash
cd /home/bszheng/NoahsArk

# 本文件存在且非空
test -s docs/delivery/contract-resolution-proposal.md && wc -l docs/delivery/contract-resolution-proposal.md

# R-01 证据
grep -n "noahsark.execution-bundle/v1" docs/contracts/schemas/security/job.schema.json
grep -n '"schema_version".*"1.0"' docs/contracts/schemas/domain/execution-bundle.schema.json

# R-02 证据
grep -n "operational_detail" docs/contracts/schemas/security/receipt.schema.json docs/contracts/schemas/domain/receipt.schema.json
grep -n "同一最小释放投影" docs/contracts/README.md

# R-03 证据
sed -n '194,243p' docs/contracts/ui-report-knowledge-audit.md
grep -n "occupancy/communication/gate/run/evidence" docs/contracts/README.md

# C-01 / C-06：枚举与类型总表
python3 - <<'PY'
import json
for p in [
 "docs/contracts/schemas/evidence/evidence-manifest.schema.json",
 "docs/contracts/schemas/evidence/verdict.schema.json",
 "docs/contracts/schemas/evidence/report-evidence-index.schema.json",
 "docs/contracts/schemas/domain/run.schema.json",
 "docs/contracts/schemas/domain/attempt.schema.json",
]:
    s=json.load(open(p)); print("==",p)
    print("  $defs.mode =", s.get("$defs",{}).get("mode"))
    for k,v in s.get("$defs",{}).items():
        if isinstance(v,dict) and "case_version" in v.get("properties",{}):
            print("  ",k,"case_version =", v["properties"]["case_version"])
        if isinstance(v,dict) and "failure_class" in v.get("properties",{}):
            print("  ",k,"failure_class =", v["properties"]["failure_class"])
PY

# C-03 / C-04 / C-05 证据
grep -n "granted\|renewed\|reclaimed" docs/contracts/schemas/security/lease.schema.json
grep -rn "audio_input\|audio_output" docs/contracts/schemas/
grep -rn "audio_capture\|audio_playback" docs/contracts/schemas/domain/
grep -n "occupancy_state" docs/contracts/domain.md

# R-01 / E-05：节点侧错误码闭集（无 subject）
sed -n '231,264p' docs/contracts/schemas/security/receipt.schema.json

# 工作区白检（不提交）
git diff --check
git status --short
```

预期：文件存在且非空；上述 `grep` 命中与本文引用行号一致；`git diff --check` 无输出。

---

## 10. 非声明

- 本文件是**非权威提案稿**，不是契约评审结论、不是冻结记件、不是批准记件。
- 本文件未修改 `docs/contracts/`、任何 schema、`.omo` 计划、`plan.md`、`docs/v2`、`openspec`、UI 文件、产品代码、迁移或 OpenAPI。
- 本文件不包含密钥、凭据、真实节点值、真实设备序列号或原始证据。
- 本文件不构成实现、测试、部署、验收或发布授权；不关闭 Phase 0，不启动 Phase 2，不替代 Phase 1 的串行 UI 工作。
- 本文件未提交（commit）或推送（push）。

---

**路径**：`docs/delivery/contract-resolution-proposal.md`
**提案数**：9（R-01..R-03、C-01..C-06）+ 5 项只读范围补充（E-01..E-05）
**未决/阻塞**：9 项所有者裁决（U-01..U-09）+ 5 项外部/阶段门阻塞（U-10..U-14）
