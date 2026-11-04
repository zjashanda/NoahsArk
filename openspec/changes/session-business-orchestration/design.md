## Context

当前任务创建路径集中在 `services/supervision.py` 的 `create_task_with_supervisor`，它建任务、建 opencode 会话，然后由 `services/supervisor.py` 派发和轮询。没有任何步骤编排层，任务类别只体现在 prompt 文本里。

知识侧 `services/knowledge.py` 只实现候选到正式条目的人工晋升，候选必须先被人工置为 `APPROVED`。任务终态到归档之间没有提炼入口，所以已完成任务在知识库中留下零条目。

测试侧 `models/test_campaign.py` 用 `scenario` 字符串字段承载场景，`services/test_campaign_results.py` 在平台侧解析不可信 payload，节点侧 `apps/node_agent/noahsark_node/tools.py` 只接受 `TEST_RUN_SCENARIOS = {"wake-recognition"}`，入口写死在同一个模块。

约束：PostgreSQL 是唯一正式数据库，SQLAlchemy 异步会话；判定维持执行、设备、证据、最终判定的分离；不可信节点输出必须校验和限额；凭据不下发到节点；不得引入第二套工作流引擎。

## Goals / Non-Goals

**Goals:**

- 用可版本化的数据定义驱动任务编排，新增业务域不修改调度代码。
- skill 调用统一走注册表和调度接口，调用、证据、失败分类可追溯。
- 任务收尾产出知识候选或显式空结论，归档前强制检查。
- 测试场景成为可注册资产，节点执行入口按场景固定，平台公共路径不含场景分支。

**Non-Goals:**

- 不实现通用 BPMN/工作流引擎，不引入外部编排中间件。
- 不在本变更内实现完整 UI，只定义只读查询接口所需的数据。
- 不改变五轴判定语义，不改变现有租约与证据模型。
- 不自动晋升知识，不允许提炼流程写正式知识库。
- 不迁移历史任务的执行记录内容。

## Decisions

### 1. 编排定义存表，代码只做解释器

新增 `workflow_templates`、`workflow_template_versions`、`workflow_steps`、`workflow_skill_bindings`。模板发布时做完整校验：步骤顺序无环、退出条件可求值、引用的 skill 版本存在且未弃用。运行时按版本快照解释，不重新读取可变定义。

备选是 Python 类定义流程，热更新要发版，跨业务域扩展必须改代码，放弃。用 JSONB 存步骤配置，关键字段单独建列以便查询和约束。

### 2. 编排实例挂到既有任务与会话，不新建执行器

新增 `orchestration_instances` 和 `step_executions`，实例引用 `task_id`、`task_revision_id`、模板版本。推进由现有 supervisor 工作循环驱动：supervisor 领取会话后先读实例，再决定本次要做的步骤，做完回写步骤状态。这样不产生第二个调度器，租约、心跳、超时的既有语义继续生效。

备选是独立编排服务加独立队列，会增加一套一致性边界和故障面，放弃。

### 3. skill 调度是显式适配层

新增 `skill_registrations`（标识、版本、域、输入/输出 JSON Schema、前置条件、超时、重试策略、幂等性）和 `skill_invocations`（调用标识、实例与步骤、输入摘要、状态、尝试序号、证据引用）。调度接口固定为 `precheck -> invoke -> classify -> record`。

执行适配分两类：节点类 skill 走 `node_commands` 下发并通过现有回执通道收敛；平台类 skill 在 control_plane 进程内执行但必须写同样的调用记录。前置条件声明为可求值表达式，覆盖节点能力、租约、权限、环境变量存在性，不写进模板文本。

失败分类由注册表规则加执行结果共同决定。`TRANSIENT` 才允许重试；非幂等 skill 缺幂等键直接拒绝；超时先清理再落状态。

### 4. 收尾提炼作为归档前置 gate

新增 `knowledge_extraction_runs`（任务、状态、理由码、候选引用、失败摘要、重试次数）。任务进入终态后触发一次提炼，输出写 `knowledge_candidates`，候选沿用现有 `PENDING_REVIEW -> APPROVED -> PROMOTED` 路径，提炼不得调用晋升接口。

无可复用知识时写 `no_reusable_knowledge`，理由码来自固定枚举，必须带判断人和时间。提炼失败写 `FAILED` 并阻塞归档，授权人可写人工结论解锁。归档检查新增一条：存在成功提炼记录或人工结论。

候选的 `duplicate_of` 通过确定性相似度（标题归一化加证据指纹加场景标识）比对，命中后按合并或新版本处理，不改写历史条目。

### 5. 场景注册表驱动节点执行

新增 `test_scenarios`（标识、版本、任务类别、参数 Schema、资产清单含校验值、前置检查、执行入口、结果适配版本、判定规则、证据要求）。`test_campaigns` 增加 `scenario_id`、`scenario_version` 作为外键，原 `scenario` 字符串保留为历史兼容列，新活动只写外键。

节点侧把 `tools.py` 中的硬编码集合改为读取命令载荷里的场景清单与入口，场景资产放在节点固定目录并做校验值核验。执行协议固定为：标准输入传 JSON 参数，标准输出返回 JSON 结果，退出码只表达进程结果，业务判定由平台按规则计算。这样新增场景只需新增清单和适配实现，平台公共路径不改。

结果适配保持当前 `test_campaign_results.py` 的防御性策略：摘要缺失判定为空，超大载荷截断并标记，路径做长度和越界校验，证据清单可反查活动与轮次。

### 6. 兼容与灰度

新增表全部为增量迁移，不改既有列语义。开关 `ORCHESTRATION_V2_ENABLED` 默认关闭；关闭时创建任务走现有路径，并生成一个单步骤的 legacy 实例以便查询口径一致。开启后按任务类别选择模板。`wake-recognition` 作为第一个注册场景，版本 1，参数与当前行为对齐。

## Risks / Trade-offs

- [模板 JSONB 过度灵活导致校验遗漏] → 发布时强制 Schema 校验并跑一组模板契约测试，运行期只接受已发布版本。
- [编排推进依赖 supervisor 循环，长步骤会拖慢领取] → 步骤内部只做编排决策，实际 skill 调用异步化并回写，循环保持短事务。
- [知识提炼阻塞归档引起积压] → 提炼失败可重试且允许授权人写人工结论，归档不被无限期卡住。
- [场景资产与节点实际文件漂移] → 校验值核验失败即 `BLOCKED`，并在活动上保留期望值与实际值。
- [历史活动只有字符串场景] → 回填时把已知字符串映射到注册场景，未知值保留为 legacy 且不参与新判定。
- [新增调用记录表带来写入放大] → 调用记录按任务保留，输出只存摘要，原文进证据存储。

## Migration Plan

1. 迁移新增六组表与两个外键列，全部可空或带默认值，先不影响旧路径。
2. 注册 `wake-recognition` 场景版本 1 与基础 skill 条目，作为灰度数据。
3. 回填历史活动的场景映射，未识别的保持 legacy。
4. 开启开关做单任务灰度，验证编排实例、调用记录、提炼记录三类数据齐全。
5. 回滚方式：关闭开关即回到现有创建路径，新增表保留不删，已产生的记录只读。
