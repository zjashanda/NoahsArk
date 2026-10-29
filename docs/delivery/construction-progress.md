# NoahsArk 施工进度表

> 版本：v0.1（2026-10-28）
> 规则：每个工作单元完成后立即更新；不得批量补记。返回的代理数据必须登记到对应行。
> 状态：`待分配`、`已派发`、`进行中`、`待验证`、`已完成`、`阻塞`、`返工`、`取消`。

## Phase 0：安全分诊、事实源统一与最小契约冻结

| 编号 | 任务 | 负责人代理 | 状态 | 依赖 | 开始 | 结束 | 证据 | 阻塞/返工 |
|---|---|---|---|---|---|---|---|---|
| P0-01 | 工作区安全分诊 | `bg_8991379d` / `ses_e7ce008b6ffeYyZLBwNLGDds5Y` | 已完成 | 无 | 2026-10-28T15:35Z | 2026-10-28T15:41Z | `docs/delivery/workspace-triage.md`；敏感文件隔离至 `/tmp/opencode/quarantine/noahsark-ssh-48308fa0.txt`；哈希一致 | 无 |
| P0-02 | 建立事实源优先级 | `bg_46181799` / `ses_e7c9b6cb5ffeUiT2XGYh0ct1cY` | 已完成 | P0-01 | 2026-10-28T23:38Z | 2026-10-29T00:02Z | `docs/VERSIONING.md`、`docs/delivery/source-reconciliation.md`；`git diff --check` 通过；42 条 SR 索引 | 前两次代理超时；本次小范围重派后已独立复核 |
| P0-03 | 同步规范文档冲突 | `bg_43400b99`；核验 `bg_63d6a1f7`；复验 `bg_98221b35` | 已完成（限定范围） | P0-01 | 2026-10-28T23:38Z | 2026-10-29T08:20Z | `docs/delivery/p0-03-postfix-verification.md`；5/5 检查 PASS | 源草案旧条文由 `approved-draft-reconciliation.md` 对账；历史 NEEDS-FIX 报告保留 |
| P0-04 | 冻结核心领域契约 | `bg_9d814571`；修复 `bg_75aae191`；核验 `bg_43d57ac1` | 已完成（候选） | P0-02 | 2026-10-28T15:35Z | 2026-10-29T07:20Z | `docs/contracts/`、`docs/delivery/phase0-contract-remediation-verification.md`；35/35 JSON Schema 通过 | F-01..F-11 已闭环；R-01..R-03 非阻塞；契约仍标 `frozen-candidate`，不是用户批准/生产冻结 |
| P0-05 | 冻结节点身份与消息安全契约 | `bg_22a5403d`；复验 `bg_43d57ac1` | 已完成（候选） | P0-02 | 2026-10-28T15:35Z | 2026-10-29T07:20Z | `docs/contracts/security-node.md`、`docs/contracts/schemas/security/`、`phase0-contract-remediation-verification.md` | 35/35 schema 通过；仍需 P0-09 记录外部未决项，未称生产冻结 |
| P0-06 | 冻结证据与判定契约 | `bg_323b8524`；复验 `bg_43d57ac1` | 已完成（候选） | P0-02 | 2026-10-28T15:35Z | 2026-10-29T07:20Z | `docs/contracts/evidence-verdict.md`、`docs/contracts/schemas/evidence/`、`phase0-contract-remediation-verification.md` | F-01..F-08 复验通过；仍需 P0-09 记录证据切片/签名未决项 |
| P0-07 | 冻结任务卡、报告、知识与审计契约 | `bg_e8fcb681`；复验 `bg_43d57ac1` | 已完成（候选） | P0-02 | 2026-10-28T15:35Z | 2026-10-29T07:20Z | `docs/contracts/ui-report-knowledge-audit.md`、`docs/contracts/schemas/experience/`、`phase0-contract-remediation-verification.md` | UI 投影映射已登记；仍需 P0-09 记录分母/刷新等未决项 |
| P0-08 | 冻结运行阈值 | `bg_ccc9969c`；复验 `bg_43d57ac1` | 已完成（候选） | P0-02 | 2026-10-28T15:35Z | 2026-10-29T08:12Z | `docs/contracts/thresholds.md`、`docs/contracts/schemas/config/`、`phase0-contract-remediation-verification.md` | 六层优先级和 256 KiB 已对齐；仍需 P0-09 记录任务级参数未决项 |
| P0-09 | 对账决策登记册 P0/P1 | `bg_62003bb5` | 已完成 | P0-04..P0-08 | 2026-10-29T08:30Z | 2026-10-29T08:45Z | `docs/delivery/p0-09-decision-reconciliation.md`；登记册追加对账注记；64 项分类 | 保留旧登记历史；5 个 open-blocker 进入 P0-11/后续门禁 |
| P0-10 | 建立环境/设备/lstest 输入清单 | `bg_cb9ec25e`；核验 `bg_ce0737d6`；复验 `bg_67235899` | 已完成（限定范围） | P0-01 | 2026-10-28T15:35Z | 2026-10-29T08:20Z | `docs/delivery/p0-10-postfix-verification.md`；F1-F4 PASS | A-0/环境就绪仍未通过，未知项仍需外部输入 |
| P0-11 | Phase 0 验证与归档 | `bg_8ab39fd7` | 已完成（候选归档） | P0-03..P0-10 | 2026-10-29T08:50Z | 2026-10-29T09:05Z | `.omo/drafts/99-history/20261029-phase0-candidate/`；56 个文件 hash 校验通过 | 保留 5 个 open-blocker；归档完成不等于 Phase 0/实施冻结 |

P0-01 证据：分诊报告见 [`workspace-triage.md`](./workspace-triage.md)；`docs/ssh.txt` 已隔离至仓库外受限路径，`.gitignore` 已追加 `docs/ssh.txt`。主控已独立核对隔离和忽略状态；未提交、未推送。敏感文件内容及凭据不得进入本进度表或 Git。

P0-10 证据：输入清单见 [`environment-inputs.md`](./environment-inputs.md)；当前共 85 条登记（38 known / 12 placeholder / 35 unknown）。早期 `20/14/51` 为代表节点事实录入前的历史快照；A-0 与 L3/L4/L5 两套清单已建，仍未宣称 A-0 通过。

P0-03 源级遗留冲突：已对齐评审架构、模块、方案 B 与优化路线中的旧租约/清理表述；核验见 `approved-draft-reconciliation.md` 和 `p0-03-postfix-verification.md`。该限定范围已完成，历史 NEEDS-FIX 记录保留。

## Phase 1 至 Phase 6 与最终验证

| 阶段 | 任务范围 | 负责人代理 | 状态 | 依赖 | 证据 | 结论/阻塞 |
|---|---|---|---|---|---|---|
| Phase 1 | 真实 UI 设计、原型、视觉 QA、冻结 | 核验 `bg_7b7d5bde`；修复 `bg_baa16193`；复核产物已落盘 | 候选原型已实现；本地 Chromium QA 通过；独立视觉评审/所有者冻结未完成 | Phase 0 候选归档 | [`ui-candidate-verification.md`](./ui-candidate-verification.md) 记录四份候选文档 4/4 PASS；[`design/ui-app/README.md`](../../design/ui-app/README.md) 与 `design/ui-app/evidence/` 记录 39 路由、响应式检查与截图；contract 100/100、smoke 248/248 | 候选 UI 可评审但未冻结；仍无独立视觉签核、所有者批准或 P1-08 冻结 |
| Phase 1 历史记录 | Apple 风格 UI 设计候选稿早期失败批次 | `bg_d5182a04`、`bg_b6a8c41c`、`bg_bf248ec1`、`bg_f78b01ff`、`bg_15f93d42`、`bg_ae2c0acd` | 历史失败/不计当前执行 | Phase 0 候选归档 | 早期超时与失效句柄保留在 `restart-handoff-20261029.md`；`bg_ae2c0acd` 无验证产物 | 当前由已落盘候选及复核报告取代，不重复派发 |
| Phase 2 | 服务端 + UI 技术落地方案 | `bg_bd795be6` 草稿 | 草稿完成、未冻结 | Phase 1 | [`phase2-landing-plan-draft.md`](./phase2-landing-plan-draft.md)，255 行 | P2-01..P2-09 未勾选；等待真实 UI 冻结和契约复核 |
| Phase 3 | 施工方案与进度表 | 主控 + 写作代理 | 草稿可评审、未冻结 | Phase 2 | [`phase3-construction-plan-draft.md`](./phase3-construction-plan-draft.md)；[`phase3-construction-plan-verification.md`](./phase3-construction-plan-verification.md) | PASS AS REVIEW DRAFT；P3-07 NOT DONE，不授权实施 |
| Phase 4 | 验收方案 | 待分配 | 待分配 | Phase 3 | 无 | 尚未编写和冻结 |
| Phase 5 | 实施 | 待分配 | 待分配 | Phase 4 冻结 | 无 | 未授权开始 |
| Phase 6 | 验收执行 | 待分配 | 待分配 | Phase 5 | 无 | 未开始 |
| Final Wave | F1-F4 | 待分配 | 待分配 | Phase 6 | 无 | 未开始 |

## 2026-10-29 非 UI 准备并行批次

| 工作单元 | Agent / Category | 状态 | 产物 | 结论/阻塞 |
|---|---|---|---|---|
| A-0 环境与设备就绪度审计 | `bg_6cd6d26b` / `Sisyphus-Junior` / `deep-low` | 已完成（历史 advisory） | [`a0-readiness-followup.md`](./a0-readiness-followup.md)，426 行 | 原审计时 A-0 未通过且未连接 SSH；后续代表节点验证见下一行，历史结论不覆盖 |
| A-0 代表节点/DUT 只读验证 | 主控 / 受限 SSH | 已完成（限定范围） | [`a0-representative-node-verification.md`](./a0-representative-node-verification.md)；`environment-inputs.md` | 一台 Windows 11/QEMU 节点、活动桌面、D:、5 个 COM、ListenAI 音频与 TCL001/V038 已确认；Python 3.10.11 不符合目标；A-0 仍受 Node Agent/profile/证书/存储/窗口/恢复演练阻塞；敏感值未落仓库 |
| 契约残余与事实源冲突审计 | `bg_a8fc184c` / `Sisyphus-Junior` / `deep-low` | 已完成（只读审计） | [`contract-residual-followup.md`](./contract-residual-followup.md)，241 行 | 9 项残余/冲突待契约所有者收口；契约仍为 `frozen-candidate v1` |
| Phase 2 输入地图 | `bg_57d30edb` / `Sisyphus-Junior` / `deep-low` | 已完成（准备稿） | [`phase2-input-map.md`](./phase2-input-map.md)，644 行 | P2-01..P2-09 仍未勾选；等待 UI 冻结、A-0 事实和契约冻结 |
| Phase 0 源同步复核 | `bg_3d9adaea` / `Sisyphus-Junior` / `deep-low` | 已完成（NEEDS-FIX） | [`source-sync-followup-verification.md`](./source-sync-followup-verification.md)，242 行 | 7/7 核心语义通过；`openspec-v2-sync.md` 与 `source-reconciliation.md` 状态登记陈旧，待非 UI 修复；Phase 0 仍未关闭 |
| Phase 0 陈旧状态修复 | `bg_8866a4f0` / `Sisyphus-Junior` / `writing` | 已完成 | [`source-sync-status-repair.md`](./source-sync-status-repair.md)，135 行；`openspec-v2-sync.md` 425→442；`source-reconciliation.md` 184→207 | 仅回填 SR-10/11/12 与 §9.1/§9.2 状态，历史原文保留；5 个 open-blocker、A-0、候选契约仍未关闭 |
| Phase 0 候选归档复核 | `bg_d6914dc2` / `Sisyphus-Junior` / `quick` | 已完成（通过，快照漂移非阻断） | [`candidate-archive-followup-verification.md`](./candidate-archive-followup-verification.md)，153 行 | 58 文件、56/56 哈希通过、55/56 当前源逐字节一致；进度快照为归档时点，未发现敏感或实现冻结暗示 |
| Phase 0 契约残余裁决提案 | `bg_e19f9220` / `Sisyphus-Junior` / `deep-high` | 已完成（非权威提案） | [`contract-resolution-proposal.md`](./contract-resolution-proposal.md)，722 行 | 9 项提案 + 5 项补充观察；21 处 PROPOSED、19 处 BLOCKED、13 处 EVIDENCED；14 项未决（U-01..U-14）；未修改契约/schema，不冻结、不关闭 Phase 0 |
| Phase 0 契约裁决落地 | `bg_32add555` / `Sisyphus-Junior` / `deep-high` | 已完成（候选 v1.1，待复核） | [`contract-adjudication-record.md`](./contract-adjudication-record.md)，459 行；`docs/contracts/**` 更新 | 9 项裁决已写入；契约 README 标 `frozen-candidate v1.1`、35 schema 全部通过；仍未生产冻结、Phase 0 未关闭 |
| Phase 0 契约 v1.1 复核 | `bg_ef833f47` / `Sisyphus-Junior` / `deep-low` | 超时/待小范围重派 | 未生成 `contract-v1.1-verification.md` | 33 分钟无活动超时；不影响已落地候选，但候选仍不得冻结；后续按 9 项拆分验证 |
| Phase 2 落地方案草稿 | `bg_bd795be6` / `Sisyphus-Junior` / `deep-low`（首试 `bg_6293d39d` 中止，重试完成） | 已完成（仅草稿） | [`phase2-landing-plan-draft.md`](./phase2-landing-plan-draft.md)，255 行 | 标注 DRAFT/PENDING UI FREEZE/A-0/CONTRACT；P2-01..P2-09 全部未勾选、未冻结 |
| 产品目标与实施总纲 | 主控 | 已完成 | [`../../1.md`](../../1.md)，333 行 | 明确最终产品、完整闭环、组件边界、TCL 后置、阶段顺序和下一步；不是冻结件或实施授权 |
| Phase 3 施工方案草稿 | 主控 + 写作代理 | 已完成（可评审草稿） | [`phase3-construction-plan-draft.md`](./phase3-construction-plan-draft.md)，556 行；[`phase3-construction-plan-verification.md`](./phase3-construction-plan-verification.md) | 66 项、W0..W9、门禁、Python 路线、TCL 后置和敏感扫描通过；P3-07 未完成，不授权 Phase 5/6 |

> 受限 SSH 凭据政策（强制）：未来冻结的施工方案（Phase 3 P3-07）和验收方案（Phase 4 P4-08）必须包含总计划第 0.1 节《受限 SSH 凭据使用政策》，以路径引用方式指向操作方提供的受限凭据文件（当前受限源位于仓库外 `/tmp/opencode/quarantine/noahsark-ssh-48308fa0.txt`），不得复制其内容。两份方案及相应证据均不得出现口令、私钥、令牌、IP、用户名，也不得打印或计算凭据文件哈希。缺此条款的方案不得冻结。

## Phase 1 代理超时复盘与防复发规则

### 事件记录

- 失败批次：`bg_d5182a04`（信息架构）、`bg_b6a8c41c`（视觉系统）、`bg_bf248ec1`（屏幕规格）。
- 共同表现：运行约 33 分钟，最后工具为 `write`，随后因 30 分钟无活动超时；三个目标文件均未落盘，不能按代理完成声明计数。
- 结论：这是**任务粒度、交付时机和可观测性设计失败**，不是 UI 需求本身被判定不可行。原任务要求代理一次完成大范围阅读、综合决策和长文写作，且没有中间交付点；代理在写入前长时间无可观察进展，触发平台超时。

### 已采取的纠正

1. 不再重派原始大任务；每个重派单元只负责一个文件，目标约 100–300 行。
2. Prompt 明确“先写入目标文件，再做有限补充”，避免把全部工作压到最后一次写入。
3. 限定阅读范围，不再要求代理扫描整个仓库。
4. 每个代理必须返回精确路径、行数和 `git diff --check` 结果；没有文件就算失败。
5. 将 IA、视觉系统、屏幕规格和研究拆成独立并行任务；一个失败只影响一个文件，不拖垮整批 Phase 1。
6. 失败任务标记为返工，不覆盖原失败证据；新代理必须使用新 ID，便于区分尝试次数和验证结果。

### 后续准入门

- 只有四个 UI 基础文档全部落盘并通过独立内容检查，才能进入 UI 原型/视觉 QA。
- 只有 UI 设计冻结归档后，才能开始 Phase 2 落地方案。
- 任何代理再次出现“最后工具为 write、无文件、超时”时，不重复派发同样范围；立即拆成更小的单文件或单章节任务，并在本表登记失败原因。

## Phase 1 四会话主动监控记录

- 2026-10-29 09:52：主动读取 `ui-research.progress.md`、`ui-ia.progress.md`、`ui-system.progress.md`；三个会话均有阶段心跳，研究会话已完成 10 个外部来源核验，IA 会话发现 7 项候选修正，视觉系统会话发现 9 项枚举/语义修正。
- 2026-10-29 09:52：屏幕规格会话未生成 `ui-screens.progress.md`，且无同批次新活动；判定为监控异常，不等待 30 分钟超时。旧任务 `bg_9a9ef8b9` 已取消并重新派发为 `bg_d5c9b591`，新会话必须先写心跳文件。
- 监控规则：每次主动检查同时核对 session transcript、独立 progress 文件、目标文档 mtime 和内容；仅有会话存活不算进展，只有心跳或产物变化才算有效进展。

## 2026-10-29 重启前检查点

- 用户将重启 OpenCode，以加载新的 Sisyphus-Junior 模型配置；暂停新派发。会话与代理状态、未完成范围、受限材料边界及恢复顺序详见 [`restart-handoff-20261029.md`](./restart-handoff-20261029.md)。
- P1-01..P1-04 保持未勾选：候选文档存在，但独立核验报告缺失；旧核验任务句柄已失效，不得记为 PASS。Phase 1 原型与视觉 QA 未开始，Phase 2 及后续未开始。

## 2026-10-29 Phase 3 至 5 执行文档批次

- 已形成三份评审稿：[`phase3-construction-plan.md`](./phase3-construction-plan.md)、[`phase4-acceptance-plan.md`](./phase4-acceptance-plan.md)、[`phase5-implementation-plan.md`](./phase5-implementation-plan.md)。
- 三份均为 `DRAFT · NOT FROZEN`：P3-07、P4-08 未完成，不授权 Phase 5/6，不声称 UI、架构、契约、A-0 或验收已通过。
- 阶段状态不变：Phase 1 候选未冻结；Phase 2 草稿未冻结；Phase 3 评审稿；Phase 4 评审稿；Phase 5 仅为计划。
- 待决事项：契约 v1.1 独立验证、工具链 ADR-001 至 ADR-010、真实认证、证据存储后端、部署拓扑、Node Agent 打包、P2-05 前端架构、样本/阈值任务级批准、RPO/RTO 演练。
- 事实冲突待主控裁定：纵切批次 2 的“进行中”口径与 `backend-integration-progress.md` 的“DONE 37 passed”不一致；UI smoke 的 249/249 与本文档早期 248/248 记录不一致。
