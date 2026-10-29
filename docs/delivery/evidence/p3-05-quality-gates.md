# P3-05 质量门与证据规范

> 状态：DRAFT · 评审输入，不是冻结件
> 归属：`docs/delivery/phase3-construction-plan.md` §8/§9/§15.1 的 P3-05 项；`.omo/plans/phase3-6-execution.md` 第 5 项
> 输入：`phase3-construction-plan.md` §4/§8/§9、`phase4-acceptance-plan.md` §3/§7/§9、`backend-slice-evidence/README.md`、`1.md` §6
> 边界：本文只定义测试层、证据层、每波 DoD、目录与判定口径；不执行任何测试，不产生 PASS，不改代码、契约、迁移、计划或勾选主计划。P3-07 仍为 NOT DONE。

## 0. 判读规则

1. 本文出现的命令是**目标命令**，不是已执行事实。W0 未交付根锁文件前，除 `apps/control_plane/` 现有命令外均不可直接运行。
2. 任一层级 PASS 只在其声明的 L 层内成立，不得跨层外推。
3. 只写角色代号，不写姓名、主机、IP、端口凭据、设备序列号。
4. T/L 口径以本文与 `phase4-acceptance-plan.md` §3 双向一致为准；两者冲突时以 P4-02 冻结件为正本、本文为施工侧引用，冲突本身登记为缺口。
5. 没有证据目录、没有可复算 manifest、没有独立评审签署，一律不得写 PASS。

## 1. T1 至 T6 测试层：边界与命令

| 层 | 证明对象 | 环境与真机 | 进入条件 | 最低覆盖 | 目标命令 | 证据层上限 |
|---|---|---|---|---|---|---|
| T1 单元 | 判定规则、状态机、分母、幂等键、权限函数 | 本地，无 DB，无真机 | 代码可导入，规则版本固定 | 每个不变量至少 1 个通过用例 + 1 个拒绝用例 | `uv run pytest tests/unit -q` | L0/L1 |
| T2 契约 | OpenAPI 3.1、JSON Schema、事件 envelope、Job/Lease/STOP/Receipt、manifest 形状、错误码 | 本地，假对象 | 契约候选可校验，生成器可跑 | 拒绝路径必须覆盖：未知 schema、未知枚举、越权、重复幂等键 | `uv run python -m tools.contract_check` + `uv run pytest tests/contract -q` | L1 |
| T3 集成 | 控制面模块与 PostgreSQL 协作、事务、唯一约束、租约与占用 | 本地多进程，真实 PostgreSQL 16 | T1/T2 通过，测试库可用 | 约束冲突、并发批准、迁移前向修复 | `uv run pytest -m integration -q` | L2 |
| T4 模拟 E2E | 假节点全链路、G0-G7 门禁、断线、STOP-first、重连对账、恢复 | 假节点，无真机 | T3 通过 | 正常链路 + 断线 + STOP + 重复送达 + 旧 epoch | `uv run pytest tests/e2e -q` | L2 |
| T5 真机烟测 | 节点、设备、端点、采集、清理链路 | 真实节点与 DUT | A-0 硬门通过，W8 前置满足 | 独立 `run_id` + `mode=smoke`，链路可跑通 | `uv run pytest tests/smoke -q --run-real-node` | L3 |
| T6 正式验收 | 正式样本、五轴、Linux 独立复核、报告 | 真实节点与 DUT | T5 通过，修订与样本阈值已批准 | 正式分母、逐 case 五轴、复核记录 | 按 `phase4-acceptance-plan.md` §8.3 第 5 至 7 步执行 | L4/L5 |

硬规则：

1. T5 与 T6 必须是不同 `run_id`；T5 样本永不进入 T6 分母。
2. T1 至 T4 证据只能支撑 L0 至 L2，不得用于声称 L3 至 L5。
3. 任何层发现 P0 缺陷即停止后续层，不以"跑完再修"替代阻断。
4. 每个层级必须包含失败用例；只跑 happy path 不算通过质量门。
5. 纵切已有 `apps/control_plane/tests/` 结果只作基线参考，不得替代任意 QG-W 门。

## 2. L0 至 L5 证据层：证明边界

| 层 | 证明什么 | 不证明什么 | 最低证据 | 典型门 |
|---|---|---|---|---|
| L0 | 文档、契约、口径一致 | 系统可运行 | 版本号、文件哈希、评审记录 | DG3、DG4 |
| L1 | 静态与契约自洽 | 模块协作 | lint、typecheck、schema 校验、T1/T2 报告 | QG-W0 至 QG-W4 |
| L2 | 模拟链路与判定逻辑正确 | 真实设备、真实时序 | T3/T4 报告、注入异常记录、假节点回执 | QG-W2、QG-W3、QG-W7 |
| L3 | 真实节点与设备链路可跑通 | 正式样本有效、正式 PASS | T5 独立 smoke run、端点快照、清理事实 | DG8、P6-03 |
| L4 | 正式样本与独立判定有效 | 其他设备、长期稳定 | 正式分母、五轴、manifest 复算、复核记录 | P6-04 |
| L5 | 业务闭环与知识可复用 | 跨项目泛化 | L4 全部 + 第二任务复用、报告、知识审阅 | P6-05 |

组合约束：`static` 只到 L1；`smoke` 最高 L3；`formal` 才可到 L4/L5。一个 `run_id` 只允许一个 `mode`，模式、层、级别不一致时判定直接 `BLOCKED`。

## 3. 每波 Definition of Done（W0 至 W10）

每波 DoD 至少含一条可执行命令；命令退出码非 0 即该波不得退出。命令中的路径为冻结后的目标路径，W0 之前的路径尚未创建。

| 波次 | DoD 要点（须全部有证据） | 至少一条可执行命令 | 门 | 失败处理 |
|---|---|---|---|---|
| W0 | 可安装、可构建、可启动；`/healthz` 与 `/readyz` 区分；空库迁移 up/down/up 通过；CI 跑 lint/typecheck/test/build/secret scan；无业务逻辑 | `uv sync --frozen && uv run ruff check . && uv run pytest -q && uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head` | QG-W0 | 停 W1/W5 |
| W1 | 身份与会话 fail-closed；RBAC 默认拒绝；冻结修订不可改动；唯一有效审批有数据库约束；G0/G1 顺序守卫；审计只追加 | `uv run pytest tests/domain/identity tests/domain/revision tests/domain/approval tests/domain/gate -q` | QG-W1 | 停 W2 |
| W2 | Run/Attempt 可创建且五轴不折叠；lease/epoch 阻断重复派发；离线不等于空闲；STOP 优先于排队；六步对账；假节点回放无重复执行；投影可重建 | `uv run pytest tests/orchestration tests/e2e/test_fake_node_replay.py -q` | QG-W2 | 停 W3、W5 联调 |
| W3 | 证据内容寻址；写入前复算 SHA-256；摘要不符转 `NEEDS_REVIEW`；manifest 期望/已接收/已核验三态；清理回执不污染证据状态；五轴 fail-closed；节点无权写判定 | `uv run pytest tests/evidence tests/verdict -q && uv run python -m tools.evidence_verify --manifest <manifest.json>` | QG-W3 | 停 W4 |
| W4 | 报告 14 章节齐全且缺失章节标 `EMPTY`；知识候选需人工审核不自动推广；TaskCard 有 freshness 与三种进度模式；投影重建零差异；读模型不写权威表 | `uv run pytest tests/projection tests/report -q --rebuild-compare` | QG-W4 | 停 W6/W7 |
| W5 | 可安装为服务；helper 在活动会话执行；工件验签拒绝篡改；spool 先落盘后上传且有容量保护；断网 replay 幂等；STOP 与 cleanup receipt 可回传；无入站管理端口 | `uv run --project apps/node_agent pytest -q` | QG-W5 | 只用假节点 |
| W6 | 39 路由按冻结设计渲染；无裸色值；四档断点、键盘、焦点、减少动效通过；Playwright 截图与点击回归通过；控制台零错误 | `npx playwright test --project=chromium` | QG-W6 | 停 W7 |
| W7 | 三入口到审批、门禁、运行、证据、判定、报告闭环；断线、STOP、释放、控制面恢复各有证据；安全扫描、性能基线、可观测性、部署与回滚可重复 | `uv run pytest tests/integration tests/recovery -q` | QG-W7 | 停 W8/W9 |
| W8 | TCL001 绑定 COM3/COM4 与音频端点；COM5/COM7 不被打开；生成式 profile 通过 preflight；唤醒词用例可执行；只产 T5 候选 | `uv run pytest tests/adapters/tcl001 -q && uv run lstest preflight --profile <frozen-profile>` | QG-W8 | 停 T6 |
| W9 | 全量回归通过；evidence manifest 可复算；敏感扫描通过；P6 入口包完整；未完成项标 `BLOCKED` | `uv run pytest -q && uv run python -m tools.evidence_manifest_verify docs/delivery/evidence/phase3` | QG-W9 | 停 P6 |
| W10 | F1 至 F4 结论齐全；归档哈希可校验；发布包与回滚包可执行；发布授权单独记录 | `sha256sum -c <archive>/hashes.sha256` | QG-W10 | 不发布、不移交 |

命令成立条件说明：`uv`、`uv.lock`、`pyproject.toml`、`tools.*` 模块、`tests/**` 路径、`npx` 与 Playwright 配置、`lstest` 均可执行性由 W0/W5/W8 建立；未建立前该命令只能登记为计划命令。跨波共享命令（`pytest -q`、`ruff`）与既有纵切命令不得互相冒充证据。

## 4. 证据目录命名与保留

### 4.1 命名

施工阶段（W0 至 W10）：

`docs/delivery/evidence/phase3/<gate-id>/<wave-id>/<UTC-timestamp>-<short-ref>/`

验收阶段（P6 及以后）：

`docs/delivery/evidence/phase4/<level-id>/<ac-id>/<UTC-timestamp>-<short-ref>/`

- `<gate-id>` 取 `qg-w0` 至 `qg-w10`、`dg3`、`dg4`、`qg-p6`；`<wave-id>` 取 `w0` 至 `w10`；`<level-id>` 取 `l0` 至 `l5`。
- `<UTC-timestamp>` 形如 `20261029T071130Z`；`<short-ref>` 为任务 ID 或 run ID 去敏感后的短码，禁止项目名、设备序列号、人名。
- P3 阶段评审件本身（`p3-01-wbs.md` 等）为扁平文件，与波次运行证据分离，不得混放。

每个证据目录至少包含：`manifest.json`（gate、wave、item_id、命令、环境摘要、结果、reviewer、UTC 时间）、`commands.log`（命令与退出码）、`result.json`、`junit.xml`（无测试写 `N/A`）、`hashes.sha256`、`review.md`（独立评审结论与残余风险）、`redaction-check.txt`。

### 4.2 保留

| 对象 | 位置 | 保留 | 删除规则 |
|---|---|---|---|
| 评审件与 manifest 索引 | Git 仓库（已脱敏） | 随版本永久保留 | 不得删除，只能新增更正项 |
| 原始音频、原始串口、原始设备日志 | 受控证据存储，不进 Git | 热存 30 天后标 `archive_pending` | 未完成归档不得删除 |
| 访问与上传审计 | 受控证据存储 + 控制面审计表 | 随版本保留 | append-only，不可编辑 |
| 归档包 | 归档路径，哈希登记 | 随版本保留 | 校验失败即视为未归档 |

规则：内容寻址、写入前复算、已接受证据不可原地覆盖；更正另立新项并写 `supersedes`；云端同步只在敏感扫描通过、独立评审完成后进行。保留期限与存储后端依赖 ADR-006，未关闭前只能写"待定"，不得写具体天数承诺。

## 5. PASS / FAIL / BLOCKED 判定

| 判定 | 成立条件 | 不成立即不得使用 |
|---|---|---|
| PASS | 命令退出码为 0；该波 DoD 每项有对应证据；`manifest.json` 哈希可复算；独立 reviewer 签署且非本任务 owner；`redaction-check.txt` 无命中；无未关闭 P0；模式与层级一致 | 缺任一条件 |
| FAIL | 有证据表明被测行为不符合冻结预期，且输入与环境有效（`VALID`），失败可归因于产品 | 证据缺失、环境无效、无法复算 |
| BLOCKED | 前置未满足：DG 门未过、ADR 未关闭、A-0 未通过、契约冲突、必需证据缺失或摘要不符、未知枚举、`verification_status != PASS` | 用推测或"先做完再补"替代 |

补充规则：

1. 无证据不得写 PASS；"文档存在""代码已合并""本地手动试过"均不构成证据。
2. 证据摘要不可复算时，结论为 `BLOCKED`，不是 FAIL，也不是 PASS。
3. `execution_status`、`validity_status`、`business_verdict`、`evidence_status`、`verification_status` 任一非理想值即不得写正式 PASS。
4. `PASSED` 门禁不等于业务 PASS；设备释放成功不等于 PASS；PASS 也不要求设备已释放。
5. 只满足五轴而缺 `decision=PASS`、`formal_pass=true`、`failure_class=none` 或分母资格时，只能写"轴一致"。
6. 质量门失败仍继续合并，按 STOP 条件处理，本轮结论记为 `BLOCKED`。

## 6. 阻碍 P3-07 的缺口

| # | 缺口 | 影响 | 解除条件 |
|---|---|---|---|
| Q1 | 目标命令全部依赖 W0 产物（根 `pyproject.toml`、`uv.lock`、`tools.*`），当前不存在 | "可执行命令"目前是计划命令，QG 无法实测 | P3-07 明确接受"命令在 W0 首次校验"的延期决议，或 W0 前先建最小骨架 |
| Q2 | 证据目录 `docs/delivery/evidence/phase3/**` 无模板与历史基线（对应 p3-01 G10） | 波次 DoD 无法按 §4.1 落盘 | W0-07 交付模板，或 P3-07 附模板草案 |
| Q3 | 本文与 `phase4-acceptance-plan.md` §3 对 T/L 各写一份 | 双写漂移风险 | P3-07 声明 P3-05 为施工侧引用、P4-02 为验收正本 |
| Q4 | 波次编号在执行计划第 22 至 26 项与施工方案不一致（对应 p3-01 G6） | `<wave-id>` 与证据目录错配 | 以施工方案 §4 为准改写执行计划条目 |
| Q5 | ADR-001（pyright/mypy）、ADR-004（前端测试形态）、ADR-008（CI 与 secret scan 工具）全部 OPEN | 类型检查、Playwright、secret scan 命令无法定稿 | 逐条关闭或给出用户批准的延期决议 |
| Q6 | ADR-006（证据存储与保留）OPEN | §4.2 保留天数只能写"待定" | 关闭 ADR-006 或明确"待定可用" |
| Q7 | 覆盖率阈值、性能基线阈值未定 | W1 至 W7 的"最低覆盖"只能定性 | P3-07 给出定量阈值或声明不设全局阈值 |
| Q8 | 独立评审者未分配（对应 p3-01 G8） | PASS 的 reviewer 字段无法填写 | 主控在 W0 前完成角色分配 |
| Q9 | 纵切既有 pytest 79 passed 与平台 QG 无映射关系 | 存在被误当 QG 证据的风险 | 进度表按 `VS-` 前缀单独登记，禁止引用为 QG |

说明：A-0 未通过不阻断 P3-07 冻结，但阻断 W7 真实节点联调、W8、P6-03 至 P6-06 的 L3 至 L5 结论，必须保持登记为条件硬门。

## 7. 复算与变更记录

- 本文所有命令均为目标命令，未执行；所有 PASS 标准均为待评审口径，无任何层级被声称通过。
- 层级映射核对：T1/T2 至 L0/L1，T3/T4 至 L2，T5 至 L3，T6 至 L4/L5，与 `phase4-acceptance-plan.md` §3.1/§3.2 一致。
- 变更记录：v0.1（2026-10-29）建立 T1-T6/L0-L5 边界与命令、W0-W10 每波 DoD 与命令、证据目录与保留、PASS/FAIL/BLOCKED 口径、P3-07 缺口清单；未修改其他文件，未勾选主计划，未声称任何门通过。
