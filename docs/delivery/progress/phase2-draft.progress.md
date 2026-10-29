# Phase 2 Draft Progress

- [DONE] skeleton + dependency table written
- [DONE] §0 boundary statement — complete, draft-only
- [DONE] §1 control-plane service boundaries — 7 logical services, Linux-authoritative, process form PENDING
- [DONE] §2 PostgreSQL logical domains — D1-D8, forward-only migration principles, no DDL
- [DONE] §3 API/event surface — 4 surfaces, auth, idempotency, error model at contract level
- [DONE] §4 Windows Node Agent boundary — fact-only, offline spool, STOP-first
- [DONE] §5 evidence storage — L1-L3 layering, integrity, on-demand log read, retention
- [DONE] §6 security/privacy/audit — control table, hard prohibitions
- [DONE] §7 deployment/backup/recovery — candidate topology, fixed recovery order, A-0 PENDING
- [DONE] §8 observability — signal classes, stale rule, integrity indicator
- [DONE] §9 explicit PENDING markers — P1, A-0, contract v1.1, A-1, P2-02
- [DONE] §10 dependency table — 6 rows with gates + reading rule
- [DONE] §11 risks and rollback — R1-R8 + global rollback principles
- [DONE] trim pass — 265→~250 lines, no content removed beyond compaction
