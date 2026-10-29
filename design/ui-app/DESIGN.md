# Cloudline UI Design Contract

## 1. Status

**CANDIDATE UI · PROTOTYPE · NOT FROZEN · MOCK DATA**

Cloudline is a dependency-free static candidate UI for the NoahsArk AI test-engineer platform console. It has no backend and no framework lock (**P2-05 pending**). This is not an acceptance artifact, implementation authorization, or freeze artifact.

## 2. Research basis

- `docs/delivery/ui-design-system.md` — Quiet Instrument principles, semantic state channels, tokens, five-axis display, accessibility, and responsive constraints.
- `docs/delivery/ui-information-architecture.md` — 12-area navigation, task lineage, route structure, state separation, density, and responsive navigation bands.
- `docs/delivery/ui-screen-specification.md` — screen purposes, evidence boundaries, gate placement, STOP-first/reconciliation behavior, and read-only projection rules.
- `1.md` — platform lifecycle, Linux authority, Windows fact reporting, five-axis PASS rule, and Phase 1 prototype boundary.
- `.omo/plans/noahsark-platform-delivery.md` — Phase 1 UI deliverables and P2-05 framework decision remains pending.

## 3. Visual direction

Apple-informed **Quiet Instrument**: neutral surfaces, one restrained blue accent, generous whitespace, hairline dividers, and subtle depth. Use the 8pt spacing scale and system/CJK font stack only. No gradients, glass, neon, colored side stripes, accent outlines on cards, emoji icons, or external fonts. Cards use tonal surface changes and hairlines, not colored edges or accent outlines.

## 4. Tokens (`styles.css`)

All visual values use these custom properties; dark values are independently assigned in the dark theme branch.

| Group | Custom property | Light | Dark |
| --- | --- | --- | --- |
| Surface | `--naa-surface-canvas` | `#F5F5F7` | `#0B0B0D` |
| Surface | `--naa-surface-raised` | `#FFFFFF` | `#1C1C1E` |
| Surface | `--naa-surface-sunken` | `#EDEDF0` | `#2C2C2E` |
| Ink | `--naa-ink-primary` | `#1D1D1F` | `#F5F5F7` |
| Ink | `--naa-ink-secondary` | `#424245` | `#C7C7CC` |
| Ink | `--naa-ink-tertiary` | `#5F5F64` | `#A1A1A6` |
| Line | `--naa-line` | `rgba(0,0,0,.07)` | `rgba(255,255,255,.10)` |
| Action | `--naa-action` | `#0071E3` | `#0A84FF` |
| Action | `--naa-action-ink` | `#FFFFFF` | `#FFFFFF` |
| Focus | `--naa-focus` | `#0071E3` | `#0A84FF` |
| Status | `--naa-status-neutral` | `#6E6E73` | `#8E8E93` |
| Status | `--naa-status-attention` | `#9A6400` | `#FFB340` |
| Status | `--naa-status-danger` | `#C4312A` | `#FF6B66` |
| Status | `--naa-status-success-limited` | `#1A7F45` | `#4CC38A` |
| Radius | `--naa-radius-sm` / `--naa-radius-md` / `--naa-radius-lg` / `--naa-radius-pill` | `10px / 14px / 22px / 999px` | same |
| Spacing | `--naa-space-1` through `--naa-space-10` | `4 / 8 / 12 / 16 / 24 / 32 / 40 / 48 / 64 / 80px` | same |
| Type | `--naa-type-display` / `--naa-type-heading` / `--naa-type-body` / `--naa-type-small` / `--naa-type-caption` | `56/40/32px` / `28px` / `14px` / `13px` / `12.5px` | same |

Font stacks: `-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", "Microsoft YaHei UI", sans-serif`; IDs and evidence keys use `SFMono-Regular, Cascadia Mono, Cascadia Code, Consolas, "Microsoft YaHei UI", monospace`.

## 5. Semantic color rules

- `COMPLETED`, `EXPECTED`, and `RELEASED` are neutral, never green. `received` is not `verified`; `OFFLINE` is not idle or stopped.
- Formal `PASS` is permitted only for the exact five-value tuple: `COMPLETED / VALID / PASS / COMPLETE / PASS` in the fixed axis order execution, validity, business, evidence, verification.
- Color is never the only channel: every state has text + glyph + shape, with color as the third channel. Unknown values fail closed to `UNKNOWN`; no invented synonym or inferred success.

## 6. Primitives inventory

App shell (fixed sidebar, topbar, content); nav item; page header; section; card/panel; data table; definition list; axis strip (5 axes); evidence row (`expected` / `received` / `verified`); gate chip; state banner (`offline` / `stale` / `unknown` / `blocked` / `partial` / `reconciling` / `draining` / `quarantined`); status badge; empty state; timeline; inspector panel; button; segmented control; toast-free inline feedback.

The axis strip never collapses the five axes. Evidence keeps expected, received, and verified distinct. Node-observed facts and Linux platform judgment remain separate. Disabled actions retain a visible reason.

## 7. Layout grammar

- One scroll owner: the main content. Sidebar, topbar, and mobile navigation remain fixed.
- The shell is `100dvh`; all contained flex/grid children use `min-height: 0` to preserve the single scroll owner.
- **≥1200px:** full fixed sidebar with the eight primary entries and Operations group.
- **1024–1199px:** compact icon rail with expandable labels.
- **768–1023px:** icon rail plus overlay drawer; detail content becomes single-column.
- **<768px:** five-item bottom bar (Mission Control, Tasks, Runs, Devices, More) plus a More sheet.

## 8. Motion

Use 120–180ms transitions and compositor-safe `transform`/`opacity` only. With reduced motion, collapse transitions to a cross-fade. No decorative loops, pulsing, parallax, scroll hijacking, or motion without a state or interaction purpose.

## 9. Accessibility

Provide a skip link, landmark regions, visible `:focus-visible` rings, and `aria-current` for the current area. Name every icon-only control. Preserve function and critical facts at 200% zoom; local horizontal scrolling is allowed where necessary. Provide forced-colors fallbacks using text, 1px borders, and glyph shapes; never depend on background color alone.

## 10. Accepted prototype debt

- Mock fixtures only; no persistence and no authentication.
- RT/AG write actions are disabled with a visible reason because their access decision remains pending.
- No i18n and no charts.
- Static projection only: no backend, real execution, authority writes, or acceptance evidence.
