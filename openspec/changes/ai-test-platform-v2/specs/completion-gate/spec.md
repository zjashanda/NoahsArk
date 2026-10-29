## ADDED Requirements

### Requirement: Binary completion gate
The platform SHALL require an eligible, hashed report covering plan, real execution, artifacts, independent verdict, evidence, knowledge write-back and reproducibility before writing a terminal result.

#### Scenario: Dry run
- **WHEN** a run is dry-run, simulated, recorded or replayed
- **THEN** real-execution evidence fails and the run cannot complete as PASS.

#### Scenario: Missing evidence
- **WHEN** a required artifact or denominator is missing
- **THEN** the relevant gate is false and the terminal write is rejected.

### Requirement: Five-axis verdict and separated facts
The platform SHALL record execution, validity, business, evidence and verification as separate axes, and SHALL keep device occupancy, communication state, execution completion and final verdict as separate facts instead of one terminal status.

#### Scenario: Formal PASS
- **WHEN** a run is considered for formal PASS
- **THEN** it requires `execution_status=COMPLETED`, `validity_status=VALID`, `evidence_status=COMPLETE`, `business_verdict=PASS` and `verification_status=PASS`; a `RUNNING` or `NOT_STARTED` execution cannot be a formal PASS.

#### Scenario: Legacy terminal name
- **WHEN** a report or integration uses `PASS | FAIL | BLOCKED_HUMAN | CANCELLED | STOPPED | INFRA_ERROR`
- **THEN** the value is treated only as a historical compatibility alias and MUST NOT replace the five-axis facts.

### Requirement: Offline continuation and occupied-device retention
The platform SHALL let an already-started frozen run continue after communication, heartbeat or lease loss, and SHALL keep the device occupied without re-dispatch, replay or re-sampling.

#### Scenario: Node loses communication during a frozen run
- **WHEN** heartbeat or lease expires after a frozen run has started
- **THEN** the run continues locally, Linux marks communication `OFFLINE/STALE`, the device remains `OCCUPIED`, and no new job is dispatched or replayed.

#### Scenario: Reconnect after offline continuation
- **WHEN** a node reconnects with pending STOP messages
- **THEN** the platform processes STOP first, then uploads, dedupes and reconciles; stale epoch/lease messages cannot change the current run.

### Requirement: Device release and evidence verdict separation
The platform SHALL record execution end, device release, evidence status and final verdict independently, and SHALL NOT require GB-scale log archive or final verdict before release after local stop, safe cleanup and occupancy reconciliation.

#### Scenario: Missing cleanup receipt
- **WHEN** `cleanup_receipt` is missing
- **THEN** the platform cannot confirm device release and keeps the device `OCCUPIED`/`QUARANTINED`; the missing receipt alone does not make all evidence incomplete and does not force a business FAIL.

#### Scenario: Release before archive
- **WHEN** local execution has stopped, cleanup is safe and occupancy is reconciled
- **THEN** the device may be released without waiting for GB-scale log archive or the final verdict.
