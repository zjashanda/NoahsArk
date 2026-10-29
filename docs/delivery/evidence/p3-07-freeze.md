# P3-07 施工方案评审与冻结记录

> 状态：**REVIEWED · NOT FROZEN**
> 归属：`docs/delivery/phase3-construction-plan.md` P3-07
> 输入：P3-01..P3-06 证据、Phase 3/5 方案、当前仓库与工具链事实
> 边界：本文不授权 Phase 5 全量实施，不声称 P3-07 已冻结。

## 1. 评审结果

| 输入 | 结果 | 说明 |
|---|---|---|
| P3-01 WBS 与依赖 | PASS | W0–W10、依赖、关键路径、66 项映射已核对 |
| P3-02 共享文件所有权 | PASS | 单写入者、合并顺序、冲突协议已记录 |
| P3-03 工具链 ADR | PARTIAL | 技术方向稳定；6 个决策仍 PENDING |
| P3-04 进度与 66 项映射 | PASS | 34 项任务可映射，无重复计数 |
| P3-05 质量门与证据 | PASS | T1–T6/L0–L5、DoD、证据命名已定义 |
| P3-06 风险与回滚 | PASS | 风险、STOP、回滚规则已定义 |

## 2. 技术建议（可关闭的 ADR）

以下是建议，不是已批准冻结：

| ADR | 建议 | 理由 |
|---|---|---|
| 前端形态 | V0.0.1 继续原生 ES Modules；生产 SPA/SSR 留到 P2-05 | 当前 39 路由原型已验证；避免在契约未冻结前引入框架 |
| 类型检查 | `pyright` | 对 Pydantic/FastAPI 类型推断更直接 |
| CI | GitHub Actions | 远端已在 GitHub；本地命令先行 |
| 容器 | V0.0.1 不强制容器；systemd + Caddy | 单机开发优先；容器化留到部署 ADR |
| Node Agent 打包 | Python 3.12 venv + NSSM 服务包装 | Windows 服务稳定；不引入新运行时 |
| 反向代理/TLS | Caddy | 自动 TLS、配置简单；可替换 Nginx |

## 3. 仍需所有者裁决

1. **真实认证**：OIDC / 本地账号 / 客户端证书；是否允许继续用开发角色头到 W1。
2. **证据存储**：本地磁盘 / NAS / 对象存储；加密、保留和备份策略。
3. **部署拓扑**：单 Linux / 双机 / 容器 / 反向代理与 TLS 终止点。
4. **NAS/第二服务器/备份恢复**：A-0 仍缺的事实。
5. **Node Agent 协议与证书**：注册、轮换、撤销、版本兼容。
6. **TCL 真机**：设备、凭据、网络、验收时间窗。

这些是 Phase 5 W5/W6/W9 的前置；未关闭前不得声称生产可用或完成验收。

## 4. 冻结清单

- [x] P3-01..P3-06 证据存在且可读。
- [x] WBS、所有权、质量门、风险、映射已记录。
- [x] 技术 ADR 有推荐与备选。
- [ ] 6 项所有者决策关闭。
- [ ] 部署/认证/证据存储/Node Agent/TCL 的 owner、日期、影响面记录。
- [ ] Phase 3 版本号、哈希、变更记录最终确认。
- [ ] 所有者签收。

## 5. 结论

**P3-07 不冻结。** 当前只能标记为 `[~]`：

```text
blocked by P3-03 PENDING ADRs and owner decisions:
auth, evidence storage, deployment topology/NAS/backup,
Node Agent protocol/certs, TCL hardware window
```

技术实施可以继续做不依赖这些决策的部分（P4 文档校验、P5-W0 基础、W1 领域模型），但不得进入 W5/W6/W9 或宣称冻结/生产可用。

## 6. 下一步

1. 所有者对 §3 六项给出选择或授权默认方案。
2. 更新 P3-03/P3-07 为 ACCEPTED/FROZEN。
3. 再进入 Phase 4 冻结与 Phase 5 全量实施。
