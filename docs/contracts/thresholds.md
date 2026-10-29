# NoahsArk V0.0.1 运行阈值与默认值契约（thresholds.md）

> 状态：`frozen-candidate v1.1`，等待 Orchestrator/所有者评审。**不是已批准契约**，不构成实现、测试、部署或发布授权。**not production-frozen; Phase 0 not closed**。
> 契约版本：`thresholds-v1`；`schema_version`：`1.0`。
> 形成日期：2026-10-28。
> 适用版本：NoahsArk V0.0.1。
> 依据：已批准需求基线；`.omo/plans/noahsark-platform-delivery.md` 的 P0-08；`.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` 第 5/6/7/9 节；`.omo/drafts/01-design/noahsark-v0.0.1-module-design.md` M-03/M-04/M-07；`.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md` 第 2.1/5 节；`.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md` 第 3.2/3.3/3.8 节；`.omo/drafts/05-decisions/noahsark-v0.0.1-decision-register.md` P0-07/P0-08；`plan.md` 中已确认的离线续跑、设备占用与 STOP-first 规则。
> 同目录 P0-05 `security-node.md` 第 16 节已经冻结了线协议侧的同类数值；本文**复用**这些值，不另立一套。冲突时以本文 §3 的优先级与 §13 的决策记录为准，并在文档同步时回写 P0-05。
> 本文只冻结数值、单位、作用域、覆盖方向与失败行为；不实现代码、不执行测试、不批准任务级参数。

## 1. 结论摘要

V0.0.1 的阈值分三类，**类别的区别比具体数字更重要**：

| 类别 | 含义 | 能否被配置放宽 | 涉及范围 |
|---|---|---|---|
| **H 硬安全边界**（hard safety floor / ceiling） | 安全与证据不可退让的下限/上限 | **否**，任何层都不能放宽 | 租约语义、STOP 语义、磁盘保护、证据不删除、审批不自动拒绝、时钟/nonce 下限、签名与路径白名单 |
| **O 可调运行默认值**（operational default） | 可以按部署/任务收紧或小幅延长的运行参数 | 可收紧；延长受硬上限约束 | 心跳、租约时长、续约宽限、重试、退避、派发超时、日志查询、上传分片、保留天数 |
| **T 任务模板**（template, not global truth） | 仅作为任务起草时的起点 | 必须在冻结修订中显式选定并批准 | 样本量、通过阈值、重试预算、运行预算 |

核心默认值一览：

| 领域 | v1 默认 | 说明 |
|---|---|---|
| 心跳 | 30 s；连续 2 次（60 s）未收到即通信离线 | 心跳消失只改通信可见性 |
| 租约 | 60 s；续约宽限 30 s；**到期不释放设备、不停止已启动运行** | 到期仅是续约截止 |
| 重连对账窗口 | 15 分钟触发人工升级；24 小时标记 `NEEDS_REVIEW` | 期间设备保持 `OCCUPIED`，不重派 |
| 作业派发超时 | 120 s；最多 3 次派发尝试 | 未确认前不得并发重派 |
| STOP 送达/ACK | 30 s；未 ACK 保持待处理并升级 | **超时不等于已停止** |
| 重试退避 | 初始 1 s，×2，上限 60 s，20% 抖动，连续 10 次失败标记离线 | 与 P0-05 一致 |
| 审批提醒 | 24 小时提醒一次；48 小时升级；**永不自动拒绝** | 超时只阻塞门禁 |
| Windows D: 磁盘 | 预警：剩余 <20% 或 <50 GiB；保护：剩余 <10% 或 <20 GiB | 保护触发本地安全停止并保全证据 |
| spool | 上限 min(2 GiB, D: 容量 10%)；70% 预警、95% 保护 | 预警禁新 case，保护本地安全停止 |
| 证据上传 | 8 MiB 分片；片重试 2 s→300 s；24 小时完成期限 | 超期 `INCOMPLETE`，不判失败、不删除 |
| 日志查询 | 24 小时 / 8 MiB / 30 s（硬上限 7 天 / 64 MiB / 120 s） | 白名单只读 |
| 时钟 / nonce | 偏差 ≤120 s（紧急 300 s）；nonce 保留 900 s；回执 grace 24 h | 控制面时间权威 |
| 样本 / 阈值 | **只有模板**：30 / 100 / 300 有效样本；严格 100% 或标准 ≥95% | 每个任务必须显式批准 |

**三条不可退让的语义**（细节见 §4–§7、§13）：

1. 租约到期、心跳丢失、通信离线都**不**释放设备、**不**停止已启动的冻结压测。
2. 审批超时**只提醒和升级**，不会自动拒绝、不会自动通过、不会让运行失败。
3. 磁盘保护触发**本地安全停止并保全证据**，不做静默删除；任何阈值都不能把"释放空间"作为删除原始证据的理由。

## 2. 范围与术语

### 2.1 覆盖范围

1. 通信、租约、心跳、离线续跑与重连对账。
2. 作业派发、STOP 送达、重试与退避、作业时长与 attempt 上限。
3. 审批提醒、升级、等待期与"不自动拒绝"。
4. Windows D: 磁盘预警/保护、spool 容量与清理前置、保留。
5. 证据分片上传、重试、部分上传超时。
6. 日志查询范围、字节、行数、超时与并发。
7. 时钟偏差、nonce/epoch/时间窗、回执 grace。
8. 任务级样本量、通过阈值、重试预算、运行预算**模板**。

### 2.2 非目标

- 不定义业务判定规则（oracle）本身；只定义默认值与模板。
- 不定义 HTTP/SQL/进程实现细节，不定义具体告警渠道产品。
- 不给出任何设备的真实容量、真实语料规模或真实业务基线；这些必须在 P0-10 与任务修订中补齐。
- 不把本文的默认值当作跨任务通用结论。

### 2.3 术语

| 术语 | 含义 |
|---|---|
| 硬安全边界（H） | 安全/证据的不可退让边界；任何配置层都只能更严格，不能放宽 |
| 可调默认值（O） | 部署或任务可调的运行参数；有方向性（只收紧 / 可延长到硬上限） |
| 任务模板（T） | 任务起草建议值；不是全局默认，未在修订中选定即视为未定义 |
| 续约截止（renewal deadline） | `expires_at`；只表示租约需要续约，不是设备所有权到期 |
| 通信离线 | 控制面按心跳窗口判定；只影响可见性，不影响执行许可与占用 |
| 执行许可（execution permit） | 已启动冻结作业在本地继续执行的依据；与通信心跳分离 |
| 保护阈值（protect threshold） | 触发本地安全停止、保全证据的容量/时间界限 |
| 预警阈值（warn threshold） | 触发告警并禁止启动新 case/新作业的界限 |

## 3. 配置层级、优先级与覆盖规则

### 3.1 优先级（从低到高）

```text
schema_default        （本文 v1 默认值，显式最低层）
  < global_default    （平台配置的全局默认）
  < environment       （部署级：控制面 env / 节点配置文件；node 与本层同层）
  < task_revision     （冻结在 revision / approval_snapshot 中）
  < run_override      （仅限冻结修订声明的运行期允许键）
  < hard_safety_floor （H，永远最后生效，只能收紧）
```

> 与 P0-05 对齐说明：`security-node.md` 第 16.2 节使用与本层完全相同的六层顺序 `schema_default < global_default < environment < task_revision < run_override < hard_safety_floor`，并明确 **`node` 与 `environment` 是同一层**。旧写法 `task > node > global > schema_default` 不再作为活动优先级；它只保留为历史说明，用于解释 `task_revision` 高于 `environment`、`node` 即 `environment` 的层间关系，以及新增 `schema_default` 作为显式最低层的原因。本文把 `node/config` 抽象为**环境层**，置于全局默认与任务修订之间；同一平台的多套部署（生产/预发/隔离 staging）可有不同的运维默认值，而不污染全局。

### 3.2 解析规则

1. **方向性**：每个参数在 §4–§12 标注方向。
   - `upper`（上限型，如超时、字节、次数）：`effective = min(候选值)`，且不得高于硬上限。
   - `lower`（下限型，如保留天数、nonce 缓存）：`effective = max(候选值)`，且不得低于硬下限。
   - `fixed`（固定语义）：不允许被覆盖，出现覆盖即拒绝。
2. **硬边界优先**：任何层给出的值若越过硬边界，该值被拒绝（`CONFIG_OUT_OF_BOUNDS`），不得"就近截断后静默使用"；若该参数是冻结修订的一部分，则拒绝冻结/派发并记录审计。
3. **未知/缺失**：fail-closed。安全类参数缺失 → 使用硬边界或拒绝派发；运行类参数缺失 → 使用本文默认并记录 `config_default_applied`。绝不默认"关闭校验"。
4. **运行覆盖的限制**：运行覆盖**只能**作用于冻结修订在 `run_override_allowlist` 中显式声明的运维键（例如日志查询的单次范围、STOP ACK 期限、证据上传并发），并且只能收紧。运行覆盖**不得**改变样本量、通过阈值、oracle、设备动作、证据必要集、预算或判定口径（B-3 冻结边界）。
5. **记录要求**：任务修订覆盖写入冻结包/批准快照；运行覆盖写入 `Run` 记录与审计事件（before/after、操作者、时间、原因）。禁止节点在运行时本地放宽任何值。
6. **不可继承**：任务模板（T）不跨任务继承，不从上一修订自动继承到新修订；每次冻结必须显式选定。

### 3.3 生效矩阵（速查）

| 参数类别 | 全局 | 环境 | 任务修订 | 运行覆盖 | 硬边界 |
|---|---|---|---|---|---|
| 心跳/租约/重试/轮询 | 可设 | 可设 | 可收紧或延长至硬上限 | 仅声明键 | 强制 |
| 派发/STOP/作业时长 | 可设 | 可设 | 可收紧 | 仅声明键 | 强制 |
| 审批提醒/升级 | 可设 | 可设 | 可收紧间隔 | 否 | 永不自动拒绝 |
| D:/spool 阈值 | 可设 | 可设（按节点容量） | 可收紧 | 否 | 保护动作固定 |
| 证据上传 | 可设 | 可设 | 可收紧 | 并发/分片可收紧 | 不得跳过校验 |
| 日志查询 | 可设 | 可设 | 只能收紧 | 可收紧 | 强制 |
| 时钟/nonce/epoch | 可设（更严） | 可设（更严） | 只能收紧 | 否 | 强制 |
| 样本/阈值/预算 | **无全局值** | 不得设 | **必须显式选定** | 否 | 不适用（属任务边界） |

## 4. 租约、心跳、离线与重连（H + O）

| ID | 参数（config key） | v1 默认 | 单位 | 作用域 | 覆盖与方向 | 硬边界 | 超限/失败行为 | 依据 |
|---|---|---|---|---|---|---|---|---|
| TH-L-01 | `heartbeat.interval_seconds` | 30 | s | 节点 | 可设，`upper` 只收紧 | 10–60 | 心跳过慢 → 控制面更早判离线；不影响执行 | P0-05 §16.1；30 s 是 NAT/长轮询下的常见折中 |
| TH-L-02 | `heartbeat.offline_after_missed` | 2 | 次 | 控制面 | 可设，`upper` 只收紧 | 2–5 | 达到即 `communication_offline`；**不改占用、不停 run** | 2 次避免单次抖动误判 |
| TH-L-03 | `heartbeat.offline_after_seconds` | 60 | s | 派生值 | 不可独立设 | = interval × missed | 写入任务卡 `freshness`；仅可观测性 | 避免两个独立阈值互相矛盾 |
| TH-L-04 | `lease.duration_seconds` | 60 | s | 设备租约 | 可设，可延长至上限 | 30–300 | 仅作为续约截止；到期不释放 | 与 P0-05 一致；心跳周期为租约一半 |
| TH-L-05 | `lease.renew_at_fraction` | 0.5 | 比例 | 节点/控制面 | 可设，仅收紧（更早续约） | 0.3–0.8 | 在租约前半段续约，留出重试余量 | 续约失败仍有半个周期可用 |
| TH-L-06 | `lease.expiry_grace_seconds` | 30 | s | 控制面 | 可设，`upper` 只收紧 | 0–60 | 宽限内到达的续约按 `renewed` 处理；超宽限只记过期事实 | 容忍一次长轮询/网络抖动 |
| TH-L-07 | `lease.expiry_semantics` | `renewal_deadline_only` | 枚举 | 全局 | **fixed** | 只能是该值 | 见 §4.1；任何"到期即释放/失败"的实现视为契约违反 | B-3、离线压测确认 |
| TH-L-08 | `lease.release_requires` | `local_stop+cleanup+reconciliation` | 枚举 | 全局 | **fixed** | 固定三项齐备 | 缺任一项 → `release_state=held`，设备继续 `OCCUPIED` | 设备释放与判定分离 |
| TH-L-09 | `reconnect.reconciliation_window_seconds` | 900（15 min） | s | 控制面 | 可设，`upper` 只收紧 | 60–3600 | 超窗 → 升级告警并请求现场确认；**仍不释放设备** | 给操作者足够的恢复时间 |
| TH-L-10 | `reconnect.stop_first` | `required` | 枚举 | 全局 | **fixed** | 固定 | 重连必须先处理待 STOP，再补传、去重、对账 | 已批准重连顺序 |
| TH-L-11 | `offline.continuation` | `allowed_for_started_frozen_runs` | 枚举 | 全局 | **fixed** | 固定 | 未启动的新作业不接受；已启动的继续 | 已批准离线续跑规则 |
| TH-L-12 | `offline.notify_after_seconds` | 1800（30 min） | s | 控制面 | 可设，`upper` 只收紧 | 300–86400 | 通知任务所有者；不停止、不释放 | 区分"提醒"与"处置" |
| TH-L-13 | `offline.needs_review_after_seconds` | 86400（24 h） | s | 控制面 | 可设，`upper` 只收紧 | 3600–604800 | 任务卡标 `NEEDS_REVIEW` + `offline_duration_exceeded`；仍不停止、不释放 | 长时间失联需要人看，但不能自动毁掉在跑压测 |
| TH-L-14 | `offline.max_continuation_seconds` | `unbounded_with_local_safety` | 枚举 | 全局 | **fixed** | 固定 | 只受本地磁盘/spool/设备安全停止约束 | 离线续跑不以时间终止 |

### 4.1 租约语义（不可退让）

```text
expires_at 到期
  → 线协议 lease.state = expired（仅表示续约截止）
  → 设备 occupancy_state 保持 OCCUPIED
  → execution_permit 保持 GRANTED（已启动冻结作业）
  → 不得重派、不得回收、不得判 run 失败
设备释放唯一路径
  → 本地停止确认 + 安全清理回执 + 占用对账完成
```

- 租约到期只是一个**事实**，不是所有权事件、不是判定事件、不是调度事件。
- 心跳丢失只改变 `communication.state`；不得据此把设备标记为空闲，也不得把 `run_state` 改为 `STOPPED`。
- 离线期间不允许启动新 case/新作业；已启动的冻结压测按冻结预算继续。
- 重连对账窗口结束后如果仍无联系，**升级给人**，而不是由系统代为释放或结束。

## 5. 作业派发、STOP 送达、重试与退避（O）

| ID | 参数（config key） | v1 默认 | 单位 | 作用域 | 覆盖与方向 | 硬边界 | 超限/失败行为 | 依据 |
|---|---|---|---|---|---|---|---|---|
| TH-D-01 | `job.dispatch_timeout_seconds` | 120 | s | 控制面 | 可设，`upper` 只收紧 | 30–900 | 标 `DISPATCH_TIMEOUT`；**不并发重派**，先确认无本地动作再重试 | 长轮询 25 s + 节点校验/下载工件余量 |
| TH-D-02 | `job.dispatch_max_attempts` | 3 | 次 | 控制面 | 可设，`upper` 只收紧 | 1–5 | 用尽 → `BLOCKED_DISPATCH`，需人工确认；不得换新 `job_id` 绕过幂等 | 与 `(job_id, attempt)` 幂等键一致 |
| TH-D-03 | `stop.ack_deadline_seconds` | 30 | s | 作业/节点 | 可设，`upper` 只收紧 | 5–120 | 未 ACK → STOP 保持 `pending`，按 §5.1 重发并升级；**绝不当成已停止** | P0-05 §16.1 |
| TH-D-04 | `stop.redelivery_interval_seconds` | 30 | s | 控制面 | 可设，`upper` 只收紧 | 10–300 | 用新 nonce/新签名重发；旧 STOP 过期不执行 | 防重放与时效性 |
| TH-D-05 | `stop.max_pending_hours` | 24 | h | 控制面 | 可设，可延长至上限 | 1–168 | 持续待处理 + 重复升级；不得自动清除、不得判已停止 | 离线期间 STOP 无法即时生效 |
| TH-D-06 | `retry.initial_interval_seconds` | 1 | s | 传输/上传/回执 | 可设，可收紧或小幅放宽 | 0.5–10 | 首次退避起点 | P0-05 一致性 |
| TH-D-07 | `retry.multiplier` | 2.0 | 倍 | 传输/上传/回执 | 可设 | 1.5–3.0 | 指数退避因子 | 业界通用指数退避 |
| TH-D-08 | `retry.max_interval_seconds` | 60 | s | 传输 | 可设，`upper` 只收紧 | 5–300 | 退避封顶，避免无限拉长 | P0-05 |
| TH-D-09 | `retry.jitter_ratio` | 0.20 | 比例 | 传输 | 可设 | 0–0.5 | 抖动打散重连风暴 | 防同步重连尖峰 |
| TH-D-10 | `retry.consecutive_failures_offline` | 10 | 次 | 传输 | 可设，`upper` 只收紧 | 3–20 | 标记 `communication_offline`；不影响本地执行 | P0-05 |
| TH-D-11 | `job.max_attempts` | 10 | 次 | 作业 | 可设，`upper` 只收紧 | 1–20 | 用尽 → `NEEDS_REVIEW`，保留全部 attempt 证据 | 重试不覆盖首次结果 |
| TH-D-12 | `job.max_duration_seconds` | 86400（24 h） | s | 单个冻结作业 | 可设，可延长至上限 | 60–604800 | 达上限 → 本地安全停止、保留证据；**不是判定失败** | 压测可能跑数小时到数天 |
| TH-D-13 | `receipt.retry_window_hours` | 24 | h | 节点 spool | 可设，可延长至上限 | 1–168 | 窗口内持续重试补传；超窗保留本地证据并升级 | 与重连对账窗口区分 |
| TH-D-14 | `receipt.max_backoff_seconds` | 300 | s | 节点 | 可设，`upper` 只收紧 | 5–600 | 回执补传退避上限 | 长离线后避免高频重试 |

### 5.1 STOP 超时的正确语义

```text
控制面发送 STOP（签名 + 当前 epoch + 新 nonce）
  → 30 s 内未收到 ACK
  → STOP 保持 pending（不是 delivered、不是 done）
  → 每 30 s 或重连时重发（重新签名、新 nonce）
  → 同时升级任务所有者
  → 设备继续 OCCUPIED，run 继续，直到节点确认本地安全停止
```

- 离线期间控制面无法即时停止；这是已批准的已知限制，不得用"超时即视为已停止"来掩盖。
- 本地安全 STOP（`local_fail_safe` / `watchdog`）不需要控制面在线，也不需要 ACK 期限；它一旦触发即生效并尽快上报。

### 5.2 重试预算的边界

- 传输重试（补传、轮询、上传）与**测试用例重试**是两件事：前者不改变样本，后者产生新 `attempt`。
- 传输重试不设总次数上限，只受时间窗（`receipt.retry_window_hours`）与退避上限约束；连续失败只影响通信状态。
- 测试重试受任务级重试预算（§11）与 `job.max_attempts` 双重约束；重试通过必须单列 `FLAKY_SUSPECT`，不覆盖首次结果。

## 6. 审批提醒与升级（H + O）

| ID | 参数（config key） | v1 默认 | 单位 | 作用域 | 覆盖与方向 | 硬边界 | 超限/失败行为 | 依据 |
|---|---|---|---|---|---|---|---|---|
| TH-A-01 | `approval.reminder_interval_seconds` | 86400（24 h） | s | 审批 | 可设，可收紧 | 3600–604800 | 到期发提醒；状态仍 `PENDING` | 与工作节奏匹配，避免噪声 |
| TH-A-02 | `approval.escalation_after_seconds` | 172800（48 h） | s | 审批 | 可设，可收紧 | 3600–1209600 | 升级到最高权限/平台管理员队列；仍 `PENDING` | 两次提醒后升级 |
| TH-A-03 | `approval.auto_reject` | `false` | 布尔 | 全局 | **fixed** | 必须为 `false` | 任何"超时自动拒绝"配置 → `CONFIG_OUT_OF_BOUNDS` | 已批准：超时只提醒/升级，不自动拒绝 |
| TH-A-04 | `approval.auto_approve` | `false` | 布尔 | 全局 | **fixed**（生产） | 必须为 `false` | 仅隔离 staging 可由独立策略开启，且不得用于正式运行 | 防止静默批准 |
| TH-A-05 | `approval.wait_timer_seconds` | 0 | s | 审批 | 可设，可增加 | 0–604800 | 等待期内批准不生效，返回 `WAIT_TIMER_ACTIVE` | GitHub Environments wait timer 对标 |
| TH-A-06 | `approval.require_comment` | `true` | 布尔 | 审批 | v1 固定为 `true` | 必须为 `true` | 无意见的批准被拒绝（400），不是超时问题 | v2 审批硬化 |
| TH-A-07 | `approval.max_pending_seconds` | `unbounded` | 枚举 | 审批 | **fixed** | 固定 | 未处理审批永不自动结束；只阻塞门禁 | 不允许"超时即失败/拒绝" |
| TH-A-08 | `approval.escalation_target` | `highest_permission_then_platform_admin` | 枚举 | 审批 | 可设（组织角色映射） | 必须解析到具体接收人 | 解析失败 → 升级到平台管理员并告警；仍不自动拒绝 | 责任必须落到人 |
| TH-A-09 | `approval.reminder_channels` | `[in_app, email]` | 列表 | 审批 | 可设 | 至少一个渠道 | 渠道失败记录并重试；审批状态不变 | 通知是尽力而为，不是状态机 |

### 6.1 审批超时的完整行为

```text
PENDING
  → T+24h：提醒提交者与审批人（状态不变）
  → T+48h：升级到最高权限/平台管理员（状态不变）
  → 之后每 24h 重复提醒/升级
  → 永不 auto-reject、永不 auto-approve、永不把 run 判失败
  → 关联门禁保持阻塞（BLOCKED_APPROVAL），任务卡显示 blocker_owner
```

- **注意（文档冲突）**：架构提案 §6 与本文件旧版草稿曾写"提醒 → 升级 → 拒绝"。V0.0.1 的冻结候选以**本文件为准**：超时只提醒和升级，不拒绝。该措辞需要在文档同步时修正架构 §6 与模块设计 M-03，保留历史评审记录，不覆盖历史结论。
- 审批被拒绝（人工点击拒绝）仍然是合法终态；本规则只禁止**因超时自动拒绝**。

## 7. Windows D: 磁盘保护与 spool（H + O）

### 7.1 磁盘阈值

| ID | 参数（config key） | v1 默认 | 单位 | 作用域 | 覆盖与方向 | 硬边界 | 超限/失败行为 | 依据 |
|---|---|---|---|---|---|---|---|---|
| TH-S-01 | `disk.warn_free_ratio` | 0.20 | 比例 | 节点 D: | 可按节点收紧 | 0.10–0.40 | 触发条件之一；见 §7.3 | 为 30 天热保留留出缓冲 |
| TH-S-02 | `disk.warn_free_bytes` | 53687091200（50 GiB） | 字节 | 节点 D: | 可按节点调整 | 5–200 GiB | 触发条件之一；见 §7.3 | 防止小容量盘比例失真 |
| TH-S-03 | `disk.protect_free_ratio` | 0.10 | 比例 | 节点 D: | 可按节点收紧 | 0.03–0.20 | 触发保护动作 | 低于 10% 时写入放大容易雪崩 |
| TH-S-04 | `disk.protect_free_bytes` | 21474836480（20 GiB） | 字节 | 节点 D: | 可按节点调整 | 2–80 GiB | 触发保护动作 | 保证能写完当前证据与停止日志 |
| TH-S-05 | `disk.protect_action` | `local_safe_stop_preserve_evidence` | 枚举 | 全局 | **fixed** | 固定 | 本地安全停止 + 保全证据 + 上报 | 已批准：不静默删除 |
| TH-S-06 | `disk.never_delete_evidence` | `true` | 布尔 | 全局 | **fixed** | 必须为 `true` | 任何自动删除策略 → 拒绝启动 | 原始证据不可由节点删除 |

### 7.2 spool 阈值

| ID | 参数（config key） | v1 默认 | 单位 | 作用域 | 覆盖与方向 | 硬边界 | 超限/失败行为 | 依据 |
|---|---|---|---|---|---|---|---|---|
| TH-S-07 | `spool.max_bytes` | 2147483648（2 GiB） | 字节 | 节点 | 可设，可延长至上限 | 256 MiB–20 GiB | 达到即 `spool_overflow`，停止接受新作业 | P0-05 §14 |
| TH-S-08 | `spool.max_ratio_of_work_dir` | 0.10 | 比例 | 节点 | 可按节点设置 | 0.02–0.20 | `effective_max = min(max_bytes, ratio × capacity)` | 防止 spool 吃掉 D: |
| TH-S-09 | `spool.warn_ratio` | 0.70 | 比例 | 节点 | 可设，可收紧 | 0.50–0.90 | 进入 `WARN`：禁止启动新 case，继续已启动 case | N-5 |
| TH-S-10 | `spool.protect_ratio` | 0.95 | 比例 | 节点 | 可设，可收紧 | 0.80–1.00 | 进入 `PROTECT`：本地安全停止 + 保全证据 | N-5 |
| TH-S-11 | `spool.delete_only_after_ack` | `true` | 布尔 | 节点 | **fixed** | 必须为 `true` | 未收到控制面 ACK 前不得删除 spool 条目 | 防"已补传但其实没落库" |
| TH-S-12 | `retention.hot_days` | 30 | 天 | 证据 | 可设，可延长 | **≥30**（硬下限） | 到期只标记 `archive_pending`，不删除 | 已批准 30 天热保留 |
| TH-S-13 | `retention.delete_requires` | `archived+authorized+audited` | 枚举 | 全局 | **fixed** | 三项齐备 | 缺任一项 → 拒绝删除，保持热副本 | 无归档不删除 |

### 7.3 触发语义（OR 而不是 AND）

```text
warn    ⇔ (free_bytes / capacity_bytes < warn_free_ratio)  OR  (free_bytes < warn_free_bytes)
protect ⇔ (free_bytes / capacity_bytes < protect_free_ratio) OR (free_bytes < protect_free_bytes)
```

- 用 OR：比例保护小盘，绝对字节保护大盘上的"比例还行但实际快满"的情况。
- `warn` 动作：告警、任务卡显示存储压力、**禁止启动新的 case/formal run**，已启动 case 继续。
- `protect` 动作：**本地安全停止**（不依赖 Linux 在线）→ 写入停止事实 → 保全现有证据与 spool → 重连后上报。
- 保护动作**不得**：删除证据、删除日志、格式化、清理 run root、丢弃 spool。
- 清理只能在"已归档 + 已授权 + 已审计"之后，且只清理热副本；原始证据的删除永远不是磁盘保护的自动后果。

### 7.4 阈值之间的关系（必须校验）

1. `spool.protect_ratio × effective_max <` 可用空间 — 否则 spool 永远先撞磁盘保护。
2. `disk.protect_free_bytes` 必须大于单次最大证据分片与停止日志的写入余量（默认 ≥20 GiB，按 P0-10 实测校准）。
3. 若节点 D: 容量未知 → 使用绝对字节阈值并在任务卡标 `capacity_unknown`；不得默认"容量充足"。
4. `spool.warn_ratio < spool.protect_ratio`，否则 spool 无预警直接保护。

## 8. 证据上传（O + H）

| ID | 参数（config key） | v1 默认 | 单位 | 作用域 | 覆盖与方向 | 硬边界 | 超限/失败行为 | 依据 |
|---|---|---|---|---|---|---|---|---|
| TH-E-01 | `evidence.chunk_size_bytes` | 8388608（8 MiB） | 字节 | 上传 | 可设，可收紧 | 1–16 MiB | 分片过大 → 单次失败重传成本高；过小 → 元数据膨胀 | 与 1 GiB 级日志的分片数量折中 |
| TH-E-02 | `evidence.max_chunks_per_upload` | 10000 | 片 | 上传 | 可设，仅收紧 | 100–10000 | 超限 → 拒绝会话并要求调大分片或拆分证据 | 防止分片元数据耗尽 |
| TH-E-03 | `evidence.chunk_retry_initial_seconds` | 2 | s | 上传 | 可设 | 0.5–30 | 片级重试起点 | 上传链路抖动比心跳更短 |
| TH-E-04 | `evidence.chunk_retry_max_seconds` | 300 | s | 上传 | 可设，`upper` 只收紧 | 5–600 | 片级退避上限 | 避免长尾重试拖死队列 |
| TH-E-05 | `evidence.chunk_retry_max_attempts` | 20 | 次 | 上传 | 可设，`upper` 只收紧 | 3–50 | 用尽 → 该片 `stalled`，会话转 `partial`，不是整个 run 失败 | 部分上传是状态，不是失败 |
| TH-E-06 | `evidence.chunk_inactivity_timeout_seconds` | 120 | s | 上传 | 可设，`upper` 只收紧 | 10–600 | 片超时 → 重试；连续超时 → `stalled` | 与长轮询量级一致 |
| TH-E-07 | `evidence.session_inactivity_timeout_seconds` | 1800（30 min） | s | 上传会话 | 可设，可延长至上限 | 60–86400 | 会话转 `partial`，等待续传；不判失败 | 断线补传可能中断很久 |
| TH-E-08 | `evidence.completion_deadline_hours` | 24 | h | 单次运行 | 可设，可延长至上限 | 1–168 | 超期 → `evidence_status=INCOMPLETE`，不得 PASS，不得删除；计时起点见 §8.2 | 给补传留时间，但迟早要结案 |
| TH-E-09 | `evidence.upload_concurrency_per_node` | 4 | 并发 | 节点 | 可设，`upper` 只收紧 | 1–16 | 超限 → 429/排队；不得挤占心跳与控制消息 | 上传不能饿死控制通道 |
| TH-E-10 | `evidence.manifest_max_bytes` | 4194304（4 MiB） | 字节 | 上传 | 可设，仅收紧 | 64 KiB–16 MiB | 超限 → 413，要求拆分或引用外部清单 | P0-05 §14 |
| TH-E-11 | `evidence.partial_is_failure` | `false` | 布尔 | 全局 | **fixed** | 必须为 `false` | 部分上传不产生失败样本；只影响 `evidence_status` | 已批准 |

### 8.1 部分上传的正确语义

```text
declared → uploading → partial → complete → verified
                        │
                        ├─ 片重试耗尽 → stalled（仍在 partial）
                        └─ 超过 completion_deadline → INCOMPLETE
```

- 部分上传**不是失败**，不得把 run 标为 `invalid-evidence` 的自动理由；但必需证据不完整时 `evidence_status ≠ COMPLETE`，判定不得 PASS。
- 上传超时的后果是"结案为 INCOMPLETE + 保留证据 + 报告标注"，不是"删除"和"判失败"。
- 设备释放不等待 GB 级日志上传完成；释放只依赖本地停止、清理回执和对账（与证据完整性独立）。

### 8.2 完成期限的计时起点（离线续跑兼容）

```text
deadline_start = max(run_end_at_local, first_control_plane_contact_after_run_end)
deadline       = deadline_start + evidence.completion_deadline_hours
```

- 不能简单用"本地 run 结束时间"起算：长时压测可能离线数天，重连后如果期限早已过期，会把完全可补传的证据误判为 `INCOMPLETE`。
- 以"控制面首次重新获知该运行已结束"为实际起点；节点在重连时上报 `run_end_at_local` 与本地 spool 状态，控制面据此计算。
- 期限届满只改变 `evidence_status`，不改变 `execution_status`、不释放设备、不删除证据；报告必须显示"证据不完整"与原因。

## 9. 日志查询限制（O + H）

| ID | 参数（config key） | v1 默认 | 单位 | 作用域 | 覆盖与方向 | 硬边界 | 超限/失败行为 | 依据 |
|---|---|---|---|---|---|---|---|---|
| TH-Q-01 | `log.query.max_range_hours` | 24 | h | 单次查询 | 可设，仅收紧 | 1–168（7 天） | 超限 → 400 `QUERY_RANGE_TOO_LARGE` | P0-05 §12.3 |
| TH-Q-02 | `log.query.max_bytes` | 8388608（8 MiB） | 字节 | 单次查询 | 可设，仅收紧 | ≤67108864（64 MiB） | 超限 → 截断 + `truncated=true` + `next_cursor` | 防止一次拉爆网络/内存 |
| TH-Q-03 | `log.query.timeout_seconds` | 30 | s | 单次查询 | 可设，仅收紧 | 5–120 | 超时 → `QUERY_TIMEOUT`，不返回半截伪装完整 | 只读快照，不挂起 |
| TH-Q-04 | `log.query.max_lines` | 50000 | 行 | 单次查询 | 可设，仅收紧 | ≤200000 | 超限 → 截断 + 游标 | 行数与字节双上限 |
| TH-Q-05 | `log.query.fragment_bytes` | 262144（256 KiB） | 字节 | 结果分片 | 可设，仅收紧 | ≤262144 | 超过 → 分片返回 | P0-05 §12.3 |
| TH-Q-06 | `log.query.max_concurrent_per_node` | 5 | 并发 | 节点 | 可设，仅收紧 | 1–20 | 超限 → 429；审计记录 | 查询不得影响执行 |
| TH-Q-07 | `log.query.request_max_bytes` | 65536（64 KiB） | 字节 | 请求体 | 可设，仅收紧 | ≤262144 | 超限 → 413 | P0-05 §14 |
| TH-Q-08 | `log.query.follow` | `forbidden` | 枚举 | 全局 | **fixed** | 固定 | 不支持 `tail -f`/长挂起；只读快照 | 防止节点资源被长期占用 |

- 查询结果不得触发设备动作，不得解释日志内容为命令。
- 必需日志不可读 → 保持待核验、不得 PASS；可选日志不可读 → 不阻断（与证据契约一致）。

## 10. 时钟、nonce、epoch 与时间窗（H + O）

| ID | 参数（config key） | v1 默认 | 单位 | 作用域 | 覆盖与方向 | 硬边界 | 超限/失败行为 | 依据 |
|---|---|---|---|---|---|---|---|---|
| TH-C-01 | `clock.max_skew_seconds` | 120 | s | 消息验证 | 可设，仅收紧 | 30–180 | 超限 → `CLOCK_SKEW`，拒绝消息并返回控制面时间 | P0-05 §8.3 |
| TH-C-02 | `clock.emergency_skew_seconds` | 300 | s | 节点 | 不可放宽 | 120–600 | 超限 → 停止接受新 Job；已启动压测在安全点继续；本地 STOP 可用 | 防止时钟攻击放大 |
| TH-C-03 | `clock.max_message_age_seconds` | 600 | s | 消息验证 | 可设，仅收紧 | 60–900 | 过旧 → `MESSAGE_EXPIRED` | 覆盖最大 TTL + 偏差 |
| TH-C-04 | `clock.heartbeat_max_age_seconds` | 180 | s | 心跳验证 | 可设，仅收紧 | 60–300 | 过旧 → 心跳被拒；不改变占用 | 心跳 TTL 90 s × 2 |
| TH-C-05 | `nonce.cache_seconds` | 900 | s | 控制面/节点 | 可设，仅延长 | **≥600** | 小于下限 → `CONFIG_OUT_OF_BOUNDS` | ≥ 最大 TTL + 2×最大偏差 |
| TH-C-06 | `nonce.entropy_bits` | 128 | bit | 全局 | **fixed** | ≥128 | 更低 → 拒绝配置 | P0-05 |
| TH-C-07 | `message.ttl_job_lease_stop_seconds` | 300 | s | 控制消息 | 可设，仅收紧 | 30–600 | 超出 → `INVALID_TTL` | P0-05 §16.1 |
| TH-C-08 | `message.ttl_heartbeat_seconds` | 90 | s | 心跳 | 可设，仅收紧 | 30–180 | 超出 → `INVALID_TTL` | 心跳间隔 30 s × 3 |
| TH-C-09 | `message.ttl_enrollment_seconds` | 300 | s | 注册 | 可设，仅收紧 | 60–600 | 超出 → `INVALID_TTL` | 一次性 token 流程 |
| TH-C-10 | `epoch.receipt_grace_hours` | 24 | h | 控制面 | 可设，仅收紧 | 1–72 | 终态回执可在 grace 内按原 epoch 幂等入库；不得改占用/租约 | P0-05 §8.2 |
| TH-C-11 | `epoch.monotonic_per_node` | `true` | 布尔 | 全局 | **fixed** | 必须为 `true` | 旧 epoch 一律 `EPOCH_STALE`，不得回退 | fencing token 语义 |
| TH-C-12 | `message.clock_authority` | `control_plane` | 枚举 | 全局 | **fixed** | 固定 | 节点不得用本地时钟延长租约或接受过期 STOP | 防时钟操控 |

## 11. 任务级样本、阈值与预算模板（T，不是全局事实）

> **重要**：本节全部是**模板**，不是全局默认值，也不构成任何任务的通过标准。每个任务必须在冻结修订中显式选定或自定义，并由批准记录绑定。未选定 = 参数未定义 = 不得冻结/派发。
> 模板只是起草起点，不能跨任务继承，不能由 Agent 自动套用，不能因为"上次是这样"而自动生效。

### 11.1 样本量模板

| ID | 模板 | 有效正式样本 | 用例数 × 迭代 | 适用场景 | 说明 |
|---|---|---|---|---|---|
| TH-T-01 | `smoke_min` | 不计入正式分母 | 1 case × 1 iteration | 烟测 | 使用独立 `run_id`；永不进入正式分母 |
| TH-T-02 | `formal_small` | 30 | 10 × 3 | 单设备、单场景快速回归 | 只够发现高频问题，不足以证明稳定性 |
| TH-T-03 | `formal_medium` | 100 | 20 × 5 | 常规语音任务验收 | 默认建议起点，不是标准 |
| TH-T-04 | `formal_large` | 300 | 30 × 10 | 高置信度/多设备对比 | 成本高，需明确预算 |
| TH-T-05 | `custom` | 任务声明 | 任务声明 | 其他 | 必须写明理由与统计口径 |

- 这里的"有效样本"指满足 `validity_status` 且进入正式分母的样本；`INVALID_*`、`BLOCKED`、`STOPPED`、烟测都不算。
- 负样本/多样性语料要求由任务声明，不由平台模板强制。
- 设备等价性条件不满足时，样本不能跨设备合并（见 AC-5）。

### 11.2 通过阈值模板

| ID | 模板 | 业务通过率 | 关键失败 | 最小有效样本 | 说明 |
|---|---|---|---|---|---|
| TH-T-06 | `strict_zero_failure` | 100% | 0 | 30 | 适合唤醒/关键交互等零容忍场景 |
| TH-T-07 | `standard_95` | ≥95% | 0 | 100 | 适合一般语音回归；失败样本必须逐条解释 |
| TH-T-08 | `custom` | 任务声明 | 任务声明 | 任务声明 | 必须写明分母与排除口径 |

- 通过率分母 = 有效正式样本；不得用烟测、重试通过或无效样本填充。
- 重试通过单列 `FLAKY_SUSPECT`，不改变首次结果的分类，也不计入"首次通过率"。
- 任何任务若把阈值设得比模板更宽松，必须在修订中写明理由并获得批准；平台不提供"全局放宽"。

### 11.3 重试预算模板

| ID | 模板 | 单 case 重试 | 单 run 重试 | 说明 |
|---|---|---|---|---|
| TH-T-09 | `retry_minimal` | 0 | 0 | 严格首次即判；适合稳定性基线 |
| TH-T-10 | `retry_standard` | 1 | 2 | 默认建议起点；重试通过标 `FLAKY_SUSPECT` |
| TH-T-11 | `retry_extended` | 3 | 5 | 高抖动环境；必须单独报告 flaky 率 |
| TH-T-12 | `custom` | 任务声明 | 任务声明 | 需说明为何需要更多重试 |

- 单 case 重试上限受 `job.max_attempts`（默认 10，硬上限 20）约束。
- 重试预算不是"允许一直重试到通过"；用尽即按首次结果分类并进入复核。

### 11.4 运行预算模板

| ID | 模板 | 最长运行时长 | 证据预算 | 并发设备 | 说明 |
|---|---|---|---|---|---|
| TH-T-13 | `budget_small` | 30 min | 5 GiB | 1 | 单机快速回归 |
| TH-T-14 | `budget_medium` | 2 h | 20 GiB | 1–2 | 常规验收 |
| TH-T-15 | `budget_large` | 8 h | 100 GiB | 1–4 | 长时压测；仍受 `job.max_duration_seconds` 上限约束 |
| TH-T-16 | `custom` | 任务声明 | 任务声明 | 任务声明 | 超长压测需单独批准并说明离线续跑预期 |

- 运行预算必须在冻结前确认设备容量（P0-10）；预算超过 D: 保护阈值时不得冻结。
- 压测类任务的时长预算应与"离线续跑"预期一起批准，避免用预算上限误伤已启动的长时间运行。

### 11.5 模板使用规则

1. 模板 ID 只是引用；冻结修订必须展开为具体数值并记录模板来源。
2. 同一任务的不同修订可以更换模板；旧运行按旧修订口径解释，不重算。
3. 模板不得被平台用作"缺省值"；缺失即 `SAMPLE_PLAN_UNDEFINED`，拒绝冻结。
4. 报告必须写明使用的模板/自定义值、分母口径和重试口径。

## 12. 失败行为汇总

| 场景 | 触发阈值 | 系统行为 | 明确不做 |
|---|---|---|---|
| 心跳丢失 | 60 s（2 次） | 标记 `communication_offline`，任务卡陈旧徽章 | 不停 run、不释放设备、不判失败 |
| 租约到期 | 60 s + 30 s 宽限 | 线协议 `expired` 事实；继续占用 | 不重派、不回收、不判失败 |
| 长时间失联 | 15 min 升级 / 24 h 标记复核 | 通知人、标 `NEEDS_REVIEW` | 不自动停止已启动压测、不自动释放 |
| 派发无确认 | 120 s × 3 | `BLOCKED_DISPATCH`，等人工确认 | 不并发重派、不换新 ID |
| STOP 未 ACK | 30 s | 保持 pending，重发 + 升级 | 不视为已停止 |
| 重试耗尽（作业） | 10 次 | `NEEDS_REVIEW`，保留所有 attempt | 不覆盖首次结果 |
| 审批超时 | 24 h 提醒 / 48 h 升级 | 保持 `PENDING`，门禁 `BLOCKED_APPROVAL` | 不自动拒绝、不自动通过、不判 run 失败 |
| D: 预警 | 剩余 <20% 或 <50 GiB | 告警、禁止新 case | 不删除证据 |
| D: 保护 | 剩余 <10% 或 <20 GiB | 本地安全停止 + 保全证据 + 上报 | 不静默删除、不格式化 |
| spool 预警 | 70% | 禁止新 case | 不中断已启动 case |
| spool 保护 | 95% | 本地安全停止 + 保全证据 | 不丢弃 spool、不删除证据 |
| 证据部分上传 | 片重试耗尽 / 会话不活跃 | `partial` / `stalled`，等待续传 | 不判失败、不计数 |
| 证据上传超期 | 运行结束且控制面首次获知后 24 h | `INCOMPLETE`，不得 PASS | 不删除、不伪造完整 |
| 日志查询超限 | 24 h / 8 MiB / 30 s | 截断 + 游标 / 400 / 超时错误 | 不返回半截冒充完整 |
| 时钟偏差超限 | 120 s | 拒绝消息、返回控制面时间 | 不放宽、不本地延长租约 |
| 紧急时钟偏差 | 300 s | 停止接受新 Job；已启动压测安全点继续 | 不强杀设备动作 |
| 配置越界 | 越过 H | `CONFIG_OUT_OF_BOUNDS`，拒绝冻结/派发 | 不静默截断 |
| 配置缺失 | 安全类缺失 | fail-closed：拒绝派发或使用硬边界 | 不关闭校验 |
| 样本/阈值未定义 | 未选模板 | `SAMPLE_PLAN_UNDEFINED`，拒绝冻结 | 不套用默认 |

## 13. 已定决策（decisions taken）

| ID | 决策 | 理由 | 被否决的替代方案 |
|---|---|---|---|
| D-TH-01 | **租约到期不是所有权到期**；到期只表示续约截止，设备保持 `OCCUPIED`，已启动冻结压测继续 | 已批准的离线续跑规则；把通信心跳与设备所有权混为一谈会导致断线时误停、重派、双任务抢设备 | "租约过期 → 释放设备/判 run 失败"（旧架构措辞，明确替代） |
| D-TH-02 | 心跳 **30 s**、离线判定 **2 次/60 s**、租约 **60 s**、宽限 **30 s** 直接复用 P0-05 | 同一系统不能有两套通信时间参数；节点与线协议必须一致 | 为调度单独再定一套（会导致心跳/租约/离线判定互相矛盾） |
| D-TH-03 | 重连对账窗口 **15 min 升级、24 h 标复核**，但**永不自动释放** | 长时压测可能离线数小时；系统不能代替人判断"设备是否还安全" | "对账窗口结束即回收设备" |
| D-TH-04 | 派发超时 **120 s**、最多 **3 次**，未确认前不得并发重派 | 长轮询 25 s + 工件校验/下载需要余量；并发重派会造成重复执行 | "超时立即重派"或"无限重派" |
| D-TH-05 | STOP ACK **30 s**，超时保持 pending 并升级 | 离线期间 STOP 无法即时送达是已知限制；超时≠已停止 | "超时即视为已停止"（会造成实际仍在跑却报告已停） |
| D-TH-06 | 退避 **1 s → ×2 → 60 s，20% 抖动，10 次失败标离线** | 指数退避 + 抖动是传输重试的成熟做法，且与 P0-05 一致 | 固定间隔（会同步重连）、无限退避（恢复太慢） |
| D-TH-07 | 审批 **24 h 提醒、48 h 升级、永不自动拒绝** | 已批准"超时只提醒/升级"；自动拒绝会把"人没看"变成"任务被否决" | 架构 §6 旧措辞"提醒→升级→拒绝"（V0.0.1 不采用，需同步修正） |
| D-TH-08 | 磁盘 **预警 20%/50 GiB、保护 10%/20 GiB，OR 触发**；保护 = 本地安全停止 + 保全证据 | 比例保护小盘、绝对值保护大盘；保护必须优先保证据而不是保空间 | 单一比例阈值（小盘/大盘都会误判）、"保护即删除旧证据" |
| D-TH-09 | spool **min(2 GiB, D: 10%)**，70% 预警 / 95% 保护 | 与 P0-05 一致；预警禁新 case、保护本地安全停止 | 无上限（会吃满 D:）、到限即删除（会丢证据） |
| D-TH-10 | 证据分片 **8 MiB**；24 h 完成期限；部分上传不是失败 | GB 级日志需要可控的分片数量；补传可能跨天；部分上传是状态不是结论 | 1 MiB 分片（元数据过多）、超期即判失败/删除 |
| D-TH-11 | 日志查询 **24 h / 8 MiB / 30 s** 默认，硬上限 **7 天 / 64 MiB / 120 s** | 只读诊断不需要全量拉取；硬上限防止单次查询拖垮节点 | 无限制查询、长时间 `tail -f` |
| D-TH-12 | 时钟 **120 s**（紧急 **300 s**）、nonce **900 s**、回执 grace **24 h** | 与 P0-05 一致；nonce 缓存必须覆盖最大 TTL + 2×偏差 | 更短窗口（误拒正常抖动）、更长窗口（重放风险） |
| D-TH-13 | 样本/阈值/预算**只提供模板**（30/100/300、100%/≥95%、重试 1/2 等），无全局值 | 不同项目、设备、语料的合理样本量差异极大；设全局值会制造错误预期 | 平台给一个"默认通过率"或"默认样本量" |
| D-TH-14 | 优先级 **`schema_default < global_default < environment < task_revision < run_override < hard_safety_floor`**（`node` 与 `environment` 同层）；运行覆盖仅限修订声明的运维键，只能收紧 | B-3 冻结边界要求运行期不能改样本/判据/预算；同时需要在不改判据的前提下调整日志范围等运维参数 | 运行期可自由覆盖（会绕过冻结边界）、完全禁止运行覆盖（日志查询等无法按场景收紧） |
| D-TH-15 | 未知/缺失配置 **fail-closed**；越界 **拒绝**而非截断 | 安全参数缺失时"默认宽松"是最危险的失败模式 | 缺省用最宽松值、就近截断 |
| D-TH-16 | **24 h 作业时长是默认值，不是全局硬上限**；按冻结作业声明，可延至 7 天 | 长时压测需要跨天；用全局 24 h 卡死会误伤已批准的长跑任务 | 全局 24 h 硬上限 |
| D-TH-17 | 审批超时阻塞门禁但**不把 run 判失败** | 未批准就没有执行授权；但"没批准"不等于"测试失败"，不能污染分母 | 超时即 `FAIL`/`INVALID` |
| D-TH-18 | 保留 **30 天热存**，到期只标归档、**无归档不删除** | 已批准保留边界；磁盘保护不能成为删除证据的理由 | 30 天后自动删除、以远程可读代替归档 |
| D-TH-19 | 配置生效值必须写入冻结快照/运行记录并审计 | 事后无法解释"为什么这次用了 5 分钟超时"会让判定不可复算 | 只存最终值不存来源、不记录覆盖者 |

### 13.1 明确的任务级覆盖点

**允许任务级覆盖（必须写入冻结修订/批准快照）：**

1. 作业最长执行时长（≤7 天）与最大 attempt（≤20，建议 ≤10）。
2. 日志查询的单次范围/行数/字节/并发（只能收紧）。
3. STOP ACK 期限（只能收紧）。
4. 证据完成期限（可延长至 7 天）、上传并发/分片（只能收紧）。
5. 样本量、通过阈值、重试预算、运行预算（§11，必须显式选定）。
6. 脱敏 profile（可强制 `strict`；`none` 仍需特权审批）。
7. 证据必要集合与保留策略（不得低于基线）。

**不允许任务级覆盖：**

1. 关闭 mTLS/签名/nonce/epoch/时钟检查。
2. 放宽硬安全边界、证书有效期、nonce 保留、消息大小、路径白名单。
3. 把租约到期当作释放/停止依据。
4. 让审批超时自动拒绝或自动通过。
5. 让磁盘/spool 保护自动删除证据。
6. 让部分上传自动判失败或自动算作完整。
7. 让节点写最终 `business_verdict` / `verification_status`。
8. 通过运行覆盖改变样本、oracle、设备动作、预算或证据要求（B-3）。

### 13.2 与既有契约的数值一致性

| 参数 | 本文 | P0-05 `security-node.md` | 结论 |
|---|---|---|---|
| 心跳 30 s / 2 次 | TH-L-01/02 | §1、§16.1 | 一致 |
| 租约 60 s / 宽限 30 s | TH-L-04/06 | §1、§16.1 | 一致 |
| 时钟 120 s / 300 s | TH-C-01/02 | §8.3、§16.1 | 一致 |
| nonce 900 s | TH-C-05 | §8.1、§16.1 | 一致 |
| 重试 1 s/60 s/20% | TH-D-06..09 | §1、§16.1 | 一致 |
| 日志 24 h / 8 MiB / 30 s | TH-Q-01..03 | §12.3、§16.1 | 一致 |
| spool 2 GiB 或 10% | TH-S-07/08 | §14 | 一致 |
| 回执 grace 24 h | TH-C-10 | §8.2 | 一致 |

- 不一致时的处理：以本文 §13 的决策记录与硬边界为准，并在 P0-05 文档同步时修正；不得让两套数值同时生效。

## 14. 待确认与测量计划

1. **D: 实际容量与设备清单**（P0-10）：`disk.warn_free_bytes` / `protect_free_bytes` 的绝对值需按真实 D: 容量校准；在大容量盘上 50 GiB/20 GiB 可能偏保守。
2. **30 天热保留 vs 磁盘容量**：需用真实音频/日志体积测量 30 天占用，确认 20% 预警是否足够；若不足，优先增加容量或缩短热存，而不是降低保护线。
3. **spool 2 GiB 是否足够**：高码率串口/音频日志可能更快打满；需在 L3 真机烟测中测量速率。
4. **证据分片 8 MiB**：需在真实 WAN/局域网带宽下测量吞吐；若单节点并发 4 × 8 MiB 造成拥塞，可降到 4 MiB 或降低并发。
5. **样本模板校准**：30/100/300 只是模板；具体项目的统计功效需业务方确认。
6. **审批升级对象**：`highest_permission_then_platform_admin` 需要映射到真实组织角色；若暂无平台管理员，需指定兜底责任人。
7. **运行覆盖是否应在 V0.0.1 开放**：建议只开放日志查询范围、上传并发、STOP ACK 三个运维键；是否扩大到其他键需评审。
8. **长时压测与 24 h/7 天边界**：若真实压测超过 7 天，需在 P0-10 明确新的硬上限，而不是运行时绕过。
9. **心跳 30 s 在弱网现场的稳定性**：需在真实节点网络测量丢包与长轮询重建成本。

## 15. 验证方式

在仓库根目录执行：

```bash
python3 -m json.tool docs/contracts/schemas/config/thresholds.schema.json > /dev/null && echo "json.tool OK"

python3 - <<'PY'
import json
from jsonschema import Draft202012Validator

path = "docs/contracts/schemas/config/thresholds.schema.json"
with open(path, encoding="utf-8") as fh:
    schema = json.load(fh)

assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema", path
Draft202012Validator.check_schema(schema)
print("Draft202012 check OK", path)
PY
```

验收口径：

1. `thresholds.schema.json` 可被 `python3 -m json.tool` 解析。
2. 通过 `Draft202012Validator.check_schema`。
3. schema 中的默认值与本文 §4–§12 的表格逐项一致（见 §15.1 的自动核对）。
4. `grep -n "auto_reject" docs/contracts/thresholds.md` 必须只出现"永不自动拒绝/必须为 false"的语义。
5. 不得出现"租约到期释放设备"或"审批超时拒绝"的肯定表述（历史引述需显式标注为被替代）。

### 15.1 默认值一致性核对（建议纳入 CI）

```python
import json, re, pathlib

schema = json.loads(pathlib.Path("docs/contracts/schemas/config/thresholds.schema.json").read_text())
doc = pathlib.Path("docs/contracts/thresholds.md").read_text()

def walk(node, prefix=""):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "default":
                yield prefix, value
            else:
                yield from walk(value, f"{prefix}.{key}" if prefix else key)

for path_, value in walk(schema):
    # 只核对数值型默认值；字符串/布尔/枚举由人工评审
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        continue
    assert str(value) in doc, (path_, value)
print("numeric defaults cross-check OK")
```

> 说明：这是**结构核对**，不是语义等价证明；数值型参数的最终确认仍需人工评审。

## 16. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| thresholds-v1 | 2026-10-28 | 首次形成 V0.0.1 运行阈值冻结候选：租约/心跳/离线/重连、派发/STOP/退避、审批提醒与升级、D:/spool、证据上传、日志查询、时钟/nonce/epoch、任务模板；明确"租约到期不释放、审批超时不拒绝、磁盘保护不删除"三条硬边界；给出配置优先级与任务级覆盖点。 |

## 17. 声明

- 本文状态为 `frozen-candidate v1.1`（**not production-frozen; Phase 0 not closed**），**未获所有者批准**，不构成实现、测试、部署或发布授权。
- 本文所有数值均为 v1 默认或模板，须经评审、真机测量与任务级批准后才能作为生产依据。
- 本文不替代 `security-node.md`（P0-05）、`evidence-verdict.md`（P0-06）、`domain.md`（P0-04）或任务修订本身；冲突时按 §3 与 §13 处理并回写文档。
