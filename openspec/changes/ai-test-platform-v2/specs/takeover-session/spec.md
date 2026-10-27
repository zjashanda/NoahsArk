## ADDED Requirements

### Requirement: Fenced human takeover
The platform SHALL support observe and exclusive interactive takeover of a registered CLI executor session with history replay, safe-boundary pause, input, resume and audited lease fencing.

#### Scenario: Lease conflict
- **WHEN** a second interactive controller uses a stale epoch
- **THEN** the request is rejected without injecting input or duplicating effects.

#### Scenario: Device action in progress
- **WHEN** takeover is requested during a device action
- **THEN** the action completes before the session pauses at a safe turn boundary.
