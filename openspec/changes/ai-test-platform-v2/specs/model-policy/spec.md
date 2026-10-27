## ADDED Requirements

### Requirement: Runtime model policy
The platform SHALL resolve task, agent and global model policies in that order, validate required capabilities, record an immutable binding, and apply a valid switch without process restart.

#### Scenario: Invalid override
- **WHEN** an override names an unavailable model or lacks a required capability
- **THEN** the setting is not mutated and the request returns a validation error.

#### Scenario: Provider failure
- **WHEN** a transient provider failure occurs
- **THEN** the next eligible candidate is tried and the binding/audit records the attempt; permanent failures emit `MODEL_BLOCKED`.
