## ADDED Requirements

### Requirement: Event log and active push
The platform SHALL append redacted, monotonic, idempotent events and deliver them at least once to SSE, terminal, file and HMAC webhook subscribers without making task state depend on delivery success.

#### Scenario: Replay
- **WHEN** a subscriber reconnects with `Last-Event-ID`
- **THEN** the event stream replays subsequent events and deduplicates by event/idempotency key.

#### Scenario: Completion notification
- **WHEN** all completion gates and archive succeed
- **THEN** exactly one `task.completed` event is emitted; blocked or stopped tasks never emit it.
