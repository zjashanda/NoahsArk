# NoahsArk Cloudline UI 完整设计与实施交接任务书

> 日期：2026-10-29
>
> 文档用途：把当前 UI 设计相关的事实源、已完成产物、正在进行的工作、剩余任务、实施方法、验证方法和交接规则集中到一个文件，供其他进程直接接手。
>
> 当前状态：**Cloudline 主方向已确认；候选 UI 已实现（12 区域 / 39 路由）并通过确定性检查与本地 Chromium QA；独立视觉评审、所有者批准和 UI 冻结尚未完成。**
>
> 状态标签：`CANDIDATE UI / PROTOTYPE / NOT FROZEN / MOCK DATA`

---

## 0. 接手进程先读

接手后不要重新猜需求，也不要把旧原型当成当前实现。按以下顺序执行：

1. 阅读本文件，确认当前真实状态和剩余工作。
2. 阅读 `/home/bszheng/NoahsArk/design/ui-app/DESIGN.md`，把它作为 Cloudline 视觉和交互实现契约。
3. 阅读 `/home/bszheng/NoahsArk/design/ui-app/routes.json`，把它作为 39 条规范路由的机器可读清单。
4. 阅读第 3 节列出的规范事实源，不从旧截图、旧 15 路由原型或 `docs/v2` 猜当前结构。
5. 所有完整 UI 新代码只写入 `/home/bszheng/NoahsArk/design/ui-app/`。
6. 不删除、不覆盖 `/home/bszheng/NoahsArk/design/ui-demos/`；Precision Desk 和 Focus Flow 必须保留。
7. 一次只允许一个 UI 实现进程写同一批文件。QA 进程必须只读，等实现文件稳定后再运行。
8. 每个批次先落盘最小可运行产物，再验证；不要把 39 页一次性放到一个长时间无产出的任务中。
9. 未通过真实浏览器 QA、用户评审和归档前，不得标记 P1-08，不得声称 UI 已冻结。
10. 不提交、不推送，除非所有者明确要求；不得读取或处理与 UI 无关的敏感文件。

---

## 1. 最终目标

当前要设计的是 **NoahsArk AI 资深测试工程师平台的完整 Web UI 候选原型**，不是静态图片、营销页面、单设备控制页或 TCL 专用页面。

UI 必须支持并准确表达平台完整闭环：

1. 用户通过对话、文件或表单提交测试任务。
2. AI 生成候选测试计划、用例、脚本、formal profile、断言和证据要求。
3. 平台执行静态检查和风险检查。
4. 人工审核并批准不可变 Revision 和 Execution Bundle。
5. Linux 控制面选择合格节点、设备、端点并授予租约。
6. Windows Node Agent 只执行冻结工件并回传事实。
7. 离线时允许安全续跑；重连必须 STOP-first，再补传、去重和对账。
8. Linux 验证证据并独立计算五轴状态和正式业务判定。
9. 平台生成报告、审计记录和知识候选。
10. 只有经审核的知识候选才能推广，历史事实和判定不可覆盖。

本轮 UI 是 Phase 1 高保真、可交互、可浏览器验证的候选原型。它使用本地 mock fixture，不连接真实后端，也不预先决定 P2-05 的 React/Vue/SSR 等生产框架。

---

## 2. 已确认的设计方向和不可变边界

### 2.1 主方向

- 主 UI 风格：**Cloudline**。
- 视觉语言：Apple-informed Quiet Instrument，简约、克制、安静、精确、有技术感。
- 信息重点：权威事实、阻塞项、下一动作、风险和证据，不做监控墙，不做赛博朋克仪表盘。
- 桌面端是完整主体验；平板和手机必须不破版并保留关键事实，但当前不要求制作独立移动产品。

### 2.2 保留方向

以下两个方向不得删除，后续可能复用其布局或密度策略：

- Precision Desk：专业仪器式、高密度扫描。
- Focus Flow：流程优先、顶部导航、主工作区和右侧检查器。

它们当前位于 `/home/bszheng/NoahsArk/design/ui-demos/`。

### 2.3 系统边界

- Linux 控制面是唯一权威业务写入方和最终判定方。
- PostgreSQL 是唯一正式数据库。
- Windows Node Agent 只回传 `node_observed_*` 事实，不能写平台最终 PASS/FAIL。
- UI 是可重建投影，不是第二权威源。
- 审批、门禁、租约、占用、设备释放、证据完整性和最终判定必须分别展示。
- mock fixture 必须明确 `server_authoritative=false`，不能冒充真实平台数据。

---

## 3. 规范事实源和优先级

### 3.1 第一优先级：产品和执行主线

| 文件 | 作用 | 当前状态 |
|---|---|---|
| `/home/bszheng/NoahsArk/1.md` | 最终产品目标、平台闭环、组件边界、建设顺序 | 已完成，333 行；不是 UI 冻结件 |
| `/home/bszheng/NoahsArk/.omo/plans/noahsark-platform-delivery.md` | 66 项唯一执行主计划；Phase 1 为 P1-01..P1-08 | 执行主计划；P1 项仍未勾选 |
| `/home/bszheng/NoahsArk/plan.md` | 当前工作进度和历史记录 | 已追加 Cloudline 实施章节 |

### 3.2 第二优先级：已审核步骤 1–6 的正文和评审记录

| 路径 | 内容 |
|---|---|
| `.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md` | 已批准需求基线 |
| `.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` | 架构方案 |
| `.omo/drafts/01-design/noahsark-v0.0.1-module-design.md` | 模块设计 |
| `.omo/drafts/01-design/noahsark-v0.0.1-tech-radar.md` | 技术雷达 |
| `.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md` | 交付与验收要求 |
| `.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md` | 测试策略 |
| `.omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md` | 优化路线 |
| `.omo/drafts/99-history/20261028-step1-step5-review/` | 第一至第五步评审快照 |
| `.omo/drafts/99-history/20261028-step4-step6-review/` | 第四至第六步补充评审记录 |

注意：评审记录证明规则和准则被审核，不证明产品已经实现、测试或冻结。第六步 v2.1 正文仍存在未同步边界，不能自行补造。

### 3.3 第三优先级：Phase 1 UI 候选规范

| 文件 | 作用 | 状态 |
|---|---|---|
| `docs/delivery/ui-design-research.md` | UI 外部研究和适配原则 | 候选文档，通过文档锚点复核 |
| `docs/delivery/ui-information-architecture.md` | 12 区域、39 路由、四旅程、状态和密度 | 候选文档，通过文档锚点复核 |
| `docs/delivery/ui-design-system.md` | Quiet Instrument 令牌、组件、状态、响应式和可访问性 | 候选文档，通过文档锚点复核 |
| `docs/delivery/ui-screen-specification.md` | 逐屏目的、动作、数据、状态、权限和 AC/L/T 追溯 | 候选文档，通过文档锚点复核 |
| `docs/delivery/ui-candidate-verification.md` | 上述四份文档的独立核验 | 4/4 PASS；仅文档复核，不是 UI QA |

### 3.4 冲突处理

出现冲突时按以下顺序裁决：

1. 当前主计划和所有者最新明确决定。
2. `1.md` 的产品和边界定义。
3. 已审核需求、架构、交付正文。
4. 当前 Phase 1 UI 候选规范。
5. 旧 `docs/v2`、旧 `design/ui-prototype.html`、旧 wireframe 和旧 15 路由原型只作历史参考。

旧 `/aitest/*`、旧 15 路由、横向主导航、旧 C1–C7 不能覆盖当前 12 区域、39 路由、左侧导航、G0–G7 和五轴模型。

---

## 4. 已完成的 UI 相关产物在哪里

### 4.1 当前 Cloudline 完整 UI 主目录

目录：`/home/bszheng/NoahsArk/design/ui-app/`

目前只有两个已完成文件：

#### A. `design/ui-app/routes.json`

状态：**已完成并独立验证**。

验证事实：

- JSON 有效。
- 精确包含 39 条路由，无缺失、无多余、无重复。
- 路由 ID 符合 `MC|IN|TK|RN|EV|DV|RP|KN|RT|AG|AU|ST-NN`。
- 区域数量正确：MC 1、IN 3、TK 9、RN 3、EV 3、DV 3、RP 2、KN 3、RT 2、AG 3、AU 3、ST 4。
- `source` 指向 `docs/delivery/ui-information-architecture.md`。
- `server_authoritative=false`。
- `git diff --check` 通过。

#### B. `design/ui-app/DESIGN.md`

状态：**已完成；已人工读取确认内容存在；尚未通过页面实现后的视觉 QA**。

包含：

- `CANDIDATE UI / PROTOTYPE / NOT FROZEN / MOCK DATA` 边界。
- 事实源引用。
- Cloudline / Quiet Instrument 视觉方向。
- 浅色/深色令牌表。
- 正式 PASS 和状态颜色规则。
- 共享组件 primitive 清单。
- 四档响应式布局。
- 动效、键盘、焦点和可访问性规则。
- 已接受的原型债务。

### 4.2 三方向可运行对比 Demo

目录：`/home/bszheng/NoahsArk/design/ui-demos/`

文件：

- `DESIGN.md`：三方向共同语义和各方向视觉合同。
- `README.md`：运行和评审说明。
- `index.html`：三方向选择器。
- `cloudline.html`：Cloudline 对比 Demo。
- `precision-desk.html`：Precision Desk 对比 Demo。
- `focus-flow.html`：Focus Flow 对比 Demo。
- `app.js`：共享渲染和交互。
- `fixtures.js`：共享 mock fixture。
- `styles.css`：三方向样式。
- `favicon.svg`。
- `plan.md`：早期代理留下的 6 行局部执行记录；不是当前主计划，不要当权威。

Demo 范围：每个方向只有 Mission Control 和 Task Detail 两个视图，用于方向比较，不是 39 路由实现。

运行命令：

```bash
python3 -m http.server 8099 --bind 0.0.0.0 -d design/ui-demos
```

当前事实：文件仍在，但截至本交接文档生成时 **没有活动 PTY 服务**，所以其他进程要预览必须重新启动。不要把“文件存在”写成“服务正在运行”。

### 4.3 旧参考资产

以下内容已经存在，但不是当前 Cloudline 完整 UI：

| 路径 | 内容 | 使用方式 |
|---|---|---|
| `design/wireframes/` | 15 份旧 wireframe Markdown + README | 只参考对象和内容，不沿用旧路由结构 |
| `design/preview/` | 桌面、平板、手机、overview、task detail 截图和 smoke JSON | 历史视觉参考，不是当前 QA 证据 |
| `design/apple/` | Apple 方向 token、原型和预览 | 令牌和质感参考，不是当前实现 |
| `design/ui-prototype.html` | 旧静态原型 | 历史参考，不能替代 39 路由 UI |
| `design/design-tokens.json` | 旧设计 token | 迁移参考；当前新组件使用 `--naa-*` 语义令牌 |

### 4.4 UI 规范和核验证据

- `docs/delivery/ui-candidate-verification.md`：四份 UI 候选文档 4/4 PASS。
- `docs/delivery/ui-information-architecture.md`：12 区域、39 路由和状态矩阵。
- `docs/delivery/ui-screen-specification.md`：逐屏实现要求。
- `docs/delivery/ui-design-system.md`：视觉和组件规范。
- `docs/delivery/ui-design-research.md`：研究基础。

“4/4 PASS”只表示文档内容满足候选评审要求；不表示页面已实现、浏览器 QA 已通过、WCAG 已认证或 UI 已冻结。

### 4.5 总体交付和施工辅助产物

- `/home/bszheng/NoahsArk/1.md`：产品目标与实施总纲。
- `docs/delivery/phase2-landing-plan-draft.md`：Phase 2 技术落地草稿，未冻结。
- `docs/delivery/phase3-construction-plan-draft.md`：Phase 3 施工草稿，未冻结。
- `docs/delivery/phase3-construction-plan-verification.md`：施工草稿核验。
- `docs/delivery/construction-progress.md`：阶段进度；Phase 1 行已同步为“候选原型已实现、本地 Chromium QA 通过、独立视觉评审/所有者冻结未完成”。
- `.omo/ulw-execute/ledger.jsonl`：执行事件 ledger；新增进度必须追加，不覆盖历史。

### 4.6 临时验证工具

以下文件位于临时目录，可能在重启后丢失，其他进程不能只依赖其存在：

- `/tmp/opencode/expected-routes.txt`：39 条期望路由文本。
- `/tmp/opencode/ui-app-check.py`：完整 UI 的确定性检查脚本草稿。
- `/tmp/opencode/ui-demos-baseline.sha256`：Demo 关键文件基线，用于确认保留目录未被改动。

如果临时文件不存在，应根据本任务书和 `routes.json` 重建检查，而不是跳过验证。

---

## 5. 当前尚未完成的内容

完整候选 UI 已实现，下列项目仍 **未完成**：

1. 独立视觉评审（UI-10）：截图已生成，但当前 `poor` 档位模型无图像输入，不能替代视觉签核。
2. 所有者对完整 Cloudline UI 的最终评审与明确批准。
3. P1-01..P1-08 在主计划中仍全部未勾选；UI 尚未冻结。
4. UI 冻结版本号、变更记录、评审包、归档和冻结哈希尚不存在。
5. 真实后端、API、数据库、认证和权限执行尚未接入；所有数据为 fixture。
6. 实时投影、真实离线续跑、STOP 送达和对账尚未接入。
7. RT/AG 写入能力仍被 Q-09 阻塞。
8. 正式无障碍认证、跨浏览器矩阵和真实设备浏览器回归尚未执行。
9. 200% 缩放、forced-colors 和 reduced-motion 仅做了实现层支持，尚未完成逐页实机验收。
10. 生产框架选型（P2-05）尚未决定；当前是静态 HTML/CSS/ES modules 候选原型。

---

## 6. 完整路由清单

机器可读源：`design/ui-app/routes.json`。

### 6.1 Mission Control，1 条

- MC-01 `/console`

### 6.2 Intake，3 条

- IN-01 `/console/intake`
- IN-02 `/console/intake/new`
- IN-03 `/console/intake/:draftId`

### 6.3 Tasks，9 条

- TK-01 `/console/tasks`
- TK-02 `/console/tasks/:taskId/overview`
- TK-03 `/console/tasks/:taskId/revisions`
- TK-04 `/console/tasks/:taskId/plan`
- TK-05 `/console/tasks/:taskId/runs`
- TK-06 `/console/tasks/:taskId/evidence`
- TK-07 `/console/tasks/:taskId/verdict`
- TK-08 `/console/tasks/:taskId/live`
- TK-09 `/console/tasks/:taskId/knowledge`

### 6.4 Runs & Attempts，3 条

- RN-01 `/console/runs`
- RN-02 `/console/runs/:runId`
- RN-03 `/console/runs/:runId/attempts/:attemptId`

### 6.5 Evidence & Verdict，3 条

- EV-01 `/console/evidence`
- EV-02 `/console/evidence/:evidenceId`
- EV-03 `/console/verdicts`

### 6.6 Devices & Nodes，3 条

- DV-01 `/console/devices`
- DV-02 `/console/devices/:deviceId`
- DV-03 `/console/nodes/:nodeId`

### 6.7 Reports，2 条

- RP-01 `/console/reports`
- RP-02 `/console/reports/:reportId`

### 6.8 Knowledge，3 条

- KN-01 `/console/knowledge`
- KN-02 `/console/knowledge/:knowledgeId`
- KN-03 `/console/knowledge/candidates`

### 6.9 Runtime & Toolchain，2 条

- RT-01 `/console/runtime/models`
- RT-02 `/console/runtime/toolchain`

### 6.10 Agents & Reviews，3 条

- AG-01 `/console/agents`
- AG-02 `/console/agents/:agentId`
- AG-03 `/console/reviews`

### 6.11 Audit & Recovery，3 条

- AU-01 `/console/audit`
- AU-02 `/console/audit/:eventId`
- AU-03 `/console/recovery`

### 6.12 Settings & Access，4 条

- ST-01 `/console/settings`
- ST-02 `/console/settings/access`
- ST-03 `/console/settings/notifications`
- ST-04 `/console/settings/retention`

精确总数：`1 + 3 + 9 + 3 + 3 + 3 + 2 + 3 + 2 + 3 + 3 + 4 = 39`。

---

## 7. 必须实现的四条用户旅程

### J1：Intake → 审批 → 门禁

路径：

`IN-01 → IN-02 → IN-03 → TK-03 → TK-05 / RT-02 → DV-01 / DV-02 → RN-02 → TK-06 / TK-07 / EV-03 → RP-02 / KN-03`

必须显示：

- 对话/文件/表单来源。
- 字段来源、冲突和缺口。
- Revision、父修订、冻结摘要和范围。
- 审批人、意见、等待时间和有效范围。
- G0–G7 门禁顺序和阻塞责任方。
- static / smoke / formal 三种 mode 的边界。

禁止：静默选择冲突来源、冻结后原地编辑、超时自动拒绝、烟测进入正式分母。

### J2：Task → Revision → Case → Run → Attempt

路径：

`TK-01 → TK-02 → TK-03 → TK-04 → TK-05 → RN-02 → RN-03`

必须显示：稳定 task_id、修订谱系、case_id/case_version、run mode、attempt ordinal、retry 链、五轴、正式分母资格和 flaky suspect。

禁止：按用例名合并不同 case_version、合并 attempt、把旧证据并入新修订、把节点回执当平台判定。

### J3：离线续跑 → STOP-first → 对账

路径：

`MC-01 / RN-01 / TK-02 / TK-08 / DV-01 → RN-02 → AU-03`

固定顺序：

1. 处理待送达 STOP。
2. 停止后续动作。
3. 补传。
4. 去重。
5. 对账 run / device / lease / epoch / occupancy。
6. 完成后恢复领取。

必须允许组合：`OFFLINE + RUNNING + OCCUPIED + GRANTED`。

禁止：显示已停止、空闲、可重派；对账完成前释放；旧 epoch 改写当前状态。

### J4：证据 → Linux 判定 → 报告

路径：

`TK-06 / EV-01 / EV-02 → TK-07 / EV-03 → RP-01 / RP-02`

必须显示：

- `expected / received / verified` 三列。
- digest、kind、size、collected_at、访问级别和缺口。
- 节点观察事实与 Linux 平台判定分栏。
- 五轴和 fail-closed 原因。
- 报告版本、分母、章节、证据索引和披露级别。
- 设备释放状态独立于证据和业务判定。

---

## 8. 必须实现的语义组件

### 8.1 五轴矩阵

固定顺序：

1. `execution_status`
2. `validity_status`
3. `business_verdict`
4. `evidence_status`
5. `verification_status`

只有精确达到以下组合，才能显示正式 PASS：

```text
COMPLETED / VALID / PASS / COMPLETE / PASS
```

规则：

- `COMPLETED` 是中性执行事实，不是绿色 PASS。
- `business_verdict=PASS` + `evidence_status=INCOMPLETE` 必须显示“不可正式 PASS”。
- 未加载值显示 `UNKNOWN / 尚未读取`，不能留空或猜测。
- 组件提供完整矩阵和紧凑条两种形式，但不能折成一个徽标。

### 8.2 证据账本

必须分别展示：

- expected
- received
- verified

规则：

- received 不等于 verified。
- complete 字节完整不等于 verified。
- 缺失、冲突、未核验必须 fail-closed。
- 受限证据显示 NO ACCESS，不显示为“没有文件”。

### 8.3 租约和设备状态块

必须同时展示：

- lease state
- communication state
- occupancy state
- execution permit
- lease epoch

规则：

- OFFLINE 不等于 IDLE。
- RELEASED 不是 PASS，保持中性色。
- 缺 cleanup receipt 时保持 OCCUPIED。
- quarantined 保持占用并要求人工恢复。

### 8.4 释放前置清单

逐项显示：

- `local_stop_confirmed`
- `safe_cleanup_done`
- `occupancy_reconciled`

三项全真才允许显示 RELEASED。释放、证据完整和最终判定是三个独立平面。

### 8.5 G0–G7 门禁

必须展示 G0 受理、G1 批准、G2 静态、G3 资源、G4 烟测、G5 正式、G6 证据判定、G7 报告知识。

门禁状态只允许：`PENDING / IN_PROGRESS / PASSED / FAILED / BLOCKED / SKIPPED`，投影缺失才用 `UNKNOWN`。

门禁 PASSED 不等于业务 PASS。

### 8.6 状态 Banner

至少覆盖：

- loading
- empty
- error
- no-permission
- blocked
- stale
- offline
- partial-evidence
- draining
- quarantined
- reconciling
- unknown-progress

状态必须使用文字 + SVG 图形/形状 + 颜色，不得只靠颜色。

---

## 9. Fixture 设计要求

所有 fixture 必须带：

```json
{
  "source": "prototype-fixture",
  "schema_version": "0.1",
  "server_authoritative": false
}
```

至少建立以下 fixture 场景：

| Fixture ID | 场景 | 必须证明 |
|---|---|---|
| FX-01 | 正常候选流程 | 页面和导航基础 |
| FX-02 | blocked | 原因、owner、解除条件和下一步 |
| FX-03 | stale + running | 最后权威更新和最后已知活动分离 |
| FX-04 | offline + running + occupied + granted | 离线不等于停止/空闲 |
| FX-05 | reconciling + pending STOP | STOP-first 六步时间线 |
| FX-06 | unknown-progress | percent=null，不出现假百分比 |
| FX-07 | partial-evidence + business PASS | 不可正式 PASS |
| FX-08 | quarantined + occupied | 隔离保持占用 |
| FX-09 | draining + running | 不接新单，已有运行继续 |
| FX-10 | no-permission | 只读摘要 + disabled 原因 |
| FX-11 | empty/loading/error | 所有路由通用状态 |
| FX-12 | complete formal PASS | 精确五轴全满足，作为唯一正式 PASS 正例 |

另外覆盖：

- 五轴全部枚举。
- Gate 六种权威状态。
- lease 六种状态。
- communication、occupancy、permit 全枚举。
- device pool、health、node、spool 和 evidence item 全枚举。
- `COUNTS / QUALITATIVE / INDETERMINATE` 三种进度模式。

禁止在 fixture 中使用真实主机、真实 IP、真实凭据、真实日志、真实音频或未脱敏标识。

---

## 10. 目标目录结构

其他进程应把完整 UI 建设为以下结构，允许微调文件名，但职责必须保持清晰：

```text
design/ui-app/
├── DESIGN.md                 # 已完成，视觉/交互合同
├── routes.json               # 已完成，39 路由 manifest
├── README.md                 # 待建，运行、状态和边界
├── index.html                # 待建，应用入口
├── favicon.svg               # 待建，本地 SVG
├── styles/
│   ├── tokens.css            # 语义令牌和主题
│   ├── base.css              # reset、排版、焦点、辅助类
│   ├── shell.css             # 四档响应式和滚动所有权
│   └── components.css        # 共享组件
├── src/
│   ├── app.js                # 启动、渲染、事件绑定
│   ├── router.js             # hash 路由、参数匹配、深链
│   ├── route-manifest.js     # 读取/校验 routes.json
│   ├── fixtures.js           # fixture 注册表
│   ├── semantics.js          # 五轴/PASS/释放/权限纯函数
│   ├── icons.js              # 本地 SVG 图标函数
│   ├── components.js         # 共享 primitive
│   ├── shell.js              # 侧栏、顶栏、手机导航和 More
│   └── pages/
│       ├── mission.js
│       ├── intake.js
│       ├── tasks.js
│       ├── runs.js
│       ├── evidence.js
│       ├── devices.js
│       ├── reports.js
│       ├── knowledge.js
│       ├── runtime.js
│       ├── agents.js
│       ├── audit.js
│       └── settings.js
├── checks/
│   ├── contract-check.mjs    # 路由和语义检查
│   └── smoke-check.mjs       # HTTP 和 DOM 检查
└── evidence/                 # QA 后生成，不放敏感数据
```

实现应保持静态 HTML/CSS/ES modules；不要引入 npm 包、CDN、远程 API、React/Vue/Svelte、外部字体或构建步骤。生产框架由 P2-05 后续 ADR 决定。

---

## 11. 分批实施 WBS

### UI-00：交接和基线确认

状态：**已完成**。

产物：

- 本文件。
- `routes.json`。
- `DESIGN.md`。
- 规范事实源清单。

退出条件：接手进程能准确说出已完成/未完成边界，不把 Demo 或候选文档当成完整 UI。

### UI-01：静态应用骨架

状态：**待实施**。

实现：

1. 创建 README、index、favicon、CSS 和 JS 入口。
2. 建立 hash router，使 `/console/*` 规范路径可通过 hash 或路由映射深链。
3. 建立 persistent candidate ribbon：`CANDIDATE UI · PROTOTYPE · NOT FROZEN · MOCK DATA`。
4. 建立 skip link、sidebar、topbar、content scroll owner、mobile nav 和 More drawer。
5. 建立 light/dark/system 主题控制和 localStorage 持久化。
6. 创建 12 区域导航，Operations 四项分组显示。

验证：入口 HTTP 200、控制台无错误、键盘可进入主内容、所有导航项可达。

### UI-02：共享语义层和组件

状态：**待实施**。

实现：

1. 用纯函数实现 formal PASS 判定。
2. 用纯函数实现进度显示规则，禁止假百分比。
3. 实现五轴矩阵和紧凑条。
4. 实现证据 expected/received/verified 账本。
5. 实现 gate、lease、communication、occupancy、permit、release checklist。
6. 实现 state banner、status badge、data table、timeline、empty/error/no-permission。
7. 实现 `node_observed_*` 与 Linux verdict 分栏。
8. 所有图标使用本地内联 SVG，不使用 emoji。

验证：semantic 单元检查覆盖正式 PASS 正反例、释放正反例、OFFLINE 组合、UNKNOWN 和 evidence 组合。

### UI-03：Mission Control 和 Intake

状态：**待实施**。

实现路由：MC-01、IN-01..03。

重点：Mission Control 克制显示异常和决策；Intake 展示三入口、来源、冲突、缺口和修订种子。

验证：J1 前半段可点击；blocked/stale/offline/reconciling/unknown-progress/partial-evidence fixture 可切换。

### UI-04：Tasks、Revision、Approval 和 Gates

状态：**待实施**。

实现路由：TK-01..09。

重点：任务列表、8 子视图、不可变 Revision、范围差异、审批、G0–G7、Plan/Cases、Live、Knowledge。

验证：任务子视图可深链；旧修订只读；审批和冻结写操作明确标 mock；禁止静默成功。

### UI-05：Runs、Evidence、Verdict 和 Reports

状态：**待实施**。

实现路由：RN-01..03、EV-01..03、RP-01..02。

重点：run/attempt 矩阵、mode 分离、分母资格、STOP、离线对账、证据账本、Linux 判定、报告版本。

验证：J2、J3、J4 全链路可导航；业务 PASS + 部分证据仍不可正式 PASS。

### UI-06：Devices、Knowledge 和 Operations

状态：**待实施**。

实现路由：DV-01..03、KN-01..03、RT-01..02、AG-01..03、AU-01..03、ST-01..04。

重点：设备和节点四信号、释放前置、隔离/排空；知识候选；runtime/agent 只读候选；审计恢复；设置和权限。

验证：RT/AG 写操作禁用并显示“待裁决”；设置不显示敏感数据；危险动作二次确认。

### UI-07：响应式、主题和可访问性

状态：**待实施**。

实现四档：

- ≥1200：完整固定侧栏。
- 1024–1199：紧凑 rail。
- 768–1023：rail + overlay drawer，详情单列。
- <768：底部五项 + More。

同时实现：

- 浅色、深色和系统主题。
- `prefers-reduced-motion`。
- `forced-colors` 基础兼容。
- `:focus-visible`。
- 抽屉/弹层焦点进入与归还。
- Esc 关闭，方向键切换任务子视图。
- 200% zoom 不裁切五轴、证据和释放清单。
- 手机触控目标至少 44×44。

### UI-08：确定性和静态验证

状态：**待实施**。

必须验证：

1. 39 路由精确、唯一、全部可达。
2. 12 区域计数正确。
3. 无外部 URL、CDN、远程字体、fetch、框架依赖和固定私网地址。
4. 无未定义 CSS 变量。
5. 无彩色边条和卡片强调描边。
6. 无 emoji 图标。
7. JS 语法通过。
8. 每个页面 HTTP 200。
9. 所有 fixture 有 metadata。
10. 所有页面保留候选声明。
11. Demo 目录与基线一致。
12. `git diff --check` 通过。

### UI-09：真实浏览器 QA

状态：**待实施**。

在最后一次源代码修改后生成全新证据。最低矩阵：

| 维度 | 覆盖 |
|---|---|
| 页面 | 39 路由全部打开；四条关键旅程重点点击 |
| 桌面 | 1440×900，light + dark |
| 平板 | 1024×768 和 768×1024 |
| 手机 | 390×844，light + dark |
| 滚动 | 所有可滚动页面顶部和底部 |
| 交互 | 路由、任务 tabs、主题、drawer、More、dialog、fixture 切换 |
| 键盘 | Tab、Shift+Tab、Enter、Space、Esc、左右方向键 |
| 状态 | offline、stale、blocked、partial、reconciling、unknown、no-permission |
| 动效 | normal + reduced motion |
| 控制台 | error 和 warning 清零或逐项解释 |

截图和 QA JSON 建议写入 `design/ui-app/evidence/`，文件名包含路由 ID、视口、主题和状态，例如：

```text
MC-01__desktop-1440__light__offline.png
TK-07__phone-390__dark__partial-evidence.png
```

### UI-10：独立视觉评审和修复循环

状态：**待实施**。

需要两个独立只读评审：

- Pass A：设计系统真实度、功能、状态、键盘、动效、可访问性。
- Pass B：布局、层级、字体、CJK 断行、触控、浅深色和视觉一致性。

任一页面失败即整体 NEEDS WORK。修复源代码后必须重新截图并重新评审，不能用旧截图通过。

### UI-11：LAN 评审和冻结准备

状态：**待实施**。

完整 UI 建议使用独立端口 8100，保留 8099 给三方向 Demo：

```bash
python3 -m http.server 8100 --bind 0.0.0.0 -d design/ui-app
```

验证本机和局域网 HTTP 200 后，只在对话中提供：

```text
http://<LAN-IP>:8100/
```

不要把真实 LAN IP 写入仓库文件。

用户评审后：

1. 收集问题和决策。
2. 修复并重跑完整 QA。
3. 形成版本号、变更记录、评审包和归档。
4. 只有用户明确批准后才更新 P1-01..P1-08 和 UI 冻结状态。

---

## 12. 当前任务状态总表

| 编号 | 工作 | 状态 | 产物/证据 | 下一步 |
|---|---|---|---|---|
| UI-00A | 事实源和需求核对 | 完成 | 本文件第 3 节；`1.md`；UI 候选规范 | 保持 |
| UI-00B | Cloudline 方向选择 | 完成 | 所有者明确选择；`plan.md` 已记录 | 保持 |
| UI-00C | 保留其他 Demo | 完成（文件存在） | `design/ui-demos/` 11 个文件 | 后续做哈希/HTTP 回归 |
| UI-00D | 39 路由 manifest | 完成并验证 | `design/ui-app/routes.json` | 不得随意增删 |
| UI-00E | Cloudline 设计合同 | 完成 | `design/ui-app/DESIGN.md` | 页面实现必须遵守 |
| UI-01 | 静态 Shell | 完成 | `index.html`、`favicon.svg`、`README.md`、`styles/*`、`src/app.js`、`src/router.js`、`src/shell.js` | 保持 |
| UI-02 | 共享语义和组件 | 完成 | `src/semantics.js`、`src/components.js`、`src/icons.js`、`src/fixtures.js` | 保持 |
| UI-03 | Mission + Intake | 完成 | `src/pages/mission.js`、`src/pages/intake.js` | 保持 |
| UI-04 | Tasks + Approval | 完成 | `src/pages/tasks.js`（8 子视图、G0–G7、审批） | 保持 |
| UI-05 | Runs + Evidence + Verdict + Reports | 完成 | `src/pages/runs.js`、`evidence.js`、`reports.js` | 保持 |
| UI-06 | Devices + Knowledge + Operations | 完成 | `src/pages/devices.js`、`knowledge.js`、`runtime.js`、`agents.js`、`audit.js`、`settings.js` | 保持 |
| UI-07 | 响应式/主题/a11y | 完成（基础） | 1440/1199/1024/900/768/767/390 无横向溢出；浅深色、跳转链接、焦点、44px 触控 | 仍需独立视觉评审 |
| UI-08 | 静态验证 | 完成 | `checks/contract-check.mjs` 100/100；`checks/smoke-check.mjs` 248/248；`git diff --check` 干净 | 修改后重跑 |
| UI-09 | 浏览器 QA | 完成（本地 Chromium） | `design/ui-app/evidence/*.png`；39 路由全部渲染；控制台 0 error | 可复跑 |
| UI-10 | 独立视觉评审 | 未完成 | 截图已生成；当前 `poor` 档位模型无图像输入，无法做视觉签核 | 需具备视觉能力的评审者 |
| UI-11 | LAN 评审 | 完成（服务运行） | `python3 -m http.server 8100 --bind 0.0.0.0 -d design/ui-app`；LAN URL `http://10.11.63.42:8100/` | 等待用户评审 |
| UI-12 | 用户批准和冻结 | 未开始 | 无 | 不能自动完成 |

### 12.1 2026-10-29 候选实施证据

- 39 条规范路由全部由 `route-manifest.js` 注册并可深链；字面路由优先于参数路由（`/console/intake/new`、`/console/knowledge/candidates` 已验证）。
- 14 个 fixture 场景 FX-01、FX-02、FX-03、FX-04、FX-05、FX-06、FX-07、FX-08、FX-09、FX-10、FX-11E/L/X、FX-12 可切换；FX-12 是唯一正式 PASS 正例。
- 本地 Chromium 验证：39/39 路由有页面标题、无未登记路由；桌面、平板、手机无横向溢出；移动底栏与抽屉可用；场景切换、主题切换、危险动作确认框、mock 反馈均正常。
- 对比度：正文 9.2:1、caption 6.35:1、激活导航 5.74:1、attention 徽章 5.25:1、danger 徽章 5.72:1（亮色）；深色模式全部不低于 6.6:1。
- 视觉关键页截图：`design/ui-app/evidence/{mc-light-1440,mc-dark-1440,mc-mobile-390,task-overview-1440,intake-new-1440,run-offline-1440,verdict-formal-pass-1440,device-release-1440,knowledge-candidates-1440,settings-access-1440}.png`。
- 未完成边界：没有独立视觉评审签核，没有所有者批准，没有 UI 冻结；所有写操作仍为 mock；RT/AG 写入仍等待 Q-09。

---

## 13. 文件所有权和并行规则

为避免多进程覆盖，按目录/文件划分：

| 工作单元 | 可写范围 | 禁止 |
|---|---|---|
| Shell 进程 | `design/ui-app/index.html`、`README.md`、`styles/*`、`src/app.js`、`src/router.js`、`src/shell.js` | 不改 Demo，不改规范文档 |
| 语义组件进程 | `src/semantics.js`、`src/components.js`、`src/icons.js`、`src/fixtures.js`、checks | 不改路由清单和页面模块 |
| 页面进程 | 指定的 `src/pages/<family>.js` | 不并行改共享组件；发现缺 primitive 先登记 |
| QA 进程 | 只写 `design/ui-app/evidence/` 和 QA 报告 | 不改产品源代码 |
| 修复进程 | 根据 QA 指定的最小源文件 | 一次只修一类问题，修后重跑相关证据 |

共享文件 `styles/components.css` 和 `src/components.js` 同一时间只能有一个写入者。

推荐执行顺序：

```text
Shell → Semantic/Components → Mission/Intake → Tasks → Runs/Evidence/Verdict/Reports
→ Devices/Knowledge/Operations → Responsive/A11y → Static QA → Browser QA
→ Independent review → Fix loop → LAN review → Owner approval/freeze
```

---

## 14. 每批接手报告格式

每个进程完成一个批次后，必须报告：

```text
批次：UI-XX
状态：PASS / NEEDS-FIX / BLOCKED
修改文件：精确路径列表
实现范围：本批实际覆盖内容
未实现：明确列出
验证命令：实际运行的命令
验证结果：退出码和关键数据
浏览器证据：截图/JSON 路径；未运行则写“未运行”
阻塞：需要谁提供什么
边界：是否仍为 CANDIDATE / NOT FROZEN
```

进度同步位置：

- 本文件第 12 节状态表。
- 根目录 `plan.md`，追加当前事实，不重写历史。
- `docs/delivery/construction-progress.md`。
- `.omo/ulw-execute/ledger.jsonl`，仅追加有效 JSON 行。

---

## 15. QA 通过条件

静态和浏览器 QA 必须同时满足：

### 15.1 功能和语义

- 39 条路由全部可导航。
- 四条用户旅程全部可点击完成。
- 五轴始终独立。
- received 始终不等于 verified。
- OFFLINE 始终不改写为 stopped/idle/free。
- release 始终不改写为 PASS。
- formal PASS 只有一个精确正例。
- unknown progress 不显示假百分比。
- RT/AG 写入在未裁决时禁用并解释原因。

### 15.2 视觉和布局

- Cloudline 视觉统一，不混入 Precision/Focus 外壳。
- 一屏一个明确主标题和一个主动作。
- 侧栏、顶栏、主滚动区职责明确，无嵌套同向滚动。
- 不使用彩色边条、卡片强调描边、装饰渐变、玻璃拟态或 emoji 图标。
- 浅色和深色均无不可读文本、发光白资产或错误状态色。
- 中文无裁字、孤字和不自然断行。

### 15.3 响应式和可访问性

- 1440、1024、768、390 宽度无主内容横向溢出。
- 手机保留关键状态和导航，不把五轴压成不可读五列。
- 每个可交互元素有可见 focus。
- 键盘顺序等于阅读顺序。
- 弹层和抽屉焦点正确进入和归还。
- reduced motion 不影响功能。
- 200% 缩放不丢失五轴、证据和释放前置。

### 15.4 运行和安全

- 所有运行资源为相对本地路径。
- 无 CDN、外部字体、远程 API、固定 IP、凭据或私钥模式。
- 无 JS 控制台 error。
- 页面资源全部 HTTP 200。
- Demo 目录仍可运行且未被完整 UI 覆盖。

---

## 16. 风险、停止条件和回滚

### 16.1 主要风险

| 风险 | 触发迹象 | 处理 |
|---|---|---|
| 39 页一次性大任务超时 | 长时间无文件落盘 | 拆成 UI-01..UI-06 小批次，每批先写骨架 |
| 多进程覆盖共享组件 | 同时改 components/styles | 串行共享文件，页面按 family 分工 |
| 旧原型污染当前结构 | 出现 15 路由或横向主导航 | 停止并以 routes.json/IA 重做 |
| 状态语义被折叠 | 单一“成功”徽标 | 阻断合并，恢复五轴和独立信号 |
| mock 被误认为真实状态 | 缺 candidate ribbon 或 authoritative 标签 | 立即停止，补边界后才继续 |
| 视觉好看但无浏览器证据 | 只有代码/静态截图 | 不得 PASS，运行完整 QA |
| 真实地址或凭据进入文件 | 扫描命中 | 立即停止、移除、复核，不提交 |

### 16.2 强制停止条件

出现以下任一情况，进程必须停止写入并报告：

- 规范源之间出现影响字段/枚举/权限的真实冲突。
- 需要决定 P2-05 生产框架才能继续，但当前只是 Phase 1 原型。
- 需要真实后端/设备/凭据才能展示页面。
- 发现 Demo 目录被意外删除或覆盖。
- 发现敏感信息进入 UI、fixture、证据或日志。
- 无法保持 Linux 权威和 Windows facts-only 边界。

### 16.3 回滚方法

- 不使用 `git reset --hard`、`git checkout --` 或其他破坏性命令。
- 只撤回本进程明确创建的最小文件或补丁。
- 不回退其他用户/代理的现有改动。
- 页面批次失败时保留已通过的共享 Shell 和语义组件，仅隔离失败 family。
- QA 证据和产品源分开，错误截图可删除重拍，不修改产品来迎合错误捕获。

---

## 17. 冻结边界

当前可以说：

- Cloudline 已被选为主方向。
- 三方向 Demo 文件存在且未被覆盖。
- UI 候选规范 4/4 通过文档锚点复核。
- 39 路由 manifest 已完成并验证。
- Cloudline DESIGN.md 已完成。
- `design/ui-app/` 已实现候选 UI，39/39 路由可深链渲染。
- 确定性检查通过：contract 100/100、smoke 248/248。
- 本地 Chromium QA 通过：控制台 0 error、四档视口无横向溢出、关键交互和截图已落盘。

当前不能说：

- 独立视觉评审已通过，或可访问性认证通过。
- UI 已冻结，或所有者已批准。
- P1-01..P1-08 已完成。
- 后端、API、数据库或 Node Agent 已接通。
- mock 数据是平台真实状态。
- 写操作已产生真实服务端效果。
- 浏览器 QA 已覆盖真实后端或真实设备执行。

Phase 1 UI 只有同时满足以下条件才可进入冻结评审：

1. 完整可运行原型存在。
2. 39 路由和四旅程可操作。
3. 所有语义边界正确。
4. 响应式、主题、键盘和 reduced motion 完成。
5. 静态检查和真实浏览器 QA 全部有新鲜证据。
6. 独立视觉评审无 blocker。
7. 用户完成评审并明确批准。
8. 版本、变更记录和归档完成。

---

## 18. 其他进程现在应做的第一件事

候选 UI 已实现，不要重新从 UI-01 开始。当前入口是评审与冻结前修复：

1. 打开 `http://10.11.63.42:8100/`（或本机 `http://127.0.0.1:8100/`），按 12 区域逐页检查视觉、密度和文案。
2. 用顶栏“状态预览”切换 FX-01..FX-12，重点检查 FX-04 离线四信号、FX-05 待 STOP 对账、FX-07 部分证据、FX-10 无权限、FX-12 唯一正式 PASS。
3. 使用具备图像输入能力的评审者，对 `design/ui-app/evidence/` 的新鲜截图做独立视觉评审；当前 `poor` 档位模型不能读取图像，不能替代该步骤。
4. 只修 blocker 或明确缺陷；修改后重跑：

```bash
cd /home/bszheng/NoahsArk/design/ui-app
node checks/contract-check.mjs
node checks/smoke-check.mjs
git diff --check
```

5. 若评审通过，由所有者明确批准后再进入 P1-08 冻结和归档；在此之前保持 `CANDIDATE UI / PROTOTYPE / NOT FROZEN / MOCK DATA`。

服务命令：

```bash
python3 -m http.server 8100 --bind 0.0.0.0 -d design/ui-app
```

---

## 19. 最终交接摘要

当前 UI 工作已从设计进入可评审候选实现：

- 需求、IA、设计系统、屏幕规格和 Cloudline 方向已明确。
- 三方向比较 Demo 已存在，Cloudline 已被选中，其他两个保留。
- 完整 UI 的 39 路由清单和 DESIGN.md 已落盘。
- `design/ui-app/` 已实现 12 区域、39 路由、8 个子视图、14 个状态 fixture、响应式、浅深色和本地 QA。
- 尚未完成独立视觉评审、所有者批准和 UI 冻结；不得把候选实现写成验收或冻结结论。
- 接手进程应先评审 8100 页面，再按 blocker 做最小修复，最后交给所有者决定是否冻结。

本文件是当前 UI 设计和实施的集中交接入口。若本文件与后续已批准决策冲突，应更新本文件并记录变更，不要让多个进程各自维护不同口径。
