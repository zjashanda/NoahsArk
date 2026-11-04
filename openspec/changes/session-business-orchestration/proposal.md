## Why

创建任务之后，平台目前只有一条固定路径：建任务、起一个 opencode 会话、把 prompt 交给 supervisor。任务属于哪个业务域、中间该调用哪些 skill、失败后重试还是停、收尾该沉淀什么，全都没有平台侧的约定。结果是每来一个业务域就得改一次代码，而已经跑过的 TCL 任务也没有留下可复用的知识条目和场景脚本。

## What Changes

- 新增任务创建后的会话编排层：按任务类别选择工作流模板，按定义好的步骤顺序推进，并在指定步骤触发 skill。语音交互、TCL 硬件测试、平台运维等类别各有自己的流程，不再共用一条硬编码链路。
- 新增 skill 注册与调度契约：平台能发现 skill、校验前置条件、发起调用、收取证据与结果、按策略处理失败/重试/停止。单个业务流不得内联写死某一个 skill 的调用逻辑。
- 新增任务收尾的知识提炼：终态任务关闭前必须产出知识候选，包含来源链、去重结果、审核状态和与任务/证据的关联；没有可复用知识时必须记录显式的空结论理由，不能静默跳过。当前单个任务确实没有产生知识条目，这一缺口在本变更中被明确补上。
- 新增 TCL 可复用测试场景框架：场景以注册表形式定义，包含资产、前置检查、执行脚本、结果适配器和判定规则。后续测试只需触发一个测试活动即可复用既有场景，不再为每次运行临时拼脚本。
- 明确承认当前缺口：没有编排注册表，没有收尾知识提炼，TCL runner 只有 wake-recognition 一个场景，也没有通用场景框架。本变更只做规划与规范，不改应用代码。

## Capabilities

### New Capabilities

- `task-workflow-orchestration`: 任务创建后的业务域识别、工作流模板选择、步骤顺序、skill 触发点、状态推进与终止条件。
- `skill-dispatch-registry`: skill 的注册、发现、前置条件校验、调用、证据采集、失败分类与重试/停止策略，以及与编排步骤的绑定契约。
- `knowledge-closeout-distillation`: 任务收尾时的知识提炼，涵盖候选生成、来源与证据关联、去重、人工审核门槛和空结论理由。
- `reusable-test-scenario-framework`: 可复用测试场景的注册表、资产与前置检查、执行适配、结果解析、判定规则和证据上传。

### Modified Capabilities

无。当前 `openspec/specs/` 下没有已存在的主 spec，本变更新增上述四个能力，不修改既有能力需求。

## Impact

- 影响 `apps/control_plane/noahsark/services/supervision.py`（任务与 supervisor 会话创建路径）和 `apps/control_plane/noahsark/services/supervisor.py`（派发与轮询）。
- 影响 `apps/control_plane/noahsark/services/knowledge.py` 与 `models/evidence.py`（候选生成入口，现只有人工晋升）。
- 影响 `apps/control_plane/noahsark/services/test_campaigns.py`、`test_campaign_results.py`、`models/test_campaign.py` 与 `apps/node_agent/noahsark_node/tools.py`（当前只接受 `wake-recognition`）。
- 需要新增编排定义、skill 注册、场景注册的数据表与迁移，以及对外的只读查询接口。
- 不引入第二套工作流引擎，不复制凭据到节点，不自动晋升知识，不把 dry-run 结果当完成证据。
- 本变更只产出 OpenSpec 规划产物，不修改应用代码，不触碰 `docs/index-tts` 与任何密钥。
