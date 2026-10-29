# P0-01 工作区安全分诊报告

> 任务：P0-01 工作区安全分诊
> 执行时间：2026-10-28（Asia/Shanghai）
> 仓库：`/home/bszheng/NoahsArk`
> 边界：只做分诊与敏感文件隔离；未修改产品源码，未暂存、未提交、未推送，未回退其他文件。
> 敏感原则：本报告不包含 `docs/ssh.txt` 的任何内容、主机名、用户名、IP 值或口令值。

## 1. 仓库基线

### 1.1 分支与远端

命令（所有 git 命令均带 `GIT_MASTER=1` 前缀）：

```bash
GIT_MASTER=1 git branch --show-current
GIT_MASTER=1 git rev-parse --short HEAD
GIT_MASTER=1 git remote -v
GIT_MASTER=1 git rev-parse --abbrev-ref '@{upstream}'
```

结果：

| 项目 | 值 |
|---|---|
| 当前分支 | `main` |
| HEAD | `8c3310f` |
| 远端 `origin` fetch | `https://github.com/zjashanda/NoahsArk.git` |
| 远端 `origin` push | `https://github.com/zjashanda/NoahsArk.git` |
| upstream | `fatal: no upstream configured for branch 'main'` |
| 暂存区 | 空（`git diff --cached --stat` 无输出） |

远端 URL 为公开 HTTPS 形式，未包含用户名、令牌或密码。

### 1.2 初始工作区快照（隔离 `docs/ssh.txt` 之前）

```bash
GIT_MASTER=1 git status --short
GIT_MASTER=1 git diff --stat
GIT_MASTER=1 git diff --name-status
GIT_MASTER=1 git status --porcelain=v1 -uall
```

`git status --short` 初始结果：

```text
 M README.md
 M docs/v2/wireframes/README.md
 D "自动化生成测试用例流程图.svg"
?? docs/VERSIONING.md
?? docs/delivery/
?? docs/references/
?? docs/ssh.txt
```

`git diff --stat` 初始结果：

```text
 README.md                                          |  11 +
 docs/v2/wireframes/README.md                       |   2 +-
 "自动化生成测试用例流程图.svg"                      | 249 ---------------------
 3 files changed, 12 insertions(+), 250 deletions(-)
```

`git diff --name-status` 初始结果：

```text
M	README.md
M	docs/v2/wireframes/README.md
D	"自动化生成测试用例流程图.svg"
```

`git diff --numstat`：

```text
1	0	.gitignore                    # 本任务新增，见 §5
11	0	README.md
1	1	docs/v2/wireframes/README.md
0	249	"自动化生成测试用例流程图.svg"
```

未跟踪文件（`git ls-files --others --exclude-standard`，隔离后）：

```text
docs/VERSIONING.md
docs/delivery/construction-progress.md
docs/references/README.md
docs/references/diagrams/自动化生成测试用例流程图.svg
```

隔离前未跟踪清单还包含 `docs/ssh.txt`；隔离并加入 `.gitignore` 后不再出现在 `git status` 中。

### 1.3 `.gitignore` 检查

命令：

```bash
GIT_MASTER=1 git check-ignore -v .omo/ .omo/plans/noahsark-platform-delivery.md docs/ssh.txt docs/VERSIONING.md docs/references/README.md
```

结果（隔离并追加规则后）：

```text
.gitignore:1:.omo/	.omo/
.gitignore:1:.omo/	.omo/plans/noahsark-platform-delivery.md
.gitignore:22:docs/ssh.txt	docs/ssh.txt
```

结论：

- `.omo/` 已被忽略，且 `.omo/plans/noahsark-platform-delivery.md` 与 `.omo/drafts/...` 都属于忽略范围。
- `docs/VERSIONING.md`、`docs/references/README.md` 未被忽略，仍为可提交的未跟踪文件。
- `.gitignore` 本身已被 git 跟踪（`git ls-files --error-unmatch .gitignore` 成功）。

## 2. 路径分类

| 路径 | 状态 | 分类 | 证据 | 建议动作 |
|---|---|---|---|---|
| `README.md` | 已修改（+11/-0） | legitimate planning artifact | 新增内容只增加 `docs/VERSIONING.md`、`docs/references/` 和“现有入口”链接；链接目标均存在；与 `docs/VERSIONING.md` 第 3 节目录树一致；计划 P0-03 明确使用 `docs/VERSIONING.md`。 | 保留。P0-03 同步规范文档时再复核链接。 |
| `docs/v2/wireframes/README.md` | 已修改（+1/-1） | legitimate planning artifact | 仅把 `../../design/wireframes/README.md` 修正为 `../../../design/wireframes/README.md`。原路径从 `docs/v2/wireframes/` 解析到 `docs/design/`（不存在）；新路径解析到仓库根 `design/wireframes/README.md`（存在，4865 bytes）。 | 保留。属于文档链接修复，不涉及产品语义。 |
| `自动化生成测试用例流程图.svg`（根目录） | 已删除（-249 行） | legitimate planning artifact | 删除前 HEAD 版本 SHA-256 为 `86e98aa6a1878d666801237d8ca22caaed1684fa19d1bca89f2d1fb5011d3e8d`；`docs/references/diagrams/自动化生成测试用例流程图.svg` 的 SHA-256 完全相同，字节数同为 19271。`docs/VERSIONING.md` §8 明确记录“把无其他入站引用的根目录参考图移入 `docs/references/diagrams/`”。除 `docs/VERSIONING.md` 与 `docs/references/README.md` 指向新位置外，仓库内未发现指向旧根路径的入站引用。 | 保留删除；新路径文件未跟踪，后续按文档整理提交时作为重命名处理（不要用 `git rm` 造成内容丢失）。 |
| `docs/VERSIONING.md` | 未跟踪 | legitimate planning artifact | 文件 9652 bytes，内容为目录状态、规范优先级、目标目录、三段式方案版本规则、发布不可变性和提交边界；被 `README.md` 引用；计划 P0-03 明确要求把规范同步写入 `docs/VERSIONING.md`。 | 保留。P0-03 阶段更新其规范内容。 |
| `docs/references/` | 未跟踪目录 | legitimate planning artifact | `docs/references/README.md`（641 bytes）说明该目录保存跨版本参考资料、不替代 v2 基线和 `solutions/1027V1/NOAHSARK-V1-TOTAL-FLOW.svg`；`docs/references/diagrams/` 内含与根目录旧图字节一致的流程参考图；目录结构与 `docs/VERSIONING.md` §3 一致。 | 保留。 |
| `docs/delivery/construction-progress.md` | 未跟踪 | legitimate planning artifact | 2054 bytes，含 P0-01..P0-11 行，与 `.omo/plans/noahsark-platform-delivery.md` 的 Phase 0 编号一一对应；计划 §0 要求持续写入该进度表。 | 保留。本任务只在其 P0-01 行追加证据说明。 |
| `docs/ssh.txt` | 未跟踪（已隔离） | sensitive | 2579 bytes、47 行；`git ls-files --error-unmatch docs/ssh.txt` 失败，`git log --all -- docs/ssh.txt` 为空，说明从未被 git 跟踪；第 12 行命中口令类关键字（仅记录类别与行号，不记录值）；第 14–26 行含 IP 地址形态字符串；未发现 `BEGIN ... PRIVATE KEY` 或 OpenSSH 公钥材料标记。 | 已移动到 `/tmp/opencode/quarantine/noahsark-ssh-48308fa0.txt`，权限 600；`.gitignore` 增加 `docs/ssh.txt`。见 §4、§5。 |
| `.gitignore` | 已修改（+1/-0） | sensitive（本任务防护性改动） | 本任务追加 `docs/ssh.txt` 一行。该路径从未被跟踪，追加规则不会掩盖任何已跟踪的合法文件。 | 保留本次改动；属于 P0-01 隔离动作，不是代理越界。 |

### 2.1 是否存在 agent scope creep

未发现需要回退的代理越界改动。判定依据：

1. 所有非敏感改动均为文档或文档目录重组，没有产品源码、配置、依赖或测试改动。
2. `docs/VERSIONING.md`、`docs/references/`、`README.md` 的链接与目录树互相一致，并且被执行计划引用。
3. 根目录 SVG 的“删除”是字节一致的移动，不是内容丢失。
4. 唯一无法从计划直接推出的是 `docs/v2/wireframes/README.md` 的相对链接深度修正；但其改动只有一行，且修正后目标真实存在，属于低风险文档修复，不构成需回退的 scope creep。
5. `.omo/drafts/99-history/20261028-step4-step6-review/` 已存在（含 README、审核记录、SHA256SUMS），本次分诊不涉及该归档内容。

## 3. 敏感文件检查（`docs/ssh.txt`）

### 3.1 哈希、行数与权限

命令：

```bash
sha256sum docs/ssh.txt
wc -l docs/ssh.txt
wc -c docs/ssh.txt
file docs/ssh.txt
stat -c '%a %U:%G %s %n' docs/ssh.txt
```

隔离前结果：

| 项目 | 值 |
|---|---|
| SHA-256 | `48308fa010348a028b9dabf5d66f2e3745f177ae485c8f0f4b36b5ace0781008` |
| 行数（`wc -l`） | 47 |
| 字节数 | 2579 |
| 文件类型 | Unicode text, UTF-8 (with BOM), CRLF/LF 混合 |
| 隔离前权限 | `664 bszheng:bszheng` |

### 3.2 凭据类内容判定（仅类别与行号）

使用带脱敏输出的模式匹配，只记录命中类别，不输出命中文本：

| 行号 | 命中类别 | 说明 |
|---|---|---|
| 12 | 口令类关键字（`Password`） | 该行长度为 91 字符，不含 `:` 或 `=` 分隔符，形态更像命令行/说明文本中的口令材料；按敏感处理。 |
| 14–26 | IP 地址形态 | 多行包含 IPv4 形态字符串，可能暴露内网拓扑；本报告不记录具体地址。 |
| — | 私钥标记 | 未命中 `BEGIN ... PRIVATE KEY`。 |
| — | OpenSSH 公钥材料 | 未命中 `ssh-rsa` / `ssh-ed25519` 公钥行。 |
| — | Token/API key 赋值 | 未命中 `token=`、`api_key=` 等赋值形态。 |

结论：**包含口令类敏感内容**，且伴随主机/IP 信息，不能提交到仓库，也不能出现在报告中。已按任务要求隔离。

> 本报告有意不记录第 12 行原文、用户名、主机名、IP 值、端口或任何命令片段。

## 4. 隔离记录

| 项目 | 值 |
|---|---|
| 原始路径 | `docs/ssh.txt` |
| 原始 SHA-256 | `48308fa010348a028b9dabf5d66f2e3745f177ae485c8f0f4b36b5ace0781008` |
| 原始大小 | 2579 bytes / 47 行 |
| 隔离路径 | `/tmp/opencode/quarantine/noahsark-ssh-48308fa0.txt` |
| 隔离后 SHA-256 | `48308fa010348a028b9dabf5d66f2e3745f177ae485c8f0f4b36b5ace0781008`（一致） |
| 隔离后权限 | `600` |
| 隔离目录权限 | `700` |
| 是否曾跟踪 | 否（`git ls-files --error-unmatch` 失败；`git log --all` 无记录） |
| `.gitignore` 处理 | 追加 `docs/ssh.txt`；`git check-ignore -v` 命中 `.gitignore:22` |
| 内容复制 | 无；仅移动，未打印、未复制到报告 |

执行命令：

```bash
mkdir -p /tmp/opencode/quarantine
chmod 700 /tmp/opencode/quarantine
SHA=$(sha256sum docs/ssh.txt | awk '{print $1}')
mv docs/ssh.txt "/tmp/opencode/quarantine/noahsark-ssh-${SHA:0:8}.txt"
chmod 600 "/tmp/opencode/quarantine/noahsark-ssh-${SHA:0:8}.txt"
sha256sum "/tmp/opencode/quarantine/noahsark-ssh-${SHA:0:8}.txt"
```

## 5. 整理后工作区状态

执行隔离与 `.gitignore` 更新后：

```bash
GIT_MASTER=1 git status --short
```

```text
 M .gitignore
 M README.md
 M docs/v2/wireframes/README.md
 D "自动化生成测试用例流程图.svg"
?? docs/VERSIONING.md
?? docs/delivery/
?? docs/references/
```

与初始状态相比，唯一差异是：

- `docs/ssh.txt` 不再出现在未跟踪列表；
- `.gitignore` 新增一条忽略规则。

其余文件均未删除、未回退、未暂存。

## 6. 结论与后续动作

1. **敏感文件已隔离**：`docs/ssh.txt` 已移出工作区到 600 权限的隔离目录，原始哈希已登记，`.gitignore` 已防止误提交。
2. **未发现需要回退的代理越界改动**：现有改动均可用计划、版本指南或链接修复解释。
3. **根目录 SVG 删除是安全移动**：新位置与 HEAD 内容 SHA-256 完全一致；后续提交应按重命名处理。
4. **不要提交本次分诊产生的临时状态**：`.gitignore` 改动和新增报告属于 P0-01 证据，是否提交由主控在验证后决定。
5. **建议在 P0-03 复核**：`docs/VERSIONING.md` 与 `README.md` 的规范表述需与 P0-02/P0-03 的事实源优先级同步；本报告只确认它们是计划内产物，不确认其契约内容已冻结。

## 7. 复现命令清单

```bash
GIT_MASTER=1 git status --short
GIT_MASTER=1 git status --porcelain=v1 -uall
GIT_MASTER=1 git branch --show-current
GIT_MASTER=1 git rev-parse --short HEAD
GIT_MASTER=1 git remote -v
GIT_MASTER=1 git diff --stat
GIT_MASTER=1 git diff --numstat
GIT_MASTER=1 git diff --name-status
GIT_MASTER=1 git diff --cached --stat
GIT_MASTER=1 git ls-files --others --exclude-standard
GIT_MASTER=1 git check-ignore -v .omo/ docs/ssh.txt docs/VERSIONING.md docs/references/README.md
GIT_MASTER=1 git ls-files --error-unmatch docs/ssh.txt
GIT_MASTER=1 git log --all --oneline -- docs/ssh.txt
GIT_MASTER=1 git ls-files docs
GIT_MASTER=1 git show 'HEAD:自动化生成测试用例流程图.svg' | sha256sum
sha256sum 'docs/references/diagrams/自动化生成测试用例流程图.svg'
sha256sum docs/ssh.txt
wc -l docs/ssh.txt
wc -c docs/ssh.txt
file docs/ssh.txt
```
