## ADDED Requirements

### Requirement: Locked toolchain compatibility
The platform SHALL maintain one hashed lock for opencode, OMO, plugins, skills, Python, SQLite, lstest and platform commit, and SHALL run versioned smoke suites when drift or upgrade occurs.

#### Scenario: Drift detected
- **WHEN** an installed component differs from the lock
- **THEN** compatibility status is recorded and real execution remains blocked until the required smoke tier is acknowledged.
