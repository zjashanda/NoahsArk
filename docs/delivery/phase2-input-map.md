# NoahsArk Phase 2 输入地图（服务端 + UI 落地方案准备稿）

> 版本：v0.1（2026-10-29）
> 状态：**只读输入地图 / 规划准备稿**。不是 Phase 2 落地方案，不是架构冻结件，不是契约冻结、实现、迁移、部署或发布授权。
> 范围：把已批准范围、已评审架构/模块/交付/测试边界、候选契约、事实源对账、环境输入和当前 UI 候选稿，映射为未来 P2-01..P2-09 的输入、候选边界和未决依赖。
> 明确未做：没有产品代码、没有 API 实现、没有数据库迁移、没有 UI 修改、没有 OpenAPI 冻结、没有契约冻结、没有阶段计划冻结、没有提交或推送。
> 进度口径：`.omo/plans/noahsark-platform-delivery.md` 中 **P2-01..P2-09 仍全部未勾选**。本文件不改变任何复选框状态。

---

## 0. 阅读范围与事实源

### 0.1 已读输入

| 类别 | 路径 | 本文件用途 |
|---|---|---|
| 执行主计划 | [`.omo/plans/noahsark-platform-delivery.md`](../../.omo/plans/noahsark-platform-delivery.md) | P2-01..P2-09 范围、阶段门、受限 SSH 政策、非授权边界 |
| 进度与交接 | [`construction-progress.md`](./construction-progress.md)、[`restart-handoff-20261029.md`](./restart-handoff-20261029.md) | 当前 Phase 1 候选状态、Phase 2 未开始、代理核验缺口 |
| 需求基线 | [`.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md`](../../.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md) | 已批准需求范围、角色、任务/修订/运行、门禁、证据、隐私 |
| 架构评审 | [`.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md`](../../.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md) | CP-01..CP-13、CP-18..CP-23、EN-01..EN-08、五轴、租约、部署建议 |
| 模块评审 | [`.omo/drafts/01-design/noahsark-v0.0.1-module-design.md`](../../.omo/drafts/01-design/noahsark-v0.0.1-module-design.md) | M-01..M-21、模块依赖、错误分类、节点边界 |
| 施工验收 | [`.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md`](../../.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md) | A-0..A-9、AC-1..AC-14、L0–L5、环境就绪、交付包 |
| 测试策略 | [`.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md`](../../.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md) | T1–T6、平台/语音/恢复矩阵、正式 PASS 条件 |
| 决策登记册 | [`.omo/drafts/05-decisions/noahsark-v0.0.1-decision-register.md`](../../.omo/drafts/05-decisions/noahsark-v0.0.1-decision-register.md) | P0/P1 取舍、备份拓扑、语言与运行时 |
| 决策对账 | [`p0-09-decision-reconciliation.md`](./p0-09-decision-reconciliation.md) | 64 项分类、5 个 open-blocker、5 个非阻塞跟进 |
| 契约索引 | [`../contracts/README.md`](../contracts/README.md) | 所有权、版本规则、跨契约对齐、候选状态 |
| 领域契约候选 | [`../contracts/domain.md`](../contracts/domain.md) | Task/Revision/Approval/Gate/Case/Run/Attempt/Bundle/Lease/Device/Node/Receipt、幂等、并发、错误码 |
| 证据判定候选 | [`../contracts/evidence-verdict.md`](../contracts/evidence-verdict.md) | manifest、证据状态、清理回执、占用/释放、五轴、Linux 独立复核 |
| 节点安全候选 | [`../contracts/security-node.md`](../contracts/security-node.md) | 身份、mTLS、消息信封、Job/Lease/Heartbeat/STOP/Receipt/Log Query/Anomaly、离线重连 |
| 阈值候选 | [`../contracts/thresholds.md`](../contracts/thresholds.md) | H/O/T 三类、租约/心跳/重连、派发/STOP、审批、磁盘/spool、证据上传、日志查询、时钟 |
| UI/报告/知识/审计候选 | [`../contracts/ui-report-knowledge-audit.md`](../contracts/ui-report-knowledge-audit.md) | TaskCard 投影、报告 14 章节、知识候选、审计、访问级别 |
| 事实源对账 | [`source-reconciliation.md`](./source-reconciliation.md)、[`approved-draft-reconciliation.md`](./approved-draft-reconciliation.md) | 21 类冲突、阶段门后事实源切换、旧草案修正 |
| 环境输入 | [`environment-inputs.md`](./environment-inputs.md) | A-0、L3/L4/L5 的 85 条 known/placeholder/unknown |
| UI 研究候选 | [`ui-design-research.md`](./ui-design-research.md) | Apple HIG、数据密集控制台、离线/stale 设计依据 |
| UI 信息架构候选 | [`ui-information-architecture.md`](./ui-information-architecture.md) | 12 区域、39 路由、8 子视图、12 类状态、访问矩阵 |
| UI 设计系统候选 | [`ui-design-system.md`](./ui-design-system.md) | Quiet Instrument 令牌、状态语言、五轴/门禁/租约/证据可视化 |
| UI 屏幕规格候选 | [`ui-screen-specification.md`](./ui-screen-specification.md) | 屏幕族、G0–G7 落点、AC/L/T 追溯、未决项 |
| UI 基线差距 | [`ui-baseline-gap-analysis.md`](./ui-baseline-gap-analysis.md) | 旧 UI 处置、新 IA 理由、可访问性/深色缺口 |

### 0.2 事实源顺序（按现有规则）

1. 已批准需求基线。
2. 根 `plan.md` 中更晚的架构/模块/字段级批准记录。
3. 已同步批准边界的 `.omo/drafts/01-design`、`.omo/drafts/02-delivery` 正文。
4. `docs/contracts/` 的字段级候选契约。
5. 根 `plan.md` 其余记录（决策日志，不替代冻结件）。
6. `docs/VERSIONING.md`、索引与导航。
7. `docs/v2/`、`openspec/` 的同步后实现参考。
8. `.omo/drafts/99-history/`、`solutions/1027V1/`、`docs/v2/` 已标历史章节（只读历史）。

> 本文件的 P2 建议位于第 4 层以下的“候选规划输入”，不得反向覆盖第 1–3 层。

---

## 1. 当前状态与 P2 入口条件

### 1.1 事实状态

| 项目 | 当前状态 | 对 P2 的含义 |
|---|---|---|
| Phase 0 | P0-01..P0-11 已在主计划标 `[x]`，但 P0-04..P0-08 是 `frozen-candidate v1`，P0-11 是候选归档 | 不能把 Phase 0 归档当作生产契约冻结或 A-0 通过 |
| 契约 | `docs/contracts/` 全部为 `frozen-candidate v1` | P2 只能引用字段语义，不能声称字段/枚举已冻结 |
| Phase 1 UI | P1-01..P1-04 四份候选文档已落盘；独立核验 `ui-candidate-verification.md` 缺失；P1-05..P1-08 未开始 | **UI 未冻结**；P2-05 与所有 UI 对接必须等待 P1-08 |
| Phase 2 | P2-01..P2-09 全部未勾选 | 本文件只准备输入，不启动 P2 |
| A-0 | 未通过；85 条输入中 20 known / 14 placeholder / 51 unknown | 真机、部署和容量相关 P2 决策仍被外部事实阻塞 |
| 真机 | L3/L4/L5 未开始 | 不能以 P2 方案替代真机验收证据 |
| 实现/部署/发布 | 未授权 | 本文件不构成任何实施许可 |

### 1.2 P2 的候选进入方式

P2 可以先用**只读、非权威**方式准备的输入：

- 服务边界草案、数据域草案、API 资源清单草案、Node Agent 交互清单草案、证据存储草案、UI 对接清单草案、部署/恢复问题清单。
- 与 A-0 无关的静态设计工作，例如模块依赖核对、错误码映射、幂等键核对、五轴/释放/重连一致性检查。

P2 不能提前冻结的输入：

- 契约字段/枚举、数据库 DDL、OpenAPI、Node Agent 消息 schema、迁移脚本、UI 组件实现。
- 任何依赖真实节点、设备、证书、存储容量、PostgreSQL 实例、NAS/第二服务器、恢复演练的部署事实。

---

## 2. 标记约定

| 标记 | 含义 | 可否作为未来 P2 冻结依据 |
|---|---|---|
| **F（已批准/已评审约束）** | 需求基线、B-1..B-7、M-01..M-21、A-0..A-9、AC-1..AC-14、S5-1..S5-4 等已确认的规划边界 | 可作为约束；不等于实现或生产冻结 |
| **C（候选）** | 本文件提出的服务/数据/API/UI 映射；或 `docs/contracts/`、P1 UI 候选稿 | 只能作为评审输入 |
| **D（待定/阻塞）** | 依赖 P1-08、A-0 外部事实、契约冻结或所有者裁决 | 不得在依赖关闭前写成既成事实 |

> 本文件的 `C` 不是“已批准候选”，只是“可讨论的候选边界”。凡涉及字段名、枚举、阈值、表结构、路由、进程拆分，均以对应冻结件为准。

---

## 3. 已批准范围到 P2 的约束映射

| 约束 | 权威来源 | P2 必须保留 | 状态 |
|---|---|---|---|
| Linux 控制面独占生成、冻结、审核、修复、版本化、最终判定 | 需求基线；B-4/B-5；`domain.md` §19；`README.md` §4 | 服务边界中“生成/判定/冻结”只在 Linux；Windows 不写最终判定 | **F** |
| Windows Node Agent 只执行冻结的 NoahsArk Execution Bundle 并回传事实 | B-4；模块 §2.2/§4.7；`security-node.md` §1/§10/§11 | Node Agent 无脚本/音频/异常规则/判定写权限 | **F** |
| 同一 `task_id`、不可变 `revision_id`、独立 `run_id`、稳定 `case_id`/`case_version`、独立 `attempt_id` | 需求基线 §4；`domain.md` §3/§4/§5/§8/§9 | 数据库主键/唯一约束/事务边界不得把修订或运行折叠 | **F** |
| 一次冻结批准覆盖静态→资格/租约→独立烟测→正式采样 | B-3；交付验收 §2.1 | 编排服务按同一批准快照推进，不重复人工批准 | **F** |
| 烟测独立 `run_id`，永不进入正式分母 | B-3；`domain.md` §14；`evidence-verdict.md` §14.5 | Run.mode 与 denominator_eligible 必须分离；数据库保留 mode | **F** |
| 五轴判定，正式 PASS 需五条件同时成立 | B-5；`domain.md` §9/§14；`evidence-verdict.md` §14 | Run/Attempt 五轴独立存储；节点回执不得写最终轴 | **F** |
| 离线续跑：已启动冻结压测断线继续；设备保持占用；不重派/重播/重复采样 | B-3/A-3；`domain.md` §15；`thresholds.md` §4 | 通信、占用、执行许可三分离；租约到期不是所有权到期 | **F** |
| STOP-first 重连：待 STOP → 停止后续动作 → 补传 → 去重 → 对账 → 恢复领取 | B-5/A-3；`domain.md` §15.3；`security-node.md` §13.3 | API/Node Gateway 必须有待送达 STOP 队列与对账状态 | **F** |
| 设备释放、证据完整性、最终判定三平面分离 | B-5/B-6；交付验收 §2.1；`evidence-verdict.md` §2/§12/§13 | 服务与数据模型不得用单一“完成/通过”状态代替三者 | **F** |
| 缺 `cleanup_receipt` 只阻断释放确认，不等于证据不完整 | S5-3；`evidence-verdict.md` §12.3 | 释放状态与 evidence_status 分字段 | **F** |
| PostgreSQL 是唯一正式数据库 | B-6；`source-reconciliation.md` SR-02；`domain.md` §17.1 | 所有正式状态、索引、审计、投影源在 PostgreSQL；禁止 SQLite 参与 | **F** |
| 原始证据内容寻址 + 数据库索引/摘要 | B-6；`evidence-verdict.md` §6/§11 | 证据文件不塞入业务表；locator 可变、ID/digest 不可变 | **F** |
| 30 天热存；无已验证归档路径不得自动删除 | 需求基线 §12；`thresholds.md` TH-S-12/TH-S-13 | 存储服务只标 `archive_pending`，不自动删除 | **F** |
| 知识候选不得自动合入；合入通用/工具/异常经验需权限 | B-6；`ui-report-knowledge-audit.md` §4 | 知识服务把候选与正式条目分表/分状态 | **F** |
| 原始事件、审计、历史判定只追加；归档只改 locator | B-6；`ui-report-knowledge-audit.md` §5 | 事件/审计表只 INSERT；更正写新事件 | **F** |
| 受限 SSH 凭据政策 | 主计划 §0.1 | P2/P3/P4 文档只引用受限路径，不写凭据、IP、用户名 | **F** |

### 3.1 P2 不应重新讨论的事项

以下事项已由更晚批准或候选契约收敛，P2 只做落点映射，不应在 P2 文档中重新打开：

- `lease.expires_at` 是续约截止，不是所有权到期。
- 心跳/通信离线不等于设备空闲、run 停止或可重派。
- 审批超时只提醒/升级，永不自动拒绝。
- `cleanup_receipt` 缺失只影响释放确认。
- 烟测、模拟、回放永不进入正式分母。
- Windows 自报 PASS 不是判定输入。
- 任务卡/列表/报告是投影，不是第二事实源。
- 旧 C1–C7、单一终态、SQLite、81 项 WBS 均只作历史。

---

## 4. 候选服务边界（C）

> 方向：**模块化单体优先，单机三进程为 V0.0.1 推荐形态**（架构 §13；决策登记册部署拓扑 P0-11）。以下服务是逻辑边界，不等于必须拆成独立微服务。进程/容器拆分属 P2-01 候选决策。

### 4.1 逻辑服务图

```text
浏览器 / Lead 会话 / API 客户端
        │ HTTPS
        ▼
┌─────────────────────────────────────────────────────────────┐
│ S-01 Edge / Console API                                     │
│ 会话、RBAC、REST、SSE/轮询、上传/下载、审计入口              │
└───────────────┬─────────────────────────────────────────────┘
                │ 内部命令/查询
┌───────────────▼─────────────────────────────────────────────┐
│ S-02 Task & Revision Service                                │
│ Intake、Task、Revision、Approval、Gate、Case 冻结            │
├─────────────────────────────────────────────────────────────┤
│ S-03 Orchestration & Run Service                            │
│ 门禁推进、static/smoke/formal、Attempt、状态投影             │
├─────────────────────────────────────────────────────────────┤
│ S-04 Resource & Lease Service                               │
│ Device/Node 资格、租约、epoch、draining/quarantine          │
├─────────────────────────────────────────────────────────────┤
│ S-05 Node Gateway                                           │
│ 出站长轮询、Job/Lease/Heartbeat/STOP/Receipt/Log Query      │
├─────────────────────────────────────────────────────────────┤
│ S-06 Evidence Service                                       │
│ manifest、分片上传、摘要重算、内容寻址、部分上传、保留       │
├─────────────────────────────────────────────────────────────┤
│ S-07 Verdict & Verification Service                         │
│ 五轴、Linux 独立复核、failure_class、分母、最终判定         │
├─────────────────────────────────────────────────────────────┤
│ S-08 Report / Knowledge / Projection Service                │
│ 报告、TaskCard、SSE 投影、知识候选、审计查询                 │
├─────────────────────────────────────────────────────────────┤
│ S-09 Identity, Access & Audit Service                       │
│ 用户/角色/任务关系、访问决策、审计事件、会话安全            │
└───────────────┬─────────────────────────────────────────────┘
                │
        PostgreSQL（唯一正式库） + 本地内容寻址证据存储
```

### 4.2 服务职责与写入权威（C）

| ID | 候选服务/模块边界 | 主要职责 | 唯一写入 | 只读消费方 | 主要来源 |
|---|---|---|---|---|---|
| S-01 | Edge / Console API | 认证、会话、RBAC 入口、REST/SSE、上传/下载、审计包装 | 无业务权威；只写会话/访问审计入口 | UI、Lead、外部客户端 | CP-12/13、M-12/13、`ui-report-knowledge-audit.md` §6 |
| S-02 | Task & Revision Service | Intake 归一化、Task、Revision、Approval、Gate、Case 冻结、Execution Bundle 引用 | Task/Revision/Approval/Gate/Case | UI、S-03、S-08 | CP-01..04、M-01..04/14 |
| S-03 | Orchestration & Run Service | 门禁推进、Run/Attempt 生命周期、smoke/formal 分离、重试/停止/范围变化 | Run/Attempt 生命周期与执行事实 | UI、S-06、S-07 | CP-04/06、M-04/06 |
| S-04 | Resource & Lease Service | 设备池、资格、租约、epoch、占用、draining/quarantine、释放对账 | Lease/Device/Node 占用与资格 | S-03、S-05、UI | CP-05、M-05/15 |
| S-05 | Node Gateway | 节点注册、长轮询、Job/Lease/Heartbeat/STOP/Receipt/Log Query/Anomaly、spool 事实 | 线协议事实与回执接收；不写最终判定 | S-04、S-06、S-07、UI | CP-06、M-06、`security-node.md` |
| S-06 | Evidence Service | manifest、分片上传、摘要重算、内容寻址、部分/重复上传、保留/归档状态 | EvidenceItem/Manifest/内容存储索引 | S-07、S-08、UI | CP-07、M-07、`evidence-verdict.md` |
| S-07 | Verdict & Verification Service | 五轴、独立复核、failure_class、正式分母、最终判定 | `business_verdict`/`verification_status`/最终 `decision` | UI、S-08、报告 | CP-07、M-07、`evidence-verdict.md` §14/§16 |
| S-08 | Report / Knowledge / Projection Service | Report、TaskCard 投影、SSE 事件、KnowledgeCandidate/Item、审计查询投影 | Report/Knowledge/投影；不改权威 Task/Run/Verdict | UI、Lead、报告读者 | CP-08/10/11、M-08/10/11 |
| S-09 | Identity, Access & Audit | 角色、任务关系、访问决策、审计事件、会话恢复快照 | 用户/角色/关系/审计事件 | 全部 | CP-09/12/13、M-09/12/13 |

### 4.3 进程形态候选（C，未冻结）

| 候选 | 组成 | 优点 | 风险/代价 | 依赖 |
|---|---|---|---|---|
| **单机三进程（推荐候选）** | `api` + `orchestrator` + `worker/verifier`，共享 PostgreSQL 与证据卷 | 与架构 §13、决策登记册部署拓扑 P0-11 建议一致；故障域小；运维简单 | 单机仍为单点；需进程内幂等与锁 | A-0 主机/端口/存储事实 |
| 单进程 | API + 编排 + 验证同进程 | 原型最快 | 长任务/重计算会阻塞 API；难隔离故障 | 仅限原型 |
| 多服务 | API/编排/租约/证据/判定/报告拆分 | 独立扩缩容 | 分布式事务、消息一致性、运维成本高 | 需要明确吞吐/可用性证据；当前无 |

**候选边界原则：**

1. 业务权威仍集中在 PostgreSQL；服务拆分不得产生第二事实源。
2. 跨服务一致性用“单事务 + 唯一约束 + 幂等键 + outbox/事件”表达，不依赖分布式事务。
3. 证据二进制不进入业务事务；先写内容存储，再以 `evidence_id + digest + locator` 登记索引。
4. Node Gateway 与 Orchestrator 的租约/epoch 校验必须共用同一权威字段，不做两套状态。
5. UI 只读 API/投影，不直连 PostgreSQL，不读取节点本地盘。

---

## 5. PostgreSQL 域（C）

> 以下是**候选逻辑域**，用于 P2-02 讨论；不是 DDL、不是迁移、不是最终 schema。表名、列名、约束名均未冻结。

### 5.1 域划分

| 域 | 候选表/对象 | 权威写入 | 关键约束/事务边界 | 备注 |
|---|---|---|---|---|
| `identity_access` | user、role、task_relation、access_policy、session、recovery_snapshot | S-09 | 角色/关系变更与审计同事务；会话令牌只存哈希 | 角色/关系来自 `ui-report-knowledge-audit.md` §6；具体 RBAC 仍 D-03 |
| `task_authoring` | task、task_revision、approval、gate、case、case_version、execution_bundle_ref | S-02 | `(task_id, current_revision_id)` 一致；每 revision 至多一个有效 approval；revision 冻结 CAS | 对应 `domain.md` §4–§10 |
| `execution` | run、attempt、case_result、run_event、stop_request | S-03 | `(run_id, attempt, job_kind)` 唯一；五轴独立列；smoke/formal 互斥 | 对应 `domain.md` §9；`attempt` 只属于一个 case_version |
| `resource_lease` | node、device、device_endpoint、lease、occupancy、cleanup_receipt_ref | S-04 | 占用键 `(node_id, device_id, endpoint_set)` 唯一；epoch 单调；释放三项前置 | 对应 `domain.md` §11/§15；`expires_at` 非所有权到期 |
| `node_protocol` | node_identity、enrollment、job、lease_message、heartbeat、receipt、anomaly_event、log_query | S-05 | `(job_id, attempt)` 唯一；`(node_id, message_id)` 去重；`(node_id, sequence)` 排序 | 对应 `security-node.md` §10/§11 |
| `evidence` | evidence_manifest、evidence_item、evidence_chunk、cleanup_receipt、device_occupancy、verification_record | S-06/S-07 | `evidence_id` 稳定；`(evidence_id, chunk_index, content_digest)` 去重；locator 可更新、ID/digest 不变 | 文件在内容存储；表只存索引/摘要/状态 |
| `verdict` | verdict、verdict_axis、denominator_snapshot、failure_classification | S-07 | 五轴同事务写入；正式 PASS 五条件校验；节点不得写 | 对应 `evidence-verdict.md` §14/§16 |
| `experience` | report、report_version、report_evidence_index、task_card_projection、knowledge_candidate、knowledge_item、knowledge_conflict | S-08 | 报告版本不可原地覆盖；投影可重建；候选/条目分状态 | 对应 `ui-report-knowledge-audit.md` §2–§4 |
| `audit_event` | audit_event、access_decision、security_event | S-09 | 只 INSERT；before/after/reason；不可删除 | 对应 `ui-report-knowledge-audit.md` §5 |
| `ops` | idempotency_key、outbox、lease_claim、projection_cursor、reconcile_run、backup_marker | 各写入方按域 | 幂等键与权威写入同事务；outbox 至少一次；投影游标单调 | 支撑 API/SSE/重连/恢复；不是业务事实源 |

### 5.2 候选数据库规则

| 规则 | 来源 | P2 落点 |
|---|---|---|
| canonical UUID（小写 RFC 9562）作为实体 ID | 契约 README §2.3；`domain.md` §2/§17 | 所有域主键/外键统一；线协议前缀只作展示别名 |
| `timestamptz` 存 UTC；应用不写本地时区 | `domain.md` §17.11 | 所有时间列、事件排序、审计 |
| SHA-256 摘要；manifest/证据 digest 独立重算 | `evidence-verdict.md` §6；`domain.md` §17.7 | 证据服务只信重算结果，不信节点摘要 |
| 租约领取使用唯一约束/部分唯一索引；`SELECT ... FOR UPDATE SKIP LOCKED` 仅限领取查询 | `domain.md` §17.2 | 资源领取查询；不用于一般读取 |
| 修订冻结用 CAS：`WHERE status='DRAFT' AND version=?` | `domain.md` §17.3 | Task/Revision 事务 |
| 审批一 revision 一个有效 `APPROVED` | `domain.md` §17.4 | 部分唯一索引 + 事务判定 |
| 回执 `(job_id, attempt)` 唯一，sequence 单调；缺口进 `RECEIPT_SEQUENCE_GAP` | `domain.md` §17.6 | Node Gateway/证据/审计 |
| 事件/审计只追加；纠错写新事件引用旧事件 | `domain.md` §17.12；`ui-report-knowledge-audit.md` §5.4 | audit_event/security_event |
| 证据索引与二进制分离 | `evidence-verdict.md` §6.3 | Evidence Service |
| 禁止 SQLite 作为正式事实源 | B-6；`domain.md` §17.1 | 连接配置、迁移、测试均不得引入 |

### 5.3 待 P2-02 决定但当前不能冻结的事项（D）

- 物理 schema 名称、表名、列名、索引名、分区策略。
- JSONB 与关系列的边界；`facts`/`payload` 的存储形态。
- 证据 manifest 的最终 JSON Schema 字段与 `schema_version` 迁移策略。
- 事件表与 outbox 的保留/归档周期；投影重建方式。
- 审计事件与安全事件的物理分表/分区。
- 软删除是否允许；若允许，原始事件/证据/判定仍必须不可删除。
- PostgreSQL 版本（候选 16，未锁定）、实例拓扑、连接池、备份模式。

---

## 6. API 面（C）

> 以下是候选资源面与交互面，不是 OpenAPI，不是路由实现。字段、枚举、状态码、错误码以冻结契约为准。

### 6.1 控制台/业务 API

| 面 | 候选资源/端点族 | 主要消费者 | 关键要求 | 依赖 |
|---|---|---|---|---|
| 认证与会话 | `/api/v1/auth/*`、`/api/v1/sessions/*`、`/api/v1/me` | UI、Lead | 令牌熵/轮换/空闲超时/登出失效；Cookie Secure/HttpOnly/SameSite | 契约 §10；D-01 |
| 任务/修订 | `/api/v1/tasks`、`/api/v1/tasks/{id}`、`/revisions`、`/freeze`、`/diff` | UI、S-02 | `task_id` 幂等创建；revision 不可变；范围变化派生新 revision | `domain.md` §4–§6/§16 |
| 审批/门禁 | `/api/v1/tasks/{id}/revisions/{rid}/approvals`、`/gates` | UI、S-02/S-03 | 一次有效批准；意见/范围快照/等待期；超时不自动拒绝 | B-3；`thresholds.md` §6 |
| 用例/执行包 | `/api/v1/revisions/{rid}/cases`、`/execution-bundle` | UI、S-02/S-03 | case_version 随修订冻结；bundle 只读引用 | `domain.md` §8/§10 |
| 运行/尝试 | `/api/v1/runs`、`/runs/{id}`、`/runs/{id}/attempts`、`/stop` | UI、S-03/S-07 | static/smoke/formal 互斥；五轴独立；烟测不入分母 | `domain.md` §9/§14 |
| 设备/节点 | `/api/v1/devices`、`/nodes`、`/leases`、`/occupancy`、`/release` | UI、S-04 | 四信号分离；释放三项前置；控制动作二次确认 | `domain.md` §11/§15 |
| 证据 | `/api/v1/evidence`、`/evidence/{id}`、`/manifests`、`/uploads/*`、`/download` | UI、S-06 | 分片/续传/幂等；expected/received/verified；访问级别 | `evidence-verdict.md` §5/§9 |
| 判定/复核 | `/api/v1/verdicts`、`/runs/{id}/verdict`、`/verification-records` | UI、S-07 | 五轴；Linux 独立复核；节点事实只读 | `evidence-verdict.md` §14/§16 |
| 报告 | `/api/v1/reports`、`/reports/{id}`、`/reports/{id}/evidence-index` | UI、S-08 | 14 章节；分母声明；四类记录分离；默认摘要 | `ui-report-knowledge-audit.md` §3 |
| 知识 | `/api/v1/knowledge`、`/knowledge/candidates`、`/promote` | UI、S-08 | 候选/条目分离；推广需权限与审计 | `ui-report-knowledge-audit.md` §4 |
| 任务卡/事件 | `/api/v1/task-cards`、`/events`（SSE）、`/events/poll` | UI、Lead | 服务端投影；stale/freshness；断线可降级轮询 | `ui-report-knowledge-audit.md` §2 |
| 审计/恢复 | `/api/v1/audit`、`/audit/{id}`、`/recovery` | UI、S-09 | 只追加；before/after/reason；导出需 `EXPORT_AUDIT` | `ui-report-knowledge-audit.md` §5 |

### 6.2 节点协议面（只出站长轮询）

| 面 | 候选消息/端点 | 方向 | 关键要求 | 依赖 |
|---|---|---|---|---|
| 注册/身份 | `node_enrollment`、`node_identity` | 节点↔控制面 | 一次性 256-bit token、15 分钟、单次、只存哈希；X.509/Ed25519 | `security-node.md` §5–§6 |
| Job 领取 | `job`、`job_ack` | 控制面→节点 / 节点→控制面 | action 闭集；bundle digest 校验；无交互会话 BLOCKED | `security-node.md` §10.1/§11 |
| 租约/心跳 | `lease`、`heartbeat` | 控制面↔节点 | 30s 心跳；60s 租约；epoch fencing；过期不释放 | `security-node.md` §10.2/§10.3；`thresholds.md` §4 |
| STOP | `stop`、`stop_ack` | 双向 | STOP-first；不中断原子动作；本地安全 STOP 独立 | `security-node.md` §10.4 |
| 回执 | `receipt` | 节点→控制面 | `node_observed_*`、`used_for_decision=false`；spool/去重 | `security-node.md` §10.5 |
| 日志查询 | `log_query`、`log_query_result` | 控制面→节点 | 白名单/路径/范围/脱敏/审计；禁止任意 shell | `security-node.md` §12 |
| 异常 | `anomaly_event` | 节点→控制面 | 主动上报与 Linux 复读共用关联字段；只追加 | `security-node.md` §10.7 |

### 6.3 横切 API 规则（C）

1. **幂等键**：创建任务、修订、冻结、审批、派发、停止、回执、证据分片、领取租约、释放、补传、门禁推进，均须按 `domain.md` §16 持久化；同键不同载荷返回 `IDEMPOTENCY_KEY_REUSED`。
2. **错误模型**：使用 `domain.md` §18 错误码；未登记错误码 fail-closed；错误码不替代五轴。
3. **分页/排序**：游标分页优先；时间/序号排序必须稳定；禁止用 offset 深分页作为审计/事件主路径。
4. **上传/下载**：分片、断点续传、幂等去重；下载按访问级别裁剪；原始材料下载需审计。
5. **SSE/轮询**：SSE 为辅，轮询/长轮询为降级路径；断线不得丢状态；事件带 `seq`/游标；任务卡带 `freshness`。
6. **审计**：所有写操作与原始材料访问写审计；审计失败不得静默放行敏感访问。
7. **鉴权**：服务端裁剪；UI 隐藏不算访问控制；未知角色/关系/策略一律 DENY。
8. **版本化**：`schema_version` 是载荷一部分；未知版本 fail-closed；破坏性变更升主版本。
9. **OpenAPI**：P2-03 产出候选 OpenAPI；当前不存在已冻结 OpenAPI，本文件不定义具体 schema。

---

## 7. Windows Node Agent 边界（F + C）

### 7.1 固定边界（F）

| 边界 | 要求 | 来源 |
|---|---|---|
| 生成/修改权 | Linux 独占脚本、音频资源、异常规则、判据、证据要求、Execution Bundle 的生成/修复/审核/冻结 | B-4；模块 §2.2 |
| 执行权 | Windows 只校验并执行冻结 bundle；不生成/修改正式交付物 | B-4；`security-node.md` §1/§11 |
| 判定权 | Windows 不写 `business_verdict`/`verification_status`/最终 PASS/FAIL；回执 `used_for_decision=false` | B-5；`domain.md` §12.1；`security-node.md` §10.5 |
| 通信 | 仅出站 TLS 1.3 + mTLS；节点主动长轮询；无入站管理端口 | `security-node.md` §9 |
| 身份 | 每节点独立 X.509 + Ed25519；证书 90 天、第 60 天续期、重叠 7 天 | `security-node.md` §1/§6 |
| 命令面 | 闭集 `static_check`/`smoke`/`formal`/`diagnostics`/`cleanup`；STOP/Log Query 独立消息；无 shell/PowerShell/cmd/SSH/argv | `security-node.md` §11 |
| 离线 | 已启动冻结压测继续；不接新 Job；本地安全 STOP 可用；重连 STOP-first | `security-node.md` §13 |
| 清理/释放 | 本地停止、安全清理、占用对账后才可释放；缺回执只阻断释放确认 | `domain.md` §15.4；`evidence-verdict.md` §12/§13 |

### 7.2 候选组件与部署形态（C）

| 组件 | 候选职责 | 运行位置 | 明确禁止 |
|---|---|---|---|
| Node Service | 注册、长轮询、心跳、Job 领取、STOP 接收、spool 管理、回执补传 | Windows 服务（Session 0） | 直接访问音频/GUI；生成/修改冻结工件 |
| Interactive Executor | 在登录会话内调用固定 lstest 适配器、播放/采集、设备动作 | 交互式用户会话 | 在 Session 0 内替代音频；接受任意命令 |
| Bundle Verifier | 校验 bundle/artifact digest、版本、路径、签名、action/mode | Node Service | 信任未验签/未知版本 |
| Fixed Adapters | `lstest` 固定版本 + 项目-lstest 适配 + 固定运行时绑定 | 交互式会话 | 写 `tool.log` 自由文本；自行格式化识别字段 |
| Evidence Collector | 采集音频/日志/结果/回执/证据引用 | 交互式会话 | 删除证据；把远程可读当归档 |
| Local Log/Spool | D: 本地日志、待补传回执/证据、容量阈值 | 节点本地 | 覆盖/删除未 ACK 的 spool |
| Local Safety Stop | 看门狗/本地人工安全停止 | 节点本地 | 依赖 Linux 在线；执行任意命令 |

### 7.3 仍需 A-0 事实（D）

- Windows 主机/OS build、服务账户、交互式会话可用性。
- 节点 Python 运行时、lstest 固定版本、适配器版本。
- 音频回放/采集端点、串口/USB 端点、GUI 会话。
- D: 容量、spool 有效上限、节点时区/时钟源。
- 节点证书、CA、注册 token 签发人、出站代理/防火墙。
- 待 STOP、残留租约、未完成清理的初始状态。

> 以上未关闭前，P2-04 只能写候选流程与接口清单，不能写“可部署的 Node Agent 方案”。

---

## 8. 证据存储（F + C）

### 8.1 分层

| 层 | 内容 | 权威/角色 | 保留/备份 | 来源 |
|---|---|---|---|---|
| PostgreSQL | manifest、evidence_item、chunk 索引、digest、locator、状态、判定/复核引用 | 权威索引 | 随数据库备份；RPO ≤1 min | B-6；`evidence-verdict.md` §5/§6 |
| Linux 本地内容存储 | 原始音频、日志、结果、回执、证据 blob；内容寻址 | 权威热副本 | 30 天热存；无归档不删除 | B-6；需求基线 §12 |
| Windows D: | 完整大日志、run 工作区、spool | 节点本地事实/缓存 | 不是异机备份；按需读取 | 交付验收 §2.1；`evidence-verdict.md` §10 |
| 第二服务器 | PostgreSQL 异步从库 + 证据增量同步 | 热备 | 证据约 15 min 增量 | B-6；决策登记册 §1.3 |
| 局域网 NAS | WAL 归档、每日全量、证据归档、配置/密钥加密备份 | 归档 | 目标 RTO 2–4h | B-6；决策登记册 §1.3 |
| `NoahsArkdata` | 本地导出/冷备暂存 | 暂存 | 不是唯一副本 | 决策登记册 §1.1 |

### 8.2 候选存储规则（C）

1. **内容寻址**：路径由 digest 派生或按 digest 分片；`evidence_id` 稳定，locator 可变。
2. **两阶段写**：先写 blob → 重算 digest/size → 再登记 PostgreSQL 索引；未登记完成的 blob 视为 orphan，可清理但需审计。
3. **分片上传**：`(evidence_id, chunk_index, content_digest)` 幂等；partial 是状态不是失败；超期转 `INCOMPLETE`，不删除、不判业务失败。
4. **部分证据**：manifest 区分 `expected/received/verified`；必要证据缺失不得 PASS；可选诊断缺失不阻断。
5. **删除**：仅“已归档 + 已授权 + 已审计”后可清理热副本；原始证据删除永远不是磁盘保护的自动后果。
6. **按需读取**：Linux 通过白名单读取 Windows D: 可形成核验证据，但不满足归档/保留；节点丢失后未读取部分即丢失。
7. **释放独立**：设备释放不等待 GB 级日志归档或最终判定；证据上传/校验可在释放后继续。
8. **归档**：归档只改 locator，不改 `evidence_id`/digest；历史判定/审计引用仍可解析。

### 8.3 待定（D）

- 证据根路径、容量、文件系统、挂载点（E01–E03）。
- 第二服务器/NAS 端点、协议、容量、挂载（E05–E07）。
- 备份加密算法、密钥保管/轮换（E10）。
- 归档验证方式、删除审批流（E14、Q-EV-03）。
- 必需证据切片粒度（Q-EV-01）；manifest 最终 schema。
- 真实音频/日志体积与 30 天容量测算。

---

## 9. UI 集成点（C，等待 P1 冻结）

### 9.1 当前 UI 候选状态

| 文档 | 版本/规模 | 状态 | P2 可用性 |
|---|---|---|---|
| `ui-design-research.md` | 525 行 | 候选 | 可作为原则输入，不是冻结件 |
| `ui-information-architecture.md` | v0.3，332 行 | 候选 | 12 区域/39 路由/8 子视图为**建议冻结项**，未评审 |
| `ui-design-system.md` | 289 行 | 候选 | 令牌/组件/状态语言候选，未视觉 QA |
| `ui-screen-specification.md` | v0.2，260 行 | 候选 | 屏幕族/门禁落点/AC 追溯候选 |
| `ui-baseline-gap-analysis.md` | v0.2，667 行 | 分析稿 | 旧 UI 处置与新 IA 理由 |
| `ui-candidate-verification.md` | 不存在 | 缺失 | **P1-01..P1-04 不能记为 PASS** |
| P1-05..P1-08 | 未开始 | 未开始 | 无高保真、无视觉 QA、无冻结 |

### 9.2 候选 UI 区域到后端/API 的映射

| UI 区域 | 候选路由 | 消费的候选服务/API | 关键状态/显示边界 | 依赖 |
|---|---|---|---|---|
| Mission Control | `/console` | S-08 TaskCard/事件、S-03 Run、S-04 Lease | blocked/stale/offline/reconciling/unknown-progress；离线仍占用 | P1-08；TaskCard 契约 |
| Intake & Revisions | `/console/intake/*` | S-02 Task/Revision、S-01 上传 | 三入口来源、冲突/缺口、冻结范围、父修订 | P1-08；P2-03 |
| Tasks | `/console/tasks/*` | S-02、S-03、S-07、S-08 | 五轴不折叠；审批/门禁/证据/判定分离 | P1-08；契约 |
| Runs & Attempts | `/console/runs/*` | S-03、S-04、S-05 | mode、attempt、重试、FLAKY_SUSPECT、offline+running+occupied | P1-08；契约 |
| Evidence & Verdict | `/console/evidence/*`、`/verdicts` | S-06、S-07 | expected/received/verified；节点事实 vs Linux 判定；缺回执≠证据不完整 | P1-08；契约 |
| Devices & Nodes | `/console/devices/*`、`/nodes/*` | S-04、S-05 | lease/通信/占用/permit 四信号；draining/quarantined/reconciling | P1-08；契约 |
| Reports & Delivery | `/console/reports/*` | S-08 | 14 章节、分母口径、四类记录、默认摘要 | P1-08；报告契约 |
| Knowledge | `/console/knowledge/*` | S-08 | 候选/条目分离；推广权限；不自动合入 | P1-08；知识契约 |
| Runtime & Toolchain | `/console/runtime/*` | S-08 + 工具链事实 | lock/drift/版本；访问级别 Q-09 未决 | P1-08；Q-09 |
| Agents & Reviews | `/console/agents/*`、`/reviews` | S-08/S-09 | 注册表/评审；Q-09 未决 | P1-08；Q-09 |
| Audit & Recovery | `/console/audit/*`、`/recovery` | S-09、S-08 | 只追加、before/after、STOP-first 对账、恢复顺序 | P1-08；契约 |
| Settings & Access | `/console/settings/*` | S-09 | 角色/任务关系/保留/通知；永不显示密钥 | P1-08；权限契约 |

### 9.3 UI 对接必须保留的显示边界（F）

1. Windows 回执只显示 `node_observed_*` + `used_for_decision=false`，不得渲染为平台判定。
2. 五轴逐项显示；`COMPLETED`/`SKIPPED`/`EXPECTED`/`RELEASED` 不是 PASS。
3. 通信、占用、执行许可、执行状态、新鲜度分别显示；`OFFLINE` 不等于“已停止/空闲/可重派”。
4. 设备释放、证据完整性、最终判定三平面分离；缺 `cleanup_receipt` 只显示“释放未确认、保持占用”。
5. 未知总量显示“未知”，`percent=null`；不得用 0%/99%/阶段序号冒充百分比。
6. 无权限保留只读摘要 + disabled 动作 + 原因；不隐藏整页；客户端过滤不算鉴权。
7. 服务端投影是唯一数据源；UI 不自算正式分母、不推断状态、不把烟测/模拟/回放计入正式样本。

### 9.4 等待 P1 冻结的具体项（D）

- P1-02 IA：12 区域是否收敛为 10（Q-02）；路由 `/console` vs `/aitest`（Q-03）；RT/AG 访问级别（Q-09）；`blocker.owner` 粒度（Q-10）。
- P1-03 设计系统：视觉方向（Q-01）；深色模式（Q-04）；`wideTablet`/`navRailWidth` 令牌；组件像素规范。
- P1-04 线框：39 条路由 manifest；每屏状态 fixture 最低集。
- P1-05 高保真：空态/加载/阻塞/离线/stale/错误/无权限/部分证据。
- P1-07 视觉 QA：Playwright 截图、深浅色、控制台检查、可访问性。
- P1-08：UI 评审与冻结包。

---

## 10. 部署与恢复关注点（F + C）

### 10.1 候选部署拓扑（C）

| 层 | 候选组件 | 说明 | 依赖 |
|---|---|---|---|
| 入口 | 反向代理 / TLS 终止 | 443；API/UI/SSE；节点仅出站 | L08/N03/N04 |
| 应用 | API 进程 | REST/SSE/上传/下载 | P2-01/03 |
| 应用 | Orchestrator 进程 | 门禁、Run、租约、派发、STOP | P2-01/04 |
| 应用 | Worker/Verifier 进程 | 证据校验、独立复核、报告/投影 | P2-01/06 |
| 数据 | PostgreSQL | 唯一正式库；从库在第二服务器 | L05–L07/E05 |
| 存储 | Linux 证据卷 | 内容寻址；容量监控 | E01–E03 |
| 存储 | 第二服务器 | 证据增量同步 + PostgreSQL 从库 | E05 |
| 存储 | NAS | WAL 归档、每日全量、证据归档、加密配置备份 | E06/E10 |
| 节点 | Windows Node Service + 交互执行器 | 仅出站；Session 0 + 交互会话 | W01–W19 |
| 运维 | systemd/日志/监控 | 进程守护、健康检查、审计日志 | L11 |

### 10.2 恢复顺序（F）

```text
1. 数据库恢复（PostgreSQL 主库/从库/PITR）
2. 证据索引/manifest 与内容存储 digest 对账
3. 任务 / 修订 / 运行 / 租约 / 设备占用 / STOP 待处理 对账
4. 确认无重复副作用、无未对账占用后，才允许新派发
```

**硬规则：**

- 恢复不能重建 task、改写 revision、重复设备动作或重复采样。
- 未完成对账前设备保持占用，不重派。
- 已启动冻结压测在控制面恢复/通信中断期间继续；恢复后先补传/去重/对账。
- 备份恢复必须实际演练；未演练不得声称 RPO/RTO 达标。
- 节点丢失/证书撤销/时钟偏差/存储耗尽均需 fail-closed 与审计。

### 10.3 目标 RPO/RTO（F，目标值）

| 对象 | RPO | RTO | 验证 |
|---|---|---|---|
| PostgreSQL | ≤1 min | ≤30 min | 恢复演练报告 |
| 证据 | ≤15 min | ≤1 h | 第二服务器/NAS 恢复演练 |
| 整机 | — | ≤4 h | 整机重建演练 |

> 这些是目标值，未演练前不是实际达标值；P2 方案必须把“演练”写成验收前置，而不是部署完成即宣称。

### 10.4 待 A-0 事实（D）

- 正式控制面主机、PostgreSQL 版本/实例/端口/备份模式。
- 证据根/容量/文件系统/挂载；D: 容量与 spool。
- 第二服务器/NAS 端点/协议/容量/密钥保管。
- CA/证书/DNS/防火墙/代理；时钟偏差实测。
- 真机窗口、T5/T6 排期、升级/回滚联系人。

---

## 11. 不变量保持清单（供 P2 评审逐项核对）

| # | 不变量 | P2 必须体现 | 证据 |
|---|---|---|---|
| 1 | 一个 `task_id` 长期身份，不创建 successor | 任务/修订域只有一个 task 主键；修订用 parent/superseded 关系 | `domain.md` I-01 |
| 2 | 一个 task 恰好一个 lead agent | Task.lead_agent_id 单值；会话不替代执行授权 | I-02 |
| 3 | revision 冻结后不可变；变化派生新 revision | 冻结 CAS；禁止 UPDATE 冻结内容 | I-03 |
| 4 | 每 revision 至多一个有效批准 | 部分唯一索引/事务判定 | I-04 |
| 5 | 门禁 G0→G7；G4 烟测不入分母 | 编排状态机；Run.mode | I-05 |
| 6 | 五轴独立；正式 PASS 五条件 | 五轴列；判定服务校验 | I-06 |
| 7 | 烟测/模拟/回放永不进入正式分母 | denominator_eligible 服务端派生 | I-07 |
| 8 | 已启动冻结压测断线继续；离线≠空闲/停止 | communication/occupancy/permit 三字段 | I-08 |
| 9 | STOP-first 重连；旧 epoch 不取得执行权 | 待 STOP 队列；epoch 校验 | I-09 |
| 10 | 释放只依赖本地停止/安全清理/占用对账 | 三项布尔；不等归档/判定 | I-10 |
| 11 | 缺 cleanup_receipt ≠ evidence INCOMPLETE | 释放状态与 evidence_status 分字段 | I-11 |
| 12 | 回执只含事实，不含最终判定 | `node_observed_*`、`used_for_decision=false` | I-12 |
| 13 | 每 run/attempt 证据独立；旧证据不并入 | evidence_id/run_id 关联；禁止跨 run 合并 | I-13 |
| 14 | 重试新 attempt；首次不覆盖；FLAKY_SUSPECT | attempt_ordinal/retry_of；单列 | I-14 |
| 15 | 原始事件/证据/判定只追加；归档只改 locator | 审计 INSERT-only；locator 可变 | I-15 |
| 16 | UTC 时间、UUID、sha256 前缀 | 全库约定 | I-16 |
| 17 | 校验失败 fail-closed；未知枚举不得当 PASS | 错误码/未知枚举处理 | I-17 |
| 18 | PostgreSQL 唯一正式库；禁止 SQLite | 连接/迁移/测试约束 | I-18 |
| 19 | 设备释放 ≠ 通过；归档 ≠ 判定；读取 ≠ 备份 | 三平面/归档/按需读取语义 | `evidence-verdict.md` P-07..P-09 |
| 20 | Linux 独立复核是正式 PASS 必要条件 | verification_record；节点不可生成 | `evidence-verdict.md` §16 |
| 21 | 知识候选不可自动合入 | 候选/条目分状态；推广权限 | `ui-report-knowledge-audit.md` §4 |
| 22 | 原始材料访问有审计；默认摘要 | 访问级别/裁剪/审计 | `ui-report-knowledge-audit.md` §5/§6 |

---

## 12. 依赖表：P2 工作必须等待什么

> 说明：`可先做` 只表示可以准备候选草案或做一致性核对，不表示可以冻结或实施。

| P2 项 | 交付内容 | 等 P1 UI 冻结 | 等 A-0 事实 | 等契约冻结 | 其他依赖 | 可先做 |
|---|---|---|---|---|---|---|
| P2-01 服务端总体架构 | 控制面服务、PostgreSQL、证据存储、队列/租约、Node Gateway、报告/知识服务 | 否（后端边界可先定） | 部分：主机/端口/存储/拓扑影响部署形态 | 是：实体边界、所有权、状态机 | 架构 §13；决策登记册部署拓扑 P0-11 建议三进程 | 可做模块依赖图、服务候选边界、故障域分析 |
| P2-02 数据模型与迁移 | 表、索引、约束、事务边界、迁移/回滚、证据索引/寻址 | 否 | 部分：证据容量/文件系统/PostgreSQL 实例 | **是**：字段/枚举/状态/错误码/幂等键 | `domain.md`/`evidence-verdict.md`/`ui-report` 候选 | 可做逻辑域、约束清单、迁移风险清单；不可写 DDL/迁移 |
| P2-03 API 契约 | OpenAPI、鉴权、错误模型、幂等、分页、上传/下载、SSE/轮询、审计 | **部分：UI 消费字段/路由需 P1 冻结** | 部分：端口/DNS/TLS/证书 | **是**：资源/字段/错误码/状态 | `domain.md` §16/§18；`ui-report` §2/§6 | 可做资源清单、错误映射、幂等矩阵；不可冻结 OpenAPI |
| P2-04 Windows Node Agent | 服务形态、Session 0/交互会话、工具链、工件校验、执行器、离线 spool、STOP、清理 | 否（Agent 本身） | **是**：Windows 主机/OS/账户/会话/端点/D:/证书/网络 | **是**：`security-node.md`/`domain.md`/`thresholds.md` | B-4；`security-node.md` §11/§13 | 可做组件边界、消息时序、失败矩阵；不可写可部署方案 |
| P2-05 UI 实现架构 | 框架、路由、状态、组件库、设计 token、i18n、权限渲染、错误边界 | **是（P1-08 冻结）** | 部分：部署/代理/运行时 | **是**：投影字段/访问级别/枚举 | P1-02/03/04/05/07；`ui-report` §2/§6 | 可做候选技术选型对比；不可实现或冻结 |
| P2-06 安全与隐私 | 身份、证书、密钥、最小权限、访问审计、脱敏、原始材料保护、备份加密 | 部分：权限渲染/无权限态需 P1 | **是**：CA/证书/token/备份密钥/网络 | **是**：`security-node.md`/`ui-report` §6 | B-6；D-01/D-03 | 可做威胁模型/权限矩阵/审计事件清单 |
| P2-07 部署与灾备 | 进程/服务、反代、TLS、监控、日志、第二服务器、NAS、本地备份、恢复演练 | 部分：UI 静态资源/路由 | **是**：主机/存储/NAS/第二服务器/恢复窗口 | **是**：数据库/证据/恢复语义 | B-6；RPO/RTO 目标 | 可做部署候选图、恢复 runbook 草案、演练清单；不可宣称达标 |
| P2-08 可观测性 | 事件、指标、追踪、告警、任务卡投影、stale、证据完整性指标 | **部分：TaskCard/stale/UI 显示需 P1 冻结** | 部分：节点健康/容量事实 | **是**：事件/字段/阈值/投影契约 | `ui-report` §2；`thresholds.md` | 可做事件/指标目录草案、stale 判定输入清单 |
| P2-09 落地方案评审与冻结 | 一致性检查、风险/回滚、版本归档、云端同步 | **是（P1-08）** | **是（A-0）** | **是（P0-04..P0-08 全部）** | P2-01..P2-08 完成；所有 open-blocker 关闭 | 不可提前冻结 |

### 12.1 三个依赖门的含义

| 门 | 当前状态 | 关闭条件 | 影响 |
|---|---|---|---|
| **P1 UI 冻结（P1-08）** | 未通过；四份候选稿 + 四个 progress；独立核验缺失；原型/视觉 QA/冻结未做 | `ui-candidate-verification.md` 逐项 PASS；P1-05..P1-07 完成；P1-08 冻结归档 | P2-05 不能实现；P2-03 的 UI 消费字段/路由不能冻结；P2-08 的 TaskCard/stale 投影不能冻结 |
| **A-0 事实** | 未通过；85 条 20 known/14 placeholder/51 unknown | 节点/设备/证书/存储/NAS/第二服务器/恢复演练/真机窗口等真实值登记 | P2-04 不能写可部署方案；P2-07 不能写可执行部署/灾备；P2-02 容量/存储决策受限 |
| **契约冻结** | `docs/contracts/` 全部 `frozen-candidate v1` | P0-04..P0-08 评审通过并记录内容哈希/评审人/时间/范围；open questions 收口 | P2-01/02/03/04/06/08 的字段、枚举、错误码、消息、阈值不能作为冻结依据 |

### 12.2 可以立即准备（不越过冻结门）的工作

1. 服务边界/数据域/API 资源清单的**候选草案**与差异分析。
2. 五轴、释放三平面、离线/STOP-first、烟测隔离的**一致性核对表**。
3. 数据库约束/幂等键/并发规则的**检查清单**（不写 DDL）。
4. Node Agent 固定 action/消息/失败矩阵的**核对清单**（不写实现）。
5. 证据存储容量/恢复演练的**问题清单**（不填真实值）。
6. UI 区域到 API/投影的**对接矩阵**（以 P1 候选稿为参考，不冻结路由/字段）。
7. 部署/恢复/安全/可观测性的**风险与待决清单**。

---

## 13. 未决依赖清单（D）

### 13.1 Phase 1 / UI 相关

| ID | 未决项 | 阻塞 | 当前证据 | 下一步 |
|---|---|---|---|---|
| U-01 | P1-01..P1-04 独立核验缺失 | P1 PASS、P2-05 | `ui-candidate-verification.md` 不存在；旧核验句柄失效 | 新派短范围只读核验，逐项 PASS/NEEDS-FIX |
| U-02 | UI 原型/视觉 QA/冻结未做 | P1-08、P2-05、P2-09 | P1-05..P1-08 未勾选 | 核验通过后做 P1-05..P1-08 |
| U-03 | 视觉方向未决 | 设计 token/组件 | Q-01：v2 Voyage Ledger / Apple v3 / 混合 | 用户/P1-02 裁决 |
| U-04 | 12 区域是否收敛为 10 | IA 路由/权限 | Q-02 | IA 评审 |
| U-05 | 路由前缀/兼容期 | API/深链 | Q-03 `/console` vs `/aitest` | 实现/运维评审 |
| U-06 | 深色模式是否进入 V0.0.1 | 令牌/QA | Q-04；候选建议 light-first | 用户/P1 评审 |
| U-07 | RT/AG 访问级别 | P2-03/P2-05 权限渲染 | Q-09 | 权限/架构评审 |
| U-08 | `blocker.owner` 显示粒度 | 任务卡/UI | Q-10 | 产品评审 |
| U-09 | `EXPECTED` 产品语义与视觉家族 | 五轴展示 | 设计系统 §10 未决 | 产品/契约评审 |
| U-10 | `wideTablet`/`navRailWidth` 令牌 | 响应式实现 | 设计系统 §7 要求先登记 | P1-03 令牌文件 |

### 13.2 A-0 / 环境相关

| ID | 未决项 | 阻塞 | 当前状态 | 下一步 |
|---|---|---|---|---|
| U-11 | Windows 节点事实（主机/OS build/服务账户/Agent 版本/交互会话） | L3、P2-04 | `environment-inputs.md` W01–W19 多为 unknown/placeholder | 节点负责人登记并验证 |
| U-12 | 设备事实（型号/固件/硬件版本/脱敏序列号/音频/串口/电源/恢复） | L3/L4、P2-04 | D01–D12 未提供 | 设备负责人登记 |
| U-13 | 真实 formal profile 与任务脚本 | L3/L4、P2-04/证据 | T02/T03/T06 unknown | lstest 负责人提供绝对路径/`profile_id`/规则数/摘要 |
| U-14 | 证据根/容量/NAS/第二服务器/备份密钥/恢复演练 | L4、AC-14、P2-02/07 | E01–E14、L16/L18 未落地 | 所有者/运维提供并演练 |
| U-15 | PostgreSQL 版本/实例/端口/备份模式 | P2-02/07 | L06 placeholder；L07 unknown；本机未安装 | 锁定版本、提供 DSN/实例 |
| U-16 | CA/证书/注册 token 签发人/DNS/防火墙 | L3、P2-06/07 | N01–N06 unknown/placeholder | 安全/网络负责人确认 |
| U-17 | 真机窗口/T5/T6/固件白名单/回滚联系人 | L3–L5 | R01–R08 unknown | 所有者排期 |
| U-18 | lstest 本地 `main f32aebc` vs `origin/main 7190ab6` 差异 | Node/证据契约 | 本地领先 1 个提交 | 节点侧 pin 前确认基线 |

### 13.3 契约/设计相关

| ID | 未决项 | 阻塞 | 当前状态 | 下一步 |
|---|---|---|---|---|
| U-19 | 字段/枚举/状态/错误码/幂等键冻结 | P2-01..P2-04/06/08 | 全部 `frozen-candidate v1` | P0-04..P0-08 评审与冻结记录 |
| U-20 | manifest 完整 schema/必要证据集/摘要扩展 | P2-02/03/06 | Q-EV-01、Q-EV-04 | P0-06 + 任务级 `evidence_requirements` |
| U-21 | 证据签名/回执签名/证书链 | P2-04/06 | Q-EV-02、security §20 | P0-05 |
| U-22 | 访问级别与 RBAC 映射 | P2-03/05/06 | Q-EV-06、D-03、Q-09 | P0-07 + 权限评审 |
| U-23 | 审批升级对象/等待期/提醒渠道 | P2-03/06 | T-14、D-04 | P0-08 + 组织角色映射 |
| U-24 | 样本/阈值/重试/预算模板选择 | P2-03/08 | 任务级；无全局值 | 任务修订冻结 |
| U-25 | 设备等价字段值/跨设备替代 | P2-02/04 | Q-08、T-05 | 任务级 + P0-10 |
| U-26 | 工具链版本/模型绑定/插件 commit | P2-01/04 | T-15、F-01 | Phase 2–3 重锁 |
| U-27 | SQLite/旧口径历史残留与 OpenSpec v2 旧口径 | 全部 P2 | `source-reconciliation.md` 已标历史，但仍需实现时避免 | P2 文档只引用规范层 |
| U-28 | Phase 0 归档 open-blocker T-23 | Phase 0 关闭 | 负责人/状态未定 | Orchestrator 指定并完成 |

### 13.4 5 个 open-blocker（来自 P0-09）

1. T-09 节点外部事实。
2. T-10 设备外部事实。
3. T-11 真实 formal profile 与任务脚本。
4. T-12 证据根/NAS/第二服务器/备份密钥/恢复演练。
5. T-23 Phase 0 验证与归档。

> 这 5 项不是 P2 文档能自行关闭的设计问题；必须在对应责任方提供事实或完成归档后才能关闭。

---

## 14. 建议的下一步（不冻结、不实施）

1. **先补 P1 独立核验**：对四份 UI 候选文档逐项 PASS/NEEDS-FIX，落盘 `docs/delivery/ui-candidate-verification.md`；未落盘前不勾选 P1-01..P1-04。
2. **收口契约 open questions**：按 P0-04..P0-08 逐项确认字段/枚举/签名/阈值/权限映射；冻结时记录内容哈希、评审人、时间、适用范围。
3. **补 A-0 事实**：优先节点、设备、formal profile/脚本、证据/NAS/第二服务器/恢复演练；未知值继续 fail-closed，不用默认值填充。
4. **在 P1-08 后才写 P2-05 与 UI 对接**：之前只维护候选对接矩阵，不冻结路由、组件、字段。
5. **P2-01..P2-09 保持未勾选**：直到各自依赖满足；P2-09 只能在 P1-08、A-0、契约冻结和 P2-01..P2-08 完成后评审冻结。
6. **每次阶段推进更新** `construction-progress.md` 与 `.omo/ulw-execute/ledger.jsonl`，但本文件不代替进度记录。

---

## 15. 非声明与复核

### 15.1 非声明

- 本文件不是 Phase 2 落地方案，不是架构/数据/API/Node Agent/UI 的实现设计。
- 本文件没有创建产品代码、API、迁移、UI 组件、测试或部署配置。
- 本文件没有修改 `docs/contracts/`、`docs/v2/`、`openspec/`、`plan.md`、`.omo/plans/` 或任何源码。
- 本文件没有解除 P1 未冻结、契约未冻结、A-0 未通过或实现未授权状态。
- 本文件没有提交或推送。

### 15.2 复核清单

- [x] 只新增 `docs/delivery/phase2-input-map.md`。
- [x] P2-01..P2-09 保持未勾选，未写落地计划。
- [x] Linux 生成/判定权威、Windows 事实-only、离线续跑、STOP-first、释放/证据/判定分离、PostgreSQL-only 均有明确落点。
- [x] 依赖表区分 P1 UI 冻结、A-0 事实、契约冻结。
- [x] 候选（C）与已批准/已评审约束（F）分开标记；未决（D）单列。
- [x] 未包含凭据、IP、用户名、真实设备序列号或原始材料。
- [x] 输出文件重读后报告路径与未决依赖。

### 15.3 复核命令（只读）

```bash
cd /home/bszheng/NoahsArk
test -s docs/delivery/phase2-input-map.md
wc -l docs/delivery/phase2-input-map.md
grep -n "P2-01\|P2-09\|P1-08\|A-0\|frozen-candidate\|open-blocker" docs/delivery/phase2-input-map.md | head
git status --short docs/delivery/phase2-input-map.md
```

> 预期：文件存在且非空；P2 复选框未被本文件修改；工作区只多出本文件（其余改动来自既有工作单元）。
