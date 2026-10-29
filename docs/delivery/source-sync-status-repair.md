# 源同步状态陈旧修复报告（Source Sync Status Repair）

> 任务：只修复 `docs/delivery/source-sync-followup-verification.md` 指出的状态/登记陈旧文字。
> 修复日期：2026-10-29（Asia/Shanghai）。
> 修复对象：`docs/delivery/openspec-v2-sync.md`、`docs/delivery/source-reconciliation.md`。
> 判定来源：`source-sync-followup-verification.md` §4.1（F-02）、§4.3（F-01）。
> 边界：未改契约、schema、产品代码、UI 文件、总计划复选框、归档；未使用 SSH 或凭据；未提交、未推送；未宣称 Phase 0 关闭。
> 性质：**记录型回填**。不改任何规范语义，只让两份状态产物的“未解决/开放”条目指向 2026-10-29 已完成的后续修复。

---

## 1. 结论

独立复核判定七项核心语义 7/7 PASS，仅两份登记产物 NEEDS-FIX。本次只处理这两处：

| 产物 | 修复前 | 修复后 | 行数变化 |
|---|---|---|---|
| `docs/delivery/openspec-v2-sync.md` | §9.1、§9.2 仍称源草案与契约租约措辞“仍未解决” | §0.2 新增回填表；§9.1、§9.2 段首加日期标记指向后续证据，原文整段保留 | 425 → 442（+17） |
| `docs/delivery/source-reconciliation.md` | SR-10、SR-11、SR-12 与 §1.3 速览仍为开放状态 | §1.4 新增回填表；三条主表状态改为已闭环并保留原状态；§4 位置索引同步 | 184 → 207（+23） |

修复只做“追加结论 + 标注原状态”，没有删除或改写任何历史结论、证据数字或审计时间线。本报告不改变：PostgreSQL 唯一正式库、Linux 权威判定、Windows 仅事实、离线续跑、STOP-first、释放/证据/最终判定分离。

---

## 2. 判定来源与证据核对

修复前逐条核对了复核报告引用的证据，全部可复现。

| 复核项 | 复核结论 | 本次核对 |
|---|---|---|
| F-02 §9.1 源草案旧条 | 已由 `approved-draft-reconciliation.md` 修正 | `architecture-proposal.md:91`（I-21）、`:126`（§7 规则 4）、`:128`（§7 规则 6）、`:379-389`（R-1..R-4）；`module-design.md:101-114`（§2.6）、`:203`（§4.2）、`:385-391`（R-1..R-3） |
| F-02 §9.2 契约租约措辞 | 已由 P0-05 修正 | `docs/contracts/README.md:58` 写明“已无 `lease_expired` 旧措辞”；`grep lease_expired docs/contracts/security-node.md` 为 0 命中；`phase0-contract-remediation-verification.md:109` 记 F-11 已关闭、`:111` 记 11/11 关闭 |
| F-01 SR-10、SR-11 | 源草案已修 | 同上 `architecture-proposal.md`、`module-design.md` 修订说明 |
| F-01 SR-12 | README 已修，映射残项另见 C-03 | `docs/contracts/README.md:58`；`contract-residual-followup.md` C-03 |

核对中确认 `docs/contracts/schemas/security/lease.schema.json` 的 `state` 闭集仍含 `expired`，但该枚举只表示续约截止，不是所有权到期。它是正确语义，不属于本轮修复对象；逐值映射仍由 C-03 跟踪。

---

## 3. 精确编辑

### 3.1 `docs/delivery/openspec-v2-sync.md`（425 → 442 行）

| # | 锚点（修复后行号） | 修复前 | 修复后 | 作用 |
|---|---|---|---|---|
| E-01 | `:5` 头部状态行 | “2026-10-29 按独立验证 F1/F2/F3 返工修订，见 §0.1” | 同句追加“；同日按独立复核追加 §0.2 状态回填” | 读者从头部即可跳到回填记录 |
| E-02 | `:26-43` 新增 §0.2 | §0.1 之后直接进入 §1 | 新增“0.2 状态回填记录（2026-10-29）”：两条原条目、原文状态、回填结论、后续证据路径；并声明 §9.3–§9.9 不变、Phase 0 未关闭、A-0 未通过、契约为 `frozen-candidate`、T-09..T-12/T-23 仍开放 | 集中登记回填，避免读者误读 |
| E-03 | `:374` §9.1 段首 | “1. **源级草案内部矛盾（不在 P0-03 同步对象）**：” | 追加“（*2026-10-29 回填：已由 `approved-draft-reconciliation.md` 修正，本条仅存档原记录；见 §0.2*）” | 保留原文，标明已被后续修复推翻 |
| E-04 | `:375` §9.2 段首 | “2. **`docs/contracts` 未对齐项（禁止编辑）**：” | 追加“（*2026-10-29 回填：`lease_expired` 措辞已由 P0-05 修正，本条仅存档原记录；见 §0.2*）” | 同上 |
| E-05 | `:327` §8.7 | “2026-10-29 返工后为 **425 行**” | “返工后为 425 行，同日状态回填（§0.2）后为 **442 行**” | 保持自述行数与实测一致 |

修复前锚点：§9.1 在 `:357`，§9.2 在 `:358`，§8.7 在 `:310`。因 §0.2 插入 17 行，修复后整体下移。

### 3.2 `docs/delivery/source-reconciliation.md`（184 → 207 行）

| # | 锚点（修复后行号） | 修复前 | 修复后 | 作用 |
|---|---|---|---|---|
| R-01 | `:8` 头部新增行 | 无 | “状态回填：2026-10-29 按独立复核 … F-01 回填 SR-10、SR-11、SR-12 及 §1.3 速览 …（见 §1.4）”；并声明 Phase 0 未关闭、不构成契约冻结或实施授权 | 登记表顶部给出回填入口 |
| R-02 | `:48-49` §1.3 速览 | “源草案旧条留待 P0-09（SR-10）”“源草案 I-21 留待 P0-09（SR-11）” | 保留原句，各追加“（2026-10-29 回填：源草案已由 `approved-draft-reconciliation.md` 修正，见 SR-10/SR-11）” | 保留历史处置，补最新状态 |
| R-03 | `:55-72` 新增 §1.4 | 无 | 新增“1.4 状态回填记录（2026-10-29）”：六行前/后锚点表 + 三条口径说明（回填含义、SR-12 映射残项、语义不变清单） | 给出可审计的 before/after 对照 |
| R-04 | `:80` §2 状态口径 | 无“后续修复回填”状态 | 新增 `已闭环（后续修复回填，2026-10-29）` 释义行 | 让新状态词有定义 |
| R-05 | `:101` SR-10 | 状态 `开放—P0-09` | 状态 `已闭环（后续修复回填，2026-10-29；原状态：开放-P0-09）`；解决路径追加草案已修的日期与文件 | 关闭开放项，保留原状态 |
| R-06 | `:102` SR-11 | 状态 `开放—P0-09` | 状态 `已闭环（后续修复回填，2026-10-29；原状态：开放-P0-09）`；解决路径追加 I-21 与 §7 规则 6 已修 | 同上 |
| R-07 | `:103` SR-12 | 状态 `开放—P0-05` | 状态 `已闭环（README 已修；映射另见 C-03）（2026-10-29 回填；原状态：开放-P0-05）`；解决路径写明 `README.md:58`、F-11 与 C-03 | 区分“已修”和“仍跟踪的映射项” |
| R-08 | `:129-131` §4 位置索引 | “待 P0-09 文档同步”“草案正文待同步”“待 P0-05 修订 README” | 分别改为“2026-10-29 已由 `approved-draft-reconciliation.md` 修正…”“草案正文已于 2026-10-29 同步…”“README 过期陈述已由 P0-05 修订…，映射另见 C-03” | 消除主表与索引互相矛盾 |
| R-09 | `:207` §6 尾注 | 无 | 新增回填注记：P0-05 租约措辞与 P0-09 草案旧条已完成；其余后续动作仍开放；Phase 0 未关闭 | 保留原后续动作清单，补完成状态 |

修复前锚点：SR-10/11/12 在 `:80-82`，§4 对应行在 `:108-110`，§6 尾段在 `:184`。

---

## 4. 未修改项（边界确认）

- 未修改任何 schema 或契约文件（`docs/contracts/**` 全部只读）。
- 未修改产品代码、测试、CI 或部署脚本。
- 未修改任何 UI 文件（`design/`、`docs/v2/UI-*`、`openspec/**/ui-v2` 未触碰）。
- 未勾选或改写 `.omo/plans/noahsark-platform-delivery.md`，未改根 `plan.md`。
- 未修改归档目录（`.omo/drafts/99-history/`、`solutions/1027V1/`）。
- 未触碰 `docs/ssh.txt`、token、凭据或 SSH。
- 未执行 commit、push、tag 或 PR。
- 未新增或删除 SR 编号，冲突类仍为 21 个；`grep -c "^| SR-"` 仍为 42（主表 21 + 索引 21）。
- 未宣称 Phase 0 关闭，未把任何契约标为 `frozen`。

---

## 5. 验证

```bash
cd /home/bszheng/NoahsArk

# 1) 行数
wc -l docs/delivery/openspec-v2-sync.md docs/delivery/source-reconciliation.md
# 442 docs/delivery/openspec-v2-sync.md
# 207 docs/delivery/source-reconciliation.md

# 2) 冲突类计数未变
grep -c "^| SR-" docs/delivery/source-reconciliation.md        # 42

# 3) 行尾空白
grep -nP '[ \t]+$' docs/delivery/openspec-v2-sync.md \
  docs/delivery/source-reconciliation.md \
  docs/delivery/source-sync-status-repair.md | wc -l          # 0

# 4) 补丁空白检查
git diff --check                                              # 无输出，EXIT=0

# 5) 陈旧状态残留扫描（当前状态列应为 0 条，仅 §1.4 历史对照表保留引用）
grep -n "待 P0-09 文档同步\|草案正文待同步\|待 P0-05 修订 README" \
  docs/delivery/source-reconciliation.md
# 只命中 1 行：§1.4 表格中引用“回填前”原文的对照行；§3 主表与 §4 索引的当前状态列 0 命中
```

说明：`docs/delivery/` 在当前工作区为未跟踪目录，`git diff --check` 不覆盖这些文件，因此第 3 项行尾空白扫描是必要补充。第 5 项的唯一命中是 §1.4 的“回填前”对照文本，属有意保留的历史引用，不是残留状态。

---

## 6. 剩余阻塞项（未由本报告关闭）

1. **5 个 `open-blocker` 仍在**：T-09 节点外部事实、T-10 设备外部事实、T-11 真实 formal profile/脚本、T-12 证据根/NAS/第二服务器/恢复演练、T-23 Phase 0 验证与归档负责人/状态（`p0-09-decision-reconciliation.md:148-158`）。
2. **A-0 仍未通过**：85 条输入 `known 20 / placeholder 14 / unknown 51`，六类外部事实无直接证据，签署清单未勾选（`a0-readiness-followup.md:16`）。
3. **契约仍为候选**：`docs/contracts/` 全部 `frozen-candidate`，无冻结声明。
4. **契约残余仍开放**：R-01..R-03、C-01..C-06 中未由 F-11 覆盖的条目仍待裁决；SR-12 的 `security.lease.state → domain Lease.state` 逐值映射仍由 C-03 跟踪。
5. **其他 SR 开放项不变**：SR-04（P0-05 契约索引）、SR-13（审批超时措辞）、SR-14/SR-15（枚举与 ID）、SR-18（图示重绘）、SR-19（优化状态标签）状态未动。
6. **历史文档低危残留仍在**：`docs/v2` 6 处旧终态语句未逐处加行内标签（F-03），旧 PDF/位图未重绘（F-04）。本报告不处理，也不据此改变任何语义。
7. **Phase 1 UI 候选独立核验仍缺失**：`docs/delivery/ui-candidate-verification.md` 不存在；本报告不评价 UI，与并行 UI Agent 无关。
8. **无实现授权**：本次修复不构成实现、测试、部署、验收或发布授权。

---

## 7. 自检

- 三份输出已完整复读：`openspec-v2-sync.md`（442 行）、`source-reconciliation.md`（207 行）、本报告。
- 两份被修文件的历史段落、证据数字、时间线均未被删除；新增内容全部带 2026-10-29 日期。
- `git diff --check` 通过；行尾空白 0。
- 未执行 commit / push / 部署 / 真机 / SSH。
