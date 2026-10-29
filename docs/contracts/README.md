# NoahsArk 核心领域契约（v1.1）

> 状态：`frozen-candidate v1.1`，等待 Orchestrator/所有者评审。**不是已批准契约，不是已冻结契约**，不构成实现、测试、部署或发布授权。
> 契约版本：候选包 `1.1-candidate`；所有 schema 的载荷 `schema_version` 仍为 `"1.0"`。`1.1-candidate` 只表示首次冻结前的候选修订，不表示冻结、批准或生产版本。9 项裁决见 `docs/delivery/contract-adjudication-record.md`。
> 形成日期：2026-10-28；候选修订日期：2026-10-29。
> 适用版本：NoahsArk V0.0.1。
> 数据库：PostgreSQL 是唯一正式数据库。本目录不定义 SQLite、ORM 私有类型或供应商锁定结构。

## 1. 本目录的作用

本目录把已评审的 V0.0.1 需求、架构、模块业务逻辑收敛为**字段级候选契约**，供 UI、API、Linux 控制面、Windows Node Agent、证据与判定服务共同消费。契约只描述领域对象、字段、枚举、状态机、不变量和幂等/并发语义，不描述应用代码、数据库迁移或测试实现。

事实源优先级（冲突时从高到低）：

1. `.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md`（已批准需求基线）。
2. `.omo/plans/noahsark-platform-delivery.md` 与根 `plan.md` 中已确认的架构/模块/字段级评审记录。
3. `.omo/drafts/01-design/`、`.omo/drafts/02-delivery/` 中已同步批准边界的正文。
4. **本目录（`docs/contracts/`）**：对上述内容的字段化表达；与 1–3 冲突时以 1–3 为准。
5. `docs/v2/`、`openspec/`、`solutions/`：同步前仅作历史参考，**不得**把其中的 SQLite、租约到期即失败、证据全量上传后才释放等旧表述带入契约。

## 2. 文件索引

### 2.1 本工作单元（P0-04 核心领域契约）

| 文件 | 内容 | 状态 |
|---|---|---|
| `README.md` | 契约索引、版本规则、所有权、验证方式 | frozen-candidate v1.1 |
| `domain.md` | 实体字段表、枚举、状态机、不变量、门禁顺序、五轴判定、离线续跑、STOP-first、设备释放、错误码、幂等键、并发规则、决策记录 | frozen-candidate v1.1 |
| `schemas/domain/task.schema.json` | 任务身份与单 lead agent | frozen-candidate v1.1 |
| `schemas/domain/revision.schema.json` | 不可变修订与冻结范围 | frozen-candidate v1.1 |
| `schemas/domain/approval.schema.json` | 绑定冻结修订的一次有效审批 | frozen-candidate v1.1 |
| `schemas/domain/gate.schema.json` | G0–G7 门禁与顺序约束 | frozen-candidate v1.1 |
| `schemas/domain/case.schema.json` | 稳定 `case_id` 与随修订冻结的用例版本 | frozen-candidate v1.1 |
| `schemas/domain/run.schema.json` | static/smoke/formal 运行与执行/通信/占用分离 | frozen-candidate v1.1 |
| `schemas/domain/attempt.schema.json` | 单用例执行尝试与五轴状态 | frozen-candidate v1.1 |
| `schemas/domain/execution-bundle.schema.json` | Linux 生成并冻结的 NoahsArk Execution Bundle | frozen-candidate v1.1 |
| `schemas/domain/lease.schema.json` | 设备独占、epoch、占用与释放前置条件 | frozen-candidate v1.1 |
| `schemas/domain/device.schema.json` | 设备身份、能力、端点、健康、池状态 | frozen-candidate v1.1 |
| `schemas/domain/node.schema.json` | Windows 节点身份、通信、spool、交互会话 | frozen-candidate v1.1 |
| `schemas/domain/receipt.schema.json` | 节点执行事实与 cleanup 回执（不含最终判定） | frozen-candidate v1.1 |

### 2.2 同目录其他工作单元（只登记，不由本契约定义）

以下文件由并行工作单元产生，本 README 只做索引与交叉核对，不声称其内容已由本工作单元冻结：

| 文件 | 归属 | 关系 |
|---|---|---|
| `security-node.md`、`schemas/security/*.schema.json` | P0-05 节点身份与消息安全 | 线协议信封、签名、nonce、epoch、心跳、STOP。领域对象仍以 `schemas/domain/` 为准。 |
| `evidence-verdict.md`、`schemas/evidence/*.schema.json` | P0-06 证据与判定 | 证据 manifest、cleanup 回执、设备占用、五轴判定细节；与本文的设备释放/判定分离规则一致。 |
| `schemas/experience/*.schema.json` | P0-07 任务卡/报告/知识/审计 | 投影与审计对象；不得反向修改 `Task`/`Run` 权威状态。 |
| `thresholds.md`、`schemas/config/thresholds.schema.json` | P0-08 运行阈值 | 心跳/租约/离线重连、派发/STOP/退避、审批提醒、D:/spool、证据上传、日志查询、时钟/nonce、任务模板。数值复用 P0-05；优先级与硬边界以 `thresholds.md` §3/§13 为准。 |

### 2.3 跨契约对齐决定（frozen-candidate v1.1）

以下条目已在 `frozen-candidate v1.1` 内统一；仍需 Orchestrator 评审确认后才能视为冻结，不得据此声称已批准。R-01..R-03、C-01..C-06 的完整裁决、理由、兼容分类与必需测试见 `docs/delivery/contract-adjudication-record.md`。

1. **ID 表示（F-03）**：v1 只使用一种实体 ID 表示——canonical UUID（小写 RFC 9562 文本）。`schemas/domain/`、`schemas/security/`、`schemas/evidence/`、`schemas/experience/` 的 `task_id`/`revision_id`/`run_id`/`case_id`/`attempt_id`/`node_id`/`device_id`/`lease_id`/`evidence_id`/`receipt_id`/`manifest_id` 均强制 UUID。线协议不再静默接受前缀形式；`node_<hex>` 等旧前缀只允许作为显式、非权威的展示别名，任何 `wire_id` 必须与同一对象的 UUID 在同一结构中显式成对出现，且不得反向解析为领域身份。映射规则见 `security-node.md` §4.5。
2. **租约到期语义（F-11）**：`security-node.md` 已无 `lease_expired` 旧措辞；`schemas/security/lease.schema.json` 的 `state` 闭集仍含 `expired`，但仅表示 `expires_at` 续约截止，**不是所有权到期**。设备必须保持 `occupancy_state=OCCUPIED`，直到本地停止、安全清理、占用对账完成；不得据 `expired` 重派设备或判 run 失败。
3. **回执字段（F-07）**：`schemas/security/receipt.schema.json` 的 `outcome` 已全部改为 `node_observed_*`，并固定 `used_for_decision: false`。节点不写平台轴；Linux 独立复核后写入最终 `business_verdict`/`verification_status`。
4. **证据与判定**：`evidence-verdict.md` 已明确 cleanup 回执缺失不等于证据不完整；与本契约 `L-6`/`P-4` 一致。若后续出现“缺 cleanup 回执即证据不完整”的表述，以 `evidence-verdict.md` 和本契约为准。
5. **cleanup 回执投影（F-02 / R-02）**：`schemas/evidence/cleanup-receipt.schema.json` 是清理步骤/资源/状态的**唯一权威**定义。`schemas/security/receipt.schema.json` 的 `cleanup_receipt` 是 `schemas/domain/receipt.schema.json` 最小释放投影的**超集**（不是“同一投影”）：domain 只承载最小释放事实，并以 `additionalProperties: false` **显式拒绝** `operational_detail`。两侧共享的必填字段与 `cleanup_status` 词表必须逐字一致；security 侧 `operational_detail` 只是传输期便捷载体，入域前必须裁剪，**不得回写 domain**。跨侧转换必须按 `evidence-verdict.md` §12.1.1 逐字段进行，未知字段丢弃并审计。**历史记录（2026-10-28，已被 2026-10-29 裁决取代）**：原文曾称两侧“是同一最小释放投影”，并称详细运维字段可放在可选 `operational_detail` 下；该表述不再作为规范，保留以追溯。
6. **配置优先级层数（F-09）**：全目录统一为六层，从低到高：`schema_default < global_default < environment < task_revision < run_override < hard_safety_floor`。`node` 与 `environment` 是同一层；`schema_default` 是显式最低层。`thresholds.md` §3.1、`thresholds.schema.json` 的 `precedence.order` 与 `security-node.md` §16.2 使用同一顺序。
7. **协议/领域词汇映射（F-04/F-05/F-08）**：`security-node.md` §19.2 与 `domain.md` §12.3 给出 action/mode/status 与领域 receipt/run 词汇的显式映射；`evidence-verdict.md` §12.5 引用同一 `receipt.status` → `node_receipt.status` 映射。`on_lease_loss` 固定为 `continue_started_job`；显式撤销与安全事件使用独立的 `on_explicit_revoke`/`on_safety_incident` 原因。
8. **UI 投影词汇（F-06 / R-03）**：`ui-report-knowledge-audit.md` §2.7 现覆盖 **occupancy / communication / gate / run / evidence 五张表**，每张表都给出权威字段映射与禁止推断；`UNKNOWN` 只允许作为展示占位，不得写回 `Run`/`Attempt`/`verdict.axes` 的权威枚举。`report_scope.mode` 表示**报告覆盖范围**（`SMOKE`/`FORMAL`/`MIXED`），不是 `Run.mode`；`BLOCKED`/`STOPPED` 在过渡期保留为兼容值，同时由可选布尔 `contains_blocked`/`contains_stopped` 表达“报告覆盖的运行含阻断/停止”。最终 UI 词汇仍归 P1-08，本候选版本不主张 UI 已冻结。**历史记录（2026-10-28，已被 2026-10-29 裁决取代）**：原文曾提前声称覆盖五表而 §2.7 实际只有四表；补入 evidence 表后该覆盖声明才成立，原文保留以追溯。
9. **审批超时语义**：`thresholds.md` 明确“超时只提醒与升级，永不自动拒绝”，与 `test-strategy.md` 第 3.2 节一致；架构提案 §6 与模块设计 M-03 的旧措辞“提醒 → 升级 → 拒绝”需在同步时修正，历史评审记录保留。
10. **R-01 bundle 版本双轴**：`security/job.schema.json` 中 `payload.execution_bundle.schema_version` 的 `noahsark.execution-bundle/v1` 是**bundle 格式标识/引用命名空间**；`schemas/domain/execution-bundle.schema.json` 的 `schema_version: "1.0"` 是**载荷 schema 版本**。两者互不比较、互不推导；节点分别校验各自支持集合，任一未知即拒绝。错误表达复用控制面 `SCHEMA_VERSION_UNSUPPORTED` 与节点侧 `SCHEMA_INVALID`，两轴结果写入 `facts.bundle_format_supported`、`facts.bundle_payload_schema_supported`；不新增顶层错误码。
11. **R-03 证据轴与 UNKNOWN**：`UNKNOWN` 不是权威值。`execution_status`/`evidence_status`/`verification_status` 的展示 `UNKNOWN` 必须携带 `freshness` 与最后权威更新时间；写回权威时未知分别使用 `NOT_STARTED`/`INCOMPLETE`/`NOT_RUN`（`validity_status` 的 `UNKNOWN` 本身是权威枚举，例外）。
12. **C-01 mode 单一口径**：运行模式在所有权威层只有 `static`/`smoke`/`formal`。`static_check` 只存在于 `job.action` 与 `Receipt.job_kind`，**不是** mode；`diagnostics`/`cleanup` 只是辅助作业种类，不改变 `Run.mode`。证据 manifest/verdict/report-index 的 `$defs.mode` 已收敛为三值；旧 `static_check` 仅允许在显式兼容读模式中归一为 `static` 并记录告警，写出方只能写 `static`。
13. **C-02 失败词表**：domain `failure_classification` 的 8 个大写值是**唯一权威词表**；证据侧 `failure_class` 的小写值是显式序列化投影，不是第二套分类学。`none` 用省略 `failure_classification` 表达，`needs-review` 用 `business_verdict=NEEDS_REVIEW` + 未通过复核表达；任一层表外值 fail-closed 为 `NEEDS_REVIEW`，不得猜测为 `valid-failure` 或 `none`。
14. **C-03 lease.state 映射**：线协议 6 值 `granted/renewed/released/expired/revoked/reclaimed` 到领域 `Lease.state` 的固定映射与守卫见 `security-node.md` §19.2 与 `domain.md` §11.2。`expired` 永不释放、不判失败、不重派；`released` 只是释放主张，必须通过三项 `release_preconditions` 才落 `RELEASED`；表外值不改变当前状态且禁止新派发。
15. **C-04 endpoint kind 与 endpoint identity**：`endpoint_kind` 是能力类别（权威集合 `audio_capture`/`audio_playback`/`serial`/`usb`/`gpio`）；`endpoint_set` 是**端点身份集合**（`endpoint_id`，线协议为 `endpoint_<32hex>`），用于占用键与证据归属，**不得**再承载 kind。`audio_input→audio_capture`、`audio_output→audio_playback` 仅为入站别名，入域前归一，写出方只发权威词。`network`/`display`/`gpio` 是否可占用仍由 T-10 真机事实确认，当前按“能力标识、不作为 V0.0.1 可占用端点”处理。
16. **C-05 占用三层**：L1 权威为 `Lease.state`（6 值）+ `Device.pool_state`（8 值）+ `release_preconditions`；L2 粗投影 `occupancy_state` 只有 `IDLE`/`OCCUPIED`/`RELEASING`；L3 的 `docs/v2`/`openspec` 四值枚举与 `device-occupancy.state` 十值细化只是展示/证据细化。`RELEASED` 属 `Lease.state`/`release_state`，`QUARANTINED` 属 `Device.pool_state`/`Lease.state`；候选 schema 已加入 `QUARANTINED → occupancy_state=OCCUPIED` 的收紧约束。
17. **C-06 case_version**：`case_version` 在所有层为 `integer ≥ 1`，是 `run_id + case_id + case_version + attempt` 连接键。evidence manifest 与 verdict 已改为整数；仅显式兼容读模式可接受规范十进制字符串并记录 `legacy_case_version_coerced` 告警，默认严格模式拒绝字符串，禁止隐式 `parseInt`。
18. **候选版本与兼容分类**：R-01/R-02/R-03/C-02/C-03 为文档或 schema `description` 级变更，保持 `1.x` 兼容；C-01/C-04/C-05/C-06 属类型、枚举成员或约束的破坏性/收紧变更，因当前无已冻结修订、无已接收证据，统一按“**首次冻结前 v1 修正**”处理并记录在 `docs/delivery/contract-adjudication-record.md`。该认定不代表冻结或批准；若未来冻结后再出现同类变更，必须按 §3.4 提升 `2.0`。

## 3. 版本规则

1. **契约版本与产品版本分离**：契约 `1.0` 可服务多个产品补丁版本；产品版本不得静默改变字段语义。
2. **`schema_version` 是载荷的一部分**，不是文件名版本。同一实体载荷缺失或未知 `schema_version` 时按 fail-closed 处理。
3. **向后兼容变更**（仅新增可选字段、放宽枚举的只读消费者）可发布 `1.x`；每个 minor 升级必须在 `domain.md` 变更记录登记。
4. **破坏性变更**（删除/重命名字段、改变类型、收紧必填、改变状态含义、改变幂等键）必须发布 `2.0`，并保留 `1.x` 只读解析器直至所有历史证据不再需要回放。
5. **已冻结修订与已接收证据不可被新契约回写**：新契约只影响新对象；历史对象按其 `schema_version` 解释。
6. **枚举扩展**：新增枚举值属于兼容变更，但消费者必须把未知值视为 `UNKNOWN`/`NEEDS_REVIEW`，不得猜测为 PASS。
7. **schema 文件不可原地覆盖历史版本**：如需保留旧版，复制到 `schemas/domain/v1/` 或提升主版本，不在本目录创建平行重复定义。
8. **候选包版本与载荷版本分离**：`1.1-candidate` 是本候选契约包的修订标识，不是载荷 `schema_version`。当前所有载荷仍为 `"1.0"`，因为 9 项裁决属于首次冻结前修正、且无已冻结修订/已接收证据；该认定必须与本文件 §2.3 第 18 条及裁决记录一致。不得据 `1.1-candidate` 声称契约已冻结、已批准或可生产使用。

## 4. 所有权与消费方

| 对象 | 写入方（唯一权威） | 只读消费方 |
|---|---|---|
| Task / Revision / Approval / Gate | Linux 控制面 | UI、API、Lead 会话桥、报告 |
| Execution Bundle | Linux 控制面（生成、修复、审核、版本化、冻结） | Windows Node Agent（只校验和执行） |
| Run / Attempt | Linux 控制面（编排与判定） | UI、报告、任务卡、知识服务 |
| Case | Linux 控制面（随 revision 冻结 `case_version`） | UI、生成器、报告 |
| Lease / Device / Node | Linux 控制面（租约与占用）；Node Agent 只回传节点/设备事实 | UI、调度、任务卡 |
| Receipt | Windows Node Agent 产生事实；Linux 控制面校验、去重、对账后入库 | UI、证据服务、审计 |
| 五轴最终判定 | **Linux 控制面独占** | UI、报告、知识、API |

硬边界：Windows Node Agent 不得写 `business_verdict`、`verification_status` 或最终 PASS/FAIL；节点回执只证明执行、设备、清理和证据引用事实。

## 5. 验证方式

在仓库根目录执行：

```bash
for f in docs/contracts/schemas/*/*.schema.json; do
  python3 -m json.tool "$f" > /dev/null || exit 1
done

python3 - <<'PY'
import glob, json
from jsonschema import Draft202012Validator
for path in sorted(glob.glob("docs/contracts/schemas/*/*.schema.json")):
    with open(path, encoding="utf-8") as fh:
        schema = json.load(fh)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema", path
    Draft202012Validator.check_schema(schema)
    print("OK", path)
PY
```

验收口径：

- 全包 **35 个 schema** 全部存在（`config` 1 + `domain` 12 + `evidence` 7 + `experience` 6 + `security` 9）；本次 9 项裁决不新增、不删除 schema。
- 12 个 domain 实体 schema 全部存在且一一对应本文同一对象。
- 每个文件可被 `python3 -m json.tool` 解析（35/35）。
- 每个文件通过 `Draft202012Validator.check_schema`。
- `grep -RIn "sqlite" docs/contracts/` 只允许出现在“禁止/历史参考”说明中，不得出现在 schema 或字段定义中。

## 6. 明确不包含

- 不包含应用代码、数据库 DDL、迁移脚本、API 路由、UI 组件或测试实现。
- 不包含生产密钥、证书、真实设备序列号、真实节点值或凭据。
- 不包含签名算法、证书链、超时数值、容量阈值、样本量、重试次数等运行参数；这些由 `P0-05`/`P0-08` 与任务级批准另行冻结。
- 不宣称任何需求已实现、测试已通过、部署已完成或获得发布授权。

## 7. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0-candidate.1 | 2026-10-28 | 首次形成 task/revision/run/case/attempt/execution bundle/approval/gate/lease/device/node/receipt 字段级候选契约；显式修正 SQLite、`lease_expired`、`INFRA_ERROR`、`cleanup_receipt`、`successor` 旧冲突。 |
| 1.1-candidate | 2026-10-29 | 所有者授权裁决 R-01..R-03、C-01..C-06，形成 `frozen-candidate v1.1` 候选基线：bundle 双版本轴、cleanup 超集投影、evidence 轴与 UNKNOWN 边界、mode 收敛为 static/smoke/formal、失败词表双向映射、线协议 lease.state 映射、endpoint kind/身份拆分、占用三层与 `QUARANTINED` 不变量、`case_version` 整数统一。裁决与测试要求见 `docs/delivery/contract-adjudication-record.md`。仍**未生产冻结，Phase 0 未关闭**。 |
