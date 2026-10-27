# NoahsArk Agent 逻辑固化边界

> 版本：1027V1
> 目标：明确哪些逻辑必须固化到平台/确定性 Agent，哪些逻辑只能由 LLM Agent 提议。

## 1. 结论

不能把整个测试流程交给一个 LLM Agent。正确边界是：

```text
LLM Agent
  负责理解、检索、设计、解释、诊断假设和生成候选工件

NoahsArk Platform / Deterministic Plane
  负责状态、权限、租约、门禁、幂等、超时、证据、终态和审计

Windows Execution Agent
  负责节点本地设备、脚本、lstest、进程树、证据采集和签名回执
```

规则：**Agent 可以提出，平台才可以决定；节点可以执行，平台才可以判定。**

## 2. 必须固化到平台/确定性 Agent

| 逻辑 | 固化位置 | 原因 |
|---|---|---|
| task_id、phase、verdict | M1 Workflow | 不能被模型自由改写 |
| phase 转移矩阵 | M1 + M0 Command Facade | 防止跳过批准/预检/验证 |
| C1–C7 门禁 | M7 Completion Gate | 证据和终态必须可重算 |
| `run_mode` / `purpose` | M2 + M7 | 防止 preflight/dry-run 冒充正式执行 |
| 节点/设备租约 | M2 Lease Service | 防止双任务操作同一设备 |
| lease epoch CAS | M2/M8 | 防止双控制和陈旧接管 |
| execution_contract.v1 | M0/M2 | 防止旧脚本、旧 runner、跨任务产物 |
| idempotency_key | M0 所有命令 | 防止重试产生重复副作用 |
| dispatch_id/attempt_id | M13 | 防止子 Agent 超时后状态不明 |
| timeout/retry budget | M0/M13/M2 | 重试必须有限、可审计 |
| 进程树停止 | Windows Node Agent | 不能依赖模型记得杀进程 |
| manifest/hash/signature | M2/M7 | 防止产物篡改和伪造回执 |
| CSV 行数/分母/时间窗口 | M7 | 防止空日志、复制结果、截断结果 |
| model binding | M3 | 执行中绑定不可漂移 |
| 工具链漂移阻断 | M9 | 未验证版本不得真实执行 |
| 事件 seq/idempotency | M4 | 事件可重放、消费端可去重 |
| `task.completed` exactly once | M4/M7 | 完成通知不能重复或提前 |
| 知识生命周期 | M5 | candidate 不能自动变 approved |
| secret/PII 扫描 | M5/M10 | 不把敏感数据写进知识/日志 |
| 受保护路径写入 | M10/M0 | 必须有评审回执 |

## 3. 只能由 LLM Agent 提议

| 候选逻辑 | LLM 可以做什么 | 平台如何接管 |
|---|---|---|
| 需求理解 | 提取功能点、风险、未知项 | 结构化 intake；缺字段进入 `NEEDS_HUMAN` |
| 测试策略 | 建议样本量、场景、优先级 | M6 校验风险、项目边界和配置值 |
| 相似任务复用 | 解释命中理由、推荐 reusable block | M5 提供引用/警告；不能复制结论 |
| 用例生成 | 生成动作、期望、禁止项、证据窗口 | schema、追溯、profile 编译、oracle 检查 |
| oracle 生成 | 提议日志序列、阈值、时间窗 | M6 检查可证伪性和证据绑定 |
| 根因分析 | 提议测试逻辑/环境/设备/固件/需求分类 | 证据树校验；最终 FAIL 需满足 13/14 类规则 |
| 脚本修复 | 提议 diff、修复理由和风险 | 评审后写 candidate；不能自动改 pin 工具 |
| 多模型讨论 | 产出共识、分歧、风险、行动项 | 候选意见，不能批准终态/知识 |

## 4. LLM Agent 明确禁止

- 直接写任务终态、门禁报告、设备租约或 approved 知识。
- 直接执行任意 shell、PowerShell、串口、电源或音频命令。
- 把模型输出的 `PASS` 当作平台结论。
- 修改 `run_mode`、`purpose`、plan hash、runner hash、manifest hash。
- 通过自然语言绕过人工批准或 C1–C7。
- 自己决定重试次数、超时、并发上限和租约释放。
- 把其他任务的日志、CSV、音频或截图复制到当前任务。
- 把模型私有思维链写入 UI、知识库或证据。

## 5. M13 Session Bridge 边界

M13 是 OpenCode/OMO 与 NoahsArk 的适配层，不是新的任务状态机。

它负责：

- `task_id ↔ lead_session_id ↔ opencode_session_id` 映射。
- `subtask_id ↔ dispatch_id ↔ omo_task_id ↔ attempt_id` 映射。
- dispatch 立即返回，主 Agent 不等待无依赖子任务。
- 子任务超时、取消、失败、孤儿、重启恢复。
- 原生会话消息/工具摘要转成 `platform_events`。
- 历史回放和人工接管入口。

它不能负责：终态、设备租约、Completion Gate、approved 知识或设备动作。

最小 dispatch 记录：

```json
{
  "dispatch_id": "dispatch-...",
  "parent_task_id": "ait-...",
  "subtask_id": "sub-...",
  "attempt_id": "attempt-1",
  "native_session_id": "opencode-session-...",
  "omo_task_id": "omo-...",
  "timeout_s": 1800,
  "retry_budget": 2,
  "status": "dispatched|running|completed|failed|timeout|orphaned"
}
```

## 6. Agent Registry 固化字段

```yaml
agent_id: planner
role: planner
purpose: generate_plan
model_policy: {requires: [json_schema]}
allowed_tools: [read, grep, glob, openspec_show]
denied_tools: [device_write, terminal_state_write, knowledge_approve]
read_scope: [".aitest/**", "knowledge/**"]
write_scope: [".aitest/local/plans/**"]
openspec_context: [test-plan-design, test-plan-assurance]
review_required: true
can_execute_real_device: false
can_change_plan: true
can_write_knowledge: candidate_only
can_write_terminal_state: false
max_concurrency: 2
retry_budget: 2
```

`script_implementer` 可以执行受控脚本，但不能写终态；`device_executor` 可以申请设备租约，但不能批准方案或写 PASS；`reviewer` 只读；`knowledge_curator` 只能写 candidate。

## 7. Windows Execution Agent 固化边界

Windows Agent 只接受受控 action：

```text
preflight
run_profile
stop
diagnostics
```

必须固化：

1. execution_contract hash 校验。
2. material/runner/profile/lstest pin 校验。
3. 节点和设备 lease 校验。
4. 工作目录隔离。
5. Windows Job Object 进程树管理。
6. 串口/声卡/电源稳定端点绑定。
7. 证据 manifest 和分块上传。
8. Ed25519 执行回执签名。
9. 断线本地落盘和重连对账。

它不能写最终 PASS/FAIL，只能返回执行事实和证据。

## 8. 业务逻辑归属

```text
需求含义、风险、测试想法
  -> LLM Agent 提议

方案、用例、oracle
  -> M6 结构化 + 保证 + 评审 + 人工批准

节点、设备、脚本、runner
  -> M2/M9 确定性检查

执行结果、证据、manifest、签名回执
  -> Windows Agent 产生，M7 校验

PASS / FAIL / BLOCKED_HUMAN
  -> M7 Completion Gate + M0 终态写入

知识候选
  -> M5 写 candidate，人工评审后 approved
```

## 9. 三种结果不能混淆

| 结果 | 产生者 | 含义 | 能否结束任务 |
|---|---|---|---|
| Agent 建议 | LLM Agent | 候选方案/判断/修复建议 | 不能 |
| Runner 结果 | Windows Agent/lstest | 本机执行事实和原始产物 | 不能单独决定 |
| Platform Verdict | M7 + M0 | 独立重算后的平台结论 | 可以，必须有 C1–C7 |

## 10. 实施顺序

1. 冻结 M0 命令门面和 C1–C7。
2. 冻结 M13 会话桥、dispatch/attempt/orphan 契约。
3. 冻结 `execution_contract.v1` 和 evidence manifest。
4. 实现 Windows Agent 和设备租约。
5. 实现 M6 方案/用例/oracle 持久化和评审。
6. 实现真实预检、正式执行、回执和独立重算。
7. 最后接 UI、推送、接管和 T3 真实验收。

如果 Agent 权限、会话桥、执行契约和完成门禁没有先冻结，后续 UI 即使能显示，也不能证明结果可信。
