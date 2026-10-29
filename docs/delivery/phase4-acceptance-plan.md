# Phase 4 验收方案（DRAFT）

> 状态：`DRAFT · NOT FROZEN`。本文只定义“如何证明”，不表示已实施、已测试、已验收、已部署或已发布。
> 适用版本：NoahsArk V0.0.1。编写日期：2026-10-29。
> 输入：需求基线、测试策略 v2.2、施工与验收 v2.2、domain v1.1 §14/§15、evidence-verdict v1.1、security-node v1.1、Phase 2 landing plan、`1.md` §6-§8。

## 0. 文件状态与边界

| 项 | 当前值 | 说明 |
|---|---|---|
| 文档状态 | `DRAFT · NOT FROZEN` | 未评审、未批准、未归档，不构成冻结件 |
| 适用版本 | NoahsArk V0.0.1 | 不外推到后续版本 |
| 覆盖范围 | AC-1..AC-14 的测试、证据、判定与执行规则 | 只回答“如何证明” |
| 不覆盖 | 产品设计、施工排期、代码实现、部署操作、RPO/RTO 承诺 | 分别由 Phase 2、Phase 3、实施阶段和演练记录回答 |
| 契约前提 | 契约仍为 `frozen-candidate v1.1` | 字段名、路由、枚举、阈值未生产冻结 |
| 环境前提 | A-0 未通过，仅完成一台代表节点与一套 DUT 的只读事实采集 | 不代表节点、设备或链路已就绪 |
| 可执行性 | 当前不可执行 | 前置冻结、实现、环境、样本批准均未完成 |

**范围边界**：

1. 本文定义验收的“证明责任”，不定义产品功能优先级，也不替代 Phase 3 施工方案。
2. 本文中的 API 路径、事件名、字段名均为候选标识，只用于追溯；契约冻结后必须逐项替换为冻结值。
3. 本文不声称任何 AC 已满足，不声称任何 T 层级或 L 层级已执行。
4. 本文不包含真实主机名、IP、证书、令牌、设备序列号或项目敏感路径。

## 1. 目的与阅读方式

目的只有三个：

1. 让每个 AC 都能落到明确的模块、接口、界面、证据和测试层级，避免“文档写了等于做了”。
2. 让正式 PASS 只能由五轴、证据、独立复核和分母规则共同产生，避免烟测、模拟或历史重放混入正式结论。
3. 让验收执行、失败处理、证据归档和冻结签收有统一口径，避免临场解释。

阅读顺序：先看第 2 节确认“谁证明什么”，再看第 3 至 6 节确认“用什么场景证明”，最后按第 7 至 10 节执行和归档。第 11 节列出当前不能说的话。

术语约定：

| 术语 | 本文含义 |
|---|---|
| 正式运行 | `mode=formal` 且绑定已冻结 Revision、已批准边界和有效租约的运行 |
| 正式分母 | 只含 `mode=formal`、`validity=VALID`、必需证据完整且已运行 Linux 复核的样本 |
| 烟测 | `mode=smoke` 的独立 run，只证明链路可跑通，永不进入正式分母 |
| 模拟 | `evidence_origin=simulated` 或假节点产生的运行，只到 L2/T4 |
| 重放 | 把历史 run 的证据或结果再次计分；不是本次 formal run 的新样本 |
| 正式 PASS | 五轴精确达到 `COMPLETED / VALID / PASS / COMPLETE / PASS` 且全部前置条件成立 |

## 2. 追溯矩阵

### 2.1 模块编号图例

AC 矩阵中的模块编号与 `phase2-landing-plan-draft.md` 的服务边界对应，冻结后以 Phase 2 的模块命名为准。本表只用于追溯，不新增实现范围。

| 模块 | 名称 | 主要责任 | 允许写入 | 禁止写入 |
|---|---|---|---|---|
| M-01 | 边缘与身份 | TLS、会话、角色、请求审计 envelope | 会话、审计 | 领域状态 |
| M-02 | 任务与修订 | Task、Revision、冻结范围、不可变 | Task、Revision | Run、Verdict |
| M-03 | 审批与门禁 | Approval、G0-G7、唯一有效批准 | Approval、Gate | 业务判定 |
| M-04 | 编排与租约 | Run/Attempt、派发、lease、epoch | Run、Attempt、Lease | 证据、判定 |
| M-05 | 设备与占用 | Device、Node、占用、健康、释放前置 | Device、占用投影 | 判定、证据完整性 |
| M-06 | 节点网关 | 出站长轮询、信封验签、回执去重 | Node、Receipt | 判定、最终状态 |
| M-07 | 证据与判定 | manifest、摘要、清理回执、五轴判定 | Evidence 索引、Verdict | 节点自报覆盖 |
| M-08 | 报告与投影 | 报告、TaskCard、UI 读模型 | 投影 | 权威表 |
| M-09 | 会话与 Lead | lead conversation、恢复、任务卡关联 | 会话上下文 | 执行授权 |
| M-10 | UI | 展示、权限渲染、读模型消费 | 无 | 任何权威状态 |
| M-11 | 知识与审计 | 知识候选、推广、访问审计 | 知识候选、审计 | 自动推广 |
| M-12 | 配置与阈值 | 六层配置、保留、任务级参数 | 配置版本 | 历史判定 |
| M-13 | 恢复与运维 | 备份、恢复顺序、对账、观测 | 恢复记录、审计 | 业务判定 |
| M-14 | 契约与校验 | schema、枚举、错误码、manifest 形状 | 契约版本 | 运行时状态 |
| M-15 | 设备能力与等价 | 能力匹配、端点、等价条件 | 能力投影 | 判定 |

### 2.2 AC 主矩阵

API 列均为候选名，前缀 `/api/v1` 表示控制面业务接口；节点侧只允许出站长轮询，不存在入站管理接口。写入端点以 `backend-integration-task.md` 的四类写意图为最小集合，冻结后以 P2-03 为准。证据列只列“判定必需”，可选诊断不在此表重复。

| AC | 验收摘要 | REQ | 模块 | API / 事件（候选） | UI | 必需证据 | 层级 |
|---|---|---|---|---|---|---|---|
| AC-1 | 三入口归一、审阅、冻结、一次批准；同人可批 | REQ-01/02/04 | M-01/02/03/12 | `POST /api/v1/intake/drafts`、`POST /api/v1/tasks/{task_id}/approvals`、`GET /api/v1/tasks/{task_id}/revisions`、`approval.recorded` | IN-01..03、TK-03 | 草稿来源、审阅记录、批准快照、冻结包摘要 | L0+L5、T2/T6 |
| AC-2 | 单 lead、可恢复会话、独立任务卡、stale 告警 | REQ-02/07/08 | M-09/10/13 | `GET /api/v1/tasks/{task_id}/overview`、`GET /api/v1/tasks/{task_id}/live`、`taskcard.freshness.changed` | TK-02、TK-08、MC-01 | 会话恢复记录、任务卡前后快照、freshness 事件 | L2+L5、T3/T4 |
| AC-3 | 静态/烟测/正式分离；烟测不入分母；逐设备结果 | REQ-09 | M-04/06/07/14 | `GET /api/v1/runs`、`GET /api/v1/runs/{run_id}`、`denominator.rebuilt` | TK-05、RN-01/02 | 三类 run 记录、分母表、逐设备结果 | L2+L4、T1/T4/T6 |
| AC-4 | 无效分类正确；缺证据 fail closed | REQ-05/10 | M-07/14 | `GET /api/v1/verdicts`、`GET /api/v1/evidence`、`verification.recorded` | TK-07、EV-03 | manifest、verdict、verification record | L2+L4、T1/T4/T6 |
| AC-5 | 设备替代受等价条件约束；结果隔离 | REQ-06/10 | M-05/15 | `GET /api/v1/devices`、`GET /api/v1/devices/{device_id}`、`device.substituted` | DV-01/02、RN-02 | 替代批准、切换原因、分设备结果 | L2+L4、T4/T6 |
| AC-6 | 范围变化派生同任务新修订；旧证据不并入 | REQ-03/06/07 | M-02/04/09 | `GET /api/v1/tasks/{task_id}/revisions`、`GET /api/v1/tasks/{task_id}/runs`、`revision.derived` | TK-03、TK-05 | 修订谱系、差量审批、旧证据归属 | L2+L5、T3/T4 |
| AC-7 | 默认摘要；原始材料受限；到期不删 | REQ-11/12 | M-08/12 | `GET /api/v1/reports/{report_id}`、`POST /api/v1/evidence/{evidence_id}/access`、`retention.marked` | RP-01/02、EV-02 | 访问审计、保留状态、报告投影 | L2+L5、T3/T4 |
| AC-8 | 知识候选需审阅；第二任务可复用 | REQ-12 | M-11 | `POST /api/v1/knowledge/{knowledge_id}/review`、`knowledge.reused` | KN-01..03 | 候选、审阅记录、复用来源与适用性 | L5、T6 |
| AC-9 | 自动 PASS 仅来自自动回放与客观证据 | REQ-05/10/11/14 | M-07/08 | `GET /api/v1/verdicts`、`verdict.source.labeled` | TK-07、RP-02 | 判定来源标注、原始证据关联 | L2+L4、T4/T6 |
| AC-10 | 展示与后端状态一致 | REQ-08/13/14 | M-10/13 | `GET /api/v1/mission`、`GET /api/v1/audit`、`projection.rebuilt` | 全域 | 一致性核对表、投影重建记录 | L5、T4/T6 |
| AC-11 | 已启动冻结压测断线继续；设备保持占用；不重派/不重播/不重复采样 | REQ-06/13 | M-05/06 | `heartbeat.offline`、`occupancy.held`、`run.continued` | RN-01/02、DV-01 | 断线运行记录、占用快照、执行许可 | L2+L3、T4/T5 |
| AC-12 | 重连先处理待 STOP，再补传、去重、对账；旧 epoch 不改变当前运行 | REQ-06/13 | M-05/06/13 | `POST /api/v1/node/poll`、`reconnect.reconciled`、`security.epoch.rejected` | TK-08、DV-01 | 重连对账记录、STOP 处理顺序、去重结果 | L2+L3、T4/T5 |
| AC-13 | 设备释放独立于大日志归档与最终判定；执行、释放、证据、判定分别记录 | REQ-06/10 | M-05/07/08 | `POST /api/v1/devices/{device_id}/release-requests`、`POST /api/v1/runs/{run_id}/stop-requests`、`cleanup.receipt`、`verdict.recorded` | RN-02、DV-02 | 释放回执、占用对账、判定记录 | L2+L4、T4/T6 |
| AC-14 | 恢复按数据库→manifest/摘要→占用对账执行；未演练不声称 RPO/RTO | REQ-13 | M-13 + M-07 | `POST /api/v1/admin/restore-drill`、`restore.drill.recorded` | AU-03、ST-04 | 恢复演练报告、对账差异、时间记录 | L2+L4、T3/T6 |

### 2.3 REQ 反向索引

| REQ | 主题 | 覆盖 AC | 未被本文覆盖的部分 |
|---|---|---|---|
| REQ-01 | 范围、三入口、语音域、排除项 | AC-1、AC-9 | 排除项只做非声明检查，不做功能验收 |
| REQ-02 | 角色、提交者、审批者、lead、管理员 | AC-1、AC-2、AC-10 | RBAC 细则待后续设计 |
| REQ-03 | 任务身份、不可变修订、独立运行、追溯 | AC-3、AC-6 | 无 |
| REQ-04 | Intake、来源、冲突、审阅 | AC-1 | 材料质量本身不由本文证明 |
| REQ-05 | 语音域、能力、有效输入、可观察结果 | AC-4、AC-9 | 未声明能力不得验收 |
| REQ-06 | 资源、能力、健康、占用、端点、替代、释放 | AC-5、AC-11..AC-13 | 设备池策略待 O-4 |
| REQ-07 | Lead 会话、恢复、不授权执行 | AC-2、AC-6 | 会话实现细节待设计 |
| REQ-08 | 任务卡、独立进度、stale、未知不编造 | AC-2、AC-10 | 百分比算法待 UI 冻结 |
| REQ-09 | 生命周期、静态/烟测/正式、修复/停止 | AC-3、AC-4 | 重试预算由任务修订批准 |
| REQ-10 | 证据、manifest、fail-closed、设备隔离 | AC-3..AC-5、AC-9、AC-13 | oracle 具体规则由任务冻结 |
| REQ-11 | 报告、摘要、索引、自动/人工区分 | AC-7、AC-9 | 报告版式待 UI 冻结 |
| REQ-12 | 隐私、保留、知识候选 | AC-7、AC-8 | 归档设施待 A-0 |
| REQ-13 | 可追溯、真实、隔离、恢复、安全、隐私、可审阅 | AC-10..AC-14 | 非功能上限待测量 |
| REQ-14 | 排除项，不宣称未运营能力 | AC-9、AC-10 | 只做文案与声明检查 |
| 基线§15 | 十项验收场景 | AC-1..AC-10 | 不是独立需求编号，是验收场景源；AC-11..AC-14 为施工验收补充 |
| 基线§16 | 后续决策清单 | 无 | 不是独立需求编号；不作为本轮通过条件 |

## 3. 测试层级与证据层级

### 3.1 T1-T6

| 层级 | 对象 | 环境 | 真机 | 进入条件 | 主要输出 | 不证明 |
|---|---|---|---|---|---|---|
| T1 单元 | 判定规则、分母、状态机、幂等键 | 本地 | 否 | 代码可构建，规则版本固定 | 覆盖率报告、边界用例清单 | 模块协作、真实链路 |
| T2 契约 | OpenAPI、事件 envelope、Job/Lease/STOP/Receipt、manifest schema | 本地 + 假对象 | 否 | 契约候选可校验 | 契约一致性报告、schema 校验日志 | 集成行为、设备可用 |
| T3 集成 | 控制面模块与 PostgreSQL、事务 outbox、租约与占用 | 本地多进程 | 否 | T1/T2 通过 | 集成报告、故障注入记录 | 真实音频、语音业务 |
| T4 模拟 E2E | 全链路、门禁、断线、STOP、恢复 | 假节点 | 否 | T3 通过 | 模拟运行记录、模拟回执 | 真实设备、真实时序 |
| T5 真机烟测 | 节点 + 设备 + 端点 + 证据链路 | 真实节点 | 是 | 静态检查通过、环境前置满足 | 烟测证据，独立 `run_id` | 正式样本有效性、正式 PASS |
| T6 正式验收 | 语音任务正式采样、五轴、Linux 复核、报告 | 真实设备 | 是 | T5 通过、修订与样本规则已批准 | 正式证据、判定、复核记录、报告 | 其他设备、长期稳定性 |

**硬规则**：

1. T5 与 T6 必须是不同 `run_id`，T5 样本不得计入 T6 分母。
2. T1-T4 的证据只能支撑 L0-L2，不得用来声称 L3-L5 完成。
3. T6 的每个 case 必须能回到 Task、Revision、Run、Attempt、Case、Evidence 和规则版本。
4. 任一层级发现 P0 缺陷，立即停止后续层级，不以“先跑完再修”替代阻断。

### 3.2 L0-L5

| 层级 | 证明什么 | 必需证据 | 不证明什么 | 对应测试 |
|---|---|---|---|---|
| L0 文档契约 | 字段、状态、口径一致 | 评审记录、契约清单、版本哈希 | 系统可运行、设备可用 | T1/T2 的文档核对 |
| L1 静态验证 | 无硬件逻辑自洽 | 静态检查输出、preflight 日志、manifest | 设备可用、音频链路可用 | T1/T2 |
| L2 模拟链路 | 门禁、判定、断线、恢复逻辑正确 | 执行日志、manifest、模拟回执、注入异常 | 真实音频、真实时序、真实释放 | T3/T4 |
| L3 真机烟测 | 节点、设备、端点、采集、清理链路可跑通 | 执行日志、串口日志、原始音频、manifest、清理事实 | 正式样本有效性、正式 PASS | T5 |
| L4 正式采样 | 批准边界内判定有效 | 原始音频、必要设备日志切片、串口日志、执行日志、manifest、异常事件、复核记录 | 其他设备/固件成立、长期稳定 | T6 |
| L5 端到端场景 | 业务闭环可用、第二任务可复用 | L4 全部 + 人工复用评审、报告、知识审阅记录 | 跨项目泛化、未纳入设备 | T6 + 第二任务 |

**禁止**：

- 用 L0-L2 的证据声称 L3-L5 完成。
- 用 L3 烟测样本拼 L4 正式分母。
- 用“节点自报完成”替代 L4 的 Linux 独立复核。
- 用“远程按需读取成功”替代归档或备份。

### 3.3 组合约束

| 运行模式 | 允许层级 | 禁止层级 | 分母 |
|---|---|---|---|
| `static` | L0/L1、T1/T2/T3 | L3-L5、T5/T6 | 永不进入 |
| `smoke` | L3/T5；模拟烟测可 L2/T4 | L4/T6 正式判定 | 永不进入 |
| `formal` | L4/T6；L5 可在正式通过后补充 | 不得用 `static` 或 `smoke` 冒充 | 满足有效性、证据完整、复核后进入 |

一个 `run_id` 只允许一个 `mode`。模式、层级、验收级别三者不一致时，判定直接 `BLOCKED`，不得“按最乐观值解释”。

## 4. 功能与语音矩阵

下表是验收必须覆盖的最小场景集。每个场景都要有独立 case 记录、独立证据集和独立五轴；不得用一个场景的通过替代另一个场景。阈值、语料和重试预算由任务修订显式批准，表中数值只是模板引用。

| ID | 场景 | 输入 / 触发 | 预期五轴与判定 | 正式分母 | 必需证据 | 关键断言 |
|---|---|---|---|---|---|---|
| F-01 | 正向唤醒 | 播放“小T小T”，设备在批准距离与噪声条件下 | `COMPLETED / VALID / PASS / COMPLETE / PASS`，`decision=PASS` | 计入 | 原始音频、串口日志、执行日志、manifest、复核记录 | 唤醒发生、响应可观察、无额外误唤醒 |
| F-02 | 负向不唤醒 | 播放非唤醒词或静音语料，预期设备不唤醒 | 未唤醒则 `COMPLETED / VALID / PASS / COMPLETE / PASS`；误唤醒则 `VALID / FAIL / COMPLETE` | 计入 | 原始音频、串口日志、manifest | 误唤醒次数不超任务阈值；负样本多样 |
| F-03 | 识别正确但未执行 | 唤醒与识别成功，设备未执行预期动作 | `COMPLETED / VALID / FAIL / COMPLETE / PASS`，`failure_class=valid-failure` | 计入 | 原始音频、设备日志切片、串口日志、执行日志 | 识别文本正确不等于交互成功 |
| F-04 | 无效输入 | 语料缺失、格式错误、参数越界、前置条件不成立 | `COMPLETED 或 ABORTED / INVALID / NOT_EVALUATED / COMPLETE 或 INCOMPLETE / NOT_RUN`，`decision=INVALID` | 不计入 | 输入校验记录、manifest、异常说明 | 不得伪装成产品失败，不得计入 PASS/FAIL 分母 |
| F-05 | 识别超时 | 有效输入后超过任务级识别时限 | 若为业务时限：`VALID / FAIL / COMPLETE`；若为端点/基础设施：`BLOCKED / NOT_EVALUATED / 视情况`，`failure_class=invalid-environment 或 infra-error` | 业务超时计入；环境/基础设施不计入 | 时间线、音频、执行日志、端点事实 | 超时原因必须可区分，不得一律记 FAIL |
| F-06 | CrossTalk | 多说话人、旁路音频或串扰条件 | `COMPLETED / VALID / FAIL / COMPLETE / PASS`，标记 CrossTalk | 计入 | 原始音频、串口日志、CrossTalk 标注 | 串扰不得被静默当作识别失败或环境失败 |
| F-07a | UnASR 首次失败 | ASR 无结果或结果不可用，首次 attempt | `COMPLETED / VALID / FAIL / COMPLETE / PASS`，保留首次结果 | 计入首次失败统计 | ASR 输出、原始音频、执行日志 | 首次结果不得被重试覆盖 |
| F-07b | UnASR 重试通过 | 同一 case 新 attempt 重试后通过 | 新 attempt 五轴通过，标 `FLAKY_SUSPECT` | 首次失败按原分类；重试单列，不覆盖首次 | 两次 attempt 的独立证据、重试原因 | 不得把重试通过写成首次通过 |
| F-08 | 运行中重启 | 设备普通重启或异常重启 | `ABORTED / UNKNOWN / NEEDS_REVIEW / COMPLETE / NOT_RUN` | 不计入，先定因 | 重启前后串口日志、时间线、设备事实、执行日志 | 重启不得自动判 PASS，也不得直接判产品 FAIL |
| F-09 | 重复执行 | 同一 `job_id`/`attempt` 重复送达，或疑似重复触发设备动作 | 幂等则返回首次结果且无重复动作；发生重复动作则 `BLOCKED / NEEDS_REVIEW` | 不计入 | 回执链、job 幂等键、设备动作时间线、审计 | 重复执行是 P0 缺陷，不得用“结果相同”豁免 |
| F-10 | 人工喊测 | 人工喊“小T小T”或主观体验记录 | 只能作为 `human_note` 支持证据，`business_verdict` 不得因此自动 PASS | 不计入自动分母 | 人工记录、来源、时间、关联 run | 人工记录永远不能单独构成正式业务 PASS |

**语音判定补充**：

1. 唤醒类指标至少记录 FAR、FRR 的原始计数；没有负样本时不得只报“唤醒成功”。
2. 识别类指标至少区分识别正确率与执行成功率；只报 WER 或只报“有响应”都不足。
3. 交互时延以任务批准的 TTFAB 口径记录；超时归类必须先区分业务超时与环境超时。
4. 所有语音证据必须与 run、case、设备身份和音频端点身份关联；跨设备音频不得混用。
5. 每次重试产生新 attempt，首次 attempt 的证据和结论保持不可变。

## 5. 平台与恢复矩阵

| ID | 场景 | 触发 | 预期行为 | 必需证据 | AC |
|---|---|---|---|---|---|
| P-01 | 门禁顺序 | 跳过 G2 直接请求 G5 | 拒绝推进，返回阻塞原因和当前 gate；不得执行 | 门禁事件、拒绝审计、状态快照 | AC-4 |
| P-02 | 缺批准执行 | 未批准冻结边界即请求派发 | `BLOCKED`，`failure_class=blocked`，不产生 run | 批准查询结果、派发拒绝记录 | AC-1、AC-4 |
| P-03 | 越权读取原始音频 | 无 `evidence_reader` 权限请求原始材料 | 拒绝并审计；不泄露对象是否存在 | 访问审计、拒绝码 | AC-7 |
| P-04 | 摘要不匹配 | 必需证据或回执 digest 与重算值不一致 | 必需证据 → `CONFLICTED`、`BLOCKED/invalid-evidence`；仅回执 → 拒绝回执，判定不变 | 双方摘要、隔离记录、重算日志 | AC-4、AC-9 |
| P-05 | 必需证据缺失 | 冻结 profile 声明的必需项未上传或未核验 | `INCOMPLETE`，不得 PASS；运行可未结案，等待补传 | manifest、缺失清单、补传记录 | AC-4、AC-13 |
| P-06 | 可选诊断缺失 | 非必需日志或截图缺失 | `evidence_status=COMPLETE`，记录 `optional_missing`，不阻塞 PASS | manifest 备注、诊断缺失记录 | AC-4 |
| P-07 | 执行中断线 | 已启动冻结 formal run 时心跳丢失或租约 `expires_at` 到期 | 本地继续执行；控制面标记 `OFFLINE/STALE`，设备保持 `OCCUPIED`，`execution_permit=GRANTED`；不新派、不重播、不重复采样 | 心跳时间线、占用快照、run 继续记录 | AC-11 |
| P-08 | 重连顺序 | 节点恢复连接 | 严格按 STOP-first：处理待 STOP → 停止后续动作 → 补传 → 去重 → 对账 → 恢复领取 | 重连对账记录、STOP ACK、去重统计 | AC-12 |
| P-09 | 旧 epoch 到达 | 旧节点或旧回执携带 `epoch < current_epoch` | `EPOCH_STALE`，不改变当前运行、租约或占用；终态回执仅在 grace 内幂等记录 | 拒绝审计、epoch 对比、回执链 | AC-12 |
| P-10 | 重复上传 | 同 `evidence_id + chunk_index + chunk_digest` 重复到达 | 幂等去重，不重复计数；同 ID 不同摘要转冲突 | 上传幂等记录、去重计数 | AC-4、AC-12 |
| P-11 | 缺清理回执释放 | 本地停止已确认，但缺 `cleanup_receipt` | 释放状态 `held`，设备继续 `OCCUPIED`；不得据此判证据不完整，也不得声称已清理 | 占用快照、释放请求、回执缺失记录 | AC-13 |
| P-12 | 释放与归档分离 | 运行结束但 GB 级日志尚未归档，判定未完成 | 满足本地停止、安全清理、占用对账即可释放；证据可继续上传，判定独立更新 | 释放回执、占用对账、后续证据上传记录 | AC-13 |
| P-13 | 清理失败 | 清理动作失败或占用不确定 | `quarantined`，拒绝释放；判定转 `NEEDS_REVIEW`；人工恢复并记录残余风险 | 清理失败回执、隔离记录、人工复核 | AC-13 |
| P-14 | 控制面重启 | 控制面进程或主机恢复 | 按数据库 → manifest/摘要 → 任务/运行/设备占用对账恢复；不重复创建 task/run，不重复执行 | 恢复日志、对账差异、ID 前后对照 | AC-14 |
| P-15 | 端点变化 | 设备拔插、端点 ID 变化或友好名漂移 | 阻断新运行；不得按友好名回退绑定；需重新识别端点并复核租约 | 端点枚举快照、阻断事件 | AC-5、AC-11 |
| P-16 | 双客户端批准 | 两个客户端同时提交批准 | 只有一个批准生效，另一个返回首次结果或冲突；不产生双批准 | 批准唯一约束、并发测试记录 | AC-1 |

**恢复判定口径**：

1. 通信离线只改变可见性，不改变设备占用和已启动作业的执行许可。
2. 租约 `expired` 只表示续约截止，不是设备所有权到期，也不是 run 失败。
3. 对账完成前不重派设备；对账完成前不得把旧 epoch 回执当作当前事实。
4. 控制面恢复必须先数据库、再 manifest/摘要、再占用对账；顺序错误视为 P0 流程缺陷。
5. 恢复演练未通过时，只能报告“未验证恢复能力”，不得填写 RPO/RTO 达成。

## 6. 设备与样本矩阵

### 6.1 设备事实

下表只登记已采集的只读事实和允许范围，不表示设备已通过能力验收。端点绑定必须使用稳定 `endpoint_id`，不得按友好名回退；表中不记录真实序列号、证书或网络地址。

| 项 | 当前事实 | 验收要求 | 备注 |
|---|---|---|---|
| DUT 身份 | 代表性 DUT `TCL001`；ListenAI 标识 `ListenAIVCOM` | 每次 run 绑定实际设备身份 | 精确硬件料号仍待确认 |
| 固件 | 当前 `V038`；允许白名单 `V038` | 非白名单固件直接 `BLOCKED` | 不做固件刷写、打包、上电 |
| 首个业务能力 | 唤醒词“小T小T” | 正向唤醒与负向不唤醒均可复算 | 尚未执行真实唤醒 |
| 其他语音能力 | 离线命令、自由说、在线 ASR 未声明为已运营 | 只有任务修订显式声明并批准后进入验收 | 不得用唤醒结果外推 |
| 串口 COM3 | CSK 日志，921600 | 只读采集，时间线可对齐 | 端点身份稳定绑定 |
| 串口 COM4 | Hisilicon 日志，921600 | 只读采集，时间线可对齐 | 端点身份稳定绑定 |
| 串口 COM5/COM7 | 当前不使用 | 适配器不得打开；出现打开即判失败 | 负向检查项 |
| 串口 COM6 | ListenAI VCOM | 仅在任务声明需要时使用 | 不作为通用命令通道 |
| 音频采集 | ListenAI Capture，8ch，活动端点 OK | 绑定稳定端点身份；历史 Unknown 端点不得使用 | 采样率、位深由任务冻结 |
| 音频回放 | ListenAI Render，2ch，活动端点 OK | 绑定稳定端点身份；回放校准需记录 | 音量与距离由任务冻结 |
| 重启方式 | 允许通过 A/COM3 发送普通重启 | 重启动作必须由冻结工件声明 | 断电、硬件复位、刷写不在范围 |
| 恢复方式 | 首选 A/COM3 普通重启 | 重启后重新健康探测与端点识别 | 硬件复位需单独批准 |

**能力门**：

1. 能力匹配必须同时检查设备类别、固件、端点、健康、占用和租约；空闲不等于可用。
2. 端点变化、固件不符、COM5/COM7 被打开、历史 Unknown 端点被绑定，任一发生即阻断。
3. 设备替代只允许在任务批准的候选范围内，并满足已批准的等价条件；未批准等价时按设备分别计算分母。
4. 本文不把“能枚举端点”写成“能执行语音任务”；能力必须由 L3/T5 烟测证明。

### 6.2 样本与阈值

样本量、通过率、重试和预算都是任务模板，不是全局默认值。未在冻结修订中显式选定即视为未定义，不得冻结或派发。

| 项 | 候选模板 | 数值 | 验收口径 | 状态 |
|---|---|---|---|---|
| 烟测样本 | `smoke_min` | 1 case × 1 iteration | 独立 `run_id`，不计入正式分母 | 待任务选用 |
| 正式样本（小） | `formal_small` | 30 个有效正式样本 | 10 case × 3 iteration | 待任务选用 |
| 正式样本（中） | `formal_medium` | 100 个有效正式样本 | 20 case × 5 iteration | 建议起点，非标准 |
| 正式样本（大） | `formal_large` | 300 个有效正式样本 | 30 case × 10 iteration | 高置信度场景 |
| 通过率（严格） | `strict_zero_failure` | 100%，关键失败 0 | 最小 30 个有效样本 | 唤醒等零容忍场景候选 |
| 通过率（标准） | `standard_95` | ≥95%，关键失败 0 | 最小 100 个有效样本 | 一般语音回归候选 |
| 重试（最小） | `retry_minimal` | 单 case 0，单 run 0 | 首次即判 | 稳定性基线候选 |
| 重试（标准） | `retry_standard` | 单 case 1，单 run 2 | 重试通过标 `FLAKY_SUSPECT` | 默认建议起点 |
| 运行预算（小） | `budget_small` | 30 min，5 GiB，1 设备 | 受 D: 保护阈值约束 | 待任务选用 |
| 运行预算（中） | `budget_medium` | 2 h，20 GiB，1-2 设备 | 受 D: 保护阈值约束 | 待任务选用 |

**批准规则**：

1. 正式样本数必须按“有效正式样本”计算，无效、阻塞、停止、烟测、模拟、历史重放都不算。
2. 阈值低于模板时必须写明理由并获批准；平台不提供全局放宽。
3. 重试预算不是“重试到通过”；用尽即按首次结果分类并进入复核。
4. 任务未选定样本或阈值时，返回 `SAMPLE_PLAN_UNDEFINED`，拒绝冻结。
5. 设备容量未知时不得批准超过保护阈值的预算；先测量再冻结。

### 6.3 任务断言

| 断言 | 对象 | 通过条件 | 证据 | 失败分类 |
|---|---|---|---|---|
| A-01 唤醒发生 | 正向样本 | 在任务规定的距离、音量、噪声下发生唤醒，且 TTFAB 不超过任务阈值 | 原始音频、串口日志、时间线 | `valid-failure` |
| A-02 响应可观察 | 正向样本 | 设备响应与任务定义的可观察结果一致，不以单一识别文本代替 | 原始音频、设备日志切片、截图（如声明） | `valid-failure` |
| A-03 负向不误唤醒 | 负向样本 | 非唤醒词、静音或干扰语料不触发唤醒；误唤醒数不超任务阈值 | 负向语料、原始音频、串口日志 | `valid-failure` |
| A-04 命令执行成功 | 已声明的命令样本 | 识别正确且设备执行预期动作；两者分别记录 | 音频、设备日志、执行日志 | `valid-failure` |
| A-05 设备隔离 | 跨设备场景 | 未批准等价条件时不合并样本、不互相替代 | 设备身份、切换记录、分设备分母 | `blocked` 或 `invalid-environment` |
| A-06 证据可追溯 | 全部样本 | 每个结论可回到 task/revision/run/case/evidence/规则版本 | manifest、verdict、verification record | `invalid-evidence` |
| A-07 无重复动作 | 重试与重连场景 | 同一 job/attempt 不产生第二次设备动作 | 回执链、动作时间线、幂等键 | P0，`BLOCKED` 或 `NEEDS_REVIEW` |

## 7. 判定规则

### 7.1 五轴

| 轴 | 允许值 | 写入方 | 说明 |
|---|---|---|---|
| `execution_status` | `NOT_STARTED` / `RUNNING` / `COMPLETED` / `ABORTED` / `SKIPPED` | Linux，基于节点事实 | 是否执行，不等于业务结论 |
| `validity_status` | `VALID` / `INVALID` / `BLOCKED` / `UNKNOWN` | Linux | 输入与环境是否有效 |
| `business_verdict` | `PASS` / `FAIL` / `EXPECTED` / `WARN` / `NEEDS_REVIEW` / `NOT_EVALUATED` | Linux | 业务轴，不是最终结论 |
| `evidence_status` | `COMPLETE` / `INCOMPLETE` / `CONFLICTED` / `UNVERIFIED` | Linux | 证据完整性，不用 `UNKNOWN` |
| `verification_status` | `PASS` / `FAIL` / `NOT_RUN` | Linux 独立复核 | 不是业务轴，不能被节点写入 |

节点回执只能提供 `node_observed_*` 事实；节点自报 PASS 必须标 `used_for_decision=false`，与 Linux 结论冲突时以 Linux 重算为准并记录冲突审计。

### 7.2 正式 PASS

正式 PASS 的精确元组，缺一不可：

```text
execution_status    = COMPLETED
validity_status     = VALID
business_verdict    = PASS
evidence_status     = COMPLETE
verification_status = PASS
mode                = formal
decision            = PASS
formal_pass         = true
failure_class       = none
denominator.formal_denominator = true
```

只满足五轴而缺少 `decision=PASS`、`formal_pass=true`、`failure_class=none` 或分母资格时，只能写“轴一致”，不得写正式 PASS。

对应前置条件必须全部为真：

| 条件 | 要求 |
|---|---|
| `approval_valid` | 批准存在，范围摘要与冻结边界一致，批准时间有效 |
| `boundary_frozen` | Revision 已冻结，`bundle_digest` 与批准快照一致 |
| `mode_formal` | `mode=formal`，不是 smoke 或 static |
| `execution_completed` | 执行完成，不是 ABORTED/SKIPPED |
| `sample_valid` | 样本有效，输入与环境满足 |
| `business_pass` | 业务轴为 PASS |
| `required_evidence_complete` | 全部必需证据 `verified`，无缺失 |
| `digest_verified` | 全部必需证据摘要由 Linux 重算一致 |
| `linux_review_pass` | 独立复核 `PASS`，复核记录独立于节点 |
| `no_blocking_anomaly` | 无未处置阻断异常 |
| `denominator_eligible` | 属于正式有效分母 |

判定派生顺序按先命中先返回：非 formal → NOT_APPLICABLE；批准/冻结/租约不符 → BLOCKED；未开始 → NOT_EVALUATED；安全或人工停止 → STOPPED；基础设施故障 → BLOCKED/infra-error；输入无效 → INVALID；环境阻塞 → BLOCKED；证据不完整或摘要/关联失败 → BLOCKED/invalid-evidence；复核未通过 → NEEDS_REVIEW；存在阻断异常 → NEEDS_REVIEW；全部 PASS 前置成立 → PASS；有效失败 → FAIL；其他 → NEEDS_REVIEW。

**禁止**：把设备释放、归档状态、节点自报 PASS 作为判定输入；把 `business_verdict=PASS` 单独当作最终 PASS；把 `verification_status=NOT_RUN` 当作“默认通过”。

### 7.3 fail-closed

| 情形 | 处理 | 不得做的事 |
|---|---|---|
| 缺批准、批准快照不匹配、边界未冻结 | `BLOCKED` | 不得先执行后补批准 |
| 租约/epoch 不符、设备占用冲突 | `BLOCKED` | 不得换新 ID 绕过幂等 |
| `mode` 缺失、未知或与层级不符 | `BLOCKED` | 不得按 formal 解释 |
| 必需证据缺失、摘要不符、来源/关联冲突 | `BLOCKED/invalid-evidence` | 不得用其他 run 证据替代 |
| 必需日志不可读 | `UNVERIFIED` 或 `INCOMPLETE` | 不得 PASS，不得猜内容 |
| `verification_status != PASS` | `NEEDS_REVIEW` | 不得口头宣布通过 |
| 存在未处置阻断异常 | `NEEDS_REVIEW` | 不得忽略异常只看业务结果 |
| 枚举未知、schema 版本未知 | `NEEDS_REVIEW` 或拒绝 | 不得猜测为成功 |
| 清理失败或占用不确定 | `quarantined` + `NEEDS_REVIEW` | 不得释放后继续派发 |

### 7.4 分母资格

| 样本类型 | 是否进入正式分母 | 说明 |
|---|---|---|
| `mode=formal` + `VALID` + 必需证据 `COMPLETE` + Linux 复核已运行 | 是 | 唯一合法正式分母 |
| `valid-failure`（VALID + FAIL + COMPLETE） | 是 | 有效失败，必须计入 |
| `mode=smoke` | 否 | 烟测永不进入 |
| `mode=static` | 否 | 静态检查不是业务样本 |
| `validity=INVALID` | 否 | invalid-input |
| `validity=BLOCKED` | 否 | invalid-environment 或 blocked |
| `evidence_status` 为 `INCOMPLETE`/`CONFLICTED`/`UNVERIFIED` | 否 | 证据不完整不得计分 |
| `decision=STOPPED` | 否 | 停止不是业务失败 |
| `failure_class=infra-error` | 否 | 基础设施故障 |
| `decision=NEEDS_REVIEW` | 暂不计入 | 待复核后再定 |
| 烟测、模拟、历史重放、演示数据 | 否 | 不得拼入正式分母 |
| 重试通过 | 首次按原分类；重试单列 `FLAKY_SUSPECT` | 不覆盖首次结果 |

报告必须固定写明：`formal_denominator = 有效正式样本`。烟测、模拟、历史重放、无效、阻塞、停止、基础设施故障均不计入。自动回放作为正式执行方式可以产生正式证据；但把历史 run 的证据或结果再次计分属于重放，不得进入正式分母。

### 7.5 释放与判定的关系

| 问题 | 规则 |
|---|---|
| 设备释放是 PASS 前置吗 | 不是；PASS 不要求设备已释放 |
| 缺 `cleanup_receipt` 等于证据不完整吗 | 不等于；只表示释放无法确认，设备保持占用 |
| 释放需要什么 | `local_stop_confirmed`、`safe_cleanup_done`、`occupancy_reconciled` 三项同时为真 |
| 释放需要等大日志归档或最终判定吗 | 不需要；执行、释放、证据完整性、判定分别记录 |
| 清理失败怎么办 | `quarantined`，拒绝释放，判定转 `NEEDS_REVIEW`，人工恢复 |
| 释放后还能补证据吗 | 可以；证据状态和复核状态独立更新，不回溯改写已作判定 |

### 7.6 验收 PASS、发布与交付的分离

| 决定 | 由谁作出 | 依据 | 不等于 |
|---|---|---|---|
| 正式 PASS | Linux 判定与独立复核 | 五轴精确元组、分母资格、证据完整、无阻断异常 | 不等于版本可发布 |
| 验收通过 | 验收负责人与所有者 | AC 矩阵、T/P 证据、P0 关闭、残余风险接受 | 不等于生产部署 |
| 发布 | 发布授权人 | DG10、发布包、回滚包、运维手册、单独授权记录 | 不等于验收通过 |
| 对外交付 | 交付负责人与所有者 | 发布授权、移交清单、支持边界 | 不等于长期稳定承诺 |

规则：

1. 正式 PASS 是样本级结论，验收通过是范围级结论，发布是运营决定，交付是合同或移交决定。四者不得互相替代。
2. 验收报告可以写“通过”，但发布记录必须单独存在；没有发布授权时不得部署生产。
3. 发布回滚不得回滚已冻结修订、已接受证据、审计记录和历史判定。
4. 任何对外声明必须同时写明版本、范围、证据层和环境边界，不得把 L2 写成 L4，不得把 T5 写成 T6。

## 8. 验收执行手册

### 8.1 角色

| 角色 | 职责 | 不得做 | 签字点 |
|---|---|---|---|
| 验收负责人 | 维护计划、组织执行、汇总报告、跟踪缺陷 | 不得代替 Linux 写判定 | 执行记录、最终报告 |
| 需求负责人 | 确认 AC 与 REQ 覆盖、裁定范围变化 | 不得跳过批准直接放行 | 需求覆盖确认 |
| 控制面负责人 | 环境、部署、数据库、证据存储、恢复演练 | 不得手工改判定或覆盖证据 | 环境就绪、恢复记录 |
| 节点/设备负责人 | 节点、设备、端点、固件、串口与音频链路 | 不得修改冻结工件或阈值 | 设备就绪、端点核对 |
| 证据管理员 | 目录、摘要、访问控制、保留与归档 | 不得删除或原地替换证据 | 证据索引、归档清单 |
| Linux 独立复核人 | 重算摘要、重建关联、复评分母与 oracle | 不得采信节点自报 PASS | 复核记录 |
| 安全/隐私负责人 | 权限、脱敏、审计、越权检查 | 不得以验收便利放宽访问 | 安全与隐私核对 |
| 所有者/授权签字人 | 批准冻结、接受残余风险、签收 | 不得在缺证据时签 PASS | 冻结批准、最终签收 |

V0.0.1 允许提交者自批，但审批与 Linux 复核仍是两个不同动作；同一人可在不同角色出现，但不得因此省略复核记录。

### 8.2 环境准备

| 类别 | 检查项 | 通过标准 | 证据 |
|---|---|---|---|
| 契约 | 契约版本、schema、错误码、字段名已冻结 | 版本与哈希可查，无候选字段混用 | 冻结记录、哈希 |
| 实现 | 待验收版本可部署、可回滚 | 构建与部署记录完整 | 构建日志、版本清单 |
| 控制面 | PostgreSQL、证据存储、时钟同步、审计 | 健康检查通过，时间偏差在限内 | 健康检查、时钟记录 |
| 节点 | 服务账户、交互式会话、出站通道、spool | 无入站管理端口，spool 未预警 | 节点自检、会话检查 |
| 设备 | 固件 `V038`、端点稳定、COM3/COM4 可读 | 白名单固件，端点身份稳定，COM5/COM7 未打开 | 设备清单、端点快照 |
| 存储 | D: 容量高于保护阈值，证据盘可写 | 预警与保护阈值均满足 | 容量记录 |
| 租约 | 无其他任务持有租约，无待处理 STOP | 占用为空，STOP 队列为空 | 占用快照、STOP 队列 |
| 备份 | 数据库、manifest、证据存储可恢复 | 恢复演练完成并记录 | 演练报告、对账差异 |
| 样本 | 样本量、阈值、重试、预算已批准 | 冻结修订中可查 | 批准快照 |
| 权限 | 角色、任务关系、证据访问已配置 | 最小权限，越权用例可执行 | 权限矩阵、审计 |

任一项不满足即不得进入 T5；T6 还必须满足 T5 通过、修订批准、资源重新检查通过。

### 8.3 执行顺序

| 步骤 | 活动 | 进入 | 退出 | 产物 |
|---|---|---|---|---|
| 0 | 冻结核对 | 本文批准、契约/环境/样本就绪 | 冻结清单签署 | 冻结记录 |
| 1 | L0/T1/T2 | 文档与契约可查 | 文档一致、单元与契约通过 | 评审记录、测试报告 |
| 2 | T3/L2 | 控制面可集成运行 | 模块协作、事务、租约逻辑通过 | 集成报告 |
| 3 | T4/L2 | 假节点可注入故障 | 门禁、断线、STOP、恢复模拟通过 | 模拟运行记录 |
| 4 | T5/L3 | 真机前置满足 | 烟测链路跑通，证据可校验 | 烟测证据，独立 `run_id` |
| 5 | T6/L4 | T5 通过、修订与样本批准 | 正式样本执行、五轴与复核完成 | 正式证据、判定、复核 |
| 6 | L5 | L4 通过 | 第二任务复用、报告、知识审阅完成 | 复用记录、报告 |
| 7 | 汇总与归档 | 所有计划用例有结论 | 报告签署、证据归档、未决登记 | 验收包 |

顺序不可倒置：不得先跑正式采样再补烟测；不得用 T4 模拟结果替代 T5；不得用 T5 结果替代 T6。

### 8.4 证据采集

每个 run 至少采集以下内容，并按第 9 节目录归档：

| 类别 | 内容 | 关联键 | 完整性要求 |
|---|---|---|---|
| 运行事实 | run、attempt、case、开始/结束时间、模式、层级 | `run_id`、`attempt`、`case_id` | UTC 时间，不可回填 |
| 设备事实 | 设备身份、固件、端点身份、串口、音频通道 | `device_id`、`endpoint_id` | 不得用友好名替代身份 |
| 输入 | 音频、语料、参数、回放记录 | `case_id`、`input_digest` | 来源与许可可查 |
| 原始证据 | 音频、串口、设备日志切片、截图 | `evidence_id`、`content_digest` | 内容寻址，不可覆盖 |
| 结构化记录 | 执行日志、结果、异常、回执 | `manifest_id`、`receipt_id` | schema 校验通过 |
| 判定 | 五轴、decision、failure_class、规则版本 | `verdict_id` | Linux 写入 |
| 复核 | 重算摘要、关联、分母、oracle 结果 | `verification_id` | 独立于节点 |
| 释放 | 本地停止、安全清理、占用对账 | `occupancy_id`、`receipt_id` | 与判定分开记录 |
| 访问 | 原始材料读取、导出、下载 | `audit_id` | 逐次审计 |

禁止把真实用户音频、凭据、证书、令牌、设备序列号或内网地址放入报告、截图或版本库。

### 8.5 失败处理

| 等级 | 示例 | 立即动作 | 分母处理 | 回归要求 |
|---|---|---|---|---|
| P0 | 假 PASS、越权、证据丢失、重复执行、跨设备污染 | 停止验收，隔离环境与证据，通知负责人 | 相关样本全部不计入 | 修复后重新执行受影响层级 |
| P1 | 错误分类、状态不一致、恢复顺序错误、分母错误 | 停止相关场景，保留现场 | 受影响样本暂不计入 | 定向回归 + 全链路复跑 |
| P2 | 可用性问题、提示不清、非阻断展示错误 | 记录并继续其他场景 | 视是否影响判定 | 修复后回归该场景 |
| P3 | 文档、文案、体验建议 | 记录，不阻断 | 不影响 | 纳入后续版本 |

失败处理规则：

1. 任何失败都先保留证据，再决定重试；不得先清理现场。
2. 重试必须新建 attempt，不得覆盖首次结果；重试通过标 `FLAKY_SUSPECT`。
3. 环境或基础设施故障归类为 `invalid-environment` 或 `infra-error`，不得写成 `valid-failure`。
4. 证据缺失时保持未结案或 `INCOMPLETE`，不得用推测补全。
5. P0 未关闭前不得进入签收，也不得用“已知问题”绕过。

### 8.6 报告模板

报告章节必须与 `docs/contracts/ui-report-knowledge-audit.md` §3.2 的 14 个必需 `category` 一一对应。即使某类不适用，也必须出现并标记 `EMPTY` 或 `NOT_APPLICABLE`，不得省略。

| 顺序 | `category` | 必填内容 | `record_kind` |
|---|---|---|---|
| 1 | `summary` | 被测版本、契约版本、环境、设备、固件、端点、日期、结论摘要 | `MIXED` |
| 2 | `automated_checks` | 静态检查、preflight、契约检查、命令与退出码 | `AUTOMATED_CHECK` |
| 3 | `smoke` | 独立 smoke run、链路结论、明确“不入正式分母” | `SMOKE` |
| 4 | `formal_records` | 正式样本、逐 case 五轴、decision、failure_class、分母 | `FORMAL` |
| 5 | `human_supplements` | 人工喊测、主观体验、补充说明，标注“非自动判定” | `HUMAN_SUPPLEMENT` |
| 6 | `deviations` | 与冻结计划不符之处、偏差原因、影响 | `MIXED` |
| 7 | `completion_assessment` | 完成评估、AC 覆盖、T/L 达成情况 | `MIXED` |
| 8 | `blockers` | 阻塞因素、未解决项、责任方、解除条件 | `MIXED` |
| 9 | `metrics` | 正式分母、逐设备/逐 case 通过率、有效率、无效分类统计 | `MIXED` |
| 10 | `residual_risks` | P0-P3 缺陷、残余风险、接受人 | `MIXED` |
| 11 | `deliverables_reusable_assets` | 交付物、可复用资产、知识候选、适用条件 | `MIXED` |
| 12 | `lessons_learned` | 成功、失败、异常、误报、修复、重试的经验 | `MIXED` |
| 13 | `evidence_index` | 证据身份、摘要、大小、访问级别、manifest 哈希 | `MIXED` |
| 14 | `unresolved_items` | 未关闭问题、下一步、是否阻断签收 | `MIXED` |

报告必须区分自动判定与人工补充；人工记录不得表述为自动 PASS。报告还必须固定写明 `formal_denominator = 有效正式样本`，并列出被排除的 smoke、static、invalid、blocked、stopped、infra-error、重放样本及排除原因。

### 8.7 退出准则

验收可以退出为“通过”“有条件通过”“阻塞”或“不通过”，但只有以下全部满足才可写“通过”：

1. 计划内用例执行完毕，或有明确的无效/阻塞分类。
2. 每个正式 PASS 都有完整证据、Linux 复核和可复算规则。
3. 分母可重建，烟测、模拟、历史重放均未混入。
4. 所有 P0 关闭，P1 有结论或明确风险接受。
5. 未决项、残余风险、回滚说明已登记。
6. 报告、证据目录、归档哈希和签字齐全。
7. 所有者或授权签字人明确签收。

未满足时任一项只能标记“进行中”“阻塞”或“不通过”，不得标记完成。

## 9. 证据目录与完整性

### 9.1 目录结构

证据目录位于受控证据存储，不进入 Git 仓库。路径只使用 ID、时间和摘要，不使用项目名、设备序列号或人员姓名。

```text
evidence/
  <release>/
    manifests/
      <manifest_id>.json
    tasks/<task_id>/
      revisions/<revision_id>/
        approvals/<approval_id>.json
        runs/<run_id>/
          attempts/<attempt>/
            cases/<case_id>/
              raw_audio/<evidence_id>__<sha256-12>__<name>.<ext>
              serial_log/<evidence_id>__<sha256-12>__<name>.log
              device_log/<evidence_id>__<sha256-12>__<name>.log
              execution_log/<evidence_id>__<sha256-12>__<name>.jsonl
              screenshot/<evidence_id>__<sha256-12>__<name>.png
            meta/manifest.json
            meta/verdict.json
            meta/verification.json
            meta/release.json
          reconnect/<timestamp>__reconciliation.json
    reports/<report_id>/
      report.json
      evidence-index.json
    knowledge/<candidate_id>/
      candidate.json
      review.json
    audit/<yyyy-mm-dd>.jsonl
```

命名规则：

| 对象 | 规则 | 示例 |
|---|---|---|
| 目录 ID | 小写 UUID，禁止可读前缀作为身份 | `cccccccc-cccc-4ccc-8ccc-cccccccccccc` |
| 时间戳 | UTC，`YYYYMMDDTHHMMSSZ` | `20261029T071130Z` |
| 证据文件 | `<evidence_id>__<sha256前12>__<name>.<ext>` | `...__a1b2c3d4e5f6__capture.wav` |
| 摘要 | 完整值写 manifest；文件名只放前 12 位 | `sha256:...` |
| 更正 | 新证据项 + `supersedes`，不覆盖原文件 | `...__supersedes-<id>.json` |
| 禁止 | 空格、中文文件名、IP、序列号、令牌、证书、真实姓名 | 发现即拒绝入库 |

### 9.2 完整性规则

| 规则 | 要求 | 失败处理 |
|---|---|---|
| 内容寻址 | 每个 blob 以 SHA-256 定位，写入前重算 | 不匹配拒绝入库 |
| 摘要复算 | Linux 消费前独立重算，不信任节点摘要 | `CONFLICTED` 或 `INVALID_EVIDENCE` |
| 大小校验 | `size_bytes` 与存储对象一致 | 拒绝并隔离 |
| 关联校验 | task/revision/run/attempt/case/node/device/lease/epoch/bundle/approval 一致 | 拒绝合并，转复核 |
| 不可覆盖 | 已接受证据不得原地替换；更正另立新项 | 违反即 P0 |
| 追加审计 | 访问、上传、校验、释放、判定均追加审计 | 缺审计即不完整 |
| 保留 | 30 天热存到期只标 `archive_pending`，不自动删除 | 无归档不删除 |
| 访问 | 原始音频/日志仅授权角色可读，逐次审计 | 越权拒绝并告警 |
| 备份 | 数据库、manifest、证据索引、文件分别核对 | 远程按需读取不算备份 |
| 归档 | 归档只改 locator，不改 `evidence_id`/digest | 改身份即视为伪造 |

**证据目录验收**：目录可被独立重建；每个 `evidence_id` 可解析；每个 manifest 可重算；每个 verdict 可回到证据和规则版本；每个访问都有审计。

## 10. 冻结检查清单

以下项目全部勾选并由评审人、所有者签署后，本文才可从 `DRAFT · NOT FROZEN` 进入冻结候选。当前全部为“待”。

| # | 检查项 | 通过标准 | 证据 | 状态 |
|---|---|---|---|---|
| 1 | AC 矩阵完整 | AC-1..AC-14 均有 REQ、模块、API、UI、证据、层级 | 本文第 2 节 | 待 |
| 2 | T/L 映射一致 | T1-T6 与 L0-L5 无越级、无混用 | 本文第 3 节 | 待 |
| 3 | 功能与语音场景齐全 | 正向、负向、无效、超时、CrossTalk、UnASR、重启、重复执行均有判定 | 本文第 4 节 | 待 |
| 4 | 平台与恢复场景齐全 | 门禁、权限、证据、断线、STOP-first、对账、释放、恢复均有预期 | 本文第 5 节 | 待 |
| 5 | 设备事实确认 | 固件、端点、串口、排除项与 A-0 记录一致 | 设备清单、端点快照 | 待 |
| 6 | 样本与阈值批准 | 任务修订显式选定样本量、通过率、重试、预算 | 批准快照 | 待 |
| 7 | 五轴与分母规则一致 | 与 domain §14、evidence-verdict §14 逐项一致 | 对照记录 | 待 |
| 8 | 释放语义一致 | 释放三前置、缺回执、清理失败与契约一致 | 对照记录 | 待 |
| 9 | 证据命名可用 | 目录、命名、摘要、更正、访问规则可执行 | 本文第 9 节 | 待 |
| 10 | 角色与签字明确 | 每个角色有责任人和替补 | 角色表 | 待 |
| 11 | 环境准备可核验 | 控制面、节点、设备、存储、时钟、备份均有检查项 | 环境就绪记录 | 待 |
| 12 | 恢复演练有记录 | 数据库 → manifest → 占用对账顺序已验证 | 演练报告 | 待 |
| 13 | 安全与隐私检查 | 无凭据、无越权路径、审计覆盖 | 安全检查记录 | 待 |
| 14 | 非声明明确 | 不声称已执行、已通过、已发布、已达成 RPO/RTO | 本文第 11 节 | 待 |
| 15 | 版本与哈希归档 | 本文、契约、报告、证据目录哈希可查 | 归档清单 | 待 |
| 16 | 独立评审与所有者批准 | 评审意见关闭，所有者签字 | 评审记录、签字 | 待 |

## 11. 明确非声明与缺口

### 11.1 非声明

1. 本文不是冻结件，不表示 Phase 4 已冻结、已批准或已归档。
2. 本文没有执行任何 T1-T6 或 L0-L5，不构成测试执行记录或通过结论。
3. 本文不表示产品代码、迁移、真实 UI、Node Agent、部署或正式测试已开始。
4. 未完成恢复演练前，不声称达到任何 RPO 或 RTO 目标。
5. 没有证据、复核和可复算规则时，不声称任何 PASS。
6. 没有 UI 评审、浏览器 QA 和所有者批准时，不声称 UI 已冻结。
7. T5/L3 烟测通过不等于 T6/L4 正式验收通过。
8. 远程按需读取日志不等于备份、归档或容灾。
9. 样本量、通过率、重试和预算只是模板，不是已批准的全局标准。
10. TCL/ListenAI 只完成有限只读事实采集，未执行真实唤醒，不代表 A-0、L3、L4 或 L5 通过。
11. 本文不授权实现、部署、真机测试、发布或对外承诺。

### 11.2 当前缺口

| 缺口 | 影响 | 关闭条件 | 当前状态 |
|---|---|---|---|
| 契约 v1.1 未生产冻结 | API、字段、枚举、错误码不能作为实现依据 | 评审通过并记录版本/哈希/范围 | 未关闭 |
| A-0 环境未通过 | 节点、设备、存储、网络、证书未就绪 | 环境就绪清单与证据齐全 | 未关闭 |
| UI 未冻结 | AC-2、AC-10 的界面证据无法最终核对 | 高保真原型、QA、所有者批准 | 未关闭 |
| 样本/阈值未任务级批准 | T6 无法定义分母和通过标准 | 冻结修订中显式选定 | 未关闭 |
| RPO/RTO 未演练 | AC-14 只能报告“未验证” | 完成恢复演练并记录时间 | 未关闭 |
| 证据存储与归档未落地 | 证据目录、保留、备份无法验收 | 存储后端、容量、归档路径确定 | 未关闭 |
| 角色与签字人未指定 | 验收无法组织 | 责任人、替补、签字矩阵确认 | 未关闭 |
| 设备等价条件未批准 | AC-5 只能按设备隔离 | 任务级等价字段与验证记录 | 未关闭 |
| 验收窗口未确定 | T5/T6 无法排期 | 所有者确认时间与资源 | 未关闭 |

## 12. 变更记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| draft-0.1 | 2026-10-29 | 建立 Phase 4 验收方案草稿：AC 矩阵、T/L 层级、功能与恢复矩阵、设备与样本、判定规则、执行手册、证据目录、冻结清单 | `DRAFT · NOT FROZEN` |
| draft-0.2 | 2026-10-29 | 增加模块编号图例；把 AC 矩阵 API 对齐到 `/api/v1` 与四类写意图；修正基线§15/§16 的非 REQ 编号表述；把正式 PASS 精确元组补上 `decision`、`formal_pass`、`failure_class`、分母；新增验收 PASS、发布与交付分离表。仍为 `DRAFT · NOT FROZEN`，未执行任何测试或验收。 | `DRAFT · NOT FROZEN` |
