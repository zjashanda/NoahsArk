# NoahsArk AI 自动化测试平台方案评审

## 总体结论

当前 `noahsark` 已经不是一个空白构想，而是已有较完整的 v2 方案基线。现有方案已经覆盖：

- 双平面架构：智能平面 + 确定性执行平面
- OpenCode + OMO 主 agent / 子 agent 调度
- 任务、节点、设备、模型、知识库、推送、接管和 UI 模块
- 项目知识库与 `lstest` 工具知识库
- C1-C7 完成门禁
- 真实设备、真实串口、真实声卡、真实脚本执行
- 节点租约、执行回执、证据哈希、知识回写
- OpenSpec、Agent Registry、Toolchain Lock
- 主动推送、SSE、终端通知和人工接管
- 版本漂移检测和升级冒烟验证
- UI 设计稿、线框、原型和多端预览

核心设计方向是正确的，不建议重新推翻。现阶段应该进入“补缺、冻结、实施”，而不是继续扩展概念。

## 一、当前方案最重要的架构判断

### 1. NoahsArk 应该拥有任务事实，OpenCode/OMO 只负责执行智能工作

不能让 OpenCode、OMO、UI 各自拥有一套任务状态。

建议固定为：

```text
NoahsArk 平台
  ├─ 拥有任务 ID、任务状态、节点租约、执行记录、证据、终态
  ├─ 拥有审批、完成门禁、知识入库和审计
  └─ 调用 OpenCode + OMO 执行 Agent 工作

OpenCode
  └─ 负责 CLI 会话和模型交互

OMO
  └─ 负责主 agent 调度子 agent、后台运行和工具协调

lstest
  └─ 负责测试框架、profile、真实脚本和结果产物

Node Agent
  └─ 负责真实设备、串口、声卡、电源和本机执行
```

平台必须保存自己的 `task_id`，并将以下 ID 做映射：

```text
task_id
  ├─ lead_session_id
  ├─ opencode_session_id
  ├─ omo_background_task_id
  ├─ subtask_id
  ├─ execution_id
  ├─ node_id
  ├─ device_lease_id
  └─ artifact/evidence IDs
```

原生 OpenCode session ID 和 OMO 后台任务 ID 只能作为外部关联 ID，不能作为平台主键。

## 二、必须补齐的关键缺口

### 1. OpenCode/OMO 会话桥

当前方案写了会话持久化和历史回放，但还需要明确一个独立模块：

```text
M13 Orchestrator Adapter / Session Bridge
```

职责：

- 启动后台 OpenCode CLI
- 注入任务上下文
- 绑定平台 `task_id`
- 记录 OpenCode session ID
- 记录 OMO background task ID
- 接收或轮询会话事件
- 统一转成平台事件
- 任务重启后恢复、标记中断或孤儿会话
- 支持历史会话回放
- 支持人工接管和继续执行
- 兼容 OpenCode/OMO 版本变化

这个模块不能拥有任务终态、设备租约和完成门禁，只负责适配和事件转译。

### 2. 真实节点执行适配器

当前 81 个 OpenSpec 任务中，真实执行部分仍需要单独落地：

```text
M2 Execution & Devices
  ├─ Node Agent
  ├─ Device Registry
  ├─ Device Lease
  ├─ Real Runner Adapter
  ├─ Receipt Signer
  └─ Artifact Collector
```

没有 Node Agent 和执行适配器，平台只能“让 Agent 说它执行了”，无法证明真实设备确实被操作。

节点至少需要提供：

- 节点唯一 ID
- 操作系统和版本
- Agent 版本
- OpenCode/OMO/lstest 版本
- 稳定设备指纹
- 串口设备列表
- 声卡端点列表
- 电源控制接口
- 网络和权限能力
- 节点公钥
- 心跳和在线状态

不能只保存 `COM3`、`COM5` 这种易变编号，应该保存 USB VID/PID、设备序列号、物理路径、节点 ID、端点类型、项目绑定和设备角色。

### 3. 明确的非阻塞 dispatch 协议

```text
Lead Agent
  ├─ dispatch subtask
  ├─ 立即拿到 dispatch_id
  ├─ 继续处理其他任务
  └─ 通过事件或查询获取结果

Platform
  ├─ subtask_id
  ├─ dispatch_id
  ├─ attempt_id
  ├─ native_session_id
  ├─ omo_task_id
  ├─ timeout
  ├─ retry budget
  └─ completion event
```

必须明确：dispatch 立即返回；子任务独立执行；子任务失败不直接阻塞主 agent；主 agent 可以继续调度不依赖该结果的任务；超时标记为 `timeout`；重试产生新的 attempt；重启后未确认完成的任务标记为 `orphaned`；达到预算后进入 `BLOCKED_HUMAN`。

## 三、任务状态建议

不要同时维护两套状态。建议采用“任务阶段 phase + 任务终态 verdict”。

阶段：

```text
intake
retrieving
planning
awaiting_approval
approved
preflight
ready
running
repairing
verifying
completion_pending
archiving
```

终态：

```text
PASS
FAIL
BLOCKED_HUMAN
CANCELLED
STOPPED
INFRA_ERROR
```

特别注意：`WAITING_HUMAN` 不是终态；不允许使用含义模糊的 `DONE`；preflight 成功不等于任务成功；runner 返回 0 不等于测试 PASS；Agent 自报完成不等于平台可以结束任务；只有完成门禁通过后才能写终态。

## 四、任务完成判定

### C1：方案有效

必须有需求拆解、用例、oracle、需求追溯、样本量和统计口径、已批准的不可变方案版本及方案质量评审记录。

### C2：真实执行

必须有 `run_mode=real`、`purpose=formal`、真实节点、有效设备租约、节点签名回执、串口/声卡/电源端点身份、实际 runner 命令和实际开始/结束时间。

`dry_run`、`mock`、`simulated`、`recorded`、`replay`、Agent 自报、手工填写 CSV、复制其他任务日志均不能作为正式完成证据。

### C3：产物完整

校验产物存在、文件哈希、时间窗口、录音和日志非空、CSV 行数与样本数、跨任务复制、截断、篡改及额外文件。

### C4：独立判定

不能只相信 runner 的 `PASS`，需要独立重算、独立检查日志、独立检查样本数和分母、独立检查 oracle。runner 与独立结果不一致时必须阻塞。

### C5：证据充分

每个用例必须有对应证据。例如唤醒需要串口、时间戳和音频；识别需要识别文本、响应日志和时间；播报需要音频输出和播报完成事件；超时需要开始时间、超时边界和设备状态。

### C6：知识回写

任务应产生项目 playbook、失败案例、根因分类、可复用脚本经验、设备特性、适用范围、不适用范围和人工确认要求。没有可复用知识时，也必须写入 `no_reusable_knowledge` 及理由。

### C7：可复现

记录 OpenCode、OMO、插件、Agent 配置、模型绑定、lstest、项目代码、节点环境、固件、设备指纹、方案/用例/oracle 哈希和结果产物哈希。

## 五、项目知识库与工具知识库

### 项目知识库

回答“这个项目应该怎么测”，建议分类：

```text
methodology
project_fact
metric_definition
vocabulary
scenario
device_behavior
playbook
failure_case
root_cause
requirement_mapping
historical_result
```

必须区分 `global`、`project`、`device`、`firmware`、`task`。项目特定数值不能未经证据泛化为全平台规则。

### 工具知识库 lstest

回答“用什么工具、如何构建和执行”，建议分类：

```text
tool_contract
profile_contract
validation_profile
device_tool
audio_tool
serial_tool
engineering_rule
script_fix
runner_failure
tool_version
compatibility_rule
```

不应把所有历史脚本直接复制进工具库，而应保留工具入口、输入、输出、副作用、风险、版本、来源、适用项目、已知失败方式、修复记录和正式执行资格。

知识生命周期：

```text
candidate -> corroborated -> approved -> stale | retracted
```

模型和 Agent 只能写入 `candidate`。`approved` 必须有来源、证据、适用边界、版本、审核人、审核时间和反例/冲突记录。圆桌只能产生建议，不能直接批准知识。

## 六、072300ai聊天室的正确定位

不建议复制成独立 Web 平台，建议改造成主 agent 可调用的 `discussion / roundtable tool`。

输入包含任务、主题、角色、上下文引用、轮次和预算；输出包含共识、分歧、风险、行动项、引用和开放问题。

硬约束：圆桌不能直接宣布 PASS，不能直接写任务终态，不能直接批准知识，不能替代真实执行；结果必须带角色、模型、版本和上下文引用；角色之间必须允许不同意见；最终输出必须明确共识和分歧。

适用场景：测试方案评审、用例覆盖评审、oracle 独立性检查、根因分析、设备异常讨论、脚本修复方案比较和人工接管判断。

## 七、OpenSpec 和 Agent 配置如何配合

每个 Agent 配置至少包含：

```yaml
agent_id:
role:
purpose:
model_policy:
allowed_tools:
denied_tools:
write_scope:
read_scope:
openspec_context:
review_required:
can_execute_real_device:
can_change_plan:
can_write_knowledge:
can_write_terminal_state:
max_concurrency:
timeout:
retry_budget:
```

OpenSpec 负责需求变更、方案/规格、任务拆解、审核追溯和文件生成约束；不能替代节点执行器、设备租约、证据校验、任务状态机和完成门禁。

典型权限：lead/planner/case-writer 只能提交候选；script-implementer 只能写限定目录；device-executor 可执行设备但不能写终态；reviewer 只读；knowledge-curator 只能提交候选；平台终态只能通过命令门面写入。

## 八、主动上报与接手入口

事件总线应产生：

```text
task.created
task.phase_changed
task.blocked
task.progress
subtask.started
subtask.completed
subtask.failed
repair.started
repair.completed
device.lease_acquired
device.lease_lost
execution.started
execution.finished
gate.failed
task.completed
toolchain.drift
model.changed
takeover.requested
```

推送渠道：Web UI SSE、终端 `task watch`、文件/JSONL、Webhook，以及后续企业消息。

任务窗口是“任务控制台 + 会话投影”，应显示 lead agent 历史消息、子 agent 状态、工具调用摘要、执行命令和结果、设备租约、阻塞原因，并支持追加信息、暂停、恢复、停止、批准、接管和重新验证。不要暴露模型私有思维链，只显示执行摘要、工具调用、结果、引用、风险、下一步和阻塞问题。

## 九、版本治理

维护：

```text
toolchain.lock.json
compatibility-matrix.json
agent-config-lock.json
```

锁定 OpenCode、OMO、插件、Agent 配置、skill、Python、SQLite、lstest、Node Agent 和平台版本。升级流程：

```text
新版本候选
  -> 版本锁更新
  -> T1 启动冒烟
  -> T2 插件/事件/推送/检索冒烟
  -> T3 节点和真实设备冒烟
  -> 兼容矩阵记录
  -> 人工批准
  -> 正式任务使用
```

任何未登记版本或哈希漂移都触发 `toolchain.drift`：允许查看和诊断，但禁止正式真实执行和 PASS，直到重新冒烟并获得批准。

## 十、实施顺序建议

### Wave 0：冻结决策和合同

补齐 M13 会话桥、Node Agent、dispatch/result/event 协议、session history projection、C8 边界、反假跑威胁模型、`tmpskill` 摄入范围、节点通信、模型配额、设备窗口和数据保留策略。

### Wave 1：平台事实层

实现 SQLite WAL、任务/事件/会话/节点/设备/知识库基础表、Command Facade、幂等命令、审计和事件回放。

### Wave 2：OpenCode/OMO 会话桥

验证后台启动、session ID 映射、OMO 任务映射、事件接收、重启恢复、orphan/timeout/cancel 和历史渲染。

### Wave 3：知识库和方案生成

实现项目 KB、工具 KB、FTS5/CJK 检索、引用和适用范围、OpenSpec 方案生成、用例/oracle 生成、多角色讨论、评审和审批。

### Wave 4：真实节点和执行

实现 Node Agent、设备发现、稳定端点指纹、设备租约、lstest 执行、真实回执、证据清单、独立重算和 C1-C7。

### Wave 5：主动推送和接管

实现 SSE、终端 watch、Webhook、任务窗口、接管租约、历史回放、继续执行、停止和恢复。

### Wave 6：UI

实现总览、任务、任务详情、节点设备、项目知识库、工具知识库、模型、工具链、Agent、圆桌、推送、接管终端和设置。

## 十一、必须新增的验收场景

1. dry-run 冒充 real，必须拒绝
2. 无签名回执，必须拒绝
3. 过期租约，必须拒绝
4. 错误设备指纹，必须拒绝
5. 空日志，必须拒绝
6. 跨任务复制产物，必须拒绝
7. 修改结果 CSV，必须拒绝
8. runner 返回 PASS 但独立重算 FAIL，必须阻塞
9. OMO 子 agent 超时，主 agent 不得卡死
10. OpenCode 进程崩溃，任务变为中断或孤儿
11. 模型中途切换不能改变当前执行绑定
12. 工具链版本漂移，禁止正式执行
13. 设备被其他任务占用，进入等待或人工阻塞
14. 真实设备离线，不能输出产品 FAIL
15. 圆桌意见一致但缺少证据，不能输出 PASS
16. 命中旧项目规则时必须显示适用边界
17. 修复成功后必须保留原始失败证据和修复链
18. 候选知识未经审核不能作为 approved 使用

## 十二、最终需要确认的决策

1. `框架.png` 的文字版结构或图片内容
2. 是否接受 Flask + SQLite WAL + SSE
3. UI 是否采用现有 Apple 风格方案
4. Node Agent 使用 HTTP、WebSocket、SSH 还是本地进程协议
5. OpenCode 采用每任务一个进程还是共享服务
6. OMO 使用官方版本、固定 fork 还是本机版本锁定
7. 默认模型、备用模型和切换权限
8. 首批真实设备和节点范围
9. 是否允许自动上电、断电、OTA 和网络配置
10. 日志和录音保留时间
11. 云端数据采集范围和脱敏规则
12. `tmpskill` 全量导入还是指定目录导入
13. 平台自我修改是否排除在首期
14. 插件升级是否必须人工批准
15. 首期是否使用 SQLite，是否需要 PostgreSQL
16. 是否需要多用户权限
17. `072300ai聊天室` 是否允许提取代码/逻辑作为插件
18. C8“测试之测试”是否纳入正式 PASS 门禁

## 最关键的执行建议

先冻结 M13 会话桥、Node Agent、真实执行回执和 C1-C7，再开始产品实现。如果先做 UI 或先让 Agent 自由调用设备，后续容易出现“界面看起来完整，但任务不可证明、会话不可接管、结果不可复现”的问题。

---

## 十三、Linux 中枢与 Windows 测试节点执行方案

### 13.1 结论先行

不要把 SSH 作为常规测试任务的主执行通道。推荐采用：

```text
Linux 中枢
  → Windows 常驻 Node Agent 出站回连
  → 平台下发 execution_contract
  → Windows 节点本地运行 lstest 和项目 runner
  → 节点回传进度、日志摘要、产物清单和签名回执
  → Linux 中枢统一 verify、archive 和知识回写
```

SSH 只用于三类场景：

1. 部署或升级 Windows Node Agent。
2. 只读诊断、抓取节点状态和人工排障。
3. Agent 或平台通道不可用时的受控人工接管。

SSH 不应承担常规任务执行、长时间任务保持、设备租约、日志回传或完成判定。

### 13.2 推荐拓扑

```text
┌──────────────────────── Linux 中枢 ────────────────────────┐
│ 编排、任务状态、模型、知识库、门禁、审计、事件和 UI        │
│ SQLite: task / execution / lease / event / evidence / kb   │
└──────────────────────────┬────────────────────────────────┘
                           │ WSS 或受保护 WebSocket
             Windows 节点主动出站回连，不要求 Linux 反向进入
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ win009 Agent │  │ win010 Agent │  │ vm1003 Agent │
   │ 心跳/能力上报 │  │ 任务领取     │  │ 设备发现     │
   │ 进程管理     │  │ 日志流       │  │ 产物补传     │
   └──────┬───────┘  └──────────────┘  └──────────────┘
          │
          ▼
   串口、声卡、电源控制器、被测设备和本地 lstest
```

Linux 是全局状态唯一持有者。Windows 节点只负责本机能力、设备和执行，不持有全局工作流状态，也不自行改变任务终态。

### 13.3 三层职责

#### Linux 中枢

- 创建和推进任务。
- 检索项目知识库和 lstest 工具知识库。
- 生成并审核方案、用例、profile 和 oracle。
- 选择节点与设备。
- 创建和维护设备租约。
- 下发执行契约。
- 接收节点事件和产物索引。
- 执行独立 verify 和完成门禁。
- 统一归档、推送和知识回写。

#### Windows Node Agent

- 启动时向 Linux 注册节点、版本、能力和设备信息。
- 保持心跳和出站连接。
- 接收平台签发的执行契约。
- 校验任务、租约、runner 和 manifest 哈希。
- 在隔离工作目录中运行确定性脚本。
- 管理进程树、超时和停止。
- 实时回传进度、stdout/stderr 摘要和状态。
- 本地保存原始产物，断线后补传。
- 生成节点签名执行回执。

#### 设备

- 只通过 Windows 节点被访问。
- 串口、声卡、电源和网络资源都必须有稳定设备身份。
- 不能仅使用易变化的 `COM3`、`COM5` 作为设备主键。

### 13.4 execution_contract 执行契约

平台不是临时发送一条 shell 命令，而是下发一个可校验、可审计、可幂等的执行契约：

```json
{
  "schema": "aitest.execution_contract.v1",
  "task_id": "ait-...",
  "execution_id": "exec-...",
  "attempt": 1,
  "lease_id": "lease-...",
  "node_id": "win009-tcl-10-11-63-24",
  "devices": [
    {
      "role": "DUT",
      "device_id": "TCL000",
      "endpoints": {
        "serial": "usb:vid=...;pid=...;serial=..."
      }
    },
    {
      "role": "SPK",
      "endpoint": "usb:vid=...;serial=..."
    }
  ],
  "pack": {
    "material_id": "pm-...",
    "manifest_sha256": "...",
    "runner": "scripts/aitest_platform_runner.py",
    "runner_sha256": "...",
    "lstest_pin": "..."
  },
  "command": [
    "python",
    "scripts\\aitest_platform_runner.py",
    "--profile",
    "tcl-csk7/r2"
  ],
  "workspace": "C:\\aitest\\workspace\\tasks\\exec-...",
  "timeout_s": 7200,
  "expected_artifacts": [
    "serial_logs/",
    "tool.log",
    "results.csv",
    "cases.csv",
    "evidence/"
  ],
  "result_contract": "orion.workflow.result.v1"
}
```

契约规则：

- `execution_id + attempt` 是幂等键，重复下发不能重复执行。
- 节点必须校验 `material_id`、`manifest_sha256` 和 `runner_sha256`。
- 契约中的脚本版本不匹配时直接拒绝执行，不能“先跑再说”。
- 节点只能使用平台签发的 `lease_id` 访问指定设备。
- runner 不能自行声明任务完成或写入平台终态。
- 平台必须重新计算最终结论。

### 13.5 脚本和代码如何分发

不建议每次通过 SSH 临时 `scp` 一份脚本到 Windows 后直接执行。推荐：

```text
项目代码 / profile / runner
  → 固定 revision 或 material_id
  → 生成 manifest 和 SHA-256
  → 节点领取或接收任务包
  → 节点校验哈希
  → 创建独立 task workspace
  → 执行
  → 产物按 execution_id 保存
```

节点工作目录示例：

```text
C:\aitest\workspace\tasks\<execution_id>\
  contract.json
  manifest.json
  runner\
  serial_logs\
  audio\
  results.csv
  cases.csv
  tool.log
  evidence\
  receipt.json
```

任务结束后不覆盖原目录、不复用旧结果、不混用不同任务的日志。

### 13.6 SSH 与 Node Agent 的分工

| 场景 | 推荐通道 | 原因 |
|---|---|---|
| 常规测试执行 | Node Agent + execution contract | 需要租约、状态、日志、产物和审计 |
| 数小时长任务 | Node Agent + watchdog | 支持断线、重连和恢复 |
| Agent 部署升级 | SSH 或安装包 | 一次性运维操作 |
| 读取诊断信息 | SSH 只读或 Agent RPC | 避免改变测试状态 |
| 人工现场调试 | Relay PTY + Agent | 接入同一任务上下文和回放缓冲 |
| 设备占用探测 | Node Agent RPC | 必须取得节点实时状态 |

### 13.7 Windows 节点的强制约束

#### 交互式用户会话

音频播放和录音不能默认放在 Windows Service 的 Session 0 中。否则可能出现脚本退出码为 0，但实际没有声音或没有录音的假成功。

Node Agent 应运行在交互式登录用户会话中，推荐使用 Windows 计划任务的“仅当用户登录时运行”模式，并在节点能力上报中记录：

- 当前用户会话 ID。
- 音频端点是否可见。
- 播放和录音自检结果。
- 当前桌面会话是否可交互。

#### 进程树管理

PowerShell 启动的子进程可能不会随父进程退出。Node Agent 必须使用 Windows Job Object 或等效进程树管理能力，保证停止和超时可以收口所有子进程。

#### 串口和音频独占

执行前必须检查串口、声卡和电源控制资源；执行后必须释放并再次对账。资源残留应归类为环境或基础设施问题，不能直接归类为产品 FAIL。

#### 编码和路径

统一 UTF-8、固定工作目录、使用绝对路径，处理空格路径、PowerShell 执行策略和 UAC。仓库统一 LF，节点运行时显式设置 `PYTHONIOENCODING=utf-8`。

### 13.8 断线和长任务恢复

```text
节点执行中
  └─连接断开
      ├─平台 execution = disconnected
      ├─节点继续本地执行并落盘
      ├─节点重连上报 execution_id 和本地状态
      ├─平台按 execution_id 对账
      │   ├─仍运行：恢复 watch
      │   ├─已完成：校验产物后进入 verify
      │   └─已停止：进入 interrupted / BLOCKED_HUMAN
      └─不能把未知状态当作成功
```

产物策略：

- `tool.log`、`results.csv`、`cases.csv`：直传并校验 SHA-256。
- 串口日志：分块回传，记录块序号和总长度。
- 录音等大文件：节点保留原始文件，平台保存对象指针、大小、哈希和必要摘要。
- `evidence/`：保存清单、逐文件哈希和执行窗口。

### 13.9 真实执行门禁

以下字段必须同时存在，才允许进入正式 verify：

```text
execution_id
lease_id
node_id
稳定端点指纹
实际 runner 命令
真实开始/结束时间
非空产物清单
节点签名回执
```

缺少任一项只能是 `BLOCKED`、`INFRA_ERROR` 或 `INTERRUPTED`，不能写成 `PASS`。

### 13.10 与当前已有方案的关系

当前 `0000/plan.md` 已经明确：

- Linux 是服务器和状态中枢。
- Windows 机器是纯 Agent 测试节点。
- 节点侧只装 lstest、音频/串口工具和 Agent。
- 测试通过 execution contract 下发。
- 设备租约由平台统一管理。
- 真实产物留在节点任务目录并回传摘要与指针。
- 节点断线后标记 `interrupted`，支持 `resume --last`。

因此，本节不是另起一套执行架构，而是将现有星型拓扑补充为正式的执行通道决策：

> **Node Agent 是流水线主通道，SSH 是运维扳手，不是测试执行器。**
