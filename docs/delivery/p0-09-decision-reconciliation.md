# P0-09 决策登记册对账（Decision Reconciliation）

> 状态：对账完成；**不是批准记录**，不构成生产冻结、实现、测试、部署或发布授权。
> 对账对象：`.omo/drafts/05-decisions/noahsark-v0.0.1-decision-register.md`（v2.1，263 行，2026-10-27/28 快照）。
> 对账日期：2026-10-29 08:26 CST（Asia/Shanghai）。
> 输入证据：P0-04..P0-08 候选契约为 `frozen-candidate v1`，`phase0-contract-remediation-verification.md` 记录 35/35 JSON Schema 通过；P0-03、P0-10 为限定范围 post-fix **PASS**；`environment-inputs.md` 为 85 条（20 known / 14 placeholder / 51 unknown）。
> 操作边界：只新增本文件与登记册末尾对账注记；未修改登记册既有行/旧状态，未改产品代码、`docs/v2/`、`openspec/`、`docs/contracts/`、`.omo/plans/`、`.omo/boulder.json`、`plan.md`、`docs/ssh.txt`；未提交、未推送、未联网。
> 重要口径：`confirmed-for-planning` 仅表示“可用于后续规划/设计”，**不表示用户已批准或已生产冻结**。P0-04..P0-08 契约仍为候选。

---

## 1. 分类定义

| 分类 | 含义 | 处理规则 |
|---|---|---|
| `confirmed-for-planning` | 已被需求基线、已确认决定或候选契约承接，可用于规划与设计 | 不重复决策；实现前仍需对应阶段评审 |
| `superseded` | 旧登记/旧草案口径已被更新决定替代 | 旧文保留为历史，不再作为当前口径 |
| `task-level` | 只能由具体任务/修订在冻结时选定，不能设全局默认 | 缺失即 fail-closed，不得由 Agent 自动套用 |
| `environment-input` | 决定已成立，执行前需要外部事实/数值 | 登记到 P0-10 输入清单，不得虚构 |
| `open-blocker` | 未解决且阻断 Phase 0 关闭或 L3/L4 真机门禁 | 需所有者/责任方关闭后才能进入下一门 |
| `non-blocking follow-up` | 不影响当前 Phase 0 对账，但后续阶段必须收口 | 指定阶段/负责人跟进，不提前宣称完成 |

---

## 2. 对账表

### 2.1 登记册 §1 已批准事项

| ID | 决策项（原登记位置） | 分类 | 当前依据/状态 | Owner / 下一门 |
|---|---|---|---|---|
| A-01 | 首个业务域＝语音交互测试（§1） | `confirmed-for-planning` | 需求基线 §5；`domain.md` D-C-09 仅 `voice_interaction` | 所有者 / P0-11 |
| A-02 | 入口＝对话、文件/表格、结构化表单（§1） | `confirmed-for-planning` | 需求基线 §2；任务草稿归一化 | 所有者 / P0-11 |
| A-03 | 自动 PASS 仅来自自动回放＋客观可追溯证据（§1） | `confirmed-for-planning` | 需求基线 §5；`evidence-verdict.md` §2；`ui-report-knowledge-audit.md` §3.3 | P0-06 / P0-11 |
| A-04 | 人工喊测仅补充记录，不自动 PASS（§1） | `confirmed-for-planning` | 需求基线 §5；报告契约 `human_supplement_can_produce_pass=false` | P0-07 / P0-11 |
| A-05 | V0.0.1 允许提交者自批（§1） | `confirmed-for-planning` | 需求基线 2.2；`domain.md` D-C-06 默认 `prevent_self_review=false` | 所有者 / P0-11 |
| A-06 | 同一 task 多不可变修订（§1） | `confirmed-for-planning` | 需求基线 §4；`domain.md` D-C-05/D-C-13 | P0-04 / P0-11 |
| A-07 | 范围变化＝安全边界暂停→同 task 新修订→重审（§1） | `confirmed-for-planning` | 需求基线 §6；`domain.md` Revision 状态机 | P0-04 / P0-11 |
| A-08 | 烟雾/正式严格分离，烟雾不入分母（§1） | `confirmed-for-planning` | `thresholds.md` D-TH-13；`ui-report-knowledge-audit.md` §3.4 | P0-08 / P0-11 |
| A-09 | 保留 30 天；无归档路径不自动删除（§1） | `confirmed-for-planning` | `thresholds.md` D-TH-18；`evidence-verdict.md` §11 | P0-10 / P0-11 |
| A-10 | 排除 Jira、断电、刷机（§1） | `confirmed-for-planning` | 需求基线 §6；`domain.md` 非目标 | 所有者 / P0-11 |

### 2.2 登记册 §1.1 本轮新增确认

| ID | 决策项（原登记位置） | 分类 | 当前依据/状态 | Owner / 下一门 |
|---|---|---|---|---|
| B-01 | 30 天保留确认（§1.1） | `confirmed-for-planning` | 同 A-09；`thresholds.md` §13 D-TH-18 | 所有者 / P0-11 |
| B-02 | 归档路径暂放 `/home/bszheng/NoahsArkdata`（§1.1） | `environment-input` | 主机/挂载点未确认；本机当前不存在；只是暂存，不是唯一副本（`environment-inputs.md` §3） | 所有者 / P0-10 A-0 |
| B-03 | 权限两类：最高权限＋仅提交任务（§1.1） | `confirmed-for-planning` | `ui-report-knowledge-audit.md` §6 角色与任务关系 | P0-07 / P0-11 |
| B-04 | “仅提交任务”是否可自批冻结边界待澄清（§1.1） | `non-blocking follow-up` | 自批已由 A-05 允许；该问仅影响“仅提交任务”角色范围，不影响 Phase 0 契约字段 | P0-06 / Phase 2 权限策略 |
| B-05 | 审批超时默认时长/升级对象/拒绝或挂起未定值（§1.1） | `superseded` | `thresholds.md` D-TH-07：24h 提醒、48h 升级、**永不自动拒绝**；升级对象映射仍见 T-14 | P0-08 已定 / 历史保留 |
| B-06 | 语言“无强制偏好”（§1.1，P1-01） | `superseded` | 已由 §1.2 **确认 Python 3.11/3.12** 替代 | §1.2 已定 / 历史保留 |
| B-07 | RPO/RTO 目标：尽量不丢、越快越好（§1.1） | `confirmed-for-planning` | 具体目标：DB ≤1min/≤30min、证据 ≤15min/≤1h、整机 ≤4h（§1.3）；仍需恢复演练验证 | 所有者 / P1-08 |
| B-08 | 备份设施已具备：局域网 NAS＋另一台服务器（§1.1） | `confirmed-for-planning` | 设施事实已确认；协议/容量/配置见 T-12 | 所有者 / P1-08 |

### 2.3 登记册 §1.2、§1.3

| ID | 决策项（原登记位置） | 分类 | 当前依据/状态 | Owner / 下一门 |
|---|---|---|---|---|
| C-01 | 统一 Python 3.11/3.12＋venv 锁定（§1.2） | `confirmed-for-planning` | `environment-inputs.md` §1.1；P0-10 lstest 基线 | P0-11 |
| D-01 | 备份拓扑 B4（第二服务器 PostgreSQL 从库）＋B3（NAS WAL/每日全量）（§1.3） | `confirmed-for-planning` | `environment-inputs.md` §1.1/§3；具体端点与容量见 T-12 | 所有者 / P1-08 |

### 2.4 登记册 P0 决策

| ID | 决策项（原登记位置） | 分类 | 当前依据/状态 | Owner / 下一门 |
|---|---|---|---|---|
| E-01 | P0-01 PostgreSQL 唯一正式库；SQLite 仅历史/只读（P0-01） | `confirmed-for-planning` | `source-reconciliation.md` SR-02 已闭环；`docs/contracts/README.md` 开篇 | P0-11 |
| E-02 | P0-02 HTTP 长轮询＋租约＋心跳（P0-02） | `confirmed-for-planning` | `security-node.md` §9；`thresholds.md` §4/D-TH-02 | P0-11 |
| E-03 | P0-03 证书＋签名＋会话内执行器（P0-03） | `confirmed-for-planning` | `security-node.md` 全文（候选）；证书算法等见 T-09 | P0-11 |
| E-04 | P0-04 lstest 外置适配器＋契约表（P0-04） | `confirmed-for-planning` | `environment-inputs.md` §6；真实 profile/脚本见 T-11 | P0-11 |
| E-05 | P0-05 OpenCode 仅交互运行时；OMO/OpenSpec 仅开发期（P0-05） | `confirmed-for-planning` | `source-reconciliation.md` SR-01/SR-06；`VERSIONING.md` §2 | P0-11 |
| E-06 | P0-06 角色＋任务关系授权（P0-06） | `confirmed-for-planning` | `ui-report-knowledge-audit.md` §6；候选契约 | P0-11 |
| E-07 | P0-07 设备＋端点组合租约；失联先隔离对账（P0-07） | `confirmed-for-planning` | `domain.md` §11/§15；`thresholds.md` D-TH-01/D-TH-03 | P0-11 |
| E-08 | P0-08 自建显式状态机＋事件回放；中断重跑新 run（P0-08） | `confirmed-for-planning` | `domain.md` §9/§15；`thresholds.md` 全文 | P0-11 |
| E-09 | P0-09 控制面独占判定；oracle 随修订冻结；lstest 五轴（P0-09） | `confirmed-for-planning` | `evidence-verdict.md` §0/§13；`domain.md` §14 | P0-11 |
| E-10 | P0-10 本地内容寻址；到期只标记不删除（P0-10） | `confirmed-for-planning` | `evidence-verdict.md` §6/§11；`thresholds.md` D-TH-18 | P0-11 |
| E-11 | P0-11 单机三进程部署（P0-11，部署拓扑） | `confirmed-for-planning` | 架构建议；不等于 Phase 0 的 P0-11 验证归档（见 T-23） | P0-11 |
| E-12 | P0-12 登记式插件（只读＋受控写）；拒绝固件打包/烧录/上电（P0-12） | `confirmed-for-planning` | 需求基线 §6 排除项；P0-12 边界 | P0-11 |
| E-13 | P0-13 工具证据网关：工具只产 `ToolEvidence`，不写权威状态（P0-13） | `confirmed-for-planning` | 工具边界成立；具体工具版本需重锁（见 T-15） | P0-11 |

### 2.5 登记册 P1 决策

| ID | 决策项（原登记位置） | 分类 | 当前依据/状态 | Owner / 下一门 |
|---|---|---|---|---|
| F-01 | P1-09 插件 commit 锁定；升级前契约测试与假设备回归；版本漂移告警（P1-09） | `non-blocking follow-up` | 策略与 P0-13 一致，但尚无独立契约/实施台账承接 | Phase 3 / 实施阶段 |

### 2.6 必须覆盖的 O 规则主题

| ID | 决策项（原登记位置） | 分类 | 当前依据/状态 | Owner / 下一门 |
|---|---|---|---|---|
| G-01 | O-11 语音指标族标准化（O-11） | `task-level` | 指标族需在任务修订声明；平台不设全局阈值 | 任务修订 / 冻结前 |
| G-02 | O-12 报告口径声明（O-12） | `confirmed-for-planning` | `ui-report-knowledge-audit.md` §3.4 强制声明分母/排除/重试口径 | P0-07 / P0-11 |

### 2.7 主题补充行（覆盖任务要求但登记册未单列的项）

| ID | 决策项（来源） | 分类 | 当前依据/状态 | Owner / 下一门 |
|---|---|---|---|---|
| T-01 | 任务分类：V0.0.1 仅 `voice_interaction`（`domain.md` §4/D-C-09） | `confirmed-for-planning` | schema `task.schema.json` enum 仅 `voice_interaction` | P0-04 / P0-11 |
| T-02 | 语音能力/失败分类：唤醒、离线命令、自由说、在线 ASR、连续识别；识别正确性≠交互成功（需求基线 §5） | `task-level` | 每个任务必须声明能力与可观察目标；平台不代选 | 任务修订 / 冻结前 |
| T-03 | 报告必需章节与四类记录分离（P0-07） | `confirmed-for-planning` | `ui-report-knowledge-audit.md` §3.2–§3.4 共 14 章节 | P0-07 / P0-11 |
| T-04 | 任务级样本/阈值/重试/预算模板（`thresholds.md` §11） | `task-level` | 30/100/300 样本等仅为模板；未选定即 `SAMPLE_PLAN_UNDEFINED` | 任务修订 / 冻结前 |
| T-05 | 设备等价字段与跨型号替代批准（`domain.md` Q-08） | `task-level` | `equivalence_group_id`/`conditions_digest`/`verified_at`/`verified_by` 字段已定义，值未定 | 任务修订 / P0-10 |
| T-06 | 证据必需切片粒度（`evidence-verdict.md` Q-EV-01） | `task-level` | 只能由冻结包声明 `evidence_requirements`，无全局固定集 | 任务修订 / 冻结前 |
| T-07 | 同修订多 `run_id` 的分母/重试/补传合并（P0-07 开放问题 8） | `task-level` | 报告契约只允许单一标签；合并规则未冻结 | 任务修订 / P0-07 后续 |
| T-08 | Linux 控制面 / Windows 节点边界：Linux 判定与事实源；Windows 仅出站、Session 0、本地设备/音频/串口（README；`security-node.md` §2/§9） | `confirmed-for-planning` | 仅出站、mTLS、交互式执行器已写入候选契约 | P0-05 / P0-11 |
| T-09 | 节点外部事实：Windows 主机/OS build/服务账户/Agent 版本、CA、注册 token 签发人（`environment-inputs.md` §4/§7） | `open-blocker` | 全部 unknown/placeholder；无节点无法注册 | 所有者/责任方 / L3 前 |
| T-10 | 设备外部事实：型号/固件/硬件版本/脱敏序列号/音频与串口端点/电源/恢复（`environment-inputs.md` §5） | `open-blocker` | 全部 unknown；L3 烟测无对象 | 所有者/责任方 / L3 前 |
| T-11 | 真实 formal profile 与真实任务脚本（`environment-inputs.md` §6） | `open-blocker` | 仅 framework 基线；`m0_min_profile.json` 为 debug/0 规则，不可替代 | 所有者/责任方 / L3–L4 前 |
| T-12 | 证据根/容量、NAS 协议与路径、第二服务器配置、备份密钥保管、恢复演练（`environment-inputs.md` §3） | `open-blocker` | 端点与演练均未落地；阻断 L4/AC-14 与归档验证 | 所有者/责任方 / L4 前 |
| T-13 | PostgreSQL 目标版本与实例运维人（`environment-inputs.md` §13 Q2） | `environment-input` | 引擎已定；版本是否锁定 16、谁运维未定 | 所有者 / P1-08 |
| T-14 | 审批升级对象映射（`thresholds.md` §14-6） | `environment-input` | `highest_permission_then_platform_admin` 需映射真实组织角色/兜底人 | 所有者 / P0-08 后续 |
| T-15 | 工具链版本重锁与模型绑定/目录（P0-13；`VERSIONING.md` P1-01..P1-07） | `non-blocking follow-up` | 工具边界已定；Pare 0.23.3 等版本需实施前重锁；模型路由属后续阶段 | Phase 2–3 / 实施前 |
| T-16 | 旧草案“`lease_expired`→`INFRA_ERROR`→先对账再重派”（SR-10） | `superseded` | 已由 E-07/E-08 与 `thresholds.md` D-TH-01 替代；旧文保留 | P0-09 已标注 / 历史保留 |
| T-17 | 旧草案 I-21“缺 `cleanup_receipt` 即证据不完整”（SR-11） | `superseded` | 已由 `evidence-verdict.md` §12.3 替代：只影响释放确认 | P0-09 已标注 / 历史保留 |
| T-18 | 旧草案审批超时“提醒→升级→拒绝”（SR-13） | `superseded` | 已由 `thresholds.md` D-TH-07 替代：永不自动拒绝 | P0-09 已标注 / 历史保留 |
| T-19 | 旧单终态枚举/C1–C7 作为当前完成门禁（SR-07/SR-08） | `superseded` | 已由五轴分离与旧门禁映射替代；C1–C7 仅历史别名 | P0-03 已标注 / 历史保留 |
| T-20 | 旧 81 项任务范围（SR-06） | `superseded` | 当前范围为 Phase 0–6；81 项仅历史账本 | P0-03 已标注 / 历史保留 |
| T-21 | 旧 UI 基线（v2 航次档案 / v3 Quiet Instrument）（SR-05） | `superseded` | 当前无已冻结 UI 基线；旧材料全部降为历史参考 | P0-02 已标注 / 历史保留 |
| T-22 | 新 Apple 风格 UI 基线（P1-08） | `non-blocking follow-up` | 等待 Phase 1 P1-08 冻结；不阻断 Phase 0 | Phase 1 / P1-08 |
| T-23 | Phase 0 验证与归档（施工进度表 P0-11，注意与登记册 P0-11 部署拓扑不同号） | `open-blocker` | 负责人/状态仍为“待分配”；Phase 0 不能关闭 | Orchestrator / P0-11 |
| T-24 | 当前任务范围 Phase 0–6；OpenSpec 仅开发期规格（`VERSIONING.md` §2；SR-06） | `confirmed-for-planning` | 81 项已降为历史；OpenSpec 不进入运行时 | P0-11 / P3-07 |
| T-25 | 新施工 WBS（P3-07） | `non-blocking follow-up` | 尚未产出；Phase 3 才冻结 | Phase 3 / P3-07 |
| T-26 | 五轴判定与正式 PASS 五条件（`domain.md` §14） | `confirmed-for-planning` | `execution_status=COMPLETED` 等五条件；节点不得写最终判定 | P0-06 / P0-11 |
| T-27 | 租约/离线/STOP-first：通信、占用、执行许可三分离；重连先 STOP；不自动释放（`domain.md` §15；`thresholds.md` §4） | `confirmed-for-planning` | 与 P0-03 post-fix、P0-07 一致 | P0-07 / P0-11 |
| T-28 | 证据/保留：内容寻址、30 天热存、到期标记、无归档不删除（`evidence-verdict.md` §11） | `confirmed-for-planning` | 与 A-09/B-01 一致；归档验证见 T-12 | P0-10 / P0-11 |

---

## 3. 分类计数

| 分类 | 数量 |
|---|---|
| `confirmed-for-planning` | 37 |
| `superseded` | 8 |
| `task-level` | 6 |
| `environment-input` | 3 |
| `open-blocker` | 5 |
| `non-blocking follow-up` | 5 |
| **合计** | **64** |

补充口径（避免把“主题补充行”误读为原登记册行）：

- 登记册直接决策项（§1、§1.1、§1.2、§1.3、P0-01..P0-13、P1-09）共 **34** 项：`confirmed-for-planning` 29、`superseded` 2、`environment-input` 1、`non-blocking follow-up` 2、`task-level` 0、`open-blocker` 0。
- 主题补充行 T-01..T-28 共 **28** 项，另 O-11/O-12 共 2 项；加上登记册 34 项，合计 64 项。
- `open-blocker` 5 项全部来自外部事实/Phase 0 收口，不是新增产品设计决策。

---

## 4. 开放阻塞项（5）

| # | 阻塞项 | 影响门禁 | 关闭条件 |
|---|---|---|---|
| 1 | T-09 节点外部事实（Windows 主机/OS build/服务账户/Agent 版本、CA、注册 token 签发人） | L3 及以后 | 真实节点登记并可注册；证书链与签发人确定 |
| 2 | T-10 设备外部事实（型号/固件/序列号/音频与串口端点/电源/恢复） | L3 烟测、L4 判定 | 至少一台 DUT 的完整事实与端点绑定登记 |
| 3 | T-11 真实 formal profile 与任务脚本 | L3–L4 | 提供绝对路径、`profile_id`、规则数与摘要 |
| 4 | T-12 证据根/NAS/第二服务器/备份密钥/恢复演练 | L4、AC-14、归档验证 | 端点、容量、协议、密钥保管与演练记录落地 |
| 5 | T-23 Phase 0 验证与归档（施工进度表 P0-11） | Phase 0 关闭 | 指定负责人并完成归档、哈希清单与验证报告 |

> A-0 仍未通过；`environment-inputs.md` 的 5 个 top blockers 与上述 1–4 对应。本文不声称 A-0 通过、环境就绪或 Phase 0 已关闭。

---

## 5. 非阻塞跟进项（5）

| # | 项 | 下一门 |
|---|---|---|
| 1 | B-04 “仅提交任务”角色能否自批冻结边界 | P0-06 / Phase 2 权限策略 |
| 2 | F-01 P1-09 插件 commit 锁定与回归策略落地 | Phase 3 / 实施 |
| 3 | T-15 工具链版本重锁与模型绑定/目录 | Phase 2–3 / 实施前 |
| 4 | T-22 新 Apple 风格 UI 基线冻结 | Phase 1 / P1-08 |
| 5 | T-25 新施工 WBS 产出 | Phase 3 / P3-07 |

---

## 6. 保留、候选状态与未宣称事项

1. 登记册对账前 263 行、所有旧状态与旧建议值**原样保留**；本对账只在文末追加注记，追加后 273 行（前 263 行哈希见 §7）。未删除、未改写任何旧行。
2. P0-04..P0-08 契约仍为 `frozen-candidate v1`；35/35 schema 通过只证明结构与不变量可校验，不证明所有者批准或生产冻结。
3. P0-03、P0-10 的 PASS 均为**限定范围 post-fix** 判定；原始 NEEDS-FIX 报告与历史计数保留，不据此宣称完整通过。
4. `confirmed-for-planning` 不得被引用为“已批准”；`superseded` 行仅用于历史追溯。
5. 未修改 `docs/v2/`、`openspec/`、`docs/contracts/`、`.omo/plans/`、`.omo/boulder.json`、`plan.md`、`docs/ssh.txt`；未提交、未推送。
6. 未联网、未执行真实设备/节点/数据库/备份动作；未读取或输出任何密钥、凭据或个人信息。

---

## 7. 复核方法

```bash
# 1. 登记册旧行数与哈希（前 263 行为原内容；追加后应为 273 行）
wc -l .omo/drafts/05-decisions/noahsark-v0.0.1-decision-register.md
head -n 263 .omo/drafts/05-decisions/noahsark-v0.0.1-decision-register.md | git hash-object --stdin
# 本次实测：前 263 行 dada1a56d053efc7e33a2bb7f9bc4db1e202a621；全文 033ab893c1bbdde24226f8ed66d75bd46df2dd1f

# 2. 对账表分类计数（按第 3 节口径）
grep -c '`confirmed-for-planning`' docs/delivery/p0-09-decision-reconciliation.md
grep -c '`superseded`' docs/delivery/p0-09-decision-reconciliation.md
grep -c '`task-level`' docs/delivery/p0-09-decision-reconciliation.md
grep -c '`environment-input`' docs/delivery/p0-09-decision-reconciliation.md
grep -c '`open-blocker`' docs/delivery/p0-09-decision-reconciliation.md
grep -c '`non-blocking follow-up`' docs/delivery/p0-09-decision-reconciliation.md

# 3. 空白/编码检查
git diff --check
file docs/delivery/p0-09-decision-reconciliation.md
```

> 注：`grep -c` 统计的是**出现行数**，第 1 节分类定义表与第 5 节标题也会命中；精确计数以第 3 节表格与脚本按行解析为准。
