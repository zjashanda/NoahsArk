# NoahsArk Phase 1 UI 设计研究：Apple 式克制 × 运营控制台

> 版本：v0.1（2026-10-29）。状态：**研究记录（research note），供 P1 设计评审参考**。不是设计冻结件，不是实施授权，不表示任何界面已实现、已测试或已通过验收。
> 范围：10 条外部权威来源的逐条提取、原则归纳、NoahsArk 落地建议与**来源局限**；覆盖 Apple 式克制、密集运营表格、状态语义、可访问性、响应式、深色模式、离线/陈旧/对账。
> 边界：本文只写本文件与进度日志；不修改 `design/`、`docs/v2/`、`docs/contracts/`、既有 UI 文档、`.omo`、`plan.md` 或产品代码；不提交、不推送。
> 事实源优先级：按 [`docs/contracts/README.md`](../contracts/README.md) §1 与 [`docs/VERSIONING.md`](../VERSIONING.md) 第 2 节执行。凡本文与 `docs/contracts/` 冲突，以契约为准；本文只解释「怎么呈现」，不新增字段、枚举或阈值。

---

## 0. 一页结论

1. **本地既有方向基本成立，但有一处引用已过期**：`docs/v2/UI-DESIGN-APPLE.md` 与 `docs/delivery/ui-design-system.md` 以 Clarity / Deference / Depth 作为 Apple 原则来源；Apple HIG 的 Design principles 页已于 **2026-06-08 重写**，当前组织框架是 Purpose / Agency / Responsibility / Familiarity / Flexibility / Simplicity / Craft / Delight，正文不再使用旧三词。视觉结论不必推翻，**论证语言必须换锚**，否则等于引用一份不存在的规范。
2. **克制与密集不矛盾，来源给了明确判据**：HIG 写的是 "Simplicity isn't minimalism"，即删除无信息目的的装饰，而不是减少事实。因此 Mission Control 可以留白，Runs / Evidence / Devices 必须密集；两者的分界是「一屏是否要回答一个决断」，不是「好不好看」。
3. **状态不能靠颜色，也不能靠单一徽标**：HIG Color / Accessibility 与 Atlassian Lozenge 三条独立来源指向同一结论——同一颜色不得表达两种含义，状态必须带文字与形状。这与 `domain.md` §9.1 的「五轴禁止折叠」方向一致，但外部来源**没有**五轴概念，不能反过来用它证明五轴设计。
4. **密集表格的可用密度是可量化的**：Carbon 给出 24 / 32 / 40 / 48 / 64px 五档行高、骨架屏优先于 spinner、行 hover 常开、工具栏最多 5 个动作、可展开行承载补充信息。这套尺度可直接映射到本地 8pt 体系，不需要发明新数值。
5. **深色模式的成本在令牌复测，不在架构**：HIG 明确深色**不是浅色反相**，并要求自定义前景/背景尽量到 7:1。本地已预留语义层且禁止 `filter` 反相（`ui-design-system.md` §2、§8），方向正确；V0.0.1 是否启用仍是未决项 Q-04，本文不替代该决策。
6. **离线/陈旧/对账是本文与所有外部来源分歧最大的地方**：Grafana 把 stale 视为「序列消失 N 个周期后 **resolved 并从 UI 移除**」；NoahsArk AC-10 要求离线标 stale、**不得**显示为停止或空闲，且不得丢失事实。**这条不能照抄**，只能借它的状态命名与「state reason」机制，反向定义我们自己的保留规则。
7. **"Keep last state" 是一个反面教材**：Grafana 自己写明该选项只适合缓解瞬时抖动，严格监控场景不宜单独依赖。NoahsArk 控制面重启后若沿用旧投影而不标 stale，等于用旧数据宣称实时，直接违反 AC-10。
8. **可访问性有一条现成的硬底线**：WCAG 2.2 AA 的 1.4.1 / 1.4.3 / 1.4.11 / 1.4.4 / 1.4.10 / 2.5.8 / 4.1.3。它能兜住「不只靠颜色、对比度、200% 缩放、320px 重排、24px 目标、状态播报」，但**不能**替代 NVDA/axe 实测，也不构成认证。
9. **响应式的正确判据是可用空间，不是设备类型**：HIG 明确 "Determine layout based on size classes, not device type or orientation"，且「功能不变，只是可见量变化」。本地四档断点（≥1200 / 1024–1199 / 768–1023 / ≤767）可以保留，但论证应从「桌面/平板/手机」改为「内容宽度阈值」。
10. **本文不产生新的数字阈值**：stale 超时、心跳周期、spool 容量、审批超时仍由 P0-06 / P0-08 决定；本文只规定这些数字出现时**界面如何不撒谎**。

---

## 1. 来源总表（10 条）

访问日期统一为 **2026-10-29**。日期取自页面 change log 或版本声明；标注「未注明」者表示该站不提供文档级日期，仅有产品版本化 URL。

| ID | 来源 | 类型 | 标题与 URL | 日期 | 本文采用的核心原则 | 不能迁移 / 局限 |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | Apple HIG | 平台规范 | [Design principles](https://developer.apple.com/design/human-interface-guidelines/design-principles) | 2026-06-08（change log） | 八项原则；"Simplicity isn't minimalism"；"Don't mistake delight for decoration" | 无量化阈值；面向原生 App；"Delight" 不适用于审计台；**旧三词已不在页面** |
| S2 | Apple HIG | 平台规范 | [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) | 2025-06-09 | 对比度表、200% 放大、44×44pt 控件、非颜色通道、减少动效 | pt≠CSS px；VoiceOver/Dynamic Type 为原生；非审计流程；不含 Windows 强制色 |
| S3 | Apple HIG | 平台规范 | [Color](https://developer.apple.com/design/human-interface-guidelines/color) | 2025-12-16 | 同一颜色不得表达不同含义；须提供浅/深/高对比变体；语义色按用途而非外观定义 | 系统色是平台 API，Web 拿不到；无法判断我们的十六进制是否达标 |
| S4 | Apple HIG | 平台规范 | [Dark Mode](https://developer.apple.com/design/human-interface-guidelines/dark-mode) | 2024-08-06 | 深色不是反相；≥4.5:1，自定义色争取 7:1；base/elevated 层次 | 假设系统级外观；**不建议应用内独立外观开关**；无表格/终端指导 |
| S5 | Apple HIG | 平台规范 | [Layout](https://developer.apple.com/design/human-interface-guidelines/layout) | 2026-09-09 | 按可用空间（size class）而非设备类型布局；功能不变、可见量可变；文本放大时行高增长 | size class 是 Apple API；Liquid Glass 与 Web 控制台无关；无桌面 Web 断点数值 |
| S6 | IBM Carbon | 企业设计系统 | [Data table](https://carbondesignsystem.com/components/data-table/usage/) | 2026-09-30（页面标注） | 24/32/40/48/64px 五档密度；骨架屏优先；行 hover 常开；工具栏 ≤5 动作；可展开行 | 密度是产品选择而非证据；24px 行对可点击行低于 WCAG 目标尺寸；无权威投影/陈旧概念 |
| S7 | Atlassian Design System | 企业设计系统 | [Lozenge](https://atlassian.design/components/lozenge/usage) | 未注明（站点无文档日期） | lozenge 只承载状态/优先级/权限；语义色与装饰色分离；实心图标慎用以保留紧迫感 | 纯视觉原语，不含 role/aria 规范；无多轴状态；无残障用户实测证据 |
| S8 | Grafana | 运维可观测性 | [No Data and Error states](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rules/state-and-health/) | 未注明（`latest` 文档） | No Data ≠ Error ≠ Normal；"Keep last state" 的适用边界；state reason 说明「为何处于该状态」 | 告警语义而非投影语义；No Data 是查询结果而非通信中断；明确警告不要用于严格监控 |
| S9 | Grafana | 运维可观测性 | [Stale alert instances](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/stale-alert-instances/) | 未注明（`latest` 文档） | stale 与 No Data 是两种状态；stale 需连续 N 个周期确认；需记录原因 | **stale 会 resolved 并从 UI 移除**，与 AC-10 相反；2 个周期阈值不适用于本域 |
| S10 | W3C | 无障碍标准 | [WCAG 2.2](https://www.w3.org/TR/WCAG22/)（细则见 Understanding 4.1.3 等） | 2024-12-12（本版）；Understanding 更新 2026-05-11 / 2026-09-06 | 1.4.1 / 1.4.3 / 1.4.11 / 1.4.4 / 1.4.10 / 2.5.8 / 4.1.3 为 AA 底线 | AA 是下限不是认证；不规定视觉语言；无法验证语义正确性；不含离线语义 |

**被评估后排除的来源**（记录理由，避免「看起来漏了」）：

| 来源 | 排除理由 |
| --- | --- |
| GOV.UK Design System — Table | 结论与 S6 重叠（caption / `th scope` / 数字右对齐），且在密度尺度上弱于 Carbon；表格语义已由 S10 覆盖。 |
| Nielsen Norman Group — Response Times | 提供 0.1s / 1s / 10s 感知阈值，但 NoahsArk 的 stale 与进度数值必须由 P0-08 / P0-06 决定，引入外部阈值会制造第二套事实。 |
| web.dev — Offline cookbook | 面向离线优先的本地应用；NoahsArk 是服务端权威投影，「离线」意味着**投影不可信**而非「本地可继续操作」，范式不匹配。 |

---

## 2. 逐条来源分析

### 2.1 S1 · Apple HIG — Design principles（2026-06-08）

**原则提取**。当前页面用八项原则组织：Purpose、Agency、Responsibility、Familiarity、Flexibility、Simplicity、Craft、Delight。与 NoahsArk 直接相关的四句原文：

- "**Simplicity isn't minimalism.** Aim for a focused, useful experience that keeps the important things close by and lets the others fall away."
- "**Establish hierarchy.** … Prioritize recognizable controls and a consistent structure that helps people understand where they are and what comes next."
- "**Don't mistake delight for decoration.** … people are trying to accomplish a task, so don't let pursuit of delight for its own sake get in the way of your product's core purpose."
- "**Help people recover from mistakes.** … Build forgiveness into your design."

**NoahsArk 应用**。

| 原则 | 落地规则 | 对应本地决策 |
| --- | --- | --- |
| Simplicity ≠ minimalism | 删的是「无信息目的」的元素：营销 hero、装饰插画、彩色边条、循环动画；**不删**安全事实（离线仍占用、待 STOP、证据不完整、隔离设备）。 | `ui-design-system.md` §1 拒绝清单；`ui-baseline-gap-analysis.md` §7 末段 |
| Establish hierarchy | 每屏一个 `h1`；回答「健康吗」的屏只留结论 + 阻断点；明细靠下钻，不靠缩小字号硬塞。 | `ui-information-architecture.md` §3、§4 |
| No decoration as delight | Mission Control 不做监控墙、不做大图；动效只解释状态变化。 | `ui-design-system.md` §4 动效节 |
| Recover from mistakes | 危险动作可撤销或二次确认；STOP、释放、隔离必须给出「已发生什么 / 还能做什么」。 | IA §4 `quarantined` / `releasing` 行 |

**局限**（必须写进评审记录）：

- 八项原则是**取向**，没有一条可度量；不能用来判定「这个表格是否太密」。
- 页面为 Apple 平台（iOS/iPadOS/macOS/tvOS/visionOS/watchOS）撰写，"Delight" 与消费级产品语境强绑定，直接搬到审计控制台会误导。
- **变更事实**：change log 写 "June 8, 2026 — Reintroduced design principles."。当前正文不再以 Clarity / Deference / Depth 为框架；任何仍引用该三词的内部文档都应标注「历史表述」而非「现行 HIG」。

---

### 2.2 S2 · Apple HIG — Accessibility（2025-06-09）

**原则提取**（可直接量化的部分）：

| 维度 | 原文要求 | 数值 |
| --- | --- | --- |
| 文本放大 | "give people the option to enlarge text by at least 200 percent" | ≥200% |
| 对比度 | 参考 WCAG AA：≤17pt 全字重 4.5:1；18pt 3:1；粗体 3:1 | 4.5:1 / 3:1 |
| 控件尺寸（iOS/iPadOS） | 默认 44×44pt，最小 28×28pt | 44 / 28 |
| 控件间距 | 有边框元件周围约 12pt；无边框约 24pt | 12 / 24 |
| 非颜色通道 | "Convey information with more than color alone"，用形状/图标 | 强制 |
| 动效 | Reduce Motion 下减少自动与重复动画；用淡入替代位移 | 强制 |

**NoahsArk 应用**。

1. 44px 触控不是「Apple 审美」，而是 iOS 默认控件尺寸；本地 `ui-design-system.md` §7/§8 已把手机端所有交互目标定为 ≥44×44，**高于** WCAG 2.2 AA 的 24×24 下限（S10），这是有意的加严，应在评审中说明「不是照抄 WCAG，也不是照抄 Apple，而是取两者较严者」。
2. 200% 放大对应本地「允许局部横向滚动，但不裁切五轴 / 证据分母 / 释放前置」。这条必须落到**表格**而非整页缩放：整页 `zoom` 会把密集矩阵压成不可读。
3. 非颜色通道对应 `ui-design-system.md` §5 的「文本 + 形状 + 颜色」三通道表；该表已超出 HIG 的要求（HIG 只要求「不只靠颜色」），属于本地加严，应保留。
4. 减少动效对应 `prefers-reduced-motion: reduce` 下 0.001ms 与停止实时圆点脉冲。

**局限**：

- pt 是 Apple 平台排版单位，与 CSS px 不是 1:1；「17pt 用 4.5:1」不能直接推出「14px 正文用 4.5:1」——数值结论可用，换算关系不可引用。
- VoiceOver、Dynamic Type、Assistive Access 均为原生能力，Web 端对应物是 `aria-live`、浏览器缩放、`prefers-contrast`，**不能**声称「已遵循 HIG 可访问性」。
- 页面给的是设计期指导，不是审计程序；它明确建议用 Accessibility Inspector，而我们的等价物是 axe + NVDA + 手工走查，三者都还没跑（见 §7）。

---

### 2.3 S3 · Apple HIG — Color（2025-12-16）

**原则提取**：

- "**Avoid using the same color to mean different things.** Use color consistently throughout your interface, especially when you use it to help communicate information like status or interactivity."
- "**Make sure all your app's colors work well in light, dark, and increased contrast contexts.** … If you define a custom color, make sure to supply light and dark variants, and an increased contrast option for each variant."
- "**Avoid relying solely on color** to differentiate between objects, indicate interactivity, or communicate essential information."
- 动态系统色按**用途**（label / separator / background）定义，而不是按外观定义；不得重定义其语义。

**NoahsArk 应用**。

| 规则 | 具体做法 | 现状 |
| --- | --- | --- |
| 一色一义 | 蓝=可交互/进行中；绿=已通过/已验签；琥珀=等待/漂移/阻断；红=失败/危险；灰=未执行/离线/未知。禁止把品牌色复用到非交互文字。 | `ui-design-system.md` §2 已定义 |
| 三态变体 | 每个语义色必须有 light / dark / `prefers-contrast: more` 三份；缺任一份不得宣称「支持深色」。 | dark 为「预留」，高对比未定义 → **缺口** |
| 语义而非外观命名 | 令牌名用 `status.ok` / `gate.fail`，不用 `green` / `red`。 | 已符合 |
| 颜色不是唯一通道 | 五轴、门禁、占用、证据状态全部保留文字。 | 已符合（§5） |

**局限**：

- 系统动态色是 `UIColor` / `NSColor` API，Web 无法调用；我们能复用的只有**方法论**（按用途定义、提供多变体），不是色值。
- 页面无法回答「`#1A7F45` 在 `#FBFBFD` 上是否 4.5:1」；这必须实测，本文不做。
- "increased contrast option" 在 Web 对应 `prefers-contrast: more`，但该媒体查询的浏览器支持与真实用户覆盖率不均，不能当作已交付能力。

---

### 2.4 S4 · Apple HIG — Dark Mode（2024-08-06）

**原则提取**：

- "these colors aren't necessarily inversions of their light counterparts: while many colors are inverted, some are not."
- "At a minimum, make sure the contrast ratio between colors is no lower than **4.5:1**. For custom foreground and background colors, strive for a contrast ratio of **7:1**, especially in small text."
- iOS/iPadOS 用 **base / elevated** 两组背景表达层级：base 更暗、后退；elevated 更亮、前进。
- "**Avoid offering an app-specific appearance setting.**"——否则用户要调两处，且会以为应用坏了。
- 深色下开 Increase Contrast 反而可能降低深色文字与深色背景的对比，必须实测组合。

**NoahsArk 应用**。

1. 本地「深色令牌为预留，禁止 filter 反色或交换黑白」与 HIG 完全一致，应保留该措辞。
2. base/elevated 模型可直接映射到 `surface.canvas`（base）与 `surface.raised`（elevated）：深色下**卡片比页面更亮**，而不是靠阴影。
3. 「不给应用内独立外观开关」是一条**产品级建议**：若未来要做主题切换，应默认 `prefers-color-scheme` 跟随系统，并提供「跟随系统 / 浅色 / 深色」三选一，而不是二元开关。
4. 终端在两种主题下都保持深色（本地已定），与 HIG「沉浸式媒体可用永久深色外观」的精神一致，但 HIG 并未覆盖终端组件——这是本地判断，不是来源结论。

**局限**：

- 假设存在系统级外观设置与系统语义色；纯 Web 交付需自己实现等价物。
- 未涉及数据密集表格、长哈希、终端、打印/PDF；这几类是 NoahsArk 深色风险最高的表面，来源**零覆盖**。
- 7:1 是「strive」而非要求；把它写成验收门槛会与 WCAG AA（4.5:1）产生口径冲突，需明确「本地门槛取 4.5:1，7:1 为目标值」。

---

### 2.5 S5 · Apple HIG — Layout（2026-09-09）

**原则提取**：

- "**Determine layout based on size classes, not device type or orientation.** Size classes describe the actual space available…"
- "**Keep functionality the same as size classes change**, and keep layout changes recognizable and familiar… you can change the amount of functionality that's visible onscreen."
- "**Be prepared for text-size changes.** … horizontally adjacent views may need to stack vertically… table rows or other containers may need to grow in height so that text isn't cropped."
- 视觉层级：按相对重要性排序，阅读顺序自上而下、自前而后；用对齐与缩进表达从属；用 progressive disclosure 降低首屏密度。

**NoahsArk 应用**。

| HIG 规则 | 本地映射 | 需要调整的地方 |
| --- | --- | --- |
| 按可用空间而非设备 | 保留 ≥1200 / 1024–1199 / 768–1023 / ≤767 四档，但文档表述改为「内容宽度阈值」，不再写「桌面/平板/手机」。 | `ui-design-system.md` §7 的措辞 |
| 功能不变、可见量变 | 手机端不得隐藏五轴、证据分母、释放前置；只能改为卡片 / 分组 / 横向滚动。 | 与 IA §8.1 一致，需在验收项固化 |
| 文本放大时行高增长 | 密集表格不能固定 `height`；行高用 `min-height` + 内容撑开，`overflow-wrap:anywhere` 处理长 ID/哈希。 | 当前组件规范未写死；需补 |
| 对齐与缩进表达层级 | 五轴矩阵用行首对象名 + 缩进表达 Run→Attempt；不用彩色分组条。 | 与「无彩色边条」一致 |
| Progressive disclosure | 12 区域 + 8 子视图必须配命令面板、面包屑、深链，否则键盘用户迷路。 | `ui-baseline-gap-analysis.md` §9.3 已列风险 |

**局限**：

- size class 是 Apple 的运行时概念（compact / regular），不是 CSS 断点；我们只能借用「按空间决策」的判据，具体数值仍是本地选择。
- 2026-09-09 版大量篇幅在 Liquid Glass、visionOS 空间布局、tvOS 网格，与 Web 控制台无关；引用时不得暗示「HIG 规定了我们的栅格」。
- 未给出「表格在窄屏转卡片」的具体规则；本地「手机端任务表转卡片」是自定策略。

---

### 2.6 S6 · IBM Carbon — Data table（2026-09-30）

**原则提取**（这是「密集运营表格」最具体的一条来源）：

| 机制 | 原文要点 | 数值 / 规则 |
| --- | --- | --- |
| 密度 | 五档行高与表头高度一致 | xs 24 / sm 32 / md 40（默认）/ lg 48 / xl 64 px |
| 密度配套 | 工具栏、批量操作栏、分页高度必须与行高匹配 | 仅 lg / xl 配 tall toolbar；sm / xs 配 short |
| 加载 | "use skeleton states instead of spinners" | 骨架屏 |
| 行 hover | "should always be enabled"，即使行不可交互，也帮助横向扫读 | 常开 |
| 斑马纹 | 可选修饰符，帮助横向扫读 | 可选，非默认 |
| 展开行 | 承载补充信息或需要额外查询的数据；过密时改去独立页/侧栏 | 渐进披露 |
| 工具栏 | 最多 5 个动作，其余进 overflow | ≤5 |
| 列标题 | 一到两个词；过长换行两行后截断，全文进 tooltip | 1–2 词 |
| 宽度 | 表格应占据页面最大宽度；不要嵌表格、不要塞进狭窄容器 | 最大宽度优先 |

**NoahsArk 应用**。

1. **密度令牌化**：把 24 / 32 / 40 / 48 / 64 映射为 `row.height.xs…xl`，落在现有 8pt 体系内（全部为 8 的倍数，24 为 3×8）。建议默认：密集区（Runs / Evidence / Audit / Devices）用 32；常规列表用 40；含两行内容用 48；24 仅用于键值型 manifest（无交互）；64 仅用于移动端卡片。
2. **骨架屏 vs 进度**：表格首次加载 / 切筛选 / 开详情用骨架屏（对应 IA `loading` 态「保留标题与动作位」）；但 `reconciling` 是**语义状态**而非加载，必须用步骤列表 + 进度，不能用骨架屏掩盖。
3. **行 hover 常开**：与「不用斑马纹也能横向扫读」配合；斑马纹只在超宽证据表启用，且不得与状态底色叠加。
4. **工具栏 ≤5**：直接约束 Mission Control 与 Runs 的工具条，避免变成按钮墙。
5. **展开行**：用于 Attempt 的失败分类、证据项摘要；不得把「五轴」藏进展开行——五轴是首屏事实。

**局限**：

- 五档密度是 Carbon 的产品选择，没有用户研究数据支撑「32 比 40 更好」；我们只能把它当**可选尺度**，不能当结论。
- 24px 行高恰好卡在 WCAG 2.2 的 24×24 下限（S10），远低于 Apple 的 44pt；因此 24 只能用于不可点击的键值行，且行内不得放精确点击操作。
- Carbon 的无障碍指导在独立 tab，本文未逐条核验；引用 usage 页不等于引用其 a11y 合规声明。
- 完全没有「权威投影 / 陈旧 / 对账」概念——这正是 NoahsArk 与通用设计系统最大的差异。

---

### 2.7 S7 · Atlassian Design System — Lozenge（未注明日期）

**原则提取**：

- lozenge 用于「workflow status（On track / In progress / Completed）、system state（Live / Active / On / Disabled）、priority（High / P1 / Urgent）、permissions（Locked / Read only / Private）」。
- 结构 = 标签文本 + 可选图标 + 可选尾部指标徽标。
- **语义色 vs 强调色**：语义色用于「color reflects shared semantic meaning」；强调色用于「color isn't carrying semantic intent」，典型是用户自选颜色的内容。
- "Don't overuse filled icons as it reduces the impact of critical status indicators."——实心图标是**稀缺资源**，留给真正需要拉注意的状态。
- 描述性元数据（分类、分组、筛选）应该用 tag，不要用 lozenge。

**NoahsArk 应用**。

| 规则 | 落地 |
| --- | --- |
| lozenge 只给状态 | PASS / FAIL / BLOCKED / STALE / OFFLINE / QUARANTINED 用 lozenge；设备型号、工具链版本、模型名用中性 tag。 |
| 语义色只给语义 | 五轴与门禁用语义色；知识标签、环境标签用中性色，避免「彩色 = 严重」的误读。 |
| 实心图标稀缺 | 只有 `QUARANTINED`、`FAIL`、`pending STOP` 用实心图标；`PENDING`、`N/A` 用描边或虚线。 |
| 可选尾部指标 | 证据 lozenge 可带 `12/14`；但分母必须来自服务端投影，不得前端计算。 |

**局限**：

- usage 页没有 `role` / `aria-label` / 键盘规范；lozenge 是视觉原语，无障碍语义必须由我们自己补（本地已要求 `aria-label` 含完整状态）。
- 没有多轴状态模型；把五个 lozenge 并排会形成「徽标墙」，需要本地用固定顺序 + 列标题约束（`ui-design-system.md` §5.2）。
- 未提供色盲用户测试证据；「语义色 + 文字」是否足够，仍需实测。

---

### 2.8 S8 · Grafana — No Data and Error states（未注明日期）

**原则提取**：

- 三种状态严格区分：**No Data**（查询成功但无数据点）、**Error**（查询失败/超时）、**Normal**。
- 状态转移遵守 pending period：`Normal → Pending → No Data / Error`；可配置为 `Alerting` / `Normal` / **Keep last state**。
- "**Keep Last State**" 的原文警告："helps mitigate temporary data source issues… However, in situations where strict monitoring is critical, relying solely on the 'Keep Last State' option may not be appropriate."
- `grafana_state_reason` 注解：当实际状态与配置不一致时，附带**原因**（`No Data` / `Error` / `Paused` / `RuleDeleted` / `Updated` / `MissingSeries`）。

**NoahsArk 应用**。

1. **三态分离映射到本地**：`unknown`（投影缺失/从未读取）≠ `error`（请求失败）≠ `empty`（已确认没有对象，**不等于通过**）。IA §8 已有对应行，本文只补来源与「三者不得互相替代」的判据；Grafana 的 `Normal` 是「已评估且未越阈值」，不能映射成 `empty`。
2. **state reason 是本文最值得吸收的机制**：每个非默认状态都带一个**机器可读原因**（`projection_lag` / `node_unreachable` / `lease_uncertain` / `reconcile_pending`），显示为状态徽标旁的第二行小字。本地 IA 只写了「原因」，未规定它是字段还是自由文本——建议定为**受控枚举**，由服务端投影给出。
3. **拒绝 Keep last state**：控制面重启后，禁止沿用旧投影并渲染为实时；必须转为 `stale` 并显示最后权威更新时间。这是 AC-10 的直接推论，也是对 S8 的**有意偏离**。
4. **pending period 的启示**：状态切换应允许「短暂过渡」（如 `reconciling` 先进 `pending` 再进最终态），但过渡本身必须可见，不能静默。

**局限**：

- 这是告警引擎文档，不是 UI 文档；「No Data」描述的是查询结果，不是「节点失联」。
- 它把「无数据」当作**异常信号**处理（默认触发 `DatasourceNoData` 告警），而 NoahsArk 的「无数据」可能是合法的 `NOT_STARTED`；不能直接套用。
- 未注明文档日期，`latest` URL 会随版本漂移；引用时只能声明「截至 2026-10-29 的内容」。

---

### 2.9 S9 · Grafana — Stale alert instances（未注明日期）

**原则提取**：

- 定义："An alert instance is considered **stale** if the alert rule query returns data but its dimension (or series) has **disappeared for a number of consecutive evaluation intervals (2 by default)**."
- 与 No Data 的区别："This is different from the **No Data** state, which occurs when the alert rule query runs successfully but returns no dimensions (or series) at all."
- 处理：保留旧状态 N 个周期 → 转 `Normal (MissingSeries)` 并标记 Resolved → **"The alert instance is removed from the UI."**

**NoahsArk 应用**。

1. **借命名，不借处置**：本地 `stale` 的定义（投影超阈值、事件延迟、缓存回退）与 Grafana 的「序列消失」不同，但「stale 是一个独立于 no-data 的状态」这一条可以直接引用。
2. **必须反向设计**：Grafana 在 stale 后**移除**对象；NoahsArk 在 stale 后**保留**对象并标注，直到对账确认。理由：设备可能仍在执行、租约仍占用（AC-11），移除行等于宣称「不存在」。
3. **stale 必须带两个时间**：最后权威更新时间 + 最后已知活动时间。前者回答「数据多旧」，后者回答「设备最后在干什么」。IA §8 已要求，本文补上来源依据与「不得只给一个相对时间（如 3 分钟前）」的规则。
4. **stale 不得自动 resolved**：任何「自动恢复为正常」的动画或文案都是禁止的；恢复必须来自服务端新投影或对账结果。

**局限**：

- Grafana 的 stale 是**数据源维度消失**，NoahsArk 的 stale 是**投影延迟**；两者成因不同，阈值不可移植。
- 「2 个评估周期」是 Grafana 的默认值，与 NoahsArk 的心跳/超时无关，**禁止**引用为设计参数。
- 该页对「stale 但仍在运行且占用」这一组合**没有任何指导**；这是 NoahsArk 的核心场景，属于来源空白。

---

### 2.10 S10 · W3C — WCAG 2.2（2024-12-12）

**原则提取**（AA 底线，逐条对应本地）：

| SC | 名称 | 级别 | 要求 | NoahsArk 落点 |
| --- | --- | --- | --- | --- |
| 1.4.1 | Use of Color | A | 颜色不是传达信息的唯一视觉手段 | 五轴/门禁/占用/证据三通道 |
| 1.4.3 | Contrast (Minimum) | AA | 正文 4.5:1；大字 3:1 | 正文 ≥4.5:1 |
| 1.4.4 | Resize Text | AA | 200% 不丢失内容或功能 | 200% 下不裁切五轴/分母/释放前置 |
| 1.4.10 | Reflow | AA | 320 CSS px 宽不出现二维滚动（例外除外） | 手机端表格转卡片 |
| 1.4.11 | Non-text Contrast | AA | UI 组件与图形对象 3:1 | 边框、焦点环、图标、门禁瓦片 |
| 2.5.8 | Target Size (Minimum) | AA | 24×24 CSS px | 本地取 44×44（更严） |
| 4.1.3 | Status Messages | AA | 状态消息可不获焦点即被辅助技术播报 | `aria-live="polite"` 合并播报 |
| 2.2.2 | Pause, Stop, Hide | A | 自动开始且持续 >5s 的移动/闪烁/滚动/自动更新内容，须可暂停、停止或隐藏 | 实时刷新与对账进度须可控 |

**NoahsArk 应用**。

- 4.1.3 是「离线/待 STOP/对账中」三类动态提示的**唯一硬依据**；本地已规定「只在语义变化时播报，不得每秒打断」，这是对 4.1.3 的正确工程化，应保留。
- 1.4.10 与本地「手机端任务表转卡片」一致；但**五轴不能压成 5 个窄列**，只能改为纵向堆叠卡片。
- 2.5.8 的 24×24 与 Apple 的 44×44 不冲突：前者是合规下限，后者是平台默认；本地取 44 属于加严，需在验收中写明「严于 AA，非法定要求」。

**局限**：

- AA 是**下限**，通过 AA 不等于好用；WCAG 不评价信息架构、密度、状态语义是否正确。
- SC 文本不提供实现细节（例如 `aria-live` 的节流策略），工程判断仍需本地完成。
- 不覆盖 Windows 高对比度（forced-colors）与深色模式的组合；这两项需单独实测。
- 无法验证「PASS 是否真的等于五轴全通过」这类**语义正确性**——那是契约测试的职责。

---

## 3. 主题综合

### 3.1 Apple 式克制：定义一条可执行的「克制预算」

把 S1 / S3 / S4 / S5 收敛成可检查的预算，而不是形容词：

| 维度 | 预算 | 检查方式 |
| --- | --- | --- |
| 强调色 | 全局 1 个（`accent.base`）；同屏最多 1 处主按钮使用 | 脚本扫描主按钮数量 |
| 阴影 | 默认 0；仅分段控件选中、弹层、Toast、滚动后顶栏 | 组件快照 |
| 字族 | 2 个（系统无衬线 + 等宽） | 令牌扫描 |
| 字号层级 | ≤6 级；标题与正文差 ≥8px | 令牌表 |
| 装饰元素 | 0（无 hero、无插画、无渐变、无彩色边条） | 设计评审 |
| 动效 | 仅状态变化；无循环、无视差、无滚动劫持 | `prefers-reduced-motion` 走查 |
| 留白 | 8pt 基准；内容最大 1160px | 布局检查 |

**关键平衡**：克制作用于**装饰**，不作用于**事实**。密集区的行高、列数、筛选器属于「信息」，可以多；卡片阴影、渐变、图标装饰属于「装饰」，必须少。这条区分直接解释了为什么 Mission Control 可以极简而 Runs 可以极密，两者不矛盾。

### 3.2 密集运营表格：从「感觉密」到「可参数化」

综合 S5 / S6 / S10：

1. **行高是密度旋钮**，不是风格选择：`24`（键值行，不可点）< `32`（密集）< `40`（默认）< `48`（两行内容）< `64`（移动卡片）。
2. **密度与可点击性耦合**：行高 < 32 时，行内不得放需要精确点击的操作；操作移到行尾 44×44 按钮或详情抽屉。
3. **表格必须能「横向扫读 + 纵向定位」**：行 hover 常开（S6）；首列固定为对象名（任务/运行/设备），不固定状态列。
4. **数字右对齐 + `tabular-nums`**：证据计数、分母、耗时、样本量一律右对齐；单位与数字分离，避免「12 次」与「12s」混淆。
5. **长值处理**：哈希、路径、ID 用 `overflow-wrap:anywhere`，并提供「复制完整值」；截断必须带 tooltip，且 tooltip 内容 = 完整值。
6. **窄屏不是「缩小表格」**：≤767px 转卡片，每张卡保留对象名 + 五轴摘要 + 阻断原因；不得只显示对象名和色点。

### 3.3 状态语义：三通道 + 五轴 + 原因

| 层 | 规则 | 来源 |
| --- | --- | --- |
| 通道 | 文本必显；形状/图标区分家族；颜色只作第三通道 | S2、S3、S7、S10-1.4.1 |
| 轴 | 五轴固定顺序，禁止折叠为单徽标或单布尔 | 本地 `domain.md` §9.1（外部无此概念） |
| 语义色 | 一色一义；语义色只给语义，装饰色只给非语义标签 | S3、S7 |
| 原因 | 每个非默认状态带受控 `state_reason`，显示为第二行小字 | S8（借鉴） |
| 播报 | 仅在语义变化时合并播报，不逐秒打断 | S10-4.1.3 + 本地 IA §8.1 |
| 释放/收尾 | `RELEASED` / `CLOSED` 用中性外框，不用绿色 | `ui-design-system.md` §5（防「收尾=通过」误读） |

**禁止清单**（由来源直接支持）：

- 用同一颜色表示「进行中」与「可点击」（S3）。
- 用颜色块替代状态文字（S2、S10）。
- 给所有状态都加实心图标（S7：会稀释紧迫感）。
- 把 `No Data` 显示为 `Normal`（S8）。
- 把 `stale` 自动 resolved 或从列表移除（S9 的做法，**本地必须相反**）。
- 用骨架屏掩盖 `reconciling`（骨架屏是加载态，S6）。

### 3.4 可访问性：把 AA 变成可执行清单

| 检查项 | 阈值 | 当前状态 | 关闭条件 |
| --- | --- | --- | --- |
| 正文对比度 | ≥4.5:1 | 设计自查，未实测 | 逐令牌测量报告 |
| 非文本对比度 | ≥3:1 | 未测 | 边框/图标/焦点环测量 |
| 200% 缩放 | 无裁切 | 有策略，未回归 | 截图回归（关键 6 屏） |
| 320px 重排 | 无二维滚动 | 有策略，未回归 | 真机/模拟器截图 |
| 触控目标 | ≥44×44（本地） | 既有原型部分按钮 22–26px（gap-analysis §9.1） | 逐项测量 |
| 键盘 | 全功能可达 | 无完整焦点陷阱 | Tab 走查记录 |
| 屏幕阅读器 | 状态可播报 | 未测 | NVDA + Edge/Chrome 记录 |
| 自动化 | 0 critical | 未运行 | axe 报告 |
| 强制色 | 状态可辨 | 未验证 | `forced-colors` 截图 |
| 动效 | 可关闭 | 已支持 | `prefers-reduced-motion` 回归 |

### 3.5 响应式：以内容宽度为判据

- 四档保留，但语义改为「可用宽度」：≥1200 双列 + 上下文栏；1024–1199 双列收紧；768–1023 单列 + 抽屉；≤767 底部 5 Tab + 卡片。
- **功能不变**：任何一档都不得隐藏五轴、证据分母、释放前置、离线时间。
- **可见量可变**：平板收起上下文栏，手机把表格转卡片，均属允许。
- **文本放大优先于断点**：字号放大导致换行时，先让行高增长、列换行，再触发断点；不要把「放大 200%」当作「进入手机布局」。
- 断点必须由令牌提供（`layout.breakpoints.*`），组件内禁止裸 `px` 媒体查询。

### 3.6 深色模式：三份令牌 + 一次实测

- 语义层三份：light / dark / increased-contrast；组件只能引用语义键。
- 深色不是反相：`surface.raised` 比 `surface.canvas` **更亮**（HIG base/elevated 模型）。
- 状态色必须逐项复测：ok / warn / danger / disputed / stale 在深色底上的对比度与色相区分度。
- 终端永远深色，不参与主题切换；打印/PDF 是第三套表面，单独定义纸面令牌。
- 不提供「应用内独立外观开关」；若必须有，采用「跟随系统 / 浅色 / 深色」三选一。
- **决策仍未闭合**：V0.0.1 是否交付深色由 Q-04 决定；本文只主张「即使不交付，也必须预留语义层且禁止硬编码浅色值」。

### 3.7 离线 / 陈旧 / 对账：本文的核心分歧点

这是唯一一处必须**明确反对**来源做法的地方。

| 信号 | 含义 | 必须显示 | 禁止显示 | 来源关系 |
| --- | --- | --- | --- | --- |
| `offline` | 节点↔控制面通信中断 | 离线徽章、执行可能继续、占用保持、离线开始时间、最后已知活动 | 「已停止」「设备空闲」「可重派」 | S9 无此概念 |
| `stale` | 投影超阈值 / 事件延迟 / 缓存回退 | 灰虚线、`state_reason`、最后权威更新时间、最后已知活动 | 「实时」；自动 resolved；从列表移除 | **与 S9 相反** |
| `reconciling` | 重连 / 控制面恢复 / 占用不确定 | 对账步骤、未确认占用、禁止新派的说明 | 对账前释放或重派；旧 epoch 当现状 | S8 的 pending 思路可借 |
| `unknown-progress` | 总量未知/计数不可靠 | 阶段、门禁、已知计数、「未知」 | `0%`、`99%`、「即将完成」 | 无来源，本地定义 |

**三条硬规则**：

1. **陈旧 ≠ 停止**：`stale` 只描述「我们看到的有多旧」，不描述「设备在做什么」。任何把 stale 渲染成 idle/stopped 的映射都是缺陷。
2. **对账前不释放**：`reconciling` 期间释放按钮必须 disabled，并给出 `aria-describedby` 原因（S10 + 本地 IA §8.1-5）。
3. **不静默续用旧值**：控制面重启后，旧投影必须立刻降级为 `stale`，直到新投影到达。Grafana 的 "Keep last state" 在这里是**反模式**。

**离线组合的可视化**：必须能同时显示 `communication=OFFLINE` + `execution=RUNNING` + `occupancy=OCCUPIED` + `execution_permit=GRANTED` + 待送达 STOP。这五个信号在视觉上不得互相覆盖（例如不能用一个大灰条把整行压暗到看不见 RUNNING）。

---

## 4. 与现有 NoahsArk 文档的关系

### 4.1 本文确认的既有决策

| 既有决策 | 位置 | 本文立场 |
| --- | --- | --- |
| 五轴独立、禁止折叠 | `docs/contracts/domain.md` §9.1 | 确认；外部来源无法推翻契约 |
| 正式 PASS 需五轴全通过 | `domain.md` §14 | 确认；UI 只读 |
| 离线标 stale、不显示停止/空闲 | `plan.md` L656（AC-10）、`ui-information-architecture.md` §8 | 确认，并补来源对照 |
| 断点四档与密度分区 | `ui-design-system.md` §7 | 确认，改论证口径 |
| 状态三通道 | `ui-design-system.md` §5 | 确认，补 Atlassian/Carbon 佐证 |
| 深色禁止反相 | `ui-design-system.md` §2、§8 | 确认，补 HIG 依据 |

### 4.2 本文提出的修正

| ID | 修正 | 理由 | 影响面 |
| --- | --- | --- | --- |
| R-1 | 把「Clarity / Deference / Depth」标注为历史表述，改用 HIG 2026 八原则 + 本地「Quiet Instrument」自有表述 | S1 已重写，旧三词不在现行页面 | `docs/v2/UI-DESIGN-APPLE.md` §2.1、`ui-design-system.md` §1（**仅建议，本文不改**） |
| R-2 | 断点描述从「桌面/平板/手机」改为「可用宽度阈值」 | S5 | `ui-design-system.md` §7 措辞 |
| R-3 | 新增 `row.height` 密度令牌（24/32/40/48/64） | S6 | 令牌文件 + 组件规范 |
| R-4 | 新增受控 `state_reason` 显示位（状态徽标第二行） | S8 | IA §8、屏幕规格 |
| R-5 | 明确 `stale` 永不自动 resolved / 永不从列表移除 | S9 反向 + AC-10 | IA §8、验收项 |
| R-6 | 表格加载用骨架屏；`reconciling` 用步骤进度，不得用骨架屏 | S6 | 组件规范 |
| R-7 | 状态用 lozenge，元数据用中性 tag；实心图标仅限三类高危状态 | S7 | 组件规范 |
| R-8 | 明确 44×44 为「本地加严」，24×24 为 AA 下限 | S2 + S10 | 验收说明 |

### 4.3 本文不覆盖的内容

- 具体色值是否达标（需实测）。
- 组件 API、CSS 实现、框架选型。
- 12 区域的逐屏线框（见 `ui-screen-specification.md`）。
- 任何阈值、超时、重试、样本量（见 P0-06 / P0-08）。
- 打印/PDF 版式。

---

## 5. 建议（按优先级）

| ID | 建议 | 优先级 | 依据 | 验收方式 |
| --- | --- | --- | --- | --- |
| A-1 | 建立「克制预算」检查表（§3.1），纳入设计评审 | P0 | S1/S3/S4/S5 | 评审记录逐项勾选 |
| A-2 | 落地密度令牌并规定「<32px 行高不得放精确点击操作」 | P0 | S6/S10-2.5.8 | 令牌扫描 + 交互走查 |
| A-3 | 五轴矩阵改为语义表格（`caption` + `th scope`），手机端转纵向卡片 | P0 | S10-1.4.1/1.4.10 + `ui-baseline-gap-analysis.md` §9.2 | axe + NVDA + 200% 截图 |
| A-4 | `stale` / `offline` / `reconciling` 三态各自独立组件，禁止合并 | P0 | S9 反向 + AC-10/AC-11 | fixture 组合测试 |
| A-5 | 引入 `state_reason` 受控枚举并显示为第二行 | P1 | S8 | 契约评审 |
| A-6 | 状态 lozenge / 元数据 tag 二分，实心图标限三类 | P1 | S7 | 组件清单核对 |
| A-7 | 深色三份令牌 + 逐项对比度复测（即使 V0.0.1 不交付） | P1（依赖 Q-04） | S4/S3 | 令牌表 + 测量报告 |
| A-8 | 离线组合的「五信号同屏」布局规范（通信/执行/占用/许可/待 STOP） | P0 | AC-11 + IA §8 | 设计评审 + 真机烟测 |
| A-9 | 骨架屏 / 进度 / 空态 / 错误四态组件化，禁止互相替代 | P1 | S6 + IA §8 | 组件快照 |

---

## 6. 未决问题（OQ = open question；与本地决策编号 Q-04 区分）

| ID | 问题 | 为何未决 | 建议归属 |
| --- | --- | --- | --- |
| OQ-1 | V0.0.1 是否交付全局深色？ | 本地 Q-04 未决；成本在复测而非架构 | 产品负责人 |
| OQ-2 | 密集区默认行高取 32 还是 40？ | 来源只给尺度，无本域可用性数据 | P1 可用性测试 |
| OQ-3 | `state_reason` 显示原始码还是本地化文案？ | 原始码利于排障，文案利于运营 | 契约 + IA 评审 |
| OQ-4 | stale 超过多久必须阻断操作？ | 阈值属 P0-08，UI 不得自定 | P0-08 |
| OQ-5 | 桌面端是否需要 44×44（而非 24×24）？ | AA 只要求 24；Apple 44 是触控默认 | 设计评审 |
| OQ-6 | 表格在 1024–1199 是否保留双列详情？ | 本地已有草案，缺实测 | P1 视觉 QA |
| OQ-7 | 打印/PDF 报告的纸面令牌 | 完全无来源覆盖 | 后续阶段 |
| OQ-8 | 中文标题是否使用负字距 | 本地已定「中文不用负字距」，但与 HIG 英文紧字距并存需说明 | 设计系统维护者 |

---

## 7. 验证与边界

**本文完成的验证**：

- 10 条来源全部**实时抓取**，标题、URL、修订日期逐条核对；Apple 页面通过官方 `.md` 端点读取 change log。
- 关键原文引用均为页面原句（英文），未改写语义。
- 本地引用逐一比对行号：`ui-design-system.md` §1/§2/§5/§7/§8；`ui-information-architecture.md` §3/§4/§8/§8.1；`ui-baseline-gap-analysis.md` §7/§9.2/§9.4；`ui-screen-specification.md` §4；`docs/contracts/domain.md` §9.1/§14/§15；`plan.md` L656（AC-10）、L662（AC-11）。
- 交叉检查：本文未引入任何契约外字段、枚举或数值阈值。

**本文明确未完成**：

- 未做对比度测量、未跑 axe、未做 NVDA 走查、未做 200%/320px 截图回归、未做真实用户可用性测试。
- 未验证深色令牌的实际对比度；未验证 `forced-colors` 表现。
- 未做任何浏览器渲染或视觉 QA；本文不含截图证据。
- 未评审 `docs/contracts/` 的字段变更（本文不提议变更）。

**结论**：本文可作为 P1 设计评审的**论证底稿**，不构成设计冻结、无障碍合规声明或实施授权。

---

## 8. 来源访问记录

| ID | 访问时间（Asia/Shanghai） | 读取方式 | 备注 |
| --- | --- | --- | --- |
| S1 | 2026-10-29 | 官方 Markdown 端点 | change log：2026-06-08 |
| S2 | 2026-10-29 | 官方 Markdown 端点 | change log：2025-06-09 |
| S3 | 2026-10-29 | 官方 Markdown 端点 | change log：2025-12-16 |
| S4 | 2026-10-29 | 官方 Markdown 端点 | change log：2024-08-06 |
| S5 | 2026-10-29 | 官方 Markdown 端点 | change log：2026-09-09 |
| S6 | 2026-10-29 | HTML | 页面标注 Last updated 2026-09-30 |
| S7 | 2026-10-29 | HTML | 站点无文档日期 |
| S8 | 2026-10-29 | HTML | `latest` 文档，无日期 |
| S9 | 2026-10-29 | HTML | `latest` 文档，无日期 |
| S10 | 2026-10-29 | HTML | 规范 2024-12-12；Understanding 2026-05-11 / 2026-09-06 |
