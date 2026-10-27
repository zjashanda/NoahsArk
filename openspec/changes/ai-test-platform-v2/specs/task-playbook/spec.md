## ADDED Requirements

### Requirement: Task playbook persistence
The platform SHALL persist an idempotent playbook after every terminal task, including requirement, plan/case/oracle hashes, prerequisites, evidence requirements, outcome, failure modes and reuse tags.

#### Scenario: Terminal archive
- **WHEN** archive runs for a terminal task
- **THEN** a playbook and failure candidates are written, or an actor-recorded `no_reusable_knowledge` reason is stored.
