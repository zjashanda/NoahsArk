# NoahsArk Tool Execution Protocol (NTEP) v1

状态：草案（开发基线）
适用范围：所有需要在节点上执行的脚本/工具，包括 usb.scan、lstest、串口探测、音频检测、日志采集、诊断脚本等。

## 1. 角色与边界

- **Control Plane**：构建、校验、排队、审计命令，不在节点上直接执行。
- **Node Agent**：唯一节点侧执行入口，出站长轮询，按白名单执行工具，回传结果。
- **Local Tool**：版本化脚本/可执行文件，放在 Agent 管理的工具目录，不接受任意路径。

平台不向节点开放任意 shell，也不直接连接设备。

## 2. Tool Descriptor

每个工具必须注册一份描述：

```json
{
  "tool_id": "usb.scan",
  "version": 1,
  "os": ["windows", "linux"],
  "description": "扫描 USB 板卡、串口和音频端点",
  "entry": "usbTree-cli.cmd",
  "argv": ["--all", "--format", "csv"],
  "cwd": "tools/usb-tree",
  "input_schema": {},
  "output_schema": { "type": "csv" },
  "timeout_seconds": 30,
  "max_output_bytes": 1000000,
  "side_effect": "read_only",
  "required_capabilities": [],
  "checksum": "sha256:..."
}
```

规则：

- `tool_id` + `version` 唯一。
- `entry` 必须是工具目录内的相对路径。
- `argv` 固定；用户只能提供 `input_schema` 允许的参数。
- `side_effect` 为 `read_only` / `mutating`；mutating 工具必须支持幂等键。
- 工具包带校验和/签名；Agent 只加载校验通过的工具。

## 3. 命令信封

```json
{
  "command_id": "cmd-<uuid>",
  "node_id": "<uuid>",
  "tool_id": "usb.scan",
  "tool_version": 1,
  "args": {},
  "timeout_seconds": 30,
  "requested_by": "admin-01",
  "trace_id": "<uuid>",
  "idempotency_key": "<uuid>",
  "created_at": "2026-10-31T00:00:00Z"
}
```

平台只接受 `tool_id + version + args`，不接受命令字符串。

## 4. 生命周期

```text
QUEUED -> CLAIMED -> RUNNING -> SUCCEEDED
                           -> FAILED
                           -> TIMEOUT
                           -> CANCELLED
```

- 平台写入 `QUEUED` 并审计。
- Agent 长轮询领取，平台原子标记 `CLAIMED` 并记录 attempt/lease。
- Agent 开始执行时回传 `RUNNING`（可选）。
- 结果只能落一次；重复结果按 `command_id` 去重。
- 节点离线/超时由平台标记 `FAILED` 或 `TIMEOUT`。

## 5. 传输

- Agent -> 平台：`POST /node/v1/poll`（Bearer per-node token）。
- 平台 -> Agent：poll 响应中的 `messages[]`，`kind = "command"`。
- Agent -> 平台：`POST /node/v1/command-results`。
- 平台查询：`GET /api/v1/nodes/{node_id}/commands/{command_id}`。
- 所有请求带 `command_id` / `trace_id`，便于审计与排障。

## 6. 执行规则

Agent 执行工具时：

1. 按 `tool_id + version` 查本地注册表；未知工具拒绝。
2. 校验 `args` 符合 `input_schema`。
3. 解析工具目录，拒绝目录穿越。
4. 使用固定 argv、固定 cwd、白名单环境变量。
5. 禁止 `shell=True` / 字符串拼接命令。
6. 超时杀进程树。
7. stdout/stderr 按 `max_output_bytes` 截断。
8. 结果写入本地 spool，断线可重放。

## 7. 结果

```json
{
  "command_id": "cmd-...",
  "node_id": "...",
  "status": "SUCCEEDED",
  "exit_code": 0,
  "stdout": "...",
  "stderr": "",
  "truncated": false,
  "duration_ms": 1234,
  "error_code": null,
  "started_at": "...",
  "finished_at": "..."
}
```

- stdout/stderr 必须脱敏、限长。
- `SUCCEEDED` 仅表示进程成功，不代表业务判定。
- 业务判定仍由控制面/证据链完成。

## 8. 安全

- per-node Bearer token；不共享平台 token。
- 只有 ADMIN 能创建命令。
- 平台与 Agent 双重白名单。
- 工具包校验和/签名；工具目录只读（尽量）。
- 最小权限运行（Windows 服务账号 / Linux 专用用户）。
- 不记录 token、密码、私钥；输出中的秘密必须脱敏。
- 所有命令写审计：谁、何时、哪个节点、哪个工具、参数摘要、结果状态。

## 9. 版本与兼容

- 协议版本 `protocol_version`；Agent 心跳上报支持的 `tools[]`（含版本）。
- 平台只下发 Agent 声明支持的工具/版本。
- 不支持时返回 `409 TOOL_VERSION_UNSUPPORTED`。
- 工具升级采用新 version，不覆盖旧版本；回滚时切回旧 version。

## 10. 错误码

```text
UNKNOWN_TOOL
TOOL_UNAVAILABLE
TOOL_VERSION_UNSUPPORTED
INVALID_ARGS
NODE_OFFLINE
TIMEOUT
OUTPUT_LIMIT
EXEC_FAILED
COMMAND_CANCELLED
DUPLICATE_COMMAND
```

## 11. 重试与幂等

- `command_id` 全局唯一；同一 id 返回同一结果。
- `read_only` 工具可安全重试。
- `mutating` 工具必须带 `idempotency_key`，由工具自身保证幂等。
- 传输失败可重试；执行超时不自动重复，交由平台决策。
- 最大 attempt 由工具描述配置。

## 12. 脚本作者规范

- 无交互、无 TTY 依赖。
- 退出码语义明确：0 成功，非 0 失败。
- 输出优先 JSON/CSV 等机器可读格式；人类可读文本可作为附加字段。
- 运行时间与输出有上限。
- 不在 stdout/stderr 输出秘密。
- 工具版本化，变更不兼容时提升 version。
- 只读工具不得修改系统状态；写操作必须声明 `side_effect=mutating`。

## 13. 第一批工具

| tool_id | version | 说明 | 输出 |
| --- | --- | --- | --- |
| `usb.scan` | 1 | usbTree-cli 扫描 USB 板卡/串口/音频 | CSV |

后续：`lstest.run`、`serial.probe`、`audio.list`、`log.tail`、`agent.diagnose` 等全部按本协议注册。

## 14. Agent 与工具更新通知

平台发布新 Agent 或工具包后，不通过 SSH 人工升级，而是由平台通知 Agent：

- Agent 心跳上报 `agent_version`、`tools[]`（含版本）。
- 平台在心跳响应中返回可选更新描述：

```json
{
  "ok": true,
  "update": {
    "kind": "agent",
    "version": "0.2.0",
    "url": "http://<platform>/install/noahsark-node-agent.tgz",
    "sha256": "..."
  }
}
```

- `kind` 可为 `agent` 或 `tool`；工具更新可带 `tool_id`。
- Agent 仅在空闲时更新，不打断正在执行的任务。
- 流程：下载到 staging -> 校验 sha256/签名 -> 原子替换 -> 重启服务/工具 -> 回执结果。
- 失败自动回滚到上一版本，并上报 `AGENT_UPDATE_FAILED`。
- 平台记录版本、更新时间、结果，并审计。
- 更新命令是 mutating：必须幂等、可回滚、不可并发执行。
