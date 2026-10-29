# P3-02 共享文件所有权与合并顺序证据

> 状态：DRAFT · 评审输入，不是冻结件
> 归属：`docs/delivery/phase3-construction-plan.md` §6、`phase5-implementation-plan.md` §5.2 的 P3-02 项
> 输入：`phase3-construction-plan.md` §4/§6、`phase5-implementation-plan.md` §3/§5、当前仓库树
> 边界：本文只定义单写者、合并序与冲突协议，不改代码、契约、设计、迁移、计划文件，不声称 P3-07 已冻结。文中“owner”指合并裁决角色，不等于唯一作者。

## 0. 判读规则与当前事实

1. 角色代号沿用施工方案 §4.0：R-ARCH、R-CON、R-BE、R-NODE、R-FE、R-QA、R-OPS、R-SEC、R-REV、R-PM。
2. “写入波次”指可直接修改文件的波次；“只读/申请波次”只能读、调用、提变更申请，不能直接改。
3. 当前仓库仍处于 W0 之前：根 `pyproject.toml`、`uv.lock`、`apps/web/**`、`apps/node_agent/**`、`packages/contracts/**` 均不存在；已有 `apps/control_plane/**` 纵向切片与 `design/ui-app/**` 候选 UI。
4. 当前已有 35 个 JSON Schema、39 条 UI 路由、16 个 API 模块、3 个迁移 revision；迁移链为 `3c118019b042 -> c240583c8a27 -> 7f3d2b91c4a5`，只有一个 head。
5. `services/read_models.py` 为 2569 行跨域读模型，`services/writes.py` 为 740 行写入服务，均未在施工方案 §6 逐文件点名，本文补上唯一 owner。
6. 本文的“通过”是文档一致性检查结论，不是构建、迁移或 UI 运行结果。

## 1. 共享文件清单与唯一 owner

| 共享文件或目录 | 当前事实 | 唯一 owner | 合并序 | 写入波次 | 只读/申请波次 | 规则 |
|---|---|---|---|---|---|---|
| `docs/contracts/**`（5 份契约文档、35 个 schema） | `frozen-candidate v1.1`，未独立验证 | R-CON | 1.5 | Phase 0 已写；此后仅 R-CON 写 | W1 至 W8 只读或申请 | 只生成不手改；字段、路由、错误码变更必须走契约变更记录 |
| 根 `pyproject.toml`、`uv.lock`、Python 版本文件 | 当前不存在，仅有 `apps/control_plane/pyproject.toml` | R-ARCH | 1 | W0 | 全部后续波次申请 | 锁文件只由 W0 串行改；其他波次提依赖申请，不直接编辑 |
| `apps/control_plane/migrations/**` | 3 个 revision，单 head | R-BE | 2、3、4 | W1 初始、W2 `c240`、W3 `7f3` 各写自己的 revision | W4 至 W8 申请 | R-BE 持有目录锁；已应用迁移永不编辑；revision 单调；合并前 `alembic heads` 必须只有一个 |
| `apps/control_plane/noahsark/main.py` | 63 行，已注册 14 组 router | R-BE | 1，后续 2、3、4、7 | W0 建根；W1 至 W4、W7 经 R-BE 注册 | W5、W6、W8 只读 | 组合根只由 R-BE 改；其他波次提交 router 注册请求，不直接改文件 |
| `apps/control_plane/noahsark/services/read_models.py` | 2569 行，跨 W1 至 W4 投影 | R-BE（W4 托管） | 5 | W4 | W1 至 W3 申请扩展；W6、W7 只读 | W3 退出后只允许 W4 写；UI 只消费读模型，不推导权威状态 |
| `apps/control_plane/noahsark/services/writes.py` | 740 行，W3 写入守卫 | R-BE（W3 托管） | 4 | W3 | W1、W2、W7 只读 | 状态机、幂等、审计只在此模块写；其他波次只调用用例 |
| `apps/web/src/shell.js`、`router.js`、`app.js`（目标路径，当前不存在） | 当前无 `apps/web` | R-FE | 6 | W6 | W7 只读 | 生产 UI 唯一入口；路由与壳层只由 W6 改；W7 只接线 |
| `design/ui-app/src/shell.js`、`router.js`、`app.js` | 候选原型，210/69/415 行 | P1 设计所有者 | 0 | P1 | W6 只读 | 候选不是冻结件；W6 不得把候选直接当生产 UI 改写 |
| `apps/web/styles/tokens.css`（目标路径，当前不存在） | 当前无生产令牌文件 | R-FE | 6 | W6 | W7 只读 | 生产令牌唯一入口；不得出现裸色值 |
| `design/design-tokens.json`、`design/apple/design-tokens.json`、`design/ui-app/styles/tokens.css` | 321/256/125 行，三份候选令牌 | P1 设计所有者 | 0 | P1 | W6 只读 | W6 发现缺令牌先提变更，不得硬编码或私建第二套令牌 |
| `.omo/plans/**` | 执行计划、backlog、进度计划 | R-PM | 永不 | 仅 R-PM | 全部波次只读 | 实施代理只读；不得在任务中改计划或勾选主计划 |
| `docs/delivery/construction-progress.md` | 102 行，已有历史记录 | R-PM | 每单元即时 | R-PM | 其他角色只读 | 只追加，不批量补记，不覆盖历史；同一时刻只允许一个写入者 |
| `docs/delivery/evidence/**` | `p3-01-wbs.md` 已存在 | R-QA | 每波 | 各波写自己的子目录，R-QA 复核 | 跨波只读 | 不跨波写；不写敏感原文；文件名与任务 ID 对应 |
| `docs/delivery/phase3-construction-plan.md`、`phase5-implementation-plan.md` | 均为 DRAFT | R-PM | P3-07、P4-08 | R-PM | 全部波次只读 | 实施代理只读；方案变更走版本记录与主控批准 |

## 2. 波次并发写入矩阵

| 波次 | 共享文件写入者 | 写入的共享文件 | 并发检查 |
|---|---|---|---|
| W0 | R-ARCH、R-BE、R-OPS | 根锁文件、`main.py`、迁移基线、CI 配置 | 每个文件只有一个 owner，通过 |
| W1 | R-BE | 迁移 revision、`main.py` 注册 | 无第二写者，通过 |
| W2 | R-BE | 迁移 revision、`main.py` 注册 | 与 W1 串行，通过 |
| W3 | R-BE | 迁移 revision、`services/writes.py`、`main.py` 注册 | 与 W2 串行，通过 |
| W4 | R-BE | `services/read_models.py`、`main.py` 注册 | 与 W5 目录不重叠，通过 |
| W5 | R-NODE | `apps/node_agent/**`，不写控制面共享文件 | 与 W4 并行无冲突，通过 |
| W6 | R-FE | `apps/web/**` 壳层、路由、应用、令牌 | 必须在 W4 读模型稳定后开始，通过 |
| W7 | R-BE、R-OPS | `main.py` 最终注册、部署与恢复文件 | 只接线，不改各波内部实现，通过 |
| W8 | R-BE、R-NODE | 适配器目录；契约只提案 | 不直接改 `docs/contracts/**`，通过 |
| W9 | R-QA、R-PM | 证据、进度、验收包 | 只追加，通过 |
| W10 | R-PM、R-QA | 归档、进度、发布包 | 只追加，通过 |

结论：按目标路径，W4 与 W5 是唯一允许并行的实现波次，目录不重叠；W2 与 W3 可以并行设计，但迁移和 `main.py` 合并必须串行；W6 晚于 W4；W7 晚于 W2、W4、W5、W6；W8 晚于 W7。

## 3. 合并顺序与冲突协议

### 3.1 合并列车

`P1 设计冻结 -> 契约 v1.1 冻结 -> W0 基座 -> W1 -> W2 -> W3 -> W4 与 W5 -> W6 -> W7 -> W8 -> W9 -> W10`

1. 契约与 W0 先合，消费方后合；契约未合前，W1 至 W8 只能做接口草案。
2. 迁移串行合并，数据库始终只有一个迁移头；任何时刻只允许一个迁移分支处于待合并状态。
3. W4 与 W5 可并行，因为 `apps/control_plane/**` 与 `apps/node_agent/**` 不重叠；共享锁文件变更必须回到 W0 owner 串行处理。
4. W6 在 W4 读模型稳定后合并，避免前端追着接口改。
5. W7 最后合并平台核心，只做接线；W8 在 W7 后合并，TCL 适配不得反向污染核心契约。
6. W9、W10 只追加证据、归档、发布文件，不改业务模块。

### 3.2 合并执行人

| 场景 | 合并执行人 | 复核人 | 说明 |
|---|---|---|---|
| 契约与生成客户端 | R-CON | R-ARCH、R-REV | 变更记录与 schema 校验齐全才合并 |
| W0 根锁文件、CI、组合根 | R-ARCH | R-OPS、R-QA | 其他波次不得代合 |
| W1 至 W4 控制面 | 对应波次 R-BE owner | R-REV | 共享文件由 owner 统一提交 |
| W5 节点代理 | R-NODE | R-SEC | 不合并控制面内部文件 |
| W6 UI | R-FE | R-QA | 令牌、壳层、路由一次只合一个主题 |
| W7 集成 | R-ARCH | R-BE、R-OPS、R-SEC | 只接线，不重写各波实现 |
| W8 TCL 适配 | R-BE 或 R-NODE 按目录 | R-QA | 不修改核心契约 |
| W9、W10 归档与发布 | R-PM | R-QA、R-REV | 发布授权单独记录 |

### 3.3 冲突协议

1. 冲突即停止合并，由该文件唯一 owner 裁决；不允许“先合再修”，不允许非 owner 在共享文件上解冲突。
2. 冲突方先在自己的分支完成 rebase，目标分支为当前集成头；rebase 后重跑该波质量门命令和受影响的 T1/T2 测试。
3. rebase 只允许在未合并的个人分支进行；已经合并到集成分支的提交不改写历史。
4. 迁移冲突不得通过编辑已应用 revision 解决；若出现两个 head，由 R-BE 重新指定 `down_revision`、重建 revision id，并证明 `alembic heads` 只有一个。
5. 契约冲突由 R-CON 先合契约，消费方再 rebase；消费方不得用本地字段猜测绕过契约。
6. UI 共享文件冲突由 R-FE 裁决；W6 适配层与页面不得同时修改，先合适配层，再合页面。
7. 冲突解决后必须由非实现者 R-REV 复核冲突处，不能只跑一次全量测试就宣布通过。

## 4. 检查结果

| 检查 | 方法 | 结果 |
|---|---|---|
| 每个共享文件只有一个 owner 角色 | 逐行核对 §1 表，共 14 个条目 | 目标状态通过；UI 生产路径为条件 owner，见 G1 |
| 同一波次没有两个共享文件写者 | 核对 §2 矩阵的写入者与文件集合 | 通过；W4 与 W5 目录不重叠，其余波次串行 |
| 每个共享文件都有合并序 | 核对 §1 合并序列 | 通过；计划文件为“永不”，其余有序号 |
| 没有孤儿共享文件 | 将 §1 与施工方案 §5.2、当前仓库树双向核对 | 目标状态通过；实际候选 UI 与令牌存在多源，见 G2 |
| 迁移单头 | 读取 3 个 revision 的 `revision` 与 `down_revision` | 通过；`3c -> c240 -> 7f3` 单链 |
| 计划与进度文件只读 | 核对 `.omo/plans/**` 与进度表 owner | 通过；仅 R-PM 可写 |
| 证据按波隔离 | 核对 `docs/delivery/evidence/**` 归属 | 通过；跨波只读 |

## 5. 阻碍 P3-07 的缺口

| # | 缺口 | 证据 | 对 P3-07 的影响 | 解除条件 |
|---|---|---|---|---|
| G1 | P2-05 与 G-UI 未决，生产 UI 路径、构建链和状态方案未定 | `phase5-implementation-plan.md` §4.3；当前无 `apps/web` | W6 的文件 owner 只能写成条件路径，无法冻结具体文件清单 | P2-05 决策关闭并确认 `apps/web` 或替代目录 |
| G2 | 候选 UI 与令牌存在多源：`design/ui-app`、`design/ui-demos`、`design/ui-prototype.html`、`design/apple/ui-prototype.html`，以及三份令牌文件 | 当前仓库树 | 可能同时维护两套 UI，违反施工方案 §6 的单 UI 规则 | P1 指定唯一候选源与唯一令牌源，其余标记只读或归档 |
| G3 | `main.py` 是单点热文件，已注册 14 组 router，W1 至 W4 各自加路由会持续冲突 | `main.py` 63 行；16 个 API 模块 | 组合根没有注册表隔离，单写者规则只能靠人工串行 | W0 改为注册表或路由清单机制，或明确 R-BE 逐波合并窗口 |
| G4 | `services/read_models.py` 与 `services/writes.py` 未在施工方案 §6 逐文件定义 owner | 两文件 2569/740 行；§6 只列模块目录 | P3-02 的“唯一 owner”无法直接引用现有条款 | 在 P3-07 前把本文的 R-BE 托管规则写入施工方案 §6 |
| G5 | 施工方案 §6 写“W1、W2、W3 各自迁移所有者”，与“共享目录唯一 owner”存在口径冲突 | 施工方案 §6；3 个迁移 revision | 迁移目录可能被三个角色同时视为自己可写 | 冻结为“R-BE 持目录锁，W1/W2/W3 只写各自 revision” |
| G6 | 契约 v1.1 尚无独立验证报告 | `p3-01-wbs.md` G9；`docs/contracts/README.md` 仍为候选 | R-CON 的契约冻结不能成立，W1 至 W5 只能做草案 | 契约逐项验证通过并由非契约作者复核 |
| G7 | 根锁文件、CI、`packages/contracts/**`、`apps/node_agent/**` 当前不存在 | 当前仓库树 | 目标 owner 表只能作为 W0 计划，无法与现有文件逐一校验 | W0 建立路径后回填实际文件与 owner |
| G8 | 进度表与证据目录的“只追加”没有机械约束 | `construction-progress.md` 102 行；无并发写检查 | 多代理同时更新可能覆盖历史，证据归属失真 | R-PM 串行写入，或增加追加校验与冲突检测 |

说明：以上缺口不改变本文的单写者结论，但在 G1、G2、G3、G5 关闭前，P3-07 不得声称共享文件所有权已冻结。

## 6. 复算与变更记录

- 共享文件条目：§1 共 14 行；owner 覆盖 R-CON、R-ARCH、R-BE、R-FE、R-PM、R-QA，设计候选文件由 P1 设计所有者托管。
- 迁移复算：`3c118019b042` 的 `down_revision = None`；`c240583c8a27` 指向 `3c118019b042`；`7f3d2b91c4a5` 指向 `c240583c8a27`。
- 行数与路径来自 2026-10-29 当前工作树；W0 建立目标路径后必须重算。
- 变更记录：v0.1（2026-10-29）建立共享文件清单、唯一 owner、波次矩阵、合并与冲突协议、检查结果和 P3-07 缺口；未修改任何代码、契约、设计、迁移或计划文件。
