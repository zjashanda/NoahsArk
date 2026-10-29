## ADDED Requirements

### Requirement: Event log and active push
The platform SHALL append redacted, monotonic, idempotent events and deliver them at least once to SSE, terminal, file and HMAC webhook subscribers without making task state depend on delivery success.

#### Scenario: Replay
- **WHEN** a subscriber reconnects with `Last-Event-ID`
- **THEN** the event stream replays subsequent events and deduplicates by event/idempotency key.

#### Scenario: Completion notification
- **WHEN** all completion gates and archive succeed
- **THEN** exactly one `task.completed` event is emitted; blocked or stopped tasks never emit it.

#### Scenario: Communication loss during a frozen run
- **WHEN** a node heartbeat or lease expires while a frozen run is executing
- **THEN** no `task.completed`, `task.failed` or device-release event is emitted from the loss alone; communication state becomes offline/stale and the device stays occupied.
