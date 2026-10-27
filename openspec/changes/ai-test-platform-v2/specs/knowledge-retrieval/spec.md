## ADDED Requirements

### Requirement: Evidence-scoped retrieval
The platform SHALL retrieve similar tasks, methodology, failure cases, project facts and script fixes using deterministic ranking, scope/status filters and citations, and SHALL inject results as untrusted evidence.

#### Scenario: Intake with history
- **WHEN** a task is created
- **THEN** a versioned retrieval packet is stored with reusable blocks, warnings, applicability and citations; no-hit is explicit.

#### Scenario: Stale knowledge
- **WHEN** a hit is stale, disputed or lacks provenance
- **THEN** its status and warning are visible and it cannot silently outrank approved evidence.
