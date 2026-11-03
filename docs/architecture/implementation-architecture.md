# NoahsArk 目标实施架构

- 状态：Draft for review
- 日期：2026-10-31
- 适用范围：控制面、Node Agent、工具通道、证据/产物、调试沙箱、UI
- 结论：**中心推理 + 节点确定性执行 + 类型化工具优先 + 沙箱化代码执行兜底**

## 1. 目标与非目标

### 目标

1. 任务可编排：创建任务、绑定 OpenCode 会话、执行、回写结果。
2. 执行可复现：同一工具 + 同一参数 → 同一行为。
3. 节点可管控：只出站、只执行白名单工具、可审计、可回滚。
4. 长尾可兜底：未知硬件问题允许写脚本，但必须在沙箱内。
5. 证据可追溯：命令、日志、产物、审批、结果全链路可查。
6. 工具可演进：一次性脚本可晋升为版本化工具。

### 非目标

- 不在每台生产节点上常驻完整 coding agent。
- 不开放节点入站端口。
- 不允许 LLM 直接拼 shell 命令操作硬件。
- 不把串口日志、固件、证据留在编排机本地目录。
- 首期不做多租户和跨地域 HA。

## 2. 现状与差距

### 已有

- 控制面：FastAPI + PostgreSQL + SQLAlchemy/Alembic。
- 任务：`Task` / `Revision` / `SupervisorSession`，OpenCode 会话监督。
- 节点：注册、心跳、命令轮询、回执、对账；per-node token。
- 命令通道：`usb.scan` 已跑通。
- UI：任务、节点/设备、报告、知识库四区。
- 设备：USB 树、串口、音频端点、DeviceKey。

### 关键差距

| 差距 | 现状 | 影响 |
|---|---|---|
| 任务状态不流转 | `Task.status` 创建后一直 `DRAFT` | UI 显示草稿，无法反映完成/失败 |
| 命令无 lease/TTL | QUEUED 可能永久滞留 | 节点离线后任务卡死 |
| 无工具注册表 | 命令是硬编码字符串 | 无法版本化、授权、灰度 |
| 无产物模型 | 串口日志落在编排机 `debugdata/` | 证据不可追溯、节点本地文件不可见 |
| 无调试沙箱 | Agent 可在节点直接跑 PowerShell | 爆炸半径过大、无审批 |
| 报告/知识库仍是 fixture | 页面不读 `/reports`、`/knowledge` | 平台看起来像半演示 |
| 无 SSE/通知 | 前端轮询 | 状态延迟、体验差 |

## 3. 目标架构总图

```text
┌──────────────────────────────────────────────────────────────┐
│ 1. 体验 / API 平面                                            │
│    Web UI（任务/节点/报告/知识） · REST · SSE · CLI           │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│ 2. 控制平面（Linux / FastAPI）                                │
│    Task · Revision · Approval · Gate · Supervisor/OpenCode    │
│    Tool Registry · Policy Engine · Scheduler · Outbox         │
└──────────────┬───────────────────────────────┬───────────────┘
               │ 命令队列（lease/TTL/幂等）     │ 事件
┌──────────────▼───────────────┐   ┌───────────▼───────────────┐
│ 3. 执行平面（每台节点）       │   │ 4. 数据 / 证据平面         │
│    Node Agent（瘦执行器）     │   │ PostgreSQL                │
│    Local Tool Server          │   │ Object Store（日志/产物）  │
│    serial / usb / device      │   │ Event Log · Audit Chain   │
│    Debug Sandbox（可选）      │   │ Artifact digest           │
└──────────────┬───────────────┘   └───────────────────────────┘
               │ 只出站（poll / WebSocket）
┌──────────────▼───────────────────────────────────────────────┐
│ 5. 安全 / 运维平面                                            │
│    Identity/RBAC · mTLS/token · Secrets · Egress Allowlist    │
│    Metrics/Logs/Traces · Backup/DR · Signed Tool Bundles      │
└──────────────────────────────────────────────────────────────┘
```

## 4. 组件与代码落点

| 组件 | 代码位置 | 职责 | 不做什么 |
|---|---|---|---|
| Web UI | `design/ui-app/src` | 任务、节点、报告、知识、命令/产物展示 | 不直接调用节点 |
| API | `apps/control_plane/noahsark/api` | REST、鉴权、校验、SSE | 不执行硬件操作 |
| Task/Supervisor | `services/supervision.py` | 任务状态、OpenCode 会话、提示词 | 不直接跑脚本 |
| Tool Registry | 新增 `services/tools.py` | 工具 manifest、版本、签名、部署 | 不信任节点上报 |
| Policy/Approval | 新增 `services/policy.py` | 工具授权、风险分级、审批 | 不由 LLM 自行批准 |
| Command Queue | `services/node_commands.py` | 入队、lease、TTL、重试、幂等 | 不做长时间同步等待 |
| Artifact Store | 新增 `services/artifacts.py` | 内容寻址、上传/下载、digest | 不把大文件塞进消息表 |
| Event/Outbox | 新增 `services/events.py` | 领域事件、SSE、通知 | 不做业务决策 |
| Node Agent | `apps/node_agent/noahsark_node` | 轮询、领取、执行、回传 | 不跑 LLM、不做规划 |
| Local Tool Server | 新增 `noahsark_node/tools/` | 类型化工具实现 + schema | 不暴露任意 shell |
| Debug Sandbox | 新增 `noahsark_node/sandbox/` | 受限执行 `debug.run` | 不挂载生产凭证 |

## 5. 核心数据模型

### 5.1 工具

```text
tools
  tool_id            uuid pk
  name               text            -- serial.reboot
  version            text            -- 1.2.0
  manifest           jsonb           -- JSON Schema + 权限 + 超时 + 风险
  bundle_sha256      text
  status             text            -- DRAFT | ACTIVE | DEPRECATED
  created_at         timestamptz
  unique(name, version)

node_tools
  node_id            uuid
  tool_id            uuid
  state              text            -- PENDING | INSTALLED | FAILED
  deployed_at        timestamptz
  last_error         text
```

### 5.2 命令（扩展现有 `node_commands`）

```text
node_commands
  command_id         uuid pk
  node_id            uuid
  task_id            uuid null
  tool_name          text
  tool_version       text
  args               jsonb
  status             text            -- QUEUED | LEASED | RUNNING | SUCCEEDED |
                                    -- FAILED | TIMEOUT | DENIED | CANCELLED | UNKNOWN
  priority           int
  idempotency_key    text unique
  approval_id        uuid null
  lease_owner        text
  lease_expires_at   timestamptz
  attempt            int
  max_attempts       int
  timeout_ms         int
  deadline           timestamptz
  created_at         timestamptz
  started_at         timestamptz
  finished_at        timestamptz
```

### 5.3 结果与产物

```text
command_results
  command_id         uuid pk fk
  status             text
  exit_code          int
  result             jsonb
  stdout_artifact_id uuid null
  stderr_artifact_id uuid null
  error_code         text
  error_message      text
  started_at         timestamptz
  finished_at        timestamptz

artifacts
  artifact_id        uuid pk
  task_id            uuid null
  command_id         uuid null
  sha256             text
  size_bytes         bigint
  media_type         text
  storage_key        text            -- content-addressed
  created_at         timestamptz
  unique(sha256, size_bytes)
```

### 5.4 审批与事件

```text
approvals
  approval_id        uuid pk
  task_id            uuid
  command_id         uuid null
  action             text
  risk               text            -- LOW | MEDIUM | HIGH | CRITICAL
  requested_by       text
  decided_by         text null
  decision           text            -- PENDING | APPROVED | DENIED | EXPIRED
  reason             text
  expires_at         timestamptz
  created_at         timestamptz

events
  event_id           bigserial pk
  type               text
  aggregate_id       uuid
  payload            jsonb
  created_at         timestamptz
  published_at       timestamptz null
```

### 5.5 任务状态

修复 `Task.status` 永不流转：

```text
DRAFT → PLANNED → RUNNING → COMPLETED
                         → FAILED
                         → STOPPED
```

规则：

- Supervisor 创建并启动 → `RUNNING`
- Supervisor `COMPLETED` → `COMPLETED`
- `FAILED` / `STOPPED` → 对应状态
- 业务 PASS/FAIL 仍由 Gate/Verdict 决定，**不混用执行状态**

## 6. 工具与命令协议

### 6.1 工具 manifest

```yaml
name: serial.reboot
version: 1.2.0
description: 打开串口，发送 reboot，抓取启动日志
schema:
  type: object
  required: [port, baud, command]
  properties:
    port: { type: string }
    baud: { type: integer, minimum: 1200, maximum: 4000000 }
    command: { type: string, maxLength: 128 }
    capture_ms: { type: integer, minimum: 0, maximum: 60000 }
permissions:
  - serial:write
timeout_ms: 60000
idempotent: false
risk: HIGH
approval: required
output_schema:
  type: object
  properties:
    boot_log: { type: string }
    matched: { type: boolean }
os: [windows]
```

### 6.2 命令信封

```json
{
  "command_id": "…",
  "task_id": "…",
  "tool": "serial.reboot",
  "version": "1.2.0",
  "args": { "port": "COM3", "baud": 921600, "command": "reboot" },
  "timeout_ms": 60000,
  "idempotency_key": "…",
  "approval_id": "…",
  "deadline": "2026-10-31T14:30:00Z"
}
```

### 6.3 结果信封

```json
{
  "command_id": "…",
  "status": "SUCCEEDED",
  "exit_code": 0,
  "result": { "matched": true, "boot_marker": "VENUSA BOOT" },
  "artifacts": [
    { "name": "serial.log", "sha256": "…", "media_type": "text/plain" }
  ],
  "started_at": "…",
  "finished_at": "…"
}
```

### 6.4 重试语义

- `idempotent: true`：lease 过期可自动重试。
- `idempotent: false`（reboot/flash/delete）：超时后进入 `UNKNOWN`，**不自动重试**，需人工对账。
- 所有命令必须带 `idempotency_key`；节点侧做去重表。

## 7. 关键流程

### 7.1 类型化工具（默认路径）

```text
UI 创建任务（节点/设备）
  → Task + Revision + execution_context
  → Supervisor 启动 OpenCode 会话
  → LLM 选择 serial.reboot
  → Policy：节点在线？工具允许？风险？需审批？
  → 写入 node_commands（QUEUED）
  → Node Agent 领取（LEASE 60s）
  → Local Tool Server 校验 args，执行
  → 结果 + artifact 上传
  → command_results / artifacts / audit
  → Task = COMPLETED，event 推送 UI
```

### 7.2 审批路径

```text
LLM 请求高风险工具
  → Policy 创建 approval（PENDING）
  → UI/通知给审批人
  → 批准：command 入队；拒绝：command = DENIED
  → 审批记录不可改
```

### 7.3 调试沙箱（兜底）

```text
LLM 请求 debug.run(script)
  → 仅 DEBUG 任务 + 人工审批
  → 节点创建一次性沙箱（低权限用户/容器）
  → 只挂载 workspace，默认禁网
  → 限时/限 CPU/内存/磁盘
  → 上传完整 transcript + artifacts
  → 销毁沙箱
  → 成功脚本可晋升为工具
```

## 8. 安全模型

| 边界 | 措施 |
|---|---|
| 控制面 ↔ 节点 | TLS + per-node token；可选 mTLS |
| 命令重放 | `command_id` + `idempotency_key` + deadline |
| 工具供应链 | manifest 固定版本 + bundle SHA256 + Ed25519 签名 |
| 参数注入 | JSON Schema 严格校验；禁止 shell 拼接 |
| 提示词注入 | 串口日志/网页/文件视为不可信；不进入策略决策 |
| 沙箱逃逸 | 低权限账户 / Job Object / 容器 / VM；FS + 网络隔离 |
| 密钥 | 不进沙箱、不进日志；执行时注入，输出脱敏 |
| 不可逆动作 | 人工审批；超时进入 UNKNOWN，不自动重试 |
| 审计 | 追加式哈希链；命令、审批、产物、访问全记录 |

## 9. 部署拓扑

```text
                 ┌──────────────┐
   Browser ─────▶│ Caddy/Nginx  │ :443
                 └──────┬───────┘
                        │ /api
                 ┌──────▼───────┐
                 │ Control Plane│ FastAPI
                 └──┬───┬───┬───┘
                    │   │   │
              ┌─────▼┐ ┌▼──┐ ┌▼────────┐
              │ PG   │ │MinIO│ │ Worker  │
              └──────┘ └────┘ └─────────┘

节点（Windows/Linux）
  NoahsArkNode 服务 ── 出站 443 ──▶ Control Plane
  本地 tools/ + 可选 sandbox
```

- 控制面：Docker Compose（api、worker、postgres、minio、caddy）。
- 节点：Windows 服务，专用服务账户；只出站，不监听入站。
- 首期 artifact 可用本地内容寻址目录；生产切 MinIO/S3。

## 10. 分阶段实施

### P0：地基（2–3 天）

| 任务 | 产出 |
|---|---|
| 修 Task 状态流转 | `services/supervision.py` + 回归测试 |
| 命令 lease/TTL/幂等 | `node_commands` 迁移 + 领取逻辑 |
| Artifact 表与上传 | `artifacts` + `POST /node/v1/artifacts` |
| 任务执行摘要 API | `GET /tasks/{id}/commands`、`/artifacts` |
| 报告/知识接真实 API | `reports.js`、`knowledge.js` 去 fixture |

**验收**：任务从创建到完成，状态正确；节点离线后命令可回收；串口日志能从节点上传并在 UI 下载。

### P1：工具化（3–5 天）

| 任务 | 产出 |
|---|---|
| Tool Registry | `tools` / `node_tools` + manifest 校验 |
| `serial.*` 工具 | list/open/write/read/expect/close/reboot |
| 节点工具同步 | `GET /node/v1/tools` + 本地加载 |
| 命令 UI | 节点命令历史、状态、产物 |
| 任务资源面板 | 显示节点/设备/工具调用 |

**验收**：`serial.reboot` 一条命令完成 CSK 重启并上传日志；无自由 PowerShell。

### P2：沙箱与更新（3–5 天）

| 任务 | 产出 |
|---|---|
| `debug.run` | 沙箱执行 + 审批 + transcript |
| Agent 自更新 | 签名 bundle、灰度、回滚 |
| 审批 UI | 待审批列表、批准/拒绝 |
| SSE/通知 | 任务/命令状态实时推送 |

**验收**：未审批的高风险命令不能执行；沙箱无法访问白名单外路径/网络。

### P3：生产化（2–3 天）

| 任务 | 产出 |
|---|---|
| mTLS/密钥管理 | 节点证书、密钥轮换 |
| 可观测性 | 指标、结构化日志、trace_id |
| 备份/恢复 | PG + artifact 备份演练 |
| 性能基线 | 并发命令、吞吐、延迟 |

## 11. 总体验收标准

1. 创建任务选择 WIN009 + `usb-listenai`，Supervisor 调 `serial.reboot`。
2. 命令完成，串口日志作为 artifact 上传，UI 可下载。
3. Task 状态从 `RUNNING` → `COMPLETED`，不是 `DRAFT`。
4. 节点中途断电：lease 过期，命令进入可对账状态，不重复 reboot。
5. 未授权工具/未审批高风险动作被拒绝。
6. 报告页和知识库读真实 API，不再是 fixture。
7. 所有命令、审批、产物有审计记录。

## 12. 待决策

1. Windows 沙箱：Job Object + 受限令牌，还是容器/轻量 VM？
2. Artifact 存储：首期本地内容寻址目录，还是直接上 MinIO？
3. 节点服务账户：SYSTEM（串口兼容性好）还是专用低权限账户？
4. 工具传输：先做进程内 registry，还是直接 MCP server？
5. 是否在 4 导航外增加“工具/命令”页面，还是并入节点详情？

## 13. 一句话

> 控制面做大脑，节点做手，工具做标准动作，沙箱做未知探索；大脑可以不确定，手必须确定、可审计、可回滚。
