# P0-10 独立验证报告：`docs/delivery/environment-inputs.md`

> 验证对象：P0-10 输入清单 [`environment-inputs.md`](./environment-inputs.md)（483 行，mtime 2026-10-28 23:41）
> 验证日期：2026-10-29（Asia/Shanghai）
> 验证方式：只读复核清单正文、汇总表、来源索引，并对来源文件与本地事实做定向抽查；未修改被验对象、契约、`.omo`、`plan.md` 或产品代码，未提交。
> 验证边界：**只验证“这是一份合格的输入清单”，不验证环境是否就绪**。本报告不构成 A-0 通过、L3/L4/L5 准入、测试执行或发布授权。

---

## 1. 判定

**NEEDS-FIX**。清单的骨架、计数、覆盖面和“未就绪”口径成立，且没有把缺失硬件写成已完成；但存在 **4 项需修正的事实/溯源问题**（F1–F4），其中 F1、F2 是可复现的事实错误，F3、F4 会削弱清单自身“每个输入可溯源”的承诺。修正后可作为 P0-10 的合格输入清单，但仍不表示环境就绪或 A-0 通过。

---

## 2. 核验结果总表

| # | 核验项 | 证据 | 结果 |
|---|---|---|---|
| C1 | 汇总表行数与三态计数 | §9 表 85 个数据行；脚本重算 `known=21`、`placeholder=13`、`unknown=51`；§9.1 与 §15 同值 | **PASS** |
| C2 | 表格结构完整性 | 85 行全部 8 列；ID 无重复；负责人、阻塞列无空值；前缀计数 L18/E14/W19/D12/T8/N6/R8 | **PASS** |
| C3 | 三态定义与“known≠就绪” | `environment-inputs.md:13-24` 定义三态；`:23` 明确 known 不证明就绪；`:381`、`:396` 再次限定 | **PASS** |
| C4 | 缺失硬件未被写成完成 | W 类 14 unknown + 5 placeholder、0 known；D 类 10 unknown + 2 placeholder、0 known；R 类 8 unknown | **PASS** |
| C5 | A-0 与 L3/L4/L5 门禁分离 | 可开工 §10.1（`:367-381`）；A-0 清单 §11（`:394-407`）；L3/L4/L5 清单 §12（`:409-439`），三处未混写 | **PASS** |
| C6 | 覆盖范围 | Linux §2、证据/备份 §3、Windows §4、设备 §5、lstest §6、网络信任 §7、真机窗口 §8、汇总 §9 | **PASS** |
| C7 | 无密钥/主机值泄漏 | 未命中 IPv4、password、token=、私钥头、UNC 路径、真实序列号；仅出现本地路径 `/home/bszheng/NoahsArkdata` 与本机硬件事实 | **PASS（见 §5.4 注）** |
| C8 | `git diff --check` | 退出码 0，无输出；文件为 UTF-8/LF，无行尾空白 | **PASS（见 §5.5 注）** |
| C9 | 计划/进度口径 | `.omo/plans/noahsark-platform-delivery.md:32` P0-10 未勾选；`docs/delivery/construction-progress.md:20` 为“待验证” | **PASS** |
| C10 | 来源索引文件存在性 | S1/S8/S10/S11/S12/S13/S14/S15/S16/S19/S20 路径均存在；“同上”类 S2–S7/S9 可回溯到 S1/S8 | **PASS（有可读性余量）** |
| C11 | 具体引用抽查（13 项） | 见 §4 | **10 PASS / 3 FAIL** |

---

## 3. 必须修复项

### F1（事实错误）`origin/main` 不是 `f32aebc`

- 清单位置：`environment-inputs.md:56`
  > 本地 `/home/bszheng/aitest/vendor/lstest`，`origin/main` HEAD `f32aebc`（2026-10-14），本次复核仍为该提交（S10 §8.4；S18）。
- 同源错误还出现在：`:205`（“`f32aebc`（2026-10-14，origin/main）”）、`:335`（T01 来源）；`:475`（S18 命令只含 `git rev-parse --short HEAD`）是证据缺口，不是同一句话。
- 本次实测：

  ```text
  $ git -C /home/bszheng/aitest/vendor/lstest branch -vv
  * main f32aebc [origin/main: ahead 1] Publish lstest

  refs/heads/main                  f32aebc  2026-10-14
  refs/remotes/origin/main         7190ab6  2026-08-18
  refs/remotes/origin/HEAD         7190ab6  2026-08-18
  ```

  `f32aebc` 是**本地 `main` HEAD**，且领先 `origin/main` 1 个提交；`origin/main` 实际为 `7190ab6`（2026-08-18）。S18 只执行了 `rev-parse --short HEAD`，不能证明 `origin/main`。
- 影响：T01 是 `known`，且被 §1.1、§4、§6 反复引用；写错远端基线会把“本地可复现”误读为“远端已同步”。
- 修复：改为“本地工作树 `main` HEAD `f32aebc`（2026-10-14）；`origin/main` 为 `7190ab6`，本地领先 1 个提交”，并同步 `:205`、`:335`。上游 `S10 §8.4`（`.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md:165`）沿用了同一错误，应在 P0-09/后续文档同步中登记，但**不在本次修改范围**。

### F2（事实错误）“10 个子命令”把顶层命令与嵌套命令混为一谈

- 清单位置：`environment-inputs.md:57`、`:209`、`:339` 均写“10 个子命令”。
- 本次实测：

  ```text
  $ python3 scripts/lstest.py --help
  {list,tts,tts-manifest,audio,preflight,init,smoke}      # 7 个顶层命令
  $ python3 scripts/lstest.py audio --help
  {ensure-laid,scan,probe,play,dual-play}                 # 5 个 audio 子命令
  ```

  `S10 §8.4` 列出的 10 个名称是“5 个顶层 + 5 个 audio 嵌套”，且**漏掉了 `init`、`smoke`**。因此“10 个子命令”既不等于顶层命令数（7），也不是完整命令树（7+5）。
- 影响：T05 是 `known`，且被 A-0 编码基线引用；命令清单不准确会影响后续调用与契约核对。
- 修复：改为“7 个顶层子命令（`list`、`tts`、`tts-manifest`、`audio`、`preflight`、`init`、`smoke`）+ `audio` 的 5 个子命令（`ensure-laid`、`scan`、`probe`、`play`、`dual-play`）”；`list --json` 的 9 项能力集仍然正确，保留。

### F3（状态口径）L01 标为 `known` 却又标“阻塞 L3”，且没有受限记录指针

- 清单位置：`environment-inputs.md:84`、`:272`
  > `主机身份（hostname/IP） | 已确认存在；按 P0-01 分诊策略不写入仓库 | known`
  > `L01 | Linux 控制面主机身份 | L3/L4/L5 | 已确认存在；值不落仓库 | known | 所有者/运维 | 是（L3）`
- `:268` 定义“阻塞”为“缺该值会阻断对应层”。若 L01 真是 `known`（真实值存在且可核验），就不应“缺值”；若值虽存在但未登记，则当前状态实际更接近 `placeholder`/`unknown`。清单只写“需在受限运维记录中给出”，没有给出记录编号、登记日期或核验人，属于**无证据的 known 断言**。
- 影响：这是三态纪律的核心边界；若 `known` 可以仅凭“我确认存在”成立，后续所有敏感值都可能被同样处理，清单就失去可核验性。
- 修复（二选一，推荐 1）：
  1. 在受限运维记录中登记记录 ID/日期/核验人（不写真实值），并把 L01 的“阻塞”改为“否”；或
  2. 在受限记录建立前，把 L01 改为 `placeholder`（“身份已口头确认，值未登记”），保留“是（L3）”。

### F4（溯源缺口）4 行没有行级来源编号，违反清单自己的 A-0 要求

- 清单自己的要求：`environment-inputs.md:399`
  > 每个输入有唯一 ID、状态、责任方、阻塞层与来源。
- 缺来源的 4 行：
  - `:292` E03 证据文件系统 —— 来源列只有“本机根为 ext4，证据路径未定”，无 `S#`。
  - `:329` D07 电源控制方式 —— “只登记事实；不含断电/上电”，无 `S#`。
  - `:340` T06 正式执行命令/参数 —— “需 profile/设备/超时参数”，无 `S#`。
  - `:354` R06 离线/断网模拟许可 —— “AC-11/AC-12”，无 `S#`。
- 影响：这 4 行无法按第 14 节索引回溯；与 A-0 清单第 2 项直接冲突。
- 修复：补行级来源，例如 E03 → `S1 §5.4；S11 §12`；D07 → `S3 §5.3；S11 §10`；T06 → `S10 §8.4；S15 §6.3`；R06 → `S1 §3（AC-11/AC-12）；S7`。

---

## 4. 来源引用抽查（13 项）

| # | 清单声称 | 清单引用 | 实际来源核对 | 结果 |
|---|---|---|---|---|
| 1 | 本机 Ubuntu 24.04.4、kernel 6.17.0-35、16 线程、约 15 GiB、468 GiB/剩 296 GiB、NTP、Asia/Shanghai、无 psql | `:58`、`:475`（S18） | 本次实测逐项一致；`nproc=16`，`MemTotal≈15.3 GiB`，`df` 468G/149G/296G | PASS |
| 2 | lstest 基线 `f32aebc`（2026-10-14，`origin/main`） | `:56`、`:205`、`:335`（S10/S18） | 本地 `main` HEAD 是 `f32aebc`；`origin/main` 是 `7190ab6`（2026-08-18） | **FAIL（F1）** |
| 3 | CLI 入口、10 个子命令 | `:57`、`:209`、`:339`（S10 §8.4） | 顶层 7 个；`audio` 下 5 个；S10 的 10 个名称漏 `init`/`smoke` | **FAIL（F2）** |
| 4 | 节点仅出站、TLS 1.3 + mTLS、X.509/Ed25519、90 天/第 60 天续期 | `:54`、`:93`、`:281`（S12 §1） | `docs/contracts/security-node.md:16-21` 一致；另 `:438` 允许最低 TLS 1.2 回退（见 M3） | PASS（有 M3 余量） |
| 5 | spool `min(2 GiB, D: 10%)`、70% 预警、95% 保护 | `:158`、`:317`（S13 §7） | `docs/contracts/thresholds.md:238-241`（TH-S-07..10）一致 | PASS |
| 6 | 原始音频/日志/证据本地热存 30 天，无归档路径不自动删除 | `:52`、`:126`、`:300`（S11 §12） | `.omo/drafts/00-baseline/...requirements-baseline.md:149` 一致 | PASS |
| 7 | 第二服务器异步从库 + 证据增量；NAS WAL/每日全量；RPO/RTO 目标 | `:51`、`:59`、`:128`、`:288`（S8 §1.3） | `.omo/drafts/05-decisions/...decision-register.md:50-59` 一致（DB ≤1min/≤30min；证据 ≤15min/≤1h；整机 ≤4h） | PASS |
| 8 | 结果目录、`tool.log` 北京时间、21 条规则 formal profile、`m0_min_profile` 为 debug、v1 缺 `profile_id` 即 BLOCKED | `:206`、`:208-211`（S10 §8.4） | `.omo/drafts/01-design/...architecture-proposal.md:165-202` 一致 | PASS |
| 9 | 旧 T3 需真实 PASS/FAIL/STOPPED/离线各一次；固件白名单 | `:250`、`:334`、`:353`（S15 §4） | `solutions/1027V1/GAP-CLOSURE.md:191-215` 一致 | PASS |
| 10 | 设备身份/等价字段：`serial_number_masked`、`identity_digest`、`equivalence_group_id`、`conditions_digest`、`verified_at`、`verified_by` | `:39`、`:188`、`:332`（S14） | `docs/contracts/schemas/domain/device.schema.json:34,100-105` 与 `docs/contracts/domain.md:492-505` 一致 | PASS |
| 11 | 建议单机三进程 | `:92`、`:280`（S9 §2 P0-11） | `.omo/drafts/05-decisions/...decision-register.md:180-183` 一致 | PASS |
| 12 | D: SMB 只读共享是“首选候选”，不是冻结契约 | `:122`、`:161`、`:296`、`:320`（S17） | 根 `plan.md:362` 明确“首选候选……不把首选候选视为已冻结契约” | PASS |
| 13 | PostgreSQL 是唯一正式数据库、SQLite 仅历史参考 | `:50`、`:276`（S8 §2 P0-01） | 该结论真实，但不在 S8 P0-01（原文仅“建议 PostgreSQL”）；实际出处是 `docs/delivery/source-reconciliation.md` SR-02（`:47`/`:72`） | **FAIL（引用，M2）** |

---

## 5. 已复核通过项（细节）

### 5.1 计数与结构

脚本按 `^| [LWEDTNR]\d{2} |` 解析 §9 的 85 行，得到：

```text
rows 85
bad col count []
states {'known': 21, 'placeholder': 13, 'unknown': 51}
missing owner []
missing block []
dup ids []
prefix {'L': 18, 'E': 14, 'W': 19, 'D': 12, 'T': 8, 'N': 6, 'R': 8}
```

与 §9.1（`21/13/51/85`）和 §15 变更记录完全一致。分类明细：L 11 known/3 placeholder/4 unknown；E 5/2/7；W 0/5/14；D 0/2/10；T 5/0/3；N 0/1/5；R 0/0/8。

### 5.2 未就绪口径

- `:5` 状态行明确“清单已建立，环境未就绪，A-0 未通过”。
- `:23` 明确 `known` 只证明输入已确认，不证明环境就绪、链路已通或验收通过。
- `:381` 只说“编码可以在不解决 L3 真机输入的情况下开始”，并紧接着“不得声称环境就绪”。
- 全文未出现“环境已就绪”“已通过验收”“已部署”“已实现”等正向宣称；`grep -nE '已就绪|已具备|已通过|已完成|已部署|已实现'` 仅命中规则性否定句和 S17 章节标题。
- W/D/R 三类真实硬件/窗口 **0 个 known**，不存在“缺硬件但标完成”。

### 5.3 门禁分离

- §10.1 `:367-381`：最小可开工，只要求语言/运行时、lstest 只读基线、契约骨架、占位存储/测试证书，明确“不需要真实设备”。
- §11 `:394-407`：A-0 签署清单，`10` 个未勾选项，并声明“勾选不表示 A-0 已通过”。
- §12.1/12.2/12.3 `:409-439`：L3 真机烟测、L4 正式采样、L5 端到端闭环分别列条件。
- §1.3 `:72-76` 显式区分“可开工”与“可真机验收”，并声明 A-0 与 L3/L4/L5 判定分别在第 11、12 节。

### 5.4 敏感值扫描

执行的扫描（`grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|password|passwd|secret|token[[:space:]]*[=:]|BEGIN (RSA|OPENSSH|PRIVATE)|ssh://|\\\\[A-Za-z0-9_.-]+'`）无命中。未出现真实序列号、证书指纹、IP、主机名、注册 token 或私钥。

注：清单包含本地绝对路径 `/home/bszheng/NoahsArkdata`（`:119`、`:293`）及本机 OS/CPU/内存/磁盘事实（`:58`、`:85-87`）。这些不是密钥，且用户名路径已在仓库 `README.md` 的目标目录中出现；但组合起来可形成开发主机指纹，建议后续如需对外分享，改为 `<repo-root>/../NoahsArkdata` 之类占位。

### 5.5 补丁与编码检查

- `git diff --check`：无输出，退出码 **0**。
- `file`：UTF-8 text；CRLF 计数 **0**；行尾空白扫描（正确的 `[ \t]+$`）无命中。
- 注：`docs/delivery/` 当前为未跟踪目录，`git diff --check` 不会覆盖未跟踪文件；上述文件级检查是对该缺口的补充。

### 5.6 计划与进度一致性

- `.omo/plans/noahsark-platform-delivery.md:32`：P0-10 仍为 `- [ ]`，未宣称完成。
- `docs/delivery/construction-progress.md:20`：状态“待验证”，证据列指向本报告；`:25` 记录“清单已建，A-0 未通过”。
- 清单自身 `:5`、`:483` 与上述口径一致。

---

## 6. 次要问题（建议随 F1–F4 一并修正）

### M1 `§0.2` 的来源优先级与 `docs/VERSIONING.md` 第 2 节不一致

- 清单 `:26-34`：基线 → 根 `plan.md` → `.omo/drafts/01/02/05` → `docs/contracts/` → `solutions/`+`docs/v2/`+`openspec/`。
- `docs/VERSIONING.md:23-31`：第 1 层是“已批准基线 + 已评审架构/模块/交付边界 + 冻结契约 + 冻结执行计划”，第 2 层才是 `plan.md`，第 4 层是 `docs/v2`/`openspec`，第 5 层是 `solutions/` 等历史归档。
- 差异：清单把“已评审 drafts”降到 `plan.md` 之下，把冻结契约降到第 4 层，并把 `solutions/` 与 `docs/v2`/`openspec` 混为同一层。
- 影响：当前引用的来源之间没有实际冲突，因此不影响本清单结论；但“事实源优先级”本身应与权威文件一致，否则后续冲突裁决会走错层。
- 建议：直接改写 §0.2 为 VERSIONING 的五层顺序，并注明“`docs/contracts/` 目前均为 `frozen-candidate`，冻结评审前不具约束力”。

### M2 PostgreSQL“唯一正式库”引用错位

- `:50`、`:276` 引 `S8 §2 P0-01`；S8 原文只写“**建议**：PostgreSQL”，并未写“唯一正式数据库/SQLite 仅历史参考”。
- 该结论实际登记在 `docs/delivery/source-reconciliation.md` 的 SR-02（`:47`、`:72`）。
- 建议：改引 `source-reconciliation.md SR-02`，避免让读者以为 S8 已作绝对化裁决。

### M3 TLS 基线遗漏“最低 TLS 1.2”回退

- `:54`、`:93`、`:281` 写“TLS 1.3 + mTLS”并标 `known`；`docs/contracts/security-node.md:438` 同时写“TLS 1.3 优先；最低 TLS 1.2（若必须）”。
- 建议：改为“TLS 1.3 优先，契约允许最低 TLS 1.2 回退（S12 §9.2）”，或明确该行只冻结“首选基线”而非绝对下限。

### M4 “候选 PostgreSQL 16”与 S20 的“版本待 P1-01”不完全一致

- `:89`、`:277` 写“候选 16，未锁定”；`S20 P2-4`（`.omo/drafts/00-VARIANT-B-AUDIT.md:68`）的裁决是“改为 PostgreSQL，版本待 P1-01”。
- 16 只是讨论中的候选，不是已登记候选。建议改为“版本待 P1-01；16 仅为讨论候选，未锁定”，避免把候选值带进实现假设。

### M5 “旧 T3 集成/资格窗口”标签易混

- `:250`、`:349` 写“旧 T3 集成/资格窗口”。现行 `S7`（`.omo/drafts/02-delivery/noahsark-v0.0.1-test-strategy.md:23`）的 T3 是“集成”，而 S15 的旧 T3 是“真实设备资格”。
- 建议改为“旧 T3 真实设备资格窗口（不是现行 T3 集成）”，与 `:246` 的编号说明一致。

---

## 7. 剩余真实未知（清单已正确留空，未用默认值填充）

以下均为**真实未知**，不是本报告的缺陷；在取得证据前，任何一条都不应被写成 `known` 或“已具备”。

| 类别 | 仍未取得的值 | 清单位置 |
|---|---|---|
| Linux/数据库 | PostgreSQL 实例、DSN/端口、流复制/归档配置、恢复演练记录；版本仅 placeholder | L06/L07/L18（`:277-278`、`:289`） |
| 证据/备份 | 证据根路径、容量、文件系统、第二服务器配置、NAS 协议/路径/容量、加密算法与密钥轮换、归档验证/删除审批 | E01–E03、E05、E06、E10、E14（`:290-303`） |
| Windows 节点 | 主机、OS build、服务账户、交互式会话、Agent/适配器、音频/串口/USB 端点、GUI、D: 容量、证书、出站连通、时区、残留 STOP/租约 | W01–W05、W08–W13、W15–W19（`:304-322`） |
| 设备 | 厂商/型号、固件、硬件版本、脱敏序列号、音频/串口绑定、电源/恢复、设备池、PASS/FAIL/离线场景 | D01–D09、D12（`:323-334`） |
| lstest | 真实 formal profile 路径与 `profile_id`、真实脚本/任务配置、正式执行命令/参数 | T02/T03/T06（`:336-340`） |
| 信任/网络 | CA/签发主体、DNS、控制面对外证书、时钟偏差实测、防火墙/代理工单；注册 token 签发人 | N01–N06（`:343-348`） |
| 真机窗口 | 旧 T3 资格窗口、T5 烟测、T6 验收、负责人、固件白名单、断网许可、升级审批、回滚联系人 | R01–R08（`:349-356`） |

这些未知与 §1.2 的 6 个 top blockers、§10.2 的 L3 进入条件、§13 的 10 个待回答问题相互对应；清单没有用“合理默认值”静默填充。

---

## 8. 本次实际执行的可复现命令

```bash
cd /home/bszheng/NoahsArk

# 1) 计数与结构（输出 rows 85 / 21 / 13 / 51 / 无重复 ID）
python3 - <<'EOF'
import re, collections
lines = open('docs/delivery/environment-inputs.md', encoding='utf-8').read().splitlines()
rows = []
for i, l in enumerate(lines, 1):
    if 272 <= i <= 356 and re.match(r'^\| [LWEDTNR]\d{2} \|', l):
        rows.append((i, [c.strip() for c in l.strip().strip('|').split('|')]))
print('rows', len(rows))
print('bad', [(i, len(c)) for i, c in rows if len(c) != 8])
print('states', dict(collections.Counter(c[4].strip('`') for i, c in rows)))
print('dup', [k for k, v in collections.Counter(c[0] for i, c in rows).items() if v > 1])
EOF

# 2) 未就绪/过度宣称词
grep -nE '已就绪|已具备|已通过|已完成|已部署|已实现' docs/delivery/environment-inputs.md

# 3) 敏感值/IP/密钥扫描（无输出）
grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|password|passwd|secret|token[[:space:]]*[=:]|BEGIN (RSA|OPENSSH|PRIVATE)|ssh://' docs/delivery/environment-inputs.md

# 4) 补丁与文件编码
git diff --check; echo "exit=$?"
file docs/delivery/environment-inputs.md
grep -nE $'[ \t]+$' docs/delivery/environment-inputs.md

# 5) lstest 基线与命令树
git -C /home/bszheng/aitest/vendor/lstest branch -vv
git -C /home/bszheng/aitest/vendor/lstest for-each-ref --format='%(refname) %(objectname:short) %(committerdate:short)' refs/heads refs/remotes
python3 /home/bszheng/aitest/vendor/lstest/scripts/lstest.py --help
python3 /home/bszheng/aitest/vendor/lstest/scripts/lstest.py audio --help

# 6) 本地事实
cat /etc/os-release | grep PRETTY; uname -r; nproc; free -g | head -2
df -h /; findmnt -no FSTYPE /; timedatectl | grep -E 'Time zone|synchronized|NTP'
command -v psql || echo 'psql: ABSENT'
```

---

## 9. 限制

1. 本报告只验证 `environment-inputs.md` 作为“输入清单”的完整性、口径和可溯源性，**不验证**真实 Windows 节点、设备、PostgreSQL、NAS、第二服务器、证书或网络；这些在本环境中不可用。
2. 未读取 `docs/ssh.txt`（按 P0-01 已隔离，当前仓库路径不存在）；未接触任何凭据。
3. `docs/delivery/` 为未跟踪目录，`git diff` 不能证明“本次未修改被验对象”；依据是只读操作、文件 mtime（2026-10-28 23:41）未变，以及本报告只新增了 `p0-10-verification.md`。
4. 未逐条核对 85 行的全部来源，只对 13 项具体声称做了定向抽查，并做了全表结构解析；未抽查的行仍可能存在同类引用偏差。
5. 本机事实是 2026-10-29 的快照；OS/内核/磁盘或 lstest HEAD 变化后，S18 类 `known` 需重新登记。
6. 未修改 `environment-inputs.md`、`docs/contracts/`、`.omo/`、`plan.md` 或产品代码；未提交、未推送。

---

## 10. 修正记录（2026-10-29，追加；不替换上文判定）

> 本节只记录被验对象对 F1–F4 的修正，保留上文原始 **NEEDS-FIX** 判定、证据与计数，不构成独立复验结论，也不表示 A-0 通过。

- **F1 已修正**：§1.1、§6、T01 改为区分本地 `main` `f32aebc`（2026-10-14）与实际 `origin/main` `7190ab6`（2026-08-18），并注明本地领先 1 个提交；S18 补充 `branch -vv` 与 `for-each-ref` 证据命令。
- **F2 已修正**：§1.1、§6、T05 改为“7 个顶层子命令 + `audio` 下 5 个嵌套子命令”，并列出名称；`list --json` 的 9 项能力集未改动。
- **F3 已修正（采用报告选项 2）**：仓库内不存在可引用的受限运维记录 ID/日期/核验人，故 L01 由 `known` 降为 `placeholder`（“身份已口头确认，值未登记”），保留“是（L3）”阻塞；未虚构记录编号，未写入任何主机名/IP。
- **F4 已修正**：E03 补 `S1 §5.4；S11 §12`；D07 补 `S3 §5.3；S11 §10`；T06 补 `S10 §8.4；S15 §6.3`；R06 补 `S1 §4（AC-11/AC-12）；S7`。
- **计数变化**：L01 状态变化使 §9.1/§15 由 `21 known / 13 placeholder / 51 unknown` 更新为 **`20 known / 14 placeholder / 51 unknown`（合计仍 85）**；上文 C1 的旧计数为修正前快照。
- **边界不变**：A-0 仍未通过，L3/L4/L5 仍未就绪；原报告 §6 的 M1–M5 次要问题未在本次范围内修改。
