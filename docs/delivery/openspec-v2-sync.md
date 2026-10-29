# P0-03 规范同步证据报告：`docs/v2/**` 与 `openspec/**`

> 任务：P0-03 同步规范文档冲突（Retry，重做并补齐可验证产物）
> 执行日期：2026-10-28（Asia/Shanghai）
> 状态：**文档同步完成**（2026-10-29 按独立验证 F1/F2/F3 返工修订，见 §0.1；同日按独立复核追加 §0.2 状态回填）。本报告是 P0-03 的权威证据；P0-03 不构成实现、测试、部署、验收或发布授权。
> 事实源优先级：已批准 `.omo/drafts/00-baseline`、已评审 `.omo/drafts/01-design`、`.omo/drafts/02-delivery` 正文与根 `plan.md` 中更晚的批准记录 > `.omo/plans/noahsark-platform-delivery.md` > `docs/contracts/`（frozen-candidate）> `docs/v2` / `openspec`。
> 同步对象：`docs/v2/**`、`openspec/**`；返工后按计划同时写入 `docs/VERSIONING.md`。本报告路径：`docs/delivery/openspec-v2-sync.md`。
> 边界：初稿未修改 `.omo/plans`、`.omo/boulder.json`、根 `plan.md`、`docs/VERSIONING.md`、`README.md`、`docs/contracts`、`docs/ssh.txt`；2026-10-29 返工仅补写 `docs/VERSIONING.md` §2.4 与本报告（见 §0.1），其余禁止路径仍未修改；未提交、未推送、未修改产品代码。

---

## 0.1 返工修订记录（2026-10-29）

独立验证报告 [`p0-03-verification.md`](./p0-03-verification.md) 判定 NEEDS-FIX。本轮只修该报告列出的 F1/F2/F3，不扩大范围。

| 编号 | 问题 | 本轮处置 | 复核位置 |
|---|---|---|---|
| F1 | `docs/VERSIONING.md` 未按 P0-03 计划写入六项规则 | 在 `docs/VERSIONING.md` 新增 §2.4「P0-03 同步后的六项规则（导航摘要）」，逐项登记 PostgreSQL、五轴、离线续跑、STOP-first、释放/证据/判定分离、`cleanup_receipt`，并声明规范效力仍来自第 1 层与根 `plan.md`。 | `docs/VERSIONING.md` §2.4 |
| F2 | 正式 PASS 谓词漏 `execution_status=COMPLETED` | 在 4 处 formal PASS 谓词加入 `execution_status=COMPLETED`，并明确 `RUNNING`/`NOT_STARTED` 不得判正式 PASS。 | `docs/v2/SOLUTION.md` §5.4、`docs/v2/IMPLEMENTATION-PLAN.md` §5.1、`openspec/.../design.md` Data and completion、`specs/completion-gate/spec.md` Formal PASS |
| F3 | 报告中 §8.3 命中数、§5.2 Scenario 数、C-19/§9.7 状态过期 | 按复核命令重跑并改正为 8 行危险旧口径命中、3 Requirement / 6 Scenario、`source-reconciliation.md` 已由 P0-02 补齐；同步更新 §10 路径统计与本报告行数口径。 | §4 C-19、§5.2、§8.3、§8.7、§9.7、§10 |

> 历史保留：本轮不删除初稿中的任何“历史/已取代（2026-10-28）”标签；对初稿错误数字采用“初稿误记 + 复核实测”并列说明，不静默改写历史结论。

---

## 0.2 状态回填记录（2026-10-29）

独立复核 [`source-sync-followup-verification.md`](./source-sync-followup-verification.md) §4.1 判定本报告 NEEDS-FIX，原因仅为 §9.1/§9.2 的“未解决”记录落后于后续已完成的修复，证据主体 PASS。按该报告 F-02 建议（归档索引附链接，不原地重写历史报告），本节只追加状态回填，§9.1/§9.2 原文整段保留，仅在段首加日期标记指向本节。

| 原条目 | 原文状态（2026-10-28 记录） | 2026-10-29 回填 | 后续证据 |
|---|---|---|---|
| §9.1 源级草案内部矛盾 | “I-21 仍写…”“§7 租约规则仍写…”“§2.6 仍写…”，并建议“后续单独任务修订草案正文” | **已由后续任务修正**。架构提案 I-21、§7 规则 4/6 与模块设计 §2.6、§4.2 均已改写；原文保留在各文件“修订说明”表 | [`approved-draft-reconciliation.md`](./approved-draft-reconciliation.md) §2–§4；`architecture-proposal.md:91,126,128,379-389`；`module-design.md:101-114,203,385-391` |
| §9.2 `docs/contracts` 租约措辞 | “`security-node.md` 仍有 `lease_expired` 旧措辞”“P0-05 需修正契约包措辞” | **已由 P0-05 修正**。`docs/contracts/README.md:58` 已改为“已无 `lease_expired` 旧措辞”；`grep lease_expired docs/contracts/security-node.md` 为 0 命中；`lease.state=expired` 仅表示续约截止的说明保留 | [`phase0-contract-remediation-verification.md`](./phase0-contract-remediation-verification.md) §3 F-11（`:109`） |

回填范围与不变结论：

- 本次只回填上述两条记录，§9.3–§9.9 其余条目状态不变；不删除任何原文，不改变任何历史结论。
- 本节不改变本报告的 P0-03 边界：不构成实现、测试、部署、验收或发布授权。
- **Phase 0 仍未关闭**：A-0 未通过（`a0-readiness-followup.md:16`），`docs/contracts/` 仍为 `frozen-candidate`，5 个 `open-blocker`（T-09、T-10、T-11、T-12、T-23）仍在，契约残余仍待裁决。

---

## 1. 结论摘要

1. **PostgreSQL-only**：`docs/v2` 与 `openspec` 中所有 SQLite 正式数据库口径已修正或加 `历史/已取代（2026-10-28）` 标签；PostgreSQL 被明确为唯一正式数据库，SQLite 只能作为历史参考或只读分析副本。
2. **五轴判定**：旧单一终态 `PASS | FAIL | BLOCKED_HUMAN | CANCELLED | STOPPED | INFRA_ERROR` 统一降为历史别名；当前判定为 `execution_status` / `validity_status` / `business_verdict` / `evidence_status` / `verification_status` 五轴，并分离执行、设备占用、通信、证据和最终判定。正式 PASS 必须同时满足 `execution_status=COMPLETED`、`validity_status=VALID`、`evidence_status=COMPLETE`、`business_verdict=PASS`、`verification_status=PASS`。
3. **离线续跑 / 占用保留**：已启动冻结压测在通信中断、心跳过期或租约过期后继续离线执行；Linux 标记通信 `OFFLINE/STALE`，设备保持 `OCCUPIED`，不新派、不重派、不重播、不重复采样。
4. **STOP-first 重连**：任何重连先处理待 STOP，再补传、去重和对账；旧 epoch/旧租约不得改变当前运行。
5. **释放 / 证据 / 判定分离**：执行结束、设备释放、证据完整性和最终判定分别建模；确认本地停止、安全清理和占用对账后可释放设备，不等待 GB 级日志归档或最终判定。
6. **`cleanup_receipt` 语义**：缺失只阻断“设备释放确认”，设备保持占用；不自动判定整条证据链不完整，也不自动构成业务 FAIL。
7. **历史任务映射**：旧 C1–C7 与 81 项任务只作历史门禁/任务账本；当前范围映射到总计划 Phase 0–6，真实施工 WBS 由 Phase 3 产出。
8. **可验证产物已落盘**：本报告存在且非空；`openspec validate ai-test-platform-v2 --strict` 通过；`git diff --check` 通过；无未加标签的 SQLite/危险旧口径残留（见 §8）。

> 说明：`docs/v2/README.md`、`docs/v2/SOLUTION.md`、`docs/v2/IMPLEMENTATION-PLAN.md` 在本次重做前已有上一轮 P0-03 的部分修改。本次逐项复核、补齐缺口、修正遗漏，并把结果登记在本报告；不以“上一轮已完成”作为完成依据。

---

## 2. 已读取的输入

### 2.1 强制读取项

| 路径 | 读取方式 | 用于确认 |
|---|---|---|
| `.omo/plans/noahsark-platform-delivery.md` | 全文 | 当前唯一执行主线；Phase 0–6；P0-03 范围；PostgreSQL、五轴、离线续跑、STOP-first、释放分离、`cleanup_receipt` 与任务范围要求 |
| `.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md` | 全文 | 已批准需求基线：任务 ID/修订、证据隔离、fail-closed、烟测/正式分离、资源占用与释放 |
| `.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` | 关键章节（§3–§8、§8.4） | 控制面/节点组件、PostgreSQL `SKIP LOCKED`、租约与失联、`cleanup_receipt`、C1–C7 旧门禁来源 |
| `.omo/drafts/01-design/noahsark-v0.0.1-module-design.md` | 关键章节（§2–§6） | 五轴映射、资源资格、租约、证据/判定、旧错误分类到五轴的映射 |
| `.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md` | 全文关键段 | A-0..A-9、AC-11..AC-14、离线续跑、STOP-first、释放/判定分离、恢复顺序 |
| `.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md` | 关键章节（§3–§4） | 五轴取值、`cleanup_receipt` 边界、断线续跑、重连对账、设备释放 |
| `.omo/drafts/05-decisions/noahsark-v0.0.1-decision-register.md` | 全文 | PostgreSQL 选择、五轴判定、资源租约与失联、证据存储与保留 |
| `.omo/drafts/99-history/20261028-step1-step5-review/**/审核记录.md` | 逐份关键条 | 更晚批准记录：离线续跑、STOP-first、清理回执边界、设备释放/判定分离、C1–C7 与五轴 |
| `docs/delivery/workspace-triage.md` | 全文 | P0-01 工作区分诊边界；哪些改动属于 P0-01，避免误改/误认领 |
| `plan.md` | 定向读取 P0-03 相关批准记录与首尾 | 所有者确认记录：PostgreSQL、五轴、断线续跑、STOP-first、释放分离、`cleanup_receipt` |
| `docs/VERSIONING.md` | §1–§3（返工后含 §2.4） | 事实源优先级；`docs/v2`/`openspec` 在 P0-03 同步后降为实现参考；六项规则导航摘要（初稿只读，返工按 F1 补写 §2.4） |
| `docs/contracts/README.md`、`domain.md`、`evidence-verdict.md` | 关键章节 | 字段级候选契约的 PostgreSQL、五轴、`cleanup_receipt`、占用与判定术语（只读，未修改） |

### 2.2 被同步对象（先读后改）

| 路径 | 读取重点 |
|---|---|
| `docs/v2/README.md` | 目录状态、阅读顺序、OpenSpec 状态 |
| `docs/v2/SOLUTION.md` | 总体架构、数据层、主流程、判定、C1–C7、路线图、附录 |
| `docs/v2/IMPLEMENTATION-PLAN.md` | D1–D13、5.1 终态、工具链锁、迁移、测试策略、81 项任务 |
| `docs/v2/UI-DESIGN.md` | 代码基线、C1–C7 门禁印列、租约/心跳、工具链与存储页面 |
| `docs/v2/ACCEPTANCE-REPORT.md` | 81 项硬校验、C1–C7、旧验收结论 |
| `docs/v2/FLOWCHART-STYLE.md` | 旧终态集合与图示口径 |
| `docs/v2/UI-REVIEW.md`、`docs/v2/UI-ORIGINALITY.md` | 旧 UI 评审/原创性记录 |
| `docs/v2/diagrams/README.md`、`docs/v2/wireframes/README.md` | 旧图与线框指针 |
| `openspec/changes/ai-test-platform-v2/README.md`、`proposal.md`、`design.md`、`tasks.md` | 变更边界、D1–D13、终态、工具链、81 项账本 |
| `openspec/changes/ai-test-platform-v2/specs/**/spec.md` | 9 个能力增量；重点 completion-gate、toolchain-compatibility、ui-v2、platform-events-push、task-playbook |
| `openspec/config.yaml` | OpenSpec 配置（仅校验，未修改） |

---

## 3. 已批准决策基线（本次同步依据）

| 编号 | 决策 | 权威来源 | 在文档中的表达 |
|---|---|---|---|
| D-PG | PostgreSQL 是唯一正式数据库；SQLite 不得作为正式数据库 | `plan.md` 2026-10-28 批准记录；`00-baseline` §13；`delivery-acceptance` §5.1；`docs/VERSIONING.md` §2 | 所有 SQLite 正式库口径标 `历史/已取代（2026-10-28）`；PostgreSQL 写入架构、工具链锁、迁移与测试 |
| D-5AXIS | 判定采用五轴并分离执行/设备/证据/判定；正式 PASS 同时要求执行完成 | `module-design` §2.3、§6；`test-strategy` §4.3；`plan.md` S5-3 条 | `execution/validity/business/evidence/verification` + `occupancy_state`/`communication_state`；formal PASS 谓词含 `execution_status=COMPLETED` |
| D-OFFLINE | 已启动冻结压测断线/心跳过期/租约过期继续执行；设备保持占用 | `plan.md` 2026-10-28 离线续跑确认；`delivery-acceptance` §2.1-3、AC-11；`test-strategy` §3.8 | 文档明确“不停止、不回收、不重派、不重播、不重复采样” |
| D-STOPFIRST | 重连先处理待 STOP，再补传/去重/对账 | `plan.md` 2026-10-28 重连确认；`delivery-acceptance` §2.1-3、AC-12；`test-strategy` §3.8 | `STOP-first` 规则写入 SOLUTION、openspec design/completion-gate |
| D-OCCUPIED | 通信离线 ≠ 设备空闲；设备保持 `OCCUPIED` | `plan.md` 2026-10-28 M-04/A-3 确认；`delivery-acceptance` §2.1-3；`test-strategy` §3.8 | 占用与通信分离；`OFFLINE` 不映射为 `IDLE`/`RELEASED` |
| D-SEPARATE | 执行结束、设备释放、证据完整性、最终判定分别建模 | `plan.md` A-3/A-5/AC-13；`delivery-acceptance` §2.1-4；`test-strategy` §3.3/§3.8 | 四类事实独立字段/独立记录；释放不等待归档或判定 |
| D-CLEANUP | 缺 `cleanup_receipt` 只阻断释放确认，不自动等同证据不完整 | `plan.md` S5-3 条；`test-strategy` §3.3；`docs/contracts/evidence-verdict.md` §12 | 设备保持占用；证据完整性独立计算；不自动 business FAIL |
| D-TASKSCOPE | 旧 81 项与 C1–C7 是历史；当前为总计划 Phase 0–6 | `.omo/plans/noahsark-platform-delivery.md` TODOs；`plan.md` 2026-10-28 主计划批准 | 旧账本/门禁保留追溯；新增 Phase 映射表；Phase 3 产出新 WBS |

---

## 4. 发现的冲突与处置

> “原位置”指本轮修改前的 `git HEAD` 或上一轮未完成状态；“处置”指本轮最终动作。所有“历史保留”项均带 `历史/已取代（2026-10-28）` 标签和本报告/总计划链接。

| ID | 文件与位置 | 冲突表述 | 已批准规则 | 处置 |
|---|---|---|---|---|
| C-01 | `docs/v2/SOLUTION.md` §4.8、§7.2、§7 页面表、附录 D2 | SQLite WAL 是数据层；PostgreSQL 是后续选项；工具链锁含 SQLite | PostgreSQL 唯一正式库 | 直接改写为 PostgreSQL + 历史标注；残留 SQLite 仅作历史/只读副本说明 |
| C-02 | `docs/v2/IMPLEMENTATION-PLAN.md` D2、§5.6、P0-03、P8-01、§15 | Flask/SSE + SQLite WAL；WAL/busy_timeout；Python/SQLite；`sqlite temp DB` | PostgreSQL 唯一正式库 | 文件级历史头 + 逐处 PostgreSQL 改写与标签；`BLOCKED_HUMAN` 旧口径加历史标注 |
| C-03 | `docs/v2/UI-DESIGN.md` 头部、工具链页、系统页 | 代码基线 SQLite WAL；工具链组件含 SQLite；存储区块 SQLite WAL | PostgreSQL 唯一正式库 | 头部加历史/同步说明；三处 SQLite 改写为 PostgreSQL + 标签 |
| C-04 | `docs/v2/UI-DESIGN.md` 全文 C1–C7、单一 Verdict 徽章 | C1–C7 是当前完成契约；`Verdict` 单一值 | 五轴 + 分离事实；C1–C7 仅历史门禁 | 头部明确 C1–C7 为旧门禁并给映射链接；不重写整份旧 UI 规格 |
| C-05 | `docs/v2/ACCEPTANCE-REPORT.md` 头部、§1、§9 | 81/81 是当前任务数；C8 仍是当前完成契约缺口 | 81 项为历史；五轴为当前判定 | 加历史/已取代横幅；C8 条目加历史标签 |
| C-06 | `docs/v2/FLOWCHART-STYLE.md` §“为什么没有加 stateDiagram-v2”、语义张力段 | 旧六终态集合；`BLOCKED_HUMAN` 终态待确认 | 五轴 + 分离事实 | 加历史同步横幅；两处旧口径加历史标签并说明已取代 |
| C-07 | `docs/v2/UI-REVIEW.md` 头部 | “等待用户设计评审（P7-00）”暗示旧 UI 仍是当前基线 | Phase 1 冻结新 Apple 基线 | 加历史评审记录横幅 |
| C-08 | `docs/v2/diagrams/README.md` 头部 | 旧图产物未标注历史 | 旧终态/门禁已被取代 | 加历史说明与重绘计划链接 |
| C-09 | `openspec/.../README.md` 任务账本 | 81 项 = 当前任务数 | 总计划 Phase 0–6 | 加同步说明；81 标历史；新增旧 Phase → 主计划映射与 C1–C7 → 五轴映射 |
| C-10 | `openspec/.../proposal.md` Why/What changes | Flask/Jinja/SSE/SQLite；11 需求映射到 81 项 | PostgreSQL；总计划 Phase 0–6 | 加同步说明；SQLite → PostgreSQL；81 项标历史并映射 |
| C-11 | `openspec/.../design.md` Context、D2、Data/completion、Model/toolchain、Migration | SQLite WAL；单一终态；WAL/busy_timeout | PostgreSQL；五轴；离线/STOP/释放/`cleanup_receipt` | 加同步说明；D2/数据层/工具链/迁移改写；新增五轴、C1–C7 映射、离线续跑与释放章节 |
| C-12 | `openspec/.../tasks.md` 头部与 Count | 81 项当前任务；Phase 0–8 当前阶段 | 总计划 Phase 0–6 | 加历史账本横幅；新增 Phase 映射表；Count 标历史 |
| C-13 | `openspec/.../specs/toolchain-compatibility/spec.md` | 锁含 SQLite | PostgreSQL 唯一正式库 | SQLite → PostgreSQL + 历史标注 |
| C-14 | `openspec/.../specs/completion-gate/spec.md` | 只有旧二值完成门禁；未表达五轴/离线/STOP/清理/释放 | 六项已批准规则 | 新增 3 个 Requirement：五轴与分离事实、离线续跑与占用保留、释放与证据/判定分离（含 `cleanup_receipt` 与 STOP-first 场景） |
| C-15 | `openspec/.../specs/ui-v2/spec.md` | UI 只显示 stage/gates/verdict；未表达离线占用与五轴 | UI 必须显示分离事实；离线不等于空闲 | 新增“五轴与分离事实”“离线运行且设备占用”两个场景 |
| C-16 | `openspec/.../specs/platform-events-push/spec.md` | 未说明通信丢失不得发 completed/failed/释放事件 | 心跳/租约过期不停止、不释放 | 新增“冻结运行中通信丢失”场景 |
| C-17 | `openspec/.../specs/task-playbook/spec.md` | “terminal task”未限定五轴/归档前置 | 终态须基于五轴与归档前置 | 补充“after the five-axis verdict and archive prerequisites” |
| C-18 | `.omo/drafts/01-design/...architecture-proposal.md` I-21 / §7 rule 4；`...module-design.md` §2.6 | “缺 `cleanup_receipt` = 证据不完整”；“心跳超时 → run=INFRA_ERROR” | 更晚批准记录明确取代 | **不修改草案正文**（超出 P0-03 同步对象）；在 §9 登记为源级遗留冲突，`docs/v2`/`openspec` 不采用旧表述 |
| C-19 | `docs/VERSIONING.md` 链接 `docs/delivery/source-reconciliation.md` | 初稿时目标文件不存在 | P0-02 产物未落盘 | 初稿不修改 VERSIONING（禁止编辑），在 §9 登记为既有问题；**2026-10-29 复核：`source-reconciliation.md` 已由 P0-02 于 2026-10-29 00:42–00:43 落盘（28582 字节），该链接已可解析**；返工按 F1 另在 `docs/VERSIONING.md` 补写 §2.4 |

---

## 5. 精确修改

### 5.1 `docs/v2`

| 路径 | 位置/章节 | 修改前 | 修改后 | 目的 |
|---|---|---|---|---|
| `docs/v2/SOLUTION.md` | 头部状态块（第 15 行附近） | “设计定稿候选，等待方案评审与 UI 设计评审”；旧工程基线 | 历史方案（2026-10-28）；总计划/契约候选链接；P0-03 同步说明 | 把整份文档降为历史参考并给出权威入口 |
| `docs/v2/SOLUTION.md` | §0.1 文档层级、§4.6、§4.8、§5.3、§5.4、§7.2、§7 页面表、附录 D2 | SQLite WAL；PostgreSQL 后续选项；单一终态；租约过期回收；缺清理回执等于证据不完整 | PostgreSQL 唯一正式库；五轴 + 分离事实；离线续跑/占用保留；STOP-first；释放/证据/判定分离；`cleanup_receipt` 边界；C1–C7 映射表 | 全面对齐 D-PG/D-5AXIS/D-OFFLINE/D-STOPFIRST/D-SEPARATE/D-CLEANUP |
| `docs/v2/SOLUTION.md` | §7.2 工具链锁、§7 页面表 | 含 Python、SQLite | Python、PostgreSQL；注明原 SQLite 已取代 | 消除工具链锁中的 SQLite 正式组件 |
| `docs/v2/SOLUTION.md` | §14 路线图/附录 | 81 项/Phase 0–8 被当作当前范围 | 标历史，链接总计划 Phase 0–6；Phase 3 产出新 WBS | 对齐 D-TASKSCOPE |
| `docs/v2/IMPLEMENTATION-PLAN.md` | 头部（第 9–11 行） | 旧目标路径/工作区；旧当前闸门 | 历史参考横幅；总计划/契约候选链接；P0-03 修改摘要 | 整份降为历史参考 |
| `docs/v2/IMPLEMENTATION-PLAN.md` | D2、§5.1、D5、§5.6、P0-03、P8-01、§15 | SQLite WAL；WAL/busy_timeout；单一终态；`sqlite temp DB` | PostgreSQL；五轴 + 分离事实；PostgreSQL 事务/约束/索引；PostgreSQL 测试库 | 消除旧技术口径 |
| `docs/v2/UI-DESIGN.md` | 头部（第 3–16 行） | 待评审；SQLite WAL 代码基线；未标注 C1–C7 历史 | 历史/已取代横幅；PostgreSQL；C1–C7 旧门禁映射与权威链接 | 防止旧 UI 规范被当当前基线 |
| `docs/v2/UI-DESIGN.md` | 工具链页（约 1883/1889 行）、系统存储区块（约 2297 行） | Python、SQLite；SQLite WAL/busy_timeout | PostgreSQL + 历史标签 | 消除 UI 文案中的正式 SQLite |
| `docs/v2/ACCEPTANCE-REPORT.md` | 头部、§1、§9 | 旧验收结论；81/81；C8 当前契约 | 历史/已取代横幅；81/C8 历史标签 | 防止旧验收报告被当当前验收 |
| `docs/v2/FLOWCHART-STYLE.md` | 头部、旧终态段 | 旧六终态集合未标历史 | 历史同步说明；两处旧口径标历史 | 防止旧图示范式约束当前图示 |
| `docs/v2/UI-REVIEW.md` | 头部 | 等待旧 UI 评审 | 历史评审记录横幅 | 与 Phase 1 新基线区分 |
| `docs/v2/diagrams/README.md` | 头部 | 旧图未标历史 | 历史说明 + 重绘计划链接 | 防止旧图被当当前流程 |
| `docs/v2/README.md`（上一轮已改，本次复核） | 头部、阅读顺序、目录状态、规则、缺口 | 旧目录状态；旧“实施计划/OpenSpec 为准” | 历史参考；总计划/契约候选优先；OpenSpec 活跃但已同步；新缺口描述 | 统一导航口径 |
| `docs/v2/wireframes/README.md` | 链接修复 | `../../design/...`（解析到不存在的 `docs/design`） | `../../../design/...` | P0-01 已有修复；本次复核确认保留，未改语义 |

### 5.2 `openspec`

| 路径 | 位置/章节 | 修改前 | 修改后 | 目的 |
|---|---|---|---|---|
| `openspec/changes/ai-test-platform-v2/README.md` | 新增“规范同步说明” | 无 | 7 条已批准规则；权威链接；P0-03 边界 | 给整个变更定同步基线 |
| `openspec/changes/ai-test-platform-v2/README.md` | Task accounting / 新增 Legacy mapping | 81 = 当前任务；无映射 | 81 标历史；旧 Phase 0–8 → 总计划 Phase 0–6 表；C1–C7 → 五轴说明 | D-TASKSCOPE |
| `openspec/changes/ai-test-platform-v2/proposal.md` | 新增同步说明；Why；What changes | SQLite；81 项当前映射 | PostgreSQL；81 项历史账本 + 总计划链接 | D-PG/D-TASKSCOPE |
| `openspec/changes/ai-test-platform-v2/design.md` | 新增同步说明；Context；D2；Data/completion；Model/toolchain；Migration | SQLite WAL；单一终态；WAL/busy_timeout | PostgreSQL；五轴 + 分离事实；C1–C7 映射表；离线续跑/STOP-first/释放/`cleanup_receipt` 新章节；PostgreSQL 迁移 | D-PG/D-5AXIS/D-OFFLINE/D-STOPFIRST/D-SEPARATE/D-CLEANUP |
| `openspec/changes/ai-test-platform-v2/tasks.md` | 头部、新增映射、Count | 81 项当前任务；Phase 0–8 当前阶段 | 历史账本横幅；Phase 映射表；Count 标历史 | D-TASKSCOPE |
| `openspec/.../specs/completion-gate/spec.md` | 新增 3 个 Requirement / 6 个 Scenario（`spec.md:17,21,28,32,39,43`；初稿误记 5 个） | 仅旧二值完成门禁 | 五轴与分离事实；离线续跑与占用保留；释放与证据/判定分离（含缺失清理回执、STOP-first） | 把六项规则变成可验证规格 |
| `openspec/.../specs/toolchain-compatibility/spec.md` | Requirement 文本 | 锁含 SQLite | PostgreSQL + 历史标注 | D-PG |
| `openspec/.../specs/ui-v2/spec.md` | 新增 2 个 Scenario | 仅 stage/gates/verdict | 五轴/分离事实展示；离线运行设备仍占用，不显示空闲/停止/完成 | D-5AXIS/D-OCCUPIED |
| `openspec/.../specs/platform-events-push/spec.md` | 新增 Scenario | 未防通信丢失误发终态 | 通信丢失不发 completed/failed/释放事件；通信 offline/stale，设备占用 | D-OFFLINE/D-SEPARATE |
| `openspec/.../specs/task-playbook/spec.md` | Requirement 限定 | “terminal task” 无前置 | “after the five-axis verdict and archive prerequisites” | D-5AXIS/D-SEPARATE |
| `openspec/config.yaml` | — | — | 未修改；仅校验 YAML | 避免无关变更 |

### 5.3 新增产物

| 路径 | 内容 |
|---|---|
| `docs/delivery/openspec-v2-sync.md` | 本报告：输入、冲突、精确修改、历史保留、映射、验证、遗留问题 |

---

## 6. 保留的历史内容（均带标签与链接）

| 文件 | 保留内容 | 标签 | 链接/说明 |
|---|---|---|---|
| `docs/v2/SOLUTION.md` | 旧 SQLite 原文引用、旧单一终态、旧 81 项路线图、旧 C1–C7 叙述 | `历史/已取代（2026-10-28）` | 文档头部同步说明 + 本报告 |
| `docs/v2/IMPLEMENTATION-PLAN.md` | 旧 D1–D13 正文、旧 81 项复选框、旧终态表 | 文件级“历史参考”横幅 + 逐处标签 | 总计划、本报告 |
| `docs/v2/UI-DESIGN.md` | 旧 v2「航次档案」15 页规格、C1–C7 门禁印列、旧 ASCII/原型说明 | 头部“历史参考（历史/已取代 2026-10-28）” | 总计划、`UI-DESIGN-APPLE.md`、本报告 |
| `docs/v2/ACCEPTANCE-REPORT.md` | 旧 81/81 校验、旧 C1–C7/C8 结论 | 头部“历史验收记录” + §9 标签 | 总计划、本报告 |
| `docs/v2/FLOWCHART-STYLE.md` | 旧终态集合、`BLOCKED_HUMAN` 张力段 | 头部“历史图示范式” + 段内标签 | 总计划、本报告 |
| `docs/v2/UI-REVIEW.md` | 旧 UI 评审记录 | 头部“历史评审记录” | 本报告 |
| `docs/v2/diagrams/README.md` | 旧两张流程图渲染产物 | 头部“历史说明” | 总计划、本报告；Phase 1/3 重绘 |
| `openspec/.../README.md` | 81 项任务账本、旧 Phase 0–8 | 同步说明 + Task accounting 历史标签 | 总计划、本报告；新增映射表 |
| `openspec/.../proposal.md` | 81 项历史账本 | `历史/已取代（2026-10-28）` | 总计划、本报告 |
| `openspec/.../tasks.md` | 全部 81 个复选框、Phase 0–8 | 文件级历史账本横幅 + Count 标签 | 总计划、本报告；新增映射表 |
| `openspec/.../design.md` | 旧终态名、C1–C7 | “legacy” + `历史/已取代（2026-10-28）` | 五轴映射表、本报告 |
| `openspec/.../specs/*` | 旧 completion 语义保留为兼容别名 | `历史/已取代（2026-10-28）` 或 legacy 说明 | completion-gate 新 Requirement、本报告 |

> 历史内容只用于追溯审批链和方案演进，不得据其恢复旧规则，也不得把旧任务数、旧状态机或旧技术选型当作现行依据（与 `docs/VERSIONING.md` §2 第 5 层一致）。

---

## 7. 旧 C1–C7 与 81 项任务 → 新主计划映射

### 7.1 C1–C7 → 五轴/分离事实

| 旧门禁 | 旧含义 | 当前映射 | 说明 |
|---|---|---|---|
| C1 方案 | 已批准不可变修订 | `validity_status` 的前置批准边界 | 不直接产生业务 PASS |
| C2 真实执行 | 真实节点签名回执 | `execution_status=COMPLETED`、`run_mode=real`、设备占用事实 | 仍需五轴与独立复核 |
| C3 产物清单 | 完整 manifest | `evidence_status` | 证据完整性独立 |
| C4 独立判定 | 独立 verdict | `verification_status` | Linux 独立复核 |
| C5 证据充分 | 必要证据 | `evidence_status` | 与 C3 共同约束 |
| C6 知识回写 | playbook/知识候选 | 归档前置，不改变五轴结论 | 不替代业务判定 |
| C7 可复现 | 工具链/环境事实 | 工具链与环境事实，不替代五轴 | 不替代五轴 |

### 7.2 旧 OpenSpec Phase 0–8 → 总计划 Phase 0–6

| 旧 Phase | 旧内容 | 当前主计划对应（覆盖关系，不是一一对应） |
|---|---|---|
| Phase 0 Foundation | 仓库骨架、迁移、契约、事件、CI、安全、ADR | 总计划 Phase 0（P0-04..P0-11）+ Phase 5 P5-01 |
| Phase 1 Model Registry | 模型目录、策略解析、热切换、降级 | Phase 2 P2-01/P2-09 + Phase 5 P5-02/P5-10 |
| Phase 2 Active Push | outbox、SSE、webhook、订阅、通知 | Phase 2 P2-08 + Phase 5 P5-08/P5-10 |
| Phase 3 Knowledge | KB schema、检索、playbook、失败挖掘 | Phase 2 P2-01 + Phase 5 P5-05/P5-08 |
| Phase 4 Planning/OpenSpec | 需求受理、方案/用例/oracle、审批、Agent 配置 | Phase 0 P0-04/P0-07 + Phase 2 P2-03 + Phase 5 P5-02 |
| Phase 5 Completion/Verdict | 完成报告、证据注册、真实回执、独立复核、归档 | Phase 0 P0-06 + Phase 4 P4-06 + Phase 5 P5-05 |
| Phase 6 Takeover | 会话注册、attach、租约、回放、输入 | Phase 2 P2-03/P2-04 + Phase 5 P5-08 |
| Phase 7 UI | 设计系统、页面、响应式、可访问性 | Phase 1 P1-01..P1-08 + Phase 5 P5-08 |
| Phase 8 Toolchain/E2E/Final | 工具链兼容、真机 E2E、升级演练、最终验证 | Phase 3 P3-03/P3-05 + Phase 5 P5-11 + Phase 6 P6-01..P6-08 |

> 81 项复选框保留在 `openspec/.../tasks.md` 仅作历史追溯；当前 WBS 由总计划 Phase 3（P3-01..P3-07）产出。P0-03 不发明新任务数。

---

## 8. 验证命令与结果

### 8.1 输入读取与修改范围

```bash
cd /home/bszheng/NoahsArk
wc -l .omo/plans/noahsark-platform-delivery.md \
  .omo/drafts/00-baseline/*.md \
  .omo/drafts/01-design/*.md \
  .omo/drafts/02-delivery/*.md \
  docs/delivery/workspace-triage.md plan.md
```

结果（节选）：主计划 109 行；基线 189 行；架构 377 行；模块 370 行；施工验收 177 行；测试策略 260 行；工作区分诊 260 行；`plan.md` 784 行。均已读取（全文或关键章节）。

```bash
git status --short
```

本轮 P0-03 触及的路径见 §10；未触及禁止路径（`.omo/plans`、`.omo/boulder.json`、`plan.md`、`docs/VERSIONING.md`、`README.md`、`docs/contracts`、`docs/ssh.txt`）。

### 8.2 SQLite 残留扫描

```bash
grep -rn "SQLite\|sqlite" docs/v2 openspec --include=*.md --include=*.yaml \
  | grep -vE "历史|已取代|原文|修正|取代|不再|legacy|historical|only as|not by itself"
```

结果：**无输出**（退出码 1）。所有 SQLite 提及均已带历史/取代标签，或仅作为“不得使用”的否定说明。

### 8.3 危险旧口径扫描

```bash
grep -rniE "lease (expiry|expiration) (reclaims|releases|stops)|heartbeat (loss|expiry) (stops|fails|releases)|心跳(过期|超时).*(停止|失败|回收|释放)|租约(过期|到期).*(回收|释放|停止|失败)|missing cleanup_receipt (means|makes).*(all )?evidence incomplete|缺.*cleanup_receipt.*(等同于|视为).*证据不完整" \
  docs/v2 openspec --include=*.md
```

结果：命中 **8 行**（初稿误记 3 条；按同一命令在最终文件状态重跑，`wc -l` = 8），全部为**否定/正确**表述，不是旧规则：

| 位置 | 性质 |
|---|---|
| `docs/v2/UI-DESIGN.md:16` | 历史头声明“断线/心跳过期继续执行”；否定旧规则 |
| `docs/v2/UI-DESIGN.md:17` | 历史头声明旧“心跳超时”文案为历史；否定旧规则 |
| `docs/v2/SOLUTION.md:251` | “通信离线不等于设备空闲/可回收”；否定旧规则 |
| `docs/v2/SOLUTION.md:498` | 正式执行行：“继续离线执行、保持占用、不重派”；否定旧规则 |
| `docs/v2/SOLUTION.md:517` | 离线续跑条：“不得停止、不得回收”；否定旧规则 |
| `docs/v2/README.md:17` | 已批准要点摘要；否定旧规则 |
| `docs/v2/IMPLEMENTATION-PLAN.md:11` | 历史头同步摘要；否定旧规则 |
| `openspec/.../proposal.md:9` | 同步说明；否定旧规则 |

无“租约到期回收设备”或“缺清理回执即证据不完整”的主动规范语句。

### 8.4 YAML / JSON / TOML

```bash
python3 - <<'PY'
import yaml, pathlib
p = pathlib.Path('openspec/config.yaml')
d = yaml.safe_load(p.read_text(encoding='utf-8'))
print('openspec/config.yaml: YAML OK, keys =', sorted(d.keys()))
PY
```

结果：`openspec/config.yaml: YAML OK, keys = ['schema']`。

- 本轮未修改任何 `.json` 或 `.toml` 文件（`git status --short` 过滤 `.json/.toml` 无输出）。
- 未修改 `docs/contracts/**` 的 schema；其 JSON 校验不在本轮范围。

### 8.5 OpenSpec 结构校验

```bash
openspec validate ai-test-platform-v2 --strict
```

结果：`Change 'ai-test-platform-v2' is valid`（退出码 0）。

### 8.6 空白/补丁检查

```bash
git diff --check
```

结果：无输出，退出码 0。

### 8.7 产物存在性

```bash
test -s docs/delivery/openspec-v2-sync.md && echo "report exists and non-empty"
wc -l docs/delivery/openspec-v2-sync.md
```

结果：`report exists and non-empty`；初稿 §8.7 记录 362 行，2026-10-29 返工后为 425 行，同日状态回填（§0.2）后为 **442 行**（以最终 `wc -l` 为准；行数变化来自 §0.1、F1/F2/F3 修订与 §0.2 状态回填，不改历史结论）。

### 8.8 新增链接目标检查

| 链接 | 目标 | 结果 |
|---|---|---|
| `docs/v2/SOLUTION.md` → `../delivery/openspec-v2-sync.md` | `docs/delivery/openspec-v2-sync.md` | 存在 |
| `docs/v2/IMPLEMENTATION-PLAN.md` → `../../.omo/plans/noahsark-platform-delivery.md` | `.omo/plans/noahsark-platform-delivery.md` | 存在 |
| `docs/v2/IMPLEMENTATION-PLAN.md` → `../delivery/openspec-v2-sync.md` | `docs/delivery/openspec-v2-sync.md` | 存在 |
| `docs/v2/UI-DESIGN.md` → `../../.omo/plans/noahsark-platform-delivery.md` | `.omo/plans/noahsark-platform-delivery.md` | 存在 |
| `docs/v2/UI-DESIGN.md` → `../delivery/openspec-v2-sync.md` | `docs/delivery/openspec-v2-sync.md` | 存在 |
| `openspec/.../README.md` → `../../../../docs/delivery/openspec-v2-sync.md` | `docs/delivery/openspec-v2-sync.md` | 存在 |
| `openspec/.../README.md` → `../../../../.omo/plans/noahsark-platform-delivery.md` | `.omo/plans/noahsark-platform-delivery.md` | 存在 |

### 8.9 F1/F2 返工复核命令

```bash
cd /home/bszheng/NoahsArk

# F1：VERSIONING §2.4 六项规则表（返回 6）
grep -c '^| [1-6] |' docs/VERSIONING.md
# 原验证关键词命令仍有 5 行命中（规则 2–6；规则 1 PostgreSQL 行不含这些中文关键词，属预期）
grep -nE "五轴|离线|STOP|cleanup_receipt|清理回执|设备释放" docs/VERSIONING.md | wc -l

# F2：三份文档的 formal PASS 谓词（返回 3，且都含 execution_status=COMPLETED）
grep -rn "Formal PASS requires\|正式 PASS 条件" docs/v2 openspec --include=*.md \
  | grep -c "execution_status=COMPLETED"

# F2：completion-gate Scenario 必须要求执行完成（返回 1）
grep -c "execution_status=COMPLETED" \
  openspec/changes/ai-test-platform-v2/specs/completion-gate/spec.md

# F2：新增 Scenario 计数（新增 6 个：17,21,28,32,39,43 行）
grep -n "#### Scenario" \
  openspec/changes/ai-test-platform-v2/specs/completion-gate/spec.md

# F3：危险旧口径实际 8 行（§8.3 已按此改正）
grep -rniE "lease (expiry|expiration) (reclaims|releases|stops)|heartbeat (loss|expiry) (stops|fails|releases)|心跳(过期|超时).*(停止|失败|回收|释放)|租约(过期|到期).*(回收|释放|停止|失败)|missing cleanup_receipt (means|makes).*(all )?evidence incomplete|缺.*cleanup_receipt.*(等同于|视为).*证据不完整" \
  docs/v2 openspec --include=*.md | wc -l
```

实测结果（2026-10-29）：F1 六项规则表 = 6（关键词命令 = 5，因 PostgreSQL 行不含关键词）；F2 formal PASS 文档谓词 = 3、completion-gate = 1（合计 4 处同步点）、新增 Scenario = 6；F3 = 8。命令与结果可用上述命令原样复算。

---

## 9. 未解决 / 需后续处理

1. **源级草案内部矛盾（不在 P0-03 同步对象）**（*2026-10-29 回填：已由 `approved-draft-reconciliation.md` 修正，本条仅存档原记录；见 §0.2*）：`.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` 的 I-21 仍写“缺 `cleanup_receipt` 视为证据不完整”，§7 租约规则仍写 `lease_expired → run=INFRA_ERROR`；`.omo/drafts/01-design/noahsark-v0.0.1-module-design.md` §2.6 仍写“心跳超时 → run=INFRA_ERROR”。更晚的 `plan.md` 批准记录（S5-3、M-04、A-3、A-5）明确要求修正这些旧表述。本次按任务边界未改 `.omo/drafts`；`docs/v2` 与 `openspec` 已不采用旧表述。建议后续单独任务修订草案正文，避免读者绕过同步记录直接引用旧条。
2. **`docs/contracts` 未对齐项（禁止编辑）**（*2026-10-29 回填：`lease_expired` 措辞已由 P0-05 修正，本条仅存档原记录；见 §0.2*）：`docs/contracts/README.md` §2.3 已登记 `security-node.md` 仍有 `lease_expired` 旧措辞、`schemas/security/lease.schema.json` 的 `state` 含 `expired`；该契约包的权威语义是 `expires_at` 只是续约截止，不是所有权到期。`docs/v2`/`openspec` 未复制该旧语义；P0-05 需修正契约包措辞。
3. **占用枚举命名差异**：`docs/contracts/domain.md` 使用 `occupancy_state = IDLE/OCCUPIED/RELEASING`，`docs/v2`/`openspec` 使用 `OCCUPIED/RELEASING/RELEASED/QUARANTINED`。语义一致（释放/隔离分开），但名称未统一；建议在 P0-06/P0-04 契约冻结时统一，P0-03 不擅自改契约。
4. **旧 PDF/位图/图源未重绘**：`docs/v2/SOLUTION.pdf`、`docs/v2/diagrams/*.svg|*.png`、`docs/v2/diagrams/FLOWCHARTS.pdf` 仍反映旧终态/旧门禁。Markdown 源已加历史标签；Phase 1/3 重绘前不得作为当前图示依据。
5. **旧 UI 规格仍保留大量 C1–C7 文案**：`docs/v2/UI-DESIGN.md` 已整份标历史并给映射，但未逐页重写；Phase 1 将以 `UI-DESIGN-APPLE.md` 为候选冻结新基线。
6. **81 项复选框仍保留**：`openspec/.../tasks.md` 作为历史账本保留；当前 WBS 由总计划 Phase 3 产出。若后续要删除旧账本，应另开归档任务，不在 P0-03 静默删除。
7. **P0-02 遗留链接（已关闭）**：初稿时 `docs/VERSIONING.md` 多处链接的 `docs/delivery/source-reconciliation.md` 不存在；**2026-10-29 复核确认该文件已由 P0-02 落盘**（28582 字节，`ls -la` 可见），链接现已可解析，不再构成遗留项。初稿只登记未修的原因保留如下：当时禁止编辑 `docs/VERSIONING.md`。
8. **C8 占位**：旧 C8“测试之测试”仍无验收标准；已在旧验收报告中标历史，当前五轴判定不以 C8 占位为依据。
9. **未运行产品/测试**：P0-03 只做文档同步；未执行任何产品实现、单元/集成测试、真机烟测、部署或发布。`docs/v2`/`openspec` 的通过只表示文档结构/一致性检查通过。

---

## 10. 变更路径清单

### 10.1 本轮 P0-03 修改/新增

| 路径 | 类型 | 说明 |
|---|---|---|
| `docs/v2/SOLUTION.md` | 修改 | PostgreSQL、五轴、离线/STOP-first/释放/清理回执、81 历史 |
| `docs/v2/IMPLEMENTATION-PLAN.md` | 修改 | 历史头、D2/5.1/5.6/P0-03/P8-01/测试策略、81 历史 |
| `docs/v2/UI-DESIGN.md` | 修改 | 历史头、SQLite → PostgreSQL、C1–C7 历史映射 |
| `docs/v2/ACCEPTANCE-REPORT.md` | 修改 | 历史验收横幅、81/C8 标签 |
| `docs/v2/FLOWCHART-STYLE.md` | 修改 | 历史图示范式、旧终态标签 |
| `docs/v2/UI-REVIEW.md` | 修改 | 历史评审横幅 |
| `docs/v2/diagrams/README.md` | 修改 | 历史产物说明 |
| `docs/v2/README.md` | 上一轮修改，本次复核 | 目录状态/阅读顺序/规则/缺口 |
| `openspec/changes/ai-test-platform-v2/README.md` | 修改 | 同步说明、81 历史、Phase/C1–C7 映射 |
| `openspec/changes/ai-test-platform-v2/proposal.md` | 修改 | 同步说明、PostgreSQL、81 历史 |
| `openspec/changes/ai-test-platform-v2/design.md` | 修改 | 同步说明、PostgreSQL、五轴、离线/STOP/释放/清理、迁移 |
| `openspec/changes/ai-test-platform-v2/tasks.md` | 修改 | 历史账本横幅、Phase 映射、Count 标签 |
| `openspec/changes/ai-test-platform-v2/specs/completion-gate/spec.md` | 修改 | 五轴、离线占用、释放/证据/判定、清理回执、STOP-first |
| `openspec/changes/ai-test-platform-v2/specs/toolchain-compatibility/spec.md` | 修改 | SQLite → PostgreSQL |
| `openspec/changes/ai-test-platform-v2/specs/ui-v2/spec.md` | 修改 | 五轴/分离事实、离线占用 UI |
| `openspec/changes/ai-test-platform-v2/specs/platform-events-push/spec.md` | 修改 | 通信丢失不误发终态/释放 |
| `openspec/changes/ai-test-platform-v2/specs/task-playbook/spec.md` | 修改 | terminal task 限定五轴/归档前置 |
| `docs/delivery/openspec-v2-sync.md` | **新增** | 本证据报告 |
| `docs/VERSIONING.md` | 返工新增修改 | 2026-10-29 按 F1 补写 §2.4 六项规则导航摘要（初稿未改；见 §0.1） |

### 10.2 工作区中非本轮 P0-03 的既有改动（未认领、未修改）

| 路径 | 状态 | 归属/说明 |
|---|---|---|
| `.gitignore` | 修改 | P0-01 隔离 `docs/ssh.txt` |
| `README.md` | 修改 | P0-01/P0-02 入口整理（禁止编辑，未改） |
| `docs/v2/wireframes/README.md` | 修改 | P0-01 链接深度修复（仅复核） |
| `自动化生成测试用例流程图.svg`（根目录） | 删除 | P0-01 已确认的字节一致移动 |
| `docs/VERSIONING.md` | 未跟踪 | P0-02 产物；2026-10-29 返工按 F1 修改 §2.4（初稿未认领，此处保留历史状态） |
| `docs/contracts/` | 未跟踪 | P0-04..P0-08 契约候选（禁止编辑） |
| `docs/references/` | 未跟踪 | P0-01 参考资料 |
| `docs/delivery/construction-progress.md` | 未跟踪（既有） | 施工进度表，不在本轮修改 |
| `docs/delivery/workspace-triage.md` | 未跟踪（既有） | P0-01 报告，只读 |

### 10.3 删除/新增统计

```text
初稿 P0-03：18 个路径（17 个修改 + 1 个新增报告）
其中 docs/v2：8 个（含上一轮已改的 README.md）
其中 openspec：9 个

2026-10-29 返工：19 个路径（18 个修改 + 1 个新增报告）
新增修改：docs/VERSIONING.md（§2.4）
另改：docs/v2/SOLUTION.md、docs/v2/IMPLEMENTATION-PLAN.md、
      openspec/.../design.md、openspec/.../specs/completion-gate/spec.md（formal PASS 谓词）
      docs/delivery/openspec-v2-sync.md（F3 数字与状态）
产品代码：0
禁止路径：0（VERSIONING 是 P0-03 计划指定同步目标，不算禁止路径）
```

> 最终以 `git status --short` 为准；本报告不改变任何暂存区状态，未提交、未推送。
