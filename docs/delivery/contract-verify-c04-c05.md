# C-04 / C-05 独立验证（只读审计）

- 审计对象：`docs/contracts/`，35 个 JSON Schema + 5 份契约文档。
- 观测版本标签：候选包 `frozen-candidate v1.1` / `1.1-candidate`（`README.md:3-4`）；所有载荷 `schema_version` 仍为 `"1.0"`（如 `schemas/domain/lease.schema.json:29`）。本文不代表冻结、批准或可生产。
- 方法：从 schema 与规范性文本重新推导；用 `jsonschema` Draft 2020-12 做元校验与反例实例验证，不采信裁决记录结论。

## 1. 结论

| 决策 | 判定 | 一句话理由 |
|---|---|---|
| C-04 endpoint_kind vs endpoint identity | **NEEDS-FIX** | 权威 kind 词表与 wire 身份集合已正确分离，但两个规范性 schema 仍让名为 `endpoint_set` 的字段承载 kind，且域内占用键按此字段定义，与“endpoint_set 不得承载 kind / 占用键用身份”直接冲突。 |
| C-05 三层占用，RELEASED/QUARANTINED 在占用枚举之外 | **PASS** | L1/L2/L3 三层在文档与 schema 中可对应；`occupancy_state` 全部为三值，`RELEASED`/`QUARANTINED` 只出现在 Lease.state / pool_state / release_state 等其它轴；释放与隔离不变量经反例实例验证成立。附 3 项边界见 §5。 |

## 2. C-04 证据

权威 kind 词表（5 值）：
- `schemas/domain/device.schema.json:61-65`（`audio_capture`/`audio_playback`/`serial`/`usb`/`gpio`）
- `schemas/domain/lease.schema.json:39-41`、`schemas/domain/execution-bundle.schema.json:144-147`（同 5 值）

wire 端点身份集合（`endpoint_<32hex>`）：
- `schemas/security/lease.schema.json:110-119`（pattern `^endpoint_[0-9a-f]{32}$`，`description` 明确“identity set, never kinds”）
- `schemas/security/job.schema.json:302-310`、`schemas/security/heartbeat.schema.json:204-206`、`schemas/security/anomaly-event.schema.json:160-163`

入站别名（仅 wire，且仅说明层）：
- `schemas/security/lease.schema.json:192-195` 与 `schemas/security/heartbeat.schema.json:209-212` 的 `kind` enum 含 `audio_input`/`audio_output`（另有 `network`/`display`，标注为非可占用能力标识）
- 归一规则：`security-node.md:570`、`security-node.md:935-942`；写出方只发权威词（同处 + `README.md:71`）

冲突点（决定性）：
- `schemas/domain/lease.schema.json:33-42`：字段名 `endpoint_set`，`items.enum` 为 5 个 kind；`description` 自认“legacy field name”。
- `schemas/domain/execution-bundle.schema.json:139-148`：同样名为 `endpoint_set`，`items.enum` 为 5 个 kind。
- `domain.md:475` 把上述域内 `endpoint_set` 定义为“kind 能力类”，而 `domain.md:57`、`domain.md:516`(L-1)、`domain.md:799`、`domain.md:813` 又把 `(node_id, device_id, endpoint_set)` 定义为占用键/幂等键。域 `Lease.endpoint_set` 在类型上无法容纳身份，故“占用键用 endpoint 身份”在域模型内不成立。
- 实证：`domain/lease` 的 `endpoint_set=["audio_capture"]` 通过、`["endpoint_"+32hex]` 失败；`execution-bundle.device_requirements` 同样；`security/lease.payload.endpoint_set` 相反（kind 失败、身份通过）。

“同一对象同时要求 kind 与身份”交叉检查：
- 没有任何 schema 在 `endpoint_set` 的元素对象上同时要求 kind 与身份（所有 `endpoint_set` 元素都是 `string`）。
- 但 3 个端点描述对象同时必填二者：`domain/device.schema.json:58-60`、`security/lease.schema.json:186-191`、`security/heartbeat.schema.json:202-206`。它们不是 `endpoint_set`，属“端点描述符”，与 C-04 字面要求不冲突，但保留了“id+kind 同体”的第二种端点表示。

`endpoint_id` 格式强度不一致：
- 域 `device.endpoints[].endpoint_id` 仅 `string, 1..200`（`device.schema.json:60`）；`node.endpoint_ids` 亦无 pattern（`node.schema.json:131-136`）；`device-occupancy.resource_key.endpoint_set` 仅 `string`（`device-occupancy.schema.json:327-335`）。身份格式只在 wire 侧强制。

## 3. C-05 证据

三层对应：
- L1 权威：`schemas/domain/lease.schema.json:52-56`（state 6 值）、`schemas/domain/device.schema.json:79-83`（pool_state 8 值）、`lease.schema.json:78-87`（release_preconditions）；文档 `domain.md:575-580`、`README.md:72`。
- L2 粗投影：`lease.schema.json:57-60`、`device.schema.json:93-96`、`run.schema.json:78-81`、`device-occupancy.schema.json:353-356`，均为 `IDLE`/`OCCUPIED`/`RELEASING`。
- L3 细化/展示：`device-occupancy.schema.json:338-351`（10 值细化）、`experience/task-card.schema.json:380-384`（UI 四值）；文档 `domain.md:581-590`、`ui-report-knowledge-audit.md:200-206`。

`RELEASED`/`QUARANTINED` 在占用枚举之外：
- 所有 `occupancy_state` 枚举均无这两个词（上列 4 处；grep 全包确认）。
- `RELEASED` 仅见 `lease.schema.json:54,120`（Lease.state 与 RELEASED 分支）及文档；`QUARANTINED` 仅见 `lease.schema.json:54,148`、`device.schema.json:81,143`、`node.schema.json:89,149`（pool/status 轴）、`task-card.schema.json:101,352`（生命周期阶段/展示）。
- 文档明确“不是 occupancy 值，不得扩展为第四值”：`domain.md:590`、`evidence-verdict.md:810`。

不变量（反例实例已实测）：
- `lease.schema.json:103-110`：GRANTED/HELD/RECLAIM_PENDING ⇒ OCCUPIED。
- `lease.schema.json:118-136`：RELEASED ⇒ IDLE + 三项前置条件 true + `released_at`；RELEASED+OCCUPIED 实例被拒。
- `lease.schema.json:146-154`：QUARANTINED ⇒ OCCUPIED；QUARANTINED+IDLE 实例被拒。
- `device-occupancy.schema.json:99-135`（free ⇒ occupant null、release released/not_applicable、quarantine.active=false）、`169-194`（release released ⇒ state free）、`195-213`（free ⇒ IDLE）、`214-232`（draining ⇒ RELEASING）、`233-260`（含 quarantined ⇒ OCCUPIED）。
- 文档不变量：`domain.md:572`(D-5)、`domain.md:573`(D-6)、`domain.md:590`。

## 4. 术语出现分类（全量）

- `endpoint_kind`
  - 规范：`schemas/domain/device.schema.json:63-64`；`schemas/domain/execution-bundle.schema.json:143,146`；`schemas/domain/lease.schema.json:37,40`；`schemas/security/lease.schema.json:193`；`schemas/security/heartbeat.schema.json:210`。
  - 别名说明：`security-node.md:570,935-942,943`；`README.md:71`；上列 wire `description`（`security/lease:194`、`heartbeat:211`）。
  - 遗留/陈旧：`domain.md:475,934`（kind 与身份共名）。
- `endpoint_set`
  - 身份语义（规范）：`schemas/security/lease.schema.json:110-119`；`schemas/security/job.schema.json:294,302-310`；`schemas/evidence/device-occupancy.schema.json:314,327-335`；`security-node.md:489,494,570,943-944`；`README.md:71`。
  - kind 语义（遗留）：`schemas/domain/lease.schema.json:13,33-42`；`schemas/domain/execution-bundle.schema.json:132,139-148`；`domain.md:437,475,934`。
  - 占用键/幂等键引用：`domain.md:57,516,799,813`。
  - 展示：`schemas/experience/task-card.schema.json:281,365-371`。
- `endpoint_id`
  - 规范描述符/字段：`schemas/domain/device.schema.json:58,60`；`schemas/security/lease.schema.json:186,188-191`；`schemas/security/heartbeat.schema.json:202,204-206`；`schemas/security/anomaly-event.schema.json:86,160-163`；`schemas/domain/node.schema.json:23,131-136`。
  - 文档：`README.md:71`；`domain.md:475,550,611`；`security-node.md:494,944`。
- `occupancy_state`
  - 规范（L2）：`domain/lease:19,57-60,109,116,125,152`；`domain/device:22,93-96,137`；`domain/run:22,78-81`；`device-occupancy:14,39-41,208,227,255`。
  - 展示（L3）：`task-card:281,380-384`；`device-occupancy:338-351`。
  - 文档：`README.md:58,72`；`domain.md:328,480,507,527,558,569,573,580,588,590,747,903`；`security-node.md:494,919,923`；`evidence-verdict.md:793,806,808,810,1227`；`ui-report-knowledge-audit.md:74,164,200,204,206,244,617`；`thresholds.md:142`。
- `RELEASED`
  - 规范：`domain/lease:54,120`。
  - 文档：`README.md:70,72`；`domain.md:479,487,496,501,510,512,531,532,534,587,590`；`security-node.md:927,928,930`；`evidence-verdict.md:810`；`ui-report-knowledge-audit.md:206`。
  - 示例/无关字符串：`evidence-verdict.md:687`（`detail_code: ENDPOINTS_RELEASED`，非枚举）。
- `QUARANTINED`
  - 规范：`domain/lease:54,148`；`domain/device:81,143`；`domain/node:89,149`；`task-card:101,352`（阶段/pool 展示）。
  - 文档：`README.md:72,142`；`domain.md:479,500,511,533,538,555,572,573,588,590,606,612,785,858,935`；`security-node.md:929`；`evidence-verdict.md:810`；`ui-report-knowledge-audit.md:92`。

## 5. 仍存矛盾与歧义

1. **C-04 主矛盾**：`domain/lease.schema.json:33-42` 与 `execution-bundle.schema.json:139-148` 的 `endpoint_set` 类型是 kind 枚举，与“endpoint_set 不得承载 kind”冲突；文档以“历史字段名 / 2.0 再拆”解释，但字面验收未通过。
2. **C-04 占用键矛盾**：`domain.md:516`（L-1）与 `domain.md:799,813` 用 `endpoint_set` 定义占用键，而域 `Lease.endpoint_set` 只能放 kind，导致域内占用键无法表达身份。
3. **C-04 身份格式不齐**：域 `device.endpoint_id`、`node.endpoint_ids`、`device-occupancy.resource_key.endpoint_set` 均未强制 `endpoint_<32hex>`；仅 wire 强制，跨层可写入不合规身份。
4. **C-04 写出方规则不可机检**：wire schema 无法区分发送方向，`security/lease:193` 与 `heartbeat:210` 仍然接受别名；“写出方只发权威词”仅为文字约束。
5. **C-04 文档串线**：`security-node.md:943` 称 `endpoint_kind` 用于 `required_kinds`，但唯一同名 schema 字段 `security/job.schema.json:397-414` 是证据 kind，不是端点 kind；不存在端点 kind 需求字段。
6. **C-05 层级命名歧义**：`device-occupancy.schema.json:338-351` 的 `$defs/occupancyState` 含 `quarantined`；“QUARANTINED 在占用枚举之外”只对 L2 `occupancy_state` 成立，对这份 L3 细化枚举不成立。
7. **C-05 展示投影矛盾**：`ui-report-knowledge-audit.md:205` 称 RESERVED 可映射自 Lease.state ∈ {GRANTED,HELD,RECLAIM_PENDING} 且“尚未 OCCUPIED”，但 `lease.schema.json:104-110` 强制这些状态为 OCCUPIED，该条件不可达；`task-card:380-384` 还用 `FREE` 而非 L2 的 `IDLE`（L3 词汇，已登记但非 1:1）。
8. **C-05 隔离准入仅为文字**：设备 `pool_state=QUARANTINED` 只要求 `quarantine_reason`（`device.schema.json:141-147`），不强制 `occupancy_state=OCCUPIED`；“隔离设备不得接新作业”仅由 `domain.md:572`(D-5) 与错误码 `DEVICE_QUARANTINED`（`domain.md:858`）表达，无 schema 不变量阻止新租约。
9. **SR-14 仍开放**：`docs/v2`/`openspec` 四值回写未同步（`domain.md:590`、`evidence-verdict.md:810` 明示），不在本次 `docs/contracts/` 范围内复核。

## 6. 无法验证

- 服务端是否真的按 `domain.md:580`“服务端派生写入”从 L1 计算 L2，需实现代码；本包只有 schema/文档。
- 设备真机事实（T-10：`gpio`/`network`/`display` 是否可占用）无法从契约文本验证。
- 运行时“写出方只发权威词”和“隔离设备拒绝新派发”的准入逻辑无法由 schema 验证（见 §5.4、§5.8）。
- 仓库当前 `docs/contracts/` 为未跟踪目录（`git status` 显示 `?? docs/contracts/`），因此 `git diff --check` 只覆盖已跟踪文件；新报告另做尾随空白检查。

## 7. 执行过的验证

- `python3 -m json.tool docs/contracts/schemas/domain/lease.schema.json` → OK。
- `Draft202012Validator.check_schema` 遍历 35 个 schema → 35/35 通过，0 失败。
- 反例实例：lease RELEASED+OCCUPIED、lease QUARANTINED+IDLE、occupancy quarantined+IDLE、release released+leased 均被拒；对应合法实例通过（9/9 符合预期）。
- 身份/kind 互斥实例：域 lease 与 bundle 接受 kind、拒绝身份；wire lease 接受身份、拒绝 kind。
- `git diff --check` → 无输出（仅已跟踪文件）。
