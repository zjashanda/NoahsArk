# 证据、清理回执、设备占用与五轴判定契约 v1.1

> 状态：`frozen-candidate v1.1`（候选修订；**not production-frozen; Phase 0 not closed**），2026-10-28 形成、2026-10-29 裁决更新。
> 本文件是待评审的契约候选，**未获所有者批准，不是最终冻结版本**，不构成实现、测试、部署或发布授权。
> 规范来源：已批准需求基线（第 3、9、10、11、12、13、15 节）、方案 B 架构 B-1 至 B-7、模块逻辑 M-05/M-06/M-07、施工验收 v2.2 第 2.1/3/4 节、测试策略 v2.2 第 3.3/3.4/3.8/4.3 节。
> 机器可读定义：`docs/contracts/schemas/evidence/` 下 7 个 JSON Schema（Draft 2020-12）。
> 本契约不复制架构文档旧不变量 I-21 的措辞。I-21 将“缺失 cleanup 回执”写成“视为证据不完整”，与已批准规则冲突；本契约以第 12、13、17 节替代它，I-21 须在后续文档同步中改写。

---

## 0. 关键结论（TL;DR）

1. **三个平面彼此独立**：证据完整性（`evidence_status`）、设备释放（`device_release`）、最终判定（`verdict.decision`）分别建模、分别记录、分别审计。任何一个平面的状态都不能代替另一个。
2. **缺 cleanup 回执不自动等于证据不完整**。缺回执只表示“设备释放无法确认”，设备继续保持占用；证据完整性仍按必需证据集独立计算。
3. **只有必需证据缺失、必需证据摘要失败、或必需证据关联/来源失败会阻塞 PASS**。可选诊断日志缺失、归档不可用、按需读取失败（非必需时）不阻塞 PASS。
4. **正式 PASS 需要五项同时成立**：正式模式、执行完成、样本有效、业务通过、必需证据完整且经 Linux 独立复核通过。设备是否已释放**不是** PASS 的前提。
5. **烟测永不进入正式分母**。烟测可以有 `mode_outcome=PASS`，但 `decision` 恒为 `NOT_APPLICABLE`、`formal_pass=false`。
6. **Windows 自报 PASS 不是判定输入**。节点只回传事实；最终五轴与 `decision` 由 Linux 判定服务写入。
7. **按需读取不是备份**。Linux 通过白名单读取 Windows D: 日志可以形成可核验证据，但不满足归档/保留要求，节点丢失后未读取部分即丢失。
8. **清理失败不是 `invalid-evidence`**。清理失败触发设备隔离与人工复核（`NEEDS_REVIEW`），不把业务结果自动改写为失败，也不把证据状态自动改写为不完整。

---

## 1. 术语

| 术语 | 含义 |
|---|---|
| 证据项（evidence item） | 一次运行中可单独寻址、可单独校验的原始材料或结构化记录。 |
| 必需证据（required evidence） | 由冻结执行包/任务级 profile 声明、当前验收层级与运行模式要求的证据项。缺一即不得 PASS。 |
| 可选诊断证据（optional diagnostic） | 有助排障但不进入必需集；缺失只记录，不阻塞 PASS。 |
| 支撑证据（supporting） | 人工说明、补充截图等；可解释结果，但不能替代客观证据产生自动 PASS。 |
| 证据清单（manifest） | 一次运行的全部证据项、分母、异常、回执引用与完整性结论的结构化索引。 |
| 内容摘要（content digest） | 对原始字节或规范化 JSON 计算的 SHA-256 值。 |
| 内容寻址（content-addressed） | 以内容摘要定位不可变 blob 的存储方式；移动 locator 不改变证据身份。 |
| 清理回执（cleanup receipt） | 节点对“停止、清理、资源释放、设备安全状态”的事实回执。 |
| 设备占用（device occupancy） | 设备被某任务/租约/运行持有的状态；与通信在线状态分离。 |
| 设备释放（device release） | 控制面确认设备可再次分配。释放是独立决定，不等于 PASS。 |
| 五轴（five axes） | `execution_status`、`validity_status`、`business_verdict`、`evidence_status`、`verification_status`。 |
| 最终判定（verdict decision） | 由五轴、前置条件、分母资格和异常处置派生出的单一结论。 |
| Linux 独立复核 | Linux 控制面在不采信节点自报结论的前提下，重算摘要、重建关联、复算分母并复评 oracle。 |
| 正式分母（formal denominator） | 仅包含 `mode=formal` 且 `validity=VALID` 且必需证据完整的有效样本。 |

**标识符约定**：`evidence_id`、`manifest_id`、`cleanup_receipt.receipt_id`、`verdict_id`、`verification_id`、`occupancy_id`、`report_id` 在 schema 中强制为 RFC 9562 UUID（规范小写），与 P0-04 领域契约中 `evidence_id`、`cleanup_receipt_id`、`evidence_manifest_id` 的 UUID 约定一致。示例中的 `task_id/revision_id/run_id/case_id` 使用可读占位符；生产载荷同样使用 UUID，消费方按字符串关联，不以可读前缀作为身份。

---

## 2. 不可协商原则

| ID | 原则 | 说明 |
|---|---|---|
| P-01 | fail closed | 任一必需前置条件无法验证时，不得 PASS；只能标记待核验、阻塞、无效或需复核。 |
| P-02 | 三平面分离 | 证据完整性、设备释放、最终判定各自有独立字段、独立状态机、独立审计事件。 |
| P-03 | 节点只报事实 | Windows Node Agent 不写最终 `business_verdict`、`verification_status` 或 `decision`。 |
| P-04 | 证据不可变 | 已登记证据不得原地覆盖；更正以新证据项 + `supersedes` 表达。 |
| P-05 | 独立重算 | Linux 消费前必须重算摘要、校验大小、校验关联、重建分母；不信任节点摘要。 |
| P-06 | 烟测隔离 | 烟测运行使用独立 `run_id`，永不进入正式分母。 |
| P-07 | 释放不等于通过 | 设备释放只说明可再分配，不说明证据完整、业务通过或判定成立。 |
| P-08 | 归档不等于判定 | 归档状态只影响保留与删除，不回溯改变已作出的判定。 |
| P-09 | 读取不等于备份 | 远程按需读取是核验路径，不是异机副本、归档或容灾。 |
| P-10 | 可追溯 | 每个结论必须能回到 `task_id/revision_id/run_id/case_id/evidence_id` 和规则版本。 |

---

## 3. 证据分类

### 3.1 十类证据

| `evidence_class` | 中文名 | 典型内容 | 产生方 | 默认可变性 | 默认访问等级 |
|---|---|---|---|---|---|
| `raw_audio` | 原始音频 | 设备播放音频、麦克风采集、回环录音、录音器输出 | Windows Node Agent / lstest 适配器 | 不可变 | `evidence_reader` |
| `device_log` | 设备日志 | 设备侧完整日志、D: 大日志、设备诊断导出 | Windows Node Agent | 不可变 | `evidence_reader` |
| `serial_log` | 串口日志 | 串口原始字节流、连续设备事实 | Windows Node Agent / lstest 适配器 | 不可变 | `evidence_reader` |
| `screenshot` | 截图 | 屏幕、UI、设备状态、播放器画面 | Windows Node Agent | 不可变 | `evidence_reader` |
| `execution_log` | 执行日志 | `tool.log`、`results.jsonl`、`events.jsonl`、`actions.jsonl`、`cases.csv`、`results.csv`、静态检查输出 | Linux 控制面 / Windows Node Agent / lstest 适配器 | 不可变 | `task_member`（原始行可升为 `evidence_reader`） |
| `manifest` | 证据清单 | `run_manifest.json`、本契约的 evidence manifest、契约清单 | Linux 控制面 | 不可变 | `task_member` |
| `receipt` | 回执 | cleanup receipt、node receipt、job receipt、STOP 回执 | Windows Node Agent | 不可变 | `task_member` |
| `anomaly_event` | 异常事件 | 节点主动上报事件、Linux 日志复核确认事件、设备级安全事件 | Windows Node Agent / Linux 控制面 | 只追加，不删除 | `task_member` |
| `linux_log_read` | Linux 日志读取记录 | 白名单查询参数、读取区间、读取摘要、读取结果 | Linux 控制面 | 不可变 | `evidence_reader` |
| `human_note` | 人工记录 | 评审意见、人工喊测记录、主观体验、复用说明 | 人类用户 | 不可变（更正另立新项） | `task_member` |

**边界**：

- `human_note` 可以满足 L0/L5 的过程证据，但**永远不能单独构成正式业务 PASS 的依据**。
- `manifest`、`receipt`、`verification record` 是结构化控制记录；其中 `manifest` 与 `receipt` 属于证据类，`verification record` 是判定审计记录，不进入证据类枚举。
- `report-evidence-index` 是报告投影，不是原始证据；它引用证据，不替代证据。

### 3.2 证据角色

| `role` | 含义 | 对 PASS 的影响 |
|---|---|---|
| `required` | 当前运行模式/验收层级/任务 profile 的必需证据。 | 缺失、摘要失败或关联失败 → 不得 PASS。 |
| `optional_diagnostic` | 排障用，不进入必需集。 | 缺失只记录，不阻塞。 |
| `supporting` | 解释性材料。 | 不能单独支撑自动 PASS。 |
| `derived` | 由其他证据复算/汇总得到。 | 必须能回到上游证据；上游缺失时 derived 也无效。 |

### 3.3 一个证据项“存在”的定义

证据项只有在同时满足以下条件时才计为“已核验存在”：

1. `state = verified`；
2. `content_digest` 与 Linux 重算结果一致；
3. `size_bytes` 与存储对象一致；
4. `provenance` 完整且与 `task_id/revision_id/run_id/node_id/device_identity` 关联一致；
5. 对 `required` 证据，`locator` 可解析且内容可取回（本地内容寻址副本，或已验证的按需读取记录）。

`declared`、`uploading`、`partial`、`complete`（尚未核验）都**不**计为已核验存在。

---

## 4. 运行模式、验收层级与测试层级

### 4.1 运行模式

| `mode` | 是否接触真实设备 | 是否可产生正式判定 | 是否进入正式分母 |
|---|---|---|---|
| `static` | 否 | 否 | 否 |
| `smoke` | 是 | 否（只有 `mode_outcome`） | **永不** |
| `formal` | 是 | 是（且满足全部前置条件） | 满足有效性+证据完整性时进入 |

> **C-01 更正（2026-10-29）**：历史表述（2026-10-28 及之前）曾把 `static_check` 作为 `mode` 值。自 v1.1-candidate 起，`mode` 在所有层只有 `static`/`smoke`/`formal`；`static_check` 仅作为 `Job.action` / `Receipt.job_kind` 存在。旧值仅允许显式兼容读入为 `static` 的只读别名，并记录告警；写出方只写 `static`。原表述保留为历史记录，不再生效。

### 4.2 L0–L5 验收层级

| 层级 | 证明什么 | 必需证据（判定） | 释放证据 | 可选诊断 | 不能证明什么 |
|---|---|---|---|---|---|
| L0 文档契约 | 字段、状态、口径一致 | `human_note`（评审记录）、`manifest`（契约清单） | 无 | `execution_log` | 系统可运行；设备可用；证据可复算 |
| L1 静态验证 | 无硬件逻辑自洽 | `execution_log`（静态检查/preflight 输出）、`manifest` | 无 | — | 设备可用；音频链路可用；会话可用 |
| L2 模拟链路 | 门禁、判定、恢复逻辑正确 | `execution_log`、`manifest`、`receipt`（模拟清理）、`anomaly_event`（注入故障时） | `receipt`（仅验证清理契约） | `screenshot`、`device_log`（假节点） | 真实设备/音频/时序；模拟回执不是真实释放证据 |
| L3 真机烟测 | 端到端链路可跑通 | `execution_log`、`serial_log`、`raw_audio`、`manifest` | `receipt`、`execution_log`（停止/清理事实） | `screenshot`、`device_log`、`anomaly_event` | 正式样本有效性；样本量代表性；正式 PASS；烟测不计入正式分母 |
| L4 正式采样 | 批准边界内判定有效 | `raw_audio`、`device_log`（必需切片）、`serial_log`、`execution_log`、`manifest`、`anomaly_event`（发生时）、`linux_log_read`（依赖远程读取时） | `receipt`、`execution_log` | `screenshot`、`human_note` | 其他设备/固件；长期稳定性；未测试场景 |
| L5 端到端场景 | 业务闭环可用、第二任务可复用 | L4 全部 + `human_note`（复用评审） | `receipt`、`execution_log` | `screenshot` | 长期稳定性；跨项目泛化；未纳入的设备 |

**规则**：

- 不得用 L0–L2 的证据声称 L3–L5 完成。
- 不得用 L3（烟测）样本拼 L4 正式分母。
- `device_log` 的“必需切片”由冻结 profile 的 `evidence_requirements` 声明；完整 GB 级大日志不自动成为必需证据。
- `anomaly_event` 在“发生异常”时成为该运行的必需证据；无异常时不需要空事件。
- `linux_log_read` 在必需日志只能远程读取时成为必需证据；详见第 10 节。
- 本表以语音交互任务为默认；非语音任务仍只能从同一 10 类证据中选取，由冻结 profile 的 `evidence_requirements` 显式声明，不得用默认表替代任务级声明。
- L0 的 `manifest` 是“契约清单/评审清单”，可用一个 `case` 表示本次评审；它不是运行证据，也不证明系统可运行。

### 4.3 T1–T6 测试层级

| 层级 | 对象 | 必需证据（判定） | 释放证据 | 可选诊断 | 不能证明什么 |
|---|---|---|---|---|---|
| T1 单元 | 判定规则、分母、状态机 | `execution_log`（覆盖/用例报告）、`manifest` | 无 | `human_note` | 模块协作；真实设备 |
| T2 契约 | 命令/事件/作业/回执/manifest | `execution_log`（契约一致性报告）、`manifest`、`human_note`（评审签署） | 无 | — | 集成行为；真实设备 |
| T3 集成 | 控制面模块协作 | `execution_log`、`manifest`、`anomaly_event`（注入时） | 无 | `device_log` | 真实音频；语音业务 |
| T4 模拟 E2E | 全链路（假节点） | `execution_log`、`manifest`、`receipt`、`anomaly_event` | `receipt`（模拟） | `screenshot`、`device_log` | 真实设备/音频/时序 |
| T5 真机烟测 | 节点+设备链路 | 同 L3 | 同 L3 | 同 L3 | 同 L3 |
| T6 正式验收 | 语音任务正式采样 | 同 L4 | 同 L4 | 同 L4 | 同 L4 |

### 4.4 模式 × 层级组合约束

- `static` 只能对应 L0/L1/T1/T2/T3；不得对应 L3–L5 或 T5/T6。静态检查的作业种类仍是 `job.action=static_check`，其运行 mode 是 `static`（C-01）。
- `smoke` 只能对应 L3/T5（或 L2/T4 的模拟烟测）；不得对应 L4/T6。
- `formal` 对应 L4/T6；L5 可在 formal 通过后作为业务闭环补充验收，但 L5 不能替代 L4/T6 的正式判定。
- 一个 `run_id` 只允许一个 `mode`；烟测与正式采样必须是不同 `run_id`。

---

## 5. 证据清单（manifest）结构

### 5.1 顶层结构

```json
{
  "schema_version": "1.0",
  "predicate_type": "noahsark.test-evidence/v1",
  "manifest_id": "44444444-4444-4444-8444-444444444444",
  "task_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "revision_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "run_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  "mode": "formal",
  "acceptance_level": "L4",
  "test_level": "T6",
  "node_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
  "device_identity": {
    "device_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    "model": "example-model",
    "serial": "SN-0001",
    "firmware": "1.2.3",
    "endpoints": ["audio_out:speaker-1", "serial:COM3"]
  },
  "lease_id": "ffffffff-ffff-4fff-8fff-ffffffffffff",
  "lease_epoch": 7,
  "endpoints": ["audio_out:speaker-1", "serial:COM3"],
  "bundle": {
    "bundle_id": "12121212-1212-4212-8212-121212121212",
    "digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111"
  },
  "approval": {
    "approval_id": "13131313-1313-4313-8313-131313131313",
    "scope_digest": "sha256:2222222222222222222222222222222222222222222222222222222222222222"
  },
  "timebase": {
    "started_at": "2026-10-28T06:30:00Z",
    "finished_at": "2026-10-28T07:10:00Z",
    "clock_source": "linux_ntp",
    "max_drift_ms": 50
  },
  "cases": [
    {
      "case_id": "14141414-1414-4414-8414-141414141414",
      "case_version": 1,
      "attempt": 1,
      "execution_status": "COMPLETED",
      "validity_status": "VALID",
      "business_verdict": "PASS",
      "evidence_status": "COMPLETE",
      "required_evidence_ids": ["11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"],
      "observed_evidence_ids": ["11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"],
      "denominator_eligible": true
    }
  ],
  "evidence_items": [
    {
      "schema_version": "1.0",
      "evidence_id": "11111111-1111-4111-8111-111111111111",
      "evidence_class": "raw_audio",
      "role": "required",
      "state": "verified",
      "content_digest": "sha256:3333333333333333333333333333333333333333333333333333333333333333",
      "size_bytes": 1048576,
      "media_type": "audio/wav",
      "digest_scope": "raw_bytes",
      "provenance": {
        "producer": "windows_node_agent",
        "producer_version": "0.1.0",
        "captured_at": "2026-10-28T06:31:00Z",
        "received_at": "2026-10-28T06:32:00Z",
        "task_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "revision_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "run_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "case_id": "14141414-1414-4414-8414-141414141414",
        "attempt": 1,
        "node_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "device_identity": {
          "device_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
          "model": "example-model",
          "serial": "SN-0001",
          "firmware": "1.2.3",
          "endpoints": ["audio_out:speaker-1"]
        },
        "bundle_id": "12121212-1212-4212-8212-121212121212",
        "bundle_digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
        "job_id": "15151515-1515-4515-8515-151515151515",
        "lease_id": "ffffffff-ffff-4fff-8fff-ffffffffffff",
        "lease_epoch": 7,
        "clock_source": "node_monotonic",
        "timebase_id": "tb-0001",
        "max_clock_drift_ms": 50,
        "trust_level": "recomputed"
      },
      "access_level": "evidence_reader",
      "locator": {
        "kind": "content_addressed",
        "uri": "sha256/33/33333333333333333333333333333333333333333333333333333333333333",
        "available": true,
        "checked_at": "2026-10-28T07:11:00Z"
      },
      "upload": {
        "chunk_size_bytes": 1048576,
        "chunks_total": 1,
        "chunks_received": 1,
        "bytes_received": 1048576,
        "sessions": [
          {
            "upload_id": "up-0001",
            "started_at": "2026-10-28T06:32:00Z",
            "finished_at": "2026-10-28T06:32:05Z",
            "resume_offset": 0,
            "status": "finished"
          }
        ]
      },
      "retention": {
        "class": "hot_30d",
        "hot_until": "2026-11-27T06:32:00Z",
        "archive_state": "pending",
        "archive_uri": null,
        "archive_verified_at": null
      },
      "integrity": {
        "digest_verified_at": "2026-10-28T07:10:30Z",
        "verified_by": "linux_verifier_service",
        "mismatch": false
      },
      "created_at": "2026-10-28T06:32:00Z"
    }
  ],
  "required_evidence": {
    "rule_set_id": "evidence-rules-0001",
    "rule_set_digest": "sha256:4444444444444444444444444444444444444444444444444444444444444444",
    "classes": ["raw_audio", "device_log", "serial_log", "execution_log", "manifest"],
    "evidence_ids": ["11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"],
    "missing_ids": [],
    "optional_missing_ids": []
  },
  "completeness": {
    "result": "COMPLETE",
    "required_total": 2,
    "required_present": 2,
    "required_verified": 2,
    "required_missing": [],
    "optional_missing": [],
    "digest_failures": [],
    "conflict_ids": []
  },
  "denominators": {
    "planned": 1,
    "executed": 1,
    "valid": 1,
    "invalid": 0,
    "blocked": 0,
    "stopped": 0,
    "infra_error": 0,
    "formal": 1,
    "per_device": { "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee": 1 },
    "per_case": { "14141414-1414-4414-8414-141414141414": 1 }
  },
  "invalid_classification": {
    "counts": {},
    "details": []
  },
  "anomalies": {
    "blocking_ids": [],
    "non_blocking_ids": []
  },
  "cleanup_receipt": {
    "receipt_id": "55555555-5555-4555-8555-555555555555",
    "receipt_digest": "sha256:5555555555555555555555555555555555555555555555555555555555555555",
    "cleanup_status": "completed"
  },
  "node_receipt": {
    "receipt_id": "77777777-7777-4777-8777-777777777777",
    "receipt_digest": "sha256:6666666666666666666666666666666666666666666666666666666666666666",
    "status": "completed",
    "signed_at": "2026-10-28T07:10:10Z",
    "signature_key_id": "node-key-01"
  },
  "linux_verification": {
    "verification_id": "66666666-6666-4666-8666-666666666666",
    "verification_digest": "sha256:7777777777777777777777777777777777777777777777777777777777777777",
    "result": "PASS"
  },
  "archive": {
    "state": "pending",
    "archive_uri": null,
    "verified_at": null,
    "verified_by": null
  },
  "redaction": {
    "policy_id": "redaction-default-v1",
    "applied": true,
    "redacted_paths": ["evidence/tools/provider_token.txt"]
  },
  "manifest_digest": "sha256:8888888888888888888888888888888888888888888888888888888888888888",
  "created_at": "2026-10-28T07:11:00Z",
  "created_by": "linux-control-plane"
}
```

### 5.2 必填与条件必填

| 字段 | 必填性 | 说明 |
|---|---|---|
| `schema_version` | 必填 | 固定 `"1.0"`。 |
| `predicate_type` | 必填 | 固定 `"noahsark.test-evidence/v1"`。 |
| `manifest_id` | 必填 | 清单身份；不可复用。 |
| `task_id/revision_id/run_id` | 必填 | 与冻结边界一致；不一致即拒绝消费。 |
| `mode` | 必填 | `static/smoke/formal`。 |
| `acceptance_level/test_level` | 必填 | 声明本次运行对应层级。 |
| `node_id/device_identity` | 必填 | 无设备的层级允许 `node_id=null`，但必须显式写 null 并说明。 |
| `timebase` | 必填 | 开始/结束、时钟源、最大漂移。 |
| `cases` | 必填 | 每 case 的尝试与五轴快照。 |
| `evidence_items` | 必填 | 可内嵌完整证据项，也可由 `$ref` 指向独立文档；本契约采用内嵌 + `$id` 可引用。 |
| `required_evidence` | 必填 | 必需规则集与证据 ID；缺规则集即 fail closed。 |
| `completeness` | 必填 | 必需集计算结果；`COMPLETE` 才可能 PASS。 |
| `denominators` | 必填 | 分母口径；`formal` 只统计有效正式样本。 |
| `cleanup_receipt` | 条件必填 | 有设备动作时必须引用；无设备动作或静态检查可为 null，但须显式 null。 |
| `node_receipt` | 条件必填 | 真实节点运行必须有；无节点层级可为 null。 |
| `linux_verification` | 条件必填 | 申请 PASS 或进入正式分母时必须非 null。 |
| `manifest_digest` | 条件必填 | `completeness.result=COMPLETE` 时必须非 null。 |
| `archive` | 必填 | 归档状态独立于判定；可 `pending`。 |

### 5.3 消费前置校验

Linux 在把 manifest 作为判定输入前必须依次执行：

1. **schema 校验**：Draft 2020-12 校验通过。
2. **摘要校验**：重算 `manifest_digest`，与声明一致。
3. **关联校验**：`task_id/revision_id/run_id/bundle_id/approval_id/lease_id/lease_epoch` 与冻结边界、租约记录一致。
4. **路径安全**：所有 locator 必须是运行内相对路径或内容寻址键；拒绝绝对路径、`..`、符号链接逃逸。
5. **证据重算**：对每个 `required` 证据重算 `content_digest` 与 `size_bytes`。
6. **必需集校验**：`required_evidence.evidence_ids` 与实际证据一一对应；缺失即 `INCOMPLETE`。
7. **分母校验**：`mode=smoke` 的样本不得出现在 `formal` 分母。
8. **异常处置校验**：`blocking_ids` 必须有处置记录；未处置即不得 PASS。
9. **复核引用校验**：`linux_verification.result=PASS` 且 `verification_digest` 与复核记录一致。

任一步失败 → `evidence_status` 不得为 `COMPLETE`，`decision` 不得为 `PASS`。

---

## 6. 摘要、规范化与内容寻址

### 6.1 算法

| 项目 | 规定 |
|---|---|
| 哈希算法 | SHA-256（FIPS 180-4）。 |
| 表示 | 小写十六进制，前缀 `sha256:`，共 71 字符。 |
| 原始字节证据 | 对**原始字节**直接计算；不做换行转换、不裁剪空白、不重新编码。文本日志保持原始行尾（CRLF/LF）。 |
| 结构化证据 | 对 RFC 8785 JSON Canonicalization Scheme（JCS）规范化后的 UTF-8 字节计算。 |
| 域分隔 | 结构化证据在规范化字节前拼接 `noahsark/v1/<type>\n`；`<type>` ∈ `evidence-manifest`、`cleanup-receipt`、`verdict`、`verification-record`、`report-evidence-index`。 |
| 空文件 | 允许，摘要为 SHA-256 空串 `e3b0c442...b855`。 |
| 流式计算 | 大文件必须流式计算，不得整文件载入内存。 |
| 分片 | 每片独立 SHA-256；整文件摘要必须等于按序拼接后的 SHA-256；片索引、偏移、长度必须连续且无重叠。 |

### 6.2 摘要覆盖范围

| 对象 | 摘要字段 | 覆盖内容 | 不覆盖 |
|---|---|---|---|
| 原始证据项 | `content_digest` | 完整原始字节。 | locator、访问等级、保留状态、标签。 |
| manifest | `manifest_digest` | 除 `manifest_digest` 与 `signatures` 外的全部字段（JCS）。 | 签名本身、传输元数据。 |
| cleanup receipt | `receipt_digest` | 除 `receipt_digest` 与 `signature` 外的全部字段（JCS）。 | 签名本身。 |
| verdict | `verdict_digest` | 除 `verdict_digest` 外的全部字段（JCS）。 | 展示层字段。 |
| verification record | `verification_digest` | 除 `verification_digest` 与 `signature` 外的全部字段（JCS）。 | 签名本身。 |
| report index | `report_digest` | 除 `report_digest` 外的全部字段（JCS）。 | 展示层排序。 |

**规则**：

- `manifest_digest` 不覆盖 `signatures`，否则签名与摘要循环依赖；签名载荷必须显式包含 `manifest_digest`。
- 证据项的 `content_digest` 不覆盖 `evidence_id`、`role`、`access_level`、`retention`；这些是控制元数据，不是内容。
- `evidence_id` 一旦分配不可更改；内容变更必须新建证据项并用 `supersedes` 指向旧项。

### 6.3 内容寻址与不可变

- Blob 存储键：`sha256/<前两位>/<完整十六进制>`。
- 同一 `content_digest` 的重复内容只存一份 blob；不同 `evidence_id` 可以引用同一 blob，但逻辑角色分别计算。
- Blob 写入后只读；删除必须经过保留策略与审计，且不得删除仍被未结案运行引用的 blob。
- 归档只更新 `locator`，不改变 `evidence_id` 与 `content_digest`。
- 任何“修复证据”的行为都必须产生新证据项；禁止原地重写、截断、补写或重新编码。

### 6.4 不信任节点摘要

- 节点回执中的摘要只作为声明；Linux 必须重算后才可写入 `integrity.digest_verified_at`。
- 节点签名只证明“该节点在该时刻声明了该摘要”，不证明内容真实、完整或未被设备侧篡改。
- 摘要不一致时，不得用节点摘要覆盖 Linux 重算值；该证据项进入 `conflicted`。

---

## 7. 来源与信任链

### 7.1 来源字段

每个证据项必须携带 `provenance`：

| 字段 | 说明 |
|---|---|
| `producer` | `windows_node_agent`、`lstest_adapter`、`linux_control_plane`、`linux_verifier`、`human`。 |
| `producer_version` | 产生方版本；与冻结包记录一致。 |
| `captured_at` | 采集发生时间（产生方时钟）。 |
| `received_at` | Linux 接收时间。 |
| `task_id/revision_id/run_id` | 必须与 manifest 一致。 |
| `case_id/attempt` | case 级证据必填；运行级证据可为 null。 |
| `node_id/device_identity` | 设备相关证据必填；纯 Linux 证据可为 null。 |
| `bundle_id/bundle_digest` | 产生该证据的冻结执行包。 |
| `job_id/lease_id/lease_epoch` | 作业与租约关联；防止旧 epoch 证据混入新运行。 |
| `clock_source` | `node_monotonic`、`node_wall`、`linux_ntp` 等。 |
| `timebase_id` | 运行时间基准标识。 |
| `max_clock_drift_ms` | 声明时钟漂移上限；超限必须记录异常。 |
| `trust_level` | `claimed`、`signed`、`recomputed`、`reviewed`。 |

### 7.2 信任链

```text
Windows Node Agent 事实（claimed）
  → 节点回执 + 签名（signed，可选）
  → Linux 重算摘要与关联（recomputed）
  → Linux 独立复核（reviewed，verification record）
  → 五轴与 decision（Linux 写入）
```

**规则**：

- `claimed` 不得直接支撑 PASS；至少达到 `recomputed`。
- `signed` 只提升来源可信度，不替代内容重算。
- `reviewed` 必须由 Linux 侧复核记录证明；节点不能自证 `reviewed`。
- 旧 `lease_epoch`、旧 `revision_id`、旧 `run_id` 的证据不得被当前运行引用；引用即 `conflicted`。

---

## 8. 访问等级

| `access_level` | 可见范围 | 典型证据 |
|---|---|---|
| `summary` | 报告摘要与证据索引，不含原始内容、不含可还原敏感信息的路径。 | 报告投影、聚合指标。 |
| `task_member` | 任务授权成员；可看执行日志、manifest、回执、异常事件、人工记录。 | `execution_log`、`manifest`、`receipt`、`anomaly_event`、`human_note`。 |
| `evidence_reader` | 任务授权证据读取者；可看原始音频、设备日志、串口日志、截图、读取记录。 | `raw_audio`、`device_log`、`serial_log`、`screenshot`、`linux_log_read`。 |
| `system_internal` | 控制面内部；签名密钥、令牌、未脱敏诊断。 | 签名材料、密钥引用、内部 trace。 |

**规则**：

- 默认报告只输出 `summary`；原始材料不得因报告导出而绕过访问控制。
- 访问等级变更必须审计（操作者、时间、旧值、新值、原因）。
- 脱敏不改变证据摘要；脱敏版本是新的 `derived` 证据项，并引用原始项。
- `human_note` 不得包含凭据、令牌、完整转录或未脱敏个人信息。

---

## 9. 部分证据、上传与去重

### 9.1 证据项状态机

```text
declared → uploading → partial → complete → verified
     │          │          │         │
     │          │          │         └→ conflicted（摘要/大小/关联不一致）
     │          │          └→ unavailable（源丢失/节点离线且无副本）
     │          └→ quarantined（上传会话异常/安全阻断）
     └→ unavailable（声明后从未开始）
```

- `complete` 只表示字节数完整，不表示已核验；必须经 Linux 重算后才进入 `verified`。
- `verified` 是唯一可计入“必需证据已存在”的状态。
- `conflicted` 必须保留双方摘要、来源、发现时间和处置记录。

### 9.2 分片上传

| 字段 | 说明 |
|---|---|
| `upload_id` | 单次上传会话标识。 |
| `chunk_index` | 从 0 开始，连续。 |
| `offset/length` | 字节区间；不得重叠或越界。 |
| `chunk_digest` | 该片 SHA-256。 |
| `chunks_total/chunks_received` | 进度。 |
| `resume_offset` | 断点续传位置。 |

**幂等规则**：

- 同一 `evidence_id + chunk_index + chunk_digest` 重复提交 → 返回首次结果，不重复写入。
- 同一 `evidence_id + chunk_index` 但 `chunk_digest` 不同 → `conflicted`，不得覆盖。
- 上传顺序可以乱序，但完成前必须校验连续性与总长度。

### 9.3 部分上传

- 部分上传**不是失败**，是 `partial`；不得因此把运行标为 `invalid-evidence`。
- 部分上传使必需证据不满足“已核验存在”，因此 `evidence_status` 不得为 `COMPLETE`，`decision` 不得为 `PASS`。
- 运行保持开放，等待续传；超过任务级上传时限仍未完成，标记 `INCOMPLETE` 并进入 `BLOCKED/invalid-evidence`。超期阈值由 `docs/contracts/thresholds.md` 的 `evidence.completion_deadline_hours`（TH-E-08，默认 24h）定义；本契约只规定超期后的状态语义。
- 断线期间节点继续本地 spool；重连后先补传、去重、对账，不重跑。
- 部分上传不得被计入正式分母。

### 9.4 重复上传

| 情形 | 处理 |
|---|---|
| 同 `evidence_id` + 同摘要 + 同大小 | 幂等无操作；返回首次登记时间；不重复计数。 |
| 同 `evidence_id` + 不同摘要 | `conflicted`；保留旧项；新内容另立 `supersedes` 候选；不得自动替换。 |
| 不同 `evidence_id` + 同摘要 | 允许；blob 去重；逻辑角色分别计算；报告不得重复计数。 |
| 重试产生新 `attempt` | 新证据集；不得合并到首次 attempt；`FLAKY_SUSPECT` 单列。 |

### 9.5 与分母的关系

- 部分、重复、冲突证据都不改变“样本是否有效”的业务事实，但会阻止证据完整性。
- 分母只统计 `mode=formal`、`validity=VALID`、`evidence=COMPLETE` 的样本。
- 重复上传不得让同一样本被计数两次；以 `run_id + case_id + attempt` 为唯一键。

---

## 10. 按需读取（on-demand read）

### 10.1 允许的读取方式

Linux 只能通过 Node Agent 的白名单日志查询读取 Windows 本地日志：

- 只读，不允许任意 shell、PowerShell、SSH 或文件系统遍历。
- 查询必须限定：`node_id`、`device_identity`、白名单路径、字节区间或游标、最大长度、超时。
- 读取不得修改源文件；不得删除、截断、重命名源日志。
- 读取请求与结果必须记录为 `linux_log_read` 证据项。

### 10.2 读取记录结构

`linux_log_read` 至少包含：

| 字段 | 说明 |
|---|---|
| `query_id` | 查询标识。 |
| `node_id/device_identity` | 目标节点与设备。 |
| `source_path` | 白名单相对路径；不得是任意绝对路径。 |
| `range` | `offset/length` 或 `cursor/limit`。 |
| `started_at/finished_at` | 读取时间。 |
| `byte_count` | 实际读取字节数。 |
| `result_digest` | 读取结果的 SHA-256。 |
| `completeness` | `complete` / `partial` / `failed`。 |
| `error_code` | 失败原因（权限、路径、超时、节点离线等）。 |
| `purpose` | `required_verification` / `optional_diagnostic` / `anomaly_replay`。 |

上述字段落在 `evidence-item.log_read` 对象；当 `evidence_class=linux_log_read` 时该对象必填，且不得在非 `linux_log_read` 证据上携带该对象。

### 10.3 语义

- 按需读取可以满足**核验**：Linux 读取必需日志切片、记录摘要、完成关联后，可将该切片作为已验证证据。
- 按需读取**不是备份、不是归档、不是异机副本**。节点磁盘损坏、离线或日志被清理后，未读取部分不可恢复。
- 必需日志切片应持久化到 Linux 内容寻址存储；若任务级策略允许“仅摘要 + 源端保留”，必须在冻结包中显式声明，并在报告中标注残余风险。
- 完整 GB 级大日志可以留在 D:，只要必需切片可核验、locator 可解析、保留策略允许。
- 必需日志读取失败 → `evidence_status=UNVERIFIED` 或 `INCOMPLETE`，`decision=BLOCKED/invalid-evidence`，不得 PASS。
- 非必需诊断日志读取失败 → 记录 `optional_missing`，不阻塞 PASS。
- 远程可读不得被报告表述为“已备份”或“已归档”。

---

## 11. 保留与归档

### 11.1 保留规则

| 项目 | 规则 |
|---|---|
| 本地热存 | 原始音频、日志、证据默认热存 **30 天**（自 `received_at` 或 `captured_at` 起算，以任务级声明为准）。 |
| 到期处理 | 进入 `pending_archive`；**没有已验证归档路径前不得自动删除**。 |
| 归档验证 | 归档副本必须可读、摘要与原始一致、归档清单可解析；验证通过才可标记 `archived`。 |
| 删除 | 仅可在 `archived` 且保留策略允许、且经授权与审计后删除热副本。 |
| 未结案引用 | 仍被未结案运行、判定、报告或审计引用的证据不得删除。 |
| 访问审计 | 读取、导出、归档、删除、权限变更全部审计。 |

### 11.2 归档状态

| `archive_state` | 含义 | 对判定影响 | 对删除影响 |
|---|---|---|---|
| `not_required` | 该证据类不要求归档（如临时诊断）。 | 无 | 仍受保留策略约束。 |
| `hot_only` | 仅在热存，尚未安排归档。 | 无 | 不得删除。 |
| `pending` | 已排队等待归档。 | 无 | 不得删除。 |
| `archived` | 归档副本已验证。 | 无 | 可按策略删除热副本。 |
| `archive_unavailable` | 归档设施不可用或验证失败。 | 无 | **禁止删除**；升级告警。 |
| `deletion_blocked` | 有未结案引用或授权缺失。 | 无 | 禁止删除。 |

**关键边界**：归档不可用不会把已完成的判定改写为失败，也不会自动让证据变为不完整；它只阻止删除并要求保留热副本。判定一旦作出，不因后续归档状态变化而回溯改变。

---

## 12. 清理回执（cleanup receipt）

### 12.1 结构

```json
{
  "schema_version": "1.0",
  "receipt_type": "cleanup",
  "receipt_id": "55555555-5555-4555-8555-555555555555",
  "task_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "revision_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "run_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  "job_id": "15151515-1515-4515-8515-151515151515",
  "attempt": 1,
  "node_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
  "device_identity": {
    "device_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    "model": "example-model",
    "serial": "SN-0001",
    "firmware": "1.2.3",
    "endpoints": ["audio_out:speaker-1", "serial:COM3"]
  },
  "lease_id": "ffffffff-ffff-4fff-8fff-ffffffffffff",
  "lease_epoch": 7,
  "started_at": "2026-10-28T07:08:00Z",
  "finished_at": "2026-10-28T07:10:00Z",
  "cleanup_status": "completed",
  "local_stop_confirmed": true,
  "safe_cleanup_done": true,
  "steps": [
    {
      "step_id": "stop",
      "action": "stop_safe",
      "status": "completed",
      "started_at": "2026-10-28T07:08:00Z",
      "finished_at": "2026-10-28T07:08:20Z",
      "detail_code": "LOCAL_STOP_CONFIRMED",
      "evidence_ids": ["33333333-3333-4333-8333-333333333333"]
    },
    {
      "step_id": "release-endpoints",
      "action": "release_endpoints",
      "status": "completed",
      "started_at": "2026-10-28T07:08:20Z",
      "finished_at": "2026-10-28T07:09:30Z",
      "detail_code": "ENDPOINTS_RELEASED",
      "evidence_ids": []
    }
  ],
  "resources": {
    "processes_terminated": ["lstest-runner.exe"],
    "files_closed": true,
    "endpoints_released": ["audio_out:speaker-1", "serial:COM3"],
    "device_reset_performed": true,
    "device_state_after": "idle",
    "spool_flushed": true,
    "residual_warnings": []
  },
  "safety_stop": {
    "triggered": false,
    "reason_code": null,
    "source": null
  },
  "warnings": [],
  "facts_digest": "sha256:9999999999999999999999999999999999999999999999999999999999999999",
  "receipt_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "produced_at": "2026-10-28T07:10:00Z",
  "notes": null
}
```

### 12.1.1 与最小释放投影的映射

P0-04 领域契约和 P0-05 节点契约中的 `receipt.cleanup_receipt` 是**最小释放投影**，本回执是清理事实的权威结构。映射关系：

| 最小投影字段 | 来源 |
|---|---|
| `cleanup_receipt_id` | 本回执 `receipt_id`。 |
| `cleanup_status` | 本回执同名字段（同名词表映射，非推断）。 |
| `local_stop_confirmed` | 本回执同名字段（节点本地停止事实）。 |
| `safe_cleanup_done` | 本回执同名字段（资源释放/设备安全事实）。 |
| `occupancy_reconciled` | 控制面 `device-occupancy.reconciliation.result=passed`；**节点不能自证**。 |
| `completed_at` | 本回执 `finished_at`。 |
| `notes` | 本回执 `notes`（可为 `null`）。 |

**投影关系（R-02，2026-10-29）**：security 侧 `receipt.cleanup_receipt` 是 domain 最小投影的**超集**；domain 只承载上表最小字段并显式拒绝 `operational_detail`。本回执（`cleanup-receipt.schema.json`）是详细清理步骤/资源/状态的唯一权威位置。跨侧转换必须逐字段按本表进行；未知字段丢弃并审计，不得互相反序列化。

两者不一致时，以本回执 + 控制面占用对账为准；不得用节点侧投影覆盖权威回执，也不得用权威回执绕过控制面占用对账。

### 12.2 `cleanup_status` 语义

| 值 | 含义 | 能否确认释放 | 设备处置 |
|---|---|---|---|
| `completed` | 所有清理步骤完成，资源释放，设备处于安全状态。 | 可以（还需满足第 13.3 节其他前置）。 | 可进入释放确认。 |
| `completed_with_warnings` | 清理完成但有非阻断告警。 | 可以，但必须记录残余风险并经复核。 | 可释放；按告警决定是否隔离观察。 |
| `failed` | 清理步骤失败、资源未释放、设备状态未知或不安全。 | **不可以**。 | `quarantined`；人工恢复。 |
| `not_required` | 本次运行无设备动作（如纯静态检查）。 | 不适用。 | 无占用。 |
| `unknown` | 未收到回执、回执损坏、签名/摘要无法验证。 | **不可以**。 | 保持占用，等待补传/对账。 |

### 12.3 缺失回执的精确语义

**缺失 cleanup 回执**（未收到、`cleanup_status=unknown`、或摘要/签名校验失败）：

1. **设备释放无法确认** → 设备保持占用，状态为 `held_pending_cleanup`（节点离线时为 `offline_held`）。
2. **设备不得被重新分配**给其他任务，不得因心跳消失而视为空闲。
3. **不自动等于整个证据集不完整**。证据完整性仍按 `required_evidence` 独立计算；如果必需证据齐全且摘要/关联通过，`evidence_status` 可以为 `COMPLETE`。
4. **不自动阻塞 PASS**。若其他正式 PASS 前置条件全部满足，`decision` 仍可为 `PASS`；但该 PASS **不授权设备释放或复用**。
5. **必须持续尝试**：补传回执、白名单读取清理日志、节点重连对账、现场确认。
6. **报告中必须单列**：`release_state=held`、`cleanup_receipt=missing`，不得把 PASS 表述为“设备已清理”或“可再次使用”。

> 该语义替代架构旧不变量 I-21。I-21 中“运行结束应产出 cleanup_receipt”的要求仍然成立；但旧措辞把“缺失回执”与“证据不完整”绑定，该绑定不再成立。缺失回执只影响释放确认，不影响证据完整性的独立计算。

### 12.4 清理失败的语义

**`cleanup_status=failed`**：

1. 设备释放**拒绝**，状态 `quarantined`，人工恢复前不得再分配。
2. 不是 `invalid-evidence`：不得仅因清理失败把证据状态改为 `INCOMPLETE`。
3. 不是业务 `FAIL`：不得把清理失败改写为 `valid-failure` 或业务失败。
4. 触发**阻断性异常** `cleanup_failure`，默认使 `decision=NEEDS_REVIEW`，自动 PASS 暂缓；正式分母暂不计入，待复核处置。
5. 复核必须确认：清理失败是否影响证据落盘/摘要完整性、是否影响设备安全、是否需要重跑该运行。
6. 若复核确认证据完整、业务结果有效、失败仅为可控资源残留，可解除阻断并允许 PASS；必须记录复核人、理由和残余风险。
7. 若复核无法确认证据完整性 → `evidence_status=INCOMPLETE`，`decision=BLOCKED/invalid-evidence`。

### 12.5 回执与节点回执的区别

| 回执 | 证明 | 不证明 |
|---|---|---|
| `cleanup_receipt` | 停止、清理、资源释放、设备安全状态的事实。 | 业务 PASS；证据完整；最终判定。 |
| `node_receipt` | 节点执行了作业、产生了哪些事实与证据引用。 | 证据内容真实；Linux 已复核；设备已释放。 |
| `job receipt` | 作业接收/开始/结束的控制事实。 | 清理完成；判定成立。 |

`evidence-manifest.node_receipt.status` 是 security 线协议回执状态的只读投影，固定映射见 `security-node.md` §19.2：`accepted→received`、`started→started`、`completed→completed`、`failed→failed`、`stopped→aborted`、`blocked→aborted`、`infra_error→failed`、`cleanup_complete→completed`、`rejected→unknown`。原始线协议 `status` 必须保留在回执中；无法映射或未通过校验的值投影为 `unknown`，不得猜测为 `completed`。该投影不是领域 `Receipt.chain_status`，也不参与最终判定。

### 12.6 清理异常的阻断范围

| 异常码 | 阻塞释放确认 | 阻塞 PASS | 说明 |
|---|---|---|---|
| `cleanup_receipt_missing` | 是 | **否** | 释放未知；证据完整性独立计算；PASS 不授权释放。 |
| `cleanup_receipt_unverifiable` | 是 | **否** | 回执摘要/签名无法验证；按缺失处理。 |
| `cleanup_failed` | 是 | 默认是，复核后可解除 | 隔离设备；复核确认证据未受影响后可恢复 PASS 资格。 |
| `cleanup_completed_with_warnings` | 视告警内容 | 视告警内容 | 非阻断告警不阻塞；涉及证据落盘/设备安全的告警按阻断处理。 |

`evidence-manifest.anomalies.blocking_ids` 只应包含**阻塞 PASS**的异常；`cleanup_receipt_missing` 必须放入 `non_blocking_ids`（同时由 `device-occupancy.release.release_state=held` 表达释放阻塞），不得因为释放阻塞而把证据状态改为不完整。

---

## 13. 设备占用与释放

### 13.1 占用状态

| `state` | `occupancy_state`（P0-04 投影） | 含义 | 是否可再分配 |
|---|---|---|---|
| `free` | `IDLE` | 无租约、无残留占用、释放已确认。 | 是 |
| `reserved` | `OCCUPIED` | 已预留给某任务，尚未开始执行。 | 否 |
| `leased` | `OCCUPIED` | 租约已授予，尚未开始运行。 | 否 |
| `running` | `OCCUPIED` | 正在执行设备动作。 | 否 |
| `offline_held` | `OCCUPIED` | 通信离线，但设备仍被当前运行占用。 | **否**（心跳消失 ≠ 空闲） |
| `held_pending_cleanup` | `OCCUPIED` | 运行结束但缺回执/清理未确认。 | 否 |
| `held_pending_reconciliation` | `OCCUPIED` | 重连后等待补传、去重、运行位置与占用对账。 | 否 |
| `draining` | `RELEASING` | 不再接新单，等待当前工作收敛。 | 否 |
| `quarantined` | `OCCUPIED` | 清理失败、设备失控、连续失败等，人工恢复前隔离。 | 否 |
| `unknown` | `OCCUPIED` | 状态不可确认。 | 否（按占用处理） |

`occupancy_state` 是 P0-04 领域契约 `Lease`/`Device` 的三值投影，用于跨契约对齐；`state` 是本契约的细化状态，不得因为细化状态为 `free` 以外的任何值而把 `occupancy_state` 写成 `IDLE`。

**与线协议 `lease.state` 的关系（C-03，2026-10-29）**：上表是**证据侧细化状态**，不是线协议 `lease.state`。线协议 6 值到领域 `Lease.state`/`occupancy_state` 的固定映射在 `security-node.md` §19.2 与 `domain.md` §11.2；`expired` 永远不映射为 `free`/`IDLE`。本表与那两张表不得出现第二套取值。

**四值历史词（C-05，2026-10-29）**：`docs/v2`/`openspec` 曾使用 `OCCUPIED / RELEASING / RELEASED / QUARANTINED` 四值。本契约只承认三值 `occupancy_state`；`RELEASED` 与 `QUARANTINED` 是历史/展示词，其投影规则见 `domain.md` §11.3（`RELEASED` 需三项前置条件全真才 → `IDLE`；`QUARANTINED` → `OCCUPIED`）。SR-14 在 v1.1-candidate 中仍为开放，回写属后续同步批次。

### 13.2 通信状态与占用状态分离

`communication_state` 独立记录：

| 值 | 含义 |
|---|---|
| `online` | 心跳正常。 |
| `degraded` | 心跳延迟/丢包，但仍可通信。 |
| `offline` | 心跳丢失或连接断开。 |
| `unknown` | 无法判断。 |

**规则**：

- `communication_state=offline` **不得**推导出 `state=free`。
- 已启动的冻结压测在离线期间继续执行；设备保持 `offline_held`，不重派、不回收、不重跑。
- 重连后先处理待 STOP，再补传、去重、对账；对账完成前保持 `held_pending_reconciliation`。
- 租约过期只是通信/租约事实，不等于设备空闲；必须先对账。

### 13.3 释放前置条件（与判定无关）

设备释放确认必须同时满足：

| ID | 前置条件 | 证据/记录 |
|---|---|---|
| R-01 | 本地停止已确认，或运行正常完成且无残留设备动作。 | `cleanup_receipt.steps`、`execution_log` |
| R-02 | `cleanup_receipt` 存在且摘要/签名可验证，`cleanup_status ∈ {completed, completed_with_warnings, not_required}`。 | `receipt`、`device-occupancy.release` |
| R-03 | 占用对账完成：运行位置确认、待处理 STOP 已清空、无其他租约、证据积压已登记。 | `device-occupancy.reconciliation` |
| R-04 | 设备处于安全状态：进程终止、端点释放、设备复位/空闲。 | `cleanup_receipt.resources` |
| R-05 | 节点可达或现场确认设备可再分配；离线时不得确认释放。 | `communication_state`、人工记录 |

**释放不要求**：

- 不要求全部 GB 级日志已上传；
- 不要求证据完整性达到 `COMPLETE`；
- 不要求归档完成；
- 不要求最终判定已作出。

**释放确认**写入 `device-occupancy.release`，不写入 `verdict`。

与 P0-04 `release_preconditions` 的映射：`local_stop_confirmed` ← R-01；`safe_cleanup_done` ← R-02 ∧ R-04；`occupancy_reconciled` ← R-03；R-05 是额外的节点可达性/现场确认，不进入三布尔投影，但在确认释放时仍必须满足。

### 13.4 释放不等于通过

- `release_state=released` 只表示设备可再分配。
- 释放不能反推 `evidence_status=COMPLETE`，也不能反推 `decision=PASS`。
- 未释放不能反推 `decision!=PASS`；缺回执场景下 PASS 与 `held_pending_cleanup` 可以并存。
- 报告必须同时展示 `decision` 与 `release_state`，不得合并为单一“通过/完成”。

### 13.5 对账

对账至少包含：

1. 运行位置：已执行 case、最后成功动作、待处理 STOP。
2. 设备占用：当前租约、epoch、是否有其他任务持有。
3. 证据：本地 spool、已上传分片、缺失分片、摘要冲突。
4. 序列：事件序号、重复事件、旧 epoch 事件。
5. 结论：可释放 / 继续占用 / 隔离。

对账结果写入 `device-occupancy.reconciliation`，并作为释放前置 R-03 的依据。

---

## 14. 五轴判定

### 14.1 五个轴与允许值

| 轴 | 允许值 | 写入方 |
|---|---|---|
| `execution_status` | `NOT_STARTED` / `RUNNING` / `COMPLETED` / `ABORTED` / `SKIPPED` | Linux（基于节点事实） |
| `validity_status` | `VALID` / `INVALID` / `BLOCKED` / `UNKNOWN` | Linux |
| `business_verdict` | `PASS` / `FAIL` / `EXPECTED` / `WARN` / `NEEDS_REVIEW` / `NOT_EVALUATED` | Linux |
| `evidence_status` | `COMPLETE` / `INCOMPLETE` / `CONFLICTED` / `UNVERIFIED` | Linux |
| `verification_status` | `PASS` / `FAIL` / `NOT_RUN` | Linux 独立复核 |

**规则**：

- 五轴是平台结果模型；兼容 lstest 结果合同，但最终判定权在 Linux。
- `business_verdict` 不是最终结论；它只是业务轴。
- `verification_status` 不是业务轴；它只表示独立复核结果。
- 任一轴不得由节点直接写入最终值；节点只能提供事实输入。
- 展示层可以用 `UNKNOWN` 作为“尚未读取”的占位，但 `verdict.axes.evidence_status` 不得写入 `UNKNOWN`；未核验应写 `UNVERIFIED`，缺失应写 `INCOMPLETE`，冲突应写 `CONFLICTED`。

### 14.2 最终判定派生顺序

`decision` 由以下顺序派生（先命中先返回）：

```text
1. mode != formal
   → decision = NOT_APPLICABLE, formal_pass = false, formal 分母 = 0
2. 批准/冻结边界缺失、批准快照或边界摘要不匹配、租约/epoch 不符
   → decision = BLOCKED, failure_class = blocked
3. execution_status = NOT_STARTED
   → decision = NOT_EVALUATED, failure_class = none
4. 触发安全停止/人工停止
   → decision = STOPPED, failure_class = stopped
5. 节点/传输/存储基础设施故障
   → decision = BLOCKED, failure_class = infra-error
6. validity_status = INVALID
   → decision = INVALID, failure_class = invalid-input
7. validity_status = BLOCKED
   → decision = BLOCKED, failure_class = invalid-environment（或 blocked）
8. evidence_status != COMPLETE，或必需证据摘要/关联失败
   → decision = BLOCKED, failure_class = invalid-evidence
9. verification_status != PASS
   → decision = NEEDS_REVIEW, failure_class = needs-review
10. 存在未处置的阻断性异常
   → decision = NEEDS_REVIEW, failure_class = needs-review
11. business_verdict = PASS 且全部 PASS 前置条件成立
   → decision = PASS, formal_pass = true
12. business_verdict = FAIL 且 validity=VALID 且 evidence=COMPLETE
   → decision = FAIL, failure_class = valid-failure
13. 其他
   → decision = NEEDS_REVIEW, failure_class = needs-review
```

**禁止**：把 `device_release`、`archive_state`、节点自报 `PASS` 作为上述派生输入。

### 14.3 正式 PASS 前置条件

`decision=PASS` 必须同时满足以下全部条件（对应 `verdict.pass_preconditions`）：

| 条件 | 字段 | 要求 |
|---|---|---|
| 批准有效 | `approval_valid` | 批准记录存在、范围摘要与冻结边界一致、批准时间有效。 |
| 边界冻结 | `boundary_frozen` | `revision_id` 已冻结、`bundle_digest` 与批准快照一致。 |
| 正式模式 | `mode_formal` | `mode=formal`。 |
| 执行完成 | `execution_completed` | `execution_status=COMPLETED`。 |
| 样本有效 | `sample_valid` | `validity_status=VALID`。 |
| 业务通过 | `business_pass` | `business_verdict=PASS`。 |
| 必需证据完整 | `required_evidence_complete` | 所有必需证据 `verified`，无缺失。 |
| 摘要通过 | `digest_verified` | 所有必需证据摘要重算一致。 |
| Linux 复核通过 | `linux_review_pass` | `verification_status=PASS`，复核记录独立。 |
| 无阻断异常 | `no_blocking_anomaly` | 无未处置阻断异常。 |
| 分母有效 | `denominator_eligible` | 样本属于正式有效分母。 |

**设备释放不是 PASS 前置条件**；`cleanup_receipt` 缺失也不是 PASS 前置条件（但清理失败默认触发阻断复核，见 12.4）。

**正式 PASS 示例**（仅示意结构；`cleanup_receipt` 是信息性字段，不参与 PASS 派生）：

```json
{
  "schema_version": "1.0",
  "verdict_id": "99999999-9999-4999-8999-999999999999",
  "task_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "revision_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "run_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  "mode": "formal",
  "acceptance_level": "L4",
  "test_level": "T6",
  "axes": {
    "execution_status": "COMPLETED",
    "validity_status": "VALID",
    "business_verdict": "PASS",
    "evidence_status": "COMPLETE",
    "verification_status": "PASS"
  },
  "decision": "PASS",
  "mode_outcome": "PASS",
  "failure_class": "none",
  "formal_pass": true,
  "denominator": {
    "eligible": true,
    "formal_denominator": true,
    "exclusion_reason": null
  },
  "pass_preconditions": {
    "approval_valid": true,
    "boundary_frozen": true,
    "mode_formal": true,
    "execution_completed": true,
    "sample_valid": true,
    "business_pass": true,
    "required_evidence_complete": true,
    "digest_verified": true,
    "linux_review_pass": true,
    "no_blocking_anomaly": true,
    "denominator_eligible": true
  },
  "reasons": [
    {
      "code": "FORMAL_PASS",
      "message": "required evidence verified and Linux independent review passed"
    }
  ],
  "evidence_manifest": {
    "manifest_id": "44444444-4444-4444-8444-444444444444",
    "manifest_digest": "sha256:8888888888888888888888888888888888888888888888888888888888888888"
  },
  "verification": {
    "verification_id": "66666666-6666-4666-8666-666666666666",
    "verification_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "result": "PASS"
  },
  "cleanup_receipt": {
    "receipt_id": "55555555-5555-4555-8555-555555555555",
    "receipt_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "cleanup_status": "completed"
  },
  "decided_by": {
    "kind": "linux_verdict_service",
    "identity": "verdict-service",
    "role": "platform_verdict_writer"
  },
  "decided_at": "2026-10-28T07:11:30Z",
  "created_at": "2026-10-28T07:11:30Z"
}
```

### 14.4 节点自报 PASS 的处理

- 节点回执可以包含 `node_reported_status`，但必须标记 `used_for_decision=false`。
- Linux 判定服务**不得**读取 `node_reported_status.business_verdict`、`node_reported_status.execution_status` 或任何节点自报 `PASS` 字段作为判定输入。
- 节点自报 PASS 与 Linux 复核不一致时，以 Linux 重算结果为准，并记录 `conflict` 审计事件。
- 报告中可以展示“节点自报”，但必须同时标注“非平台判定依据”。

### 14.5 分母规则

| 样本类型 | 是否进入正式分母 |
|---|---|
| `mode=formal` + `validity=VALID` + 必需证据 `COMPLETE` + Linux 复核已运行 | 是 |
| `mode=smoke` | 否 |
| `mode=static` | 否 |
| `validity=INVALID`（invalid-input） | 否 |
| `validity=BLOCKED`（invalid-environment/blocked） | 否 |
| `evidence_status ∈ {INCOMPLETE, CONFLICTED, UNVERIFIED}` | 否 |
| `decision=STOPPED` | 否 |
| `failure_class=infra-error` | 否 |
| `decision=NEEDS_REVIEW` | 暂不计入，待复核 |
| 重试通过 | 首次失败样本按原分类；重试样本单列 `FLAKY_SUSPECT`，不覆盖首次结果 |
| `valid-failure`（VALID + FAIL + COMPLETE） | 是 |

报告必须固定声明：`formal_denominator = 有效正式样本`；`INVALID_*`、`BLOCKED`、`STOPPED`、`INFRA_ERROR`、烟测不计入。

### 14.6 逐用例与运行级

- `case_results` 逐用例记录五轴与 `failure_class`；运行级 `axes` 是聚合结果，不得掩盖逐用例差异。
- 一个运行中只要存在必需证据缺失的 case，该 case 不得 PASS；运行级 `decision` 不得为 PASS，除非缺失 case 被明确排除出本次正式判定范围并重新冻结。
- 跨设备结果不得合并；设备等价条件未批准时，按设备分别计算分母与判定。

---

## 15. 失败分类

### 15.1 分类定义

| `failure_class` | 含义 | 典型触发 | `decision` | `validity_status` | `business_verdict` | `evidence_status` | 正式分母 |
|---|---|---|---|---|---|---|---|
| `none` | 无失败或尚未评估 | 正常通过；未开始 | `PASS`/`NOT_EVALUATED` | 按实际 | 按实际 | 按实际 | 视情况 |
| `invalid-input` | 输入/用例前提不满足 | 语料缺失、参数越界、用例前置条件不成立 | `INVALID` | `INVALID` | `NOT_EVALUATED` | `COMPLETE`/`INCOMPLETE` | 否 |
| `invalid-environment` | 环境/会话/端点不满足 | 无交互会话、端点缺失、音频设备不可用 | `BLOCKED` | `BLOCKED` | `NOT_EVALUATED` | 视情况 | 否 |
| `invalid-evidence` | 证据链失败 | 必需证据缺失、摘要不符、来源/关联冲突、必需日志不可读 | `BLOCKED` | `VALID`/`UNKNOWN` | `NOT_EVALUATED` | `INCOMPLETE`/`CONFLICTED`/`UNVERIFIED` | 否 |
| `blocked` | 前置条件/资源/授权阻塞 | 缺批准、租约冲突、待处理 STOP、边界不匹配 | `BLOCKED` | `BLOCKED`/`UNKNOWN` | `NOT_EVALUATED` | 视情况 | 否 |
| `stopped` | 安全停止/人工停止 | 设备危险、人工停止、安全边界暂停 | `STOPPED` | `UNKNOWN`/`BLOCKED` | `NOT_EVALUATED` | 视情况 | 否 |
| `infra-error` | 基础设施故障 | 节点崩溃、传输中断、存储耗尽 | `BLOCKED` | `BLOCKED`/`UNKNOWN` | `NOT_EVALUATED` | 视情况 | 否 |
| `valid-failure` | 有效输入但业务未达预期 | 识别错误、响应错误、指标未达标 | `FAIL` | `VALID` | `FAIL` | `COMPLETE` | 是 |
| `unsupported` | 超出 V0.0.1 范围 | 断电、刷写、未登记任务类别 | `NOT_APPLICABLE` | `UNKNOWN` | `NOT_EVALUATED` | 视情况 | 否 |
| `needs-review` | 无法自动定论 | 复核未完成、异常冲突、清理失败待复核 | `NEEDS_REVIEW` | `UNKNOWN`/`VALID` | `NEEDS_REVIEW` | 视情况 | 待复核 |

**与 domain 权威词表的双向映射（C-02，2026-10-29 裁决）**

权威词表是 domain 的 8 个大写值（`domain.md` §9.4）；本表小写值是判定产物的序列化投影，不是第二套分类学。

| domain `failure_classification` | 证据 `failure_class` | 是否进入正式分母 |
|---|---|---|
| `INVALID_INPUT` | `invalid-input` | 否 |
| `INVALID_ENVIRONMENT` | `invalid-environment` | 否 |
| `INVALID_EVIDENCE` | `invalid-evidence` | 否 |
| `VALID_FAILURE` | `valid-failure` | **是** |
| `BLOCKED` | `blocked` | 否 |
| `STOPPED` | `stopped` | 否 |
| `UNSUPPORTED` | `unsupported` | 否 |
| `INFRA_ERROR` | `infra-error` | 否 |
| （省略字段） | `none` | 视情况 |
| （无对应枚举值） | `needs-review` | 待复核，不计入 |

规则：

1. `none` 用“省略 `failure_classification`”表达，不新增 domain `NONE` 值；`evidence-manifest` 中的 `null` 与省略、`none` 三者等价（E-02）。
2. `needs-review` 用 `business_verdict=NEEDS_REVIEW` + `verification_status!=PASS` 表达，不塞进 domain `failure_classification`。
3. 双向转换共享同一张机器可读映射表；表外值一律 fail-closed 为 `NEEDS_REVIEW`，不得猜测为 `valid-failure` 或 `none`。
4. 只有 `valid-failure` ↔ `VALID_FAILURE` 计入正式分母；其余值不计入。
5. 报告/UI 不得直接透传原始词串，必须先归一为展示词汇；`none`/`needs-review` 不得显示为失败类计数。

### 15.2 区分规则

- **`invalid-evidence` ≠ `BLOCKED`**：前者是证据链缺陷（执行可能已完成）；后者是前置条件/资源/授权阻塞（可能尚未执行）。两者都 fail closed，但修复路径不同。
- **`invalid-evidence` ≠ `valid-failure`**：证据不完整不得改写为业务 FAIL；业务 FAIL 必须建立在 `VALID + COMPLETE` 之上。
- **`stopped` ≠ `FAIL`**：安全停止不是业务失败，不计入正式分母。
- **`infra-error` ≠ `invalid-environment`**：前者是平台基础设施故障，后者是设备/会话/端点环境不满足。
- **`needs-review` 不是 PASS 的同义词**：在复核完成前，不得进入正式分母，不得对外表述为通过。
- **`unsupported` 不得被计入任何 PASS/FAIL 分母**。

---

## 16. Linux 独立复核

### 16.1 复核定义

Linux 独立复核是正式 PASS 的必要条件。复核必须在 Linux 控制面执行，且：

- 不采信 Windows 节点自报的 `business_verdict`、`PASS` 或 `verification_status`；
- 不采信未经重算的节点摘要；
- 使用冻结的 oracle/规则版本、冻结的必需证据规则、冻结的样本规则；
- 产出可审计的 `verification-record`。

### 16.2 复核步骤

| 步骤 | 检查 | 失败处理 |
|---|---|---|
| V-01 | schema 校验（manifest、receipt、evidence item、verdict 候选） | `FAIL`，不得 PASS |
| V-02 | 重算 `manifest_digest` 与所有必需证据 `content_digest` | `FAIL/invalid-evidence` |
| V-03 | 校验 `size_bytes`、分片连续性、无重叠 | `FAIL/invalid-evidence` |
| V-04 | 校验 `task/revision/run/node/device/lease/epoch/bundle/approval` 关联 | `FAIL/invalid-evidence` 或 `BLOCKED` |
| V-05 | 校验必需证据集完整性与角色 | `FAIL/invalid-evidence` |
| V-06 | 重建分母：排除烟测、无效、阻塞、停止、基础设施故障 | `FAIL`，分母不可信 |
| V-07 | 复评 oracle：使用冻结规则与版本，不读取节点结论 | `FAIL` 或 `NEEDS_REVIEW` |
| V-08 | 异常处置：阻断异常是否已解释/关闭 | `FAIL` 或 `NEEDS_REVIEW` |
| V-09 | 清理/占用交叉核对（信息性，不改变判定） | 记录差异；必要时 `NEEDS_REVIEW` |
| V-10 | 访问/脱敏检查 | `FAIL`（越权/泄露） |
| V-11 | 生成复核记录并计算 `verification_digest` | — |

### 16.3 独立性要求

`verification-record.independence` 必须声明：

| 字段 | 要求 |
|---|---|
| `linux_side` | `true`。 |
| `separate_from_node` | `true`。 |
| `node_reported_status_used` | `false`。 |
| `verifier_not_submitter` | 可选；V0.0.1 允许提交者自批，不强制与提交者不同。 |
| `method` | 说明复核方式（自动复核服务、人工复核、两者结合）。 |

**规则**：

- 正式 PASS 至少需要一条 `linux_verifier_service` 的 `result=PASS` 记录。
- 若复核使用 `WAIVED`、覆盖异常、或人工改判，必须有人工复核者签署，并记录理由、范围、残余风险。
- 复核记录不得由 Windows 节点生成或修改。
- 复核记录本身不可变；更正另立新记录并 `supersedes`。

### 16.4 复核与审批的区别

| 项目 | 审批 | 复核 |
|---|---|---|
| 时点 | 执行前 | 执行后 |
| 对象 | 冻结边界、范围、预算、设备动作 | 证据、分母、oracle、异常、结论 |
| 是否可自批 | V0.0.1 允许提交者自批 | 不要求与提交者不同；但必须 Linux 侧独立于节点 |
| 产物 | `Approval` | `verification-record` |
| 对 PASS 的作用 | 前置条件 | 必要条件 |

---

## 17. 决策表（10 个场景）

> 表中“判定”指正式模式下的 `verdict.decision`；“释放”指 `device-occupancy.release.release_state`；“分母”指是否进入 `formal_denominator`。

| # | 场景 | `evidence_status` | 设备释放 | 最终判定 | 正式分母 | 必做动作 |
|---|---|---|---|---|---|---|
| 1 | **必需证据缺失** | `INCOMPLETE` | 独立判断：若释放证据齐全，可释放；否则保持占用 | `BLOCKED` / `invalid-evidence` | 否 | 保持运行未结案；要求补传/重取；不得 PASS；不得用其他运行证据替代。 |
| 2 | **可选诊断日志缺失** | `COMPLETE`（记录 `optional_missing`） | 不受影响 | 可为 `PASS`（其他前置满足） | 是（若其余有效） | 记录缺失原因；报告中标注诊断信息不完整；不阻塞。 |
| 3 | **摘要不匹配（必需证据或回执）** | 必需证据 → `CONFLICTED`；仅回执 → 不变 | 回执摘要不匹配 → 拒绝；仅证据摘要不匹配 → 独立判断 | 必需证据 → `BLOCKED` / `invalid-evidence`；仅回执 → 不变 | 必需证据 → 否；仅回执 → 不变 | 隔离冲突证据；保留双方摘要；从不可变源重取；禁止覆盖；必要时人工复核。 |
| 4 | **部分上传** | `INCOMPLETE` | 可释放（若释放证据齐全且本地保留已登记） | `BLOCKED` / `invalid-evidence`（待续传） | 否 | 断点续传；幂等去重；未完成前不判定；超时后标记 `INCOMPLETE`。 |
| 5 | **重复上传** | 不变（同摘要幂等） | 不受影响 | 不变 | 不变 | 按 `evidence_id + chunk_index + chunk_digest` 幂等；不得重复计数；同 ID 不同摘要转冲突。 |
| 6 | **清理回执缺失** | 不变（可为 `COMPLETE`） | **`held`（无法确认）**；设备保持占用 | 可为 `PASS`（其他前置满足） | 是（若其余有效） | 保持占用；补传回执/白名单读取清理日志/重连对账；报告中单列 `release=held`；不得表述为“已清理”。 |
| 7 | **清理失败** | 不变（除非清理失败导致证据未落盘） | **`quarantined`（拒绝释放）** | `NEEDS_REVIEW`（自动 PASS 暂缓） | 暂不计入，待复核 | 隔离设备；人工恢复；复核是否影响证据完整性/设备安全；记录理由与残余风险。 |
| 8 | **设备已释放** | 不变 | `released` | 不变 | 不变 | 记录释放确认、回执、对账；释放不推导 PASS，也不推导证据完整。 |
| 9 | **归档不可用** | 不变 | 不受影响 | 不变 | 不变 | 保留热副本；禁止删除；标记 `archive_unavailable`；升级告警；不得把远程读取当归档。 |
| 10 | **按需读取失败** | 必需日志 → `UNVERIFIED`/`INCOMPLETE`；可选日志 → 不变 | 不受影响 | 必需 → `BLOCKED` / `invalid-evidence`；可选 → 不阻塞 | 必需 → 否；可选 → 不变 | 重试白名单读取；检查路径/权限/节点状态；必需日志不可读时不得 PASS；记录失败原因。 |

**表读法**：

- 第 6 行与第 7 行是关键区分：**缺回执 = 释放未知，不自动证据不完整；清理失败 = 已知安全异常，隔离并复核**。
- 第 1、3、4、10 行都可能导致 `invalid-evidence`，但修复路径不同：补传、重取、去重、重读。
- 第 8、9 行说明释放与归档都不是判定输入。

---

## 18. 决策记录（decisions taken）

| ID | 决策 | 理由 | 被拒绝的替代方案 |
|---|---|---|---|
| D-EV-01 | 证据完整性、设备释放、最终判定三平面分离。 | 已批准规则明确要求释放可先于证据完整/归档；合并会导致“已释放=已通过”或“证据未传完=设备不能放”的错误。 | 单一 `status` 枚举；以释放状态驱动判定。 |
| D-EV-02 | cleanup receipt 默认是释放证据，不是判定必需证据；缺回执不自动使证据不完整。 | 所有者明确“缺回执阻塞释放确认，不自动阻塞整个证据链”；只有必需证据缺失/摘要失败阻塞 PASS。 | 沿用 I-21“缺回执=证据不完整”；把回执加入所有层级的必需证据集。 |
| D-EV-03 | 烟测永不进入正式分母；烟测 `decision=NOT_APPLICABLE`。 | 需求基线与 B-3 明确烟测独立运行、独立证据；`PASS` 一词若用于烟测会被误读为正式通过。 | 允许烟测 `decision=PASS`，仅在报告中标注。 |
| D-EV-04 | SHA-256 + RFC 8785 JCS + 域分隔；原始字节不规范化。 | 可跨语言复算；域分隔防止跨类型摘要混淆；文本日志保持字节级可追溯。 | 自定义 JSON 序列化；对文本做换行归一化。 |
| D-EV-05 | 稳定 `evidence_id` + `content_digest`；locator 可变。 | 复读、补传、归档只改变位置，不改变证据身份；便于审计引用。 | 以 locator 作为身份；以摘要作为唯一 ID（部分上传阶段无完整摘要）。 |
| D-EV-06 | 部分上传是 `partial`，不是失败。 | 断线续跑是已批准能力；把部分上传当失败会误判为 `invalid-evidence`。 | 任何未完成上传立即判失败。 |
| D-EV-07 | 重复上传幂等；同 ID 不同摘要 = 冲突。 | 防止重传导致重复计数；防止静默覆盖。 | 后到覆盖先到；按内容去重但丢失逻辑身份。 |
| D-EV-08 | 按需读取是核验路径，不是备份/归档。 | 已批准规则明确“远程可读不等于备份”；避免节点丢失后误以为有副本。 | 把 D: 远程可读视为归档；释放后不再保留必需切片。 |
| D-EV-09 | 归档不可用不回溯改变判定，只阻止删除。 | 判定应基于执行时证据；归档是保留问题，不是判定问题。 | 归档失败即撤销 PASS。 |
| D-EV-10 | 清理失败 → 隔离 + `NEEDS_REVIEW`，不是 `invalid-evidence`、不是业务 FAIL。 | 清理失败是安全/运维异常，不直接证明测量无效；但可能影响证据落盘，故需复核。 | 清理失败即判 `INVALID_EVIDENCE`；清理失败即判业务 FAIL。 |
| D-EV-11 | 五轴 + 派生 `decision`；节点自报只作事实。 | 与 lstest 五轴兼容；Linux 独占判定权；防止节点自报 PASS 成为最终结论。 | 单一 verdict 枚举；直接采用节点 PASS。 |
| D-EV-12 | 失败分类显式区分 `invalid-input`、`invalid-environment`、`invalid-evidence`、`blocked`、`stopped`、`infra-error`、`valid-failure`、`unsupported`、`needs-review`。 | 需求基线验收项 4 要求区分 invalid-input、invalid-evidence、阻塞与 valid-failure；不同分类的修复与分母规则不同。 | 把所有非 PASS 归为 `FAIL`；把证据问题归为业务失败。 |
| D-EV-13 | 释放前置条件独立于判定；释放确认写入 occupancy，不写入 verdict。 | 防止“释放=通过”；允许 PASS 与 held 并存（缺回执场景）。 | 释放作为 PASS 前置；PASS 作为释放前置。 |
| D-EV-14 | 原始材料热存 30 天；无已验证归档路径不删除。 | 已批准保留边界；防止证据丢失。 | 30 天后自动删除；以远程读取代替归档。 |
| D-EV-15 | L0–L2 不得替代 L3–L5；T5 不得替代 T6。 | 施工验收与测试策略的层级隔离要求；防止用文档/模拟证据声称真机/正式验收。 | 用静态检查+模拟链路直接宣称正式通过。 |
| D-EV-16 | 必需日志“切片”而非完整 GB 大日志作为判定证据；必需切片持久化到 Linux，完整日志可留 D:。 | 兼顾可核验性与“释放不必等 GB 日志上传”；避免把存储容量问题变成判定阻塞。 | 要求完整 GB 日志全部上传后才能判定；只保留 D: 远程可读而不持久化必需切片。 |

---

## 19. 与现有文档的差异及待同步项

| 文档 | 现有表述 | 本契约处理 | 后续动作 |
|---|---|---|---|
| 架构 v2 第 5.2 节 I-21 | 旧表述把“缺失回执”与“证据不完整”绑定。 | **不采用该绑定**；保留“应产出回执”，但缺失只阻塞释放确认。 | 文档同步时改写 I-21，拆为“回执应产出”“缺回执阻塞释放确认”“缺回执不自动使证据不完整”三条。 |
| 架构 v2 第 7 节租约规则 | “失联 → lease_expired → INFRA_ERROR → 先对账再重派”。 | 补充：失联期间已启动压测继续；设备 `offline_held`，心跳消失不等于空闲。 | 与 B-3/离线续跑规则同步。 |
| 模块设计 M-05 | “释放需 cleanup 回执”。 | 细化为第 13.3 节 R-01..R-05；回执是必要非充分条件。 | 同步释放前置条件。 |
| 施工验收第 2.1 节 | “释放与判定分离”。 | 本契约给出字段级落地。 | 无冲突；作为引用。 |
| 测试策略第 3.3/3.4 节 | “缺 cleanup 回执不得确认释放；不据此判定证据不完整”。 | 与本契约一致。 | 无冲突。 |
| 报告模板 | 尚未冻结。 | 本契约定义 `report-evidence-index` schema。 | 报告契约评审时引用。 |

**与同目录并行契约的对齐点**：

| 契约 | 对齐内容 |
|---|---|
| P0-04 `domain.md` / `schemas/domain/receipt.schema.json` | `evidence_id`、`manifest_id`、`cleanup_receipt_id` 使用 UUID；`cleanup_receipt` 最小投影字段映射见 12.1.1；`release_preconditions` 映射见 13.3；`occupancy_state` 三值投影见 13.1。 |
| P0-05 `security-node.md` / `schemas/security/receipt.schema.json` | `receipt.cleanup_receipt` 是设备释放前置条件的最小投影；清理步骤/资源/状态的权威定义是本契约的 `cleanup-receipt.schema.json`；节点 `outcome` 只作观察事实，不写最终判定。 |
| P0-07 `ui-report-knowledge-audit.md` | 报告默认 `summary_and_index`；`evidence_status=UNKNOWN` 仅作展示占位，不写入判定轴；`report-evidence-index.schema.json` 提供报告投影结构。 |
| P0-08 `thresholds.md` | 证据上传超期引用 `evidence.completion_deadline_hours`（TH-E-08）；时钟偏差引用 TH-C-01/02；本契约不重复硬编码数值。 |

---

## 20. 开放问题

| ID | 问题 | 影响 | 建议归属 |
|---|---|---|---|
| Q-EV-01 | 每个任务/profile 的“必需证据切片”粒度（哪些音频段、哪些日志区间、哪些 case 必配哪些证据）尚未冻结。 | 必需集无法全局固定，只能由冻结包声明。 | 任务级 `evidence_requirements`；A-1 契约冻结。 |
| Q-EV-02 | cleanup receipt / node receipt 是否强制签名、签名算法与证书链。 | 影响 `verified` 判定与防伪。 | P0-05 节点身份契约。 |
| Q-EV-03 | 归档设施最终路径、验证方式、删除审批流。 | 影响 `archived` 判定与 30 天到期处置。 | P0-10 / B-6 备份契约。 |
| Q-EV-04 | 时钟漂移容忍值与超限处置。 | 影响事件排序与证据时间可信度。 | P0-08；`thresholds.md` TH-C-01/02 候选为 120s/300s，待本契约评审确认采用。 |
| Q-EV-05 | 正式 PASS 是否强制人工复核签署（当前仅要求在 waiver/改判时签署）。 | 影响复核资源与责任边界。 | 所有者/验收评审。 |
| Q-EV-06 | 访问等级与 RBAC 角色的映射（`task_member`/`evidence_reader` 对应哪些角色）。 | 影响报告与原始材料访问。 | P0-07 权限契约。 |
| Q-EV-07 | 必需日志“仅摘要 + 源端保留”的允许条件与残余风险表述。 | 影响节点丢失后的可复核性。 | 任务级策略 + 报告模板。 |
| Q-EV-08 | `NEEDS_REVIEW` 的超时与升级规则。 | 影响运行结案与分母统计。 | P0-08。 |

---

## 21. 机器可读 Schema 索引

| Schema | 用途 |
|---|---|
| [`evidence-item.schema.json`](schemas/evidence/evidence-item.schema.json) | 单个证据项：分类、角色、状态、摘要、来源、上传、locator、保留、访问。 |
| [`evidence-manifest.schema.json`](schemas/evidence/evidence-manifest.schema.json) | 运行级证据清单：case、必需集、完整性、分母、异常、回执引用、复核引用。 |
| [`cleanup-receipt.schema.json`](schemas/evidence/cleanup-receipt.schema.json) | 清理回执：状态、步骤、资源、安全停止、事实摘要。 |
| [`device-occupancy.schema.json`](schemas/evidence/device-occupancy.schema.json) | 设备占用：占用状态、通信状态、租约、释放确认、对账、隔离。 |
| [`verdict.schema.json`](schemas/evidence/verdict.schema.json) | 五轴判定：轴值、派生决定、失败分类、PASS 前置条件、分母。 |
| [`verification-record.schema.json`](schemas/evidence/verification-record.schema.json) | Linux 独立复核：独立性声明、检查项、重算结果、结论。 |
| [`report-evidence-index.schema.json`](schemas/evidence/report-evidence-index.schema.json) | 报告投影：分母声明、运行/证据/释放索引、访问边界。 |

所有 schema 使用 JSON Schema Draft 2020-12，`additionalProperties=false`，并通过相对 `$ref` 互相引用。解析校验命令见下：

```bash
for f in docs/contracts/schemas/evidence/*.schema.json; do
  python3 -m json.tool "$f" >/dev/null || exit 1
done
```

---

## 22. 冻结候选声明

- 本文件是 `frozen-candidate v1.1`，用于契约评审，不是最终冻结版本；**未生产冻结，Phase 0 未关闭**。
- 本文件不宣称所有者已批准；批准须单独记录。
- 本文件不包含实现代码、测试代码、部署配置或真实运行证据。
- 本文件不修改 `.omo/plans/`、`.omo/boulder.json` 或仓库根 `plan.md`。
- 评审通过后，冻结版本应记录内容哈希、评审人、评审时间与适用范围；任何字段变更须形成新版本，不得原地覆盖。
