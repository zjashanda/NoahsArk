# UI Design System Progress (Phase 1 candidate)

## 2026-10-29T09:20:00+08:00 — START
- Phase: reconnaissance
- Read: docs/delivery/ui-design-system.md (228 lines, full)
- Findings: candidate already covers 10 sections (Apple principles, light/dark tokens, typography/CJK/mono, spacing/radii/shadow/motion, status language, five-axis, G0–G7, lease/occupancy/reconciliation, evidence, TaskCard, data components, responsive, a11y, token migration, Phase-1 checklist). Draft is substantially complete but enums and prohibitions need independent verification against authoritative contracts.
- Next: verify authoritative domain enums against docs/contracts/domain.md; check evidence/verdict enums; confirm lease/communication/occupancy/permit values; confirm G0–G7 naming.
- Blockers: none

## 2026-10-29T09:21:00+08:00 — corpus map
- Phase: source reading
- Sources to read: docs/contracts/domain.md (§7/§9/§11/§14/§15 referenced), docs/contracts/ui-report-knowledge-audit.md §2, docs/delivery/ui-baseline-gap-analysis.md §5–§9, docs/delivery/ui-information-architecture.md
- Next: read domain contract enum sections
- Blockers: none

## 2026-10-29T09:31:00+08:00 — enum verification complete
- Phase: contract cross-check
- Read: domain.md §7 (Gate), §9.1–9.5 (five axes, run/attempt), §11 (Lease/Device/Node), §14 (formal PASS), §15 (offline/STOP/release), §13 invariants; evidence-verdict.md §5 (manifest), §8 (access levels), §9 (evidence item state machine), §13 (occupancy); ui-report-knowledge-audit.md §2.2–2.7 (TaskCard projection); gap-analysis §6 (12 statuses), §9 (a11y/dark); IA §1–§4; design-tokens.json.
- Findings (defects in candidate):
  1. §5.1 maps `execution_status=COMPLETED` → green pass family. Contradicts domain §9.1 (“COMPLETED 只表示执行结束，不等于 PASS”) and IA §1. Must be neutral “已执行，未判定”.
  2. §5 status table lists `pass` text as “PASS / PASSED / COMPLETE” — “COMPLETE” must be removed.
  3. Tokens define `status.okInk/warnInk/dangerInk` but doc never says which ink to use on `*Soft`; only prohibits soft-as-text.
  4. `gate.notApplicable` token and `SKIPPED→NOT_APPLICABLE` projection missing; `gate.pending` #C7C7CC used as text would fail contrast.
  5. No visual mapping for device pool_state / health_state / node status / spool / interactive_session, despite DV high-density requirement.
  6. No evidence-item state machine (declared→uploading→partial→complete→verified/conflicted/unavailable/quarantined); manifest completeness fields only partly covered.
  7. Progress modes COUNTS/QUALITATIVE/INDETERMINATE and percent constraints absent.
  8. Breakpoint tiers (1024/768 split) conflict with token/IA `768–1199` tablet band; radius list omits component tokens (input 12px, terminal 18px) while forbidding arbitrary values.
  9. No explicit non-equivalence table for release≠PASS, offline≠idle, received≠verified, completed≠PASS, receipt≠verdict, skipped≠pass, candidate≠promoted, archived≠verified.
- Next: apply targeted edits to §2–§10, then diff-check.
- Blockers: none

## 2026-10-29T09:52:00+08:00 — edits applied
- Phase: refinement
- File: docs/delivery/ui-design-system.md (228 → 289 lines)
- Exact changes:
  1. Header: added enum-cross-check note (domain §7/§9.1/§11/§14/§15, evidence-verdict §5/§9.1, ui-report §2.7) and server-projection-only rule for derived vocabulary.
  2. §2: added `status.okInk/warnInk/dangerInk` row (light inks; dark uses bright status tones), `gate.notApplicable` row; added `*Soft`→`*Ink` rule, banned `gate.pending/notApplicable` as text color.
  3. §3: added CJK line-breaking (`line-break: strict`, no global `word-break: break-all`), no manual spacing, full-width punctuation not tracked.
  4. §4: separated radius scale from component tokens (input 12px, card 22px, terminal 18px); new radius must be registered in tokens.
  5. §5 status table: removed `COMPLETE` from pass; added `executed` (COMPLETED, neutral), `expected` (EXPECTED, neutral), `released` (RELEASED/CLOSED/ARCHIVED, neutral); attention now includes NEEDS_REVIEW; green restricted to pass family; STALE threshold server-supplied, OFFLINE not IDLE/FREE.
  6. New §5.1 “禁止等价与禁改写”: 10-row table covering release≠PASS, offline≠idle, received≠verified, COMPLETED≠PASS, receipt≠verdict, SKIPPED≠PASS, candidate≠promoted, archived≠verified, unknown percent, smoke/simulated≠formal.
  7. Renumbered old 5.1–5.5 → 5.2–5.6. §5.2 fixed execution axis COMPLETED→executed (not green), EXPECTED→expected (not green), added “single axis green ≠ overall pass”.
  8. §5.3 added authority→projection gate map (SKIPPED→NOT_APPLICABLE), pending text contrast rule, gate PASSED≠business PASS.
  9. §5.4 added four-signal visual map (lease/comm/occupancy/permit) + device/node enum map (pool_state 8, health_state 4, node status 4, spool 4, session 3); HELD shown as accent outline vs OCCUPIED accent solid.
  10. §5.5 added manifest source fields (`required_total/present/verified`, `completeness.result`, missing/digest/conflict lists) and evidence-item state machine (8 states; complete≠verified, partial≠failure).
  11. §5.6 added progress modes COUNTS/QUALITATIVE/INDETERMINATE with percent formula constraints; stale reasons and last_authoritative_update vs last_known_at separation.
  12. §6 table header: banned `text.quaternary` on `surface.sunken` (measured 4.34:1 < 4.5:1).
  13. §7 rewritten to IA §3 navigation: desktop left fixed rail, 1024–1199 icon rail, 768–1023 rail+drawer, <768 bottom tabs; added nav a11y (`nav` landmark, skip link, aria-current); flagged `wideTablet`/`navRailWidth` token gaps; page padding now full 3-value shorthand.
  14. §8 added forced-colors system keywords and `color-scheme` declaration rule.
  15. §9 added rule 8: component tokens / inks / notApplicable / wideTablet must be registered before use.
  16. §10 added checks for non-equivalence copy, full enum coverage, progress modes, breakpoint token; expanded unresolved list (EXPECTED semantics, wideTablet, chart tokens).
- Verification: re-read full file; scripted table pipe-count check → no issues; heading order 1–10 + 5.1–5.6 intact; `grep` for trailing whitespace/conflict markers → none; `git diff --check` exit 0 (file is untracked, so diff is empty; whitespace check also run directly).
- Note: IA §3/Q-11 required §7 writeback from “≥1024 横排导航” to left-rail navigation; done.
- Unresolved design decisions (recorded in §10): Q-04 dark mode in V0.0.1; 12→10 region collapse (IA Q-02); `/console` vs `/aitest` compat (Q-03); print/PDF surface (Q-07); EXPECTED product semantics & final visual family; `wideTablet` token registration; chart/metric visual contract not yet specified.
- Blockers: none
