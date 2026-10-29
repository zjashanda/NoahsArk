# 模型路由与 Token/成本预算

- 状态：当前用户批准的经济型路由说明。Agent 层已有新的 CLI agent-resolution 证据覆盖全部 13 个 Agent；Category 的派发优先级和真实 API 完成仍未验证。
- 生效来源：当前 OMO 路由的用户层是 `/home/bszheng/.omo/omo.jsonc`。`~/.config/opencode/omo.json` 是旧路径文件，不是当前 OMO 加载器的用户层，不能把它当作唯一生效来源。
- 合并规则：用户层优先级最低。OMO 加载器从工作目录向上到 `$HOME` 查找 `.omo/omo.jsonc`（再回退 `.omo/omo.json`）并逐层合并，越靠近工作目录的文件优先级越高。对象深合并，标量和数组整体替换。NoahsArk 当前没有项目级 `.omo/omo.jsonc`，所以就 OMO 的 `.omo` 配置层而言，当前生效的是用户层；以后添加项目文件时按上述规则合并。
- Provider：`listenai`。本路由只使用 `gpt-6-sol`、`gpt-5.6-terra`、`deepseek-v4.1-flash-expires-on-0910` 三个模型 ID，`gpt-6.1-sol` 不在最终路由中使用。
- DeepSeek 模型 ID：`listenai/deepseek-v4.1-flash-expires-on-0910` 中的 `expires-on-0910` 是用户选定的 provider 模型 ID 固定后缀，本文按完整 ID 原样引用，不对其有效期作任何推断。当前所有 DeepSeek 路由都使用这一完整 ID，旧的 `listenai/deepseek-v4.1-flash` 不再使用。
- 适用范围：`~/.omo/omo.jsonc` 的 `[opencode].agents` / `[opencode].categories` 路由，以及 `~/.config/opencode/opencode.json` 中的 OpenCode Agent 条目。本文描述当前用户批准的路由和已验证范围，不把未验证项写成已生效。
- 边界：不测量 provider 账单，不含密钥，不记录 API key，不授权实现、提交或推送。

## 1. 配额假设（用户提供，非实测）

| 预算池 | 假设日额度 | 使用模型 |
| --- | --- | --- |
| GPT 池 | 约 **$300/天**（用户估算） | `gpt-6-sol`、`gpt-5.6-terra` |
| 非 GPT 池 | 约 **$100/天**（用户估算） | `deepseek-v4.1-flash-expires-on-0910` |

这些数字是用户给出的规划额度，不是账单、不是实测用量，也不是模型单价。本文的 Token 区间是单任务“输入+输出”的规划估算，不等于实际计费 Token，也不等于美元。真实计费以 provider 用量或账单为准，本文没有读取或推算账单。

两个池相互独立。不要让全 GPT 的路由意外吃掉廉价池，也不要假设廉价池能吸收 GPT 溢出。

## 2. Agent 与 Category 的关系

- **Agent 默认**：命名 Agent 直接运行时的模型，定义角色身份。
- **Category 默认**：任务通过 category 派发时使用的模型，是委派任务的成本路由面。
- 两层独立，不要求同名或同价。Agent 层已有新的 CLI agent-resolution 证据覆盖全部 13 个 Agent，确认了上表的 Agent 模型解析。该证据只覆盖 Agent 解析，不覆盖 category 派发时的优先级。
- **Category 派发优先级未验证**：`atlas` 的 Agent 默认是 DeepSeek，非 GPT。若任务经 `visual-engineering` / `artistry` / `visual-final` 等 category 派发，且 category 路由优先，则实际走 Terra 的 GPT 池；若 Agent 默认优先，则仍走 DeepSeek。实际以 category 派发验证为准，本文不假设。
- **真实 API 完成未验证**：本文没有证明任一 Agent 或 Category 路由已成功完成真实 API 请求，也没有证据说明 provider 侧的请求结果、限流或计费。
- **回退策略**：所有 Agent 与 Category 的 `models` / `fallback_models` 只重复主模型，不配置跨模型 fallback。这样可避免 GPT 与非 GPT 之间、Terra 与无视觉模型之间发生静默降级。需要换模型时必须人工改路由，并复核、记录。

## 3. Agent 路由表（13 个）

Token 区间为单任务规划估算，包含输入与输出，不是 provider 账单，也不是模型单价。“预算池”指主模型消耗的日额度。“并发”是建议槽位，不是 provider 硬限制。

下表的 Agent 主模型来自当前用户层，并有一次新的 CLI agent-resolution 结果覆盖全部 13 个 Agent。该结果确认 Agent 模型解析，不确认 category 派发优先级或真实 API 完成。

| Agent | 在 NoahsArk 的用途 | 主模型 | 单任务 Token 估算 | 预算池 | 建议并发 |
| --- | --- | --- | --- | --- | --- |
| `atlas` | 顶层编排与跨模块协调 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 25k-70k | 非 GPT | 低成本，≤6 |
| `sisyphus` | 主编排、计划执行负责人 | `listenai/gpt-6-sol` | 25k-70k | GPT | GPT-heavy，≤4 |
| `hephaestus` | 实现与构建工程 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 25k-80k | 非 GPT | 低成本，≤6 |
| `prometheus` | 架构与方案综合 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 25k-70k | 非 GPT | 低成本，≤6 |
| `build` | 通用构建与执行 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 25k-80k | 非 GPT | 低成本，≤6 |
| `plan` | 计划起草与任务拆解 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 12k-35k | 非 GPT | 低成本，≤6 |
| `metis` | 需求分析与解读 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 12k-35k | 非 GPT | 低成本，≤6 |
| `momus` | 评审、批评与风险质疑 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 12k-35k | 非 GPT | 低成本，≤6 |
| `oracle` | 深度推理与疑难调试 | `listenai/gpt-6-sol` | 25k-70k | GPT | GPT-heavy，≤4 |
| `multimodal-looker` | 图像、UI 与渲染结果检查 | `listenai/gpt-5.6-terra` | 15k-45k | GPT | GPT-heavy，≤4 |
| `sisyphus-junior` | 委派任务执行 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 2k-35k（quick 类 2k-8k） | 非 GPT | 低成本，≤6 |
| `explore` | 代码库快速探索 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 3k-12k | 非 GPT | 低成本，≤6 |
| `librarian` | 外部资料与参考研究 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 3k-12k | 非 GPT | 低成本，≤6 |

## 4. Category 路由表（14 个）

下表是当前用户层写入的 Category 目标路由。Token 区间仍是单任务规划估算，不是账单。Category 的派发优先级和真实 API 完成尚未验证，不能把本表当作运行中已按此优先级派发的证据。

| Category | 用途 | 模型 | 单任务 Token 估算 | 派发场景 |
| --- | --- | --- | --- | --- |
| `visual-engineering` | UI 与视觉工程 | `listenai/gpt-5.6-terra` | 15k-45k | 看图、设计令牌、渲染检查 |
| `artistry` | 创意与视觉方案推演 | `listenai/gpt-5.6-terra` | 25k-70k | 设计方向、交互叙事、风格取舍 |
| `visual-final` | 最终视觉验收 | `listenai/gpt-5.6-terra` | 15k-45k | 交付前的视觉终检、渲染复核 |
| `ultrabrain` | 极限推理 | `listenai/gpt-6-sol` | 25k-70k | 难题攻坚、长时间推理 |
| `quick` | 小改动、快速查询 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 2k-8k | 低风险、短链路任务 |
| `writing` | 文档、文案与整理 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 4k-12k | 说明文档、注释、措辞清理 |
| `explore` | 代码检索与结构理解 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 3k-12k | 搜索、读文件、定位调用 |
| `git` | 版本操作辅助 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 2k-8k | 状态检查、diff 归纳、提交信息草拟 |
| `unspecified-low` | 未分类低成本任务 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 2k-8k | 无法归类但工作量小的任务 |
| `deep-low` | 中等深度分析 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 12k-35k | 局部设计、较复杂的排查 |
| `deep-high` | 高深度分析 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 25k-70k | 跨模块问题、复杂契约推演 |
| `unspecified-high` | 未分类高成本任务 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 25k-70k | 无法归类但需要强推理的任务 |
| `architect` | 架构设计 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 25k-70k | 模块边界、接口与依赖设计 |
| `deep` | 通用深度任务 | `listenai/deepseek-v4.1-flash-expires-on-0910` | 25k-70k | 深度任务的默认入口 |

## 5. 回退、视觉与人工改路由

- 所有 `models` / `fallback_models` 都只重复主模型，没有跨模型 fallback 数组。正常运行时不会发生跨类自动降级。
- `gpt-5.6-terra` 是本地唯一声明的视觉模型。任何改到 `deepseek-v4.1-flash-expires-on-0910` 的人工重路由都会失去视觉能力，涉及图片、UI 或渲染的判断必须标记 `NEEDS_REVIEW` 并回到 Terra 重跑。
- 人工改路由必须复核：确认预算池、是否失去视觉、是否改变模型类别，并在任务记录中写明原因。
- 并发上限是建议值，不承诺 provider 会按此限流，也不承诺超限一定被拒绝。

## 6. 并发与配额控制

- 起始限制：**4 个 GPT-heavy 并发**、**6 个非 GPT 并发**。这是在实测吞吐、错误率和延迟之前的保守起点，后续按实测数据调整。
- 这些数字是配置建议，不是 provider 限额，也不保证运行时强制执行。
- GPT 池接近额度时，把新的低风险探索和文档任务移到 `deepseek-v4.1-flash-expires-on-0910`，推迟非紧急的 `deep-*` / `architect` / `ultrabrain` 任务。
- 非 GPT 池接近额度时，减少 `explore` / `librarian` / `git` 任务，不要把廉价任务提升到 GPT 池。
- 任一池接近额度时都不要提高并发“追赶”，应降低 fan-out。
- 当前 `~/.config/opencode/opencode.json` 顶层 `model` 为 `listenai/gpt-6-sol`，`small_model` 为 `listenai/deepseek-v4.1-flash-expires-on-0910`。顶层默认模型会影响未显式指定模型的主流程流量，因此未指定模型的任务可能走 GPT 池；`small_model` 只承担轻量/后台小模型场景。该配置仅在 OpenCode 重启后生效（见第 7 节），本文不据此断言实际计费或运行时路由。

## 7. 重启要求

OpenCode 启动时由 OMO 插件加载 `~/.omo/omo.jsonc`、项目级 `.omo/omo.jsonc` / `.omo/omo.json`，OpenCode 自身加载 `~/.config/opencode/opencode.json`，这些文件都不会热重载。任何配置修改后都必须退出并重启 OpenCode，改动才会生效。本文只记录操作要求；当前文档修正本身只改文档，不触发配置变更，也不声称当前存在待重启的配置修改。

## 8. 验证状态（verification status）

**已有证据：Agent 层。** 新的 CLI agent-resolution 结果覆盖全部 13 个 Agent，确认第 3 节的 Agent 模型解析。该证据只证明 Agent 解析，不证明 category 派发或实际请求完成。

**仍有未验证项：**

- Category 派发优先级：任务通过 category 派发时，Agent 默认与 Category 默认谁优先，尚未通过实际派发确认。因此第 4 节的映射是配置目标，不是运行中优先级的证明。
- 真实 API 完成：没有证据证明任一 Agent 或 Category 路由已成功完成真实 API 请求；provider 侧限流、错误和返回结果未验证。
- 账单与单价：本文没有读取账单，也没有推算 provider 单价。
- 语法与加载：JSONC 的运行时加载未在本文中单独复验；如果再次改配置，重启后应检查加载诊断。
- 回退链：`models` / `fallback_models` 只重复主模型，这是配置目标，未通过请求失败场景实测。

早期版本中的“尚未完成重启”和“两份文件待对齐”不再是当前状态，已由上述 Agent 层证据替代。剩余未验证项仅限上面列出的 Category 派发优先级、真实 API 完成等内容。验证完成前，本文对 Category 只代表配置目标，不代表运行中的实际派发；对 Agent 只代表已解析的模型，不代表实际 API 完成。

## 9. 边界

- 本次只改本文档，未改任何配置文件（包括 `~/.omo/omo.jsonc`、`~/.config/opencode/omo.json`、`~/.config/opencode/opencode.json`）、provider 凭据、插件源码、产品代码、`plan.md`、契约、UI 文档或进度文件。
- 未记录密钥或 API key。
- 未执行 commit 或 push。
- $300/天与 $100/天是用户提供的规划估算，不是实测账单；Token 区间是规划估算，不是计费数据，也不是模型单价。
- 本文不含 benchmark 结论或自拟价格。
