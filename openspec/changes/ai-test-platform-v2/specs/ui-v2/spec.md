## ADDED Requirements

### Requirement: Platform console UI
The platform SHALL provide a coherent UI for overview, tasks/detail, knowledge, nodes/devices, models, versions, push, takeover and progress using read-only projections, audited command actions, SSE and polling fallback.

#### Scenario: Live task detail
- **WHEN** an authorized user opens a task
- **THEN** the UI displays stage progress, gates, verdict, evidence, delivery and takeover state without secrets.

#### Scenario: SSE unavailable
- **WHEN** the event stream disconnects
- **THEN** the UI falls back to bounded polling and deduplicates refreshed events.

#### Scenario: Five-axis and separated facts
- **WHEN** a task detail is rendered
- **THEN** execution, validity, business, evidence, verification, device occupancy and communication are shown as separate facts, not one all-purpose terminal badge.

#### Scenario: Offline run with occupied device
- **WHEN** a node is offline but its frozen run is still executing
- **THEN** the UI shows communication offline and device occupied, and MUST NOT show the device as free, the task as stopped, or the task as completed.
