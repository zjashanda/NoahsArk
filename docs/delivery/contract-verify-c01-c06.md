# 契约验证：C-01（mode 词汇）与 C-06（case_version 整数）

- 范围：`docs/contracts/` 规范包的两个裁决，只读审计；未采信 `docs/delivery/contract-adjudication-record.md`。
- 方法：逐条重读 schema/文档原文；用 `grep -rn` 枚举出现位置；用 `python3 -m json.tool` 与 `jsonschema` Draft 2020-12 元校验。
- 观测版本标签：`frozen-candidate v1.1`（`README.md:3`），候选包 `1.1-candidate`（`README.md:4`），载荷 `schema_version` 仍为 `"1.0"`（`schemas/domain/run.schema.json:31`）。**未冻结、未批准**。

## 结论

| 决定 | 判定 | 摘要 |
|---|---|---|
| C-01 | **NEEDS-FIX** | 所有 `Run.mode` 与 evidence/verdict/report-index 的 `$defs.mode` 均为三值；但 `static_check` 仍出现在 `device-occupancy.occupant.purpose`，违反“只允许出现在 `job.action`/`Receipt.job_kind`”的验收句，且 `evidence-verdict.md:120` 的“所有层”表述过宽。 |
| C-06 | **NEEDS-FIX** | 5 个含 `case_version` 的规范 schema 全部为 `integer, minimum 1`，无 string；但 `evidence-verdict.md:568` 仍把唯一键写成 `run_id + case_id + attempt`，漏掉 `case_version`，与 C-06 的身份键直接冲突。 |

## C-01 逐项证据

通过：
- `Run.mode` 仅三值：`schemas/domain/run.schema.json:35-39`，`enum: ["static","smoke","formal"]`。
- Attempt 的运行模式同三值：`schemas/domain/attempt.schema.json:34-38`。
- evidence 三层 `$defs.mode` 均三值：`schemas/evidence/evidence-manifest.schema.json:331-339`、`schemas/evidence/verdict.schema.json:544-552`、`schemas/evidence/report-evidence-index.schema.json:100-108`。
- 上列三层引用同一 `$defs.mode`：`evidence-manifest.schema.json:57-59`、`verdict.schema.json:54-56`、`report-evidence-index.schema.json:273-275`。
- 条件分支只比较 `static`/`smoke`/`formal`：`run.schema.json:134-156`、`evidence-manifest.schema.json:280-308`、`verdict.schema.json:181,295-302`。
- 文档规范面：`domain.md:322`（Run.mode 三值）、`domain.md:671-687`（action/job_kind/Run.mode 映射与 C-01 说明）、`security-node.md:888-897`（Job.action/Job.mode → Receipt.job_kind/Run.mode）、`README.md:68`。
- 兼容读只作只读别名且有告警：`evidence-manifest.schema.json:338`、`verdict.schema.json:551`、`report-evidence-index.schema.json:107`、`domain.md:686`。
- 写出方只写 `static`：`verdict.schema.json:551`、`README.md:68`。

未通过/残余：
- `schemas/evidence/device-occupancy.schema.json:483-490`：`occupant.purpose` 的 `enum` 含 `static_check`（`static_check`/`smoke`/`formal`/`diagnostics`/`recovery`）。这不是 `mode` 字段，但它是“`static_check` 只存在于 `job.action` 与 `Receipt.job_kind`”这一验收句之外的第三处出现；`recovery` 也说明它并非 `job.action` 的复本。应改为 `static`，或明确声明 purpose 是 job-action 派生词并登记例外。
- `docs/contracts/evidence-verdict.md:120`：“`mode` 在所有层只有 `static`/`smoke`/`formal`”与 `schemas/security/job.schema.json:145-152`（`Job.mode` 另含 `diagnostics`/`cleanup`）字面冲突。`security-node.md:888-894` 已区分 `Job.mode` 与 `Run.mode`，故属文档措辞过宽，非 `Run.mode` 定义错误。
- 相邻但非 C-01 模式定义：`report.schema.json:64-73` 的 `report_scope.mode` 含 `SMOKE/FORMAL/MIXED/BLOCKED/STOPPED/UNKNOWN`（`report.schema.json:68` 明示“NOT Run.mode”）；`knowledge-candidate.schema.json:101-104` 的 `run_mode` 使用大写 `STATIC/SMOKE/FORMAL/MIXED/UNKNOWN`，是与三值 `Run.mode` 不同层的投影，需在后续词汇裁决中确认。

## C-06 逐项证据

通过：
- `schemas/domain/attempt.schema.json:34`：`{ "type": "integer", "minimum": 1 }`。
- `schemas/domain/case.schema.json:32-36`：`type: integer, minimum: 1`；条件分支只加严为 `minimum: 2`（`case.schema.json:117`），未放宽类型。
- `schemas/domain/revision.schema.json:106`：`case_refs[].case_version` 为 `integer, minimum 1`。
- `schemas/evidence/evidence-manifest.schema.json:552-559`：integer/minimum 1，描述明确拒绝 string。
- `schemas/evidence/verdict.schema.json:698-702`：integer/minimum 1，描述要求与 `attempt.case_version` 整数相等。
- 身份键正确定义：`README.md:73` 为 `run_id + case_id + case_version + attempt`；`domain.md:687` 与 `domain.md:936`（D-C-22）一致。
- 示例已为整数：`evidence-verdict.md:206`（`"case_version": 1`）。
- 兼容读为显式、只读、带告警：`README.md:73`（`legacy_case_version_coerced`）、`domain.md:936`；规范 schema 默认严格，`evidence-manifest.schema.json:555-557` / `verdict.schema.json:701`。

未通过：
- `docs/contracts/evidence-verdict.md:568`：“以 `run_id + case_id + attempt` 为唯一键。” 漏掉 `case_version`，与 `README.md:73`、`domain.md:687` 的四元键冲突；按此去重会把同一 case 的不同版本合并计数，直接违背 C-06 验收中的身份键要求。应改为 `run_id + case_id + case_version + attempt`。

## 文件枚举与分类（规范包）

### 含 `mode` 的文件（`docs/contracts/`，16 个独立 `mode`；另 2 个仅含 `run_mode`/`entry_mode`）
- 规范定义：`schemas/domain/run.schema.json:35-39`；`schemas/domain/attempt.schema.json:34-38`；`schemas/evidence/evidence-manifest.schema.json:57-59,331-339`；`schemas/evidence/verdict.schema.json:54-56,544-552`；`schemas/evidence/report-evidence-index.schema.json:100-108,273-275`。
- 协议/动作词表（非 Run.mode）：`schemas/security/job.schema.json:121-152`（`Job.action` 与 `Job.mode`）；`schemas/domain/receipt.schema.json:42-53`（`job_kind`）；`schemas/security/lease.schema.json:163`（`allowed_actions`）。
- 证据 purpose（非 mode，残余）：`schemas/evidence/device-occupancy.schema.json:483-490`。
- 其他同名字段（非 Run.mode，已文档化）：`schemas/experience/report.schema.json:64-73`（报告覆盖范围）；`schemas/experience/task-card.schema.json:472-475`（进度模式）；`schemas/experience/knowledge-candidate.schema.json:101-104`（投影 run_mode）；`schemas/security/log-query.schema.json:381-385`（投递模式）；`schemas/security/stop.schema.json:128-133`（停止模式）；`schemas/domain/task.schema.json:47-50`（entry_mode）。
- 文档：`domain.md:322,671-687,931,936,958`（规范 + 裁决/历史）；`security-node.md:474-480,884-897`（规范映射）；`evidence-verdict.md:114-120,568`（规范 + 过宽句 + C-06 陈旧句）；`README.md:3,68,73,142`（裁决/版本）；`ui-report-knowledge-audit.md:257-270`（UI 投影说明）。

### 含 `case_version` 的文件（`docs/contracts/`，8 个）
- 规范定义：`schemas/domain/case.schema.json:32-36,117`；`schemas/domain/attempt.schema.json:34`；`schemas/domain/revision.schema.json:106`；`schemas/evidence/evidence-manifest.schema.json:552-559`；`schemas/evidence/verdict.schema.json:698-702`。
- 文档：`domain.md:149,284,293,298-300,353,687,936,958`；`evidence-verdict.md:206,568`；`README.md:73,94,142`。

### 非规范副本（仓库内其余命中）
- `.omo/drafts/` 下 38 个含 `mode` 的文件为历史草稿/候选快照（含 `.omo/drafts/99-history/20261029-phase0-candidate/01-contracts/**` 整套镜像），全部**非规范**、不作证据。
- `.omo/drafts/` 下 13 个含 `case_version` 的文件与 `plan.md` 同为历史/执行记录，**非规范**。`docs/delivery/contract-residual-followup.md:45,159` 引用的 `"type": "string"` 与 `"1"` 属修复前证据，已与现行 schema 不符，属陈旧引用（交付记录，非契约）。

## 元校验与仓库状态
- `python3 -m json.tool`：对 11 个被引用 schema（run/attempt/case/revision/receipt/job/lease/evidence-manifest/verdict/report-evidence-index/device-occupancy）全部通过。
- `jsonschema.Draft202012Validator.check_schema`：`docs/contracts/schemas` 35/35 通过，0 失败。
- `grep` 扫描确认：`docs/contracts/schemas/**/*.json` 中 `case_version` 出现在 5 个文件、共 6 处，均为 integer；无 `"type": "string"`。
- `git diff --check` 退出码 0；但 `docs/contracts/` 当前为未跟踪目录（`git status` 显示 `?? docs/contracts/`），该检查不覆盖本包，且本包无提交历史可核。

## 无法验证的事项
- 运行时写入方/读取方行为：包内无实现代码，无法验证“写出方只发三值”“兼容读开关默认关闭”在运行期成立。
- 数据库/服务端唯一约束：无 DDL 或实现，无法验证四元身份键被强制。
- 兼容读告警 `legacy_case_version_coerced` 的实际触发与审计落盘。
- 规范 schema 的实例级行为：只做了元 schema 校验，未用实例语料做正/负向验证。
- `docs/contracts/` 未纳入 Git 跟踪，无法用 diff/历史确认变更边界。
