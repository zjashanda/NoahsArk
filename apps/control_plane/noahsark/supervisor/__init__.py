"""Independent OpenCode supervisor worker.

The worker is a separate process from the HTTP API.  It consumes persisted
``supervisor_sessions`` rows, drives them through the verified OpenCode 1.19.4
session endpoints, and writes only the supervisor binding/result fields.  Task
business status, verdicts and evidence are never touched here.
"""

from __future__ import annotations

from .config import SupervisorSettings
from .repository import ClaimedSession, SqlSupervisorRepository, SupervisorRepository

__all__ = [
    "ClaimedSession",
    "SqlSupervisorRepository",
    "SupervisorRepository",
    "SupervisorSettings",
]
