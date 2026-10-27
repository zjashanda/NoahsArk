# 对 `noahsark-review-12-sections.md` 的优化建议

> 评审对象：`noahsark/gpt6sol/noahsark-review-12-sections.md`
> 对照基线：`SOLUTION.md`、`MODULE-DESIGN.md`、`REMOTE-EXECUTION.md`、`IMPLEMENTATION-PLAN.md`
> 结论：评审方向正确；**不建议推翻现有方案**，建议吸收 9 项、调整 3 项、暂缓 2 项。

---

## 0. 总体判断

这份评审最有价值的地方不是重复了 C1–C7，而是指出了两个当前方案容易“看起来完整、实际不可证明”的组织缺口：

1. **缺少 M13 Orchestrator Adapter / Session Bridge**：OpenCode/OMO 会话 ID、后台任务 ID、断线恢复、孤儿会话、非阻塞 dispatch 没有独立归属。
2. **缺少正式的 execution_contract**：当前远程执行文档有 job/payload，但没有把 material、runner、workspace、expected artifacts、attempt 作为可校验契约冻结。

这两项不补，平台容易出现：

- 平台有自己的 task_id，但 OpenCode/OMO 会话无法可靠映射；
- 子 Agent 超时后主 Agent 卡死；
- 进程崩溃后任务变成“不知道是否跑过”；
- 节点执行了旧脚本/旧 runner；
- 跨任务复制日志或 CSV 也能混过完成门禁。

---

## 1. 建议立即采纳（P0）

| # | 评审建议 | 当前方案状态 | 建议动作 |
|---|---|---|---|
| 1 | 增加 M13 Orchestrator Adapter / Session Bridge | 当前模块表没有 M13 | 增加 M13；只做适配/事件转译，不拥有终态、租约、门禁 |
| 2 | 平台拥有 task_id，OpenCode/OMO ID 只做外部关联 | `MODULE-DESIGN` 已有平台事实边界，但缺映射表 | 增加 `agent_sessions`、`dispatch_attempts`、`session_events`；禁止用 native session 当主键 |
| 3 | 非阻塞 dispatch 协议 | 当前方案没有 dispatch_id/attempt_id/orphan 语义 | 增加 `dispatch_id`、`attempt_id`、`parent_task_id`、`timeout`、`retry_budget`、`orphaned` |
| 4 | `phase + verdict` 分离 | 总体方案有阶段和终态，但缺完整阶段枚举和会话状态 | 固定 phase 枚举；`WAITING_HUMAN` 非终态；增加 `orphaned`/`interrupted` 会话状态 |
| 5 | `purpose=formal` | 当前 C2 只写 `run_mode=real` | C2 同时要求 `run_mode=real` 且 `purpose=formal`；预检只能 `purpose=preflight` |
| 6 | execution_contract 契约 | `REMOTE-EXECUTION.md` 有 job payload，未冻结 material/runner/workspace | 增加 `aitest.execution_contract.v1`；节点校验 manifest、runner、material、attempt |
| 7 | C3/C5 反作弊 | 当前有 manifest/hash，但缺时间窗口、CSV 行数、跨任务复制、截断、额外文件 | 把 5 类检查写入 C3/C5；空日志、复制日志、改 CSV 一律失败 |
| 8 | C7 完整复现字段 | 当前有 toolchain/lstest/model/env，缺 agent config、project code、firmware、device fingerprint | C7 增加 agent-config hash、项目 commit、固件、设备指纹、方案/用例/oracle/结果哈希 |
| 9 | Agent 权限字段与 agent-config-lock | 当前 registry 有 write_scope/tools/review，缺 can-execute/can-write-terminal | 增加 `can_execute_real_device`、`can_write_terminal_state`、`can_change_plan`、`max_concurrency`、`timeout`、`retry_budget`、`agent-config-lock.json` |

### 1.1 M13 的边界

M13 只负责：

- 启动/恢复 OpenCode 后台会话。
- 注入平台任务上下文。
- 记录 `opencode_session_id`、`omo_task_id`、`subtask_id`。
- 接收/轮询会话事件并转成 `platform_events`。
- 标记 `running / disconnected / orphaned / interrupted / completed`。
- 处理历史回放和人工接管入口。

M13 不负责：

- 写任务终态。
- 获取设备租约。
- 计算完成门禁。
- 修改已批准知识。
- 直接执行设备动作。

### 1.2 非阻塞 dispatch 的最小字段

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
  "status": "dispatched|running|completed|failed|timeout|orphaned",
  "idempotency_key": "task:ait-...:sub-...:attempt-1"
}
```

`dispatch` 立即返回；主 Agent 不阻塞；超时/孤儿不直接让任务 PASS。

### 1.3 execution_contract 的最小字段

```json
{
  "schema": "aitest.execution_contract.v1",
  "task_id": "ait-...",
  "execution_id": "exec-...",
  "attempt": 1,
  "lease_id": "lease-...",
  "node_id": "win009",
  "devices": [{"role": "DUT", "device_id": "TCL000", "serial": "usb:vid=...;pid=...;serial=..."}],
  "material_id": "pm-...",
  "manifest_sha256": "...",
  "runner": "scripts/aitest_platform_runner.py",
  "runner_sha256": "...",
  "lstest_pin": "0.9.14",
  "workspace": "C:\\NoahsArk\\work\\exec-...",
  "timeout_s": 7200,
  "expected_artifacts": ["serial_logs/", "tool.log", "results.csv", "cases.csv", "evidence/"],
  "result_contract": "aitest.execution_result.v1"
}
```

规则：`execution_id + attempt` 是幂等键；节点校验 material/manifest/runner；不匹配拒绝执行。

---

## 2. 需要调整后再采纳（P1）

### 2.1 WSS/WebSocket vs HTTPS 长轮询

评审建议 WSS 或受保护 WebSocket。当前 `REMOTE-EXECUTION.md` 选择 HTTPS 长轮询，理由是 Flask + SQLite + 内网 NAT，减少 ASGI/WS 代理。

建议：

- **v2 继续采用 HTTPS 长轮询**，但明确 SLA：任务下发最长 25 秒，取消/停止最多 5 秒心跳窗口。
- 如果要求亚秒级取消、实时日志推送或大量节点，再增加 **WSS 网关**；不要让 WSS 成为 v2 的前置依赖。
- 不管选哪种，`execution_contract`、attempt、orphan、receipt 契约保持一致。

因此：**采纳“Node Agent 主通道”，不采纳“v2 必须 WSS”**；WSS 作为 v2.1 选项。

### 2.2 SSH 的定位

评审建议 SSH 只用于部署/诊断/人工接管。当前 `REMOTE-EXECUTION.md` 写“Linux 不向 Windows 发起入站连接”。

建议改为：

- 常规执行：Node Agent 出站 HTTPS。
- 部署、升级、只读诊断：允许独立管理网的 SSH/WinRM，但**不属于任务执行通道**，单独账号、单独审计，默认不在平台内自动调用。
- 人工排障：通过受控 Relay PTY 或管理网 SSH，不进入测试执行状态机。

这样既保留现场运维能力，又不把 SSH 变成执行器。

### 2.3 C8“测试之测试”

评审判定 Wave 0 要冻结 C8。用户此前明确要求 P4-12 先保留占位，等整体方向确定后再定。

建议：

- 保留 P4-12 占位。
- 现在只定义 **C8 是“测试有效性证明”占位门禁**，不纳入 PASS/FAIL。
- 等完成首个真实任务、拿到证据样本后，再定义 oracle 独立性、已知好/已知坏样本、变异检测、假 PASS 检查。
- 不要把 C8 立即变成硬门禁，否则会阻塞 P4-12 和真实 E2E。

---

## 3. 不建议改变（已有方案正确）

| 评审建议 | 当前方案 | 结论 |
|---|---|---|
| 平台拥有任务事实，OpenCode/OMO 只执行智能工作 | `SOLUTION.md` 4.2、`MODULE-DESIGN.md` M0/M1 | 已正确，保留 |
| 不允许第二套状态机 | D3 双平面、一个事实源 | 已正确，保留 |
| 真实执行、dry-run 不能作为完成证据 | C2/C7、REMOTE-EXECUTION | 已正确，强化 purpose=formal |
| 知识只能写 candidate，approved 需评审 | M5/KB 生命周期 | 已正确，补齐知识分类 |
| 圆桌只能产生候选意见 | M12、P4-11 | 已正确，保留 |
| 不引入 PostgreSQL/独立消息中间件 | D2、SQLite WAL | v2 保持；大规模再评估 |
| 不复制 072300ai 聊天室为独立 Web 平台 | P4-11 discussion plugin | 已正确，保留 |
| Windows 音频必须交互式会话 | REMOTE-EXECUTION 3 | 已正确，必须作为硬验收 |
| 进程树用 Job Object | REMOTE-EXECUTION 2.2 | 已正确，必须实现 |

---

## 4. 评审中建议新增的验收场景

这 18 条应直接进入 P8 的验收矩阵：

1. dry-run 冒充 real
2. 无签名回执
3. 过期租约
4. 错误设备指纹
5. 空日志
6. 跨任务复制产物
7. 修改结果 CSV
8. runner PASS / 独立重算 FAIL
9. OMO 子 Agent 超时，主 Agent 不卡死
10. OpenCode 崩溃，任务变为 interrupted/orphaned
11. 模型中途切换不能改变当前执行绑定
12. 工具链漂移禁止真实执行
13. 设备被其他任务占用
14. 设备离线不能输出产品 FAIL
15. 圆桌一致但缺证据不能 PASS
16. 命中旧项目规则必须显示适用边界
17. 修复成功必须保留原始失败证据和修复链
18. 候选知识未经审核不能当 approved

当前计划有部分测试，但没有把这些作为显式验收项；建议加入 P8-05/P8-10 的验收清单。

---

## 5. 计划变更建议

在不删除现有 81 项的前提下，建议：

| 新任务 | 内容 | 依赖 | 影响 |
|---|---|---|---|
| P0-03c | Agent session / dispatch schema | P0-03 | 增加 `agent_sessions`、`dispatch_attempts`、`session_events` |
| P0-04c | execution_contract.v1 | P0-04 | 冻结 material/runner/workspace/attempt 契约 |
| P0-05b | M13 Orchestrator Adapter / Session Bridge | P0-05 | 非阻塞 dispatch、事件转译、orphan/timeout |
| P5-00 | Execution adapter / Node Agent | P0-04、P5-03 | 已有缺口方案中的执行适配器 |
| P0-03b | Plan/case/oracle schema | P0-03、P4-03 | 已有缺口 |
| P0-04b | Evidence manifest | P0-04、P5-03 | 已有缺口 |
| P8-03b | T3 real-device qualification | P8-03 | 已有缺口 |
| P3-07b | PDF ingestion/OCR | P3-07 | 已有缺口 |

建议计数：**81 + 5 个缺口 + 3 个 M13/契约任务 = 89 项**。如果 M13 与 dispatch schema 合并，则 88 项。

---

## 6. 需要回答的评审决策

评审文件第十二节列了 18 个决策。结合当前方案，建议先定这 8 个：

1. **是否采纳 M13**：建议采纳。
2. **Node Agent 通道**：建议 v2 长轮询，WSS 作为 v2.1。
3. **OpenCode 进程模型**：建议每任务一个 Lead 会话，子 Agent 后台，不共享全局进程。
4. **OMO 版本**：固定官方版本 + toolchain lock，不做未登记 fork。
5. **默认/备用模型**：listenai 默认 `deepseek-v4.1-flash-expires-on-0910`，备用模型由 M3 策略决定。
6. **首批节点/设备**：需要真实清单；没有它 T3 不能做。
7. **自动上电/断电/OTA**：先限定设备与电源控制器；不要默认允许 OTA。
8. **C8**：保留 P4-12 占位，不纳入当前 PASS/FAIL。

---

## 7. 结论

这份评审最值得采纳的不是“再增加功能”，而是把 **平台事实层、会话桥、执行契约、反作弊门禁** 四件事补齐。

优先级：

1. M13 会话桥
2. execution_contract.v1
3. `purpose=formal`
4. C3/C5/C7 反作弊字段
5. Windows 交互式会话 + Job Object
6. WSS/SSH/C8 的取舍

做完 1–5，当前方案才真正从“设计完整”变成“可证明地执行”。
