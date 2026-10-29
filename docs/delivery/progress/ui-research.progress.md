# UI Design Research — Progress Log

Scope: write only `docs/delivery/ui-design-research.md` (+ this log). No product code, no `.omo`, no `plan.md`, no commits.

## 2026-10-29T09:20+08:00 — Phase 0: bootstrap

- Phase: environment scan / source inventory.
- Files read: repo root listing; `docs/delivery/` listing; `plan.md` (grep for UI/HIG context); `docs/delivery/ui-design-system.md` (lines 1-120); `docs/delivery/ui-information-architecture.md` (lines 1-90).
- Findings:
  - `docs/delivery/` already holds `ui-design-system.md`, `ui-information-architecture.md`, `ui-screen-specification.md`, `ui-baseline-gap-analysis.md`; the new research doc must complement, not duplicate, and must not edit them.
  - Existing design system already encodes Apple-inspired "Quiet Instrument" tokens, five-axis status separation, stale/offline rules — these are the local decision anchors the research doc must cite.
  - `plan.md` §AC-10 requires UI/task card/report consistency with Linux authoritative state, five status axes, stale marking on comms loss, no false "stopped" during offline soak.
- Next action: read `docs/v2/UI-DESIGN-APPLE.md`, `docs/contracts/domain.md` status sections, `docs/delivery/ui-screen-specification.md`, gap analysis; then confirm authoritative Apple HIG and operations-console sources with dates.
- Blockers: none.

## 2026-10-29T09:32+08:00 — Phase 1: local evidence gathered

- Phase: local source reading (UI baseline + contracts index).
- Files read: `docs/v2/UI-DESIGN-APPLE.md` (lines 1-80, heading map); `docs/delivery/ui-screen-specification.md` (headings, §4); `docs/delivery/ui-baseline-gap-analysis.md` §7 density, §9 accessibility/dark mode; `docs/contracts/domain.md` heading map; `docs/contracts/` file list.
- Findings:
  - Density policy is explicitly per-region: MC/Intake/Report default "restrained", Runs/Evidence/Devices/Runtime/Audit "high density". Research must justify BOTH, not pick one.
  - A11y P0 gaps already enumerated (5-axis table semantics, aria-live for offline/reconcile, disabled reasons, focus management, 200% zoom, 44px targets, NVDA/axe). Research should cite these as the local requirement set.
  - Dark mode: gap analysis §9.4 offers Option A (light-first, semantic layer reserved) vs Option B (full dark in Phase 1); unresolved decision — research must not silently decide.
  - `docs/contracts/domain.md` §9.1 forbids collapsing five axes; §14 defines formal PASS; §15 covers offline/STOP-first/release.
- Next action: verify authoritative external sources (Apple HIG, W3C WCAG 2.2, Carbon/Atlassian/Grafana/GOV.UK, NN/g, web.dev) with live fetches for title/date and principle accuracy.
- Blockers: none.

## 2026-10-29T09:52+08:00 — Phase 2: external sources verified

- Phase: source verification (live fetch of every cited URL).
- Sources verified (title + revision date read from page/change log):
  - HIG Design principles — change log "June 8, 2026: Reintroduced design principles"; current set is Purpose/Agency/Responsibility/Familiarity/Flexibility/Simplicity/Craft/Delight; the old Clarity/Deference/Depth triad is **no longer on the page**.
  - HIG Accessibility — change log June 9, 2025; 4.5:1 up to 17pt, 3:1 at 18pt/bold, 200% text enlargement, 44x44pt default / 28x28pt min control, 12pt/24pt spacing.
  - HIG Color — change log December 16, 2025; no single color for two meanings; supply light+dark+increase-contrast variants.
  - HIG Dark Mode — change log August 6, 2024; dark colors are not inversions; >=4.5:1, strive 7:1 for custom colors; base/elevated backgrounds.
  - HIG Layout — change log September 9, 2026; lay out by available space (size classes), not device type; functionality constant, visible amount varies; rows grow under text scaling.
  - Carbon Data table — "Last updated Sep 30, 2026"; 5 row heights 24/32/40/48/64px; skeleton instead of spinner; hover always on; zebra optional; toolbar <=5 actions.
  - Atlassian Lozenge — usage page undated; lozenge for status/state/priority/permission, not descriptive metadata; semantic vs accent color; filled icon sparingly.
  - Grafana No Data and Error states — undated "latest" docs; No Data != Error != Normal; "Keep last state" mitigates blips but is warned against for strict monitoring; state-reason annotation.
  - Grafana Stale alert instances — undated; stale != No Data; stale -> Normal(MissingSeries) resolved -> **evicted from UI**. Direct conflict with NoahsArk AC-10.
  - W3C WCAG 2.2 — spec 12 December 2024; Understanding pages updated 11 May 2026 / 06 September 2026.
- Findings: exactly 10 sources fit the 6-10 cap; GOV.UK Table, NN/g response times and web.dev Offline cookbook were consulted and deliberately excluded (documented as exclusions, not silently dropped).
- Next action: write `docs/delivery/ui-design-research.md` (Chinese, ~330 lines), then re-read both files and run `git diff --check`.
- Blockers: none.

## 2026-10-29T10:12+08:00 — Phase 3: draft written + self-review fixes

- Phase: artifact written, then re-read line-by-line and corrected.
- File: `docs/delivery/ui-design-research.md` (525 lines per `wc -l`).
- Structure: 0 一页结论 / 1 来源总表(10) / 2 逐条分析(S1–S10，各含原则+应用+局限) / 3 主题综合(克制预算、密集表格、状态语义、a11y、响应式、深色、离线陈旧对账) / 4 与本地文档关系(确认+修正 R-1..R-8) / 5 建议 A-1..A-9 / 6 未决 OQ-1..OQ-8 / 7 验证与边界 / 8 访问记录.
- Self-review fixes applied:
  - 引用锚点纠错：五轴固定顺序在 `ui-design-system.md` §5.2（原写 §5.1）；IA 迷路风险在 `ui-baseline-gap-analysis.md` §9.3（原写 IA §9）。
  - 事实纠错：Carbon 24px 行高是「卡在 WCAG 24×24 下限」而非「低于」；2.2.2 改为「自动开始且持续 >5s 的移动/闪烁/滚动/自动更新」。
  - 逻辑纠错：Grafana `Normal` 不再映射为本地 `empty`（`empty` ≠ 通过）；离线组合由「四信号」改为准确的「五信号」。
  - 编号去重：本文未决问题改为 OQ-1..OQ-8，避免与本地既有决策编号 Q-04 冲突。
  - 文字：三句→四句；「这三类」→「这几类」；`domain.md` 统一为 `docs/contracts/domain.md`。
- Verification: 10 source rows confirmed; 0 table-pipe issues; 0 trailing whitespace; 0 tabs; `git diff --check` clean; `git diff --check --no-index /dev/null <file>` emits no whitespace diagnostics for both files.
- Scope: only the two files above were written. `git status` shows unrelated pre-existing modifications from other sessions (docs/v2, openspec, .gitignore, README) — untouched by this session.
- Next action: none; deliverable complete pending reviewer read.
- Blockers: none.
