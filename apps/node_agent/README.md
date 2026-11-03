# NoahsArk Node Agent（开发模拟器）

> 状态：P5-W5 开发骨架 · 非生产冻结
> 边界：只做 Windows Node Agent 的开发/模拟形态；**未连接真实设备**，**未做 TCL 真机验证**。

## 定位

Windows 节点只负责“领取冻结工件 → 本地执行 → 回传 `node_observed_*` 事实”。
Linux 控制面是唯一权威：最终五轴判定、证据核验、释放确认都在控制面完成。

本目录提供：

- **出站长轮询**：节点不监听任何入站端口，只主动访问控制面。
- **租约/epoch 跟踪**：拒绝旧 epoch，STOP 优先于新作业。
- **本地 SQLite spool**：先落盘后上传；按 `STOP → stop actions → receipt → reconcile` 顺序重放；message_id 幂等去重。
- **工件校验**：SHA-256 摘要 + 可插拔签名 hook；校验失败拒绝执行。
- **执行器模拟器**：只产生 `node_observed_*` + `used_for_decision=false` 事实，绝不写 `business_verdict` / `verification_status`。
- **清理回执**：`local_stop_confirmed`、`safe_cleanup_done`，并与 `occupancy_reconciled` 组合成释放前置条件。
- **Windows 服务包装 stub**：pywin32 主方案（Linux 上仅做导入保护），NSSM 作为文档化备选。

## 安装与运行

```bash
cd apps/node_agent
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'

# 单轮模拟（控制面不可用时也不会崩，事实留在 spool）
.venv/bin/python -m noahsark_node --once

# 持续运行
.venv/bin/python -m noahsark_node --interval 15
```

环境变量见 `.env.example`。程序不会自动读取 `.env` 文件，请由服务管理器/终端注入。

## 校验

```bash
cd apps/node_agent
../../.venv/bin/python -m pytest
../../.venv/bin/ruff check noahsark_node tests
../../.venv/bin/mypy noahsark_node
```

## 控制面协议（开发骨架，G-NODE 未冻结）

本骨架假定以下出站端点；控制面 W0–W3 完成后可对齐或替换：

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/node/v1/register` | 节点注册 |
| POST | `/node/v1/heartbeat` | 心跳 |
| POST | `/node/v1/poll` | 长轮询作业 / STOP |
| POST | `/node/v1/receipts` | 幂等上传事实回执 |
| POST | `/node/v1/reconcile` | 占用/租约对账 |

响应中的 `messages` 支持 `kind`：`job`、`stop`、`lease`。作业工件可带 `content_b64` 供模拟器验证；生产必须改为受控工件存储 + 正式签名验证。

## 明确未做

- 不监听端口，不接收控制面入站连接。
- 不访问真实串口、声卡、电源或 lstest。
- 不生成正式 PASS/FAIL、`business_verdict`、`verification_status`。
- 不校验真实 Ed25519 签名；当前 HMAC verifier 仅用于模拟测试。
- 不安装/运行 Windows 服务（Linux 开发机）；pywin32 与 NSSM 步骤见 `noahsark_node/service.py`。

## NSSM 备选（文档化）

若目标机不方便用 pywin32 自注册服务，可用 NSSM 包装同一个入口：

```bat
nssm install NoahsArkNodeAgent "C:\path\to\python.exe" "-m noahsark_node --interval 15"
nssm set NoahsArkNodeAgent AppDirectory "C:\path\to\apps\node_agent"
nssm set NoahsArkNodeAgent AppEnvironmentExtra NOAHSARK_CONTROL_PLANE_URL=http://control-plane:8000
nssm start NoahsArkNodeAgent
```

pywin32 仍是主方案（SCM 生命周期、Session 0 服务、STOP 与重启控制）；NSSM 只作简化部署备选。
