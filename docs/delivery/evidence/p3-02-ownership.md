# P3-02 共享文件所有权与合并顺序证据

> 状态：DRAFT · 评审输入，不是冻结件
> 归属：`docs/delivery/phase3-construction-plan.md` §6
> 输入：Phase 3/5 方案、当前仓库树、Phase 2 实际文件布局
> 边界：本文只定义所有权与合并顺序，不写业务代码，不声称 P3-07 冻结。

## 1. 共享文件清单与 owner

| 共享文件/目录 | owner 角色 | 触达波次 | 说明 |
|---|---|---|---|
| `docs/contracts/**` | 契约 owner | P2 决策、P3、P5-W1/W2 | 只允许契约变更单点写入；不得由 UI/实现 Agent 顺手改 |
| `.omo/plans/noahsark-platform-delivery.md` | 计划 owner | 全程 | 勾选与映射由编排者维护 |
| `.omo/plans/phase3-6-execution.md` | 计划 owner | P3–P6 | 任务勾选、NEXT_TASK、BLOCKED |
| `docs/delivery/phase3-construction-plan.md` | 文档 owner | P3-01..P3-07 | P3-07 冻结前可改 |
| `docs/delivery/phase4-acceptance-plan.md` | 文档 owner | P4-01..P4-08 | P4-08 冻结前可改 |
| `docs/delivery/phase5-implementation-plan.md` | 文档 owner | P5 | 与施工进度同步 |
| `docs/delivery/phase6-acceptance-plan.md` | 文档 owner | P6 | 验收执行前可改 |
| `apps/control_plane/pyproject.toml` | 工具链 owner | P5-W0 | 依赖与版本锁定 |
| `apps/control_plane/alembic.ini` / `migrations/**` | DB owner | P5-W1..W4 | 迁移单点写入；禁止并行迁移 |
| `apps/control_plane/noahsark/models/**` | DB owner | P5-W1..W4 | 领域模型；改动需迁移 |
| `apps/control_plane/noahsark/main.py` | API owner | P5-W1..W8 | 路由挂载单点 |
| `apps/control_plane/noahsark/api/deps.py` / `envelope.py` | API owner | P5-W1..W8 | 鉴权、错误、响应包 |
| `apps/control_plane/noahsark/services/read_models.py` | API owner | P5-W2..W4 | 读投影 |
| `apps/control_plane/noahsark/services/writes.py` | API owner | P5-W3..W4 | 写意图与状态机 |
| `apps/control_plane/noahsark/seed.py` | DB owner | P5-W0..W4 | 确定性 seed |
| `design/ui-app/index.html` | UI owner | P5-W7 | 入口单点 |
| `design/ui-app/src/app.js` | UI owner | P5-W7 | 应用引导/路由/数据源 |
| `design/ui-app/src/shell.js` | UI owner | P5-W7 | 外壳、导航、演示控制 |
| `design/ui-app/src/router.js` | UI owner | P5-W7 | 39 路由单点 |
| `design/ui-app/src/api.js` / `api-adapter.js` / `data-source.js` | UI owner | P5-W7 | API 客户端与映射 |
| `design/ui-app/styles/**` | UI owner | P5-W7 | 设计令牌与组件样式 |
| `design/ui-app/src/pages/*.js` | UI owner（可按 family 并行） | P5-W7 | 每个 family 单写入 |
| `scripts/sync-cloud.sh` | 发布 owner | 全程 | 提交/推送策略 |
| `plan.md` | 计划 owner | 全程 | 进度记录，仓库忽略 |

## 2. 合并顺序

固定顺序，避免契约/迁移/路由互相踩踏：

```text
契约与计划
  → 迁移与模型
  → seed
  → services（read_models / writes）
  → API deps/envelope
  → routers + main.py
  → UI api/data-source
  → UI shell/router/app
  → UI pages（按 family 可并行，但共享文件不并行）
  → 文档与证据
  → sync-cloud
```

规则：

1. 同一波次内，`migrations/**`、`models/**`、`main.py`、`services/*`、`app.js`、`shell.js`、`router.js` 各自最多一个写入者。
2. 页面 family 可并行，但不得同时改 `components.js`、`icons.js`、`styles/**`。
3. 契约变更先于实现；实现不得反向修改契约来“适配”代码。
4. UI 适配层（`api.js`/`api-adapter.js`/`data-source.js`）先于页面接入。
5. 迁移先于 seed；seed 先于 API 测试；API 先于 UI API QA。
6. 文档证据最后写，不得先勾选后补证据。

## 3. 冲突处理

- worker 不合并、不 push 主分支；只提交自己的分支/工作区。
- 编排者负责决定 landing 顺序；后合并方先 rebase 到最新 `main`。
- 冲突解决后必须重跑该波测试；不通过不得标记完成。
- 禁止 `git reset --hard`、`git checkout --`、force push。
- 迁移冲突不得靠删除迁移解决；必须新增前向修复迁移。

## 4. 检查结果

- 共享文件均有唯一 owner。
- 同一波次未发现两个并发写入者。
- 未发现无 owner 的孤儿共享文件。
- 合并顺序无环：契约→迁移→seed→services→API→UI→文档。
- 唯一例外：页面 family 并行，但共享 UI 文件仍单写入。

## 5. 阻塞 P3-07 的缺口

1. Phase 3 施工方案中的 WBS 仍需与 66 项主计划逐项对齐（P3-04）。
2. 工具链精确版本与前端 P2-05 仍待 ADR（P3-03）。
3. 质量门命令与证据命名需最终确认（P3-05）。
4. 风险/回滚矩阵需覆盖认证、证据存储、部署、Node Agent、TCL（P3-06）。
