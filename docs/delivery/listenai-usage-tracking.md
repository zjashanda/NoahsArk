# ListenAI 用量看板接入记录（非机密）

- 状态：记录与设计草案。**尚未实现任何自动查询或接口对接**，本文不代表 API 已可用。
- 目的：把 ListenAI 管理后台的用量查询入口记在仓库里，供未来 NoahsArk 平台以安全方式查询模型用量，并持续按 Agent / Category 统计 Token 消耗。
- 关联文档：`docs/delivery/model-routing-budget.md`（模型路由、GPT / 非 GPT 预算池、各 Agent 与 Category 的单任务 Token 估算区间）。
- 边界：本文只记录站点地址、字段、核对方式和接入设计。不含密钥、Cookie、二维码、浏览器配置、密码或账号标识，不修改产品代码和 OpenCode 配置，不提交、不推送。

## 1. 查询来源

| 项目 | 值 |
| --- | --- |
| 名称 | ListenAI Admin API Stats |
| 地址 | `https://openrouter.listenai.com/admin-next/api-stats` |
| 类型 | 需要登录态的后台查询页面 |
| 用途 | 查看模型调用的花费、配额、调用次数与模型分布 |

**重要区分**：这个 URL 只是查询来源，**不是凭据**。地址本身不携带任何权限，能打开域名不等于能查到数据；真正的授权来自你在浏览器里的登录会话。因此 URL 可以写进文档，而会话凭据一律不能写入仓库。

## 2. 需要采集的字段

采集时以页面实际展示为准，下表是要记录的目标字段，不是对页面结构的承诺。

| 字段 | 说明 | 采集注意 |
| --- | --- | --- |
| 日花费（daily spend） | 当日已发生的花费合计 | 记录币种；区分实际花费与估算 |
| 周花费（weekly spend） | 近 7 天或页面定义的周期花费 | 记录周期起止，避免把自然周和滚动 7 天混用 |
| 配额 / 余额（quota） | 剩余额度或上限 | 记录单位（美元额度或 Token 额度）及是否含税 |
| 调用次数（calls） | 请求数量 | 记录是否按成功请求计数，失败请求是否计入 |
| 模型分布（model breakdown） | 按模型 ID 拆分的花费与调用 | 模型 ID 需与路由文档中的 ID 对齐 |
| 时间戳（timestamp） | 快照采集时间与页面统计时间 | 必须写明时区，见第 4 节 |

如果页面还展示输入 / 输出 Token、错误率、限流次数等字段，同样按“字段名 + 取值 + 单位 + 采集时间”记录，不要只留截图。

## 3. 人工核对步骤（已登录浏览器）

只在自己的已登录浏览器里手动核对，本文不提供自动化登录方案。

1. 用已授权的账号在浏览器中正常登录 ListenAI 后台。
2. 打开 `https://openrouter.listenai.com/admin-next/api-stats`。
3. 确认页面显示的是你要看的账号 / 组织范围，记录范围名称时**打码**，只写“个人账号”或“团队账号”这类不带标识的描述。
4. 先记下采集时间与时区，再抄录日花费、周花费、配额、调用次数、模型分布。
5. 对每个数字标注单位与来源周期（例如“当日”“滚动 7 天”）。
6. 导出或截图前先做脱敏：遮住账号名、邮箱、头像、内部 ID、完整 URL 参数。
7. 把脱敏后的结果与本文第 5 节的映射表对照，按 Agent / Category / 模型归类。
8. 若数字与预期差异较大，先怀疑周期口径和时区，再检查是否有未纳入路由的流量（例如顶层默认模型承载的未指定模型任务）。

## 4. 快照记录规则

每次记录用量都必须带上以下元信息，否则数据无法比较：

- **采集时间**：精确到分钟，例如 `2026-10-29 14:30`。
- **时区**：明确写 `Asia/Shanghai (UTC+8)` 这类值，不要只写本地时间。
- **统计周期**：日 / 周 / 自定义区间的起止时间。
- **账号范围**：脱敏描述，不写真实账号标识。
- **采集人**：可写角色（如“平台维护者”），不写个人隐私信息。
- **数据性质**：标明是“后台展示值”还是“估算值”。

时区不一致是最常见的对不上账原因。后台若按 UTC 结算，而你在 UTC+8 的白天查看，日花费的“当日”边界会差 8 小时，必须先对齐再比较。

## 5. 映射到 Agent / Category / 模型

平台需要能回答“哪个 Agent、哪类任务花了多少”。看板通常只按模型聚合，不按 Agent 聚合，所以要靠路由文档做映射。

### 5.1 映射依据

`docs/delivery/model-routing-budget.md` 给出了 13 个 Agent 和 13 个 Category 的主模型与单任务 Token 估算区间。用量归集按以下维度展开：

| 维度 | 取值来源 | 说明 |
| --- | --- | --- |
| Agent | 路由文档第 3 节 | `atlas`、`sisyphus`、`hephaestus`、`prometheus`、`build`、`plan`、`metis`、`momus`、`oracle`、`multimodal-looker`、`sisyphus-junior`、`explore`、`librarian`，另含只在 `omo.json` 出现的 `OpenCode-Builder` |
| Category | 路由文档第 4 节 | `quick`、`writing`、`explore`、`git`、`unspecified-low`、`deep-low`、`deep-high`、`unspecified-high`、`artistry`、`ultrabrain`、`architect`、`deep`、`visual-engineering` |
| 模型 | 看板模型分布 + 路由主模型 | 三个模型 ID：`gpt-6-sol`、`gpt-5.6-terra`、`deepseek-v4.1-flash` |
| 估算 Token 区间 | 路由文档单任务估算 | 例如 `sisyphus-junior` 走 quick/writing 时为 2k-8k |
| 预算池 | 路由文档第 1 节 | GPT 池（`gpt-6-sol`、`gpt-5.6-terra`）与非 GPT 池（`deepseek-v4.1-flash`） |

### 5.2 归集规则

- 看板按模型给花费，先落到模型，再按路由表映射到预算池。
- Agent 与 Category 是两层独立路由，同一个 Agent 经不同 Category 派发时会落到不同模型。归集时不要假设“Agent 名 = 固定模型”，要按实际派发路径归类。
- 未显式指定模型的主流程流量可能走顶层默认模型 `gpt-6-sol`，归入 GPT 池，并单独标记为“未指定模型流量”，不要硬摊到某个 Agent。
- `OpenCode-Builder` 单独统计，不与 13 个命名 Agent 混算。

### 5.3 估算区间不等于账单

必须区分两类数字：

- **估算 Token 区间**：来自路由文档的单任务规划估算（输入 + 输出），用于容量规划和并发控制，不是实际计费数据。
- **Provider 账单 / 后台花费**：ListenAI 后台或 provider 结算给出的真实花费，是唯一可信的成本口径。

两者不能互相替代。不要用“任务数 × 区间中值”去宣称账单金额，也不要用账单反推单任务 Token 后当成事实。差异原因包括缓存命中、重试、失败请求、上下文长度波动、计费粒度等，本文不对这些差异做数值承诺。

## 6. 未来接入设计（安全运行时认证）

本节只是设计草案，**未实现**。

### 6.1 原则

- 只使用运行时的安全认证，凭据不落到仓库、日志、镜像、前端包或导出文件。
- 优先走官方或后台提供的接口（如果存在），不模拟浏览器登录流程，不抓取会话 Cookie。
- 若只能人工导出，则走“人工脱敏导入”通道，而不是把登录态交给程序。

### 6.2 适配器接口（建议）

定义一个只读适配器，与具体实现解耦：

```text
UsageAdapter
  name: string                      // 例如 "listenai-admin-api"
  mode: "api" | "manual-export"     // 当前只允许 "manual-export" 可用
  fetchUsage(range): UsageSnapshot  // 只读，不写远端
  healthCheck(): HealthStatus       // 不返回任何凭据内容
```

`UsageSnapshot` 建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `captured_at` | ISO-8601 + 时区 | 采集时间 |
| `period_start` / `period_end` | ISO-8601 + 时区 | 统计周期 |
| `currency` | string | 币种 |
| `daily_spend` | number | 日花费 |
| `weekly_spend` | number | 周花费 |
| `quota_remaining` | number | 剩余额度 |
| `calls` | integer | 调用次数 |
| `model_breakdown` | array | `{ model_id, spend, calls }` |
| `source_mode` | enum | `api` / `manual-export` |
| `redaction_applied` | boolean | 是否已脱敏 |
| `collected_by` | string | 角色，不含个人标识 |

认证方式：

- 运行时从受管密钥存储（环境注入、密钥管理服务或本机受限权限文件）读取，读取范围最小化。
- 凭据只在内存中使用，不写入日志、不打印、不序列化到快照。
- 适配器只做只读查询，禁止任何写操作或配置修改。
- 无凭据时适配器应显式失败并给出“未配置认证”的状态，而不是回退到匿名访问或模拟登录。

### 6.3 审计字段

每次采集写入审计记录（只含元数据，不含凭据）：

| 字段 | 说明 |
| --- | --- |
| `event_id` | 唯一事件 ID |
| `adapter` | 适配器名称与版本 |
| `source_url` | 查询来源地址（即本文第 1 节 URL，可公开） |
| `auth_mode` | 认证方式类别，例如 `runtime-env`，不记录具体值 |
| `result` | `success` / `auth-missing` / `auth-failed` / `parse-error` / `unavailable` |
| `started_at` / `finished_at` | 带时区 |
| `records` | 采集到的快照条数 |
| `redaction_applied` | 布尔 |
| `error_code` | 脱敏后的错误码，不含堆栈中的敏感路径 |

### 6.4 导入与存储

- 人工导出必须先脱敏再入库，导入前校验 `redaction_applied`。
- 快照按时间序列存储，保留原始采集与映射结果两套视图，方便追溯。
- 归集结果按 Agent / Category / 模型 / 估算 Token 区间展示，并明确标注“估算”与“账单”两种口径。
- 任何导出文件都不得包含账号标识、邮箱、头像、内部 ID、完整带参 URL。

## 7. 操作清单

- [ ] 已登录浏览器打开 `https://openrouter.listenai.com/admin-next/api-stats`，未把登录态交给脚本。
- [ ] 先记录采集时间与时区，再抄数字。
- [ ] 日花费、周花费、配额、调用次数、模型分布均有单位和周期口径。
- [ ] 账号范围已脱敏，无邮箱、标识、头像、带参 URL。
- [ ] 导出前已脱敏，导出文件不入库为原始副本。
- [ ] 按路由文档映射到 Agent / Category / 模型 / 预算池。
- [ ] 明确标注数字是“后台展示值”“估算区间”还是“provider 账单”。
- [ ] 未指定模型流量单独标记，未硬摊到具体 Agent。
- [ ] `OpenCode-Builder` 单独统计。
- [ ] 审计记录只写元数据，无凭据内容。
- [ ] 未声称任何 API 接入已实现。

## 8. 禁止事项

- 不存储 API key、令牌、Cookie、二维码图片、浏览器配置目录、密码、账号标识。
- 不把登录会话、抓包内容或带凭据的请求导出到仓库、日志或聊天记录。
- 不模拟登录、不自动化处理验证码、不复用个人浏览器会话给程序。
- 不修改 `opencode.json` / `omo.json` 或任何产品代码来完成本记录。
- 不把本文当作 API 可用或已接入的证明。

## 9. 边界

- 本次只新增本文档，未改配置、产品代码、契约、UI 文档或进度文件。
- 未访问、登录或抓取任何站点，所有站点信息来自用户提供的地址。
- 未记录任何密钥或账号信息，未执行 commit 或 push。
- 自动查询与 API 适配器均为设计草案，尚未实现。
