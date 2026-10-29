# UI 基线差距分析独立核验（UI Baseline Gap Verification）

> 核验对象：`docs/delivery/ui-baseline-gap-analysis.md`（v0.1，2026-10-28，665 行）
> 核验日期：2026-10-29
> 核验范围：仅核验该差距分析的**事实准确性、引用完整性、覆盖完整性**。
> 核验结论：**NEEDS-FIX**
> 非授权边界：本报告不评审最终 UI 设计，不批准 IA、令牌、路由、页面规格或实施；不把 mock 烟测当作真实 UI 证据；不宣称任何 AC 已通过。本报告只新增本文件，未修改 `design/`、`docs/v2/`、`docs/contracts/`、`plan.md`、`.omo` 或产品代码。

---

## 1. 核验方法与证据

本次核验使用只读检查，不依赖截图内容判断：

- 读取差距分析全文（665 行）及其引用的关键文档、契约、原型与烟测 JSON。
- 用 Python `json.load()` 校验两份烟测 JSON 可解析，并提取 `routeCount`、`navCount`、`routes`、`navResults`、`detailResults`、`screenshots`、`failedRoutes`、`allPass`。
- 用 `grep`/`sed` 抽查 `design/apple/ui-prototype.html` 的侧栏、任务页签、路由分发，以及 `design/ui-prototype.html` 的知识治理队列、系统设置备份区。
- 用脚本检查差距分析中的 36 个相对链接：36 个全部可解析，0 缺失。
- 运行 `git diff --check`：退出 0；但该文件为未跟踪文件，`git diff --check` 实际不覆盖其内容（见 F9）。另用 `grep -nP '[ \t]+$'` 复核差距分析，0 行尾空白。
- 未读取截图内容；本报告不基于截图作任何视觉结论，只核对截图资产是否存在及其数量。

关键计数核验结果：

| 证据 | 实测值 | 对应差距分析位置 |
|---|---|---|
| Apple 烟测 `routeCount` | 15 | 第 129 行“15 路由” |
| Apple 烟测 `navCount` | 11；`navHashes` 11 项 | 第 129 行“15 路由 × 3 视口”及第 2.4 节 |
| Apple 烟测 `routes` | 15 项，含 overview/tasks/task-detail/knowledge-detail/node-detail 等 | 第 129 行 |
| Apple 烟测 `screenshots` | 7 项 | 第 129 行“截图 7 张” |
| Apple 烟测 `failedRoutes` / `allPass` | `[]` / `true` | 第 129 行 |
| v2 烟测 `navResults` / `detailResults` | 11 / 4 | 第 128 行“11 个导航 + 4 个详情” |
| v2 原型侧栏导航 | 11 项，`design/apple/ui-prototype.html:1379-1389` | 第 2.1 节、第 3.1 节 |
| 任务详情页签 | 11 项，`design/apple/ui-prototype.html:1710` | 第 3.1 节 |
| 路由分发 | 15 个 `case`，`design/apple/ui-prototype.html:1742-1758` | 第 2.1 节、第 3.1 节 |

---

## 2. 逐项核验结论

| # | 检查项 | 结论 | 证据与说明 |
|---|---|---|---|
| 1 | 旧 15 路由 / 11 导航 / 11 页签计数 | **PASS** | Apple 烟测 `routeCount=15`、`navCount=11`（`design/apple/ui-smoke-result.json:23-24`）；侧栏 11 项（`design/apple/ui-prototype.html:1379-1389`）；任务页签 11 项（同文件 `:1710`）；路由 `switch` 15 个分支（同文件 `:1742-1758`）。差距分析第 3.1 节列出的 11 导航与 11 页签与原型一致。 |
| 2 | 新 IA 为 10–12 区域 | **PASS** | 差距分析第 4.1 节列出 12 个区域（第 212-223 行），第 4.2 节给出桌面 8 个一级入口 + 4 个治理组（第 227-228 行），12 = 8 + 4，落在 10–12 范围内。第 4.3 节有 39 条屏幕记录，39 条路由均唯一。 |
| 3 | Task / Revision / Run / Case / Attempt 主线 | **PASS** | 第 5.1 节给出 `Intake → Task + Revision → Approval → static/smoke/formal run → Attempt → 五轴 Verdict → Report`（第 318-353 行），并明确烟测不入正式分母；与 `docs/contracts/domain.md:12`、`:40`、`:252-269` 的对象与门禁顺序一致。 |
| 4 | 五轴判定 | **NEEDS-FIX** | 五轴名称与“禁止折叠为单状态”的方向正确，但正式 PASS 条件漏掉 `execution_status`，且 UI 投影的 `UNKNOWN` 与权威枚举混写。详见 F2、F3。 |
| 5 | offline / STOP-first | **PASS** | 第 5.4 节要求离线时同时显示通信 `OFFLINE`、执行 `RUNNING`、占用 `OCCUPIED`、`execution_permit=GRANTED`，并禁止“已停止/设备空闲/可重派”（第 373 行）；STOP-first 顺序完整（第 375 行），与 `docs/contracts/domain.md:646-679` 一致。 |
| 6 | 设备释放 | **PASS** | 第 5.4 节列出本地停止、安全清理、占用对账三项前置，并要求缺 `cleanup_receipt` 不得显示“已释放”，释放不等于通过（第 377-378 行）；与 `docs/contracts/domain.md:681-689`、`:476-483` 一致。 |
| 7 | 证据 manifest | **PASS** | 第 5.5 节要求 schema、digest、size、kind、collected_at、node receipt、per-device/per-case 分母与 `partial`（第 385 行）；`docs/contracts/evidence-verdict.md:161-240` 的 manifest 结构覆盖这些字段，且第 106 行明确 partial/uploading 不计为已核验。 |
| 8 | 审计 / 知识 | **NEEDS-FIX** | 审计部分与契约一致；但“旧 UI 没有候选队列”的断言与旧原型相反，且 AC-9 把规范中的禁止文案误写成旧 UI 实际文案。详见 F1、F4。 |
| 9 | 十二类状态 | **PASS** | 第 6.1 节恰好列出 12 类：loading、empty、error、blocked、stale、offline、partial-evidence、no-permission、draining、quarantined、reconciling、unknown-progress（第 401-412 行）；第 6.2 节给出 offline+running+occupied、partial-evidence+PASS、quarantined+occupied 等关键组合（第 414-426 行）。 |
| 10 | 深色模式与可访问性缺口 | **PASS** | 深色：v2 仅局部深色终端（`docs/v2/UI-DESIGN.md:76`），Apple 原型 `color-scheme` 固定 light（`design/apple/ui-prototype.html:6`、`:16`），两套原型均无 `prefers-color-scheme`（grep 0 命中）。可访问性：未跑 NVDA/axe、200% 未回归、高对比度未验证、Apple 未实现完整 focus trap，分别见 `docs/v2/UI-REVIEW.md:138-143`、`docs/v2/UI-DESIGN-APPLE.md:449-450`。第 9.1 节结论与这些来源一致。 |
| 11 | 来源指针 | **PASS（有轻微漂移）** | 差距分析 36 个相对链接全部可解析，0 缺失。但第 83 行的 v2 截图清单和第 128 行的 v2 烟测“3 视口”表述有引用精度问题，见 F7、F8。 |
| 12 | 是否虚构截图结论 | **PASS** | 差距分析第 13.2 节明确“未做视觉评审”（第 653 行），第 2.4 节把截图标为“不代表真实数据或全部页面”，未出现“截图显示/从截图可见”之类未执行的视觉结论。 |

---

## 3. 必须修正的问题

### F1（高，准确性）旧知识页“没有候选队列”的断言与原型相反

- 差距分析位置：第 170 行“旧 UI 有‘提升/撤回’，但没有候选队列与禁止自动推广的强约束”；第 182 行“增加候选队列入口”。
- 实际证据：
  - `design/ui-prototype.html:2394` 的知识页侧栏直接渲染“治理队列”，包含“候选 24 / 有争议 3 / 陈旧 18 / 待合并 5”，并列出“候选 · 音频回环阈值 · 未评审”，卡片副标题为“需要人处理，不自动批准”。
  - `design/ui-prototype.html:2270` 的任务知识页写明“候选不会自动 approved”。
  - `design/ui-prototype.html:2421` 的治理动作要求“角色 4 + 理由 + review receipt”，并说明“撤回保留修订，不物理删除”。
- 影响：低估旧 UI 已有能力，可能把“新增候选队列”误列为从零建设，导致 Phase 1 的范围与工作量判断偏大；也会让 KN-01/KN-03 的“扩展”依据不准确。
- 修正建议：改为“旧 UI 已有治理侧栏、候选计数与‘不自动批准’文案，但没有独立的候选生命周期页（PROPOSED→UNDER_REVIEW→APPROVED→PROMOTED）和完整的权限/状态机”；第 182 行的“增加候选队列入口”改为“把侧栏治理队列提升为 KN-03 独立页并补齐生命周期”。

### F2（高，完整性）正式 PASS 条件漏掉 execution_status

- 差距分析位置：第 367 行“正式 PASS 的 UI 条件：五轴同时满足 `VALID + COMPLETE + PASS + PASS`”。
- 实际契约：`docs/contracts/domain.md:620-627` 明确要求五轴全部满足：
  - `execution_status == COMPLETED`
  - `validity_status == VALID`
  - `business_verdict == PASS`
  - `evidence_status == COMPLETE`
  - `verification_status == PASS`
- 影响：差距分析声称“五轴同时满足”，实际只列了四个值，漏掉执行轴；在 fail-closed 语义下会误导 UI 把“未执行/执行中止但其余轴看似正常”的结果当成可 PASS。
- 修正建议：改为 `COMPLETED + VALID + PASS + COMPLETE + PASS`，并直接引用 `docs/contracts/domain.md:620-627`；同时保留第 361 行“执行完成 ≠ PASS”的说明。

### F3（中，准确性）五轴允许值混用了权威枚举与 UI 投影占位

- 差距分析位置：第 361、364、365 行分别给 `execution_status`、`evidence_status`、`verification_status` 加入 `UNKNOWN`。
- 实际证据：
  - 权威契约 `docs/contracts/domain.md:309-313` 的枚举为：execution 无 `UNKNOWN`；evidence 无 `UNKNOWN`；verification 无 `UNKNOWN`。
  - `docs/contracts/evidence-verdict.md:880` 明确“`verdict.axes.evidence_status` 不得写入 `UNKNOWN`；未核验写 `UNVERIFIED`，缺失写 `INCOMPLETE`，冲突写 `CONFLICTED`”。
  - `docs/contracts/ui-report-knowledge-audit.md:102-106` 才允许 UI 投影层出现 `UNKNOWN`（作为“尚未读取”的展示占位）。
- 影响：差距分析没有区分“权威判定轴”与“UI 投影占位”，读者可能把 `UNKNOWN` 当成可写入的第五轴值，违反“UI 不得成为第二事实源”。
- 修正建议：把第 5.3 节表格拆成两列或加注：“左列为权威枚举（domain.md 9.1），`UNKNOWN` 仅用于 UI 投影占位，不得写入 verdict axes”；并在第 367 行 PASS 条件中只使用权威枚举。

### F4（中，准确性）AC-9 把规范里的禁止文案误写成旧 UI 实际文案

- 差距分析位置：第 513 行“旧 UI 有‘AI 已确认’类风险文案”。
- 实际证据：
  - `docs/v2/UI-DESIGN.md:2613` 位于 §10.6“禁止的声明”，原文是“- ‘AI 已确认’替代证据。”它是旧规范明令禁止的文案，不是旧 UI 已存在的文案。
  - 旧原型实际有“机器复算 vs runner”“不信任 runner 自报 PASS”等反向约束（`design/ui-prototype.html:2252`、`:2796`），方向上与 AC-9 一致。
- 影响：把“规范禁止项”当成“旧 UI 缺陷”，会高估旧 UI 与 AC-9 的差距，也会削弱差距分析的可信度。
- 修正建议：改为“旧规范已把‘AI 已确认’列为禁止文案；旧 UI 已有 runner/复算分离，但仍缺五轴与 evidence/verification 的逐项展示”。

### F5（中低，准确性）AC-14 “旧系统设置只有审计”表述过强

- 差距分析位置：第 518 行“旧系统设置只有审计，无恢复演练”。
- 实际证据：`design/ui-prototype.html:2683` 的系统设置包含“存储”卡片、最近备份时间、`备份数据库` 按钮；`docs/v2/UI-DESIGN.md:582` 与 `:2961` 也把系统设置描述为“开关、角色、安全、审计、存储”。
- 影响：旧系统确实没有恢复演练/对账页，但不是“只有审计”；过强表述会掩盖可复用的备份入口，也会让 AC-14 的差距描述不精确。
- 修正建议：改为“旧系统设置只有审计与备份入口，没有恢复顺序、恢复演练和占用对账页面”。

### F6（低，计数）UI-REVIEW 的交互项应为 10 项，不是 11 项

- 差距分析位置：第 130 行“交互 11 项”。
- 实际证据：`docs/v2/UI-REVIEW.md:69-78` 的交互表共 10 个场景：导航、手机抽屉、接管模式、任务页签、模型切换、版本漂移、推送测试、批准计划、命令面板、实时状态。
- 影响：计数错误会削弱第 2.4 节“证据一致性”论证的可复核性。
- 修正建议：改为“交互 10 项”，或改为“交互表列出的 10 个场景”。

### F7（低，资产清单）v2 截图清单误列 models

- 差距分析位置：第 83 行“v2 截图 … overview/task-detail/models 的 1440/768/390 等 7 张”。
- 实际证据：`design/preview/` 只有 `desktop-1440.png`、`overview-desktop.png`、`overview-phone.png`、`overview-tablet.png`、`phone-390.png`、`tablet-768.png`、`task-detail-1440.png`；没有 `models*.png`。`models-desktop.png` 存在于 `design/apple/preview/`。
- 影响：资产来源与复用判断会错位；v2 截图并不能证明 models 页的视觉基线。
- 修正建议：v2 行改为“overview/task-detail + 视口外壳 7 张”；models 截图只写在 Apple 行。

### F8（低，证据范围）v2 烟测的“3 视口”只覆盖响应式外壳，不是逐路由三视口

- 差距分析位置：第 128 行“11 个导航 + 4 个详情可达；3 视口”。
- 实际证据：`design/preview/ui-smoke-result.json:16` 的 `navResults` 与 `:132` 的 `detailResults` 均为单次记录，没有 viewport 字段；只有 `:169` 的 `responsive` 数组记录 desktop/tablet/phone 三档的 `scrollWidth`、`hOverflow`、`topNav`、`bottomNav`。`docs/v2/UI-REVIEW.md:44` 声称“12 条主路由 × 3 视口 = 36 次渲染”，但该 JSON 未保存逐路由逐视口明细。
- 影响：读者可能把“导航/详情在 3 视口验证过”当成已证明事实；实际上 JSON 只能证明响应式外壳与导航可达，不能证明每个详情页的三视口渲染。
- 修正建议：改为“11 个导航 + 4 个详情可达；响应式外壳覆盖 3 视口；逐路由三视口数据未保存在该 JSON”，并把 UI-REVIEW 的 36 次渲染标为文档声明而非本 JSON 的可复核数据。

### F9（信息，验证方法）`git diff --check` 对未跟踪文件不构成有效检查

- 差距分析位置：第 648 行“验证命令：`git diff --check` 退出 0”。
- 实际状态：该文件当前是未跟踪文件（`git status` 显示 `??`），`git diff --check` 不会检查未跟踪内容，因此退出 0 不能证明该文件无行尾空白。
- 影响：验证声明本身不假（实测 0 行尾空白），但方法不足以支撑“已验证”的结论。
- 修正建议：保留“0 行尾空白”的实测结果，改为 `grep -nP '[ \t]+$' <file>` 或 `git diff --no-index --check /dev/null <file>`，并注明 `git diff --check` 不覆盖未跟踪文件。

---

## 4. 已核实为准确的部分

以下内容与现有资产/契约一致，可作为差距分析的可靠基础：

1. **旧 UI 规模**：15 路由、11 一级导航、11 任务页签。依据：Apple 烟测 `design/apple/ui-smoke-result.json:23-24`、`:505-523`；Apple 原型 `design/apple/ui-prototype.html:1379-1389`、`:1710`、`:1742-1758`；v2 文档 `docs/v2/UI-DESIGN.md:2843-2845`。
2. **旧 UI 证据边界**：两套原型都是 MOCK；Apple 45/45 仅证明 15 路由 × 3 视口的静态渲染、0 console/page error、0 外链、0 溢出，不证明 API、状态 fixture、a11y 或真实设备。依据：`design/apple/ui-smoke-result.json:23-24`、`:505-523`；`docs/v2/UI-REVIEW.md:44-60`；`docs/v2/UI-DESIGN-APPLE.md:476-481`。
3. **12 区域与 8+4 导航模型**：第 4.1 节 12 行、第 4.2 节 8 个一级 + 4 个治理组，数量自洽；第 4.3 节 39 条屏幕记录均有唯一路由。
4. **十二类状态**：第 6.1 节确实定义了 12 类，而不是六类；offline 明确不改变运行态、不表示设备空闲（第 406 行），与 `docs/contracts/domain.md:652-663` 一致。
5. **offline / STOP-first / 设备释放**：第 5.4 节与 `docs/contracts/domain.md:646-689` 的顺序、前置条件和禁止项一致；缺 `cleanup_receipt` 不显示“已释放”与 L-6 一致。
6. **manifest 与报告**：第 5.5 节的 manifest 字段与 `docs/contracts/evidence-verdict.md:161-240` 对齐；14 章节报告与 `docs/contracts/ui-report-knowledge-audit.md:202-228` 的 14 行章节表对齐。
7. **审计与知识生命周期**：审计的 actor/action/object/before-after/reason/hash chain 与 `docs/contracts/ui-report-knowledge-audit.md:381-396` 一致；知识条目状态 APPROVED/CORROBORATED/DISPUTED/STALE/RETRACTED/SUPERSEDED 与同文件 `:351-362` 一致；候选生命周期 PROPOSED→UNDER_REVIEW→APPROVED→PROMOTED 与 `:313-333` 一致。问题只在“旧 UI 没有候选队列”这一句（F1）。
8. **可访问性/深色缺口**：第 9.1 节的结论有来源支撑：NVDA/axe 未实测、200% 未回归、高对比度未验证、Apple 无完整 focus trap、两套原型均无全局深色；依据 `docs/v2/UI-REVIEW.md:127-143`、`docs/v2/UI-DESIGN-APPLE.md:440-450`、`docs/v2/UI-DESIGN.md:76`、`:2912`。
9. **来源指针**：36 个相对链接全部可解析；`design/wireframes/` 16 个文件、两套 preview 各 7 张截图、2 份烟测 JSON 均存在。

---

## 5. 结论与放行条件

**总体结论：NEEDS-FIX。**

差距分析在计数、IA 方向、十二状态、离线/STOP-first、设备释放、manifest、审计/知识生命周期和可访问性缺口上大体可靠；但存在两类不能忽略的问题：

- **事实反转**：旧知识页并非“没有候选队列”，旧原型已有治理队列与“不自动批准”文案（F1）。
- **fail-closed 条件不完整**：正式 PASS 条件漏掉 `execution_status=COMPLETED`（F2），且五轴 `UNKNOWN` 的权威/投影边界未说明（F3）。

在任何 Phase 1 IA/页面规格冻结或 P1-02 评审引用本文之前，至少应修正 F1–F4；F5–F8 建议同批修正，以避免资产清单和证据口径继续漂移。

本报告不构成：

- 对最终 UI、视觉方向、12 区域 IA、8 子视图或任何路由的批准；
- 对 mock 烟测作为真实 UI 证据的认可；
- 对任何 AC 已通过、已实现或已验收的声明；
- 对 `docs/v2/`、`design/`、契约、`plan.md` 或 `.omo` 的修改授权。

---

## 6. 核验边界

- 未做用户可用性测试、视觉评审、像素对照或最终 UI 批准。
- 未运行 axe、NVDA、200% 缩放、高对比度、深色模式审计。
- 未接真实 API；所有状态讨论是设计/契约层，不是运行证据。
- 未重新执行烟测；只校验已有 JSON 的字段与计数，以及原型源码中的导航/页签/路由定义。
- 未证明任何 AC 已通过；本报告只判断差距分析是否准确描述了“应由哪些屏幕承载、还缺什么”。

---

## 7. 修正记录（2026-10-29，F1–F9）

本报告结论 **NEEDS-FIX** 对应的 F1–F9 已在 `docs/delivery/ui-baseline-gap-analysis.md` v0.2 中一次性修正。修正为文档订正，不改变本报告的原核验结论，也不构成对最终 UI 的批准。

| # | 修正位置（v0.2） | 修正内容 |
|---|---|---|
| F1 | §3.2 “知识”行；§3.3 第 5、6 行；§2.5 可继承；§8.2 AC-8 | 改为“旧 UI 已有治理侧栏、候选计数、‘不自动批准’与角色+理由+review receipt 约束，但没有独立候选生命周期页与完整状态机”；“增加候选队列入口”改为“把侧栏治理队列提升为 KN-03 独立页并补齐生命周期” |
| F2 | §5.3 正式 PASS 段 | 改为 `execution_status=COMPLETED + validity_status=VALID + business_verdict=PASS + evidence_status=COMPLETE + verification_status=PASS`，并引用 `docs/contracts/domain.md:620-627`；保留“执行完成 ≠ PASS” |
| F3 | §5.3 五轴表 | 拆为“权威枚举（domain.md 9.1）／UI 投影占位”两列，注明 `UNKNOWN` 仅作投影占位、`verdict.axes.evidence_status` 不得写入 `UNKNOWN`，并引用 `evidence-verdict.md:880` 与 `ui-report-knowledge-audit.md:102-106` |
| F4 | §8.2 AC-9 | 改为“旧规范已把‘AI 已确认’列为禁止文案（`docs/v2/UI-DESIGN.md` §10.6）；旧 UI 已有 runner/复算分离，但仍缺五轴与 evidence/verification 逐项展示” |
| F5 | §8.2 AC-14 | 改为“旧系统设置只有审计与备份入口（`design/ui-prototype.html:2683` 的存储卡与备份按钮），没有恢复顺序、恢复演练和占用对账页面” |
| F6 | §2.4 v2 评审记录 | 交互项由 11 改为 10，并列出 10 个场景 |
| F7 | §2.1 v2 截图 | 改为“overview / task-detail 与视口外壳共 7 张；不含 models”；models 截图只保留在 Apple 行 |
| F8 | §2.1 v2 烟测；§2.4 v2 烟测与“证据一致性问题” | 改为“11 导航 + 4 详情可达；响应式外壳覆盖 3 视口；逐路由三视口明细未保存在该 JSON”，并说明 UI-REVIEW 的“36 次渲染”是文档声明、不能由该 JSON 复核 |
| F9 | §13.1 验证命令 | 改为用 `grep -nP '[ \t]+$'` 复核 0 行尾空白（等价 `git diff --no-index --check /dev/null <file>`），并注明 `git diff --check` 不覆盖未跟踪文件 |

保持不变的部分：12 区域 IA、8 个任务子视图、十二类状态、offline/STOP-first/设备释放、证据 manifest、REQ/AC 追溯、offline+running+occupied 等组合矩阵均未改动，且修正过程未新增任何截图视觉结论。

仍有效的边界：v0.2 仍是分析稿。修正事实不等于批准 IA 或页面规格；最终 UI 仍需 Phase 1 的设计冻结、原型与真实浏览器视觉 QA，本报告与差距分析都不构成 UI 验收证据。上述修正尚未经过第二轮独立复核。
