# Phase 0 源同步产物独立复核（Source Sync Follow-up Verification）

> 复核日期：2026-10-29（Asia/Shanghai）
> 复核性质：**只读独立复核**。不修改任何被复核源文档、契约、产品或配置；只新增本报告。
> 复核对象：P0-03 源同步证据链（`openspec-v2-sync.md`、`p0-03-postfix-verification.md`）、P0-02 冲突登记（`source-reconciliation.md`）、源草案对账（`approved-draft-reconciliation.md`）、`docs/VERSIONING.md`、`docs/v2/**`、`openspec/**`、总计划与根 `plan.md`。
> 边界：未执行提交、推送、部署、产品代码、真机、SSH 或凭据操作；未宣称 Phase 0 关闭。
> **总体结论：NEEDS-FIX（仅文档记录陈旧，非语义冲突）**。七项语义检查全部 PASS；两个证据/登记类产物的“未解决/状态”条目落后于后续已完成的修复，需由后续任务更新状态，不得在本报告外静默改写。

---

## 1. 结论摘要

| 项目 | 结果 |
|---|---|
| 七项语义检查（PostgreSQL-only、Linux 权威、Windows 仅事实、离线续跑、STOP-first、释放/证据/判定分离、旧口径残留） | **7/7 PASS** |
| 活动规范层（`docs/v2` + `openspec`）未标注的 SQLite 正式库口径 | **0 处**（29 处 SQLite 提及全部带历史/取代标签或否定说明） |
| 危险旧口径（租约/心跳到期即停止/回收、缺回执即证据不完整） | 命中 **8 行，全部为否定/正确表述**（与 `openspec-v2-sync.md` §8.3 一致） |
| 产物 PASS / NEEDS-FIX | **6 PASS / 2 NEEDS-FIX**（按 8 个复核单元计，见 §4） |
| Phase 0 是否可关闭 | **否**。5 个 `open-blocker` 仍在，A-0 未通过，契约仍为 `frozen-candidate` |
| 本报告自身检查 | 已复读；`git diff --check` 通过；行尾空白 0 |

一句话：**已批准的六项同步语义在活动规范中成立，没有发现需要回退的语义错误；需要修的是两份报告的“未解决项/状态栏”未回填后续修复结果，以及 3 份历史文档中若干未逐处标注的旧终态语句。**

---

## 2. 复核方法与可复算证据

所有命令均在 `/home/bszheng/NoahsArk` 执行，只读。

### 2.1 读取范围

| 类别 | 文件 |
|---|---|
| P0-03 证据链 | `docs/delivery/openspec-v2-sync.md`（425 行）、`docs/delivery/p0-03-verification.md`（历史 NEEDS-FIX）、`docs/delivery/p0-03-postfix-verification.md`（144 行） |
| 冲突与对账 | `docs/delivery/source-reconciliation.md`（184 行）、`docs/delivery/approved-draft-reconciliation.md`（193 行） |
| 规范优先级 | `docs/VERSIONING.md`（237 行，§2、§2.2、§2.3、§2.4） |
| 同步对象 | `docs/v2/SOLUTION.md`、`IMPLEMENTATION-PLAN.md`、`UI-DESIGN.md`、`README.md`、`ACCEPTANCE-REPORT.md`、`FLOWCHART-STYLE.md`、`UI-REVIEW.md`、`diagrams/README.md`、`wireframes/README.md`；`openspec/changes/ai-test-platform-v2/` 全部 13 个 Markdown + `openspec/config.yaml` |
| 主计划与批准记录 | `.omo/plans/noahsark-platform-delivery.md`（124 行，Phase 0 第 34–46 行）、根 `plan.md`（798 行） |
| 旁证（只读） | `docs/contracts/README.md`、`security-node.md`、`evidence-verdict.md`、`domain.md`、`ui-report-knowledge-audit.md`、`schemas/security/lease.schema.json`；`docs/delivery/p0-09-decision-reconciliation.md`、`a0-readiness-followup.md`、`contract-residual-followup.md`、`construction-progress.md` |

### 2.2 关键命令与结果

```bash
# 1) SQLite 提及总量与未标注残留
grep -rn "SQLite\|sqlite" docs/v2 openspec --include=*.md | wc -l          # 29
grep -rn "SQLite\|sqlite" docs/v2 openspec --include=*.md --include=*.yaml \
  | grep -vE "历史|已取代|原文|修正|取代|不再|legacy|historical|only as|not by itself|不得|禁止|仅作"
# 无输出，EXIT=1

# 2) 危险旧口径（租约/心跳到期即停/回收、缺回执即证据不完整）
grep -rniE "lease (expiry|expiration) (reclaims|releases|stops)|heartbeat (loss|expiry) (stops|fails|releases)|心跳(过期|超时).*(停止|失败|回收|释放)|租约(过期|到期).*(回收|释放|停止|失败)|missing cleanup_receipt (means|makes).*(all )?evidence incomplete|缺.*cleanup_receipt.*(等同于|视为).*证据不完整" \
  docs/v2 openspec --include=*.md | wc -l                                  # 8，逐行人工确认为否定/正确表述

# 3) 五轴正式 PASS 谓词（4 处同步点）
grep -rn "execution_status=COMPLETED" docs/v2/SOLUTION.md docs/v2/IMPLEMENTATION-PLAN.md \
  openspec/changes/ai-test-platform-v2/design.md \
  openspec/changes/ai-test-platform-v2/specs/completion-gate/spec.md        # 4 文件均命中

# 4) OpenSpec 结构校验
export PATH="/home/bszheng/.nvm/versions/node/v24.14.1/bin:$PATH"
openspec validate ai-test-platform-v2 --strict                              # valid，EXIT=0（openspec 1.7.0）

# 5) 报告自述数字复算
wc -l docs/delivery/openspec-v2-sync.md                                     # 425，与 §8.7 一致
grep -c "^| [1-6] |" docs/VERSIONING.md                                     # 6，与 §2.4 行 86–91 一致
grep -c "### Requirement" openspec/.../specs/completion-gate/spec.md        # 4（新增 3）
grep -c "#### Scenario"  openspec/.../specs/completion-gate/spec.md        # 8（新增 6）
```

---

## 3. 七项语义检查（逐项判定）

| # | 检查项 | 权威落点（证据） | 判定 |
|---|---|---|---|
| S1 | **PostgreSQL 唯一正式库** | `docs/v2/SOLUTION.md:266,293,617,679,972`；`docs/v2/IMPLEMENTATION-PLAN.md:11,78,261,310,905`；`docs/v2/UI-DESIGN.md:5,14,1884,1890,2298`；`docs/v2/ACCEPTANCE-REPORT.md:7`；`docs/v2/README.md:17,32,46,92`；`openspec/.../design.md:14,21,60`；`openspec/.../specs/toolchain-compatibility/spec.md:4`；`openspec/.../README.md:9`；`openspec/.../proposal.md:7,16`。29 处提及 0 处未标注。 | **PASS** |
| S2 | **Linux 权威判定** | `docs/contracts/README.md:87`（五轴最终判定 Linux 独占）；`docs/contracts/evidence-verdict.md:16,18,40,1071,1075`（Linux 独立复核是正式 PASS 必要条件）；`docs/contracts/domain.md:313`；`docs/contracts/security-node.md:517`；`docs/contracts/ui-report-knowledge-audit.md:25-30`。同步层以 `verification_status`（`docs/v2/SOLUTION.md:532`）+ 正式 PASS 五条件（`:537`）+ `openspec/.../design.md:38` 承接。 | **PASS** |
| S3 | **Windows 仅回传事实** | `docs/contracts/README.md:59,82,86,89`（节点不写平台轴，`used_for_decision:false`）；`docs/contracts/evidence-verdict.md:18,53`；`docs/contracts/security-node.md:517`；`docs/contracts/ui-report-knowledge-audit.md:26-27,516`；根 `plan.md:436,442,486`（M-05/M-07/M-06 确认）。 | **PASS** |
| S4 | **离线续跑** | `docs/v2/SOLUTION.md:251,498,517`；`docs/v2/README.md:17`；`openspec/.../design.md:52-56`（Execution lifecycle）；`openspec/.../specs/completion-gate/spec.md:25-31`（Requirement + 2 Scenario）；`openspec/.../specs/platform-events-push/spec.md:19-22`；`openspec/.../specs/ui-v2/spec.md:19-22`。 | **PASS** |
| S5 | **STOP-first 重连** | `docs/v2/SOLUTION.md:251,498,518`；`openspec/.../design.md:56`；`openspec/.../specs/completion-gate/spec.md:32-35`；`docs/VERSIONING.md:89`（§2.4 第 4 项）。 | **PASS** |
| S6 | **释放 / 证据 / 最终判定分离** | `docs/v2/SOLUTION.md:519,744,745,746`；`openspec/.../design.md:52-56`；`openspec/.../specs/completion-gate/spec.md:36-45`（Requirement + 2 Scenario）；`docs/VERSIONING.md:90-91`；`docs/contracts/evidence-verdict.md:16`（设备是否释放不是 PASS 前提）。 | **PASS** |
| S7 | **活动文档是否仍残留 SQLite / 租约到期矛盾** | SQLite：0 未标注。租约/心跳：8 行危险扫描命中全部为否定表述；`lease_expired` 在 `docs/v2`/`openspec` **0 命中**。逐行复核另发现 6 处未逐处标注的旧终态语句，均在带“整份历史参考”横幅的文件内（见 §5 F-03）。 | **PASS（附低危残留）** |

---

## 4. 逐产物 PASS / NEEDS-FIX

### 4.1 `docs/delivery/openspec-v2-sync.md` — **NEEDS-FIX**

核心证据可复算：425 行、§8.3 危险命中 8 行、§5.2 新增 3 Requirement / 6 Scenario（行 17,21,28,32,39,43）、§8.9 F1/F2 命令结果、§8.5 OpenSpec strict 通过、§8.8 链接目标存在，均与实测一致。`docs/VERSIONING.md` §2.4 六行（86–91）与 §0.1 返工记录一致。

但“未解决项”两节已落后于后续修复：

- `openspec-v2-sync.md:357`（§9.1）仍称源草案 I-21、§7 租约规则、模块 §2.6 “仍写旧表述”“建议后续单独任务修订”。实际已由 `approved-draft-reconciliation.md` 于 2026-10-29 修正（见 `03`/`04` 证据）。
- `openspec-v2-sync.md:358`（§9.2）仍称 `security-node.md` 仍有 `lease_expired` 旧措辞、需 P0-05 修正。实际 `docs/contracts/README.md:58` 已改为“已无 `lease_expired` 旧措辞”，且 `phase0-contract-remediation-verification.md:109` 记 F-11 已关闭，`grep lease_expired docs/contracts/security-node.md` 为 0 命中。

判定：证据主体 PASS，但因两个“未解决项”事实过期，本产物计 **NEEDS-FIX（低危，记录型）**。按 `approved-draft-reconciliation.md:193`（§6 第 7 项）的既定处理，**不回写历史证据报告**，应由归档索引附链接或后续状态更新任务处理。

### 4.2 `docs/delivery/p0-03-postfix-verification.md` — **PASS**

V1–V5 全部复现：

- V1：`docs/VERSIONING.md:80` 章节标题，规则表 `:86-91` 共 6 行，逐项与 `openspec-v2-sync.md` §0.1 F1 对应。
- V2：4 处 formal PASS 均含 `execution_status=COMPLETED` 与 `RUNNING`/`NOT_STARTED` 排除句（`docs/v2/SOLUTION.md:537`、`docs/v2/IMPLEMENTATION-PLAN.md:162`、`openspec/.../design.md:38`、`openspec/.../specs/completion-gate/spec.md:17-19`）。
- V3：`openspec validate ai-test-platform-v2 --strict` → `Change 'ai-test-platform-v2' is valid`，EXIT=0。
- V4：危险扫描 8 行；`wc -l` 425 行；C-19 已改正。
- V5：`git diff --check` 通过；行尾空白 0。

限制声明（§5 未跟踪路径）仍成立：`git status` 显示 `docs/VERSIONING.md` 与 `docs/delivery/` 为 `??`，故 `git diff --check` 不覆盖这些路径，需辅助行尾空白扫描。

### 4.3 `docs/delivery/source-reconciliation.md` — **NEEDS-FIX**

登记表结构与 21 个冲突类（SR-01..SR-21）完整，§3 主表 + §4 位置索引各 21 行。但 4 处状态未随后续修复回填：

| 位置 | 现状 | 应有状态 | 证据 |
|---|---|---|---|
| `source-reconciliation.md:80`（SR-10） | `开放—P0-09` | 已闭环（源草案已修） | `architecture-proposal.md:126`（§7 规则 4 已改）、`:387`（R-3 修订说明）；`module-design.md:101-114,203` |
| `source-reconciliation.md:81`（SR-11） | `开放—P0-09` | 已闭环（源草案已修） | `architecture-proposal.md:91`（I-21 已改）、`:385`（R-1） |
| `source-reconciliation.md:82`（SR-12） | `开放—P0-05` | 已闭环（README 已修；映射问题另见 C-03） | `docs/contracts/README.md:58`；`phase0-contract-remediation-verification.md:109` |
| `source-reconciliation.md:48-49`（§1.3 速览） | 仍写“源草案旧条留待 P0-09（SR-10）/（SR-11）” | 应改为已由 `approved-draft-reconciliation.md` 关闭 | 同上 |

判定：**NEEDS-FIX（登记状态陈旧，非语义冲突）**。该文件是唯一冲突登记表（`docs/VERSIONING.md:232` §9），状态过期会误导后续读者以为源草案仍有冲突。

### 4.4 `docs/delivery/approved-draft-reconciliation.md` — **PASS**

四份草案的修改均落盘，且原文保留在新增“修订说明”表：

- `architecture-proposal.md:91`（I-21 新语义）、`:126`（§7 规则 4）、`:128`（§7 规则 6）、`:379-389`（§18 R-1..R-4）。
- `module-design.md:101-114`（§2.6 三分类）、`:203`（§4.2 失联）、`:390-391`（§11 修订说明）。
- `variant-b-balanced.md:170,172,174` 与 `:296-305`（§16 修订说明）。
- `optimization-roadmap.md:66` 与 `:122-130`（§10 修订说明）。

残留扫描仅命中各“修订说明”表的“原表述（摘要）”列（`module-design.md:390`、`variant-b-balanced.md:302,304`、`optimization-roadmap.md:128`），正文规范语句 0 处，与该报告 §5.2 一致。

### 4.5 `docs/VERSIONING.md` — **PASS**

- §2.4（`:80`）六项规则表 `:86-91`，覆盖 PostgreSQL、五轴、离线续跑、STOP-first、释放/证据/判定分离、`cleanup_receipt`，并声明规范效力仍来自第 1 层与根 `plan.md`。
- §2 第 4 层（`:30`）明确 `docs/v2`/`openspec` 同步后为“实现参考”，冲突时以第 1 层为准；第 5 层（`:31`）历史归档只读。
- §9（`:232`）指定唯一冲突登记表为 `source-reconciliation.md`，链接可解析。

备注（不计缺陷）：`docs/VERSIONING.md:30` 称 `docs/v2` 为“实现参考”，而 `docs/v2/README.md:12,46` 自称“整体转为历史参考”。两者都否认其当前规范效力，只是标签措辞不同，不构成事实源冲突。

### 4.6 `docs/v2/**` — **PASS（附低危残留）**

- PostgreSQL-only、五轴正式 PASS、离线续跑、STOP-first、释放/证据/判定分离、`cleanup_receipt` 均已落点（见 §3 S1/S4/S5/S6）。
- 6 处旧终态语句未逐处标注，但均处于带“整份历史参考”横幅的文档中：`SOLUTION.md:7`（整份历史）、`UI-DESIGN.md:3,14,17`（整份历史 + 明确点名旧租约失败文案）、`IMPLEMENTATION-PLAN.md:11`（整份历史）。逐处清单见 §5 F-03。
- 二进制/图源仍为旧口径：`docs/v2/SOLUTION.pdf`、`docs/v2/diagrams/*.svg|png`、`docs/v2/diagrams/FLOWCHARTS.pdf`。已在 `openspec-v2-sync.md:360`（§9 第 4 项）与 `source-reconciliation.md:88`（SR-18）登记为待 Phase 1/3 重绘，不构成本轮语义缺陷。

判定：**PASS**；残留属“未逐处标注 + 未重绘”，不改变活动规范口径。

### 4.7 `openspec/**` — **PASS**

- 13 个 Markdown + `config.yaml`；`openspec validate --strict` EXIT=0。
- `design.md:3-10` 同步说明；`:14,21,60` PostgreSQL；`:36-50` 五轴/C1–C7 映射；`:52-57` 离线续跑/STOP-first/释放分离。
- `specs/completion-gate/spec.md` 4 Requirement / 8 Scenario（新增 3/6）：正式 PASS（`:17-19`）、旧终态仅别名（`:21-23`）、离线续跑（`:25-31`）、重连 STOP-first（`:32-35`）、释放/证据/判定分离（`:36-45`）。
- `specs/ui-v2/spec.md:13-22` 五轴分离展示 + 离线仍占用；`specs/platform-events-push/spec.md:19-22` 通信丢失不误发终态/释放；`specs/task-playbook/spec.md:4` 终态限定五轴与归档前置。
- SQLite 0 未标注；`lease_expired` 0 命中。
- 未在 `openspec` 中写入“Windows 仅事实”专属条款，但也没有相反表述；该边界由更高层 `docs/contracts` 与 `plan.md` 承担（见 §3 S3）。

### 4.8 主计划 `.omo/plans/noahsark-platform-delivery.md` + 根 `plan.md` — **PASS**

- 主计划 `:6` 写明“Linux 控制面…判定；Windows Node Agent 只执行冻结工件并回传事实；PostgreSQL 唯一正式库；断线续跑、STOP-first、释放/证据/判定严格分离”。
- 主计划 `:38`（P0-03）列出六个同步主题；`:41`（P0-06）含 Linux 独立复核。
- 根 `plan.md`：`:430`（M-04 八条）、`:436`（M-05 八条）、`:442`（M-07 八条）、`:479`（M-04 七条）、`:486`（M-06 七条）、`:547`（A-3）、`:559`（A-5）、`:611`（S5-3）、`:660`（AC-11..14）均一致表达 Linux 权威/Windows 仅事实/离线续跑/STOP-first/释放分离。

---

## 5. 发现清单（按严重度）

> 本轮**未修改**任何源文档；以下均为登记项，等待对应责任任务处理。

| ID | 严重度 | 位置 | 问题 | 建议动作（提案） |
|---|---|---|---|---|
| F-01 | 中（记录型） | `docs/delivery/source-reconciliation.md:80-82,48-49` | SR-10/SR-11/SR-12 状态仍为 `开放—P0-09` / `开放—P0-05`，但对应修复已完成 | 更新为“已闭环（源草案已修/契约 README 已修）”，并保留原处置历史 |
| F-02 | 低（记录型） | `docs/delivery/openspec-v2-sync.md:357,358` | §9.1/§9.2 的“仍未解决”已被后续修复推翻 | 由归档索引附 `approved-draft-reconciliation.md` 与 `phase0-contract-remediation-verification.md` 链接；不原地改写历史报告 |
| F-03 | 低（标签型） | `docs/v2/UI-DESIGN.md:171`（Verdict 术语表单值）、`:2383`（设备/租约失败 → `INFRA_ERROR`）、`docs/v2/SOLUTION.md:403`（图 5-2 旧终态集）、`:741`（旧终态名 + C7）、`docs/v2/IMPLEMENTATION-PLAN.md:178`（同 `:741` 英文版）、`:857`（device offline → `BLOCKED_HUMAN`/`INFRA_ERROR`） | 6 处旧语句未逐处加“历史/已取代”标签；已被文件级历史横幅覆盖，但单行引用时可能误读 | 下次文档整理时逐处加行内标签或图注；不得据其改变离线/租约语义 |
| F-04 | 低（资产型） | `docs/v2/SOLUTION.pdf`、`docs/v2/diagrams/*.svg|png`、`FLOWCHARTS.pdf` | 旧终态/旧门禁未重绘（SR-18） | 由 Phase 1/3 重绘并归档；在此之前不得作为当前图示依据 |
| F-05 | 低（标签型） | `docs/v2/README.md:12,46` vs `docs/VERSIONING.md:30` | 同一目录一处称“整体历史参考”，一处称“实现参考” | 统一为“与已批准边界一致的实现参考（历史内容保留）”；不改变效力 |
| F-06 | 低（边界型，不判冲突） | `docs/contracts/security-node.md:255` | 证书过期可安全停止已启动运行，与“通信/租约事件不停止”并存；属身份安全事件 | 契约冻结时明确“身份失效可安全停止”与“通信失联必须继续”的边界（`contract-residual-followup.md` §5 已提出） |
| F-07 | 低（跨契约，既有登记） | `docs/contracts/schemas/security/lease.schema.json:136`、`security-node.md:489-500,648`、`domain.md:441` | `lease.state` 的 `expired` 语义正确（仅续约截止），但缺 `security.lease.state → domain Lease.state` 逐值映射 | 已由 `contract-residual-followup.md:42` C-03 登记；契约冻结前补映射 |
| F-08 | 信息（非缺陷） | `docs/v2/**`、`openspec/**` | 未显式写“Windows 仅事实/Linux 权威”条款；该规则由 `docs/contracts` 与 `plan.md` 承担 | 无需在本轮补写；若要在实现参考中自足，可在 Phase 2 落地文档引用契约条款 |

---

## 6. 计数汇总

| 计数项 | 数值 |
|---|---|
| 复核产物单元 | 8 |
| PASS / NEEDS-FIX | 6 / 2 |
| 七项语义检查 | 7 / 7 PASS |
| `docs/v2` + `openspec` SQLite 提及 | 29（未标注 0） |
| 危险旧口径命中 | 8（全部否定/正确） |
| `lease_expired` 在 `docs/v2`/`openspec` | 0 |
| 五轴正式 PASS 同步点 | 4（`SOLUTION.md:537`、`IMPLEMENTATION-PLAN.md:162`、`design.md:38`、`completion-gate/spec.md:17-19`） |
| `completion-gate` Requirement / Scenario | 4 / 8（新增 3 / 6） |
| `docs/VERSIONING.md` §2.4 规则行 | 6（`:86-91`） |
| 未逐处标注的旧终态语句 | 6（3 文件，均在历史横幅内） |
| 陈旧“未解决/状态”条目 | 6（`openspec-v2-sync.md` 2 + `source-reconciliation.md` 4） |
| 陈旧二进制图示资产 | 3 组（PDF / SVG+PNG / FLOWCHARTS.pdf） |
| 新发现的语义冲突 | **0** |

---

## 7. 阻塞项（Phase 0 仍不可关闭）

以下均为既有登记，不由本报告关闭；本报告**不声称 Phase 0 已关闭**。

1. **5 个 `open-blocker`**（`docs/delivery/p0-09-decision-reconciliation.md:148-158`）：T-09 节点外部事实、T-10 设备外部事实、T-11 真实 formal profile/脚本、T-12 证据根/NAS/第二服务器/恢复演练、T-23 Phase 0 验证与归档负责人/状态。
2. **A-0 未通过**：`docs/delivery/a0-readiness-followup.md:16` — 85 条输入 `known 20 / placeholder 14 / unknown 51`；六类外部事实无直接证据；`environment-inputs.md` §11 签署清单全部未勾选。
3. **契约仍为候选**：`docs/contracts/` 全部 `frozen-candidate`（`docs/VERSIONING.md:61-73` §2.3；`construction-progress.md` P0-04..P0-08 行）。
4. **契约残余 9 项**（`contract-residual-followup.md:31-45`）：R-01..R-03 + C-01..C-06；非阻断但冻结前须裁决。
5. **Phase 1 UI 候选未独立核验**：`docs/delivery/ui-candidate-verification.md` 不存在（`restart-handoff-20261029.md`），与本次并行的 UI Agent 相关；本报告不评价 UI。
6. **P0-11 归档为候选归档**：`construction-progress.md` P0-11 行明确“归档完成不等于 Phase 0/实施冻结”。

---

## 8. 本报告自检

```bash
cd /home/bszheng/NoahsArk
grep -nP '[ \t]+$' docs/delivery/source-sync-followup-verification.md | wc -l   # 0
git diff --check                                                              # 无输出，EXIT=0
git status --short docs/delivery/source-sync-followup-verification.md          # ??（新增未跟踪）
```

说明：

- 本报告只新增一个文件；未修改任何源文档、契约、`docs/v2`、`openspec`、`.omo`、根 `plan.md`、产品代码或凭据。
- `docs/delivery/` 当前为未跟踪目录，因此 `git diff --check` 不覆盖本报告；已用行尾空白扫描补充（0 处）。
- 本报告已完整复读一次，行号引用以当前工作区文件为准。
- 未执行 commit / push / 部署 / 真机 / SSH。

---

## 9. 最终判定

**NEEDS-FIX（非阻塞、记录与标签层）**。

- 已批准的 Phase 0 源同步语义（PostgreSQL-only、Linux 权威判定、Windows 仅事实、离线续跑、STOP-first、释放/证据/判定分离）在活动规范层**全部成立**，未发现语义层冲突。
- 需要修的是两份证据/登记产物的状态回填（F-01、F-02）与历史文档的行内标签/二进制重绘（F-03、F-04）；这些不改变任何规范口径，也不授权实现、测试、部署或发布。
- Phase 0 **仍未关闭**：5 个 `open-blocker` + A-0 未通过 + 契约为候选。
