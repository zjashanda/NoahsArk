# Phase 0 候选归档独立复核报告

> 复核日期：2026-10-29
> 复核对象：`.omo/drafts/99-history/20261029-phase0-candidate/`（P0-11 候选快照）
> 复核性质：只读独立复核。未修改归档、未修改任何源文件、未提交、未推送、未联网。
> 结论摘要：**归档可确认为 candidate-only 文档快照；未发现实现冻结、测试通过、Phase 0 关闭或生产就绪的错误暗示。完整性在归档时点成立；复核时发现 1 个源文件在归档后被继续编辑，属预期快照漂移，不是归档损坏。**

## 1. 复核范围与方法

| 项目 | 方法 |
|---|---|
| 归档目录清单 | `find` 全量枚举（含隐藏文件、符号链接） |
| 哈希完整性 | `sha256sum -c SHA256SUMS.md` |
| 副本一致性 | 对 56 个归档文件逐一执行 `cmp -s` 与 README §6 声明的源路径比对 |
| 覆盖数量 | 按目录计数，与 README §6 表格逐项核对 |
| 排除项 | 文件名/扩展名扫描 + 内容特征扫描（仅统计命中数，不输出敏感内容） |
| 候选边界 | 阅读 README、`SHA256SUMS.md`、归档的 `construction-progress.md`，检索“冻结/完成/权威”类表述的限定语 |
| 空白字符 | `git diff --check --no-index /dev/null <本报告>` |

## 2. 文件数量与哈希

- 归档目录文件总数：**58**
  - 载荷副本：**56**
  - 元文件：`README.md`、`SHA256SUMS.md`（2）
- `SHA256SUMS.md` 条目数：**56**，与载荷文件数一致。
- `sha256sum -c SHA256SUMS.md`：**56/56 OK，退出码 0**（无 FAILED、无缺失条目）。
- 哈希清单不包含 `README.md` 与 `SHA256SUMS.md` 自身，与 README §6/§8 声明一致。
- 无符号链接、无重复条目、无清单外载荷文件。

分目录计数（与 README §6 完全一致）：

| 目录 | 归档数 | README 声明 | 结果 |
|---|---:|---:|---|
| `01-contracts/` | 42 | 42 | 一致 |
| `02-source-sync/` | 6 | 6 | 一致 |
| `03-environment/` | 3 | 3 | 一致 |
| `04-decisions/` | 2 | 2 | 一致 |
| `05-ui-preparation/` | 2 | 2 | 一致 |
| `06-progress/` | 1 | 1 | 一致 |
| **合计** | **56** | **56** | 一致 |

契约分族核对：`domain 12 / security 9 / evidence 7 / experience 6 / config 1 = 35` JSON Schema；加 6 个 Markdown（`README.md`、`domain.md`、`security-node.md`、`evidence-verdict.md`、`ui-report-knowledge-audit.md`、`thresholds.md`）共 41，再加 `phase0-contract-remediation-verification.md` 共 42。与 README §6 一致。

## 3. 副本与源文件比对

比对映射按 README §6 执行：

| 归档路径 | 源路径 | 结果 |
|---|---|---|
| `01-contracts/`（除 remediation 报告） | `docs/contracts/` | 41/41 一致 |
| `01-contracts/phase0-contract-remediation-verification.md` | `docs/delivery/phase0-contract-remediation-verification.md` | 一致 |
| `02-source-sync/VERSIONING.md` | `docs/VERSIONING.md` | 一致 |
| `02-source-sync/` 其余 5 份 | `docs/delivery/` 同名文件 | 5/5 一致 |
| `03-environment/` 3 份 | `docs/delivery/` 同名文件 | 3/3 一致 |
| `04-decisions/noahsark-v0.0.1-decision-register.md` | `.omo/drafts/05-decisions/` 同名文件 | 一致 |
| `04-decisions/p0-09-decision-reconciliation.md` | `docs/delivery/` 同名文件 | 一致 |
| `05-ui-preparation/` 2 份 | `docs/delivery/` 同名文件 | 2/2 一致 |
| `06-progress/construction-progress.md` | `docs/delivery/construction-progress.md` | **不一致（见 §4）** |

汇总：**55/56 与当前源文件逐字节一致；1 个漂移**。所有 56 个副本与 `SHA256SUMS.md` 登记值一致，说明漂移发生在源文件侧，而非归档副本被改动。

## 4. 发现的唯一不一致：`06-progress/construction-progress.md`

- 归档副本 mtime：2026-10-29 08:29（归档目录建于 08:30）。
- 当前源文件 mtime：2026-10-29 12:53，晚于归档。
- 差异方向：源文件新增后续工作记录（Phase 1 会话、非 UI 并行批次、重启检查点），并把 P0-11 从“已派发”改为“已完成（候选归档）”。
- 归档副本仍保留归档时点文本：P0-11 为“已派发”、备注“不提前宣称 Phase 0 关闭”。
- 判定：**预期快照漂移，不是归档损坏、不是篡改、不构成阻断**。归档 README §4 已规定“源文件变化后应另行建立新的日期归档，不修改本目录”，本次未做任何回写。
- 影响：README §8 第 1 条“56 个副本逐一与源文件 `cmp -s`，全部字节一致”仅在**归档时点**成立；复核时点该句对 1 个文件不再成立。建议后续引用时注明“归档时点一致”，不要据此断言当前源状态。

## 5. 敏感与无关文件排除检查

### 5.1 路径/扩展名

| 检查项 | 结果 |
|---|---|
| `docs/ssh.txt` 副本 | 0（该文件当前也不在仓库内） |
| 隔离区 `/tmp/opencode/quarantine/` 文件内容 | 0（未收录；目录内实际存在 1 个 ssh 隔离文件，未被带入） |
| `*.log`、`*.wav`、`*.mp3`、`*.pcap` 等原始日志/音频/抓包 | 0 |
| 截图/图片（`*.png`/`*.jpg` 等） | 0 |
| 私钥/证书/密钥库（`*.pem`/`*.key`/`*.crt`） | 0 |
| 数据库/配置（`*.db`/`*.sqlite*`/`*.sql`/`*.env`） | 0 |
| 产品代码（`*.py`/`*.js`/`*.ts`/`*.go`/`*.rs` 等） | 0；56 个载荷全部为 `.md`/`.json` |
| `workspace-triage.md`、`phase0-contract-verification.md` | 0（按 §7 排除） |
| 根 `plan.md`、`.omo/plans/`、`.omo/boulder.json` | 0 |
| 符号链接 | 0 |

### 5.2 内容特征（仅统计命中文件数，未打印内容）

| 特征 | 命中文件数 |
|---|---:|
| `BEGIN ... PRIVATE KEY` / `BEGIN OPENSSH PRIVATE KEY` | 0 |
| `ssh-rsa` / `ssh-ed25519` / `IdentityFile` | 0 |
| AWS/GitHub/OpenAI/Slack 风格令牌前缀 | 0 |
| 邮箱地址模式 | 0 |
| IPv4 地址模式 | 0 |
| 明文口令/API key 赋值模式 | 0 |

说明：

- 归档中有 **10 个文件** 提到 `docs/ssh.txt`（多为“已隔离、未收录”的政策性引用），有 **2 个文件** 提到 `/tmp/opencode/quarantine`（`README.md` 与归档的 `construction-progress.md`）。这些是**路径/文件名引用**，不是凭据或文件内容；归档内不存在被引用文件本身。
- 有 10 个文件出现 `/home/bszheng/NoahsArk` 形式的仓库绝对路径，属文档溯源信息，非个人信息或凭据。
- `docs/ssh.txt` 当前不存在于仓库工作区，隔离区文件未被读取其内容，仅核对了目录元数据。

## 6. 是否 candidate-only

**是。** 依据：

1. README 顶部状态明确：`candidate-only，历史候选证据`，并逐项声明“不是生产冻结件、不是 implementation-authoritative、不构成实现/测试/部署/验收/发布授权”。
2. 契约被持续标注为 `frozen-candidate v1`，并声明 35/35 schema 通过“不证明所有者批准或生产冻结”。
3. README §3 将 P0-11 标为“已派发（未完成）”，并明确“本目录只是候选证据，不构成 P0-11 完成或 Phase 0 关闭”。
4. README §5 保留 5 个开放阻塞（T-09..T-12、T-23），任一未关闭都不得称 Phase 0 完成。
5. `SHA256SUMS.md` 头部声明哈希“不证明源文件正确、契约获批、实现存在或测试通过”。
6. A-0 被明确标注“未通过”，P0-10 的 PASS 限定在 F1-F4。

未发现任何把归档称为“Phase 0 已归档/已完成/生产契约/实施权威”的表述。

## 7. 是否错误暗示实现冻结

**否。** 逐项核对：

- 归档内“冻结”类词只出现在限定语境：`frozen-candidate`（契约候选）、Phase 1 的“冻结”作为**未来门禁名称**、以及 README 中反复出现的否定句“不是生产冻结件”。
- 归档的 `construction-progress.md` 在归档时点对 P0-11 记为“已派发”，比当前源文件更保守，不会让读者误以为 P0-11 已完成。
- 归档 README 明确“不证明代码存在、测试执行、设备可用、部署完成或发布就绪”。
- 未发现 `PASS` 被扩大解释为功能实现或验收通过；原始 `NEEDS-FIX` 报告被保留且声明不可被 post-fix 的限定 PASS 覆盖。

唯一需要提示的措辞风险：归档 README §8 的 `cmp` 全一致结论是**归档时点**结论，若被脱离语境引用，可能让人误以为“当前源仍与归档一致”。这是时效性表述问题，不构成实现冻结暗示。

## 8. 复现命令

```bash
cd .omo/drafts/99-history/20261029-phase0-candidate
find . -type f | wc -l                 # 58
grep -cE '^[0-9a-f]{64}  \./' SHA256SUMS.md   # 56
sha256sum -c SHA256SUMS.md             # 56/56 OK, exit 0

cd /home/bszheng/NoahsArk
cmp -s .omo/drafts/99-history/20261029-phase0-candidate/06-progress/construction-progress.md \
       docs/delivery/construction-progress.md   # exit 1（预期漂移）

git diff --check --no-index /dev/null docs/delivery/candidate-archive-followup-verification.md
```

## 9. 结论与遗留

- **归档完整性：通过。** 56/56 哈希匹配；56 个载荷齐备；分目录计数与声明一致；无敏感文件、无隔离区内容、无凭据、无原始日志/音频、无产品代码。
- **归档性质：candidate-only，确认。**
- **实现冻结暗示：不存在。**
- **唯一不一致：** `06-progress/construction-progress.md` 在归档后源文件被继续编辑（55/56 一致，1 漂移）。属预期快照漂移，**不阻断**，归档本身未被修改。
- **建议（不执行）：**
  1. 引用 README §8 时注明“归档时点一致”。
  2. 若需反映当前 P0-11 状态，另建新的日期归档；不要回写本目录。
  3. 本报告不代表 P0-11 完成、Phase 0 关闭、契约冻结或实现就绪。
