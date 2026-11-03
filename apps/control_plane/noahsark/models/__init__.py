"""Import every model so ``Base.metadata`` is complete for Alembic."""

from .artifact import TestCampaignArtifact
from .audit import AuditEvent, IdempotencyKey
from .base import Base
from .command import NodeCommand
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
from .resource_lease import ResourceLease
from .run import Attempt, Run
from .supervisor import SupervisorSession
from .task import Approval, Case, Gate, Task, TaskRevision
from .test_campaign import TestCampaign
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
    "NodeCommand",
    "Report",
    "ResourceLease",
    "Review",
    "Role",
    "Run",
    "SessionToken",
    "Setting",
    "SupervisorSession",
    "Task",
    "TaskRevision",
    "TestCampaign",
    "TestCampaignArtifact",
    "User",
    "Verdict",
    "WriteRequest",
]
