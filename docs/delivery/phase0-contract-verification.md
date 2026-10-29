# Phase 0 契约包验证报告

- 验证日期：2026-10-29
- 验证范围：`docs/contracts/` 下的 5 份说明文档与 `docs/contracts/schemas/**/*.json`（35 个 schema）
- 验证目录：`/home/bszheng/NoahsArk`
- 验证性质：只读一致性核验，不是契约评审，不是批准，不构成实现、测试、部署或发布授权
- 最终结论：**`needs-fix`**

> 重要声明：本报告不声称契约包已获批准。所有文档自述状态仍为 `frozen-candidate v1`（`thresholds.md` 为 `thresholds-v1` 候选）。本次未修改任何契约、`.omo`、`plan.md`、`docs/v2`、`openspec`、产品代码或 git 历史。

## 1. 验证环境

| 项 | 值 |
|---|---|
| 操作系统 | Linux |
| Python | `Python 3.12.3` |
| jsonschema | `4.10.3` |
| schema 总数 | 35 |
| 分族数量 | domain 12、security 9、evidence 7、experience 6、config 1 |

文档自述数量与磁盘一致：

- `README.md` §2.1 声明 12 个 domain schema，实际 12 个。
- `evidence-verdict.md` 头部与 §21 声明 7 个 evidence schema，实际 7 个。
- `ui-report-knowledge-audit.md` §8 声明 6 个 experience schema，实际 6 个。
- `security-node.md` 声明的 9 个 security schema，实际 9 个。
- `thresholds.md` 声明的 1 个 config schema，实际 1 个。

## 2. 已执行命令与结果

### 2.1 JSON 语法解析（全部 35 个 schema）

```bash
cd /home/bszheng/NoahsArk
fail=0
for f in $(find docs/contracts/schemas -name '*.json' | sort); do
  if python3 -m json.tool "$f" > /dev/null 2>/tmp/opencode/e; then
    echo "OK   $f"
  else
    echo "FAIL $f"
    cat /tmp/opencode/e
    fail=1
  fi
done
echo "PARSE_EXIT=$fail"
```

结果：

```text
35 个文件全部 OK
PARSE_EXIT=0
```

### 2.2 Draft 2020-12 元 schema 校验（全部 35 个 schema）

```bash
cd /home/bszheng/NoahsArk
python3 - <<'EOF'
import json, glob
from jsonschema import Draft202012Validator

files = sorted(glob.glob('docs/contracts/schemas/**/*.json', recursive=True))
bad = 0
for f in files:
    try:
        schema = json.load(open(f))
    except Exception as e:
        print("JSONERR", f, e)
        bad += 1
        continue
    try:
        Draft202012Validator.check_schema(schema)
        print("VALID", f)
    except Exception as e:
        print("SCHEMAFAIL", f, type(e).__name__, str(e).splitlines()[0])
        bad += 1
print("TOTAL", len(files), "BAD", bad)
EOF
```

结果：

```text
35 个文件全部 VALID
TOTAL 35 BAD 0
```

### 2.3 结构与引用核验

| 检查 | 命令/方法 | 结果 |
|---|---|---|
| `$schema` 均为 Draft 2020-12 | 逐文件读取 | 35/35 |
| 顶层 `additionalProperties: false` | 逐文件读取 | 35/35 |
| 顶层 `schema_version` 为 `"1.0"` 常量 | 逐文件读取 | 35/35 顶层一致 |
| 本地 `$ref` 可解析 | JSON Pointer 手工解析 | 0 个未解析 |
| 跨文件 `$ref` | `evidence-manifest.schema.json` → `evidence-item.schema.json` | 1 个合法相对引用；依赖 `$id` 注册，离线校验器需 resolver |
| SQLite 禁用 | `grep -RIn -i sqlite docs/contracts/` | 10 处，全部为“禁止/历史参考”说明；schema 内 0 处 |
| experience UI 字段策略 | 读取 6 个 schema 的 `x-ui-field-policy` | 6/6 存在 |
| 默认载荷含原始材料 | `grep -rn 'raw_audio_included.*true\|raw_logs_included.*true' docs/contracts/schemas/experience/` | 无结果 |
| thresholds 数值默认值 | 对 schema 中 61 个数值型 `default` 逐个在 `thresholds.md` 查找 | 61/61 存在 |

SQLite 命中位置均在以下文档而非 schema：`README.md:7,19,113,126`、`domain.md:6,35,616,718,853`、`ui-report-knowledge-audit.md:19`。

### 2.4 缺失 schema 检查

按文档中的 `.schema.json` 引用与各契约声明的清单逐一核对：**未发现缺失 schema**。`README.md`、`domain.md`、`security-node.md`、`evidence-verdict.md`、`ui-report-knowledge-audit.md`、`thresholds.md` 引用的 schema 均存在。

注：`security/lease.schema.json` 与 `domain/lease.schema.json`、`security/receipt.schema.json` 与 `domain/receipt.schema.json` 同名不同族，均存在，但语义不同（线协议消息 vs 领域实体），见 §3/§4。

## 3. 一致性核对矩阵

| 核对项 | 结论 | 证据与说明 |
|---|---|---|
| `schema_version` | **不通过（1 处硬冲突）** | 所有顶层均为 `"1.0"`；但 `security/receipt.schema.json` 内嵌 `evidence_manifest.schema_version` 为 `"2.0"`，与 evidence 契约的 `"1.0"` 冲突，见 F-01。 |
| IDs | **不通过** | domain 统一 UUID；security 使用前缀字符串并声明一对一映射；evidence 部分 ID 为 UUID、`task_id/revision_id/run_id` 却是无约束 string；experience 使用宽泛字符串正则。三处未形成统一表示，见 F-03。 |
| 状态词汇 | **部分不通过** | Task/Revision/Run/Gate/Lease/Device/Node 在 domain 文档与 schema 内一致；跨族存在 `run job_kind`、UI 投影、node receipt 状态词汇差异，见 F-04/F-06/F-08。 |
| 五轴判定 | **通过（有命名遗留）** | domain、evidence、security 的五轴枚举一致；`verification_status` 在节点回执固定 `NOT_RUN`；正式 PASS 五条件一致。节点回执字段命名仍与 domain 禁止字段冲突，见 F-07。 |
| PostgreSQL-only | **通过** | 文档一致声明 PostgreSQL 为唯一正式数据库；schema 无 SQLite/ORM 字段；SQLite 只出现在禁止条款与历史说明。 |
| 离线续跑 | **通过（有 1 处 schema 选项冲突）** | `thresholds.md` TH-L-11 为 fixed `allowed_for_started_frozen_runs`；domain §15.2、security §13.2、UI §2.5 一致。但 `job.stop_policy.on_lease_loss` 允许 `stop_safe`，见 F-05。 |
| STOP-first | **通过** | domain §15.3、security §13.3、thresholds TH-L-10、`thresholds.schema.json` 的 `stop_first_on_reconnect: required` 一致。 |
| 设备释放独立于证据/最终判定 | **通过（投影结构有冲突）** | domain L-5/L-6/P-4、evidence §13.3/§13.4、verdict schema 无 release 门控、device-occupancy 独立记录，语义一致。最小投影字段在 security receipt 中不一致，见 F-02。 |
| cleanup 回执语义 | **语义通过，结构不通过** | “缺回执只阻塞释放确认，不等于证据不完整”在 domain/evidence/security 文档一致；但 security 的 `cleanup_receipt` 结构与权威 cleanup-receipt 和 domain 最小投影不一致，见 F-02。 |
| 闭集命令枚举 / 无任意 shell | **通过** | `security/job.schema.json` 的 `action` 仅 `static_check/smoke/formal/diagnostics/cleanup`；schema 中无 `command`/`argv`/`script`/`shell` 字段；`constraints.allow_shell` 为 `false`；文档 §2.2/§11 明确禁止。 |
| 阈值优先级 | **部分不通过** | `thresholds.md` §3.1 与 `thresholds.schema.json` 的 5 层有效顺序一致；`security-node.md` §16.2 仍为 `task > node > global > schema_default`，且 §3.1 还列出第 6 层 schema 默认值，见 F-09。 |

## 4. 矛盾与问题清单

### F-01 [高] 节点回执内嵌 evidence manifest 的 `schema_version` 为 `"2.0"`

- `docs/contracts/schemas/security/receipt.schema.json:287-288`：`evidence_manifest.schema_version` 为 `const: "2.0"`。
- `docs/contracts/schemas/evidence/evidence-manifest.schema.json:31-33`：权威 evidence manifest 的 `schema_version` 为 `const: "1.0"`。
- 同一对象还声明 `predicate_type: "noahsark.test-evidence/v1"`（`security/receipt.schema.json:290-291`），形成“v1 predicate + v2 schema_version”自相矛盾。
- 影响：按 `README.md` §3.2，未知或错误 `schema_version` 必须 fail-closed；该回执引用的 manifest 无法通过 evidence 契约校验，也无法按同一版本解释。属于硬错误。

### F-02 [高] `cleanup_receipt` 最小释放投影在 security receipt 中与权威定义不一致

权威/领域定义：

- `docs/contracts/schemas/domain/receipt.schema.json:178-209` 要求最小投影包含 `cleanup_receipt_id`、`local_stop_confirmed`、`safe_cleanup_done`、`occupancy_reconciled`、`completed_at`，可选 `notes`。
- `docs/contracts/schemas/evidence/cleanup-receipt.schema.json` 的 `cleanupStatus` 为 `completed / completed_with_warnings / failed / not_required / unknown`，并要求 `local_stop_confirmed`、`safe_cleanup_done`。

security receipt 实际定义：

- `docs/contracts/schemas/security/receipt.schema.json:318-386` 的 `cleanup_receipt` 必填 `cleanup_id`、`status`、`completed_at`、`residual_processes`、`disk_freed_bytes`、`actions`、`notes`。
- `status` 仅为 `complete / partial / failed`（`:334-339`），没有 `unknown`、`not_required`、`completed_with_warnings`。
- 没有 `local_stop_confirmed`、`safe_cleanup_done`、`occupancy_reconciled`，无法表达设备释放的三项前置条件。
- 字段名是 `cleanup_id` 而非 `cleanup_receipt_id`。

与文档声明的冲突：

- `security-node.md:516` 与 `:865` 声明该对象是“设备释放前置条件的最小投影”，权威定义是 `schemas/evidence/cleanup-receipt.schema.json`，两者必须一致。
- `README.md:59` 同样要求两者必须一致。
- 实际三者字段/枚举不一致，无法满足“同一投影”。

影响：API 无法仅凭 security receipt 判定 `occupancy_reconciled`；`partial` 在权威契约中没有对应语义；缺失回执与失败回执的区分在投影层被压缩。

### F-03 [高] 同一实体的 ID 表示在三族契约中不一致且未全部声明映射

- domain：`task_id`、`revision_id`、`run_id`、`node_id`、`device_id`、`evidence_id` 等统一 UUID。示例：`schemas/domain/task.schema.json:28-30`。
- evidence：部分 ID 强制 UUID（`manifest_id`、`evidence_id`、`verdict_id`、`receipt_id`），但 `task_id/revision_id/run_id` 只是 `type: string`：
  - `schemas/evidence/evidence-manifest.schema.json:42-49`
  - `schemas/evidence/verdict.schema.json:39-46`
  - `schemas/evidence/evidence-item.schema.json:513-521`
  - `schemas/evidence/cleanup-receipt.schema.json:40-49`
  - evidence 文档 §1 声明“生产载荷同样使用 UUID”，但 schema 未约束。
- experience：`$defs.identifier` 统一使用 `^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$`（如 `schemas/experience/task-card.schema.json:883-885`），并用于 `task_id`、`revision_id`、`run_id`、`node_id`、`device_id`、`evidence_id`。
- security：使用 `node_<hex>`、`job_<hex>`、`lease_<hex>` 等前缀 ID，并在 `security-node.md:158-174` 声明与 domain UUID 一对一映射。

`README.md:55` 只登记了 domain 与 security 的差异，没有登记 evidence 的宽松 string 与 experience 的宽泛正则。影响：同一任务/运行在不同契约中可能拥有不同格式的 ID，消费者无法做统一外键或幂等键校验；这与 `domain.md` I-16“所有 ID UUID”冲突。

### F-04 [中] Job 的 `cleanup` action 在领域 Receipt 中没有对应 `job_kind`

- `schemas/security/job.schema.json:117-124` 的 `action` 包含 `cleanup`。
- `schemas/domain/receipt.schema.json:42-50` 的 `job_kind` 只有 `static_check / smoke / formal / stop_safe / diagnostics`，没有 `cleanup`。
- 同时 `job.mode` 包含 `diagnostics / cleanup`（`security/job.schema.json:138-145`），而 `Run.mode` 只有 `static / smoke / formal`（`schemas/domain/run.schema.json:35`）。

影响：清理作业产生的节点回执无法映射到领域 Receipt 的 `job_kind`，也无法映射到 Run 的 `mode`；需要明确“协议动作/模式”与“领域 job_kind/run mode”的映射表，或在领域枚举中补齐。

### F-05 [中] `job.stop_policy.on_lease_loss` 允许 `stop_safe`，与固定离线续跑语义冲突

- `schemas/security/job.schema.json:426-431`：`on_lease_loss` 允许 `continue_started_job` 或 `stop_safe`。
- `thresholds.md:132`（TH-L-11）：`offline.continuation` 为 fixed `allowed_for_started_frozen_runs`。
- `thresholds.md:128`（TH-L-07）：`lease.expiry_semantics` 为 fixed `renewal_deadline_only`。
- `security-node.md:651`：已启动冻结压测继续执行，不因通信中断而中止。
- `domain.md:658`：已启动冻结压测在通信中断、心跳不可达、`expires_at` 到期后继续执行。

若 `on_lease_loss` 指“租约过期/续约截止”，则允许 `stop_safe` 与 fixed 规则直接冲突；若指“租约被撤销/设备所有权变更”，文档没有区分。需要冻结定义或移除该选项。

### F-06 [中] UI 投影对同一概念使用不同枚举且未声明映射

- 占用状态：`schemas/experience/task-card.schema.json:380-382` 为 `OCCUPIED / RESERVED / FREE / UNKNOWN`；domain 为 `IDLE / OCCUPIED / RELEASING`（`schemas/domain/lease.schema.json:56`、`schemas/domain/device.schema.json:92`）。
- 通信状态：`task-card.schema.json:657-659` 为 `LIVE / DEGRADED / OFFLINE / UNKNOWN`；domain/security 为 `ONLINE / STALE / OFFLINE`。
- 门禁状态：`task-card.schema.json:244-247` 为 `PASS / FAIL / PENDING / BLOCKED / NOT_APPLICABLE / UNKNOWN`；domain Gate 为 `PENDING / IN_PROGRESS / PASSED / FAILED / BLOCKED / SKIPPED`（`schemas/domain/gate.schema.json:41-44`）。
- 运行状态：`task-card.schema.json:147` 附近为 `NOT_STARTED / RUNNING / STOPPING / BLOCKED / STOPPED / COMPLETED / FAILED / UNKNOWN`；domain `lifecycle_status` 为 `CREATED / DISPATCHED / RUNNING / FINISHING / COMPLETED / STOPPED / ABORTED / BLOCKED`。

投影层可以有自己的展示词汇（`ui-report-knowledge-audit.md` D-01 明确任务卡是派生投影），但当前没有一张“UI 词汇 → 权威字段”的映射表。影响：消费方无法确定 `FREE` 对应 `IDLE` 还是 `RELEASING`，`LIVE` 对应 `ONLINE` 还是 `STALE`；这与“不得由通信状态推断占用”的规则结合时容易产生误读。

### F-07 [中] 节点回执仍包含名为 `business_verdict` 的字段，与 domain Receipt 禁止字段冲突

- `schemas/security/receipt.schema.json:160-205` 的 `outcome` 必填 `business_verdict`，枚举与平台五轴同名同值。
- `schemas/domain/receipt.schema.json:90` 明确说明 “Receipts must not contain business_verdict or verification_status”；domain §12.1 将该组列为“必须不存在”的禁止字段。
- `README.md:57` 已登记该差异，要求线协议 `outcome` 必须明确为“节点观察事实”，API 映射为 `node_observed`，不得直接当作平台判定。
- `security-node.md:515` 与 `evidence-verdict.md:1010-1013` 有语义澄清，但 security receipt schema 没有把字段改名为 `node_observed_*`，也没有 `used_for_decision: false` 之类的 schema 常量（evidence 的 `nodeReportedStatus` 有，见 `schemas/evidence/verdict.schema.json` 的 `$defs.nodeReportedStatus.used_for_decision: false`）。

影响：字段级契约仍允许节点写入与平台判定同名的轴值；仅靠文档约束，无法由 schema 阻止调用方误用。该问题已在 README 登记为待对齐，但尚未关闭。

### F-08 [低] `node_receipt.status` 在 evidence 与 security 中枚举不一致

- `schemas/evidence/evidence-manifest.schema.json:934-942`：`received / started / completed / aborted / failed / unknown`。
- `schemas/security/receipt.schema.json:135-143`：`accepted / rejected / started / completed / failed / stopped / blocked / infra_error / cleanup_complete`。

两者都表示节点回执状态，但一个使用 `received/accepted`、`aborted/stopped`，security 还多出 `rejected/blocked/infra_error/cleanup_complete`。如果 evidence manifest 的 `node_receipt` 只是 security receipt 的投影，需要一张枚举映射；否则同一回执在证据清单中无法保真表达。

### F-09 [低] 阈值优先级层数与措辞未统一

- `thresholds.md:82-90`：从低到高为
  `schema 默认值 < 全局默认 < 环境覆盖 < 任务修订覆盖 < 运行覆盖 < 硬安全边界`（6 层）。
- `schemas/config/thresholds.schema.json:59-85`：`order` 固定 5 项，`global_default / environment / task_revision / run_override / hard_safety_floor`，没有 `schema_default`。
- `thresholds.md:442`（D-TH-14）也写作 5 层，未列 schema 默认值。
- `security-node.md:765-773` §16.2 仍写 `task > node > global > schema_default`。
- `README.md:60` 已登记该差异，要求 P0-05 同步时统一 `node == environment`，但当前仍未统一。

影响：`schema_default` 是否作为独立层、`node` 与环境层是否等价，在两个契约中仍有两种写法；实际数值默认值一致（61/61 核对通过），但优先级解释存在歧义。

### F-10 [低] `security-node.md` 内部对日志分片默认值自相矛盾

- `security-node.md:597`：分片大小“默认 64 KiB，可调至 256 KiB”。
- `security-node.md:31`：日志结果分片 256 KiB。
- `security-node.md:753`：日志分片 256 KiB。
- `thresholds.md:314`（TH-Q-05）：`log.query.fragment_bytes` 默认 `262144`（256 KiB）。

同一文档三处默认值不一致（64 KiB vs 256 KiB），且 thresholds 以 256 KiB 为准。需要同步修正 §12.3 或明确“默认 64 KiB、最大 256 KiB”的准确语义（当前写法与 §1/§16.1 的“默认 256 KiB”冲突）。

### F-11 [低] `README.md` 对 security-node 的租约旧措辞描述已过期

- `README.md:56` 称 `security-node.md` “仍有一处‘租约到期后进入 `lease_expired`’的旧措辞”。
- 实际 `grep -RIn 'lease_expired' docs/contracts/` 在 `security-node.md` 中无命中；`security-node.md:488,498,644` 已明确 `expired` 仅表示续约截止、设备保持 `OCCUPIED`。
- `schemas/security/lease.schema.json` 的 `state` 含 `expired` 仍然存在，这部分描述正确。

影响：README 的跨契约待对齐项已部分过时，评审者可能重复处理已修正的问题。

### F-12 [信息] 其他非阻断观察

- `$id` 基址不统一：domain 使用 `https://noahsark.invalid/...`，evidence 使用 `https://schemas.noahsark.local/...`，experience/security/config 使用 `https://noahsark.local/...`。当前本地 `$ref` 不依赖网络，但统一注册表时会出现多个命名空间。
- `security/job.schema.json:188` 的 `execution_bundle.schema_version` 为 `"noahsark.execution-bundle/v1"`，与 domain `ExecutionBundle.schema_version: "1.0"` 不同。若这是“bundle 格式版本”而非“载荷 schema 版本”，应在文档中显式区分；否则会被误读为同一版本字段。
- `evidence-manifest.schema.json` 对 `evidence-item.schema.json` 使用裸相对 `$ref`；`Draft202012Validator.check_schema` 不解析它，离线实例校验需要注册 `$id`。不是错误，但 CI 需要配置 resolver。

## 5. 未解决问题

以下问题在契约自身或跨契约层面仍未关闭；本次不替作者做决定：

1. **ID 统一**：domain UUID、security 前缀 ID、evidence 宽松 string、experience 宽泛正则之间缺少统一映射（README §2.3-1 只覆盖 domain/security；F-03）。
2. **cleanup 最小投影**：security receipt 应补齐三项释放布尔值与 `cleanup_receipt_id`，还是由 API 从权威 cleanup receipt 重新投影（F-02；README §2.3-5）。
3. **节点 outcome 命名**：是否把 `outcome.business_verdict` 改成 `node_observed_business_verdict` 并加 `used_for_decision=false`，或由 API 层严格映射（F-07；README §2.3-3）。
4. **lease loss 定义**：`on_lease_loss=stop_safe` 是否仅指撤销/所有权变更，还是也包含续约截止（F-05）。
5. **阈值层命名**：`node` 是否等同 `environment`，`schema_default` 是否显式入列（F-09；README §2.3-6）。
6. **UI 词汇映射**：`FREE/RESERVED`、`LIVE/DEGRADED`、`PASS/FAIL` 等投影枚举与权威枚举的映射表（F-06）。
7. **证据切片粒度**：每个任务/profile 的必需证据切片未冻结（`evidence-verdict.md` Q-EV-01）。
8. **回执签名**：cleanup receipt / node receipt 是否强制签名、算法与证书链未冻结（`evidence-verdict.md` Q-EV-02）。
9. **报告多运行分母合并**：同一修订下多个 `run_id` 的分母、重试与补传合并规则需与 evidence 契约对齐（`ui-report-knowledge-audit.md` 开放问题 8）。
10. **陈旧/刷新阈值**：任务卡的 `freshness.stale_after_seconds`、刷新间隔由 P0-08 冻结，当前只约定服务端解析（`ui-report-knowledge-audit.md` 开放问题 1）。
11. **节点证书算法**：Windows/CNG 对 Ed25519 X.509 的支持、ES256 迁移窗口、TPM/DPAPI 方案未冻结（`security-node.md` §20-1/2）。
12. **自动批准边界**：生产是否允许任何 enrollment 自动批准仍待确认（`security-node.md` §20-5）。

## 6. 最终结论

**`needs-fix`**

判定依据：

- `confirmed` 不成立：存在至少 3 个高严重度的具体契约冲突（F-01 `schema_version` 2.0、F-02 cleanup 投影结构、F-03 ID 表示），不是单纯的文档措辞问题。
- `blocked` 不成立：没有缺失 schema，没有工具缺失，35/35 文件可解析且通过 Draft 2020-12 元 schema 校验；可以完成验证。
- `needs-fix` 成立：包在结构上可用，但跨契约字段/枚举/版本尚未一致，不能视为内部一致的冻结候选。

修复优先级建议：

1. F-01：把 security receipt 内嵌 manifest 的 `schema_version` 改为 `"1.0"`，或明确拆分“manifest 格式版本”与“payload schema 版本”。
2. F-02：让 security `cleanup_receipt` 与 domain 最小投影、evidence 权威回执三者字段和枚举一致。
3. F-03：统一 `task_id/revision_id/run_id` 的 UUID 约束，或在所有契约中显式声明 alias/映射并加入 schema 校验。
4. F-04/F-05：补齐 cleanup `job_kind`/`mode` 映射，冻结 `on_lease_loss` 语义。
5. F-06/F-08：为 UI/evidence 投影枚举增加显式映射表。
6. F-09/F-10/F-11：同步文档措辞与 README 待对齐项。

## 7. 非批准声明与变更范围

- 本报告**不**表示契约包已获批准，不表示任何字段已冻结为生产契约。
- 本报告**不**构成实现、测试、部署、发布或任务执行授权。
- 本次只创建 `docs/delivery/phase0-contract-verification.md`；未修改 `docs/contracts/`、`.omo/`、`plan.md`、`docs/v2/`、`openspec/`、`solutions/`、产品代码或 git 历史。
- 所有结论基于 2026-10-29 工作区快照；未执行任何真实设备、节点或网络动作。
