## 1. 数据模型与迁移

- [ ] 1.1 在 `models/orchestration.py` 新增 `workflow_templates`、`workflow_template_versions`、`workflow_steps`、`workflow_skill_bindings` 四张表，字段覆盖设计第 1 节，并为模板标识与版本建立唯一约束
- [ ] 1.2 在同一模块新增 `orchestration_instances`、`step_executions`，实例关联 `task_id`、`task_revision_id`、模板版本，并加“同任务仅一个活动实例”的部分唯一索引
- [ ] 1.3 在 `models/skill.py` 新增 `skill_registrations`、`skill_invocations`，包含输入输出 Schema、前置条件、超时、重试策略、幂等标记和证据引用
- [ ] 1.4 在 `models/knowledge.py` 或 `models/evidence.py` 新增 `knowledge_extraction_runs`，包含任务、状态、理由码、候选引用、失败摘要、重试次数
- [ ] 1.5 在 `models/test_campaign.py` 新增 `test_scenarios` 表，并给 `test_campaigns` 增加可空 `scenario_id`、`scenario_version` 外键列，保留原 `scenario` 字符串列
- [ ] 1.6 编写 Alembic 迁移，全部为增量操作，含索引与外键，验证向前迁移和回滚都能在空库与现有库上执行

## 2. 编排定义与实例核心

- [ ] 2.1 新建 `services/workflow_templates.py`，实现模板创建、版本发布、弃用和引用完整性校验，校验失败返回缺失或非法步骤清单
- [ ] 2.2 实现模板解释器：按版本快照求值步骤进入与退出条件，输出下一可执行步骤，覆盖 `PENDING/READY/RUNNING/SUCCEEDED/FAILED/SKIPPED/BLOCKED` 迁移
- [ ] 2.3 新建 `services/orchestration.py`，实现实例创建、按任务类别选择模板、手动改派类别，并在无法识别类别时置 `AWAITING_CLASSIFICATION`
- [ ] 2.4 在 `services/supervision.py` 的 `create_task_with_supervisor` 中接入实例创建，受 `ORCHESTRATION_V2_ENABLED` 控制，关闭时生成单步骤 legacy 实例
- [ ] 2.5 在 `services/supervisor.py` 的领取与轮询路径接入步骤推进，保证步骤决策保持短事务，状态迁移写审计事件
- [ ] 2.6 实现暂停、恢复、终止：暂停在安全点生效，终止先跑清理再进终态，终态拒绝恢复，全部记录请求人、原因、时间
- [ ] 2.7 实现只读查询接口，返回当前步骤、步骤状态列表、skill 调用摘要和证据引用，事件回放按时间排序且脱敏

## 3. skill 注册与调度

- [ ] 3.1 新建 `services/skills.py`，实现注册、按域与能力发现、版本弃用，拒绝缺输入或输出契约的注册
- [ ] 3.2 实现前置条件求值器，覆盖运行环境、节点能力、资源租约、操作权限，不满足时记录 `PRECHECK_FAILED` 且不发起调用
- [ ] 3.3 实现统一调度接口 `precheck -> invoke -> classify -> record`，节点类 skill 走 `node_commands`，平台类 skill 在进程内执行但写同样的调用记录
- [ ] 3.4 实现不可信输出处理：大小上限、脱敏、截断标记，证据引用必须能反查调用标识
- [ ] 3.5 实现失败分类与重试：仅 `TRANSIENT` 在声明上限内按退避重试，`PERMANENT`、`PRECHECK_FAILED` 不重试，非幂等缺幂等键直接拒绝
- [ ] 3.6 实现超时与取消传播，超时触发已声明清理，取消后部分输出只作证据保留
- [ ] 3.7 在模板发布校验中检查 skill 绑定，引用不存在或已弃用版本时拒绝发布

## 4. 收尾知识提炼

- [ ] 4.1 新建 `services/knowledge_closeout.py`，任务终态后创建 `knowledge_extraction_runs` 并执行一次提炼
- [ ] 4.2 实现候选写入，强制校验标题、类型、适用边界、结论、步骤、风险、证据引用与来源链，缺适用边界直接判不合格
- [ ] 4.3 实现来源链校验：候选必须关联来源任务、执行或尝试记录、可反查证据，仅有会话文本时标记证据不足
- [ ] 4.4 实现确定性去重，写入 `duplicate_of` 并记录相似度，命中时按合并或新增版本处理，不改写历史
- [ ] 4.5 实现空结论路径：写入 `no_reusable_knowledge` 理由码、判断人与时间，验证此时归档检查通过
- [ ] 4.6 实现提炼失败语义：标 `FAILED` 并阻塞归档，提供重试和授权人人工结论入口，人工结论保存操作人与理由
- [ ] 4.7 在归档前置检查加入提炼 gate：无成功提炼记录或无人工结论时拒绝归档
- [ ] 4.8 实现场景关联：执行过注册场景的候选写入场景标识与版本，可按场景检索

## 5. 测试场景框架

- [ ] 5.1 新建 `services/test_scenarios.py`，实现场景注册、版本发布、弃用和契约完整性校验
- [ ] 5.2 改造 `services/test_campaigns.py`，活动只接受场景标识加版本与合法参数，拒绝内联脚本路径，参数校验失败不下发
- [ ] 5.3 实现资产与前置检查，核对校验值、节点能力、设备与环境，不满足时活动置 `BLOCKED` 并返回未满足项
- [ ] 5.4 改造 `apps/node_agent/noahsark_node/tools.py`，移除硬编码 `TEST_RUN_SCENARIOS`，改为读取命令载荷中的场景清单与固定入口，并校验资产
- [ ] 5.5 定义节点执行协议：标准输入传 JSON 参数，标准输出返回 JSON 结果，退出码只表达进程结果，业务判定留在平台
- [ ] 5.6 将 `wake-recognition` 注册为场景版本 1，参数与现有行为对齐，并用 `test_campaign_results.py` 的防御性解析验证判定不变
- [ ] 5.7 在 `services/test_campaign_results.py` 按场景判定规则出结论，保持摘要缺失判定为空、超限截断、非法路径拒绝
- [ ] 5.8 实现场景证据清单，条目反查活动、轮次与场景版本，路径受长度与越界约束
- [ ] 5.9 用第二个最小场景验证扩展路径：只新增注册条目与适配实现，公共路径无需按场景分支

## 6. 集成、灰度与验证

- [ ] 6.1 为编排状态机、模板校验、前置条件求值补充单元测试，覆盖拒绝路径
- [ ] 6.2 为 skill 调度补充测试：重试上限、永久失败不重试、非幂等缺键、超时清理、脱敏
- [ ] 6.3 为知识提炼补充测试：完整候选、缺边界、证据不足、重复合并、空结论、提炼失败阻塞归档
- [ ] 6.4 为场景框架补充测试：参数非法、资产校验失败、只有产物路径不出 PASS、未知场景拒绝
- [ ] 6.5 跑一次端到端灰度：单任务走完整编排，验证实例、调用记录、提炼记录、场景活动四类数据齐全
- [ ] 6.6 验证开关关闭时创建任务仍走原路径且生成 legacy 实例，回滚步骤在预发环境演练一次
- [ ] 6.7 更新运维与接口文档，说明新增表、开关、只读接口和人工结论入口，不涉及 `docs/index-tts`
