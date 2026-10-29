# P4-06 判定与证据规则

> 状态：`DRAFT · NOT FROZEN · NOT EXECUTED`
> 归属：`.omo/plans/phase3-6-execution.md` 第 13 项；`docs/delivery/phase4-acceptance-plan.md` §7
> 输入：`phase4-acceptance-plan.md` §3/§4/§7/§9、`docs/contracts/evidence-verdict.md` §3/§5/§6/§9/§12/§13/§14/§15/§16、`docs/contracts/domain.md` §14/§15
> 边界：只固化"怎么判、凭什么判"。不执行测试，不产生 PASS，不改代码、契约、迁移、计划或主计划勾选。

## 0. 判读规则

1. 本文是判读规范，不是判定结果；当前没有任何 run、manifest、verdict 或复核记录。
2. 判定权唯一属于 Linux 判定服务。节点、UI、报告、Lead 会话只提供事实或展示，不得写最终结论。
3. 任一必需前置无法验证即 fail closed，落到待核验、阻塞、无效或需复核，不允许"暂按通过"。
4. "禁止解释"具有阻断效力：出现该解释即判该条 FAIL，即使表面行为已发生。一个 `run_id` 只有一个 `mode`，跨层、跨设备、跨 revision 的结论不得合并。

## 1. 五轴、正式 PASS 与 fail-closed

### 1.1 五轴允许值与写入方

| 轴 | 允许值 | 写入方 | 常见误读 |
|---|---|---|---|
| `execution_status` | `NOT_STARTED` / `RUNNING` / `COMPLETED` / `ABORTED` / `SKIPPED` | Linux，基于节点事实 | 执行完成即业务通过 |
| `validity_status` | `VALID` / `INVALID` / `BLOCKED` / `UNKNOWN` | Linux | 无效样本算作产品失败 |
| `business_verdict` | `PASS` / `FAIL` / `EXPECTED` / `WARN` / `NEEDS_REVIEW` / `NOT_EVALUATED` | Linux | 业务轴即最终判定 |
| `evidence_status` | `COMPLETE` / `INCOMPLETE` / `CONFLICTED` / `UNVERIFIED` | Linux | 用 `UNKNOWN` 表示未核验 |
| `verification_status` | `PASS` / `FAIL` / `NOT_RUN` | Linux 独立复核 | `NOT_RUN` 视为默认通过 |

`verdict.axes.evidence_status` 不得写 `UNKNOWN`：未核验写 `UNVERIFIED`，缺失写 `INCOMPLETE`，冲突写 `CONFLICTED`。展示层占位值不进入判定轴。

### 1.2 正式 PASS 的精确元组

十一项同时成立才算正式 PASS，缺一即降级，不得"轴一致"就宣称通过：

```text
execution_status = COMPLETED          mode         = formal
validity_status  = VALID              decision     = PASS
business_verdict = PASS               formal_pass  = true
evidence_status  = COMPLETE           failure_class = none
verification_status = PASS            denominator.eligible = true
denominator.formal_denominator = true
```

配套 `pass_preconditions` 十一项必须全真：批准有效、边界冻结、正式模式、执行完成、样本有效、业务通过、必需证据完整、摘要通过、Linux 复核通过、无阻断异常、分母有效。前五项回答"能否开始、样本是否有效"，后六项回答"结论是否成立"，两类都要查。

### 1.3 派生顺序（先命中先返回）

```text
非 formal → NOT_APPLICABLE / formal_pass=false
批准、边界、租约、epoch 不符 → BLOCKED
execution_status=NOT_STARTED → NOT_EVALUATED
安全停止或人工停止 → STOPPED
节点、传输、存储基础设施故障 → BLOCKED / infra-error
validity=INVALID → INVALID / invalid-input
validity=BLOCKED → BLOCKED / invalid-environment
evidence!=COMPLETE 或必需摘要、关联失败 → BLOCKED / invalid-evidence
verification!=PASS 或存在未处置阻断异常 → NEEDS_REVIEW
全部前置成立且 business=PASS → PASS / formal_pass=true
VALID + FAIL + COMPLETE → FAIL / valid-failure
其他 → NEEDS_REVIEW
```

### 1.4 fail-closed 情形

| 情形 | 必须落到 | 不得做 |
|---|---|---|
| 缺批准、批准快照不匹配、边界未冻结 | `BLOCKED` | 先执行后补批准 |
| 租约冲突、`lease_epoch` 不符、占用冲突 | `BLOCKED` | 换新 ID 绕过幂等 |
| `mode` 缺失、未知或与层级不符 | `BLOCKED` | 按最乐观值解释为 formal |
| 必需证据缺失、摘要不符、来源或关联冲突 | `BLOCKED / invalid-evidence` | 用其他 run 的证据替代 |
| 必需日志不可读 | `UNVERIFIED` 或 `INCOMPLETE` | 猜内容、标 PASS |
| `verification_status=FAIL` 或 `NOT_RUN` | `NEEDS_REVIEW` | 口头宣布通过 |
| 存在未处置阻断异常 | `NEEDS_REVIEW` | 只看业务结果忽略异常 |
| 枚举、schema 版本未知 | `NEEDS_REVIEW` 或拒绝消费 | 猜测为成功 |
| 清理失败或占用不确定 | `quarantined` + `NEEDS_REVIEW` | 释放后继续派发 |

## 2. 证据：期望、收到、已核验

### 2.1 三态必须分开记录

| 态 | 判据 | 能证明 | 不能证明 |
|---|---|---|---|
| 期望（expected） | 冻结 profile 的 `evidence_requirements` 声明了证据类与角色 | 本次运行应产出什么 | 该证据确实存在 |
| 收到（received） | 状态为 `declared` / `uploading` / `partial` / `complete` | 有字节到达、有来源声明 | 内容完整、摘要正确、关联成立 |
| 已核验（verified） | `state=verified` 且 Linux 重算通过五条件 | 可作为判定输入 | 业务结论正确 |

`complete` 只表示字节数完整，不表示已核验；只有 `verified` 可计入"必需证据已存在"。部分上传是 `partial`，不是失败，但不得计入正式分母；超期后转 `INCOMPLETE` 并按 `BLOCKED / invalid-evidence` 处理。

### 2.2 "已核验存在"的五条件

五项条件缺一不可：`state=verified`；`content_digest` 与 Linux 重算一致；`size_bytes` 与存储对象一致；`provenance` 完整且 `task_id/revision_id/run_id/node_id/device_identity/lease_epoch` 与运行一致；必需证据的 `locator` 可解析且内容可取回（本地内容寻址副本，或已验证的按需读取记录）。`declared`、`uploading`、`partial`、`complete` 四态一律不计。

### 2.3 摘要与 manifest 口径

| 对象 | 字段 | 覆盖范围 | 关键约束 |
|---|---|---|---|
| 原始证据 | `content_digest` | 原始字节，SHA-256，`sha256:` 前缀共 71 字符 | 不转换换行、不裁剪、不重编码 |
| 结构化证据 | `content_digest` | RFC 8785 JCS 规范化后的 UTF-8 字节 | 前置域分隔 `noahsark/v1/<type>\n` |
| manifest | `manifest_digest` | 除 `manifest_digest` 与 `signatures` 外全部字段 | `completeness=COMPLETE` 时必须非 null |
| 清理回执 | `receipt_digest` | 除 `receipt_digest` 与 `signature` 外全部字段 | 摘要不符即拒绝释放 |
| 判定 | `verdict_digest` | 除 `verdict_digest` 外全部字段 | 展示层字段不参与 |
| 复核记录 | `verification_digest` | 除自身与 `signature` 外全部字段 | 签名载荷须含 `manifest_digest` |

消费 manifest 前按序校验：schema、`manifest_digest` 重算、关联、路径安全、必需证据摘要与大小复算、必需集一一对应、分母（`mode=smoke` 不得出现在 `formal` 内）、阻断异常处置、复核引用。任一步失败，`evidence_status` 不得为 `COMPLETE`，`decision` 不得为 `PASS`。

### 2.4 冲突与去重

| 情形 | 结果 | 处置 |
|---|---|---|
| 同 `evidence_id` + 同摘要 + 同大小 | 幂等无操作 | 返回首次登记，不重复计数 |
| 同 `evidence_id` + 不同摘要 | `conflicted` | 保留旧项，新内容另立 `supersedes` 候选，禁止原地覆盖 |
| 不同 `evidence_id` + 同摘要 | 允许 | blob 去重，逻辑角色分别计算 |
| 节点摘要与 Linux 重算不符 | `conflicted` | 保留双方摘要与发现时间，不得用节点值覆盖重算值 |
| 引用旧 `lease_epoch` / 旧 `revision_id` / 旧 `run_id` 的证据 | `conflicted` | 拒绝并入当前运行 |
| 重试产生新 `attempt` | 新证据集 | 首次结果不合并、不覆盖，重试单列 `FLAKY_SUSPECT` |

## 3. 释放、分母与 PASS 的边界

### 3.1 释放前置条件

| ID | 前置 | 证据来源 |
|---|---|---|
| R-01 | 本地停止已确认，或运行正常完成且无残留设备动作 | `cleanup_receipt.steps`、`execution_log` |
| R-02 | 回执存在、摘要或签名可验证，`cleanup_status ∈ {completed, completed_with_warnings, not_required}` | `receipt` |
| R-03 | 占用对账完成：位置确认、待处理 STOP 清空、无其他租约、证据积压已登记 | `device-occupancy.reconciliation` |
| R-04 | 设备安全：进程终止、端点释放、设备复位或空闲 | `cleanup_receipt.resources` |
| R-05 | 节点可达或现场确认可再分配；离线不得确认释放 | `communication_state`、人工记录 |

domain 三布尔投影：`local_stop_confirmed` ← R-01，`safe_cleanup_done` ← R-02 ∧ R-04，`occupancy_reconciled` ← R-03；R-05 不进投影但确认释放时仍需满足。释放不要求 GB 级日志上传、`evidence_status=COMPLETE`、归档完成或判定已作出。释放结论写入 `device-occupancy.release`，不写入 `verdict`。

### 3.2 释放不等于通过

- `release_state=released` 只说明设备可再分配，不反推证据完整或判定通过；未释放也不反推 `decision!=PASS`，缺回执场景下 PASS 与 `held_pending_cleanup` 可以并存。
- 清理失败不是 `invalid-evidence`，也不是业务 FAIL，而是安全异常，触发隔离与 `NEEDS_REVIEW`。
- 报告必须同屏展示 `decision` 与 `release_state`，不得合并为单一"通过/完成"。

### 3.3 分母资格

| 样本 | 进入正式分母 | 说明 |
|---|---|---|
| `formal` + `VALID` + 必需证据 `COMPLETE` + 复核已运行 | 是 | 唯一合法正式样本 |
| `valid-failure`（VALID + FAIL + COMPLETE） | 是 | 有效失败必须计分 |
| `smoke`、`static` | 否 | 烟测与静态检查永不进入 |
| `INVALID`、`BLOCKED` | 否 | 输入或环境无效 |
| `INCOMPLETE`、`CONFLICTED`、`UNVERIFIED` | 否 | 证据不完整不得计分 |
| `STOPPED`、`infra-error`、`NEEDS_REVIEW` | 否，后者待复核 | 停止、故障、未定论都不是业务结果 |
| 模拟、历史重放、演示数据 | 否 | 不得拼入 |
| 重试通过 | 首次按原分类 | 首次结果保留，重试单列 |

唯一键为 `run_id + case_id + attempt`；重复上传或重试不得让同一样本被计数两次。跨设备结果在等价条件未批准时按设备分别计算。

## 4. 禁止解释清单

| 禁止解释 | 为什么错 | 正确口径 |
|---|---|---|
| 已收到等于已核验 | `complete` 只证明字节数 | 以 Linux 重算后的 `verified` 为准 |
| 设备已释放等于 PASS | 释放只回答"可否再分配" | 释放与判定两平面分别记录 |
| PASS 必须已释放 | 缺回执时 PASS 与 `held` 可并存 | 释放是独立结论 |
| 烟测可进正式分母 | 烟测独立 `run_id`，只证明链路可跑通 | 烟测 `decision=NOT_APPLICABLE`，只有 `mode_outcome` |
| 节点自报 PASS 可作判定输入 | 节点只报事实，`used_for_decision=false` | Linux 重算并独立复核 |
| `business_verdict=PASS` 即通过 | 业务轴只是五轴之一 | 需十一项精确元组 |
| `verification_status=NOT_RUN` 视为通过 | 复核是必要条件 | `NOT_RUN` 只能落 `NEEDS_REVIEW` |
| 缺清理回执等于证据不完整 | 缺回执只影响释放确认 | 证据完整性按必需集独立计算 |
| 远程按需读取等于备份或归档 | 读取只形成核验记录，节点丢失即丢失 | 归档状态单独跟踪 |
| 归档不可用可撤销既有判定 | 归档只影响保留与删除 | 判定不回溯改变 |
| 用 L2/T4 证据声称 L4/T6 完成 | 层级隔离，模拟不证明真机 | 逐层升级，缺层即 BLOCKED |
| 验收通过等于可发布 | 样本级、范围级、运营级是三个决定 | 分别记录，分别授权 |

## 5. 当前缺口

| 缺口 | 影响 | 关闭条件 | 状态 |
|---|---|---|---|
| 契约未冻结，规则集版本绑定未固化 | 字段、枚举不能作为实现依据；无法证明判定用了哪版 oracle | 评审通过并记录版本、哈希、范围与 `rule_set_digest` | 未关闭 |
| Q-EV-01 必需证据切片粒度未冻结 | 无法全局固定必需集 | 任务级 `evidence_requirements` 冻结 | 未关闭 |
| Q-EV-02 回执签名强度未定 | `verified` 与防伪边界不清 | 节点身份契约给出算法与证书链 | 未关闭 |
| Q-EV-08 `NEEDS_REVIEW` 超时与升级未定 | 分母长期悬空 | 阈值文档给出时限与升级路径 | 未关闭 |
| 上传超期与时钟漂移阈值未采用 | 超期判定与时间可信度无依据 | 采用 TH-E-08、TH-C-01/02 并写入冻结包 | 未关闭 |
| 证据存储与归档后端未落地 | 只能声明语义，不能验收目录与保留 | 存储、容量、归档路径确定 | 未关闭 |
| 设备等价条件未批准 | 跨设备只能隔离计分 | 任务级等价值与验证记录 | 未关闭 |
| 上游 P4-01 追溯与 P4-05 设备矩阵证据文未产出 | 本规则缺少 AC 与设备侧锚点 | 补齐两份证据文并回填引用 | 未关闭 |

本文不声明任何 PASS、验收通过、发布或冻结。规则是否可执行，需在契约冻结、样本批准与首次演练后才能判定。
