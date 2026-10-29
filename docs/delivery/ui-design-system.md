# NoahsArk UI Design System（Quiet Instrument）

> 状态：Phase 1 设计系统候选稿（decision draft），供评审与实现准备；**未冻结、未获实施批准**。
> 依据：`docs/v2/UI-DESIGN-APPLE.md` §1–§4、`design/apple/design-tokens.json`、`docs/delivery/ui-baseline-gap-analysis.md` §5–§9、`docs/delivery/ui-information-architecture.md`、`docs/contracts/domain.md` §7/§9/§11/§14/§15、`docs/contracts/ui-report-knowledge-audit.md` §2。
> 边界：本文只定义视觉与组件契约，不定义接口、不改代码。**未做浏览器/图像 QA，不声明视觉冻结、WCAG AA 认证、性能或深色模式已验证**；深色令牌为候选，采用前须复测对比度并取得决策。状态枚举以 `docs/contracts/domain.md` 为准，UI 不得发明同义值。
> 枚举核对：本文所有权威值已逐条对照 `domain.md` §7（Gate）、§9.1（五轴）、§11（Lease/Device/Node）、§14（正式 PASS）、§15（断线/STOP-first/释放）、`evidence-verdict.md` §5（manifest）、§9.1（证据项状态机）、`ui-report-knowledge-audit.md` §2.7（投影映射）。**投影词汇（如 `LIVE/DEGRADED`、`PASS/FAIL/PENDING`、`NOT_APPLICABLE`）只是展示层派生值，必须由服务端生成，UI 不得自行映射或扩展。**

## 1. Apple-inspired 原则

| 原则 | 落地规则 |
| --- | --- |
| Clarity | 每页一个 `h1`；标题 56/40/32px 三级；表格首列是任务或对象名。 |
| Deference | 顶栏、导航、卡片后退为白/灰表面；无背景大图、无装饰插画。 |
| Depth（克制） | 默认卡片无阴影，靠白面 + 1px 发丝线分层；仅分段控件选中、弹层、Toast、滚动后顶栏使用阴影。 |
| Typographic hierarchy | 最多两个字族（系统无衬线 + 等宽）；字号差拉开，不靠加粗堆层级。 |
| Generous whitespace | 8pt 间距；桌面内容最大 1160px，上 48px、侧 40px；卡片 26px 内边距。 |
| One accent | 唯一强调蓝只用于主按钮、焦点、进度与进行中；链接用更深的 `accent ink`。 |
| Material, not decoration | 半透明材质只用于“始终可见的导航”，不铺卡片、不铺整页。 |
| Direct labeling | 状态徽标始终带文字；图标按钮必须有 `aria-label`；危险动作写结果动词。 |

明确拒绝：营销式大图 hero、玻璃拟态铺满、彩虹渐变与彩色边条、彩色描边卡片、加载 SF Pro 字体文件、复制 Apple 导航结构、用循环动画制造“高级感”、把“预检通过”做成绿色成功页。

## 2. 语义令牌：浅色 / 深色（预留）

CSS 前缀 `--naa`。深色列仅作为语义层预留，实现时必须经 `prefers-color-scheme` 分支独立赋值，**禁止用 filter 反色或简单交换黑白伪造**。

| 语义 | 浅色 | 深色（预留） |
| --- | --- | --- |
| surface.canvas | `#F5F5F7` | `#0B0B0D` |
| surface.raised | `#FFFFFF` | `#1C1C1E` |
| surface.subtle | `#FBFBFD` | `#161618` |
| surface.sunken | `#EDEDF0` | `#2C2C2E` |
| surface.inverse | `#1D1D1F` | `#F5F5F7` |
| border.hairline | `rgba(0,0,0,0.07)` | `rgba(255,255,255,0.10)` |
| border.strong | `rgba(0,0,0,0.13)` | `rgba(255,255,255,0.18)` |
| border.hover | `rgba(0,0,0,0.22)` | `rgba(255,255,255,0.28)` |
| text.primary | `#1D1D1F` | `#F5F5F7` |
| text.secondary | `#424245` | `#C7C7CC` |
| text.tertiary | `#5F5F64` | `#A1A1A6` |
| text.quaternary | `#6E6E73` | `#8E8E93` |
| text.link | `#0066CC` | `#409CFF` |
| accent.base | `#0071E3` | `#0A84FF` |
| accent.hover / pressed | `#0077ED` / `#0068D1` | `#409CFF` / `#0071E3` |
| accent.soft | `rgba(0,113,227,0.09)` | `rgba(10,132,255,0.16)` |
| status.ok | `#1A7F45` | `#4CC38A` |
| status.warn | `#9A6400` | `#FFB340` |
| status.danger | `#C4312A` | `#FF6B66` |
| status.neutral / stale | `#6E6E73` | `#8E8E93` |
| status.disputed | `#8A5A00` | `#D9A441` |
| status.okInk / warnInk / dangerInk | `#14663A` / `#7D4A00` / `#A82721` | 同名前缀取明亮状态色本身（`#4CC38A` / `#FFB340` / `#FF6B66`），深色药丸底上不再压暗 |
| status.okSoft / warnSoft / dangerSoft | `rgba(26,127,69,.09)` / `rgba(200,132,0,.11)` / `rgba(196,49,42,.09)` | `rgba(76,195,138,.16)` / `rgba(255,179,64,.16)` / `rgba(255,107,102,.16)` |
| gate.pass / fail | `#1A7F45` / `#C4312A` | `#4CC38A` / `#FF6B66` |
| gate.pending / blocked | `#C7C7CC` / `#9A6400` | `#48484A` / `#FFB340` |
| gate.notApplicable | `#E1E1E6` | `surface.sunken`（`#2C2C2E`） |
| border.focus | `#0071E3` | `#0A84FF` |
| overlay.scrim | `rgba(0,0,0,.30)` | `rgba(0,0,0,.55)` |
| terminal.background / raised | `#1D1D1F` / `#2C2C2E` | `#000000` / `#1C1C1E` |
| terminal.text / dim / role / ok / warn / danger | `#F5F5F7` / `#86868B` / `#64D2FF` / `#7DD3A0` / `#FFB340` / `#FF7A7A` | 同左（终端不反转） |

规则：颜色永不是唯一信息；同一颜色只表达一类含义（蓝=可交互/进行中，绿=仅表示“已通过/已验签”，琥珀=等待/漂移/阻断，红=失败/危险）；卡片、行、导航不使用彩色侧边条。`*Soft` 只作底色，不能直接当文字色；落在 `*Soft` 上的文字必须用对应 `*Ink`（浅色）或明亮状态色（深色）。`gate.pending`（`#C7C7CC`）与 `gate.notApplicable`（`#E1E1E6`）只作填充/边框，**不得作为文字色**（对比度不足），其印章文字使用 `text.secondary`。深色下状态色必须重新做对比度测量，不得沿用浅色值直接反转；终端在两种主题下都保持深色。

## 3. 排版：系统字体、CJK、等宽

- 无衬线：`-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", "Microsoft YaHei UI", sans-serif`；不加载外部字体。
- 等宽：`SFMono-Regular, Cascadia Mono, Cascadia Code, Consolas, "Microsoft YaHei UI", monospace`；用于 ID、哈希、时间戳、终端、证据键。
- 字距：标题 `-0.035em`，小标题 `-0.02em`，正文 `-0.006em`，眉题 `+0.07em`。

| 令牌 | 尺寸 | 行高 | 用途 |
| --- | --- | --- | --- |
| display | 56 / 40 / 32px | 1.04 | 桌面 / 平板 / 手机页面标题 |
| hero | 46 / 32px | 1.15 | 总览陈述句 |
| taskTitle | 38 / 26px | 1.15 | 任务详情标题 |
| h2 | 28px | 1.15 | 分区标题 |
| cardTitle | 16px | 1.40 | 卡片标题 |
| body | 14px | 1.55 | 正文 |
| bodySmall | 13px | 1.55 | 密集表格正文 |
| caption | 12.5px | 1.40 | 说明文字 |
| eyebrow / micro | 11px | 1.40 | 眉题、表格表头、徽标 |

CJK 规则：始终使用系统字体渲染，不加载外部字体；中文标题不使用负字距（仅英文大标题用 `-0.035em`），行高 ≥1.3，避免裁切中文降部；长 ID、哈希、英文模型名用 `overflow-wrap:anywhere` 兜底；说明文字 64–66 字符宽，正文段落不超过 75 字符；手机端任务表转卡片，避免中文列被挤压。等宽仅用于 ID、哈希、时间戳、终端与证据键，并与中文混排时统一 `font-variant-numeric: tabular-nums`，时间与计数右对齐。中文断行使用 `line-break: strict` + `word-break: normal`；`overflow-wrap:anywhere` 是逐元素例外，不得全局 `word-break: break-all`。中文与拉丁/数字之间保留自然间距，不手动插入空格字符；全角标点不参与负字距。

## 4. 间距、圆角、阴影、动效

- 表面：`surface.canvas` 只作页面底；`raised` 承载卡片、表格与任务头；`subtle` 用于状态条、hover 与轻量分区；`sunken` 用于轨道、开关关闭态；`inverse` 用于终端与深色胶囊。默认卡片无阴影，仅靠表面差与 1px 发丝线分层。
- 间距 8pt 基准，允许 4px 半档：`4 / 8 / 12 / 16 / 24 / 32 / 40 / 48 / 64 / 80`；卡片 26px、紧凑卡片 20px、移动端 20/16px。
- 圆角：尺度 `10 / 14 / 18 / 22 / 28 / 999px`；组件令牌另行固定：卡片 22px（`card.radius`）、任务头与总览 28px、输入 12px（`input.radius`）、终端 18px、移动端卡片 18px、按钮与徽标 pill。组件令牌不得用任意新值替代；新增圆角必须先登记到 `design/apple/design-tokens.json`。
- 阴影：默认 `none`；分段控件选中 `0 1px 3px rgba(0,0,0,.09)`；滚动后顶栏 `0 10px 30px rgba(0,0,0,.06)`；Toast `0 12px 40px rgba(0,0,0,.22)`；弹层 `0 30px 90px rgba(0,0,0,.24)`。
- 动效：140ms（hover/按压）、220ms（页签/开关）、320ms（页面进入），统一 `cubic-bezier(.25,.1,.25,1)`；只动 `transform / opacity / filter`。禁止弹跳、循环漂浮、视差、滚动劫持。
- 所有颜色、字号、间距、圆角、阴影必须引用令牌；组件内不得出现裸十六进制、任意 px 或“先写死再补令牌”。缺令牌时先扩展 `design/apple/design-tokens.json` 与本文，再使用。

## 5. 状态语言：文本、形状、颜色三通道

状态必须同时具备 **文本 + 形状/图标 + 颜色** 三个通道，颜色只作第三通道。实现使用内联 Lucide SVG，不使用 emoji；紧凑视图也不能只留色点。图标默认 `aria-hidden="true"`，可见文本承担语义。

| 语义 | 形状/边框 | 图标（Lucide） | 必显文本 | 颜色令牌 |
| --- | --- | --- | --- | --- |
| pass | 实心胶囊 | `check` | PASS / PASSED | ok |
| executed | 中性外框 | `circle-check`（中性描边，不是绿色实心） | COMPLETED / 已执行（未判定） | neutral |
| fail | 实心胶囊 | `x` | FAIL / FAILED / CONFLICTED | danger |
| attention | 实心胶囊 | `triangle-alert` | WARN / BLOCKED / DRAINING / INCOMPLETE / NEEDS_REVIEW | warn |
| expected | 中性外框 | `flag` | EXPECTED / 预期内（语义待产品确认） | neutral |
| running | 实心胶囊 | `play` | RUNNING / IN PROGRESS | accent |
| pending | 虚线胶囊 | `circle-dashed` | PENDING | neutral |
| not-run | 虚线胶囊 | `circle-minus` | NOT RUN / NOT EVALUATED / SKIPPED / N/A | neutral |
| released | 中性外框 | `archive` | RELEASED / CLOSED / ARCHIVED | neutral |
| unknown | 点线胶囊 | `circle-help` | UNKNOWN / 尚未读取 | neutral |
| stale | 虚线边框 + 时钟 | `clock` | STALE / 陈旧 | neutral |
| offline | 斜线边框 + 断连 | `wifi-off` | OFFLINE | neutral |
| quarantined | 外框 + 警示盾 | `shield-alert` | QUARANTINED | danger |
| reconciling | 外框 + 循环 | `refresh-cw` | RECONCILING | accent |
| no-access | 外框 + 锁 | `lock` | NO ACCESS / 无权限 | neutral |

- 状态文本必须来自权威枚举或明确投影；未知枚举显示 `UNKNOWN`，不得猜成 PASS。`aria-label` 必须包含完整状态，禁止只播报“红色/绿色”。
- 同一屏不得用两种颜色表达同一语义；`*Soft` 只作底色，文字用 `*Ink`。绿色**只**属于 `pass` 家族；`executed`（COMPLETED）、`expected`（EXPECTED）、`released`（RELEASED/CLOSED/ARCHIVED）、`not-run`（SKIPPED/N/A）一律中性，避免被读成“通过”。
- `STALE` 始终附最后权威更新时间与陈旧原因；陈旧阈值由服务端从配置解析后下发，**UI 不得硬编码秒数**。`OFFLINE` 始终附最后已知活动时间；二者都不得改写成“已停止 / 空闲 / 可重派”，也不得把 `OFFLINE` 映射为 `IDLE`/`FREE`。

### 5.1 禁止等价与禁改写

任何屏幕、报告、导出、Toast 与 `aria-label` 都不得把下列事实互相替代。UI 只显示权威值，不存在“语义等价”的捷径。

| 真实事实 | 禁止写成 | 原因 / 权威依据 |
| --- | --- | --- |
| 设备已释放（`RELEASED`，三项前置全真） | PASS / 通过 / 已完成 | 释放只表示占用归还，与业务判定无关（domain §15.4、I-10） |
| 节点通信 `OFFLINE` | 设备空闲 / `IDLE` / 可重派 / 已停止 | 通信只表示可见性（L-2、D-3、domain §15.1–15.2） |
| 证据 `received`（已传输） | `verified`（已核验）/ 证据完整 | 只有 verified 才计入“必需证据已存在”（evidence-verdict §9.1） |
| `execution_status=COMPLETED` | PASS / 通过 | 执行结束不等于判定（domain §9.1） |
| 节点回执 `receipt` | 平台判定 / 五轴结论 | 回执只含事实，不含最终判定（I-12、domain §12） |
| `SKIPPED` / `NOT_APPLICABLE` | PASS | 跳过不是通过；G1/G5/G6 不得跳过（domain §7.2） |
| 知识候选 `PROPOSED/UNDER_REVIEW` | 已推广 / 已验证 | 候选状态不等于知识条目（ui-report §4） |
| 证据已归档 / `archive.state=verified` | 证据已核验 / 判定通过 | 归档状态独立于判定（evidence-verdict §5.2） |
| 进度 `percent` 未知 | 0% / 99% / 即将完成 / 阶段序号 n/11 | 未知总量必须显示“未知”（ui-report §2.4） |
| 烟测 / 模拟 / 回放样本 | 正式样本 / 正式分母 | 永不进入正式分母（I-07、G-3） |

实现约束：任何徽标或文案必须从语义令牌到权威值一一映射；缺映射一律 fail-closed 为 `UNKNOWN`，不得回退到旧卡片或猜测为正常状态。

### 5.2 五轴判定可视化

固定顺序：`execution_status` → `validity_status` → `business_verdict` → `evidence_status` → `verification_status`。禁止折叠为单一徽章或单一布尔值。

| 顺序 | 轴 | 中文短标签 | 权威值 → 视觉家族（文本保留原值） |
| --- | --- | --- | --- |
| 1 | execution_status | 执行 | `NOT_STARTED`→pending；`RUNNING`→running；`COMPLETED`→executed（中性“已执行”，**不得绿**）；`ABORTED`→attention；`SKIPPED`→not-run |
| 2 | validity_status | 有效 | `VALID`→pass；`INVALID`→fail；`BLOCKED`→attention；`UNKNOWN`→unknown |
| 3 | business_verdict | 结论 | `PASS`→pass；`FAIL`→fail；`EXPECTED`→expected（中性，不绿）；`WARN`/`NEEDS_REVIEW`→attention；`NOT_EVALUATED`→not-run |
| 4 | evidence_status | 证据 | `COMPLETE`→pass；`INCOMPLETE`→attention；`CONFLICTED`→fail；`UNVERIFIED`→unknown |
| 5 | verification_status | 复核 | `PASS`→pass；`FAIL`→fail；`NOT_RUN`→not-run |

- **完整矩阵**：语义 `<table>`，带 `caption`（含 run/attempt ID 与 `case_version`）、`th scope`；每行一个轴，值格显示图标 + 权威值 + 中文含义；页脚注明“来源：Linux 控制面”。
- **紧凑条**：固定顺序五格，每格图标 + 短值，触控 ≥44px，可换成两行；`aria-label` 如“执行 COMPLETED，有效 VALID，结论 PASS，证据 INCOMPLETE，复核 NOT_RUN”。不得把未加载的轴留空，应显示 `UNKNOWN / 尚未读取`。
- **总体结论**：只有五轴同时为 `COMPLETED / VALID / PASS / COMPLETE / PASS` 时才显示绿色“正式 PASS”。否则显示“不可正式 PASS”并给出首个阻断原因与跳转。`business_verdict=PASS` 且 `evidence_status=INCOMPLETE` 时，必须写成“业务 PASS · 证据不完整 · 不可正式 PASS”，不得出现绿色通过。
- **单轴绿色不等于整体通过**：`execution_status=COMPLETED` 只证明执行结束，`validity_status=VALID` 只证明输入有效，`business_verdict=PASS` 只证明业务断言通过；三者任一单独出现都不得触发页面级绿色或“已完成”。五轴中任一项为 `UNKNOWN/尚未读取` 且无其他阻断时，总体显示“尚未读取”，不得显示“即将通过”。
- `UNKNOWN` 只表示“尚未读取/未加载”的投影占位；`evidence_status` 不得以 `UNKNOWN` 写入 verdict axes：未核验写 `UNVERIFIED`，缺失写 `INCOMPLETE`，冲突写 `CONFLICTED`。执行完成、节点回执、设备释放都不是 PASS。

### 5.3 门禁：G0–G7 八枚瓦片

| 门禁 | 名称 | 主要落点 |
| --- | --- | --- |
| G0 | 受理审阅 | IN-02 / IN-03 |
| G1 | 冻结批准 | TK-03 |
| G2 | 静态检查 | TK-05 / RT-02 |
| G3 | 资源资格与租约 | DV-01 / DV-02 |
| G4 | 真机烟测 | TK-05 / RN-02 |
| G5 | 正式采样 | TK-05 / RN-02 |
| G6 | 证据复核与判定 | TK-06 / TK-07 / EV-03 |
| G7 | 报告/知识 | RP-02 / TK-09 / KN-03 |

- 权威状态只有 `PENDING / IN_PROGRESS / PASSED / FAILED / BLOCKED / SKIPPED`；投影缺失时才显示 `UNKNOWN`。每枚瓦片 = 门禁代号 + 名称 + 图标 + 状态文本 + `blocker.owner`（阻塞时）+ `version`。
- **权威 → 展示映射**（由服务端投影，UI 不自造）：`PASSED→PASS`、`FAILED→FAIL`、`PENDING/IN_PROGRESS→PENDING`（`IN_PROGRESS` 加“进行中”文字）、`BLOCKED→BLOCKED`、`SKIPPED→NOT_APPLICABLE`（仅当权威显式记录不适用）、缺失→`UNKNOWN`。**门禁 `PASSED` ≠ 业务 `business_verdict=PASS`**，二者不得互相引用为证据。
- `PENDING` 不得提前显示 PASS；`SKIPPED` 必须有真人原因，且不得跳过 G1/G5/G6；`FAILED`/`BLOCKED` 停止推进，修复走新 revision 或新 run。瓦片底色/边框用 `gate.*`，但文字必须用 `text.primary/secondary`；`gate.pending` 不得当文字色。
- G4 必须链接独立 `mode=smoke` 的 run；烟测样本永不进入 G5 正式分母。瓦片支持 Enter/Space，手机 ≥44×44；禁止把旧 C1–C7 当作当前判定模型。

### 5.4 租约、占用与对账

- 同一区块并列展示四个独立信号，禁止合并成一个“设备状态”：lease `state`（`GRANTED / HELD / RELEASING / RECLAIM_PENDING / RELEASED / QUARANTINED`）、`communication_state`（`ONLINE / STALE / OFFLINE`）、`occupancy_state`（`IDLE / OCCUPIED / RELEASING`）、`execution_permit`（`GRANTED / NOT_GRANTED / SUSPENDED`），并显示 `lease_epoch`。

| 信号 | 权威值 → 视觉家族（文本保留原值） |
| --- | --- |
| lease `state` | `GRANTED`→中性外框“已授予”；`HELD`→accent 外框“已持有”；`RELEASING`→attention“释放中”；`RECLAIM_PENDING`→attention“回收待对账”；`RELEASED`→中性外框“已释放”（不绿）；`QUARANTINED`→danger“隔离中” |
| `communication_state` | `ONLINE`→accent 圆点“在线”（不用绿色）；`STALE`→warn“陈旧”+ 原因与最后权威更新；`OFFLINE`→中性 `wifi-off`“离线”+ 最后已知活动；缺失→`UNKNOWN` |
| `occupancy_state` | `IDLE`→中性“空闲（已确认释放）”；`OCCUPIED`→accent 实心“占用中”；`RELEASING`→attention“释放中”；**只有 `IDLE` 可显示空闲，`OFFLINE/STALE` 不得映射为 `IDLE`** |
| `execution_permit` | `GRANTED`→accent“允许执行”；`NOT_GRANTED`→中性“未授予”；`SUSPENDED`→attention“已暂停”；断线不自动变为 `NOT_GRANTED` |

- Devices & Nodes 高密集区另用一组设备/节点枚举，不得与 lease 四信号合并成单一“设备状态”徽标：

| 对象 | 权威枚举 → 视觉家族 |
| --- | --- |
| `Device.pool_state` | `DISCOVERED`→中性“已发现”（未就绪）；`READY`→中性“就绪”；`RESERVED`/`ATTACHED`→accent“已保留/已接入”（同时必须 `OCCUPIED`）；`DRAINING`→attention“排空中”（已有 run 继续）；`QUARANTINED`→danger“隔离中”；`OFFLINE`→中性“离线”（保持占用）；`RETIRED`→中性外框“已退役”（不是隔离） |
| `Device.health_state` | `HEALTHY`→中性；`DEGRADED`→attention；`UNHEALTHY`→danger；`UNKNOWN`→unknown。健康差**不等于**自动隔离，隔离只来自 `QUARANTINED` |
| `Node.status` | `ACTIVE`→中性；`DRAINING`→attention；`QUARANTINED`→danger；`RETIRED`→中性外框 |
| `Node.spool.state` | `NORMAL`→中性；`WARN`→attention（禁止启动新 case）；`PROTECT`→danger（本地安全停止并保全证据）；`BLOCKED`→danger |
| `Node.interactive_session.state` | `AVAILABLE`→中性；`UNAVAILABLE`/`LOCKED`→attention“无交互会话”（相关任务必须 `BLOCKED`，不得 Session 0 降级） |

- 释放清单三项逐项显示：`local_stop_confirmed`、`safe_cleanup_done`、`occupancy_reconciled`。三项全为 true 才能显示 `RELEASED`；缺 `cleanup_receipt` 时设备保持 `OCCUPIED`，但**不等于** `evidence_status=INCOMPLETE`。`expires_at` 只是续约截止，不是所有权到期。
- 断线组合必须显示“通信 OFFLINE · 执行 RUNNING · 设备 OCCUPIED · permit GRANTED · 最后已知时间”；禁止“已停止 / 设备空闲 / 可重派 / 完成百分比”。
- 对账中显示 `RECONCILING` + STOP-first 六步时间线：处理待送达 STOP → 停止后续动作 → 补传 → 去重 → 核对 run/device/lease/epoch/占用 → 恢复领取。未完成前禁止新派发；旧 epoch 只作历史事实。设备隔离 `QUARANTINED` 保持占用，必须人工恢复。

### 5.5 证据与判定

- manifest 头固定展示 `expected / received / verified` 三列，以及 `kind`、`size`、`collected_at`、`digest`、节点回执、`access_level`；按 case/device 分组，不用一个总文件数代替分母。三列分别取 `required_evidence`/`completeness.required_total`、`required_present`、`required_verified`；任一缺失显示“未知”，不得推算。`completeness.result` 只取 `COMPLETE / INCOMPLETE / CONFLICTED`，并展开 `required_missing`、`digest_failures`、`conflict_ids`。
- **证据项状态机**（逐项显示，不得只显示汇总）：`declared → uploading → partial → complete → verified`，旁支 `conflicted`（摘要/大小/关联不一致）、`unavailable`（源丢失/从未开始）、`quarantined`（上传异常/安全阻断）。`complete` 只表示字节完整，**不等于 `verified`**；只有 `verified` 计入“必需证据已存在”。`partial` 是进行中而不是失败。
- `received` 只表示已传输；`verified` 只表示 Linux 已完成摘要/manifest 校验。已接收 ≠ 已核验；未知写“未知”，不得写 0 或 99%。
- 证据状态只用 `COMPLETE / INCOMPLETE / CONFLICTED / UNVERIFIED`；部分上传显示 `INCOMPLETE`，不是失败。缺清理回执或 GB 级日志未归档是独立事实，不自动导致证据不完整或判定失败。
- 长哈希/长路径用等宽 + `overflow-wrap:anywhere` + 复制完整值；受限材料显示 `NO ACCESS` 与访问级别，不能伪装成“没有文件”。

### 5.6 TaskCard（任务卡）

- 必备字段：标题、短 `task_id` + 复制、当前 `R-<n>`、阶段、run mode 徽标（`static / smoke / formal`）、五轴紧凑条、阻塞方、资源三信号、证据三列摘要、资源四信号（lease/通信/占用/permit + `lease_epoch`）、最后权威更新与最后已知活动、进度。
- 进度只有三种合法模式：`COUNTS`（已批准分母，显示“已完成 / 总数”+ 度量名）、`QUALITATIVE`（有部分可信计数但总量未知，显示已知计数 + “未知”）、`INDETERMINATE`（无可靠计数，只显示阶段、门禁、状态）。`percent` 仅在 `COUNTS` 且 `denominator_kind ∈ {APPROVED_CASE_COUNT, APPROVED_EVIDENCE_ITEM_COUNT}`、`total > 0` 时按 `round(clamp(completed/total×100,0,100),1)` 生成；`percent_label` 必须写明“已完成用例占比”，不得写成“任务完成度”。
- `progress.percent=null` 时显示“未知”，不得用 0%、99%、“即将完成”或阶段序号冒充。任务卡是服务端投影，UI 不得自行推导状态或把烟测/模拟/回放计入正式分母。`freshness.is_stale=true` 时必须显示陈旧徽章 + `stale_reasons`，不得宣称“实时”；`last_authoritative_update` 与 `last_known_at` 必须分别显示，不得合并成一个“更新时间”。
- 每卡只有一个主操作；整体颜色不得早于五轴条件变绿。

## 6. 数据面组件

**基础组件**：按钮高 42px（小 36 / 超小 30，手机 ≥44），胶囊圆角；每页一个主按钮；人工裁决动作（批准/停止/释放）用墨黑填充，危险操作用白底红字红边；卡片 22px 圆角、26px 内边距、默认无阴影。徽标高 23px、11px/500，必须带文字。任务详情 8 个子视图用分段控件，选中为白胶囊 + `raised` 阴影，滚动吸顶，支持左右方向键。

**表格**：表头 11px/600/`text.quaternary` + 发丝下边线；`text.quaternary` 表头只可置于 `surface.raised/subtle/canvas`，不得置于 `surface.sunken`（`#EDEDF0` 上仅 4.34:1，低于 4.5:1）。行内边距 14px；hover `surface.subtle`；数字右对齐、等宽数字；无斑马纹；带 `caption` 与 `th scope`。窄屏不压缩列，外层容器内部横向滚动；仅任务列表在手机转卡片。密集矩阵在 200% 缩放下允许局部横向滚动，但不得裁切五轴、证据、释放结论。

**表单**：输入高 44px、圆角 12px、边线 `border.strong`；焦点环 `0 0 0 4px rgba(0,113,227,0.12)`；标签常显，不用 placeholder 代替标签；错误 = 文本 + 图标 + `aria-describedby`，不只变红；禁用动作配可见原因；危险操作二次确认并写结果动词。

**时间线**：用于审计、对账、STOP-first 重连。节点 = 时间（等宽）+ 事件类型 + 主体 + 结果；`before/after` 结构化 diff 必须同时给文本摘要与表格替代，不能只靠颜色；待送达 STOP、旧 epoch 事件用虚线连接并标注“历史事实，不改当前运行”。

**终端**：两种主题下都是深色面（`terminal.background`），圆角 18px，12px/1.75 等宽；角色 `role`、成功 `ok`、警告 `warn`、错误 `danger` 为独立令牌；颜色均配文字标签。必须提供“复制可见文本 / 下载日志”的文本替代，不能只给 ANSI 着色画面；不使用扫描线、闪烁光标或循环动画。

**弹层/Toast**：遮罩 `overlay.scrim` + 6px 背景模糊；弹层 28px 圆角、最大宽 560px、`role="dialog"` + `aria-modal`，打开焦点进入、关闭焦点归还；Toast 底部居中，成功/警告/错误只改图标色，文字仍说明结果。

## 7. 响应式与密度

断点与导航（回写 IA §3，覆盖旧“≥1024 横排导航”）：

- **≥1200px**：左侧固定导航——8 个主入口（含 Intake 流程入口）+ “Operations” 分组展开 4 个治理区域（Runtime & Toolchain、Agents & Reviews、Audit & Recovery、Settings & Access）；顶栏承载搜索/命令面板、新建任务、环境与连接状态、用户与角色；详情双列 + 右上下文栏、4 列指标。
- **1024–1199px**：左侧图标轨道（可展开标签），分组与顺序不变；详情保持主子视图同屏；侧边距 32px、导航标签 12.5px。
- **768–1023px**：图标轨道 + 覆盖式抽屉；详情单列、上下文区移到主内容下方、任务子视图 sticky tabs、2–3 列指标。
- **<768px**：底部 5 项（Mission Control / Tasks / Runs / Devices / More），More 打开 12 区域全量抽屉；任务详情 8 子视图横向滚动；任务表转卡片；所有按钮 ≥44px。

导航可访问性：`nav` 地标 + “跳到主内容”链接；当前区域用 `aria-current="page"`；抽屉、命令面板、全屏接管必须焦点进入与归还；Tab 顺序等于阅读顺序。路由、区域与子视图清单以 `docs/delivery/ui-information-architecture.md` 为准。

断点口径：IA 已固定上述四档；令牌文件目前只有 `≥1200 / 768–1199 / ≤767`，必须先登记 `layout.breakpoints.wideTablet = 1024px` 与 `layout.navRailWidth`（展开/图标两档）才能作为实现依据。未登记前以 IA §3 为准，组件不得写裸 `1024px` 或裸导航宽度。

主滚动区是唯一滚动所有者；左侧导航、顶栏、状态条和底部 Tab 固定，不随内容滚动。外壳高度：fixture 声明条 30px（仅 mock/契约 fixture，正式环境显示环境 ribbon）、ribbon 28/26px、顶栏 62/56px、导航项高 48px、底部 Tab 64px + 安全区；左侧导航宽度由 `layout.navRailWidth` 令牌给出，禁止组件写死。内容最大宽度 1160px；页面内边距桌面 `48px 40px 80px`、平板 `48px 28px 80px`、手机 `24px 20px 100px`（上/侧/下）。底部 100px 下留白用于避开底部 Tab 与 `env(safe-area-inset-bottom)`。

| 密度 | 区域 | 规则 |
| --- | --- | --- |
| 克制 | Mission Control、Intake、Task overview、Reports 默认、Settings | 一屏回答“健康吗 / 哪里需要我 / 下一步”；只放异常、待决断、离线/对账/隔离 |
| 中等 | Tasks 列表、Knowledge、Agents & Reviews | 默认列 + 列设置；详情走抽屉或子页 |
| 高密集 | Plan & Cases、Runs & Attempts、Evidence、Devices & Nodes、Runtime、Audit & Recovery | 矩阵 + 筛选 + 分组 + 行详情；关键安全事实不得藏到二级页 |

克制不等于省略安全事实：Mission Control 可以少放图，但“离线仍占用 / 待 STOP / 证据不完整 / 隔离设备”必须首屏可见。

## 8. 可访问性与减少动效

- 焦点：`focus-visible` 3px `rgba(0,113,227,0.62)`、offset 2px；Tab 顺序等于阅读顺序；Esc 关闭弹层；Ctrl/Cmd+K 命令面板；页签支持左右方向键；子视图切换、抽屉、全屏接管必须有焦点进入与归还，不得困住键盘。
- 触控：手机所有可交互目标 ≥44×44，含门禁瓦片、五轴 chip、证据行操作、设备释放按钮。
- 对比度目标：正文 ≥4.5:1，大字 ≥3:1；`text.quaternary` 也不得低于 4.5:1。**未做 WCAG AA 认证**，当前仅为设计自查，声明前必须有真实审计。
- 动态播报：offline、待 STOP、对账进度用 `aria-live="polite"` 合并播报，不得每秒打断；状态变化只在语义变化时播报。
- 高对比度/强制颜色：`prefers-contrast: more` 与 `forced-colors: active` 下仍保留文本、1px 边框和图标形状，不依赖背景色区分 PASS/FAIL/BLOCKED。使用系统色关键字（`Canvas`、`CanvasText`、`LinkText`、`Highlight`、`HighlightText`、`ButtonBorder`），不设 `forced-color-adjust: none`；`*Soft` 底会被系统覆盖，因此状态词与图标必须独立存在，系统强制色覆盖时不得隐藏状态词。
- 主题声明：V0.0.1 未决策深色前只声明 `color-scheme: light`；启用深色时改为 `color-scheme: light dark` 并配 `prefers-color-scheme` 分支。浅色/深色都必须在 `::selection`、滚动条、原生表单控件上保持可读。
- 深色：仅在 `prefers-color-scheme: dark` 分支重新赋语义令牌，禁止 filter 反色或交换黑白；状态色、焦点环、终端与五轴对比度必须逐项复测。V0.0.1 是否启用深色仍待 Q-04 决策，未决策前按 light-first 实现但禁止组件硬编码浅色值。
- 缩放：200% 下不丢失五轴、证据分母、释放前置；允许局部横向滚动，不允许裁切或重叠。
- 减少动效：`prefers-reduced-motion: reduce` 下过渡降至 0.001ms，停止实时圆点脉冲，仅保留状态文字切换与进度数值；不影响任何功能可达性。
- 已知缺口（须在实现前关闭）：axe-core 未运行、NVDA 未实测、焦点陷阱未完整实现、高对比度未验证、打印/PDF 未覆盖。

## 9. 令牌迁移说明

1. `--na-*` 是 v2 只读别名，全部指向对应 `--naa-*`；新样式只写 `--naa-*`，不改旧别名指向，避免两套色值分叉。
2. 组件内禁止硬编码十六进制、px 字号与任意间距；缺令牌时先扩展令牌文件，再在组件使用。
3. 状态语义按“含义”迁移而非按“颜色”迁移：`ok/warn/danger/neutral/disputed` 对应 PASS/等待-漂移-阻断/失败-危险/未执行-离线-未知/知识争议；`gate.*` 只用于门禁印章，不复用为普通徽标。
4. 旧单状态字段不得直接映射为主色徽标；必须拆成独立信号 + 五轴，映射口径以 `ui-report-knowledge-audit.md` §2.7 为准，无法映射一律 fail-closed 为 `UNKNOWN`。
5. 深色令牌以同名语义键预留，实现时新增 `prefers-color-scheme: dark` 分支并逐一复测对比度；终端在两种主题下都保持深色，不参与反转。
6. 打印/PDF 是第三套表面，不复用屏幕深色令牌；报告导出需单独定义纸面令牌与分页规则。
7. 迁移验收：脚本扫描不得发现裸色值；新旧令牌引用可对齐；键盘、200% 缩放、减少动效三项回归通过后才可移除旧别名。
8. 组件令牌（`input.radius`、`card.padding`、`terminal.radius` 等）、`status.*Ink`、`gate.notApplicable` 与 `layout.breakpoints.wideTablet` 必须先在 `design/apple/design-tokens.json` 登记，再在本文与组件中引用。本文与令牌文件不一致时，以令牌文件为准并在同一次变更中回填本文，禁止只改一处。

## 10. Phase 1 需求可追溯性

本表只为候选稿评审提供定位，不新增行为、枚举、阈值或实施指引；引用范围为本文现有规则。

| 验收项 | 设计系统支撑锚点 |
| --- | --- |
| AC-1 | §5.2 五轴判定可视化（L136–152） |
| AC-2 | §5.3 门禁：G0–G7 八枚瓦片（L154–170） |
| AC-3 | §5.4 租约、占用与对账（L172–195） |
| AC-4 | §5.5 证据与判定（L197–203） |
| AC-5 | §5.6 TaskCard（L205–210） |
| AC-6 | §5.1 禁止等价与禁改写（L117–134） |
| AC-7 | §5 状态语言：文本、形状、颜色三通道（L91–115） |
| AC-8 | §6 数据面组件（L212–224） |
| AC-9 | §7 响应式与密度（L226–247） |
| AC-10 | §8 可访问性与减少动效（L249–260） |
| AC-11 | §2 语义令牌：浅色 / 深色（预留）（L23–60） |
| AC-12 | §3 排版：系统字体、CJK、等宽（L62–80） |
| AC-13 | §4 间距、圆角、阴影、动效（L82–89） |
| AC-14 | §9 令牌迁移说明（L262–271） |

**证据与测试层：**L0–L5 说明验收证据由低层规则/令牌到跨界面可用性验证的层次；T1–T6 说明产生该证据的测试层。本文只提供设计系统规则与待核对项，实际证据、测试结果及通过结论仍由相应验收材料记录，不能由本表推定。

**变更说明：**本次仅响应验证报告 F1，补充 AC-1..AC-14 与 L0–L5/T1–T6 的定位；候选、未冻结、未实施、未做浏览器/图像 QA、无 WCAG 声明等边界不变。

## 11. Phase 1 验收检查与未决

- [ ] 状态 fixture：至少覆盖 loading / empty / error / blocked / stale / offline / partial-evidence / no-permission / draining / quarantined / reconciling / unknown-progress，以及 offline+running+occupied、stale+running、partial-evidence+business PASS、reconciling+pending STOP、quarantined+occupied 五组组合；每张 fixture 标注 `source`、`schema_version`、`server_authoritative`。
- [ ] 可见性：任取一屏，遮住颜色后仍能通过文本/图标/边框区分 PASS、FAIL、BLOCKED、PENDING、UNKNOWN、OFFLINE、STALE、QUARANTINED、RECONCILING、RELEASED、COMPLETED、EXPECTED、NO ACCESS；并确认 COMPLETED/EXPECTED/RELEASED 在彩屏上也不呈绿色。
- [ ] 代码扫描：组件内无裸十六进制、无任意 px 字号/间距；状态只引用语义令牌。
- [ ] 键盘与缩放：Tab 顺序、Esc、方向键、焦点归还通过；200% 缩放下五轴、证据分母、释放前置不被裁切；手机触控目标 ≥44×44。
- [ ] 减少动效：`prefers-reduced-motion` 下过渡为 0.001ms，实时圆点停止，进度数值仍可读；无循环装饰动画。
- [ ] 深色（若 Q-04 选择启用）：独立 `prefers-color-scheme` 分支、对比度复测、终端不反转；未复测不得声称支持。
- [ ] 可访问性证据：axe-core、NVDA/VoiceOver、高对比度、焦点陷阱、打印/PDF 仍是缺口；完成前不得声明 WCAG AA。
- [ ] 文案禁令：不出现“已完成”替代 PASS、“已接收”替代“已核验”、“已释放”替代清理完成、offline 替代“设备空闲”、`COMPLETED` 替代 PASS、`SKIPPED` 替代 PASS、候选替代“已推广”、归档替代“已核验”。
- [ ] 枚举覆盖：每个权威枚举值至少一张 fixture 并确认无映射缺口——五轴 5 组、Gate 6 值、lease `state` 6 值、`communication_state` 3 值、`occupancy_state` 3 值、`execution_permit` 3 值、`pool_state` 8 值、`health_state` 4 值、`Node.status` 4 值、`spool.state` 4 值、证据项状态 8 值；缺映射一律 fail-closed 为 `UNKNOWN`。
- [ ] 进度模式：`COUNTS / QUALITATIVE / INDETERMINATE` 各一张 fixture；`percent=null` 时页面不出现数字百分比；`percent_label` 不被写成“任务完成度”。
- [ ] 断点令牌：`wideTablet=1024px` 已登记且组件无裸 `1024px`；否则按 1200/768 三档回归。

未决：Q-04 深色模式是否纳入 V0.0.1；12 区域是否收敛为 10（Reports→Tasks、Agents→Settings）；`/console` 与 `/aitest` 兼容期；报告是否需要打印/PDF 表面；`business_verdict=EXPECTED` 的产品语义与最终视觉家族（当前先按中性 `expected` 显示）；`layout.breakpoints.wideTablet` 是否登记；图表/指标是否需要独立 `chart.*` 视觉契约（本文未展开）。以上由 Phase 1 评审裁决，本文不预判。

本文是设计系统候选稿，**不构成视觉冻结、UI 实施批准或图像/浏览器 QA 结论**；未运行真实界面、axe、屏幕阅读器或性能测试。
