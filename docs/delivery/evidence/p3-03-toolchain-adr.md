# P3-03 工具链 ADR 与环境决策证据

> 状态：DRAFT · 评审输入，不是冻结件
> 归属：`docs/delivery/phase3-construction-plan.md` §7、`docs/delivery/phase5-implementation-plan.md` §1/§3/§12 的 P3-03 项
> 输入：`phase3-construction-plan.md` §7、`phase5-implementation-plan.md`、`1.md` §5、`apps/control_plane/pyproject.toml`、当前 `.venv` 与本机 PostgreSQL 事实
> 边界：本文只记录工具链决策、环境事实、锁定策略与阻塞缺口；不改代码、契约、迁移、设计、计划文件，不启动 W0，不声称 P3-07 已冻结。所有“推荐”在决策门关闭前都只是推荐。

## 0. 判读规则

1. 状态只有两种：`ACCEPTED` 表示方向已由上游文件确认，本文只做落地登记；`PENDING` 表示仍需 ADR 或决策门裁定，任何实现不得把 PENDING 值写死。
2. `ACCEPTED` 不等于版本已锁。方向确认与精确版本、补丁号、锁文件是两件事，后者仍受 ADR-001 与 P2-09 约束。
3. 当前仓库状态仍早于 W0：根 `pyproject.toml`、锁文件、`apps/web/**`、`apps/node_agent/**`、`packages/contracts/**`、CI 配置均不存在。已有 `apps/control_plane/**` 纵切只能按预研资产使用。
4. 本文所有环境数字来自 2026-10-29 的本机只读探测；换机器或换日期必须重跑 §4 的命令，不得引用本文数字当作持续事实。
5. PENDING 项一律遵循“停下来登记，不发明值”的规则。缺 CI provider 就不写 provider 专用 YAML，缺容器运行时就不写 `docker compose`，缺前端 ADR 就不预选框架。

## 1. 决策表

| ID | 决策 | 推荐选择 | 备选 | 状态 | 决策门 |
|---|---|---|---|---|---|
| D-01 | 控制面语言与运行时 | Python 3.12（当前 3.12.3），保留 3.11 兼容表达 | 无（TypeScript/.NET 仅未来版本） | ACCEPTED | 方向已确认；精确小版本由 P2-09 |
| D-02 | 包管理与环境 | 当前继续 `venv` + `pip`；W0 再按 ADR-001 决定是否引入 `uv` | `uv` + `uv.lock`、`pip-tools` | PENDING | ADR-001 / P2-09 |
| D-03 | Web 框架 | FastAPI + OpenAPI 3.1 | Flask（仅同进程模板 UI 时评估） | ACCEPTED | P2-01/P2-03 |
| D-04 | 数据校验与配置 | Pydantic v2 + pydantic-settings | attrs/dataclass 手工校验 | ACCEPTED | P2-03 |
| D-05 | 数据访问 | SQLAlchemy 2 + asyncpg，显式 repository/unit-of-work | psycopg 3 + SQL-first | ACCEPTED | P2-02 |
| D-06 | 迁移 | Alembic，forward-only + expand/contract | Flyway | ACCEPTED | P2-02 |
| D-07 | 正式数据库 | PostgreSQL 16（当前 16.15） | 无正式备选 | ACCEPTED | 大版本已定；小版本由 P2-02 |
| D-08 | Python 测试 | pytest + pytest-asyncio | unittest | ACCEPTED | P2-01/P2-04 |
| D-09 | Python 规范 | ruff check + ruff format --check | flake8 + black | ACCEPTED | P2-09 |
| D-10 | 类型检查 | pyright（推荐），mypy 为唯一备选，二选一 | mypy | PENDING | ADR-001 / P2-09 |
| D-11 | 前端实现形态 | 由 P1-08 冻结原型与 P2-05 决定，本文不预选 | 原生 ES Modules、SPA、SSR | PENDING | P1-08 / P2-05 |
| D-12 | CI provider | 命令先行；若远端为 GitHub 则 GitHub Actions | GitLab CI、本地 runner | PENDING | P2-07 / P3-07 |
| D-13 | 容器与部署单元 | 未定；不得假设 Docker 可用 | 原生 systemd、容器编排 | PENDING | P2-07 |
| D-14 | Node Agent 打包 | Python 3.12 + 服务安装 + Session 0 helper，打包形态待定 | PyInstaller、MSI、脚本安装 | PENDING | P2-04 |
| D-15 | 反向代理与 TLS | 未定；验收前必须有明确拓扑 | Nginx、Caddy、直接暴露（不推荐） | PENDING | P2-07 |
| D-16 | 仓库形态 | 单仓多应用：`apps/control_plane`、`apps/node_agent`、`packages/contracts`、`apps/web` | 多仓 | PENDING | P2-01 / P2-09 |
| D-17 | 本地数据库来源 | 复用已批准的本机实例；Docker Compose 仅在 P2-07 批准后 | Docker Compose、原生实例 | PENDING | P2-02 / P2-07 |
| D-18 | 身份与认证 | OIDC 或本地账号 + 服务端会话，二选一待裁 | 继续 `X-NoahsArk-Role`（仅开发） | PENDING | P2-06 / ADR-007 |
| D-19 | 证据存储后端 | 未定；不得默认本地磁盘即为最终方案 | 本地磁盘、NAS、对象存储 | PENDING | P2-06 / P2-07 / ADR-006 |

计数：ACCEPTED 8 项（D-01、D-03 至 D-09），PENDING 11 项（D-02、D-10 至 D-19）。任何 PENDING 项关闭前，P3-07 不得冻结，W0 不得启动。

## 2. 已确认项（ACCEPTED）

### 2.1 Python 3.12

控制面与 Node Agent 统一 Python 路线，`1.md` §5.2 与施工方案 §7.1 均已确认，ADR 不得推翻。当前解释器为 3.12.3，`requires-python = ">=3.12,<3.13"`。代表节点仍为 Python 3.10.11，属于 A-0 整改项，不改变控制面选型。落地约束：

- 禁止使用 3.12 之后才有的语法去阻塞 3.11 兼容表达，除非 P2-09 明确放弃 3.11。
- 禁止依赖系统 Python；一律使用项目内 `.venv` 或 W0 后的锁定环境。
- Python 补丁号升级需重跑测试与迁移，不静默漂移。

### 2.2 FastAPI、Pydantic v2、SQLAlchemy 2、asyncpg、Alembic

与方案 B 和纵切实现一致，方向不再讨论。落地约束：

- Pydantic 只允许 v2 语义（`model_validate`、`field_validator`、`model_config`），不引入 v1 兼容层。
- SQLAlchemy 使用 2.0 风格声明与显式事务，领域层不泄露 ORM 私有状态；异步驱动固定 asyncpg。
- Alembic 只做 forward-only；回退以“已验证回退”或“前向修复”记录，不凭记忆 downgrade。
- 已应用迁移永不编辑；`alembic heads` 必须单头，当前为 `7f3d2b91c4a5`。

### 2.3 PostgreSQL 16、pytest、ruff

- PostgreSQL 是唯一正式数据库，SQLite 不得成为第二权威源；迁移与 seed 已显式拒绝 SQLite。
- pytest 是唯一测试入口，集成测试用 marker 区分，不用脚本代替。
- ruff 同时承担 lint 与 format 检查，不并行引入 flake8/black 形成双标准。

## 3. 待决项（PENDING）

### 3.1 前端 P2-05

| 问题 | 本文立场 | 关闭条件 |
|---|---|---|
| 原生 ES Modules、SPA 还是 SSR | 不预选。候选 UI `design/ui-app/` 仍是 NOT FROZEN，39 路由与状态语义可复用，技术形态不可直接继承 | P1-08 冻结 + P2-05 ADR 回答框架、路由、状态、i18n、权限渲染、构建链 |
| 组件库 | 不绑定；须证明键盘、焦点、弹层与中文可访问性 | 同 P2-05 |
| 前端测试 | Playwright 必选；单测运行器随前端 ADR 决定 | P2-05 |

当前环境没有 Node.js，`npx playwright` 不可执行。这既是环境缺口，也是不能在 W6 之前假装前端可验证的理由。

### 3.2 类型检查：pyright 还是 mypy

推荐 pyright，理由是 FastAPI/Pydantic v2 生态类型推导更完整、CI 集成简单。备选 mypy 只在团队已有配置或插件约束更强时采用。关闭前：不写死 `pyrightconfig.json`，不在 CI 中声明“类型检查通过”。两者均未安装。

### 3.3 CI provider

流程必须先命令化：`ruff check`、`ruff format --check`、类型检查、`pytest`、迁移演练、秘密扫描。provider 只负责调度，不承载业务逻辑。若远端确认为 GitHub，则用 GitHub Actions；否则在 P2-07 裁定 GitLab CI 或本地 runner。关闭前不提交任何 provider 专用流水线。

### 3.4 容器运行时

本机无 Docker、无 Podman，当前也没有 Compose 文件。P2-07 未定前，禁止把本地开发写成“必须 Docker”。允许的临时事实是：直接用已批准的本机 PostgreSQL 16.15 实例。容器化若被选中，需补镜像基线、非 root、只读根文件系统、健康检查与数据卷策略。

### 3.5 Node Agent 打包

已确认 Python 主路径，未确认交付形态。必须回答：服务安装方式、Session 0 与交互执行器边界、helper 进程、spool 路径与容量、升级与回滚、证书存放。关闭前只做模拟节点与协议草案，不产出安装包，不声称可在代表节点部署。

### 3.6 反向代理与 TLS

必须回答：单进程还是分进程、监听地址、证书来源与轮换、上传大小限制、超时与 SSE 行为、备份入口是否暴露。关闭前部署脚本只能是开发版，且不得写入真实域名、证书路径或凭据。

## 4. 环境事实与复现命令

### 4.1 事实表（2026-10-29 探测）

| 项 | 事实 | 判读 |
|---|---|---|
| 操作系统 | Ubuntu 24.04.4 LTS | 开发机事实，不等于生产基线 |
| Python | 3.12.3，位于 `/home/bszheng/NoahsArk/.venv` | 符合 D-01 |
| pip | 24.0 | 当前唯一包管理器 |
| 已装后端版本 | fastapi 0.162.0、pydantic 2.14.1、pydantic-settings 2.16.2、SQLAlchemy 2.1.6、asyncpg 0.32.0、alembic 1.20.1、uvicorn 0.54.0、httpx 0.28.1 | 仅本机状态，不是锁定版本 |
| 测试与规范 | pytest 9.2.0、pytest-asyncio 1.4.1、ruff 0.17.3 | 仅本机状态 |
| 类型检查器 | pyright 与 mypy 均未安装 | D-10 仍 PENDING |
| PostgreSQL | 16.15，`pg_isready` 返回 accepting connections | 版本未冻结 |
| 迁移 | 单头 `7f3d2b91c4a5`，共 3 个 revision | 与纵切事实一致 |
| 缺失工具 | 无 `uv`、无 `poetry`、无 `docker`、无 `node`/`npm` | 直接约束 D-02、D-11、D-13 |
| 已有基础工具 | git、make、curl、psql | 可支撑最小命令链 |
| 仓库缺口 | 无根 `pyproject.toml`、无锁文件、无 CI、无 `apps/web`、无 `apps/node_agent`、无 `packages/contracts` | W0 入口不成立 |

### 4.2 复现命令

```bash
cd /home/bszheng/NoahsArk
.venv/bin/python -V
.venv/bin/python -m pip --version
.venv/bin/python -m pip list
psql --version
pg_isready
command -v uv poetry docker node npm || true
cd apps/control_plane && ../../.venv/bin/alembic heads
```

说明：以上均为只读命令，不建库、不迁移、不写文件。W0 建立根环境后，替换为 `uv sync --frozen` 等锁定命令，并保留本节作为迁移前后对照。

## 5. 版本锁定策略

### 5.1 声明与锁分离

1. `pyproject.toml` 只声明兼容区间与 Python 约束；真正可复现的是锁文件或带哈希的 requirements。
2. 生产依赖禁止只有下限的浮动声明。当前 `apps/control_plane/pyproject.toml` 的 `fastapi>=0.115`、`sqlalchemy>=2.0` 等属于预研期声明，不是生产锁；实际已装版本已明显高于下限，说明漂移真实存在。
3. W0 必须产出唯一锁文件（按 D-02 裁定为 `uv.lock` 或 `requirements.lock`），CI 使用 `--frozen` 或 `--require-hashes`，禁止 CI 现场解析最新版本。
4. 开发依赖也进锁文件；允许区间声明，但安装结果必须可复算。

### 5.2 约束规则

| 规则 | 内容 |
|---|---|
| Python 版本 | `requires-python` 与版本文件一致；CI 矩阵不隐式升级 |
| 主版本 | Pydantic 固定 2.x，SQLAlchemy 固定 2.x，禁止跨主版本静默升级 |
| 迁移依赖 | Alembic 与 SQLAlchemy 升级必须同批验证迁移链与单头 |
| 驱动 | asyncpg 版本与 PostgreSQL 大版本组合需在集成测试中验证 |
| 升级流程 | 提依赖变更申请，跑 lint、类型、单测、集成、迁移演练，附证据 |
| 禁止项 | 生产依赖使用 `*`、`latest`、未固定 git 分支；仓库提交 `.env` 或凭据 |

### 5.3 当前漂移示例

| 包 | 声明下限 | 本机实际 | 风险 |
|---|---|---|---|
| fastapi | `>=0.115` | 0.162.0 | 跨多个小版本，行为与文档可能不同 |
| SQLAlchemy | `>=2.0` | 2.1.6 | 2.1 语义差异未评审 |
| pytest | `>=8` | 9.2.0 | 主版本跨越，插件兼容需复核 |
| ruff | `>=0.6` | 0.17.3 | 规则集变化可能改变检查结果 |

结论：在锁文件建立前，“本机测试通过”只能作为预研证据，不能作为 W0 出口证据。

## 6. 阻塞 P3-07 的缺口

| # | 缺口 | 影响 | 解除条件 | 责任 |
|---|---|---|---|---|
| G-01 | 根 `pyproject.toml`、锁文件不存在 | 无可复现安装，W0 无法进入 | W0 基座或提前产出锁定草案 | R-ARCH |
| G-02 | ADR-001 至 ADR-010 全部 OPEN | P3-07 冻结条件不成立 | 逐项关闭并留评审记录 | 各 ADR owner |
| G-03 | 无 CI 配置与秘密扫描 | QG-W0 出口不成立 | provider 裁定 + 命令化流水线 | R-OPS |
| G-04 | 无容器运行时 | D-13 无法落地，部署拓扑不可验证 | P2-07 裁定并记录环境前提 | R-OPS |
| G-05 | 无 Node.js 与浏览器依赖 | 前端与 Playwright 无法执行 | P2-05 裁定 + 环境安装记录 | R-FE |
| G-06 | 无类型检查器与配置 | 类型门无法执行 | D-10 关闭并安装 | R-ARCH |
| G-07 | 前端 P2-05 未冻结 | W6 不能选型，39 路由无法落地 | P1-08 与 P2-05 完成 | R-FE |
| G-08 | 单仓目录未建立 | 契约、节点、Web 无落点 | W0 目录结构与 owner 确认 | R-ARCH/R-PM |
| G-09 | PostgreSQL 仅“已安装” | 版本与实例策略未冻结 | P2-02 关闭 | R-BE |
| G-10 | 生产依赖未钉死 | 复现性与供应链风险 | 锁文件 + 哈希 + 升级流程 | R-ARCH/R-SEC |

## 7. P3-07 放行检查

- [ ] D-02、D-10、D-11、D-12、D-13、D-14、D-15、D-16、D-17、D-18、D-19 全部有裁定记录，无遗留 PENDING。
- [ ] ADR-001 至 ADR-010 均有 owner、结论、日期与影响面。
- [ ] 根锁文件存在，且在干净环境可复算安装。
- [ ] §4 的复现命令在目标开发机与 CI 上结果一致。
- [ ] 每个 PENDING 项对应的“不得写死”约束已写入 W0 任务卡。
- [ ] 本文件与 `phase3-construction-plan.md` §7 无冲突；冲突以计划文件为准并回写本文。

当前结论：本文可关闭 P3-03 的“决策登记”职责，但不能关闭 P3-07。工具链方向已稳定，版本、前端、CI、容器、节点打包与部署拓扑仍未决，W0 不具备正式开工条件。
