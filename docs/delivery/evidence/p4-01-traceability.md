# P4-01 需求到 AC-1..AC-14 追溯

> 状态：DRAFT · 追溯草案，不是冻结件
> 归属：`.omo/plans/phase3-6-execution.md` 第 8 项；`docs/delivery/phase4-acceptance-plan.md` §2 的 P4-01 落点
> 输入：`00-baseline/noahsark-v0.0.1-requirements-baseline.md`、`docs/delivery/ui-screen-specification.md` §4/§5、`docs/contracts/domain.md` §4 至 §18、`docs/contracts/evidence-verdict.md` §2 至 §16、`02-delivery/noahsark-v0.0.1-test-strategy.md` §2/§4/§8
> 边界：只建立追溯关系。不改代码、契约、设计、计划；不执行测试或命令；不采集证据；不声称任何 AC 已满足、任何 T/L 层已通过、任何门已放行。

## 0. 判读规则

1. AC 编号与措辞取 `ui-screen-specification.md` §4。该表是当前唯一逐条编号 AC-1..AC-14 的来源，本文件不重新定义 AC。
2. REQ-01..REQ-14 不是需求基线原文编号。基线只按 §1..§16 分节，REQ 编号由 `phase4-acceptance-plan.md` §2.3 派生。本表两列并给，避免把派生编号当成已批准编号。
3. 模块列用 `phase4-acceptance-plan.md` §2.1 的 M-01..M-15 服务边界编号。它与 `.omo/drafts/01-design/noahsark-v0.0.1-module-design.md` 的 M-01..M-21 编号同名不同义，登记为 §4 G1。本文件不合并两套编号。
4. API 与事件列全部是候选标识。`docs/contracts/README.md` 明确契约不描述 API 路由，`phase4-acceptance-plan.md` §0 也声明路径为候选。冻结前不得当成已实现接口。
5. T 层取 `ui-screen-specification.md` §4 与 `phase4-acceptance-plan.md` §2.2 的并集。两源不一致处逐条列在 §3，本文件不静默择一。
6. L 层按来源原文记录。来源只写 L5 而并集含 T6 时，按 `evidence-verdict.md` §4.2/§4.4 标注“T6 隐含 L4”，不把隐含关系改写成来源已声明。
7. 证据列只列判定必需项，不列可选诊断。证据类名取 `evidence-verdict.md` §3.1 十类；审批快照、verdict、verification record 是结构化记录，不冒充证据类。
8. 本文件说“有证据”只表示存在**应采集的证据类型**，不表示该证据已采集、已核验或可复算。

## 1. AC-1..AC-14 主追溯表

| AC | 验收要点 | 需求（派生 REQ / 基线） | 模块 | API / 事件（候选） | UI 路由 / 族 | 必需证据 | T 层 | L 层 |
|---|---|---|---|---|---|---|---|---|
| AC-1 | 三入口归一、人工审阅、不可变冻结、一次有效批准；同人可批 | REQ-01/02/04；基线 §1/§4/§15-1 | M-01/02/03/12 | `POST /api/v1/intake/drafts`；`POST /api/v1/tasks/{task_id}/approvals`；`GET /api/v1/tasks/{task_id}/revisions`；`approval.recorded` | IN-01..03、TK-03（§2.2、§2.4；G0/G1） | `manifest`、`human_note`（审阅）；approval 快照含 `revision_content_digest`/`scope_digest` | T2/T3/T5/T6 | L0/L1/L5（T6 ⇒ L4） |
| AC-2 | 恰一个 lead、会话可恢复、任务卡独立、stale 告警、未知不编造 | REQ-02/07/08；基线 §2.3/§7/§8/§15-2 | M-09/10/13 | `GET /api/v1/tasks/{task_id}/overview`；`GET /api/v1/tasks/{task_id}/live`；`taskcard.freshness.changed` | MC-01、TK-02（§2.1、§2.3） | TaskCard 前后快照、`execution_log`；freshness 事件记入 `anomaly_event` | T3/T4 | L2/L5（缺 L4） |
| AC-3 | static/smoke/formal 分离；烟测不入分母；逐设备、逐用例结果 | REQ-09；基线 §9/§15-3 | M-04/06/07/14 | `GET /api/v1/runs`；`GET /api/v1/runs/{run_id}`；`denominator.rebuilt` | TK-05、RN-01..03（§2.5；G2/G4/G5） | 三类 run 的 `execution_log`、`manifest`、`receipt`；分母表 | T1/T4/T6 | L2/L4 |
| AC-4 | invalid-input/invalid-environment/invalid-evidence/阻塞/valid-failure 分类；缺证据 fail closed | REQ-05/10；基线 §5/§10/§15-4 | M-07/14 | `GET /api/v1/verdicts`；`GET /api/v1/evidence`；`verification.recorded` | TK-04、TK-06、EV-03（§2.3、§2.7、§2.8） | `manifest`；verdict 记录；verification record | T1/T4/T6 | L2/L4 |
| AC-5 | 设备替代受批准等价条件约束；记录实际设备与切换原因；结果隔离 | REQ-06/10；基线 §6/§10/§15-5 | M-05/15 | `GET /api/v1/devices`；`GET /api/v1/devices/{device_id}`；`device.substituted` | DV-01..03、RN-01（§2.5、§2.6；G3） | 替代批准与切换原因（`human_note`/`anomaly_event`）；分设备 `execution_log`/`manifest` | T3/T4/T5/T6 | L2/L4 |
| AC-6 | 范围变化同 task 派生新修订；旧修订与旧证据不变且不并入 | REQ-03/06/07；基线 §6/§15-6 | M-02/04/09 | `GET /api/v1/tasks/{task_id}/revisions`；`GET /api/v1/tasks/{task_id}/runs`；`revision.derived` | TK-03、TK-05（§2.3、§2.5） | 修订谱系与 `content_digest`；差量 approval；旧 run 的 `manifest` 归属 | T1/T3/T4 | L2/L5（缺 L4） |
| AC-7 | 默认报告仅摘要；原始音频/日志受限；30 天到期不自动删除 | REQ-11/12；基线 §11/§12/§15-7 | M-08/12 | `GET /api/v1/reports/{report_id}`；`POST /api/v1/evidence/{evidence_id}/access`；`retention.marked` | RP-02、EV-01/02、ST-04（§2.7、§2.8、§2.11） | 访问审计记录；`archive_state`/保留记录；报告投影 | T3/T4 | L2/L5（缺 L4） |
| AC-8 | 知识候选需人工审阅，不自动推广；第二任务可复用且保留来源与适用性 | REQ-12；基线 §12/§15-8 | M-11 | `POST /api/v1/knowledge/{knowledge_id}/review`；`knowledge.reused` | KN-01..03、TK-09（§2.9；G7） | 候选与审阅记录（`human_note`）；复用 provenance | T3/T4/T6 | L5（T6 ⇒ L4） |
| AC-9 | 自动 PASS 只来自自动回放与客观可追溯证据；人工喊测只作补充 | REQ-05/10/11/14；基线 §5/§11/§14/§15-9 | M-07/08 | `GET /api/v1/verdicts`；`verdict.source.labeled` | TK-07、EV-03、RP-02（§2.8） | verdict 来源标注；`raw_audio`、`device_log`、`serial_log`；`human_note` 单列 | T1/T4/T6 | L2/L4 |
| AC-10 | 记录、报告、UI 与后端权威状态一致；不以未实现能力作声明 | REQ-08/13/14；基线 §13/§15-10 | M-10/13 | `GET /api/v1/mission`；`GET /api/v1/audit`；`projection.rebuilt` | MC-01、TK-02、RN-02、AU-01（§2.1、§2.3、§2.5、§2.10） | 一致性核对表（`human_note`/`manifest`）；投影重建日志；审计记录 | T2/T4/T6 | L5（T6 ⇒ L4） |
| AC-11 | 断线后已启动冻结运行继续；设备保持占用；不重派/重播/重复采样 | REQ-06/13；基线 §6/§13；测试策略 §3.8 | M-05/06 | `heartbeat.offline`；`occupancy.held`；`run.continued` | MC-01、RN-01、TK-08、DV-01/02（§2.1、§2.5、§2.6） | 心跳时间线（`anomaly_event`）；占用快照；`execution_log` 证明运行继续 | T3/T4/T5 | L2/L3 |
| AC-12 | STOP-first 重连：待 STOP → 停止后续动作 → 补传 → 去重 → 对账 → 恢复领取；旧 epoch 不改当前运行 | REQ-06/13；基线 §6/§13；测试策略 §3.8 | M-05/06/13 | `POST /api/v1/node/poll`；`reconnect.reconciled`；`security.epoch.rejected` | AU-03、RN-02、DV-01（§2.5、§2.6、§2.10） | 对账 `execution_log`；STOP 顺序记录；去重统计；epoch 拒绝审计 | T3/T4/T5 | L2/L3 |
| AC-13 | 释放只依赖本地停止、安全清理、占用对账；释放≠判定；证据/判定/释放分记 | REQ-06/10；基线 §6/§10；evidence-verdict §12/§13 | M-05/07/08 | `POST /api/v1/devices/{device_id}/release-requests`；`POST /api/v1/runs/{run_id}/stop-requests`；`cleanup.receipt`；`verdict.recorded` | DV-02、RN-02、TK-07、EV-02（§2.5..§2.8；G6） | `receipt`；占用对账记录；`execution_log`；verdict；`evidence_status` 独立 | T1/T3/T4/T6 | L2/L4 |
| AC-14 | 恢复顺序固定；未演练不得声称 RPO/RTO | REQ-13；基线 §13；测试策略 §3.8 | M-13 + M-07 | `POST /api/v1/admin/restore-drill`；`restore.drill.recorded` | AU-03、ST-04（§2.10） | 演练报告（`human_note`）；对账差异；时间记录；无演练则无 RPO/RTO 证据 | T3/T6 | L2/L4 |

> 表中 14/14 个 AC 同时具备至少一个证据类型与至少一个 T 层；统计见 §2，来源冲突见 §3，未决缺口见 §4。

## 2. 覆盖核对

### 2.1 逐 AC 闭合检查

| AC | 必需证据（类型计数） | T 层 | 是否同时具备证据与测试层 |
|---|---|---|---|
| AC-1 | `manifest`、`human_note` + approval 记录（2+1） | T2/T3/T5/T6 | 是 |
| AC-2 | `execution_log`、`anomaly_event` + TaskCard 快照（2+1） | T3/T4 | 是 |
| AC-3 | `execution_log`、`manifest`、`receipt`（3） | T1/T4/T6 | 是 |
| AC-4 | `manifest` + verdict/verification 记录（1+2） | T1/T4/T6 | 是 |
| AC-5 | `human_note`、`anomaly_event`、`execution_log`、`manifest`（4） | T3/T4/T5/T6 | 是 |
| AC-6 | `manifest` + revision/approval 记录（1+2） | T1/T3/T4 | 是 |
| AC-7 | `human_note`、`execution_log` + 访问/保留审计（2+2） | T3/T4 | 是 |
| AC-8 | `human_note`、`manifest`（2） | T3/T4/T6 | 是 |
| AC-9 | `raw_audio`、`device_log`、`serial_log`、`human_note` + verdict 记录（4+1） | T1/T4/T6 | 是 |
| AC-10 | `execution_log`、`manifest`、`human_note` + 审计记录（3+1） | T2/T4/T6 | 是 |
| AC-11 | `anomaly_event`、`manifest`、`execution_log`（3） | T3/T4/T5 | 是 |
| AC-12 | `execution_log`、`anomaly_event`、`receipt` + 审计记录（3+1） | T3/T4/T5 | 是 |
| AC-13 | `receipt`、`execution_log`、`manifest` + verdict 记录（3+1） | T1/T3/T4/T6 | 是 |
| AC-14 | `human_note`、`execution_log`、`manifest`（3） | T3/T6 | 是 |

核对结果：证据覆盖 14/14，测试层覆盖 14/14，没有孤立 AC，也没有只写需求、没有任何证明路径的条目。此处只核对结构完整性，不评价证据质量。

### 2.2 T 层分布

| T 层 | 覆盖 AC | 数量 |
|---|---|---|
| T1 单元 | AC-3、AC-4、AC-6、AC-9、AC-13 | 5 |
| T2 契约 | AC-1、AC-10 | 2 |
| T3 集成 | AC-1、AC-2、AC-5、AC-6、AC-7、AC-11、AC-12、AC-13、AC-14 | 9 |
| T4 模拟 E2E | AC-1 至 AC-14 | 14 |
| T5 真机烟测 | AC-1、AC-5、AC-11、AC-12 | 4 |
| T6 正式验收 | AC-1、AC-3、AC-4、AC-5、AC-8、AC-9、AC-10、AC-13、AC-14 | 9 |

两个薄弱点必须登记，不能当作已覆盖：T2 只覆盖 2 个 AC，契约类证据集中在 AC-1/AC-10；T5 只覆盖 4 个 AC，AC-3 的 smoke 与 formal 边界没有真机烟测层落点（§4 G6）。

### 2.3 判定口径核对

1. 五轴不折叠：AC-4、AC-9、AC-13 的证据列都要求 verdict 与 verification 分记，符合 `domain.md` §14 与 `evidence-verdict.md` §14.1。
2. 正式 PASS：只有 AC-1/3/4/5/8/9/10/13/14 的 T6 能提供正式样本；AC-2/6/7/11/12 的 T 层不含 T6，不得外推正式 PASS。
3. 烟测隔离：AC-3 明确要求三类 run 的独立 `execution_log`，对应 `evidence-verdict.md` §4.1 与 §14.5。
4. 释放独立：AC-13 把 `receipt`、占用对账、`evidence_status`、verdict 分列，符合 `domain.md` I-10/I-11 与 `evidence-verdict.md` §12.3/§13.4。
5. 旧证据隔离：AC-6 要求旧 run 的 `manifest` 归属，对应 `domain.md` R-3/I-13。
6. 层级外推禁止：L2 证据不得支撑 L3..L5；本表未把任何 L2 条目写成 L3 以上结论。

## 3. 两源 T 层差异

`ui-screen-specification.md` §4 与 `phase4-acceptance-plan.md` §2.2 对 14 个 AC 中的 10 个给出不同 T 层。本文件取并集，不判优劣；收敛由 P4-02 负责，冻结由 P4-08 负责。

| AC | ui-screen-spec §4 | phase4-plan §2.2 | 本文件取值 |
|---|---|---|---|
| AC-1 | T2/T3/T5 | T2/T6 | T2/T3/T5/T6 |
| AC-4 | T1/T4 | T1/T4/T6 | T1/T4/T6 |
| AC-5 | T3/T5/T6 | T4/T6 | T3/T4/T5/T6 |
| AC-6 | T1/T3 | T3/T4 | T1/T3/T4 |
| AC-8 | T3/T4 | T6 | T3/T4/T6 |
| AC-9 | T1/T4/T6 | T4/T6 | T1/T4/T6 |
| AC-10 | T2/T4 | T4/T6 | T2/T4/T6 |
| AC-11 | T3/T4/T5 | T4/T5 | T3/T4/T5 |
| AC-12 | T3/T4/T5 | T4/T5 | T3/T4/T5 |
| AC-13 | T1/T3/T6 | T4/T6 | T1/T3/T4/T6 |

AC-2、AC-3、AC-7、AC-14 两源一致，不单列。

## 4. 缺口与未决

| # | 缺口 | 影响 | 解除条件 |
|---|---|---|---|
| G1 | 模块编号同名不同义：`phase4-acceptance-plan.md` §2.1 的 M-01/04/05/07 与 `module-design.md` 的 M-01/04/05/07 指向不同职责 | 主表“模块”列在跨文档引用时会被误读 | P4-02 指定唯一编号源，或在表头固定引用版本 |
| G2 | REQ-01..REQ-14 不是基线原文编号，基线只有 §1..§16 与 §15 的十项验收场景 | 需求追溯指向派生索引，不是已批准编号 | 在 P4-08 记录派生映射，或回写基线编号 |
| G3 | 10/14 个 AC 的 T 层两源不一致，见 §3 | 同一 AC 可被不同执行者按不同层级取证 | P4-02 收敛并给出命令与证据格式 |
| G4 | UI 落点两源不一致：AC-4（UI §4 为 TK-04/TK-06/EV-03，P4 为 TK-07/EV-03）、AC-10（P4 写“全域”）、AC-13（P4 多列 TK-07/EV-02）等 | 证据采集者可能漏掉一个强制屏幕 | P1-04 路由 manifest 与 P4-02 对齐后回写 |
| G5 | AC-2/AC-6/AC-7/AC-10 声明 L5，但 T 层不含 T6；`evidence-verdict.md` §4.2 要求 L5 含 L4 全部证据 | L5 无法成立，属于层级越级声明 | 补 T6，或把 L5 降为 L2 并说明理由 |
| G6 | AC-3 的 T 层无 T5：static/smoke/formal 分离只在 T4 模拟与 T6 正式出现 | 真实烟测与正式采样的边界没有被 AC-3 直接证明 | P4-02 为 AC-3 增加 T5，或在 AC-3 说明由 AC-11 承载 |
| G7 | AC-8（知识）、AC-10（审计查询/投影）、AC-14（恢复演练）在 `domain.md` 与 `evidence-verdict.md` 中没有字段级契约 | 证据结构无法校验，只能引用 UI 规格 §2.9/§2.10 与测试策略 §4.5 | P0-07 交付知识/报告/审计契约 |
| G8 | API、事件名均为候选；契约明确不定义路由 | 主表接口列不能作为实现或测试断言 | 契约冻结后由 P2-03 替换为冻结值 |
| G9 | AC-5 的设备等价字段未定（`domain.md` Q-08） | 无法构造“已批准等价条件”的替代证据 | P0-10 或任务级等价批准流程 |
| G10 | AC-7 的归档路径与保留后端未定（ADR-006 / G-EVIDENCE 未关闭） | 只能证明“到期不删”，不能证明归档与删除边界 | 关闭 ADR-006，或声明保留后端待定 |
| G11 | T6 的样本量、阈值、重试与预算未批准（基线 §16、测试策略 §10） | AC-1/3/4/5/8/9/10/13/14 的 T6 证据无法完整 | 任务级冻结样本规则与阈值 |
| G12 | `docs/delivery/evidence/phase4/**` 目录尚未建立，P3-05 §4.1 的 `<level>/<ac-id>` 命名没有实例 | 本表无法指向任何实际证据位置 | W10 或 P6 启动时按 P3-05 §4.1 建目录与模板 |
| G13 | AC-14 无恢复演练记录，也无 RPO/RTO 数值目标 | 只能记录“未演练”，不能写任何恢复指标 | P6-06 演练并登记实测值 |
| G14 | AC-10 的“UI 与后端一致”没有机器可校验的投影契约与容差 | 一致性只能靠人工核对表 | P0-07 投影契约 + P5-W7 投影重建比对 |

## 5. 边界与变更记录

- 本文件未执行任何测试、命令或数据采集；未创建 `phase4` 证据目录；未修改契约、设计、代码、计划，未勾选主计划。
- 事实源版本：需求基线 V0.0.1（2026-10-27 批准）；UI 屏幕规格 v0.2（2026-10-29 候选）；domain v1.1-candidate；evidence-verdict v1.1-candidate；测试策略 v2.2 评审同步稿。
- 后续入口：P4-02 收敛 T/L 与命令；P4-06 定义判定与证据规则；P4-08 评审冻结。本文件不得单独作为验收依据。
- 变更记录：v0.1（2026-10-29）建立 AC-1..AC-14 到需求、模块、候选 API、UI 路由、证据、T 层、L 层的追溯；登记 14 项缺口；未声称任何 AC、T 层或 L 层已通过。
