## ADDED Requirements

### Requirement: Binary completion gate
The platform SHALL require an eligible, hashed report covering plan, real execution, artifacts, independent verdict, evidence, knowledge write-back and reproducibility before writing a terminal result.

#### Scenario: Dry run
- **WHEN** a run is dry-run, simulated, recorded or replayed
- **THEN** real-execution evidence fails and the run cannot complete as PASS.

#### Scenario: Missing evidence
- **WHEN** a required artifact or denominator is missing
- **THEN** the relevant gate is false and the terminal write is rejected.
