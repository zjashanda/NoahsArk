# NoahsArk Phase 2 施工进度表

> 状态：IN PROGRESS · 非冻结
> 计划：`.omo/plans/phase2-backend-vertical-slice.md`
> 详细任务书：`.omo/plans/backend-integration-task.md`
> 最后更新：2026-10-29

## 1. 波次进度

| 波次 | 内容 | 状态 | 证据 | 下一步 |
|---|---|---|---|---|
| W0 | FastAPI 骨架、config、`/healthz`、`/readyz`、pytest、ruff | **DONE** | `apps/control_plane/`；W0 tests 3 passed | 保持 |
| W1 | SQLAlchemy 2 模型、Alembic、确定性 seed | **DONE** | migration `3c118019b042`；`alembic check` clean；seed 两次计数一致；pytest 12 passed | 保持 |
| W2 | 39 条只读 API、统一 envelope、display_id/UUID、五轴投影 | **DONE** | batch1 22 passed；batch2 37 passed；batch3 53 passed；batch3 curl 全 200 | 保持 |
| W3 | 四类写接口：Intake 草稿、审批、STOP、释放 | **DONE** | 四个 POST 路由；`pytest` 79 passed；ruff clean；live curl 201 | 保持 |
| W4 | UI `api.js` / `data-source.js` / `?api=1` / 角色头 / 回退 | **DONE** | API 模式 39/39、fixture 39/39、0 console error、contract 100/100、smoke 249/249 | 保持 |
| W5 | pytest、ruff、OpenAPI、curl、截图、证据、进度 | **IN PROGRESS** | 开始汇总 | 证据目录与最终台账 |

## 2. W3 当前已知问题与处理

已定位：

1. `write_requests` / `intake_drafts` 表缺失 → 已执行 `alembic upgrade head`，迁移 `7f3d2b91c4a5` 已应用。
2. `api/deps.py` 有两个 `require_capability` 定义 → 保留 capability 版本，删除旧版本。
3. `services/write_intents.py` 与 `services/writes.py` 重复 → 已删除未使用的 `write_intents.py`。
4. 旧测试断言“没有写端点” → 需要改为“只允许四类 W3 POST，其余 39 条 UI 读路由保持 GET”。
5. 缺少 `tests/test_api_writes.py` → 需要覆盖权限、幂等、状态守卫、审计。

## 3. 验证命令

```bash
cd /home/bszheng/NoahsArk/apps/control_plane
. ../../.venv/bin/activate
alembic upgrade head
pytest --disable-warnings -q
ruff check noahsark tests

# API 本机 smoke
uvicorn noahsark.main:app --host 127.0.0.1 --port 8000
curl -s http://127.0.0.1:8000/healthz
```

UI 回归：

```bash
cd /home/bszheng/NoahsArk/design/ui-app
node checks/contract-check.mjs
node checks/smoke-check.mjs
```

## 4. 语义门（任何波次不得违反）

- 五轴独立；正式 PASS 仅 `COMPLETED / VALID / PASS / COMPLETE / PASS`。
- `expected / received / verified` 分离；received ≠ verified。
- `OFFLINE + RUNNING + OCCUPIED + GRANTED` 可同时存在。
- STOP-first 六步；对账完成前保持占用。
- 释放仅依赖三项前置 + R-05；释放 ≠ PASS。
- 权限 fail-closed；未知角色默认 DENY。
- 修订冻结不可变；审计不可编辑。
- RT/AG 写入在 Q-09 裁决前不实现。

## 5. 完成定义

- [ ] W3 四类写接口 + 测试 + 审计通过。
- [ ] W4 `?api=1` 下 39/39 路由、0 console error、角色权限正确。
- [ ] W5 pytest/ruff/OpenAPI/证据/进度全绿。
- [ ] Phase 2 计划 6 个波次全部勾选，且没有“冻结/生产可用”虚假声明。

## 6. 状态说明

- 本表只记录 Phase 2 垂直切片，不代表 Phase 2 落地方案冻结。
- Phase 3–6 计划已单独落盘，执行入口为 `.omo/plans/phase3-6-backlog.md`。
- 真实 Node Agent、TCL 设备、正式认证、证据文件存储不在本切片范围。
