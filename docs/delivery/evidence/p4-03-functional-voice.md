# P4-03 功能与语音矩阵

> 状态：DRAFT · 评审输入，不是冻结件
> 归属：`docs/delivery/phase4-acceptance-plan.md` §4；`.omo/plans/phase3-6-execution.md` 第 10 项
> 输入：`phase4-acceptance-plan.md` §3/§4/§6.2/§7/§9、`noahsark-v0.0.1-test-strategy.md` §4、`1.md` §7、`docs/contracts/domain.md` §8/§9/§14
> 边界：本文只定义功能与语音场景的最小覆盖、前置、oracle、证据、失败分流和分母口径。不执行测试，不产生 PASS，不改代码、契约、设计、计划或勾选。P4-08 冻结前全部状态为“待”。

## 0. 判读规则

1. 每个场景必须有独立 `case`、独立 `run_id`/`attempt`、独立证据集和独立五轴，不得用一个场景的通过替代另一个。
2. 场景编号、五轴取值和 `failure_classification` 词表与 `domain.md` §9 一致；证据侧小写投影按 §9.4 映射表转换，不得另造词串。
3. 本文的“通过”只表示该场景在其声明层级内成立，不表示正式 PASS、验收通过、发布或交付。
4. 只写角色代号与设备标识 `TCL001`、固件 `V038`、项目 `ListenAIVCOM`，不写姓名、主机、IP、串口凭据或音频文件内容。
5. 阈值、样本量、重试预算缺省即未定义，返回 `SAMPLE_PLAN_UNDEFINED`，不得按最乐观值冻结。

## 1. 最小覆盖矩阵

| ID | 场景 | 五轴预期 | `failure_classification` | 层级 | 正式分母 |
|---|---|---|---|---|---|
| F-01 | 正向唤醒“小T小T” | `COMPLETED / VALID / PASS / COMPLETE / PASS` | 省略（`none`） | T6（L4） | 计入 |
| F-02 | 负向不唤醒（非唤醒词/静音） | 未唤醒同 F-01；误唤醒 `VALID / FAIL / COMPLETE` | `VALID_FAILURE` | T6（L4） | 计入 |
| F-03 | 识别正确但未执行 | `COMPLETED / VALID / FAIL / COMPLETE / PASS` | `VALID_FAILURE` | T6（L4） | 计入 |
| F-04 | 无效输入 | `COMPLETED 或 ABORTED / INVALID / NOT_EVALUATED / COMPLETE 或 INCOMPLETE / NOT_RUN` | `INVALID_INPUT` | T2/T3 预检，T6 归因 | 不计入 |
| F-05 | 识别超时 | 业务时限 `VALID / FAIL / COMPLETE`；环境 `BLOCKED` | `VALID_FAILURE` 或 `INVALID_ENVIRONMENT` 或 `INFRA_ERROR` | T4 分流，T6 实测 | 业务超时计入，其余不计入 |
| F-06 | CrossTalk | `COMPLETED / VALID / FAIL / COMPLETE / PASS` | `VALID_FAILURE`（带 CrossTalk 标注） | T6（L4），T4 预演 | 计入 |
| F-07a | UnASR 首次失败 | `COMPLETED / VALID / FAIL / COMPLETE / PASS` | `VALID_FAILURE` | T6（L4） | 计入首次失败 |
| F-07b | UnASR 重试通过 | 新 attempt 五轴通过，`flaky_suspect=true` | 新 attempt 省略；首次保留 | T6（L4） | 首次按原分类；重试单列，不计入分母 |
| F-08 | 运行中重启 | `ABORTED / UNKNOWN / NEEDS_REVIEW / COMPLETE / NOT_RUN` | 省略（待定因） | T4 模拟，T6 观察 | 不计入，先定因 |
| F-09 | 重复执行 | 幂等返回首次结果；发生重复动作 `BLOCKED / NEEDS_REVIEW` | 幂等无新增；否则 `BLOCKED` | T1/T2 幂等，T4 重放，T5 真机 | 不计入 |
| F-10 | 人工喊测 | 仅 `human_note`，`business_verdict` 不得自动 PASS | 省略 | 人工记录 | 不计入 |

补充约束：

1. F-02 必须记录 FAR/FRR 的原始计数，`FAR = 误唤醒次数 / 负样本总数`、`FRR = 漏唤醒次数 / 正样本总数`，只报“唤醒成功”或百分比而不给分子分母视为证据不完整。
2. F-03 与 F-06 必须把“识别文本正确”和“设备执行成功”分开记录，A-04 的两个断言不得合并为一条。
3. F-07a/F-07b 是同一 `case_id` 的两个 `attempt`，`retry_of_attempt_id` 指向首次，首次证据不可覆盖。
4. F-10 可以补充主观体验，但永远不能单独构成正式 PASS，也不进入自动分母。

## 2. 逐场景执行卡

| ID | 前置条件 | Oracle（可判定断言） | 期望证据 | 失败分流 |
|---|---|---|---|---|
| F-01 | A-0 与 T5 通过；修订和样本规则已批准；`mode=formal`；能力 `listenai.capture/render` 与固件 `V038` 匹配；距离/音量/噪声在批准档位；无待 STOP、无残留占用 | 唤醒发生；响应可观察且与任务定义一致；TTFAB 不超任务阈值；无误唤醒 | 原始音频、COM3/COM4 串口日志切片、执行日志、manifest、Linux 复核记录 | 未唤醒或响应不符转 `VALID_FAILURE`；端点缺失或会话不可用转 `INVALID_ENVIRONMENT`；摘要不符转 `INVALID_EVIDENCE` |
| F-02 | 同上；负样本集在修订中声明并记录许可与来源；负样本类型至少含非唤醒词、静音、环境干扰三类 | 负样本不触发唤醒；误唤醒数不超任务阈值；每条负样本有独立 attempt | 负样本原始音频、串口日志、manifest、FAR 计数表 | 误唤醒转 `VALID_FAILURE`；负样本缺失或格式不可解码转 `INVALID_INPUT`；语料许可不明不得冻结 |
| F-03 | 唤醒与识别已成功；预期动作在 `expected_observable_result` 中已冻结；设备处于可执行态 | 识别文本正确但设备动作缺失或不符；两个断言分别留证 | 原始音频、设备日志切片、串口日志、执行日志、动作时间线 | 有效输入下动作未达预期为 `VALID_FAILURE`；无法判定动作是否发生转 `NEEDS_REVIEW`，不得猜 PASS |
| F-04 | 用例声明 `validity_conditions`；输入缺失、格式错误、参数越界或前置不成立任一命中 | 输入校验在派发前拒绝或 attempt 标 `INVALID`；不产生设备动作 | 输入校验记录、拒绝码、manifest、异常说明 | 统一 `INVALID_INPUT`；不得伪装成产品失败；不得计入 PASS/FAIL 分母 |
| F-05 | 有效输入已送达；任务级识别时限已批准；端点身份快照已采集 | 超时时刻与原因可区分：业务超时、端点异常、基础设施故障三者互斥 | 时间线、原始音频、执行日志、端点事实、对账记录（若为基础设施） | 业务超时 `VALID_FAILURE`；端点/会话异常 `INVALID_ENVIRONMENT`；仅对账确认的节点/传输/存储故障可判 `INFRA_ERROR` |
| F-06 | 多说话人或旁路音频条件已在用例中声明；CrossTalk 标注规则已批准；串扰源与设备距离记录 | 串扰发生且被标注；不得静默归为识别失败或环境失败；按任务定义判 FAIL 或 EXPECTED | 原始音频（含串扰声道）、串口日志、CrossTalk 标注、执行日志 | 任务定义下不达预期为 `VALID_FAILURE`；串扰源不可考或通道混叠无法区分转 `NEEDS_REVIEW` |
| F-07a | ASR 返回空结果或不可用结果；首次 attempt 尚未重试；重试预算已批准 | 首次结果被完整保留；`attempt_ordinal=1`；不因后续重试被覆盖 | ASR 输出、原始音频、执行日志、首次 manifest | 有效输入下 ASR 无结果为 `VALID_FAILURE`；若音频通道本身异常转 `INVALID_ENVIRONMENT` |
| F-07b | 首次失败已结案；新 attempt 使用同一 `case_id`/`case_version`；重试原因已记录 | 新 attempt 五轴全绿且 `flaky_suspect=true`；首次分类不变；报告同时列首次与重试 | 两次 attempt 的独立证据、重试原因、`retry_of_attempt_id`、复核记录 | 重试通过不得写成首次通过；重试用尽即按首次结果分类并转复核 |
| F-08 | 运行中发生普通重启（A 串口）或异常重启；重启前后时间线可对齐；设备身份未变 | 重启不得自动 PASS，也不得直接判产品 FAIL；先定因再归类；重启后设备需重新健康探测 | 重启前后串口日志、时间线、设备事实、执行日志、`draining` 记录 | 原因未定前 `validity=UNKNOWN`、`business=NEEDS_REVIEW`、不计入分母；确认输入/环境问题后按对应类归档 |
| F-09 | 同一 `job_id`/`attempt` 可重复送达；幂等键规则已冻结；设备动作时间线可观测 | 重复送达返回首次结果且无第二次设备动作；`attempt_ids` 无重复；审计链完整 | 回执链、幂等键记录、设备动作时间线、审计日志、去重统计 | 幂等即止，不新增 attempt；一旦发生重复动作，按 P0 处理，标 `BLOCKED` 或 `NEEDS_REVIEW`，不得以“结果相同”豁免 |
| F-10 | 人工喊测已录音或记录；来源、时间、操作者角色、关联 `run_id` 齐全 | 仅作支持证据；`business_verdict` 仍由 Linux 依证据判定 | 人工记录、来源声明、时间戳、关联 run、音频（若采） | 不产生自动 PASS；无关联 run 的记录不得引用 |

## 3. 正式分母规则

正式分母的唯一合法集合是同时满足下列条件的 attempt：

```text
run.mode == formal
AND attempt.evidence_origin == real_device
AND attempt.validity_status == VALID
AND attempt.evidence_status == COMPLETE
AND attempt.execution_status == COMPLETED
AND run.decision != NEEDS_REVIEW
AND run.decision != STOPPED
```

| 样本 | 是否计入 | 依据 |
|---|---|---|
| `mode=formal` 且 `VALID` 且证据 `COMPLETE` 且复核已运行 | 是 | 唯一合法正式分母 |
| `VALID_FAILURE`（VALID + FAIL + COMPLETE） | 是 | 有效失败必须计入，不能只报通过率分子 |
| `mode=smoke` | 否 | 烟测永不进入，T5 与 T6 必须不同 `run_id` |
| `mode=static` | 否 | 静态检查不是业务样本 |
| `evidence_origin=simulated` | 否 | 模拟证据只能支撑 L2 |
| `evidence_origin=replay` 或历史 run 结果再次计分 | 否 | 重放不得进入分母 |
| 自动回放作为正式执行方式新产生的 `real_device` 证据 | 是 | 属正式执行，不是历史重放 |
| `validity=INVALID` | 否 | `INVALID_INPUT` |
| `validity=BLOCKED` | 否 | `INVALID_ENVIRONMENT` 或 `BLOCKED` |
| 证据 `INCOMPLETE`/`CONFLICTED`/`UNVERIFIED` | 否 | 证据不完整不得计分 |
| `decision=STOPPED` | 否 | 停止不是业务失败 |
| `failure_class=INFRA_ERROR` | 否 | 仅对账确认后成立 |
| `decision=NEEDS_REVIEW` | 暂不计入 | 复核后再定 |
| 重试通过 | 首次按原分类；重试单列 `FLAKY_SUSPECT` | 不覆盖首次结果 |
| 人工喊测、演示数据、他人借用样本 | 否 | 无正式链路与身份绑定 |

派生与报告规则：

1. `formal_denominator_eligible` 只能由服务端派生，客户端与节点不得自行置真。
2. 分母按 attempt 计数、按 case 版本分组；跨 `case_version`、跨设备、跨固件不得只凭名称合并通过率。
3. 报告必须固定写明 `formal_denominator = 有效正式样本`，并同时给出分子分母：通过数、`valid-failure` 数、无效/阻塞/停止数量。
4. 无效、阻塞、停止、烟测、模拟、重放、基础设施故障只出现在排除项统计，不得混入通过率。
5. 重试通过必须单列，不得把重试分子加到首次分母上制造“首次通过率”。
6. 样本计划未在冻结修订中显式选定即返回 `SAMPLE_PLAN_UNDEFINED`，不得启动 T6。

## 4. TCL 专属阈值缺口

以下项目在 `phase4-acceptance-plan.md` §6.2 只有模板，没有 TCL 任务级批准值。未关闭前，F-01 至 F-09 只能写“阈值未定义”，不得产出正式 PASS。

| 缺口 | 影响场景 | 需要的批准内容 | 当前状态 |
|---|---|---|---|
| 唤醒词与正样本集 | F-01 | “小T小T”发音变体、距离档、音量档、噪声场景与样本数 | 未批准 |
| 负样本集 | F-02 | 负样本类型、数量、来源与许可；FAR 允许上限 | 未批准 |
| 通过率口径 | F-01/F-02/F-03 | 是否采用 `strict_zero_failure`（关键失败 0，最小 30 有效样本）或 `standard_95` | 未批准 |
| 正式样本量 | 全部 | `formal_small` 30、`formal_medium` 100、`formal_large` 300 三者选一 | 未批准 |
| TTFAB 阈值 | F-01/F-05 | 首次音频延迟口径（起点事件、终点事件、允许毫秒数） | 未批准 |
| 识别时限 | F-05 | 超时秒数，以及业务超时与环境超时的分界判据 | 未批准 |
| CrossTalk 定义 | F-06 | 串扰源数量、信噪比、距离、标注规则，以及判 FAIL 还是 EXPECTED | 未批准 |
| UnASR 重试预算 | F-07a/F-07b | `retry_minimal` 或 `retry_standard`（单 case 1、单 run 2），以及重试用尽后的归档路径 | 未批准 |
| 命令与预期动作清单 | F-03 | 每条命令的 `expected_observable_result` 与设备侧可观测点 | 未批准 |
| 重启分类 | F-08 | 普通重启与异常重启的判定阈值、允许次数、是否计入稳定性 | 未批准 |
| 端点身份 | F-01 至 F-09 | ListenAI Capture/Render 端点 ID、波特率 921600 的 COM3/COM4 映射快照与漂移处理 | 未批准 |
| 设备与固件范围 | 全部 | 是否只认 `TCL001` + `V038`；等价设备条件与验证记录 | 未批准 |
| 存储与预算 | 全部 | D: 保护阈值、单 run 预算（时长/容量）、音频保留策略 | 未批准 |
| 角色与窗口 | 全部 | 执行人、复核人、签字人与验收时间窗 | 未指定 |

补充说明：COM5、COM7 当前不使用；硬件复位存在但不作为常规动作，重启类场景默认走 A 串口普通重启，任何偏离必须在修订中声明。

## 5. 非声明

1. 本文未执行任何 T1 至 T6 场景，无任何 PASS、FAIL 或覆盖率结论。
2. 本文不表示 TCL 适配已开始，也不表示 A-0、L3、L4、L5 通过。
3. 本文不冻结契约、阈值、样本量或证据 schema；P4-06 的判定规则和 P4-08 的冻结结论仍待完成。
4. 本文不授权实现、真机测试、部署、发布或对外承诺。
