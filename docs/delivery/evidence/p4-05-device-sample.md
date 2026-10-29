# P4-05 设备与样本矩阵

> 状态：`DRAFT · 评审输入 · 非冻结件`
> 归属：`.omo/plans/phase3-6-execution.md` 第 12 项；`docs/delivery/phase4-acceptance-plan.md` §6
> 输入：`phase4-acceptance-plan.md` §3/§6/§7/§8.2、`1.md` §7、`docs/contracts/security-node.md` §9/§11/§12/§16、`docs/contracts/domain.md` §11.3/§11.4、`docs/contracts/evidence-verdict.md` §13.3、`docs/delivery/a0-representative-node-verification.md`
> 边界：本文只登记设备事实、端点、样本量、阈值、分母资格和前置条件；不执行测试，不产生 PASS/FAIL，不改代码、契约、设计、迁移或计划勾选。

## 0. 判读规则

1. 表中“当前事实”来自一次只读采集，只覆盖一台代表节点和一套 DUT，不外推到其他节点、其他固件或其他设备。
2. 端点绑定只认稳定 `endpoint_id`。友好名、历史 COM 号、`2-`/`3-` 前缀的历史端点一律不得作为回退依据。
3. 样本量与阈值均为候选模板。任务修订未显式选定即视为未定义，返回 `SAMPLE_PLAN_UNDEFINED`，不得冻结或派发。
4. 本文出现的任何“预计”“候选”字样都不构成批准值，也不构成验收结论。
5. 设备级结论与样本级结论分开记录。单设备结果不得外推为型号级结论。

## 1. 设备能力、固件与端点矩阵

### 1.1 设备身份与固件

| 项 | 当前事实 | 验收要求 | 缺口 |
|---|---|---|---|
| 代表性 DUT | `TCL001`，所有者确认，首个正式 DUT | 每次 run 绑定实际 `device_id`，不得复用别名 | 无第二台设备，无法做跨设备隔离对照 |
| 产品/功能标识 | `ListenAIVCOM` | 作为能力标签参与匹配，不作为硬件料号 | 是否为精确硬件料号未确认 |
| 硬件版本 | 未采集 | `identity.hardware_revision` 必填 | 需现场读取 |
| 序列号 | 未采集 | 只允许 `serial_number_masked` 加 `identity_digest` | 需脱敏后登记 |
| 固件 | `V038` | 白名单只含 `V038`，非白名单直接 `BLOCKED` | 无升级/回退路径，不做刷写 |
| 数量 | 1 | 分母按单设备独立计算 | 设备等价条件未批准 |

### 1.2 端点矩阵

端点 `kind` 只作能力匹配，域内取值限 `audio_capture` / `audio_playback` / `serial` / `usb` / `gpio`。入站别名 `audio_input` / `audio_output` 归一后再入库，写出方只发权威词。

| 端点角色 | 当前枚举 | 绑定身份（脱敏） | 参数 | 验收用途 | 禁止项 |
|---|---|---|---|---|---|
| 音频采集 | `麦克风 (ListenAI Audio)`，状态 `OK` | `VID_8765&PID_5678`，需补 endpoint 摘要 | 8ch，采样率与位深待任务冻结 | `F-01`..`F-07` 的原始音频 | 历史 `Unknown` 麦克风端点 |
| 音频回放 | `扬声器 (ListenAI Audio)`，状态 `OK` | `VID_8765&PID_5678`，需补 endpoint 摘要 | 2ch，音量与距离待任务冻结 | 唤醒词与负向语料回放 | 历史 `Unknown` 扬声器端点 |
| 串口 CSK | `COM3`，`USB-SERIAL-A CH344`，`OK` | `VID_1A86&PID_55D5` | 921600 | CSK 日志、允许的普通重启 | 写任意命令、脚本注入 |
| 串口 Hisilicon | `COM4`，`USB-SERIAL-C CH344`，`OK` | `VID_1A86&PID_55D5` | 921600 | Hisilicon 日志 | 作为通用命令通道 |
| 串口 VCOM | `COM6`，`USB 串行设备`，`OK` | `VID_8765&PID_5678` | 待确认 | 仅在任务显式声明时使用 | 默认打开 |
| 串口未授权 | `COM5`、`COM7`，均 `OK` | CH344 | 921600 | 仅负向检查 | 打开即判本次 run 失败 |
| 历史残留 | `COM8`..`COM11`、带前缀音频端点 | 历史 `Unknown` | 无 | 无 | 任何自动绑定或回退 |

### 1.3 能力门与替代

1. 能力匹配必须同时满足设备类别、固件白名单、端点身份、健康、占用、租约六项。空闲不等于可用，`communication_state=OFFLINE` 不得映射为 `IDLE`。
2. 任一端点身份漂移、固件不符、`COM5`/`COM7` 被打开、历史 `Unknown` 端点被绑定，均阻断新 run。
3. 设备替代只在任务批准的候选范围内成立，且需 `equivalence_group_id` 与 `conditions_digest`。当前未批准任何等价组，故按设备分别计算分母，`F-05` 跨设备场景只能出 `blocked` 或 `invalid-environment`。
4. 枚举到端点只证明端点存在，不证明能执行语音任务。能力必须由 `T5` 烟测证明，`T6` 另行证明。

## 2. 样本量与阈值

### 2.1 候选样本模板

| 模板 | 有效正式样本 | 结构 | 当前状态 |
|---|---|---|---|
| `smoke_min` | 不进入分母 | 1 case × 1 iteration，独立 `run_id` | 待任务选用 |
| `formal_small` | 30 | 10 case × 3 iteration | TCL 单设备候选，未批准 |
| `formal_medium` | 100 | 20 case × 5 iteration | 建议起点，非标准 |
| `formal_large` | 300 | 30 case × 10 iteration | 高置信度场景 |

### 2.2 逐 case 分配（按 `formal_small` = 30）

| Case | 场景 | case 数 | iteration | 样本 | 计入分母 |
|---|---|---|---|---|---|
| `F-01` | 正向唤醒“小T小T” | 3 | 3 | 9 | 是 |
| `F-02` | 负向不唤醒（非唤醒词、静音、干扰） | 3 | 3 | 9 | 是 |
| `F-06` | CrossTalk 串扰 | 2 | 3 | 6 | 是 |
| `F-03` | 识别正确但未执行 | 1 | 3 | 3 | 是 |
| `F-07a` | UnASR 首次失败 | 1 | 3 | 3 | 是 |
| 合计 | 10 个 case | 10 | 3 | 30 | 是 |

`formal_medium` 与 `formal_large` 按同比例放大：`F-01` 6×5/9×10、`F-02` 6×5/9×10、`F-06` 4×5/6×10、`F-03` 2×5/3×10、`F-07a` 2×5/3×10，总数分别 100 与 300。

不进入上表的 case：`F-04` 无效输入、`F-05` 环境类超时、`F-08` 运行中重启、`F-09` 重复执行、`F-10` 人工喊测。这些 case 仍然执行并留证，但只用于分类与缺陷定位，不计入 30。

### 2.3 阈值与断言

| 断言 | 对象 | 通过条件 | 判定分类 |
|---|---|---|---|
| `A-01` 唤醒发生 | `F-01` | 批准距离、音量、噪声下发生唤醒，TTFAB 不超任务阈值 | `valid-failure` |
| `A-02` 响应可观察 | `F-01` | 响应与任务定义的可观察结果一致，不以识别文本代替 | `valid-failure` |
| `A-03` 负向不误唤醒 | `F-02` | 误唤醒数为 0；任一误唤醒即该样本 FAIL | `valid-failure` |
| `A-04` 命令执行成功 | `F-03` | 识别与执行分别记录，执行缺失即 `valid-failure` | `valid-failure` |
| `A-05` 设备隔离 | 跨设备 | 未批准等价时不合并样本、不互相替代 | `blocked` / `invalid-environment` |
| `A-06` 证据可追溯 | 全部 | 可回到 task/revision/run/case/evidence/规则版本 | `invalid-evidence` |
| `A-07` 无重复动作 | 重试、重连 | 同一 `job_id`/`attempt` 不产生第二次设备动作 | P0，`BLOCKED` / `NEEDS_REVIEW` |

通过率候选：`strict_zero_failure` 为 100% 且关键失败 0，最小 30 个有效样本，适用于唤醒类零容忍场景；`standard_95` 为 ≥95% 且关键失败 0，最小 100 个有效样本。TCL 单设备建议从 `formal_small` 加 `strict_zero_failure` 起步，但未获批准前不得作为派发依据。

距离、音量、噪声底、TTFAB 上限、CrossTalk 判定口径、识别时限均为任务级参数，当前全部未定义，属于缺口而非默认值。

### 2.4 正式分母

```text
formal_denominator =
  count(sample where mode = formal
        and validity_status = VALID
        and evidence_status = COMPLETE
        and linux_verification_has_run = true)
```

有效失败必须计入：`VALID + FAIL + COMPLETE` 的样本照常占分母。以下一律不计入：`mode=smoke`、`mode=static`、`validity=INVALID`、`validity=BLOCKED`、证据为 `INCOMPLETE`/`CONFLICTED`/`UNVERIFIED`、`decision=STOPPED`、`failure_class=infra-error`、模拟或历史重放、演示与 seed 数据。`decision=NEEDS_REVIEW` 暂不计入，复核后再定。

报告必须固定写 `formal_denominator = 有效正式样本`，并逐项列出被排除样本及原因。分母不得用脚本推断，须由 Linux 从 Run、Attempt、Evidence 和复核记录重建。

### 2.5 重试

| 模板 | 单 case 上限 | 单 run 上限 | 处理 |
|---|---|---|---|
| `retry_minimal` | 0 | 0 | 首次即判 |
| `retry_standard` | 1 | 2 | 重试单列 `FLAKY_SUSPECT`，不覆盖首次 |

重试必须新建 attempt。首次 attempt 的证据与结论不可变。`F-07b` 的重试通过只作为独立统计项，不能改写 `F-07a` 的首次失败，也不能把两次 attempt 合并成一个样本重复计入分母。

## 3. 环境前置与 R-05

### 3.1 进入 T5/T6 的前置条件

| 类别 | 检查项 | 通过标准 | 当前状态 |
|---|---|---|---|
| 契约 | 契约版本、schema、枚举已冻结 | 版本与哈希可查 | 未关闭，`frozen-candidate v1.1` |
| 控制面 | PostgreSQL 16、证据存储、时钟同步、审计 | 健康检查通过，时间偏差在限内 | 未部署 |
| 节点 | 服务账户、交互式会话、仅出站通道、spool | 无入站管理端口，spool 未预警 | Node Agent 未构建 |
| 节点运行时 | Python 3.11/3.12、lstest、adapter pin | 版本可查且锁定 | 当前 `3.10.11`，NEEDS-FIX |
| 安全 | mTLS 客户端证书、注册与撤销 | 证书链、主机名、有效期校验通过 | 未验证 |
| 设备 | 固件 `V038`、端点稳定、`COM3`/`COM4` 可读 | 白名单固件，`COM5`/`COM7` 未打开 | 仅只读枚举 |
| 存储 | D: 高于保护阈值，证据盘可写 | 预警与保护阈值均满足 | 约 199.3 GiB 可用，阈值未定 |
| 租约 | 无其他任务持有租约，无待处理 STOP | 占用为空，STOP 队列为空 | 未验证 |
| 备份 | 数据库、manifest、证据索引可恢复 | 演练完成并记录 | 未演练 |
| 样本 | 样本量、通过率、重试、预算已批准 | 冻结修订中可查 | 未批准 |
| 权限 | 角色、任务关系、证据访问已配置 | 最小权限，越权用例可执行 | 未配置 |

任一不满足即不得进入 `T5`。`T6` 还需 `T5` 通过、修订批准、资源重新检查通过。

### 3.2 R-05：节点可达或现场确认

本文的 R-05 指 `docs/contracts/evidence-verdict.md` §13.3 的释放前置条件，不是 `phase3-construction-plan.md` §10 中编号相同但含义为“共享文件冲突”的风险项，两者不同源，引用时必须带契约章节。

| 项 | 规则 |
|---|---|
| 内容 | 节点可达，或由现场人员确认设备可再分配；离线时不得确认释放 |
| 证据 | `communication_state`、人工现场记录（含时间、人员角色、设备身份） |
| 与三布尔关系 | 不进入 `release_preconditions` 三布尔投影，但确认释放时仍必须满足 |
| 离线处理 | 设备保持 `OCCUPIED` 或 `held_pending_reconciliation`，不得因离线转 `IDLE` |
| 与判定关系 | R-05 只影响释放，不参与五轴，不得作为 PASS 或 FAIL 的输入 |
| 与证据关系 | 缺 R-05 不等于 `evidence_status=INCOMPLETE`，也不得反推 `decision!=PASS` |
| 演练要求 | 离线不确认释放、重连后补确认两条路径都要有记录，当前均未演练 |

在设备矩阵语境下，R-05 还约束样本切换：设备未完成释放确认前，不得把下一批样本派到同一 `(node_id, device_id, endpoint_set)` 占用键上。

## 4. 需真实设备或凭据才能关闭的缺口

| # | 缺口 | 影响的矩阵项 | 关闭条件 |
|---|---|---|---|
| 1 | 硬件版本、脱敏序列号、`identity_digest` 未采集 | 1.1 身份、设备隔离 | 现场只读采集并登记 |
| 2 | 音频端点稳定 `endpoint_id` 与身份摘要未生成 | 1.2 音频两行 | 采集 endpoint 身份摘要并与设备绑定 |
| 3 | 串口端点身份摘要与端口占用策略未验证 | 1.2 串口各行 | 枚举快照加负向打开检查 |
| 4 | 距离、音量、噪声底、TTFAB、识别时限未定 | 2.3 全部阈值 | 任务修订批准并写入冻结包 |
| 5 | 正式 profile、TCL 脚本、case 清单未提供 | 2.2 全部分配 | 平台生成加人工评审后冻结 |
| 6 | Python 3.10.11 低于目标 3.11/3.12 | 3.1 节点运行时 | 升级或重建受控 venv |
| 7 | Node Agent、adapter、lstest pin 未构建 | 3.1 节点 | W5 交付并可安装 |
| 8 | mTLS 证书、注册、撤销、出站长轮询未验证 | 3.1 安全 | 证书签发加链路验证记录 |
| 9 | NTP 源与偏差未测 | 3.1 时钟同步 | 记录偏差并在限内 |
| 10 | 设备等价条件与候选池未批准 | 1.3 替代、`A-05` | 任务级批准加验证记录 |
| 11 | 第二台设备或第二固件缺失 | 跨设备结论 | 提供设备并单独计算分母 |
| 12 | 证据存储后端、容量、归档路径未定 | 3.1 存储与备份 | 后端确定并完成恢复演练 |
| 13 | R-05 的离线与现场确认两条路径未演练 | 3.2 | 演练记录加对账差异 |
| 14 | T5/T6 时间窗与责任人未指定 | 全部 | 所有者确认时间、资源、角色 |

上述缺口在关闭前，相关 case 只能标 `BLOCKED` 或 `NEEDS_REVIEW`，不得用其他 run、其他设备或模拟结果填补。

## 5. 非声明

1. 本文未执行任何 `T5`/`T6` 或 `L3`/`L4`/`L5`，不构成测试记录或通过结论。
2. 本文不表示 A-0 已通过。代表节点仅完成有限只读事实采集，真机唤醒仍为 PENDING。
3. 本文不表示设备能力已验收。端点枚举成功不等于能执行语音任务。
4. 本文的样本量与阈值是候选模板，不是已批准的全局标准，也不构成对任何任务的默认值。
5. 本文不表示 R-05 已验证，离线不确认释放与重连补确认均未演练。
6. 本文不声称任何设备、固件或端点组合已通过正式 PASS，也不授权真机执行、部署或对外承诺。
