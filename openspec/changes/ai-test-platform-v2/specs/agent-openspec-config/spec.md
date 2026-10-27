## ADDED Requirements

### Requirement: Generated agent governance
The platform SHALL use a single agent registry to render OpenSpec context, commands, tools, skills, model policy and write scope, and SHALL reject drift or protected writes without review receipts.

#### Scenario: Registry drift
- **WHEN** rendered agent files differ from the registry
- **THEN** validation fails closed and generated configuration is not accepted.

#### Scenario: Protected write
- **WHEN** an agent writes an OpenSpec or protected project path without an eligible review receipt
- **THEN** the command facade rejects the write and audits the denial.
