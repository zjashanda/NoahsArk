# 契约残余与事实源冲突跟进审计（Contract Residual Follow-up）

- 审计日期：2026-10-29
- 审计性质：**只读审计 + 建议**，不是契约评审、不是冻结、不是批准，不构成实现、测试、部署、验收或发布授权。
- 审计范围：`docs/contracts/`（README、domain、security-node、evidence-verdict、ui-report-knowledge-audit、thresholds 及 35 个 schema）、Phase 0 整改复验、事实源对账、来源对账、已评审验收/测试草案、交付主计划与施工进度。
- 候选契约状态：全部仍为 `frozen-candidate v1`（`thresholds.md` 为 `thresholds-v1` 候选）；`docs/contracts/README.md` §2.3 明确“仍需 Orchestrator 评审确认”。本审计把这些契约当作**非最终**对象处理。
- 输出边界：本文件只登记残余、证据与建议，不修改任何契约、schema、`.omo`、`plan.md`、`docs/v2`、`openspec`、产品代码或 git 历史。
- 与并行工作的关系：本审计是 P1 UI 候选核验之外的并行准备，不声称 UI 已核验、契约已冻结或 Phase 0 已关闭。

## 1. 审计口径与事实源

冲突时沿用 `docs/VERSIONING.md` §2 与 `docs/contracts/README.md` §1 的优先级：已批准需求基线 > 已评审架构/模块/验收/测试边界 > 同步后的草案正文 > `docs/contracts/` 字段化表达 > `docs/v2`/`openspec`/`solutions/` 历史参考。根 `plan.md` 是批准记录日志，不单独替代字段或阈值契约。

本审计读取的关键文件：

| 类别 | 文件 |
|---|---|
| 契约索引 | `docs/contracts/README.md` |
| 领域契约 | `docs/contracts/domain.md`、`schemas/domain/*.json` |
| 节点安全契约 | `docs/contracts/security-node.md`、`schemas/security/*.json` |
| 证据与判定契约 | `docs/contracts/evidence-verdict.md`、`schemas/evidence/*.json` |
| 任务卡/报告/知识/审计契约 | `docs/contracts/ui-report-knowledge-audit.md`、`schemas/experience/*.json` |
| 阈值契约 | `docs/contracts/thresholds.md`、`schemas/config/thresholds.schema.json` |
| Phase 0 复验 | `docs/delivery/phase0-contract-remediation-verification.md`、`docs/delivery/phase0-contract-verification.md` |
| 事实源对账 | `docs/delivery/source-reconciliation.md`、`docs/delivery/p0-09-decision-reconciliation.md`、`docs/delivery/approved-draft-reconciliation.md` |
| 验收/测试边界 | `docs/v2/ACCEPTANCE-REPORT.md`、`docs/delivery/p0-03-postfix-verification.md`、`docs/delivery/p0-10-postfix-verification.md` |
| 主计划/进度 | `.omo/plans/noahsark-platform-delivery.md`、`docs/delivery/construction-progress.md`、`docs/delivery/restart-handoff-20261029.md` |

**证据与提案分离规则**：下文“证据”只列本次只读观察到的文件、行号、枚举与结构；“建议”是解决方向，不是已生效规范。任何建议在获得契约所有者确认前都不得被写成已冻结规则。

## 2. 发现总表

共 **9 项残余/冲突**：3 项为此前已登记的候选残余（R-01..R-03），6 项为本次新确认的仍具生命力的跨契约冲突（C-01..C-06）。另有 5 个主题（PostgreSQL、离线续跑、STOP-first、设备释放、五轴判定）经核对**无新的规范性冲突**，见 §5。

| ID | 主题 | 性质 | 主要源文件/证据 | 影响 | 建议解决（提案） | 依赖 | 需用户/真机环境输入 |
|---|---|---|---|---|---|---|---|
| R-01 | Execution Bundle 版本语义分裂 | 文档精度/版本语义 | `schemas/security/job.schema.json:196-198`；`schemas/domain/execution-bundle.schema.json:26`；`security-node.md` 无解释 | 读者可能误以为 `noahsark.execution-bundle/v1` 与载荷 `1.0` 必须相等；目前不破坏 schema 校验 | 明确前者为“bundle 格式/句柄版本”，后者为“载荷 schema 版本”，在 README/security-node/domain 登记二者关系与兼容规则 | P0-04/P0-05 契约所有者 | 否 |
| R-02 | cleanup `operational_detail` 投影不对称 | 结构超集/措辞 | `schemas/security/receipt.schema.json:370-405`；`schemas/domain/receipt.schema.json:180-215`；`README.md:61` | 语义不冲突，但“同一最小投影”对 domain 不成立；消费方可能误以为 domain 也接受运维明细 | 二选一：(a) 把 README 改为“security 投影为 domain 最小投影的超集”；(b) 在 domain 增加可选 `operational_detail`（需按 1.x 兼容规则评估） | P0-04/P0-05/P0-06 契约所有者 | 否 |
| R-03 | UI 证据轴映射缺失 + 投影 `UNKNOWN` 越权 | 文档精度/投影契约 | `ui-report-knowledge-audit.md:194-243`（§2.7 仅四表）；`README.md:64`；`report.schema.json:271-289`、报告 `report_scope.mode:66-68`；`ui-report-knowledge-audit.md:100-106` | evidence 轴无逐轴权威映射；报告/任务卡投影允许权威枚举没有的 `UNKNOWN`；`report_scope.mode` 用大写且混入终态值，未按 §2.7 自定规则登记 | 在 §2.7 增补 evidence 轴映射与 `UNKNOWN` 的“仅展示占位、不写回权威”声明；修正 README §2.3-8 表述；登记 `report_scope.mode` 的权威来源或改为与其他投影一致的词汇 | P0-07 + P0-06；最终词汇随 P1-08 UI 冻结确认 | 否（UI 词汇确认由 P1-08 承担，非真机） |
| C-01 | `mode` 枚举 `static_check` vs `static` | 跨契约词汇冲突 | `evidence-manifest.schema.json $defs.mode`（`:330-335`）；`verdict.schema.json $defs.mode`（`:543-548`）；`domain/run.schema.json:37`；`security/job.schema.json:147`；`security-node.md` §19.2 | 证据清单/判定用 `static_check`，领域 Run 与线协议 job.mode 用 `static`；同一静态运行在 manifest 与 run 关联时需额外映射，易被误判为不同 mode | 统一为 `static`（或在 manifest 明确 `static_check` 是 `Run.mode=static` 的投影并给出映射）。属枚举收紧/语义统一，须走契约版本规则 | P0-04/P0-05/P0-06 契约所有者 | 否 |
| C-02 | `failure_classification` 与 `failure_class` 大小写/成员不一致 | 判定词汇冲突 | `domain/run.schema.json:104-116`、`attempt.schema.json:112-124`（大写 8 值，无 `NEEDS_REVIEW`/`NONE`）；`evidence/verdict.schema.json $defs.failureClass:599-614`（小写 10 值，含 `none`/`needs-review`） | 领域记录与证据判定对同一失败使用不同词表；报告/UI 若直接透传会出现同一失败两种写法，影响复核与分母解释 | 建立一张权威映射表（如 `INVALID_INPUT ↔ invalid-input`），并明确 `needs-review` 在领域侧的表达方式；或统一大小写与成员集 | P0-04/P0-06 契约所有者；涉及报告时 P0-07 | 否 |
| C-03 | 线协议 `lease.state` 无到领域 `Lease.state` 的显式映射 | 设备释放/租约 | `security/lease.schema.json:135-137`（`granted/renewed/released/expired/revoked/reclaimed`）；`domain.md:441`（`GRANTED/HELD/RELEASING/RECLAIM_PENDING/RELEASED/QUARANTINED`）；`security-node.md` §19 只说“对齐但不替代” | 两套 lease 状态无逐值映射；`renewed/revoked/reclaimed` 在领域侧对应关系只能靠推断，可能影响设备释放与对账实现 | 仿照 receipt.status 映射，在 `security-node.md` §19.2 或 §10.2 增补 lease.state → domain Lease.state 的固定映射与未知值 fail-closed 规则 | P0-04/P0-05 契约所有者 | 否（映射本身）；真机验证属 L3/L4 |
| C-04 | 端点类型词汇不一致（音频输入/输出命名） | 设备释放/租约/证据关联 | `domain/device.schema.json:63`、`domain/lease.schema.json:39`（`audio_capture/audio_playback`）；`security/lease.schema.json:191`、`security/heartbeat.schema.json:209`（`audio_input/audio_output`）；`security-node.md` §10.2/§10.3 | 占用键 `(node_id, device_id, endpoint_set)` 与证据端点关联使用不同词表；跨契约比较可能把同一端点视为不同端点 | 统一端点 kind 词表，或在边界显式映射 `audio_capture↔audio_input`、`audio_playback↔audio_output` 并声明哪一侧是权威 | P0-04/P0-05/P0-06；实际设备端点清单对齐 T-10 | **部分是**：枚举统一不需真机；确认真实设备端点能力需 T-10 |
| C-05 | 设备占用枚举命名分歧（SR-14 仍开放） | 设备释放/事实源 | `domain.md:442/499/502`（`IDLE/OCCUPIED/RELEASING` + 独立 `pool_state`）；`docs/v2/SOLUTION.md:533`、`openspec/.../README.md:10`（`OCCUPIED/RELEASING/RELEASED/QUARANTINED`）；`source-reconciliation.md:84`（SR-14 登记为不阻断） | 契约用三值占用投影，`docs/v2`/`openspec` 用四值枚举；语义可对齐但名称不同，冻结前若不同步会让“已登记不阻断”延续到实现 | 由 P0-04/P0-06 在冻结时统一名称与层级（占用 vs 池状态 vs 隔离），并回写 `docs/v2`/`openspec` 的当前口径；SR-14 关闭前不得声称已统一 | P0-04/P0-06；文档同步可在 P0-03 后续 | 否 |
| C-06 | evidence manifest `case_version` 为字符串，领域为整数 | 追溯/判定键 | `evidence-manifest.schema.json:551-553`（`"type": "string"`）；`domain.md:284`（`case_version` integer ≥1）；`evidence-verdict.md:206` 示例 `"case_version": "1"` | 证据清单与领域 Case 对同一版本号使用不同类型；严格消费者可能拒绝或做隐式转换，影响 `run_id + case_id + attempt` 追溯与分母键 | 统一为 integer（manifest 侧改类型属破坏性/需版本评估），或在 manifest 明确“字符串仅为展示投影”并给出转换规则 | P0-04/P0-06 契约所有者 | 否 |

## 3. 重点候选残余（R-01..R-03）

### R-01 Execution Bundle 版本分裂

**证据（只读）**

- `schemas/security/job.schema.json:196-198`：Job 内 `execution_bundle.schema_version` 为 `const: "noahsark.execution-bundle/v1"`。
- `schemas/domain/execution-bundle.schema.json:26`：领域 ExecutionBundle 的 `schema_version` 为 `const: "1.0"`。
- `docs/contracts/README.md`、`security-node.md`、`domain.md` 均未解释“格式/句柄版本”与“载荷 schema 版本”的关系；`security-node.md` 仅要求“未知 bundle 版本 → 拒绝”。
- `phase0-contract-remediation-verification.md` §5 R-01、§6.2 第 7 项将该问题列为非阻断遗留。

**影响**

不破坏任何 schema 校验：前者是 Job 内引用句柄，后者是 bundle 载荷本身。但读者/实现者可能误以为二者必须相等，从而在节点校验或兼容判断中做出错误比较。

**建议（提案，非规范变更）**

1. 在 `docs/contracts/README.md` §2.3 或版本规则中增加一条：`noahsark.execution-bundle/v1` 是 **bundle 格式标识/引用命名空间**，`schema_version: "1.0"` 是 **载荷 schema 版本**，二者独立演进。
2. 在 `security-node.md` §10.1/§11 与 `domain.md` §10 各自引用该说明。
3. 明确未知格式标识或未知载荷版本均 fail-closed，但失败原因码区分（如 `BUNDLE_FORMAT_UNSUPPORTED` vs `SCHEMA_VERSION_UNSUPPORTED`）。

**依赖/输入**：P0-04/P0-05 契约所有者评审；不需要用户或真机环境输入。

### R-02 cleanup `operational_detail` 投影不对称

**证据（只读）**

- `schemas/security/receipt.schema.json:370-405`：`cleanup_receipt.operational_detail` 为可选对象，含 `residual_processes`、`disk_freed_bytes`、`actions`、`failure_code`。
- `schemas/domain/receipt.schema.json:180-215`：domain 的 `cleanup_receipt` 为 `additionalProperties: false`，无 `operational_detail`。
- `README.md:61` 称 security 与 domain 的 `cleanup_receipt` “是同一最小释放投影……详细运维字段只允许放在……可选 `operational_detail` 下”。
- 三处 `cleanup_status` 枚举一致（`completed/completed_with_warnings/failed/not_required/unknown`），且 `evidence-verdict.md:711-723` 给出最小投影到权威回执的映射。

**影响**

语义不冲突：domain 只承载最小释放事实，security 额外承载运维细节。但“同一投影”措辞对 domain 不成立，可能让消费方以为 domain 也接受 `operational_detail`，或在反序列化时失败。

**建议（提案，非规范变更）**

- 首选：把 `README.md:61` 改为“security 投影是 domain 最小投影的**超集**；domain 只保留最小释放字段”。
- 备选：在 domain `cleanup_receipt` 增加可选 `operational_detail`。按 `README.md` §3.3，新增可选字段可归为 `1.x` 兼容变更，但仍需契约所有者确认，且不得改变释放前置条件语义。

**依赖/输入**：P0-04/P0-05/P0-06 契约所有者；不需要真机环境输入。

### R-03 UI 证据轴映射缺失与投影 `UNKNOWN`

**证据（只读）**

- `ui-report-knowledge-audit.md:194-243` §2.7 只有 occupancy、communication、gate、run 四张映射表；没有 evidence 轴映射表。
- `README.md:64` 却称 §2.7 覆盖 “occupancy/communication/gate/run/evidence”。
- `ui-report-knowledge-audit.md:100-106` §2.3 列出五轴允许值，其中 `execution_status`、`validity_status`、`evidence_status`、`verification_status` 含 `UNKNOWN`；而 `domain.md` §9.1 与 `run/attempt.schema.json` 的权威枚举中，`execution_status` 无 `UNKNOWN`、`evidence_status` 无 `UNKNOWN`、`verification_status` 无 `UNKNOWN`（`validity_status` 有 `UNKNOWN`）。
- `report.schema.json:271-289` 的 `verdict_summary.axes` 同样允许上述 `UNKNOWN` 值；`report.schema.json:66-68` 的 `report_scope.mode` 为 `SMOKE/FORMAL/MIXED/BLOCKED/STOPPED/UNKNOWN`，其中 `BLOCKED`/`STOPPED` 是结果/终态而非运行模式，且该投影词汇未在 §2.7 登记。
- §2.7 末尾自定规则：“若新增投影枚举，必须先在此登记权威来源与禁止推断”。当前 evidence 轴与 report mode 未满足该规则。

**影响**

展示层 fail-closed 语义仍成立（无法映射一律 `UNKNOWN`），不会直接产生错误 PASS；但缺少逐轴登记会让 UI/报告对 authority 与投影的边界产生歧义，尤其 `evidence_status=UNKNOWN` 可能被误当作权威值写回。`report_scope.mode` 混入 `BLOCKED/STOPPED` 还可能把“运行结果”误读为“运行模式”。

**建议（提案，非规范变更）**

1. 在 §2.7 增补 evidence 轴映射表：权威 `COMPLETE/INCOMPLETE/CONFLICTED/UNVERIFIED` → 任务卡/报告展示值；明确 `UNKNOWN` 仅用于“尚未读取/投影不可用”，不得写回 `verdict.axes.evidence_status`（该规则已在 `evidence-verdict.md:882` 表达，应在 UI 契约中引用）。
2. 对 `execution_status`、`verification_status` 的 `UNKNOWN` 做同样声明。
3. 修正 `README.md:64`：§2.7 当前覆盖四表，evidence 轴待登记，或先补齐再声明。
4. 为 `report_scope.mode` 增加权威来源说明；若它确实是“报告覆盖范围”而非“运行模式”，建议改名/改值（如 `SCOPE_SMOKE/SCOPE_FORMAL/MIXED`），或明确 `BLOCKED/STOPPED` 只表示“报告覆盖的运行含阻断/停止”，不是 mode。

**依赖/输入**：P0-07 + P0-06；最终 UI 词汇随 Phase 1 P1-08 冻结确认。不需要真机环境输入。

## 4. 新确认的仍具生命力冲突（C-01..C-06）

### C-01 `mode` 词汇：`static_check` vs `static`

**证据**：`evidence-manifest.schema.json` 的 `$defs.mode` 为 `["static_check","smoke","formal"]`（`:330-335`）；`verdict.schema.json` 的 `$defs.mode` 同为 `["static_check","smoke","formal"]`（`:543-548`）；`domain/run.schema.json:37` 与 `attempt.schema.json` 的 `run_mode` 为 `["static","smoke","formal"]`；`security/job.schema.json:147` 的 `job.mode` 含 `static`；`security-node.md` §19.2 将 `static_check` action 映射到 `Run.mode=static`。

**影响**：manifest/verdict 与 Run/Job 对同一静态运行使用不同字符串。若实现按 `mode` 直接关联，需额外映射；若按字符串相等校验，会把合法静态运行判为不匹配。

**建议**：统一为 `static`，或在 evidence 契约中显式声明 `static_check` 是 `Run.mode=static` 的投影并给出映射/校验规则。枚举收紧涉及版本规则，须由契约所有者决定。

### C-02 失败分类词表分裂

**证据**：`domain/run.schema.json:104-116` 与 `attempt.schema.json:112-124` 使用大写、8 值：`INVALID_INPUT`、`INVALID_ENVIRONMENT`、`INVALID_EVIDENCE`、`VALID_FAILURE`、`BLOCKED`、`STOPPED`、`UNSUPPORTED`、`INFRA_ERROR`；`evidence/verdict.schema.json:599-614` 的 `$defs.failureClass` 使用小写、10 值，另含 `none`、`needs-review`。`evidence-verdict.md` §14.2/§15.1 使用小写值。

**影响**：领域记录与证据判定对同一失败使用不同词表；报告/UI 若直接透传会出现两种写法；`needs-review` 在领域侧无对应值，可能需要映射到 `NEEDS_REVIEW` 业务轴或新增字段。不会改变 PASS 派生本身，但影响可追溯与复核一致性。

**建议**：建立权威映射表（大小写 + 成员），明确 `needs-review` 在领域侧的表达；若统一枚举，按契约版本规则处理并保留历史解析器。

### C-03 线协议 `lease.state` 缺少领域映射

**证据**：`security/lease.schema.json:135-137` 的 `state` 为 `granted/renewed/released/expired/revoked/reclaimed`；`domain.md:441` 的 `Lease.state` 为 `GRANTED/HELD/RELEASING/RECLAIM_PENDING/RELEASED/QUARANTINED`；`security-node.md` §19 只说协议消息与领域实体“字段对齐但不互相替代”，未给出 lease.state 逐值映射（receipt.status 则有 §19.2 显式映射）。

**影响**：`renewed`、`revoked`、`reclaimed` 在领域侧无同名状态，只能靠推断；设备释放与对账实现可能对“撤销租约是否等于可释放/隔离”产生分歧。设备释放前置条件本身（本地停止/安全清理/占用对账）仍清晰，但状态映射缺失会削弱实现一致性。

**建议**：在 `security-node.md` §19.2 或 §10.2 增补 lease.state → domain Lease.state 固定映射，并规定未知值 fail-closed；特别说明 `expired` 仅续约截止、`revoked`/`reclaimed` 如何进入 `RELEASING`/`RECLAIM_PENDING`/`QUARANTINED`。

### C-04 端点类型词汇不一致

**证据**：`domain/device.schema.json:63` 与 `domain/lease.schema.json:39` 使用 `audio_capture/audio_playback/serial/usb/gpio`；`security/lease.schema.json:191` 与 `security/heartbeat.schema.json:209` 的 `endpoints[].kind` 使用 `audio_input/audio_output/serial/usb/network/display`；`security/job.schema.json` 的 `evidence_policy.required_kinds` 与 `receipt` artifacts 使用 `audio_capture`。`security-node.md` §10.2/§10.3 未解释该差异。

**影响**：占用键 `(node_id, device_id, endpoint_set)` 与证据端点关联使用不同词表；跨契约比较可能把同一音频端点视为不同端点，影响租约冲突判断与证据归属。设备释放安全条件（端点释放）依赖端点身份一致。

**建议**：统一词表，或在 API 边界建立显式双向映射并声明权威侧。`network`/`display` 是否属于 V0.0.1 设备端点也需确认（domain 当前无这两个值）。

**输入**：枚举统一本身不需真机；真实设备端点能力清单需 P0-10/T-10 输入，属于 L3 前置。

### C-05 设备占用枚举命名分歧（SR-14）

**证据**：`domain.md:442/499/502` 用 `IDLE/OCCUPIED/RELEASING` 作为 `occupancy_state`，另以 `pool_state` 表达 `RESERVED/ATTACHED/DRAINING/QUARANTINED` 等；`docs/v2/SOLUTION.md:533`、`openspec/.../README.md:10` 仍用 `OCCUPIED/RELEASING/RELEASED/QUARANTINED` 作为设备占用枚举；`source-reconciliation.md:84` 将 SR-14 登记为“已登记（不阻断）”，处置为 P0-04/P0-06 冻结时统一。

**影响**：语义可对齐（占用与通信/释放/隔离分离），但名称与层级不同。冻结前若不同步，`docs/v2`/`openspec` 的旧四值枚举可能被实现或 UI 误用，尤其 `RELEASED` 与 `QUARANTINED` 在领域侧分属 `Lease.state`/`pool_state`，不在 `occupancy_state`。

**建议**：在契约冻结时统一名称与层级，并回写 `docs/v2`/`openspec` 当前口径；在 SR-14 关闭前不得声称占用枚举已统一。该条与 C-03/C-04 同属设备释放面，建议合并为一次契约对齐任务。

### C-06 evidence manifest `case_version` 类型不一致

**证据**：`evidence-manifest.schema.json:551-553` 的 `$defs.caseEntry.case_version` 为 `"type": "string"`；`domain.md:284` 的 `Case.case_version` 为 `integer ≥1`；`evidence-verdict.md:206` 示例写 `"case_version": "1"`。`domain/attempt.schema.json` 亦为 integer。

**影响**：证据清单与领域 Case 对同一版本号使用不同类型；严格消费者可能拒绝或做隐式转换，影响 `run_id + case_id + attempt` 追溯、分母键与跨契约比较。不直接改变 PASS 派生，但削弱“可追溯”保证。

**建议**：统一为 integer；若 manifest 需保留字符串展示，明确其为投影字段并给出 `case_version_int`/转换规则。类型变更按契约版本规则评估。

## 5. 已核对但当前无新规范性冲突的主题

以下主题经只读核对，**核心已批准语义一致**；不把“文档仍有历史文本”误报为活动冲突。

| 主题 | 证据 | 结论 |
|---|---|---|
| PostgreSQL / SQLite | `README.md` 开篇、`domain.md:6/35/632/734`、`source-reconciliation.md` SR-02、`p0-09-decision-reconciliation.md` E-01、`docs/v2`/`openspec` 均已加“历史/已取代 2026-10-28”标签 | **无活动冲突**。PostgreSQL 是唯一正式数据库；残留 SQLite 文本均在历史/禁止说明中。不需新动作。 |
| 离线续跑 | `domain.md` §15、`thresholds.md` §4、`security-node.md` §13、`ui-report-knowledge-audit.md` §2.5、`approved-draft-reconciliation.md` | **无活动冲突**。已启动冻结压测断线继续、设备保持占用、不重派/重播/重复采样，四处一致。 |
| STOP-first 重连 | `domain.md` §15.3、`thresholds.md` TH-L-10、`security-node.md` §13.3、`ui-report-knowledge-audit.md` §2.5 | **无活动冲突**。重连顺序固定为处理待 STOP → 补传 → 去重 → 对账 → 再领取；旧 epoch 不改当前运行。 |
| 设备释放与判定分离 | `domain.md` §15.4、`evidence-verdict.md` §12/§13、`thresholds.md` TH-L-08、`ui-report-knowledge-audit.md` §2.5 | **核心无冲突**。释放仅依赖本地停止、安全清理、占用对账；缺 cleanup 回执不自动等于证据不完整；释放不是 PASS 前置。设备面的实现细节冲突见 C-03/C-04/C-05。 |
| 五轴判定与正式 PASS | `domain.md` §14、`evidence-verdict.md` §14/§16、`docs/v2/SOLUTION.md:537`、`openspec/.../design.md:38`、`p0-03-postfix-verification.md` §3.2 | **核心无冲突**。五轴分离、正式 PASS 五条件、Linux 独立复核、节点不得写最终判定一致。词表/投影细节见 C-02/C-06/R-03。 |

**一处需要澄清但暂不判为冲突**：`security-node.md:255` 写“证书过期后，节点停止接受新 Job；已启动的冻结压测在安全点完成或 STOP”，而离线续跑规则强调通信/租约事件不停止已启动运行。证书过期是身份/安全事件，不是通信或租约事件，二者可以并存；但建议在契约冻结时明确“身份失效时可安全停止”与“通信失联必须继续”的边界，避免实现把证书过期当作普通离线处理。

## 6. 阻塞项与所需输入

本审计可独立完成的部分已全部完成；以下事项**不能由本审计替所有者决定**，需外部输入或后续阶段：

| 阻塞/待决项 | 为什么现在不能关闭 | 所需输入 | 关联 |
|---|---|---|---|
| 契约所有者对 R-01..R-03、C-01..C-06 的裁决 | 契约仍为 `frozen-candidate v1`；本审计只登记，不改规范 | Orchestrator/所有者评审；冻结版本号与变更记录 | `README.md` §2.3 |
| P1 UI 候选核验 | 并行核验尚未产出 `ui-candidate-verification.md`；R-03 的最终 UI 词汇需 P1 结论 | 独立 UI 核验 PASS/NEEDS-FIX；P1-08 冻结包 | `restart-handoff-20261029.md` |
| 真机端点能力与设备事实（C-04 部分） | 实际设备有哪些音频/串口端点、如何命名，只有真机事实能确认 | T-10 设备型号/固件/端点清单；A-0 环境准入 | `p0-09-decision-reconciliation.md` T-10 |
| 节点/设备/正式 profile/备份恢复事实 | A-0 未通过，L3/L4 无法执行；不影响本审计的文档结论 | T-09/T-10/T-11/T-12；真实节点、设备、profile、NAS/第二服务器 | `environment-inputs.md`；`p0-10-postfix-verification.md` |
| PostgreSQL 版本/运维人、审批升级对象等环境参数 | 属 `environment-input`，不是契约字段冲突 | 所有者/责任方提供 | `p0-09-decision-reconciliation.md` T-13/T-14 |

## 7. 验证与复现（只读）

本次审计未修改被审对象。可复现的关键检查：

```bash
cd /home/bszheng/NoahsArk

# R-01 / R-02 / R-03 证据
grep -n "noahsark.execution-bundle/v1" docs/contracts/schemas/security/job.schema.json
grep -n '"schema_version".*"1.0"' docs/contracts/schemas/domain/execution-bundle.schema.json
grep -n "operational_detail" docs/contracts/schemas/security/receipt.schema.json docs/contracts/schemas/domain/receipt.schema.json
grep -n "evidence" docs/contracts/README.md | head

# C-01..C-06 枚举/类型
python3 - <<'PY'
import json
for p in [
 "docs/contracts/schemas/evidence/evidence-manifest.schema.json",
 "docs/contracts/schemas/evidence/verdict.schema.json",
 "docs/contracts/schemas/domain/run.schema.json",
 "docs/contracts/schemas/security/lease.schema.json",
 "docs/contracts/schemas/domain/device.schema.json",
]:
    s=json.load(open(p))
    print("==",p)
    def walk(o,path=""):
        if isinstance(o,dict):
            if "enum" in o and isinstance(o["enum"],list): print(" ",path,"=",o["enum"])
            for k,v in o.items(): walk(v,path+"/"+k)
        elif isinstance(o,list):
            for i,v in enumerate(o): walk(v,path+f"[{i}]")
    walk(s)
PY

# 历史/禁令声明检查
grep -rIn "sqlite" docs/contracts/
grep -rIn "lease_expired" docs/contracts/
```

**证据边界**：以上命令只证明当前工作区文本与 schema 的枚举/类型状态；不证明契约已评审、已冻结、已实现或已测试。

## 8. 结论

- 本次新增 **9 项**发现：R-01、R-02、R-03 为此前非阻断候选残余的继续跟踪；C-01..C-06 为本次新确认的仍有生命力的跨契约冲突，集中在 **mode/失败分类词表、租约状态映射、端点/占用枚举、case_version 类型、投影词汇登记**。
- **PostgreSQL、离线续跑、STOP-first、设备释放/五轴核心语义**未发现新的规范性冲突；相关历史文本均已带历史标签，设备面的实现细节冲突已单列为 C-03..C-05。
- 所有结论都是**候选契约的审计意见**，不是冻结、批准、实现、测试或验收结论。任何修复必须由契约所有者按版本规则决定，并按 `README.md` §3 处理兼容性。

---

**路径**：`docs/delivery/contract-residual-followup.md`
**非声明**：本文件不修改任何契约/schema/主计划/UI，不构成实现、测试、部署、验收或发布授权；不包含密钥、凭据、真实节点值或原始证据。
