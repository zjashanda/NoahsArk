# NoahsArk Phase 2 垂直切片证据

> 状态：**PROTOTYPE SLICE · NOT FROZEN · NOT PRODUCTION**
> 日期：2026-10-29
> 范围：`apps/control_plane/` + `design/ui-app/` 的真实 API 接入

## 结论

Phase 2 垂直切片已跑通：PostgreSQL 唯一库、39 条 UI 读路由（38 个 GET + IN-02 表单）、四类写接口、UI `?api=1` 真实数据模式。

这不是生产实现、验收报告或冻结件。真实 Node Agent、TCL 设备、证据文件存储、正式认证、部署与可观测性均未实现。

## 验证结果

| 项 | 结果 |
|---|---|
| Alembic | `alembic check` 无新增操作 |
| Seed | 连续两次计数一致：tasks 2 / runs 4 / evidence 5 / audit 5 |
| pytest | 79 passed |
| ruff | clean |
| OpenAPI | `/openapi.json` 可导出 |
| 读 API | 38/38 GET 返回 200 |
| 写 API | 创建草稿 201；同键重放 201；不同 payload 409；STOP 201；释放 409（缺 cleanup_receipt） |
| UI fixture | 39/39 路由，0 console error |
| UI API | 39/39 路由，0 console error，`server_authoritative=true` |
| UI 检查 | contract 100/100；smoke 249/249 |

## 文件

- `pytest.txt`、`ruff.txt`、`alembic-check.txt`
- `seed-1.txt`、`seed-2.txt`
- `openapi.json`
- `curl/health.json`、`curl/read-endpoints.txt`、`curl/write-endpoints.txt`、`curl/write-*.json`
- `screenshots/mc-api-1440.png`、`screenshots/mc-fixture-390.png`
- `ui-checks.txt`

## 复现

见 `commands.txt`，或 `.omo/plans/phase2-w5-brief.md`。

## 边界

- 数据来自 seed fixture，不代表真实执行。
- `server_authoritative=true` 只表示响应来自控制面读模型，不等于验收通过。
- 五轴、正式 PASS、证据三列、释放三前置、STOP-first、OFFLINE 语义必须继续保持。
- 未演练恢复不得声称 RPO/RTO。
