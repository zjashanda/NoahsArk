## Purpose

给平台提供统一的 skill 注册与调度契约，使编排步骤能够以一致方式发现、校验、调用 skill 并收取结果与证据，避免把某个 skill 的调用细节写死在单个业务流里。

## ADDED Requirements

### Requirement: skill 注册

平台 SHALL 维护 skill 注册表，每个条目 MUST 声明唯一标识、语义化版本、所属业务域、输入契约、输出契约、前置条件、超时上限和失败分类规则。注册表 MUST 支持同一标识的多个版本共存，且 MUST 能标记某版本为已弃用。未注册的 skill MUST NOT 被编排引用。

#### Scenario: 注册新 skill

- **WHEN** 提交包含完整契约的 skill 注册
- **THEN** 平台保存该版本，返回注册标识与版本号，并使其可被模板引用

#### Scenario: 缺少输出契约

- **WHEN** 提交的注册缺少输出契约
- **THEN** 注册被拒绝，返回缺失字段清单，注册表不变

#### Scenario: 弃用版本

- **WHEN** 某 skill 版本被标记弃用
- **THEN** 新模板不得引用该版本，已引用该版本的实例继续按原版本执行并记录弃用告警

### Requirement: skill 发现

平台 SHALL 支持按业务域、能力和版本约束查询可用 skill。查询结果 MUST 稳定排序，MUST 返回每个条目的前置条件摘要和版本状态。

#### Scenario: 按能力查询

- **WHEN** 客户端按能力 `tcl-scenario-run` 查询可用 skill
- **THEN** 返回全部可用版本，按标识和版本稳定排序，并标注弃用状态

#### Scenario: 无匹配

- **WHEN** 查询条件没有任何匹配的 skill
- **THEN** 返回空列表和显式的 `no_match` 标记，不返回模糊替代项

### Requirement: 前置条件校验

调用 skill 之前，平台 MUST 校验其声明的全部前置条件，至少覆盖运行环境、目标节点能力、资源租约和操作权限。任一前置条件不满足时，平台 MUST NOT 发起调用，并把 skill 调用记录为 `PRECHECK_FAILED`，同时返回未满足项。

#### Scenario: 租约缺失

- **WHEN** skill 声明需要独占设备租约而当前任务没有有效租约
- **THEN** 平台不发起调用，记录 `PRECHECK_FAILED`，返回缺失的租约要求

#### Scenario: 权限不足

- **WHEN** 请求方缺少 skill 声明的能力
- **THEN** 平台拒绝调用，记录拒绝原因，不产生节点侧任何动作

### Requirement: 调用与证据采集

每次 skill 调用 SHALL 生成唯一调用记录，包含调用标识、skill 版本、输入摘要、开始与结束时间、退出状态、输出摘要和证据引用。原始输出 MUST 按不可信输入处理，落库前 MUST 做大小上限和敏感信息脱敏。证据 MUST 能追溯到具体调用记录。

#### Scenario: 成功调用

- **WHEN** skill 调用正常结束
- **THEN** 调用记录置为 `SUCCEEDED`，输出摘要与证据引用写入，且证据可反查到该调用标识

#### Scenario: 超大输出

- **WHEN** skill 返回输出超过声明上限
- **THEN** 平台截断并保存摘要，保留原始证据的存储引用，调用记录标注 `TRUNCATED`

#### Scenario: 输出含敏感信息

- **WHEN** skill 输出包含凭据形态的字符串
- **THEN** 落库内容已脱敏，审计记录标注发生过脱敏，原值不出现在任何可查询接口

### Requirement: 失败分类与重试策略

平台 SHALL 对失败调用分类为 `TRANSIENT`、`PERMANENT`、`PRECHECK_FAILED` 或 `CANCELLED`。仅 `TRANSIENT` 可按注册表声明的次数与退避策略重试，且重试次数 MUST 有上限。`PERMANENT` 与 `PRECHECK_FAILED` MUST NOT 自动重试。非幂等 skill MUST 携带幂等键，缺少幂等键时 MUST NOT 自动重试。

#### Scenario: 瞬时失败重试

- **WHEN** 调用因节点短暂不可达失败且被分类为 `TRANSIENT`，未达重试上限
- **THEN** 平台按退避策略重试，调用记录保留每次尝试，最终状态取最后一次结果

#### Scenario: 永久失败

- **WHEN** 调用因参数错误失败并被分类为 `PERMANENT`
- **THEN** 平台不重试，立即把所属编排步骤置为 `FAILED` 并上报失败原因

#### Scenario: 非幂等缺幂等键

- **WHEN** 非幂等 skill 的调用请求没有幂等键
- **THEN** 平台拒绝发起调用，返回幂等键缺失错误

### Requirement: 超时与取消

每次调用 SHALL 受注册表声明的超时上限约束。超时 MUST 把调用置为 `TIMEOUT` 并触发已声明的清理动作。取消请求 MUST 传播到执行侧，且 MUST 记录取消发起人与时间。取消后不得把部分输出当作成功结果。

#### Scenario: 调用超时

- **WHEN** skill 调用超过声明上限仍未返回
- **THEN** 调用置为 `TIMEOUT`，执行清理，所属步骤按失败策略处理

#### Scenario: 运行中取消

- **WHEN** 操作人取消正在执行的调用
- **THEN** 平台向执行侧传播取消，调用置为 `CANCELLED`，部分输出只作为证据保留，不作为步骤成功依据

### Requirement: 调度与编排解耦

编排层 SHALL 只通过统一的调度接口发起 skill 调用，MUST NOT 直接依赖某个 skill 的内部实现或私有参数。新增一个业务域时，MUST 只需注册 skill 和定义模板，不修改调度接口本身。

#### Scenario: 新增业务域复用调度

- **WHEN** 新业务域注册了新的 skill 并定义模板
- **THEN** 编排可以调用该 skill，调度代码无需改动

#### Scenario: 绕过调度直接调用

- **WHEN** 编排实现尝试绕过调度接口直接执行 skill 逻辑
- **THEN** 该实现被评审判为违反契约，测试用例断言调用必须产生调度记录
