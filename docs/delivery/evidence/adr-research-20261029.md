# ADR 联网核对记录（2026-10-29）

> 状态：RESEARCHED · ACCEPTED FOR V0.0.1 DEVELOPMENT BASELINE
> 用途：对 P3-03 工具链建议做外部核对，修正两处选型。
> 边界：不改变五轴/证据/释放/STOP/权限规则，不声称生产冻结。

## 1. 类型检查

**结论：mypy + `pydantic.mypy` 插件。**

依据：

- Pydantic 官方文档明确提供 mypy 插件，能检查字段类型、构造参数、`model_construct`、frozen model、未注解字段等；Pyright 仅通过 `dataclass_transform` 部分支持。
- Pyright 官方对比文档：Pyright 更快（大型代码库约 3–5 倍），但 Pydantic 特定能力不如官方 mypy 插件。
- 本项目模型大量使用 Pydantic v2 + SQLAlchemy 2，优先选择模型字段正确性，而不是纯速度。

来源：

- https://pydantic.dev/docs/validation/dev/integrations/dev-tools/mypy/
- https://github.com/microsoft/pyright/blob/main/docs/mypy-comparison.md

配置要求：`[tool.mypy] plugins = ["pydantic.mypy"]`；CI 运行 `mypy noahsark`。

## 2. Windows Node Agent 服务包装

**结论：pywin32 作为主方案；NSSM 仅作简化部署备选。**

依据：

- pywin32 仍在维护（PyPI v312，2026-06），提供 Windows Service 原生 API。
- NSSM 简单稳定，但社区反馈其多年未更新；不应作为长期唯一依赖。
- Node Agent 需要 Session 0 服务、STOP、清理、日志与重启控制，pywin32 能直接控制 SCM 生命周期。

来源：

- https://pypi.org/project/pywin32/
- https://caddyserver.com/docs/automatic-https

## 3. 反向代理/TLS

**结论：Caddy。**

依据：Caddy 默认自动 HTTPS、自动续期、HTTP→HTTPS 重定向；单二进制、Caddyfile 简单。控制面路由规模小，运维带宽有限，Caddy 更合适；Nginx 留作复杂路由/高流量备选。

来源：

- https://caddyserver.com/docs/automatic-https
- https://www.longsight.com/blog/migrating-from-nginx-to-caddy/

## 4. 未改变的选择

- CI：GitHub Actions（仓库已在 GitHub）。
- 前端：V0.0.1 原生 ES Modules；生产 SPA/SSR 留 P2-05。
- 容器：V0.0.1 不强制；systemd + Caddy。
- 认证：开发期角色头 + OIDC-ready 抽象；生产 OIDC 后接。
- 证据存储：本地内容寻址目录 + NAS/对象存储接口。

## 5. 影响

- P5-W0 使用 mypy（不是 pyright）。
- P5-W5 Node Agent 使用 pywin32 服务包装；NSSM 仅作备选。
- P5-W9 使用 Caddy + systemd。
- 其他冻结门与阻塞项不变。
