# Phase 0 契约包整改复验报告（F-01..F-11）

- 复验日期：2026-10-29
- 复验范围：`docs/contracts/` 下 6 份契约文档与 `docs/contracts/schemas/**/*.json`（35 个 schema）
- 工作目录：`/home/bszheng/NoahsArk`
- 上一轮报告：`docs/delivery/phase0-contract-verification.md`（结论 `needs-fix`，2026-10-29）
- 复验性质：只读一致性核验，不是契约评审、不是批准，不构成实现、测试、部署或发布授权
- **最终结论：`PASS`（附 3 项非阻断遗留，见 §5）**

> 重要声明：本报告不声称契约包已获批准。所有契约文档自述状态仍为 `frozen-candidate v1`（`thresholds.md` 为 `thresholds-v1` 候选），`README.md` §2.3 明确“仍需 Orchestrator 评审确认”。本次**未修改任何契约、schema、`.omo`、`plan.md`、`docs/v2`、`openspec`、产品代码或 git 历史**；唯一新增文件为本报告。

## 1. 验证环境

| 项 | 值 |
|---|---|
| 操作系统 | Linux |
| Python | 3.12.3 |
| jsonschema | 4.10.3 |
| schema 总数 | 35 |
| 分族数量 | domain 12、security 9、evidence 7、experience 6、config 1 |

## 2. 已执行命令与结果

### 2.1 JSON 解析 + Draft 2020-12 元 schema 校验（35 个）

```bash
cd /home/bszheng/NoahsArk
python3 - <<'EOF'
import json, glob
from jsonschema import Draft202012Validator
files = sorted(glob.glob('docs/contracts/schemas/**/*.json', recursive=True))
bad = parse_bad = 0
for f in files:
    try:
        schema = json.load(open(f))
    except Exception as e:
        print("JSONERR", f, e); parse_bad += 1; continue
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as e:
        print("SCHEMAFAIL", f, type(e).__name__, str(e).splitlines()[0]); bad += 1
print("TOTAL", len(files), "PARSE_BAD", parse_bad, "SCHEMA_BAD", bad)
EOF
```

实际输出：

```text
TOTAL 35 PARSE_BAD 0 SCHEMA_BAD 0
```

### 2.2 结构不变量（35 个逐文件）

```bash
python3 - <<'EOF'
import json, glob
files = sorted(glob.glob('docs/contracts/schemas/**/*.json', recursive=True))
bad_schema=[]; bad_ap=[]; bad_ver=[]
for f in files:
    s=json.load(open(f))
    if s.get('$schema')!='https://json-schema.org/draft/2020-12/schema': bad_schema.append(f)
    if s.get('additionalProperties') is not False: bad_ap.append(f)
    if s.get('properties',{}).get('schema_version',{}).get('const')!='1.0': bad_ver.append(f)
print("BAD_SCHEMA",bad_schema)
print("BAD_AP",bad_ap)
print("BAD_VER",bad_ver)
EOF
```

实际输出（三项均为空列表）：

```text
BAD_SCHEMA []
BAD_AP []
BAD_VER []
```

### 2.3 `$ref` 解析

- 本地 `$ref` 全部可解析。
- 跨文件 `$ref` 仅 1 处：`schemas/evidence/evidence-manifest.schema.json` → `evidence-item.schema.json`，可解析。
- 结果：`UNRESOLVED 0`；`CROSS_FILE_REFS [('.../evidence/evidence-manifest.schema.json', 'evidence-item.schema.json')]`。
- 说明：`Draft202012Validator.check_schema` 不解析裸相对 `$ref`；离线实例校验仍需注册 `$id` resolver，这一点与上轮一致，不是错误。

### 2.4 数值默认值一致性（辅助）

`schema/config/thresholds.schema.json` 中数值型 `default` 计数：`61`，与 `thresholds.md` 的默认值集合仍一致（上轮 61/61）。

### 2.5 整改台账检查

- `docs/delivery/phase0-contract-verification.md` **没有** “整改/remediation” 章节（全文仅在 §6 有“修复优先级建议”，无“已修复”回填）。
- 因此本复验不依赖上一报告的回填，而是对 11 项逐条直接读取当前文件与 schema 取证。
- `docs/delivery/construction-progress.md:14` 记录 P0-04 状态为“返工/待验证”，并显式引用待核验文件 `phase0-contract-remediation-verification.md`（即本报告）。

## 3. F-01..F-11 逐项复验

| 编号 | 上轮问题 | 当前状态 | 证据 |
|---|---|---|---|
| F-01 | 节点回执内嵌 manifest 的 `schema_version` 为 `2.0` | **已修复** | `schemas/security/receipt.schema.json:300-306` 为 `const: "1.0"`，并注明必须等于 `evidence/evidence-manifest.schema.json` 的 1.0；`predicate_type` 仍为 `noahsark.test-evidence/v1`，且已写明“predicate 版本 ≠ payload schema 版本”。`schemas/evidence/evidence-manifest.schema.json:31-33` 为 `const: "1.0"`。grep `"2.0"` 在 35 个 schema 中 0 命中。 |
| F-02 | security `cleanup_receipt` 与 domain 最小投影、evidence 权威回执字段/枚举不一致 | **已修复（字段名与枚举一致）** | security `cleanup_receipt`（`security/receipt.schema.json:329-400`）与 domain（`domain/receipt.schema.json:180-209`）均必填 `cleanup_receipt_id`、`cleanup_status`、`local_stop_confirmed`、`safe_cleanup_done`、`occupancy_reconciled`、`completed_at`，可选 `notes`；两侧 `$defs.cleanupStatus` 枚举均为 `completed / completed_with_warnings / failed / not_required / unknown`，与 `evidence/cleanup-receipt.schema.json:594` 完全一致。`cleanup_receipt_id` ↔ 权威回执 `receipt_id` 及 `occupancy_reconciled` 的控制面来源见 `evidence-verdict.md:713-721`（§12.1.1）。残余结构差异见 §5 R-02。 |
| F-03 | ID 表示跨族不一致且未全部声明映射 | **已修复** | evidence 的 `task_id/revision_id/run_id` 已强制 UUID：`evidence-manifest.schema.json:42-49`、`verdict.schema.json:39-46`、`cleanup-receipt.schema.json:40-49`；experience `$defs.identifier` 改为 UUID 正则：`experience/task-card.schema.json:883-886`（6 个 experience schema 同值）。security 的实体 ID（`job_id/lease_id/node_id/receipt_id/message_id`）全部为 UUID。README §2.3-1（`:57`）登记统一规则，`security-node.md` §4.5（`:159-174`）定义 `wire_id` 显式别名规则。仅消息级 ID（`stop_id/query_id/anomaly_id/enrollment_id`）保留命名空间前缀，文档已显式标注为非实体 ID。 |
| F-04 | `cleanup` action 在领域 Receipt 无 `job_kind` 映射 | **已修复** | `domain/receipt.schema.json:42-50` 的 `job_kind` 已含 `cleanup`，并写明“cleanup/diagnostics 是辅助作业，不改变 Run.mode”；映射表见 `security-node.md` §19.2（`:873`）与 `domain.md` §12.3（`:595`）。`Run.mode` 仍仅 `static/smoke/formal`（`domain/run.schema.json`）。 |
| F-05 | `on_lease_loss` 允许 `stop_safe` | **已修复（改为固定值 + 独立原因）** | `security/job.schema.json:440-447`：`on_lease_loss` 为 `const: continue_started_job`；新增 `on_explicit_revoke: stop_safe`（租约撤销/所有权变更）与 `on_safety_incident: stop_safe`（安全事件），并在 `security-node.md:476` 明确二者不得合并。 |
| F-06 | UI 投影枚举无权威映射表 | **已修复** | `ui-report-knowledge-audit.md` §2.7（`:194-243`）给出 occupancy / communication / gate / run 四张映射表、禁止推断规则与 fail-closed 规则。映射引用的权威值均存在：Lease.`occupancy_state`=`OCCUPIED/RELEASING/IDLE`、Device.`pool_state` 含 `RESERVED/READY`、Gate.status=`PENDING/IN_PROGRESS/PASSED/FAILED/BLOCKED/SKIPPED`、Run.`lifecycle_status` 8 值、Node.`communication_state`=`ONLINE/STALE/OFFLINE`。残余文档精度问题见 §5 R-03。 |
| F-07 | 节点回执 `business_verdict` 与 domain 禁止字段冲突 | **已修复** | `security/receipt.schema.json:160-216`：五轴全部改名为 `node_observed_*`，`used_for_decision` 为 `const: false`，描述明确“节点只回传事实，控制面必须从已验证证据重算五轴”。`security-node.md:517` 与 README §2.3-3（`:59`）同步。evidence `verdict.schema.json` 的 `$defs.nodeReportedStatus.used_for_decision` 亦为 `const: false`。 |
| F-08 | `node_receipt.status` 枚举不一致 | **已修复（显式映射）** | `security-node.md` §19.2（`:873` 起）给出 9 个线协议状态的完整映射：`accepted→received`、`rejected→unknown`、`started→started`、`completed→completed`、`failed→failed`、`stopped→aborted`、`blocked→aborted`、`infra_error→failed`、`cleanup_complete→completed`；`evidence-verdict.md` §12.5（`:760-766`）引用同一映射。security `status` 9 值、evidence `node_receipt.status` 6 值，映射覆盖全部 9 个输入。 |
| F-09 | 阈值优先级层数与措辞未统一 | **已修复** | 三处统一为六层：`thresholds.md:80-91`、`thresholds.schema.json` `precedence.order`（6 项，含 `schema_default`，且 `allOf` 强制包含 `schema_default` 与 `hard_safety_floor`）、`security-node.md:772`（明确 `node == environment`，旧写法仅作历史说明）。全目录已无“5 层/五层”写法。 |
| F-10 | 日志分片默认值自相矛盾 | **已修复** | `security-node.md:599-601` 统一为“单分片最大 256 KiB；默认 256 KiB；硬上限 256 KiB，只能收紧”，与 `:31`、`:757` 及 `thresholds.md:314`（`fragment_bytes` 默认 262144）一致；旧“默认 64 KiB”写法已消失。 |
| F-11 | README 对 security-node 租约旧措辞描述过期 | **已修复** | `README.md:58` 已改为“已无 `lease_expired` 旧措辞”，并保留 `lease.state=expired` 仅表示续约截止的正确说明。`grep lease_expired` 在 `security-node.md` 0 命中。 |

**F-01..F-11：11/11 已关闭。**

## 4. 跨族一致性抽查（整改未回退的部分）

| 检查 | 结果 |
|---|---|
| 顶层 `schema_version` 常量 | 35/35 为 `"1.0"` |
| 五轴枚举（domain/evidence/security） | `business_verdict` 6 值、`validity_status` 4 值、`execution_status` 5 值、`evidence_status` 4 值、`verification_status` 3 值，三族一致 |
| `predicate_type` | security 投影与 evidence manifest 均为 `noahsark.test-evidence/v1` |
| cleanup 状态词汇 | domain/security/evidence 三处枚举完全一致（5 值） |
| action/mode/run mode | 协议 action 5 值；`Run.mode` 仍 3 值；cleanup/diagnostics 明确不改变 run mode |
| schema 数量声明 | domain 12、security 9、evidence 7、experience 6、config 1，与磁盘一致 |

## 5. 剩余发现（非阻断，低/信息级）

以下为本次复验仍存在的**非阻断**遗留。它们不改变 `PASS` 结论：无缺失 schema、无解析/元 schema 失败、无跨契约字段/枚举硬冲突。

### R-01 [低，信息] `execution_bundle.schema_version` 的“格式版本 vs 载荷版本”仍未在文档中区分

- `schemas/security/job.schema.json:197`：`execution_bundle.schema_version` 为 `const: "noahsark.execution-bundle/v1"`。
- `schemas/domain/execution-bundle.schema.json:26`：领域 ExecutionBundle 的 `schema_version` 为 `const: "1.0"`。
- 上一轮 F-12 已将其列为“信息级、需在文档显式区分”。当前 `README.md`、`security-node.md`、`domain.md` 均未解释该命名空间版本与领域载荷版本的关系；`security-node.md:561` 只要求“未知 bundle 版本 → 拒绝”。
- 影响：不会破坏任何 schema 校验（前者是 job 内的 bundle 引用句柄，后者是 bundle 载荷本身），但读者可能误以为二者必须相等。属于文档可读性/版本语义缺口，不是字段冲突。

### R-02 [低] security 最小投影多出可选 `operational_detail`，与“同一最小投影”措辞不完全一致

- security `cleanup_receipt` 允许可选 `operational_detail`（`security/receipt.schema.json:370`，内含 `residual_processes`、`disk_freed_bytes`、`actions`、`failure_code`）。
- domain `cleanup_receipt` 为 `additionalProperties: false` 且无 `operational_detail`（`domain/receipt.schema.json:180-209`）。
- `README.md:61` 称两者“是同一最小释放投影……详细运维字段只允许放在……可选 `operational_detail` 下”，但 domain 侧没有该字段。
- 影响：语义无冲突（domain 只承载最小释放事实，security 额外承载运维细节），但“同一投影”表述对 domain 不成立，建议改为“security 投影为 domain 最小投影的超集”。非阻断。

### R-03 [低] README 声称 §2.7 覆盖 evidence 映射，但 §2.7 无 evidence 轴映射表

- `README.md:64`：§2.7 给出 occupancy/communication/gate/run/**evidence** 的权威字段映射。
- 实际 `ui-report-knowledge-audit.md` §2.7（`:194-243`）只有 occupancy、communication、gate、run 四张表；evidence 轴值在 §2.3（`:105`）列出。
- 同时 `experience/report.schema.json` 的投影轴允许 `UNKNOWN`（`execution_status`、`evidence_status`、`verification_status`），而权威枚举中这三轴没有 `UNKNOWN`。§2.7 的“无法映射一律 fail-closed 为 `UNKNOWN`”可覆盖该语义，但缺少逐轴登记，未满足 §2.7 末尾“新增投影枚举必须先在此登记”的自定规则。
- 影响：展示层 fail-closed 语义仍成立，不产生错误判定；属于映射表不完整与 README 表述过度。非阻断。

### 其他观察（不计为发现）

- `docs/delivery/phase0-contract-verification.md` 无整改回填章节；本报告已用直接取证替代，不影响结论。
- `README.md:65` 提到的“架构提案 §6 / 模块设计 M-03 审批超时旧措辞”属于契约目录外文档，本次范围不外扩。

## 6. 未解决问题

### 6.1 上一轮 §5 中已被本轮整改关闭的问题

1. ID 统一（原问题 1）：已由 UUID 统一 + `wire_id` 规则关闭。
2. cleanup 最小投影（原问题 2）：已由三处一致字段/枚举 + §12.1.1 映射关闭（结构超集差异见 R-02）。
3. 节点 outcome 命名（原问题 3）：已由 `node_observed_*` + `used_for_decision: false` 关闭。
4. lease loss 定义（原问题 4）：已由 `on_lease_loss` 固定 + `on_explicit_revoke`/`on_safety_incident` 拆分关闭。
5. 阈值层命名（原问题 5）：已由六层统一、`node == environment` 关闭。
6. UI 词汇映射（原问题 6）：已由 §2.7 四表关闭（evidence 轴登记缺失见 R-03）。

### 6.2 仍然开放（契约字段结构之外，需所有者/后续阶段决定，本次不替作者决定）

1. **证据切片粒度**：每任务/profile 的必需证据切片未冻结（`evidence-verdict.md` Q-EV-01，`:1203`）。
2. **回执签名**：cleanup / node receipt 是否强制签名、算法与证书链未冻结（Q-EV-02，`:1204`）。
3. **报告多运行分母合并**：同修订多 `run_id` 的分母/重试/补传合并规则（`ui-report-knowledge-audit.md` 开放问题 8）。
4. **陈旧/刷新阈值**：`freshness.stale_after_seconds` 等数值由 P0-08 冻结，当前只约定服务端解析（`ui-report-knowledge-audit.md` 开放问题 1，`:669`）。
5. **节点证书算法**：Windows/CNG 对 Ed25519 X.509 的支持、ES256 迁移窗口、TPM/DPAPI 方案（`security-node.md` §20-1/2）。
6. **自动批准边界**：生产是否允许任何形式 enrollment 自动批准仍待确认（`security-node.md` §20-5，`:916`）。
7. **R-01 bundle 版本语义**：是否把 `noahsark.execution-bundle/v1` 明确为“格式标识”并在文档登记。

## 7. 结论与判定依据

**`PASS`**

- 35/35 schema 全部可解析并通过 Draft 2020-12 元 schema 校验（`PARSE_BAD 0`、`SCHEMA_BAD 0`）。
- 35/35 顶层 `schema_version` 为 `"1.0"`，35/35 `additionalProperties: false`，`$ref` 0 处不可解析。
- F-01..F-11 全部关闭，且整改未引入新的跨族字段/枚举冲突。
- 不判 `NEEDS-FIX`：不存在缺失 schema、工具缺失、版本硬冲突或跨契约字段/枚举硬冲突；R-01..R-03 为非阻断的版本语义/文档精度遗留，不影响 schema 可校验性与判定语义。
- 不判 `blocked`：验证可完整执行，无需外部设备、网络或凭据。

## 8. 非批准声明与变更范围

- 本报告**不**表示契约包已获批准或已冻结为生产契约；契约自述仍为 `frozen-candidate v1`，需 Orchestrator 评审确认。
- 本报告**不**构成实现、测试、部署、发布或任务执行授权。
- 本次仅创建 `docs/delivery/phase0-contract-remediation-verification.md`；未修改 `docs/contracts/`、`.omo/`、`plan.md`、`docs/v2/`、`openspec/`、`solutions/`、产品代码或 git 历史。
- 所有结论基于 2026-10-29 工作区快照；未执行任何真实设备、节点或网络动作；未读取或输出任何密钥、凭据或个人信息。
