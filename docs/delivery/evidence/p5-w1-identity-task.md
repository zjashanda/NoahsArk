# P5-W1 身份、会话、RBAC、审计、Task/Revision 证据

> 状态：DONE（开发基线）· 非生产冻结
> 日期：2026-10-29
> 范围：`apps/control_plane/`

## 交付

- `noahsark/services/auth.py`：`Principal`、`Credentials`、`AuthProvider`、`DevHeaderProvider`、`OIDCProvider` stub；未知角色 fail-closed。
- `noahsark/services/sessions.py`：`sks_` token、SHA-256 哈希存储、TTL 上限/下限、过期/撤销检查、`issue/resolve/revoke`。
- `noahsark/services/audit.py`：追加式哈希链、`prev_event_hash`/`event_hash`、链校验、append-only。
- `noahsark/models/identity.py`：`sessions` 表（token hash、actor、role、issued/expires/revoked）。
- `noahsark/models/task.py`：`TaskRevision.content`（不可变修订内容快照）。
- 迁移：`8a4e6c21d9f0_w1_sessions_revision_content.py`，已 `alembic upgrade head`。
- 测试：`tests/test_w1_auth_session.py`（未知角色、默认 OBSERVER、token 哈希、过期/撤销）。

## 验证

```text
$ pytest --disable-warnings -q
83 passed

$ ruff check noahsark tests
All checks passed!

$ mypy noahsark
Success: no issues found in 41 source files

$ alembic upgrade head
7f3d2b91c4a5 -> 8a4e6c21d9f0
```

## 缺口

- OIDC provider 仍是 stub；真实登录/OIDC 未接。
- 会话 issue/revoke API 尚未暴露给 UI。
- 审计链校验已有服务，但缺少对历史事件损坏的端到端测试。
- 修订不可变/审批绑定主要由现有 `test_api_writes.py` 覆盖，尚无独立 W1 测试文件。

## 下一步

W2：门禁、Run/Attempt、Lease/Occupancy、Device/Node、TaskCard、stale；保持五轴独立、进度仅 COUNTS、OFFLINE 组合可见。
