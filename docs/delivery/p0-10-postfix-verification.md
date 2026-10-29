# P0-10 修正后复验报告：`docs/delivery/environment-inputs.md`

> 复验对象：`docs/delivery/environment-inputs.md`（484 行，UTF-8/LF，文件大小 38947 字节，mtime 2026-10-29 07:38:28 +0800）
> 对照基准：[`p0-10-verification.md`](./p0-10-verification.md) 原始判定 **NEEDS-FIX** 及其 F1–F4（该报告 §10 仅记录修正内容，不替换原始判定）
> 复验日期：2026-10-29（Asia/Shanghai）
> 复验范围：**仅复核 F1–F4 的修正是否成立**，以及计数、L01 状态、A-0 口径是否被意外改动。
> 复验边界：不验证环境是否就绪，不构成 A-0 通过、L3/L4/L5 准入、测试执行或发布授权。
> 操作边界：只读复核；**未修改** `environment-inputs.md`、契约、`plan.md`、`.omo/`、产品代码；未 commit、未 push。

---

## 1. 判定

**PASS（仅针对 F1–F4 的修正）**。

F1、F2、F3、F4 四项均已按原报告要求修正，且可独立复现；85 行结构、计数口径（`20 known / 14 placeholder / 51 unknown`，合计 85）与唯一预期变化（L01 由 `known` 降为 `placeholder`）一致；未引入密钥/主机值；A-0 仍为未通过。

**该 PASS 不表示** `environment-inputs.md` 已通过独立验证（原始报告判定仍为 NEEDS-FIX）、不表示 A-0 通过、不表示环境就绪，也不覆盖原报告 §6 的 M1–M5 未修项。

---

## 2. F1–F4 逐项复验

| # | 原始缺陷 | 修正后位置与内容 | 独立复核证据 | 结果 |
|---|---|---|---|---|
| F1 | 把本地 `main` `f32aebc` 当成 `origin/main` | `:56`、`:205`、`:335` 均改为“本地 `main` HEAD `f32aebc`（2026-10-14）；`origin/main` `7190ab6`（2026-08-18），本地领先 1 个提交”；S18（`:475`）补入 `branch -vv`、`for-each-ref` | `git -C .../lstest branch -vv` → `* main f32aebc [origin/main: ahead 1]`；`for-each-ref` → `refs/heads/main f32aebc 2026-10-14`、`refs/remotes/origin/main 7190ab6 2026-08-18`、`origin/HEAD 7190ab6` | **PASS** |
| F2 | “10 个子命令”混淆顶层与嵌套 | `:57`、`:209`、`:339` 改为“7 个顶层子命令（`list`、`tts`、`tts-manifest`、`audio`、`preflight`、`init`、`smoke`）+ `audio` 下 5 个嵌套子命令（`ensure-laid`、`scan`、`probe`、`play`、`dual-play`）”；全文已无“10 个子命令”字样 | `lstest.py --help` → `{list,tts,tts-manifest,audio,preflight,init,smoke}`（7）；`lstest.py audio --help` → `{ensure-laid,scan,probe,play,dual-play}`（5）；`grep '10 个子命令'` 无命中 | **PASS** |
| F3 | L01 标 `known` 但阻塞 L3，且无受限记录指针 | 采用原报告“选项 2”：`:84`、`:272` 改为 `placeholder`（“身份已口头确认，值未登记”），保留“是（L3）”，来源列写明“受限记录建立前不得转 `known`”；未虚构记录 ID/日期/核验人，未写入任何主机名/IP | 状态列解析为 `placeholder`；`:268` 阻塞定义与“是（L3）”自洽；全表 `L` 类状态由 11/3/4 变为 10/4/4，仅 L01 一项迁移 | **PASS** |
| F4 | E03/D07/T06/R06 无行级来源编号 | `:292` E03 → `S1 §5.4；S11 §12`；`:329` D07 → `S3 §5.3；S11 §10`；`:340` T06 → `S10 §8.4；S15 §6.3`；`:354` R06 → `S1 §4（AC-11/AC-12）；S7`（均在来源列，且保留原备注文本） | 脚本按 8 列解析 85 行后逐行检查来源列，**0 行**缺少 `S\d+` 编号；`AC-11/AC-12` 实测位于 `.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md` §4（第 73–74 行），与 R06 引用一致 | **PASS** |

> F4 备注（不影响判定）：R06 引用的 `S1 §4` 内容成立，但 §14 来源索引（`:458`）为 S1 列出的章节为“§1、§2.1、§3、§5.1、§5.4、§5.6”，未含 §4；§4 在 S7（`:464`，“同上 §3、§4（L0–L5、AC-1..AC-14）”）下被索引。因 S1 与 S7 指向同一文件，检索仍可到达，属索引书写余量。

---

## 3. 计数与状态一致性（确认无意外改动）

按 `^\| [LWEDTNR]\d{2} \|` 解析 §9 汇总表（`:271-356`）：

```text
rows 85
bad col count []
states {'known': 20, 'placeholder': 14, 'unknown': 51}
missing owner []   missing block []   dup ids []
prefix {'L': 18, 'E': 14, 'W': 19, 'D': 12, 'T': 8, 'N': 6, 'R': 8}
```

分类明细与原始报告 §5.1 的差异只有 L01 一行：

| 前缀 | 原始报告 | 本次实测 | 差异 |
|---|---|---|---|
| L | 11 known / 3 placeholder / 4 unknown | **10 / 4 / 4** | 仅 L01 `known`→`placeholder` |
| E | 5 / 2 / 7 | 5 / 2 / 7 | 无 |
| W | 0 / 5 / 14 | 0 / 5 / 14 | 无 |
| D | 0 / 2 / 10 | 0 / 2 / 10 | 无 |
| T | 5 / 0 / 3 | 5 / 0 / 3 | 无 |
| N | 0 / 1 / 5 | 0 / 1 / 5 | 无 |
| R | 0 / 0 / 8 | 0 / 0 / 8 | 无 |

| 检查点 | 结果 |
|---|---|
| §9.1（`:362-365`）= `20/14/51/85` | 与脚本重算一致 |
| §15 最新变更记录（`:484`）= “85 条（20 known / 14 placeholder / 51 unknown）” | 与表一致 |
| §15 历史记录（`:483`）仍写“21 known / 13 placeholder / 51 unknown” | 属 2026-10-28 建表历史，非当前状态，**不算矛盾** |
| 真实硬件 W/D/R 仍 0 `known` | 保持，未出现“缺硬件标完成” |
| 无重复 ID、无空负责人/阻塞列、8 列结构完整 | 保持 |

结论：`known / placeholder / unknown` 三态总量相对修正前仅发生“1 行从 known 迁到 placeholder”的**已被声明**变化，合计 85 不变，其余 84 行状态未变。

---

## 4. A-0 与门禁口径

| 检查点 | 证据 | 结果 |
|---|---|---|
| 清单自述 | `:5`“清单已建立，环境未就绪，A-0 未通过”；`:76`“本文不声称 A-0 通过” | 保持 |
| §11 签署清单 | `:394-407` 10 个复选框全部 `[ ]`；`:396`“勾选只表示已登记/已决定，不表示 A-0 已通过” | 保持，A-0 未通过 |
| §10 可开工 vs §12 L3/L4/L5 | `:367-381` / `:409-439` 两套清单未混写 | 保持 |
| 计划台账 | `.omo/plans/noahsark-platform-delivery.md:32` 仍为 `- [ ]` | 未勾选 |
| 进度台账 | `docs/delivery/construction-progress.md:20`“返工中……A-0 仍未通过” | 口径一致 |

**A-0 仍未通过**，且本次复验不改变该结论。

---

## 5. 回归检查

| 检查 | 命令/方法 | 结果 |
|---|---|---|
| 无密钥/主机值泄漏 | `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}\|password\|passwd\|secret\|token[[:space:]]*[=:]\|BEGIN (RSA\|OPENSSH\|PRIVATE)\|ssh://'` | 无命中（F1–F4 新增文本未引入凭据或 IP） |
| 无过度宣称 | `grep -nE '已就绪\|已具备\|已通过\|已完成\|已部署\|已实现'` | 仅命中 `:21`、`:23`、`:396` 三处规则性否定句 |
| 编码/行尾 | `file`、CR 计数、行尾空白扫描 | UTF-8，CR=0，无行尾空白；GBK/乱码未出现 |
| 行级来源完整性 | 85 行来源列匹配 `S\d+` | 85/85 命中，0 缺失 |
| 未修改被验对象 | `stat` mtime 仍为 2026-10-29 07:38:28；本轮仅读取 | 未改动 |

---

## 6. 限制

1. 本报告**只复核 F1–F4 的修正结果**，不重新做原报告 §4 的 13 项来源抽查，也不复核 M1–M5；原报告 **NEEDS-FIX** 判定在未被新证据推翻前仍然有效。
2. F1 的“本地 main vs origin/main”复核对象是 `lstest` 仓库（`/home/bszheng/aitest/vendor/lstest`）；NoahsArk 仓库本身在本地没有 `refs/remotes/origin/main` 引用（`git rev-parse --verify origin/main` 报 `Needed a single revision`），因此无法在本地证明 NoahsArk 与 `origin/main` 的同步状态。
3. 未验证真实 Windows 节点、设备、PostgreSQL、NAS、第二服务器、证书或网络；这些在本环境不可用。
4. `docs/delivery/` 为未跟踪目录，`git diff` 无法证明“未修改被验对象”；依据是只读操作与未变化的 mtime/大小。
5. 本机事实与 lstest 引用是 2026-10-29 快照；任一变化后 T01/L02–L04/L11/L12 等 `known` 需重新登记。
6. 未接触 `docs/ssh.txt` 或任何凭据。

---

## 7. 非阻塞跟进项（不在本次修改范围）

1. `docs/delivery/construction-progress.md:25` 仍写“85 条登记（21 known / 13 placeholder / 51 unknown）”，与修正后的 `20/14/51` 不一致，建议下次进度更新时同步。
2. `p0-10-verification.md` §10 已如实记录“20/14/51”，与清单一致；但该报告正文 §5.1、C1 保留修正前快照，阅读时需以 §10 为准（原始报告已声明不替换判定）。
3. 上游 `S10 §8.4`（`.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md:165`）仍沿用“`f32aebc` 为 origin/main”的错误；清单内已改正，但来源文档未改，建议在后续文档同步中登记。
4. §14 的 S1 章节索引未含 §4（R06 引用 `S1 §4`），可通过 S7 到达；可在下一次维护时补全索引。
5. `.omo/plans/noahsark-platform-delivery.md:32` 的 P0-10 仍未勾选，`construction-progress.md` 状态仍为“返工中”，需由主控在独立验证通过后更新。

---

## 8. 可复现命令

```bash
cd /home/bszheng/NoahsArk

# F1：本地 main 与 origin/main
git -C /home/bszheng/aitest/vendor/lstest branch -vv
git -C /home/bszheng/aitest/vendor/lstest for-each-ref \
  --format='%(refname) %(objectname:short) %(committerdate:short)' refs/heads refs/remotes

# F2：7 + 5 命令树
python3 /home/bszheng/aitest/vendor/lstest/scripts/lstest.py --help
python3 /home/bszheng/aitest/vendor/lstest/scripts/lstest.py audio --help
grep -n '10 个子命令' docs/delivery/environment-inputs.md   # 期望无输出

# F3/F4、计数与结构
python3 - <<'EOF'
import re, collections
lines = open('docs/delivery/environment-inputs.md', encoding='utf-8').read().splitlines()
rows = []
for i, l in enumerate(lines, 1):
    if re.match(r'^\| [LWEDTNR]\d{2} \|', l):
        rows.append((i, [c.strip() for c in l.strip().strip('|').split('|')]))
print('rows', len(rows))
print('bad', [(i, len(c)) for i, c in rows if len(c) != 8])
print('states', dict(collections.Counter(c[4].strip('`') for i, c in rows)))
print('dup', [k for k, v in collections.Counter(c[0] for i, c in rows).items() if v > 1])
print('no-src', [c[0] for i, c in rows if not re.search(r'\bS\d+\b', c[7])])
EOF

# L01 / F4 具体行 / §9.1 / A-0
sed -n '84p;268,272p;292p;329p;340p;354p;362,365p;394,407p' docs/delivery/environment-inputs.md

# 回归：敏感值、过度宣称、编码
grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|password|passwd|secret|token[[:space:]]*[=:]|BEGIN (RSA|OPENSSH|PRIVATE)|ssh://' docs/delivery/environment-inputs.md
grep -nE '已就绪|已具备|已通过|已完成|已部署|已实现' docs/delivery/environment-inputs.md
file docs/delivery/environment-inputs.md
stat -c '%y %s' docs/delivery/environment-inputs.md
```
