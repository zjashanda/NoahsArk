# P5-W0 基础与 CI 证据

> 状态：DONE（开发基线）· 非生产冻结
> 日期：2026-10-29
> 范围：`apps/control_plane/`、`.github/workflows/`、`scripts/`

## 交付

| 项 | 路径 | 说明 |
|---|---|---|
| mypy 配置 | `apps/control_plane/pyproject.toml` | `[tool.mypy]` + `pydantic.mypy` 插件，Python 3.12 |
| 依赖锁 | `apps/control_plane/requirements.lock` | `pip freeze`，42 行，不含 editable 项目行 |
| CI | `.github/workflows/backend-ci.yml` | Python 3.12 + PostgreSQL 16 service；迁移、seed、ruff、mypy、pytest、secret scan |
| 秘密扫描 | `scripts/secret-scan.sh` | 私钥、password/API key、长 Bearer、RFC1918 IPv4；排除 `.venv/.git/.env` |
| Makefile | `apps/control_plane/Makefile` | install/migrate/seed/api/test/lint/typecheck/secret-scan/ui-check |
| 类型修复 | `services/read_models.py`、`api/envelope.py`、`main.py` | Verdict 轴来源、可选 lease ID、Sequence、Starlette handler 签名 |

## 验证结果

```text
$ mypy noahsark
Success: no issues found in 38 source files

$ ruff check noahsark tests
All checks passed!

$ pytest --disable-warnings -q
79 passed

$ ./scripts/secret-scan.sh
secret scan: clean

$ python -c "yaml.safe_load(open('.github/workflows/backend-ci.yml'))"
ci-yaml-ok
```

## 边界

- CI 尚未在 GitHub Actions 实际运行；本地只验证了 YAML 与等价命令。
- 依赖锁为当前 venv 快照，不是完整 hash 锁；后续可换 `uv.lock`。
- 未改变五轴、证据、释放、STOP-first、权限 fail-closed 语义。

## 下一步

W1：身份/会话/RBAC/审计/Task/Revision 领域；先做 OIDC-ready 抽象 + 开发角色头，保持 fail-closed。
