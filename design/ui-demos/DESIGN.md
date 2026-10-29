# NoahsArk UI Direction Comparison

> **DRAFT · PROTOTYPE** — a static comparison exercise for choosing a direction. This is not a UI freeze, production implementation, accessibility certification, or visual-QA result.

## 0. Research Log

- Delivery inputs: `ui-screen-specification.md`, `ui-design-system.md`, and `ui-information-architecture.md` establish the five independent verdict axes, evidence vocabulary, responsive IA, and Linux-authoritative status boundary.
- Embedded references: `minimalist-skill.md` + `apple.md` selected because the brief explicitly asks for Apple-inspired minimalist technology UI; their neutral canvas, single blue action ink, tight system type, and two-gear spacious/dense rhythm are adapted to NoahsArk.
- Spatial references: `layout-skill.md` contributes a named single-scroll-owner shell; `stylegallery.md` was read. External retrieval was deliberately skipped: the user requires local-only runtime assets and the implementation has a sufficiently named `fixed-sidenav-shell` / `list-detail` contract.
- Quality and review: `perfection/README.md`, `designpowers/README.md`, and `lane-c-review.md` inform the explicit accessibility constraints, accepted debt, and separate-reviewer boundary. No visual QA is performed by this implementation task.

> **DRAFT / PROTOTYPE / NOT FROZEN** — this bounded demo is for owner comparison only.

## 1. Atmosphere & Identity

NoahsArk is a quiet instrument, not a monitoring wall: neutral, carefully spaced surfaces carry authoritative facts without manufacturing confidence. Its signature is **verdict separation**—the same five-axis evidence block remains unmistakably discrete while each direction changes the information architecture around it. One restrained blue signals navigation, active work, and direct actions; it never acts as decoration or a proxy for PASS.

## 2. Shared Semantic Contract

- **Fixture identity:** every demo reads one local `fixtures.js` fixture projection labeled `source: prototype-fixture`, `schema_version: 0.1`, `server_authoritative: false`. It is illustrative data only, never a live API or a claim of Linux authority.
- **Five axes, fixed order:** execution → validity → business verdict → evidence → verification. `COMPLETED` is neutral execution fact, not PASS. A business `PASS` combined with incomplete evidence remains **not eligible for formal PASS**.
- **Evidence:** `expected`, `received`, and `verified` are distinct. Received evidence is not verified evidence.
- **Independent signals:** communication, occupancy, permit, release, and verdict never replace each other. `OFFLINE` retains `RUNNING`, `OCCUPIED`, and `GRANTED`; release remains unrelated to the verdict.
- **Required facts on both views:** offline, stale, blocked, partial evidence, unknown progress, evidence three-column counts, and a release state independent of a verdict.

## 3. Color

All runtime colors are semantic CSS custom properties in `styles.css`; individual directions only reassign surface/density tokens.

| Role | Token | Light | Dark | Use |
|---|---|---|---|---|
| canvas | `--c-canvas` | `#f5f5f7` | `#0b0b0d` | application background |
| raised | `--c-raised` | `#ffffff` | `#1c1c1e` | cards and panels |
| subtle | `--c-subtle` | `#fbfbfd` | `#161618` | grouped facts / hover wash |
| ink | `--c-ink` | `#1d1d1f` | `#f5f5f7` | primary text |
| muted | `--c-muted` | `#5f5f64` | `#a1a1a6` | metadata |
| hairline | `--c-line` | `rgba(0,0,0,.10)` | `rgba(255,255,255,.14)` | dividers / containment |
| action | `--c-action` | `#0071e3` | `#0a84ff` | only interactive/active/focus signals |
| action contrast | `--c-on-action` | `#ffffff` | `#ffffff` | text on the action surface |
| pass | `--c-pass` | `#14663a` | `#4cc38a` | verified pass values only |
| warn | `--c-warn` | `#7d4a00` | `#ffb340` | blocked/incomplete/review |
| danger | `--c-danger` | `#a82721` | `#ff6b66` | failure/quarantine |

Rules: no colored edge stripes, no colored card outlines, no decorative gradients, and no status represented by color alone.

## 4. Typography, Spacing & Surface

- **Font stack:** `-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", "Microsoft YaHei UI", sans-serif`; mono facts use `SFMono-Regular, Cascadia Mono, Consolas, monospace`. No external fonts.
- **Type tokens:** `--type-display: clamp(2rem, 4vw, 3.5rem)`, `--type-h1: 2rem`, `--type-h2: 1.25rem`, `--type-body: .875rem`, `--type-small: .75rem`, `--type-micro: .6875rem`.
- **Spacing scale:** `--s-1` 4px, `--s-2` 8px, `--s-3` 12px, `--s-4` 16px, `--s-5` 20px, `--s-6` 24px, `--s-8` 32px, `--s-10` 40px, `--s-12` 48px, `--s-16` 64px.
- **Radius:** 10px compact controls, 14px tables, 18px panels, 22px cards, 999px status chips. Depth uses neutral hairlines plus the `--shadow-control` token only for active segmented controls and overlays.

## 5. Primitives

### App shell
- **Structure:** skip link → prototype ribbon → fixed navigation/header regions → one named main scroll owner.
- **Variants:** `cloudline` fixed left side navigation; `precision` compact rail + instrument header; `focus` top navigation + contextual inspector.
- **Accessibility:** landmark regions, current page label, keyboard reachable controls, `min-block-size: 0` scroll body.

### Status chip
- **Structure:** inline SVG glyph + authoritative value text.
- **Variants:** neutral/executed, active, pass, warning, danger, unknown; never communicates with color alone.
- **States:** static facts; no animation.

### Axis matrix
- **Structure:** semantic table/caption with five fixed-order rows.
- **States:** completed, valid, business pass, partial evidence, not-run verification; the displayed overall message is not formal PASS.

### Evidence ledger
- **Structure:** three labeled counts (`expected / received / verified`) and a concise explanatory line.
- **States:** partial, complete, conflicted, unknown; received and verified are distinct values.

### Task card / instrument row
- **Structure:** title, discreet stage/run metadata, explicit signals, and one detail link.
- **Variants:** spacious card (A), compact row (B), workspace queue item (C).
- **States:** default, hover wash, keyboard focus, stale/offline/blocked. No colored border state.

### Theme and view controls
- **Structure:** native `<button>` with inline SVG and visible text/tooltip label.
- **States:** hover, pressed, focus-visible; persisted through `localStorage`; reduced motion has no transform transition.

## 6. Direction Contracts

| Direction | Spatial grammar | Density / grouping | Navigation |
|---|---|---|---|
| **A · Cloudline** | `fixed-sidenav-shell`: quiet vertical sidebar, broad editorial main column, optional calm supporting column | low density, generous cards, air between decisions | restrained left sidebar |
| **B · Precision Desk** | `fixed-sidenav-shell`: compact rail, instrument header, data grid as the primary surface | high-but-calm density, aligned rows, scan bands | narrow icon/label rail and local filter strip |
| **C · Focus Flow** | top-navigation workspace with task queue, primary canvas, and contextual right inspector | workflow-first, panel-led progressive disclosure | top navigation; right inspector has its own job |

All directions retain the same fixture, both Mission Control and Task Detail view, theme toggle, and responsive behavior. Only layout and information language vary.

## 7. Layout & Responsive Rules

- **Scroll ownership:** each demo uses one main application scroll owner. Fixed/structural regions do not compete for document scrolling.
- **Desktop ≥1200:** A uses 232px sidebar + main; B uses compact 96px rail + main; C uses top navigation and a three-region workspace.
- **Tablet 768–1199:** A/B reduce navigation to a compact rail and collapse secondary content; C collapses the inspector beneath the workspace.
- **Mobile <768:** navigation becomes a horizontal bottom/switcher surface, all primary layouts become one column, action targets have a minimum 44px block size, and the axis table remains readable via vertical rows.
- **Content stress:** labels wrap, identifiers use `overflow-wrap:anywhere`, data grids retain a contained horizontal overflow only where needed, and unknown progress is text—not a synthetic percentage.

## 8. Motion & Accessibility Constraints

- Only 140ms/220ms `transform` and `opacity` transitions for control feedback and view changes; no autonomous or decorative animation.
- `prefers-reduced-motion: reduce` disables transitions while preserving every state and control.
- `:focus-visible` gets a blue focus ring; semantic buttons/links, landmarks, headings, table captions, and readable status text are required.
- Theme is explicit, local, and persisted. It does not rely only on OS preference.
- Theme, control interaction, and selected view changes have accessible labels. No claim of WCAG certification is made.

## 9. Accepted Debt & Prototype Boundary

| Item | Location | Why accepted | Exit |
|---|---|---|---|
| Two views only per direction | all direction pages | comparison exercise intentionally excludes the 39-route implementation | owner selects direction and the route plan expands |
| Static fixture only | `fixtures.js` | no backend/API is allowed in this prototype | future read-model contract |
| No independent visual QA | all surfaces | user explicitly assigns visual QA to a separate reviewer | reviewer performs desktop/mobile, themes, clicks, console review |
| No automated a11y audit | all surfaces | dependency-free static scope | audit in later implementation phase |

## 10. Implementation Status

**DRAFT · PROTOTYPE.** The demo is local-only, static, and comparison-oriented. It intentionally does not assert owner approval, production readiness, UI freeze, live status, or formal PASS.
