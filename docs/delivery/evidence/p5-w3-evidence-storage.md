# P5-W3 证据接收、摘要、manifest、访问、保留证据

> 状态：DONE（开发基线）· 非生产冻结
> 日期：2026-10-30
> 范围：`apps/control_plane/`

## 交付

- `noahsark/services/evidence_storage.py`：
  - SHA-256 内容寻址，相对 key 固定为 `sha256/<ab>/<cd>/<hex>.blob`；
  - 写入先落临时文件 + `os.replace`，同 digest 幂等且不覆盖既有 blob；
  - 每次读取/校验都从磁盘字节复算 digest，缺失或损坏 fail-closed；
  - `received` 与 `verified` 分离：收到字节只进入 `complete`，复算一致才进入 `verified`；
  - `EVIDENCE_RAW` 能力校验；允许/拒绝都追加 `EVIDENCE_RAW_ACCESS` 审计；
  - manifest 独立统计 expected/received/verified/conflicted/missing，空 manifest 不报 COMPLETE；
  - 保留策略 dry-run 只读，跳过 hold/未收到/窗口内/非终态；破坏性清理仅 ADMIN + `PURGE_EVIDENCE` 确认短语，保留元数据与审计；
  - API/JSON 只暴露相对 storage key，不暴露绝对路径或存储凭据。
- `tests/test_p5_w3_evidence_storage.py`（21 项）：digest 规范化、写入/读取/复算、声明 digest 不符、不可覆盖、缺失/损坏、大小上限与路径穿越、上传/确认状态机、manifest 分母、retention dry-run。
- `tests/test_p5_w3_evidence_db.py`（6 项）：receive→verify 审计、损坏/缺失 fail-closed、ALLOW/DENY 访问审计、digest 不符不改状态不写审计、retention dry-run→ADMIN purge、manifest 相对 key。

## 关键修复

1. `attach_evidence_blob()` 在已 `verified` 证据重复上传相同字节时，返回值与审计事件曾把 `received_is_not_verified`/`verified` 固定为未验证，和实际状态矛盾。现在返回值沿用 `apply_upload()` 的结论，审计事件记录真实 `verified`。
2. 新增回归测试 `test_receiving_identical_bytes_for_verified_item_reports_verified`，同时锁定返回值和 `EVIDENCE_RECEIVED` 审计字段；回退修复即失败。

## 验证

工作目录：`apps/control_plane`；解释器/工具均来自仓库 `.venv`。

```text
$ ../../.venv/bin/python -m pytest tests/test_p5_w3_evidence_storage.py tests/test_p5_w3_evidence_db.py --disable-warnings -o addopts="" -q
27 passed

$ ../../.venv/bin/python -m pytest --disable-warnings -o addopts="" -q
131 passed

$ ../../.venv/bin/python -m ruff check noahsark tests
All checks passed!

$ ../../.venv/bin/python -m mypy noahsark
Success: no issues found in 46 source files
```

说明：本机 PostgreSQL 可连接，W3 DB 测试真实执行，未 skip；测试使用仓库既有 seed 流程（`reset=True`）准备数据，结束后清理本用例创建的 evidence 行。

## 验收映射

| 计划要求 | 证据 |
|---|---|
| 内容寻址 SHA-256 | `test_put_read_and_verify_roundtrip_exposes_only_relative_key` |
| 上传/下载（读取） | 同上；`test_missing_and_corrupt_blobs_fail_closed` |
| digest 复算与不符拒绝 | `test_put_blob_rejects_declared_digest_mismatch_without_writing`、`test_apply_verification_requires_received_and_recomputes` |
| 证据不可覆盖 | `test_put_blob_is_idempotent_and_does_not_replace_same_digest`、`test_corrupt_existing_blob_is_never_overwritten` |
| received ≠ verified | `test_apply_upload_marks_received_but_not_verified`、`test_received_but_unverified_is_unverified_not_complete` |
| 访问审计（含拒绝） | `test_raw_access_allows_and_denies_with_audit` |
| manifest 计数 | `test_manifest_counts_keep_expected_received_verified_separate`、`test_extra_received_item_cannot_mask_a_missing_expected_item` |
| 保留 dry-run/hold/fail-closed | `test_retention_dry_run_classifies_holds_and_blob_states_without_deleting`、`test_retention_dry_run_then_admin_purge_keeps_metadata_and_audit` |

## 缺口

- W3 服务尚未通过 HTTP 路由暴露上传/下载/verify/retention cleanup；本波验证到服务层与数据库编排层。
- DB 测试依赖本机 PostgreSQL 与 seed；CI 未配置数据库时应显式 skip，而不是伪造结果。
- 尚未执行 L2/L3 集成演练，也未做对象存储/NAS 或加密存储迁移。
- `evidence_storage.py` 已超过 250 纯行阈值，后续扩展前应拆分存储、manifest、retention 三块；本波不重构以保持验证范围稳定。

## 下一步

W4：判定、报告、知识、TaskCard；保持正式 PASS 仅精确元组、报告冻结不可原地改、知识候选无自动推广。
