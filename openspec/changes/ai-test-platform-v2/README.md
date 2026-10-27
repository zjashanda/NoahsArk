# ai-test-platform-v2 OpenSpec change

P0-01 documentation/specification deliverable for the AI Test Platform v2 plan. No product code, database, existing main spec or unrelated file is changed by this draft.

## Traceability

| Requirement | Capability delta | Primary tasks |
|---|---|---|
| 1 Model switching | `model-policy` | P1-01..P1-07, P7-05, P8-06 |
| 2 Version/upgrade compatibility | `toolchain-compatibility` | P0-03, P1-01, P7-06, P8-01, P8-02, P8-07 |
| 3 Active push | `platform-events-push` | P2-01..P2-06, P7-10, P8-04 |
| 4 Similar retrieval/playbook | `knowledge-retrieval`, `task-playbook` | P3-02..P3-04, P7-04, P8-04 |
| 5 Failure and knowledge write-back | `knowledge-retrieval`, `task-playbook` | P3-01..P3-10, P7-08, P8-05 |
| 6 Completion contract | `completion-gate` | P0-04, P5-01..P5-07, P8-05 |
| 7 Human takeover | `takeover-session` | P6-01..P6-06, P7-07, P8-06 |
| 8 Platform UI | `ui-v2` | P7-00..P7-13, P8-10 |
| 9 Real execution | `completion-gate`, `toolchain-compatibility` | P5-03, P8-03..P8-05 |
| 10 OpenSpec/agent governance | `agent-openspec-config` | P4-07..P4-09, P0-01 |
| 11 Quality plans/cases/oracles | `knowledge-retrieval`, `completion-gate` | P3-02, P4-01..P4-10, P5-04 |

## Task accounting

`tasks.md` contains the plan's 81 checkbox items, grouped Phase 0–8, with dependencies preserved. Count: 8 + 7 + 6 + 10 + 13 + 7 + 6 + 14 + 10 = 81.

## Validation

Run from the canonical repository: `openspec validate ai-test-platform-v2 --strict` and, if supported, `openspec show ai-test-platform-v2 --json`.
