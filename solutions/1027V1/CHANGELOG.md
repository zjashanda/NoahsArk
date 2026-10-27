# 1027V1 变更记录

> 对比基线：`noahsark/docs/v2/`
> 版本范围：模块级设计、远程执行、缺口关闭、评审优化
> 状态：设计评审版；产品代码未开始

---

## 1. 已新增

### 1.1 模块级实施设计

文件：`MODULE-DESIGN.md`、`MODULE-DESIGN.pdf`

新增内容：

- 13 个模块：M0 Platform Core、M1 Task/Workflow、M2 Execution/Devices、M3 Model Policy、M4 Event/Push、M5 Knowledge/Retrieval、M6 Planning/Assurance、M7 Completion/Archive、M8 Takeover、M9 Toolchain、M10 Agent/OpenSpec、M11 UI、M12 Discussion。
- 模块职责、不负责范围、数据归属、命令/查询接口、依赖、失败边界。
- 模块耦合矩阵：同步命令、异步事件、只读投影的边界。
- 13 张逐模块/端到端时序图。
- **5.1 逐步骤执行契约**：每一步的触发、输入、校验、写入/状态、结果传导、失败出口。
- **5.2 结果传导表**：`retrieval_packet → plan_revision → executor_receipt → completion_report → task.completed`。
- **5.3 端到端链路**：受理、方案、执行、完成、接管、展示。
- 实施顺序 W0–W7 和模块完成定义。

### 1.2 远程节点执行方案

文件：`REMOTE-EXECUTION.md`、`REMOTE-EXECUTION.pdf`

新增内容：

- Linux 控制面 + Windows 节点 + 设备本地执行拓扑。
- Windows 节点主动出站 HTTPS + 长轮询取任务；Linux 不向节点发起入站连接。
- Windows 服务 + 登录会话执行器双层设计，解决 Session 0 看不到音频设备的问题。
- 技术栈：Flask/Gunicorn/SQLite、Python 3.12 Agent、httpx、pyserial、sounddevice、pywin32 Job Object、WinSW。
- 节点注册、心跳、取任务、claim、状态、证据上传、回执 API。
- Job 状态机：queued → offered → claimed → preparing → preflight → running → uploading → verifying → completed/lost/blocked。
- 远程执行逐步逻辑表。
- 断线、重试、重复回执、设备拔插、上传中断处理。
- 安全边界：只执行 action 枚举、路径守卫、签名回执、TLS、节点 token。
- `seq-14-remote-windows-node` 和 `remote-execution-topology` 两张图。

### 1.3 缺口关闭方案

文件：`GAP-CLOSURE.md`、`GAP-CLOSURE.pdf`

新增内容：

- G1 M2 执行适配器/节点 Agent：契约、文件、验收、所需节点/设备/profile。
- G2 M6 方案/用例/oracle 持久化：`plan_revisions`、`case_sets`、`oracle_sets`，DB 元数据 + 文件内容寻址。
- G3 证据 manifest：目录结构、逐文件哈希、分母、空文件/篡改/路径穿越规则、脱敏。
- G4 M9 T3 真实设备资格：PASS/FAIL/STOPPED、升级/回滚、窗口与负责人。
- G5 美的 5 个 PDF 摄取：文本/表格/OCR、页码引用、质量验收、secret 扫描。
- 建议新增 5 个任务：`P5-00`、`P0-03b`、`P0-04b`、`P8-03b`、`P3-07b`，计划从 81 项扩展到 86 项。
- 需要用户提供的最小启动包。

### 1.4 评审优化建议

文件：`REVIEW-OPTIMIZATION.md`、`REVIEW-OPTIMIZATION.pdf`

新增内容：

- 对 `gpt6sol/noahsark-review-12-sections.md` 的逐项取舍。
- **9 项建议立即采纳**：M13 会话桥、非阻塞 dispatch、phase/verdict 分离、`purpose=formal`、execution_contract、C3/C5 反作弊、C7 复现字段、Agent 权限、session schema。
- **3 项调整**：长轮询 vs WSS、SSH 仅运维、C8 保留占位。
- **2 项暂缓/不采纳**：v2 不强制 WSS、C8 不立即纳入 PASS/FAIL。
- 建议新增 3 个任务：`P0-03c`、`P0-04c`、`P0-05b`；与 5 个缺口任务合计建议 89 项。
- 18 条反作弊验收场景。

### 1.5 V1 总流程图

文件：`NOAHSARK-V1-TOTAL-FLOW.svg`、`.png`、`.pdf`

新增内容：

- 1800 × 1500 总览图，4 个阶段带。
- 覆盖 12 个主阶段、Linux/Windows 执行边界、方案回炉、预检失败、dry-run 拒绝、自修复、C1–C7、C6 回写、归档、终态、接管、M13 会话桥建议。
- 27 个节点、无节点重叠、无文字出画布。
- 后续每个 `1027V*` 都必须生成同名总流程图。

### 1.6 时序图与 PDF

新增目录：`sequences/`

- 14 个时序图 `.mmd` + PNG。
- 1 个远程拓扑图 `.mmd` + PNG。
- `seq-01` 至 `seq-13` 覆盖核心模块；`seq-14` 覆盖 Linux→Windows 远程执行。
- 所有图已用 Mermaid CLI 11.4.2 渲染。
- 对应 PDF 内嵌图片，不依赖 Mermaid 渲染器。

---

## 2. 已修改

- `docs/v2/README.md`：新增 1027V1 文档入口，路径改为 `../../solutions/1027V1/...`。
- `docs/v2/ACCEPTANCE-REPORT.md`：新增模块设计、远程执行、缺口关闭、评审优化入口；链接改到 1027V1。
- 新增 `1027V1/README.md` 版本索引和版本规则。
- `listenai-provider.ts`：恢复/补全 listenai 模型 fallback，当前 `opencode models` 可见 35 个 `listenai/*` 模型。

---

## 3. 仅建议、尚未并入 81 项计划

以下内容已经写在评审/缺口文档中，但 **还没有改 81 项计划，也没有写产品代码**：

- M13 Orchestrator Adapter / Session Bridge。
- `execution_contract.v1`。
- `purpose=formal` 与 C2 增强。
- C3/C5 时间窗口、CSV 行数、跨任务复制、截断/额外文件检查。
- C7 增加 agent config、项目代码、固件、设备指纹、方案/用例/oracle/结果哈希。
- Agent 配置的 `can_execute_real_device`、`can_write_terminal_state`、`max_concurrency`、timeout/retry。
- WSS 作为 v2.1 选项。
- SSH 仅用于部署/诊断。
- C8 仍为 P4-12 占位。

---

## 4. 当前状态

- 设计文档可评审。
- 81 项计划：1 项完成（P0-01），80 项因 M0 评审阻塞。
- 没有后端、真实执行、真实模型切换或真实设备接管。
- 后续建议目录：`1027V2`、`1027V3`，每个版本独立，不覆盖 V1。
