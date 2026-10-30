"""Import every model so ``Base.metadata`` is complete for Alembic."""

from .audit import AuditEvent, IdempotencyKey
from .base import Base
from .device import Device, Lease, Node
from .evidence import (
    EvidenceItem,
    EvidenceManifest,
    KnowledgeCandidate,
    KnowledgeItem,
    Report,
    Verdict,
)
from .identity import Agent, Review, Role, SessionToken, Setting, User
from .intake import IntakeDraft
from .run import Attempt, Run
from .task import Approval, Case, Gate, Task, TaskRevision
from .write_request import WriteRequest

__all__ = [
    "Agent",
    "Approval",
    "Attempt",
    "AuditEvent",
    "Base",
    "Case",
    "Device",
    "EvidenceItem",
    "EvidenceManifest",
    "Gate",
    "IdempotencyKey",
    "IntakeDraft",
    "KnowledgeCandidate",
    "KnowledgeItem",
    "Lease",
    "Node",
    "Report",
    "Review",
    "Role",
    "Run",
    "SessionToken",
    "Setting",
    "Task",
    "TaskRevision",
    "User",
    "Verdict",
    "WriteRequest",
]
