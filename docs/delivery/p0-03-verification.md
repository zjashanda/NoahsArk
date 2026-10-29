# P0-03 独立验证报告：`docs/delivery/openspec-v2-sync.md`

> 验证对象：P0-03 证据报告 [`openspec-v2-sync.md`](./openspec-v2-sync.md)（362 行，mtime 2026-10-28 23:48:32）
> 验证日期：2026-10-29（Asia/Shanghai）
> 验证方式：只读复核被报告声称修改的 `docs/v2/**`、`openspec/**`、权威 `docs/VERSIONING.md` 与 `plan.md` 批准记录；未修改任何被验对象，未提交。
> **结论：NEEDS-FIX**。核心六项规则大部分已正确落盘，但存在 1 项计划级范围缺口、1 项 PASS 判定语义缺口和 3 处证据报告不可复现/过期陈述。

---

## 1. 判定

**NEEDS-FIX**（不通过）。P0-03 不能宣称“文档同步完成”，原因见 §2 的 F1、F2；F3 为证据报告自身准确性问题。F4 为不影响主结论的残留项。

---

## 2. 必须修复项

### F1（范围缺口）`docs/VERSIONING.md` 未按 P0-03 计划同步

- 计划原文：`.omo/plans/noahsark-platform-delivery.md:25`
  > P0-03 同步规范文档冲突：把 PostgreSQL、五轴判定、离线续跑、STOP-first、设备释放与判定分离、清理回执语义、任务范围和任务数写入 `docs/v2`、`openspec` **与 `docs/VERSIONING.md`**。
- 报告边界：`docs/delivery/openspec-v2-sync.md:8`
  > 未修改 ... `docs/VERSIONING.md` ...
- 现状：`grep -nE "五轴|离线|STOP|cleanup_receipt|清理回执|设备释放" docs/VERSIONING.md` 无命中；该文件仅含导航、目录优先级和 P0-03 完成声明（`docs/VERSIONING.md:30,154,172`），没有六项规则的正文表达。
- 结论：三个计划指定同步目标中有一个未同步。需二选一：
  1. 在 `docs/VERSIONING.md` 补写六项规则（推荐）；或
  2. 由主控/所有者给出“P0-03 不改 VERSIONING、由 P0-02 承担”的明确范围变更记录，并写入 P0-03 报告。
- 注：当前 VERSIONING 的 mtime 为 2026-10-29 00:43，晚于本报告，属 P0-02 产物；但其中仍无六项规则，不能视为已完成同步。

### F2（语义缺口）正式 PASS 谓词漏掉 `execution_status=COMPLETED`

- 权威决定：`plan.md:611`（S5-3）
  > 正式 PASS 必须同时满足**执行完成**、`validity=VALID`、`business_verdict=PASS`、`evidence=COMPLETE`、`verification=PASS`。
- 同步后仍写成四个条件、遗漏“执行完成”的位置：
  - `docs/v2/SOLUTION.md:537`：只列 `validity_status`、`evidence_status`、`business_verdict`、`verification_status`。
  - `docs/v2/IMPLEMENTATION-PLAN.md:162`：同上。
  - `openspec/changes/ai-test-platform-v2/design.md:38`：同上。
  - `openspec/changes/ai-test-platform-v2/specs/completion-gate/spec.md:17-19`：Scenario “Formal PASS” 未要求 `execution_status=COMPLETED`。
- 风险：规格字面允许 `execution_status=RUNNING/NOT_STARTED` 的运行被判 formal PASS，与已批准的 fail-closed 五轴判定冲突。C2 映射（`SOLUTION.md:751`、`design.md:45`）虽提到 `execution_status=COMPLETED`，但不能替代 formal PASS 谓词。
- 修复：在上述 4 处把 `execution_status=COMPLETED` 加入 formal PASS 条件，并同步报告 §1.2/§3 D-5AXIS 的表述。

### F3（证据报告不可复现/过期）

1. **§8.3 命中数错误**：报告称“仅命中 3 条（SOLUTION:498、:517、proposal:9）”。按其给出的原命令重跑，实际为 **8 行**：
   `docs/v2/UI-DESIGN.md:16,17`、`docs/v2/SOLUTION.md:251,498,517`、`docs/v2/README.md:17`、`docs/v2/IMPLEMENTATION-PLAN.md:11`、`openspec/.../proposal.md:9`。
   8 条均为否定/正确表述（继续执行、保持占用、不得回收等），不影响规则正确性，但报告记录的结果不可复现。
   旁证：`docs/v2/UI-DESIGN.md` mtime 为 `23:48:40`，比报告 mtime `23:48:32` 晚 8 秒，说明报告扫描快照早于最终文件状态。
2. **§5.2 数量错误**：报告称 `completion-gate/spec.md` 新增 “3 Requirement / 5 Scenario”；实际为 **3 Requirement / 6 Scenario**（`spec.md:17,21,28,32,39,43`）。
3. **C-19/§9.7 已过期**：报告称 `docs/delivery/source-reconciliation.md` 不存在；该文件现存在（2026-10-29 00:42–00:43，由 P0-02 落盘）。这不是 P0-03 造成的缺陷，但报告应更新为“已由 P0-02 补齐”。

---

## 3. 已复核通过项

| 检查 | 证据 | 结果 |
|---|---|---|
| PostgreSQL 唯一正式库 | 报告 §8.2 原命令重跑：`grep ... \| grep -vE "历史\|已取代..."`，无输出，退出码 1 | PASS |
| 五轴与分离事实 | `docs/v2/SOLUTION.md:522-539`、`openspec/.../design.md:38`、`specs/completion-gate/spec.md:14-23`、`specs/ui-v2/spec.md:14-22` | PASS |
| 离线续跑、设备保持 `OCCUPIED` | `docs/v2/SOLUTION.md:251,498,517`、`design.md:52-56`、`completion-gate/spec.md:25-34` | PASS |
| STOP-first 重连 | `docs/v2/SOLUTION.md:251,517`、`design.md:54`、`completion-gate/spec.md:32-34` | PASS |
| 释放/证据/判定分离 | `completion-gate/spec.md:36-45`、`design.md:52-56`、`docs/v2/SOLUTION.md:745` | PASS |
| `cleanup_receipt` 语义 | `completion-gate/spec.md:39-41`、`design.md:56`、`docs/v2/SOLUTION.md:520,745` | PASS |
| C1–C7 / 81 项历史化 | `openspec/.../README.md` Legacy mapping、`tasks.md:5,120`、`SOLUTION.md:907,953`、`IMPLEMENTATION-PLAN.md:7,11` | PASS（F4 有局部残留） |
| OpenSpec 结构校验 | `openspec validate ai-test-platform-v2 --strict` → `Change 'ai-test-platform-v2' is valid`，退出码 **0** | PASS |
| 补丁空白检查 | `git diff --check` → 无输出，退出码 **0** | PASS |
| YAML 配置 | `openspec/config.yaml` 可解析，keys=`['schema']` | PASS |
| 报告存在性 | `wc -l docs/delivery/openspec-v2-sync.md` = **362**（与报告 §8.7 一致） | PASS |
| 同步路径数量 | 报告称 17 修改 + 1 新增 = 18；`git status` 中 P0-03 相关为 18（排除 P0-01 的 `wireframes/README.md`、`.gitignore`、`README.md` 与 P0-02/P0-04..08 未跟踪产物） | PASS |
| 新增链接目标 | 报告 §8.8 的 `docs/delivery/openspec-v2-sync.md`、`.omo/plans/noahsark-platform-delivery.md` 均存在；`source-reconciliation.md` 现已存在（见 F3.3） | PASS |

### 3.1 源草案仍矛盾的确认（不属于 P0-03 同步对象）

报告 §9.1 的说法经复核属实：

- `.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md:91`：I-21 “缺失视为证据不完整”。
- 同文件 `:126`：`lease_expired → 运行 INFRA_ERROR`。
- `.omo/drafts/01-design/noahsark-v0.0.1-module-design.md:101`：`心跳超时 → 租约过期 → run=INFRA_ERROR`。

这些是 P0-03 明确排除的源草案正文，应由后续文档同步/契约任务修正，**不构成本次 P0-03 的返工项**；但 `docs/VERSIONING.md:25` 已声明“草案正文旧条文以 plan.md 批准记录为准”，故在修复前不得直接引用这些条文作为当前规则。

---

## 4. 次要残留（可随 F1/F2 一并修正）

1. `docs/v2/SOLUTION.md:1030` 的 Q9 仍写“【已同步】81 项”，`:1058` 仍写“均为 81 项”，未逐处加历史标签。虽然文件头 `:15` 已把 81 项声明为历史，但表格中的“已同步”是正向当前表述，建议改为历史/追溯。
2. `docs/v2/UI-DESIGN.md:171,1623,2383` 仍保留旧终态表、心跳超时文案和“设备/租约失败 → INFRA_ERROR”。文件头 `:10-17` 已将整份文档标为历史并覆盖冲突，报告 §9.5 也已披露“未逐页重写”，因此不算隐藏矛盾；若要彻底消除歧义，可在这些行内加 `历史/已取代` 标签。
3. `docs/VERSIONING.md:30,154,172` 已宣称 P0-03“于 2026-10-28 完成”，而 `docs/delivery/construction-progress.md:13` 仍为“待验证”。这是状态口径冲突；建议在 P0-03 通过后由主控统一，或在 VERSIONING 改为“同步产物已落盘，待独立验证”。

---

## 5. 可复现命令（本次实际执行）

```bash
cd /home/bszheng/NoahsArk

# 1) SQLite 正式库残留：无输出，exit 1
grep -rn "SQLite\|sqlite" docs/v2 openspec --include=*.md --include=*.yaml \
  | grep -vE "历史|已取代|原文|修正|取代|不再|legacy|historical|only as|not by itself"

# 2) 危险旧口径：8 行命中（报告写 3 行）
grep -rniE "lease (expiry|expiration) (reclaims|releases|stops)|heartbeat (loss|expiry) (stops|fails|releases)|心跳(过期|超时).*(停止|失败|回收|释放)|租约(过期|到期).*(回收|释放|停止|失败)|missing cleanup_receipt (means|makes).*(all )?evidence incomplete|缺.*cleanup_receipt.*(等同于|视为).*证据不完整" \
  docs/v2 openspec --include=*.md | wc -l

# 3) OpenSpec 严格校验：exit 0
openspec validate ai-test-platform-v2 --strict

# 4) 补丁检查：exit 0，无输出
git diff --check

# 5) formal PASS 缺口
grep -rn "Formal PASS\|正式 PASS" docs/v2 openspec --include=*.md

# 6) VERSIONING 六项规则缺口：无命中
grep -nE "五轴|离线|STOP|cleanup_receipt|清理回执|设备释放" docs/VERSIONING.md
```

---

## 6. 限制

1. 仓库中 `docs/VERSIONING.md`、`docs/contracts/`、`docs/delivery/` 均为未跟踪路径，无法用 `git diff` 证明“P0-03 未修改 VERSIONING”；本报告依据 mtime、报告自述和 P0-02 证据交叉判断。
2. 未运行任何产品代码、单元/集成测试、真机烟测、部署或发布；P0-03 的“通过”只可能指文档结构与一致性。
3. 未读取 `.omo/drafts/99-history` 全文，仅定向核对报告 §9.1 所指的草案矛盾行。
4. 未检查 `docs/ssh.txt` 或任何凭据内容；该文件按 P0-01 已隔离。
5. 本报告只覆盖 P0-03 声称的同步范围，不评价 P0-04..P0-11 契约内容。
