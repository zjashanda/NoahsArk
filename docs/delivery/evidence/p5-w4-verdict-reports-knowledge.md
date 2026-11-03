# P5-W4 Verdict, Report, Knowledge and TaskCard Evidence

- Date: 2026-10-30
- Status: IMPLEMENTED AND VERIFIED AT CONTROL-PLANE UNIT/DB/API LEVEL
- Scope: W4 only. No W5/W6/UI/frontend, no SSH, no node bootstrap, no production deployment, no real-device acceptance.
- Plan item `20` is **not** marked complete here; the orchestrator owns the checkbox.

## Delivered

### Five-axis verdict derivation (fail-closed)

- `noahsark/domain/verdict_rules.py`
  - `FORMAL_PASS_PRECONDITIONS` contains exactly the 11 contract keys.
  - `derive_verdict()` follows `docs/contracts/evidence-verdict.md` §14.2 order.
  - `PASS`/`formal_pass=true` is only produced when all 11 preconditions hold.
  - Smoke/static modes return `decision=NOT_APPLICABLE` and never enter the formal denominator.
  - Release, archive state and node-reported status are not derivation inputs.
- `noahsark/services/verdict_facts.py` resolves approval validity, frozen boundary, manifest completeness, digest verification, blocking anomalies and denominator eligibility from authoritative rows.
- `noahsark/services/verdicts.py` persists one immutable `Verdict` per run and appends `VERDICT_RECORDED`; re-evaluation is `409 VERDICT_IMMUTABLE`.

### Reports

- `noahsark/services/report_model.py`, `report_sections.py`, `reports.py`, `report_freeze.py`
  - Exactly 14 categories from `docs/contracts/ui-report-knowledge-audit.md` §3.2.
  - Missing categories are emitted as `EMPTY` or `NOT_APPLICABLE`, never omitted.
  - Versions are `max(existing version) + 1` per task.
  - Freeze is a one-way `DRAFT -> FROZEN` transition; frozen content is not edited in place.
  - Run, evidence, release and unresolved records remain separate.

### Knowledge

- `noahsark/services/knowledge.py`
  - Candidates are never promoted automatically.
  - Promotion requires the target-library capability, an `APPROVED` candidate, a complete source chain and a human actor.
  - Agents/system actors and non-`APPROVED` states fail closed.
  - Promotion creates a new `KnowledgeItem` and appends `KNOWLEDGE_PROMOTED`; candidate history is not deleted.

### TaskCard

- `noahsark/services/read_models.py` adds `task_card` to task summaries/overview.
  - Stage, run state, axes, resources, blocker owner/next step, counts/progress and freshness are separate fields.
  - Unknown progress stays `INDETERMINATE` with `percent=null`; it is never coerced to 0 %.
  - Freshness remains independent from communication state.

### Write surface

- `POST /api/v1/runs/{run_id}/verdicts`
- `POST /api/v1/tasks/{task_id}/reports`
- `POST /api/v1/reports/{report_id}/freeze`
- `POST /api/v1/knowledge/candidates/{candidate_id}/promotions`

All four require `Idempotency-Key` and explicit capabilities (`VERDICT_WRITE`, `REPORT_WRITE`, `KNOWLEDGE_PROMOTE` + target-library capability). Only `ADMIN` holds the new W4 capabilities.

## Verification commands and results

```bash
cd /home/bszheng/NoahsArk/apps/control_plane
/home/bszheng/NoahsArk/.venv/bin/python -m pytest -q tests/test_p5_w4_verdict_reports_knowledge.py
# 8 passed

/home/bszheng/NoahsArk/.venv/bin/python -m pytest --disable-warnings \
  tests/test_api_batch1.py tests/test_api_batch2.py tests/test_api_batch3.py \
  tests/test_ui_routes_coverage.py tests/test_api_writes.py
# 67 passed (W4 + these selected suites together = 74)

/home/bszheng/NoahsArk/.venv/bin/python -m pytest --disable-warnings
# 139 passed, 1 warning in 13.46s (previous W3 baseline was 131)

/home/bszheng/NoahsArk/.venv/bin/ruff check noahsark tests
# All checks passed!

/home/bszheng/NoahsArk/.venv/bin/mypy noahsark
# Success: no issues found in 55 source files
```

Local PostgreSQL was reachable, so the seeded DB/API paths executed rather than skipped.

## Regression coverage added

`tests/test_p5_w4_verdict_reports_knowledge.py` locks:

- each of the 11 prerequisites individually blocks formal `PASS`;
- smoke `mode_outcome=PASS` cannot become a formal PASS decision;
- missing/incomplete evidence and missing Linux review are fail-closed;
- seeded `run-031` has the exact five-axis tuple but lacks approval/manifest completeness, and the API still refuses PASS;
- report creation is 14 sections, versioned, freeze is one-way, correction creates the next version;
- a `PROPOSED` knowledge candidate cannot be promoted; an `APPROVED` one can, and non-ADMIN is denied;
- TaskCard preserves counted progress for the seeded task and unknown progress for a task with no formal cases;
- manifest counters must be backed by actual expected/verified evidence rows, so a manifest claiming more verified evidence than exists fails closed.

## Manual API QA (verification gate)

Executed with `fastapi.testclient.TestClient` against a freshly seeded local PostgreSQL authority; 43 checks passed. The QA script is temporary (`/tmp/w4_manual_qa.py`) and not committed.

Covered per route:

- missing `Idempotency-Key` -> `400 IDEMPOTENCY_REQUIRED`;
- `OBSERVER`/`APPROVER` capability denial -> `403 FORBIDDEN`;
- unknown run/task -> `404 NOT_FOUND`;
- malformed report disclosure and promotion target -> `400 VALIDATION_ERROR`;
- verdict fail-closed creation, exact five-axis tuple with `formal_pass=false`, 11 prerequisite keys, idempotent replay, and `409 VERDICT_IMMUTABLE` on a new key;
- 14-section report creation/detail, idempotent replay, one-way freeze, preserved digest, second freeze `409 REPORT_NOT_DRAFT`, correction version increment;
- knowledge promotion rejection for `PROPOSED`, agent actor, and non-ADMIN; successful `APPROVED` promotion; promoted knowledge item readback; idempotent replay; second promotion `409`;
- TaskCard counted progress for the seeded task and `INDETERMINATE`/`percent=null` for a task with no formal cases.

## Verification-gate defect found and fixed

Manual QA reviewed the fail-closed evidence logic and found that `evidence_facts()` trusted `required_evidence.required_total == required_verified` plus "all present rows verified" without checking that the expected evidence rows actually existed. A manifest claiming 5 verified while containing 3 rows could therefore satisfy `required_evidence_complete`/`digest_verified`.

Fixed in `services/verdict_facts.py`: expected rows must number at least `required_total`, and verified rows must number at least `required_total`. Added a regression test (`test_manifest_counts_must_be_backed_by_evidence_rows`). Focused W4 is now 8 passed; full suite 139 passed.

## Limitations / not claimed

- No production readiness, real-device acceptance, W5 Node Agent, W6 UI, or Phase 6 formal acceptance is claimed.
- Positive formal PASS is proven at the pure derivation layer with all 11 preconditions true. Seeded DB runs intentionally do not satisfy the full tuple, so the DB/API proof is the negative fail-closed case.
- Report sections are structures with truthful `PRESENT`/`EMPTY`/`NOT_APPLICABLE` status; human-authored prose content for every section is not fabricated.
- `read_models.py` remains a pre-existing oversized module; this wave only added a bounded TaskCard helper.
