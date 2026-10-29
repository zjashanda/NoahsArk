# P0-03 修复后独立验证（Post-fix Verification）

> 验证对象：P0-03 证据报告 [`openspec-v2-sync.md`](./openspec-v2-sync.md) 在 F1/F2/F3 返工后的最终状态
> 验证日期：2026-10-29 08:16 CST（Asia/Shanghai）
> 验证性质：**有限范围的修复后复验**（bounded post-fix re-verification），不是完整重审
> 前置判定：原始报告 [`p0-03-verification.md`](./p0-03-verification.md) 结论为 **NEEDS-FIX**（F1/F2/F3）。该历史结论原样保留，未被本文件改写。
> 验证方式：只读复核；未修改任何被验对象，未提交、未推送，未触碰产品代码、`docs/contracts/`、`.omo/`、根 `plan.md`、`docs/ssh.txt`。
> **结论：PASS**——原 F1/F2/F3 的范围内缺口均已关闭，且未发现新的范围内回归。

---

## 1. 判定

**PASS（限定范围）**。五项指定检查全部通过：VERSIONING 六项规则、四处 formal PASS 含 `execution_status=COMPLETED`、OpenSpec strict 校验、过期计数/C-19 更正、git 空白检查。

说明：本判定仅覆盖原验证报告的 F1/F2/F3 范围与本次五项复验项，不代表 P0-03 的实现、测试、部署或验收通过。

---

## 2. 复验项与结果

| # | 复验项 | 命令（均在 `/home/bszheng/NoahsArk` 执行） | 实际结果 | 判定 |
|---|---|---|---|---|
| V1 | `docs/VERSIONING.md` 含六项规则 | `grep -nE "五轴\|离线\|STOP\|cleanup_receipt\|清理回执\|设备释放" docs/VERSIONING.md` | 命中 5 行（§2.4 表格第 2–6 项）；表格另含第 1 项 PostgreSQL，合计 **6 项**（行 86–91） | PASS |
| V2 | 四处 formal PASS 均含 `execution_status=COMPLETED` | 见 §3.2 的四文件逐点核对 | 4/4 处均含该条件，且明确 `RUNNING`/`NOT_STARTED` 不得判正式 PASS | PASS |
| V3 | OpenSpec strict 校验 | `openspec validate ai-test-platform-v2 --strict` | `Change 'ai-test-platform-v2' is valid`，退出码 **0** | PASS |
| V4 | 过期报告计数与 C-19 已更正 | 重跑 §8.3 扫描 / 核对 §5.2、§9.7 | 危险旧口径实测 **8 行**、新增 **3 Requirement / 6 Scenario**、C-19 已标注 `source-reconciliation.md` 由 P0-02 补齐 | PASS |
| V5 | git 空白检查 | `git diff --check` | 无输出，退出码 **0**；变更文档行尾空白扫描 **0** 处 | PASS |

---

## 3. 证据明细

### 3.1 V1 — `docs/VERSIONING.md` 六项规则（F1）

新增章节：`docs/VERSIONING.md:80` `### 2.4 P0-03 同步后的六项规则（导航摘要）`，表格位于 `docs/VERSIONING.md:86-91`：

| 行 | # | 规则 |
|---|---|---|
| 86 | 1 | PostgreSQL 唯一正式库 |
| 87 | 2 | 五轴判定（含 `execution_status=COMPLETED` 等五条件） |
| 88 | 3 | 离线续跑 |
| 89 | 4 | STOP-first 重连 |
| 90 | 5 | 释放 / 证据 / 判定分离 |
| 91 | 6 | `cleanup_receipt` 语义 |

关键词命令命中 5 行（第 2–6 项），第 1 项 PostgreSQL 行不含上述关键词但确实存在，故合计六项。**F1 关闭。**

### 3.2 V2 — 四处 formal PASS 谓词（F2）

逐文件核对结果（`grep -n "execution_status=COMPLETED"` 取 formal PASS 段落）：

| 文件 | 行 | 证据 | 判定 |
|---|---|---|---|
| `docs/v2/SOLUTION.md` | 537 | 正式 PASS 条件首项即 `execution_status=COMPLETED`，并注明 `RUNNING`/`NOT_STARTED` 不得判正式 PASS | PASS |
| `docs/v2/IMPLEMENTATION-PLAN.md` | 162 | `Formal PASS requires execution_status=COMPLETED, ...`，含 `RUNNING`/`NOT_STARTED` 排除句 | PASS |
| `openspec/changes/ai-test-platform-v2/design.md` | 38 | `Formal PASS requires execution_status=COMPLETED, ...`，含排除句 | PASS |
| `openspec/changes/ai-test-platform-v2/specs/completion-gate/spec.md` | 17-19 | Scenario `Formal PASS` 的 THEN 首项即 `execution_status=COMPLETED`，含排除句 | PASS |

附注：`docs/v2/SOLUTION.md:751` 与 `openspec/.../design.md:45` 的 C2 映射亦含 `execution_status=COMPLETED`，属补充一致，不作为 formal PASS 谓词替代。**F2 关闭。**

### 3.3 V3 — OpenSpec strict

```bash
export PATH="/home/bszheng/.nvm/versions/node/v24.14.1/bin:$PATH"
openspec validate ai-test-platform-v2 --strict
# Change 'ai-test-platform-v2' is valid
# EXIT=0
```

工具版本：`openspec --version` → `1.7.0`。**通过。**

### 3.4 V4 — 过期计数与 C-19（F3）

1. **§8.3（危险旧口径命中数）**：按报告原命令重跑，`wc -l` = **8**，与报告 `openspec-v2-sync.md:256` 的“命中 8 行（初稿误记 3 条）”一致；8 条均为否定/正确表述，不构成旧规则。
2. **§5.2（Scenario 数）**：报告 `:151` 记为“新增 3 个 Requirement / 6 个 Scenario（`spec.md:17,21,28,32,39,43`；初稿误记 5 个）”。核对 `specs/completion-gate/spec.md`：新增段落（行 14–45）确为 3 个 Requirement / 6 个 Scenario；文件整体另有既存 “Binary completion gate” 的 1 Requirement / 2 Scenario，与“新增”口径不冲突。
3. **C-19 / §9.7**：`openspec-v2-sync.md:117` 与 `:363` 均已改为“`source-reconciliation.md` 已由 P0-02 落盘（28582 字节），链接可解析”，不再声称文件不存在。
4. **§8.7 行数口径**：`wc -l docs/delivery/openspec-v2-sync.md` = **425**，与报告 `:310` 记录的“返工后为 425 行”一致。

**F3 关闭。**

### 3.5 V5 — git 空白检查

```bash
git diff --check
# （无输出）
# EXIT=0
```

补充只读扫描：`grep -rnP "[ \t]+$"` 覆盖 `docs/VERSIONING.md`、`docs/delivery/openspec-v2-sync.md`、`docs/v2/SOLUTION.md`、`docs/v2/IMPLEMENTATION-PLAN.md`、`openspec/.../design.md`、`openspec/.../specs/completion-gate/spec.md`，命中 **0** 处。**通过。**

---

## 4. 历史保留声明

- 原始验证报告 `docs/delivery/p0-03-verification.md` 的 **NEEDS-FIX** 判定与 F1/F2/F3 正文原样保留，未修改、未删除。
- 证据报告 `docs/delivery/openspec-v2-sync.md` 保留初稿“误记 + 复核实测”的并列记录（如 §8.3 “初稿误记 3 条”，§8.7 “初稿 362 行 → 返工后 425 行”），未静默改写历史。
- 本文件仅新增为修复后复验记录，不替代原始 NEEDS-FIX 报告。

---

## 5. 限制

1. 仓库中 `docs/VERSIONING.md`、`docs/delivery/openspec-v2-sync.md` 仍为**未跟踪路径**（`git status` 显示 `??`），因此 `git diff --check` 只覆盖已跟踪文件；未跟踪变更另用行尾空白扫描补充，结果为 0。
2. 本复验只覆盖原报告 F1/F2/F3 与指定五项检查，未重做 §3 全量通过项，也未评价 P0-04..P0-11。
3. 未运行产品代码、单元/集成测试、真机烟测、部署或发布；PASS 仅指文档结构与一致性范围。
4. 未读取或修改 `docs/ssh.txt` 及任何凭据内容。
5. 未执行 commit / push。

---

## 6. 复验命令清单（本次实际执行）

```bash
cd /home/bszheng/NoahsArk

# V1 六项规则
grep -nE "五轴|离线|STOP|cleanup_receipt|清理回执|设备释放" docs/VERSIONING.md
grep -n "^| [1-6] |" docs/VERSIONING.md

# V2 formal PASS 四处
grep -rn "Formal PASS\|正式 PASS" docs/v2 openspec --include=*.md
grep -n "execution_status=COMPLETED" docs/v2/SOLUTION.md \
  docs/v2/IMPLEMENTATION-PLAN.md \
  openspec/changes/ai-test-platform-v2/design.md \
  openspec/changes/ai-test-platform-v2/specs/completion-gate/spec.md

# V3 strict 校验（需 nvm node 路径）
export PATH="/home/bszheng/.nvm/versions/node/v24.14.1/bin:$PATH"
openspec validate ai-test-platform-v2 --strict

# V4 计数与 C-19
grep -rniE "lease (expiry|expiration) (reclaims|releases|stops)|heartbeat (loss|expiry) (stops|fails|releases)|心跳(过期|超时).*(停止|失败|回收|释放)|租约(过期|到期).*(回收|释放|停止|失败)|missing cleanup_receipt (means|makes).*(all )?evidence incomplete|缺.*cleanup_receipt.*(等同于|视为).*证据不完整" \
  docs/v2 openspec --include=*.md | wc -l
grep -nE "8\.3|5\.2|6 Scenario|C-19|9\.7|source-reconciliation" docs/delivery/openspec-v2-sync.md
wc -l docs/delivery/openspec-v2-sync.md

# V5 空白
git diff --check
grep -rnP "[ \t]+$" docs/VERSIONING.md docs/delivery/openspec-v2-sync.md \
  docs/v2/SOLUTION.md docs/v2/IMPLEMENTATION-PLAN.md \
  openspec/changes/ai-test-platform-v2/design.md \
  openspec/changes/ai-test-platform-v2/specs/completion-gate/spec.md | wc -l
```
