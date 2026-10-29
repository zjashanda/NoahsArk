# 已批准草案源级冲突对账报告

> 执行日期：2026-10-29（Asia/Shanghai）
> 范围：仅修正四份已评审草案中与更晚批准规则冲突的**规范性陈述**。
> 结论：C-18 所列源级冲突已完成正文更正，并以追加修订说明保留原评审历史。本报告不构成实现、契约冻结、测试、部署或发布授权。

---

## 1. 背景与权威依据

`docs/delivery/openspec-v2-sync.md` §4 C-18 登记：`.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md`（I-21、§7 规则 4）与 `.omo/drafts/01-design/noahsark-v0.0.1-module-design.md`（§2.6）仍保留“缺 `cleanup_receipt` = 证据不完整”“心跳/租约超时 → `run=INFRA_ERROR`”等旧表述；P0-03 因同步对象边界未改草案正文，仅登记遗留。本任务即关闭该遗留，并把同类冲突一并收敛到四份已评审草案。

事实源优先级沿用 `docs/VERSIONING.md` §1–§3 与 `docs/delivery/openspec-v2-sync.md` 头部：根 `plan.md` 中更晚的所有者批准记录 > 已评审草案正文。因此，**2026-10-28 的根 `plan.md` 批准记录取代草案中 2026-10-27/28 早期评审时的旧表述**，而不是反过来用旧草案否定新批准。

本任务引用的具体批准记录：

| 批准记录（根 `plan.md`） | 行号 | 确立规则 |
|---|---|---|
| 《契约评审：离线压测规则确认》 | 283 | 已启动冻结压测不因断联/心跳不可达/租约无法续期自动停止；设备保持占用；重连先补传对账；未授权断联期间启动新任务 |
| 《字段级契约评审：第 2 项 Job/Lease/Node Agent 消息确认》 | 339 | Job 执行许可、设备独占、通信在线三态分离；重连先处理待送达 STOP，再补传/去重/对账；旧 epoch 不改变当前运行 |
| 《字段级契约评审：第 4 项业务边界确认》 | 364 | 本地停止、安全清理、占用对账后可释放，不等 GB 级日志归档或最终判定；“证据全部上传后才可释放”以本条为准 |
| 《第三步时序评审确认与第四步启动》 | 372 | 断线续跑且设备占用；STOP-first；释放与证据/判定分离；恢复不能凭心跳超时重派 |
| 《M-04 资源资格、设备占用与租约确认》 | 428 | 通信离线 ≠ 设备空闲；释放条件；连续异常才 draining/quarantined |
| 《M-07 证据与判定确认》 | 440 | 执行停止、证据上传/校验、设备释放、正式判定彼此独立 |
| 《A-3 资源与租约准则确认》 | 547 | 失联续跑、过期不重派、重连 STOP-first、清理失败不释放、普通通信中断不触发隔离 |
| 《A-5 门禁与独立判定准则确认》 | 559 | 通信断开不自动判已启动压测失败或释放设备；四类事实分别建模 |
| 《S5-3 门禁、证据与判定矩阵确认》 | 609 | 缺 `cleanup_receipt` 只表示不能确认设备释放、设备保持占用，不直接等同证据不完整 |
| 《AC-11 至 AC-14 确认》 | 660 | 离线续跑、STOP-first 对账、释放/证据/判定分离、恢复顺序与仅回收已确认失效租约 |

---

## 2. 精确修改（修改前 → 修改后）

行号均指本节修改前后的**目标文件行号**。所有原文语义均保留在新增的修订说明章节；未删除、未改写任何既有评审结论或批准记录。

### 2.1 `.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md`

| 位置（前） | 位置（后） | 修改前 | 修改后 | 取代依据 |
|---|---|---|---|---|
| L91 §5.2 I-21 | L91 | “运行结束必须产出 `cleanup_receipt`，缺失视为证据不完整” | “运行结束应产出 `cleanup_receipt`；缺失只阻断‘设备释放确认’，设备保持占用，不自动判定整条证据链不完整（见 §18 修订 R-1）” | plan.md L609 S5-3；L364 第 4 项 |
| L113 §6 门禁恢复 | L113 | “中断默认停止并对账，不静默续跑” | 控制面/门禁中断按持久事实恢复并先对账；已启动冻结压测不因通信中断停止且设备保持占用（见 §7 规则 4） | plan.md L283；L372；A-2（重启不凭心跳过期释放/重派/判失败） |
| L126 §7 规则 4 | L126 | “失联：标记 `lease_expired` → 运行 `INFRA_ERROR` → **先对账再重派**” | 区分已启动冻结压测与未启动作业：已启动继续离线执行、通信 `OFFLINE/STALE`、设备 `OCCUPIED`、不自动停止/回收/重派/重播/重复采样/置最终 `INFRA_ERROR`；本地人工停止与设备级安全停止独立生效；未启动作业不得开始新动作；重连先处理待送达 STOP，再补传/去重/对账；旧 epoch 不改变当前运行 | plan.md L283；L339；L428；L547；L559；L660 AC-11/AC-12 |
| L128 §7 规则 6 | L128 | “结束：必须产出 cleanup 回执；释放租约幂等” | 确认本地停止、安全清理、占用对账后可释放（幂等），不等 GB 级日志归档或最终判定；缺 `cleanup_receipt` 只阻断释放确认，设备保持占用，不自动等同证据不完整 | plan.md L364；L440；L547 A-3；L559 A-5；L660 AC-13 |
| 文件末尾（新增） | L379–L389 §18 | 无 | 新增“修订说明（2026-10-29）”，逐条登记 R-1..R-4 的原表述、现表述与依据 | 保留历史，避免让读者误以为原评审时即如此 |

### 2.2 `.omo/drafts/01-design/noahsark-v0.0.1-module-design.md`

| 位置（前） | 位置（后） | 修改前 | 修改后 | 取代依据 |
|---|---|---|---|---|
| L60 §2.2 时序末尾 | L60 | “M-05 安全点释放 + cleanup 回执” | “M-05 确认本地停止/安全清理/占用对账后释放；cleanup 回执缺失仅阻断释放确认” | plan.md L364；L547；L660 AC-13 |
| L101–L107 §2.6 设备异常 | L101–L114 | “心跳超时 → 租约过期 → `run=INFRA_ERROR` → 对账 → 设备失败计数/隔离” | 拆为三类：①通信中断/心跳失联/租约无法续期（已启动冻结压测）继续本地执行、通信 `OFFLINE/STALE`、设备 `OCCUPIED`、不自动置最终 `INFRA_ERROR`，重连 STOP-first 再补传/去重/对账；②未启动作业不得开始新动作；③设备级异常（失控/死机/清理失败）才失败计数并 draining/quarantined。补充“普通通信中断不等于设备故障，不自动触发隔离” | plan.md L283；L339；L428 M-04；L547 A-3；L660 AC-11/AC-12 |
| L192 §4.2 “失联” | L203 | “到期即 `lease_expired`，先对账再重派” | 已启动冻结压测继续本地执行；通信 `OFFLINE/STALE`、设备 `OCCUPIED`；不自动停止/回收/重派、不置最终 `INFRA_ERROR`；未启动作业不得开始新动作；重连先处理停止指令，再补传/去重/对账 | plan.md L283；L339；L547；L660 AC-12 |
| L194 §4.2 “释放” | L205 | “幂等；需 cleanup 回执” | 幂等；确认本地停止、安全清理、占用对账后释放，不等 GB 级日志归档或最终判定；缺 `cleanup_receipt` 只阻断释放确认，设备保持占用，不自动等同证据不完整 | plan.md L364；L440 M-07；L609 S5-3；L660 AC-13 |
| 文件末尾（新增） | L383–L392 §11 | 无 | 新增“修订说明（2026-10-29）”，登记 R-1..R-3 | 保留历史 |

### 2.3 `.omo/drafts/03-variants/noahsark-v0.0.1-variant-b-balanced.md`

| 位置（前） | 位置（后） | 修改前 | 修改后 | 取代依据 |
|---|---|---|---|---|
| L170 §5 “失联” | L170 | “`lease_expired` → `INFRA_ERROR` → 对账后再派” | 区分已启动冻结压测与未启动作业；已启动离线续跑、通信 `OFFLINE/STALE`、设备 `OCCUPIED`；不自动停止/回收/重派/重播/重复采样/置最终 `INFRA_ERROR`；本地人工与设备安全停止独立生效 | plan.md L283；L339；L547；L660 AC-11/AC-12 |
| L172 §5 “清理” | L172 | “缺失视为证据不完整” | 缺失只阻断“设备释放确认”，设备保持占用，不自动视为整条证据不完整 | plan.md L609 S5-3；L660 AC-13 |
| L174 §5 资源资格段落 | L174 | “租约过期后停止，不开始新动作，重连后先补传和对账再决定重试” | 已启动冻结压测断线/心跳失联/租约无法续期后继续本地执行；重连先处理待送达 STOP，再补传/去重/对账，完成前不重派/重播/重复采样；未启动作业不得开始新动作；释放不等 GB 日志归档或最终判定 | plan.md L283；L339；L364；L372；L660 AC-12/AC-13 |
| 文件末尾（新增） | L296–L305 §16 | 无 | 新增“修订说明（2026-10-29）”，登记 R-1..R-3 | 保留历史 |

### 2.4 `.omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md`

| 位置（前） | 位置（后） | 修改前 | 修改后 | 取代依据 |
|---|---|---|---|---|
| L66 §4 “节点离线” | L66 | “资源不可用，租约到期回收，不静默换设备” | 不静默换设备；已启动冻结压测继续本地执行、设备保持 `OCCUPIED`，不因心跳/租约到期自动回收/重派；未启动作业不得开始新动作；重连 STOP-first 后补传/去重/对账；本地人工与设备级安全停止独立生效 | plan.md L283；L547 A-3；L660 AC-11/AC-12；第六步优化补充审核（V0.0.1 可信底线） |
| 文件末尾（新增） | L122–L130 §10 | 无 | 新增“修订说明（2026-10-29）”，登记 R-1 | 保留历史 |

---

## 3. 为什么用较晚批准覆盖较早措辞

1. `plan.md` 是所有者审批记录载体；上述条目日期均为 2026-10-28，晚于四份草案的初稿/早期评审（2026-10-27 及部分 2026-10-28 上午）。
2. 这些条目不是一般讨论，而是明确使用“所有者认可/确认/批准”的结论，并直接点名旧规则冲突（例如离线压测修订条明确写道：不得将旧“租约过期停止/不得开始新动作”视为这类运行的最终契约）。
3. `docs/delivery/openspec-v2-sync.md` §4 C-18 已把草案内部矛盾列为“源级遗留冲突”，并说明 `docs/v2`/`openspec` 不采用旧表述；本任务只是把已批准的更晚规则回写到源草案，消除“绕过同步记录直接引用旧条”的风险。
4. 因此修订的是**规范陈述**，不是历史事实：原评审意见、原批准边界、原对标来源均原样保留；每份文件末尾新增修订说明，明确标注 2026-10-29 的变更及依据。

---

## 4. 未改动边界

未修改：

- `docs/contracts/**`（含 `lease.schema.json`、`security-node.md` 等候选契约）
- `docs/v2/**`
- `openspec/**`
- 根 `plan.md`
- `.omo/plans/**`、`.omo/boulder.json`
- 任何产品代码、脚本、测试或部署配置

未执行：提交、推送、部署、真实测试、真机执行、契约冻结。

---

## 5. 验证

### 5.1 空白/补丁检查

```bash
git diff --check
```

结果：无输出，退出码 0。

但必须说明：本次目标文件中，`.omo/` 已被 `.gitignore` 忽略，`docs/delivery/` 当前为未跟踪目录，因此 `git diff --check` 实际不覆盖上述 5 个文件（它只检查已跟踪差异）。为此补充执行未跟踪/忽略文件的空白检查：

```bash
grep -nP '[ \t]+$' \
  .omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md \
  .omo/drafts/01-design/noahsark-v0.0.1-module-design.md \
  .omo/drafts/03-variants/noahsark-v0.0.1-variant-b-balanced.md \
  .omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md \
  docs/delivery/approved-draft-reconciliation.md
```

结果：无输出，退出码 1（无行尾空白）。

### 5.2 四份草案的残留旧口径扫描

扫描模式覆盖：`缺 cleanup_receipt ... 证据不完整`、`lease_expired → INFRA_ERROR`、`心跳超时 → 租约过期 → run=INFRA_ERROR`、`租约到期回收`。

```bash
grep -nE "缺失视为证据不完整|lease_expired.*INFRA_ERROR|心跳超时.*租约过期.*INFRA_ERROR|租约到期回收|租约过期后停止" \
  .omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md \
  .omo/drafts/01-design/noahsark-v0.0.1-module-design.md \
  .omo/drafts/03-variants/noahsark-v0.0.1-variant-b-balanced.md \
  .omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md
```

结果：4 处命中，全部位于各文件新增“修订说明”表格的**“原表述（摘要）”列**，用于保留历史；正文规范语句中 0 处。命中位置：

```text
module-design.md:390            （§11 R-2 原表述列）
variant-b-balanced.md:302       （§16 R-1 原表述列）
variant-b-balanced.md:304       （§16 R-3 原表述列）
optimization-roadmap.md:128     （§10 R-1 原表述列）
```

即：活跃规范正文已无旧口径；旧措辞只作为被取代的历史记录存在。

### 5.3 新版关键规则存在性

```bash
grep -c "不自动停止、不回收、不重派" \
  .omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md \
  .omo/drafts/01-design/noahsark-v0.0.1-module-design.md \
  .omo/drafts/03-variants/noahsark-v0.0.1-variant-b-balanced.md
grep -c "不因心跳或租约到期自动回收" .omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md
```

结果：三份草案各 ≥1 处；优化路线 1 处。均明确写入“已启动冻结压测继续执行/设备保持占用/未启动作业不得开始新动作/STOP-first/释放不等归档或判定”。

### 5.4 文件行数（修改后）

```text
390 .omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md
393 .omo/drafts/01-design/noahsark-v0.0.1-module-design.md
306 .omo/drafts/03-variants/noahsark-v0.0.1-variant-b-balanced.md
130 .omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md
```

### 5.5 变更范围

```bash
git status --short
```

关键事实：`.omo/` 被 `.gitignore` 忽略，`docs/delivery/` 当前未跟踪，因此上述文件的改动**不会出现在 `git status` 的普通差异列表中**。这不是“未修改”，而是本仓库既有的忽略/未跟踪状态。已通过文件行数、grep 与内容回读确认改动落盘（见 §5.4、§5.3）。

```text
修改：.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md
修改：.omo/drafts/01-design/noahsark-v0.0.1-module-design.md
修改：.omo/drafts/03-variants/noahsark-v0.0.1-variant-b-balanced.md
修改：.omo/drafts/02-delivery/noahsark-v0.0.1-optimization-roadmap.md
新增：docs/delivery/approved-draft-reconciliation.md（本报告）
```

未修改任何禁止路径（`docs/contracts`、`docs/v2`、`openspec`、`plan.md`、`.omo/plans`、`.omo/boulder.json`）。

---

## 6. 未解决 / 需后续处理

1. **候选契约仍是旧措辞（禁止编辑）**：`docs/contracts/README.md` §2.3 登记的 `security-node.md` `lease_expired` 措辞与 `schemas/security/lease.schema.json` 的 `expired` 状态不在本任务范围；权威语义应为“`expires_at` 是续约截止，不是所有权到期/自动回收”。应由 P0-05 契约修正任务处理。
2. **占用枚举命名未统一**：`docs/contracts/domain.md` 的 `IDLE/OCCUPIED/RELEASING` 与 `docs/v2`/`openspec` 的 `OCCUPIED/RELEASING/RELEASED/QUARANTINED` 语义一致但名称不同；本任务未改契约，建议契约冻结时统一。
3. **数值/时序未冻结**：租约时长、心跳间隔、重连超时、spool 预警/保护阈值、日志共享挂载参数仍未冻结；本次只修正业务规则，不发明数值。
4. **组件表中的 `reaper` 命名**：架构 CP-06 与模块 M-06 仍保留 `reaper`/“回收记录”作为组件能力名，其行为现由 §7 规则 4/6 约束（只对账过期租约，不自动回收已启动运行）。契约冻结时建议更名为“过期租约对账器”，以免误读；本次不做非必要的布局性改名。
5. **变体内嵌 SVG 未重绘**：图 B-1 中“安全点释放租约（幂等）”与新规则一致，未重绘；若后续重绘，应同步加入“离线续跑/占用保持/STOP-first”标注。
6. **其他草案未在本次范围**：`delivery-acceptance.md` 与 `test-strategy.md` 已在此前记录中同步（见 plan.md 第五步归档条“测试策略正文已同步为 v2.2”）；本次未改，以免扩大范围。若后续发现新冲突，应另开对账条目。
7. **P0-03 报告 §9 第 1 项**：本任务完成后，该“源级草案内部矛盾”遗留可视为已处理；但 `docs/delivery/openspec-v2-sync.md` 按任务边界未回写更新，建议由主控在归档时附本报告链接，而不是原地重写既有证据报告。
