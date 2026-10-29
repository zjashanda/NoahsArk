# Phase 2 Landing Plan — Draft (bounded, non-binding)

> STATUS: DRAFT / PENDING. Not a freeze, not a commitment, no checkbox in the master plan.
> Scope constraints: no product code, no migrations, no OpenAPI files, no UI edits, no contract/schema edits.

## 0. Boundary Statement

| Item | Position |
|---|---|
| This document | Draft landing plan, bounded, non-binding. |
| Master-plan checkbox | **Not touched.** P2-01..P2-09 remain unchecked. |
| Freeze | **None.** Nothing here is frozen, approved, or implementation-authorized. |
| Code / DDL / OpenAPI / UI / contract / schema | **None produced or edited by this draft.** |
| Phase 2 completion | **Not claimed.** This is one input to P2-09 review, not a result. |
| Inputs read | `docs/delivery/phase2-input-map.md` (headings), `docs/contracts/README.md`, master plan §Phase 2 (items 20–28). |
| Search / web / secrets / SSH / commit | Not used or performed. |

Assumptions (recorded, not decided here): A-1 contract freeze is outstanding, so §3 field names are placeholders; A-0 environment facts are outstanding, so all §7 values are placeholders; P1 UI freeze is outstanding, so §9 keeps UI implementation open.

## 1. Control-Plane Service Boundaries and Responsibilities

Linux is the **sole authority** for all domain state and all final verdicts. Windows nodes produce facts only.

| # | Logical service | Responsibilities | Write authority | Explicit non-goals |
|---|---|---|---|---|
| S1 | Edge/API gateway & auth | TLS termination, session/token validation, rate limits, route to S2–S7, request audit envelope | Session/audit only | No domain writes |
| S2 | Task/Revision/Approval/Gate core | Task lifecycle, immutable revisions, freeze scope, one-valid-approval rule, G0–G7 gate ordering | Task, Revision, Approval, Gate | No execution, no verdict |
| S3 | Orchestration & lease | Run/Attempt creation, dispatch, lease + epoch, occupancy reconciliation, device pool, STOP fan-out | Run, Attempt, Lease, Device | No node-local actions; never treats `expires_at` as ownership loss |
| S4 | Node gateway | Outbound long-poll session endpoint for agents, envelope verify, heartbeat, receipt intake (dedupe/reconcile) | Node, Receipt persistence | Never signs a verdict, never writes `business_verdict` |
| S5 | Evidence & verdict | Manifest ingest, hash/index, integrity checks, cleanup-receipt reconciliation, five-axis verdict computation | Evidence index, final `business_verdict` / `verification_status` | Node input is never final; missing cleanup ≠ evidence incomplete |
| S6 | Report / knowledge / projection | Task card, report, knowledge projection, UI read models, SSE feeds | Projections only | Must not reverse-write Task/Run authority |
| S7 | Audit & config | Append-only audit log, threshold/config resolution (six layers), secrets reference resolution | Audit, config versions | No silent config mutation outside versioned path |

Boundary rules (binding shape, not yet frozen):
- Every state transition is server-side and audited; clients submit intents, never state.
- Cross-service writes go through the owning service; no shared-table writes.
- S3/S4 split keeps orchestration logic testable without network.

PENDING: process form (single modular monolith vs. split processes), queue technology, and deployment unit count — candidate only, decided in P2-01 after A-1.

## 2. PostgreSQL Logical Domains and Schema/Migration Strategy

PostgreSQL is the **only** authoritative database (no SQLite, no ORM-private or vendor-locked structures).

| Domain | Core objects (contract names) | Owner | Notes |
|---|---|---|---|
| D1 Identity & access | principal, role, session, token reference | S1 | No raw credentials stored |
| D2 Task definition | task, revision, approval, gate, case (with frozen `case_version`) | S2 | Revisions immutable once frozen |
| D3 Execution | run, attempt, lease, device, node | S3/S4 | Lease `expires_at` ≠ ownership expiry |
| D4 Evidence | manifest, evidence index entry, cleanup receipt projection | S5 | Binary payloads in object/file store, not PG |
| D5 Verdict | five-axis verdict record, verification status history | S5 | Linux-exclusive write |
| D6 Audit | append-only audit event | S7 | Partitioned, retention-bound |
| D7 Config | threshold/config version, precedence snapshot | S7 | Six-layer precedence resolved at read |
| D8 Projections | task card, report, knowledge read models | S6 | Rebuildable; never authoritative |

Schema/migration strategy (principles, **no DDL here**):
1. One logical database, one migration ledger; schema namespaces map 1:1 to D1–D8 ownership.
2. Forward-only, expand→migrate→contract; every migration has a tested rollback or a documented forward-fix.
3. Never rewrite frozen revisions or received evidence; history is interpreted by `schema_version`.
4. Idempotency keys are unique constraints at the owning domain (receipt dedupe, request dedupe).
5. Event publication uses a transactional outbox so DB commit and event emission cannot diverge.
6. High-volume Audit and Evidence index tables are partition candidates; partitioning key decided in P2-02.
7. Verdict computation reads a consistent snapshot; verdict records are append-only with supersede links, not updates.

PENDING: table/index/constraint detail, partition keys, retention windows, and migration tooling — P2-02, after A-1. Field names await contract v1.1 verification.

## 3. API / Event Surface, Auth, Idempotency, Error Model

### 3.1 Surfaces

| Surface | Consumers | Shape |
|---|---|---|
| Console/business API (`/v1/...`) | UI, operator, integrations | REST intents + read models; cursor pagination |
| Node protocol | Windows agent | **Outbound-only long-poll**; no inbound listener on nodes |
| Event stream | UI, projection, audit | Domain events from transactional outbox; SSE for UI, pull for consumers |
| Artifact transfer | Agent, evidence service | Pre-signed, scoped, short-TTL upload/download handles |

### 3.2 Auth (contract level)

- Nodes: mutual TLS identity + signed message envelope (nonce, epoch, replay window). Envelope verification precedes any state change.
- Users: session/token authn + role-based authz; authorization is server-side per intent, never UI-rendered permissions alone.
- Service-to-service: distinct identity per service, least privilege.
- All auth failures fail closed, are audited, and never reveal whether an object exists.

### 3.3 Idempotency

- All mutating intents accept a client idempotency key; same key + same payload → same result; same key + different payload → conflict.
- Receipts dedupe on `receipt_id` scoped to node identity/epoch (at-least-once transport, effectively-once persistence).
- Gate/approval transitions use expected-version optimistic concurrency; event consumers dedupe by event id, so replay is safe.

### 3.4 Error model

- Stable machine error code + human message + retryable flag + correlation id; no stack traces or internal identifiers leaked.
- Unknown/absent `schema_version` → fail closed (`NEEDS_REVIEW`-class rejection), never guessed as success.
- Unknown enum values map to `UNKNOWN` / `NEEDS_REVIEW`, never to PASS.
- STOP and safety paths use dedicated, non-retry-blocking codes.
- Pagination/listing errors never silently truncate; next-cursor is explicit.

PENDING: exact route list, error-code enum, header names, SSE event names, and payload field names — **contract v1.1 verification + P2-03**. No OpenAPI file is produced here.

## 4. Windows Node Agent Boundary

**Fixed boundary:** the Node Agent is a *fact producer*. It never computes or writes `business_verdict`, `verification_status`, or PASS/FAIL.

| Component (candidate) | Responsibility | Must not |
|---|---|---|
| Node service (Session 0) | Identity, outbound long-poll, heartbeat, lease/epoch tracking, STOP reception, spool manager | Open inbound ports; author verdicts |
| Interactive-session helper | Drive serial/audio/power/device and `lstest` in the interactive session | Run as a decision authority |
| Artifact verifier | Verify bundle signature/hash and freeze reference before execution | Repair or reinterpret the bundle |
| Executor | Run the frozen execution bundle; capture raw output | Alter case intent or thresholds |
| Receipt writer | Emit node-observed facts + evidence references + cleanup status | Write platform axes |
| Cleanup handler | Local stop, device release, resource cleanup, cleanup receipt | Declare completion when cleanup is unverified |

Offline behavior:
- Facts are written to the local spool **before** upload acknowledgement; bounded capacity with oldest-first policy explicit and audited.
- On reconnect: resume session, replay spool idempotently, reconcile leases/epoch; never double-execute a started job.
- **STOP-first:** STOP overrides queued work; in-flight job receives `on_lease_loss = continue_started_job` until local stop + cleanup complete; explicit revoke and safety incident use their own reasons.
- No silent retries that could duplicate side effects; every replay is receipt-id-idempotent.
- Spool encryption-at-rest and retention are required properties (values PENDING).

PENDING: service packaging (MSI/service account), session-launch mechanism, toolchain pinning, spool path/capacity, and exact receipt field names — **A-0 facts + contract v1.1**.

## 5. Evidence Storage, Index, Retention, On-Demand Log Read

### 5.1 Layering (fixed shape)

| Layer | Content | Authority |
|---|---|---|
| L1 Metadata/index (PostgreSQL) | manifest, `evidence_id`, hashes, sizes, provenance, retention class | S5 |
| L2 Payload store (file/object/NAS) | raw artifacts, logs, captures | Content-addressed |
| L3 Audit/projection | access log, report projection | S6/S7 |

Rules: payloads are content-addressed; DB stores pointers + digests, never blobs. Accepted evidence is never overwritten (correction = new object + supersede link). Hash verified on write and before verdict; mismatch → `NEEDS_REVIEW`, never PASS. **No "full upload before release" gating:** device release follows local stop + safe cleanup + occupancy reconciliation, and a missing cleanup receipt does **not** make evidence incomplete. On-demand log read is scoped, ranged, authorized through the control plane, never unbounded, and audited.

### 5.2 Retention

- Retention class per artifact kind (raw capture, normalized log, report, audit) — values PENDING.
- Audit records are append-only and outlive evidence payload expiry.
- Deletion applies only to non-evidence transient artifacts and expired payloads after index tombstone + audit entry.
- Legal hold / case freeze overrides expiry.

PENDING: capacity, retention windows, storage backend choice (local disk vs NAS vs object store), encryption and key custody — **A-0 + P2-06**.

## 6. Security, Privacy, Audit

| Area | Control (draft) | Status |
|---|---|---|
| Identity | Distinct identity per node/service/user; mTLS for nodes; rotation with overlap window | PENDING values |
| Authorization | Least privilege, server-side RBAC per intent; deny-by-default for unknown routes | Shape fixed |
| Secrets | External secret store/reference only; no secrets, keys, tokens, or SSH material in repo or logs | Fixed rule |
| Transport | TLS everywhere; signed envelopes for node messages; nonce + replay window | Shape fixed |
| Raw material | Device captures/logs may contain identifiers → redaction before projection; raw access is privileged + audited | PENDING rules |
| Privacy | Data minimization in read models; no PII in metrics labels or error messages | Shape fixed |
| Audit | Append-only, tamper-evident, includes actor/intent/object/result/correlation id; covers auth, config, evidence access, STOP, release | Shape fixed |
| Backup | Encrypted at rest and in transit; restore access audited | PENDING crypto |
| Break-glass | Time-boxed, dual-acknowledged, fully audited admin path | PENDING |

Hard prohibitions (carried forward, not negotiable in P2):
- Nodes cannot write verdicts; UI cannot write authority state; projections cannot reverse-write.
- No credential, token, session dump, or real device serial in documents, logs, or fixtures.
- Unknown schema/version or failed integrity → fail closed and flag for review.

PENDING: certificate authority choice, key custody, redaction field list, audit retention, and break-glass policy — **P2-06 with A-0**.

## 7. Deployment, Backup, Recovery Topology

```text
            ┌─────────────┐        ┌──────────────┐
 Operators ─┤ reverse     ├────────┤ Primary Linux│──┐
            │ proxy + TLS │        │ control plane│  │
            └─────────────┘        └──────┬───────┘  │
                                          │          │
                            ┌─────────────┴───┐  ┌───▼────────┐
                            │ PostgreSQL      │  │ Evidence   │
                            │ (authoritative) │  │ store/NAS  │
                            └────────┬────────┘  └────┬───────┘
                                     │ backups        │ replicas/snapshots
                            ┌────────▼────────────────▼───┐
                            │ Second server (standby)     │
                            │ + local backup volume       │
                            └─────────────────────────────┘
 Windows nodes ── outbound long-poll ──► primary (no inbound)
```

- Single primary control plane; standby is warm/restore-capable, not an active writer.
- Reverse proxy terminates TLS; internal traffic is also TLS.
- Windows nodes are **not** backed up as state; their config is reproducible from the control plane + installer.
- Backups: DB base + WAL/PITR, evidence store snapshots, config/secret-reference export; encrypted; off-host copy.
- **Recovery order (fixed):** (1) PostgreSQL restore + integrity check → (2) evidence store mount/verify → (3) control-plane services → (4) rebuild projections/read models → (5) re-enable node polling and dispatch. Nodes must not be dispatched before occupancy/lease reconciliation.
- Restore drills are scheduled and recorded as evidence.

PENDING: hostnames, capacity, backup cadence, retention of backups, RPO/RTO numeric targets — **all wait A-0**. Topology shape above is a candidate, not a freeze.

## 8. Observability Signals

| Signal class | Examples | Purpose | Numeric threshold |
|---|---|---|---|
| Domain events | task/revision frozen, gate decision, run dispatched, lease acquired, STOP issued, receipt accepted, evidence indexed, verdict written | Reconstruct what happened | n/a |
| Logs | structured JSON with correlation id, actor, object id; no secrets/PII | Debug + audit trail | n/a |
| Metrics | queue depth, dispatch latency, heartbeat age, lease skew, spool backlog, upload failure rate, evidence hash mismatch count, verdict latency | Health + SLO | **PENDING (P0-08 thresholds)** |
| Traces | request → service → DB → outbox → consumer; long-poll session span | Latency attribution | PENDING |
| Audit stream | auth failures, config changes, evidence reads, admin actions | Security review | n/a |

- **Stale judgment** uses heartbeat age + lease state + node session presence; `expires_at` alone must never mark a device free or a run failed.
- **Evidence integrity indicator**: accepted vs. hash-mismatch vs. missing-manifest counts, surfaced per run and globally.
- **Task-card projection** must label data freshness explicitly (live / lagging / stale) rather than infer.
- Alerts are tiered (page / ticket / dashboard only); every alert names the owning service and a runbook anchor.

PENDING: metric names, bucket boundaries, alert thresholds, dashboard layout, retention of metrics/traces — **P2-08 + P0-08 values**.

## 9. Explicit PENDING Markers

| Marker | What stays open | Waits on | What can proceed meanwhile |
|---|---|---|---|
| **PENDING(P1)** | UI implementation architecture: framework, routing, state, component library, design tokens, i18n, permission rendering, error boundaries | **Phase 1 UI freeze** | UI↔API mapping review, display-boundary rules, read-model shape |
| **PENDING(A-0)** | Environment values: hostnames, capacity, storage backend, TLS/CA, node accounts, RPO/RTO numbers, spool path/size, retention windows | **A-0 environment facts** | Topology shape, recovery order, control design |
| **PENDING(CONTRACT-v1.1)** | Exact field/route/event/error-code names, enum values, header names, schema `$id`s | **Contract v1.1 verification** | Domain modeling, invariant tests, service boundaries |
| PENDING(A-1) | Task/revision/approval/gate freeze semantics edge cases | Contract freeze | Logic design, invariant list |
| PENDING(P2-02) | Table/index/partition/retention DDL detail | A-1 | Domain split, migration principles |

Rule: no section may silently consume a PENDING value. If an implementation task needs one, it stops and escalates rather than inventing a value.

## 10. Dependency Table

| # | Dependency | Required before | Blocks | Gate | Status |
|---|---|---|---|---|---|
| 1 | Control-plane service split (S1–S7) + process form | P2-01 review | API surface, data ownership, deployment units | A-1 scope | PENDING |
| 2 | PostgreSQL logical domains D1–D8 + migration strategy | P2-02 start | Schema detail, retention jobs, backup scope | A-1 | PENDING |
| 3 | Contract v1.1 field verification | Any field-level API/DB/UI work | Routes, errors, events, schemas | Contract v1.1 | PENDING |
| 4 | Windows Node Agent spool/STOP + packaging | P2-04 | Offline evidence path, STOP semantics | A-0 + contract v1.1 | PENDING |
| 5 | Evidence store backend + retention classes | P2-06/P2-07 | Capacity plan, backup, audit retention | A-0 + P2-06 | PENDING |
| 6 | Deployment/backup topology values (hosts, RPO/RTO) | P2-07 | Release gate, restore drill | A-0 | PENDING |

Reading rule: rows 1–2 can be drafted in parallel; rows 3–6 are hard gates for any *implementation* task, not for further drafting.

## 11. Risks and Rollback

| ID | Risk | Impact | Mitigation | Rollback / trigger |
|---|---|---|---|---|
| R1 | Contract drift between API/DB/UI/agent | Silent semantic break | Contract v1.1 verification gate; `schema_version` fail-closed; compatibility rules | Reject deploying consumer ahead of contract; revert consumer, keep 1.x reader |
| R2 | Write-authority violation (node/UI writes verdict) | Trust collapse | Single-writer enforcement at DB/service; tests assert node cannot write verdict | Disable offending path; invalidate affected verdicts → `NEEDS_REVIEW` |
| R3 | Lease/occupancy split-brain after reconnect | Duplicate execution on device | Epoch + receipt dedupe + reconcile-before-dispatch | STOP node, reconcile, re-run only after clean release |
| R4 | Evidence payload loss / hash mismatch | Unverifiable run | Content hash + replication + integrity check before verdict | Mark run `NEEDS_REVIEW`; restore from replica/NAS snapshot |
| R5 | Spool overflow on offline node | Lost facts | Bounded spool, oldest-first policy, alerting on backlog | Reject new jobs early; manual export before cleanup |
| R6 | Migration failure | Downtime / partial schema | Expand→contract, backup before migrate, tested forward-fix | Stop rollout; forward-fix; restore only from verified backup |
| R7 | Single primary control plane outage | Platform unavailable | Warm standby + documented restore order | Fail to standby; rebuild projections |
| R8 | UI assumes authority it does not have | Misleading PASS/FAIL | Display-boundary rules; projection freshness labels | Revert UI release; projections rebuildable |

Global rollback principles:
- Roll back **deployments**, never history: frozen revisions and accepted evidence are immutable.
- Migrations are forward-fix first; destructive rollback only with verified backup and explicit approval.
- Projections/read models are disposable and rebuildable.
- Any rollback touching verdicts requires an audit entry and explicit review; triggers must be observable (§8), not incident-time judgement calls.

PENDING: concrete SLO-based triggers, backup restore time evidence, and approval authority for rollback — **A-0 + P2-09**.
