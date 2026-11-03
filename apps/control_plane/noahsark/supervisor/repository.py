"""Persistence boundary for the independent supervisor worker.

A claim is represented durably by the existing ``supervisor_sessions`` fields:
the row state plus ``updated_at`` act as the lease heartbeat, and
``result_updated_at`` stores the dispatch timestamp until it is replaced by the
terminal result timestamp.  No model, migration or API field is added.

Every state write is a compare-and-set on the previous state, so two workers
racing on the same row cannot both perform a transition.  Claim selection uses
``FOR UPDATE SKIP LOCKED`` so concurrent workers never block each other.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import SupervisorSession, Task
from .state import ACTIVE_STATES, LEASABLE_STATES, WORK_STATES, SupervisorState

CLAIMABLE_STATES = (*ACTIVE_STATES,)


@dataclass(frozen=True, slots=True)
class ClaimedSession:
    """A durable supervisor row plus the task fields needed to build a prompt."""

    supervisor_session_id: uuid.UUID
    display_id: str
    task_id: uuid.UUID
    revision_id: uuid.UUID
    state: str
    remote_session_id: str | None
    prompt_digest: str
    prompt_bytes: int
    result_summary: str | None
    error_code: str | None
    dispatch_at: datetime | None
    created_at: datetime
    updated_at: datetime
    task_display_id: str
    task_title: str
    task_objective: str
    task_execution_context: dict[str, Any] = field(default_factory=dict)
    lease_expires_at: datetime | None = None


class SupervisorRepository(Protocol):
    """The narrow persistence interface the service depends on."""

    async def claim_next(
        self, *, worker_id: str, lease_seconds: float, now: datetime
    ) -> ClaimedSession | None: ...

    async def load(self, session_id: uuid.UUID) -> ClaimedSession | None: ...

    async def bind_remote(
        self,
        session_id: uuid.UUID,
        *,
        remote_session_id: str,
        now: datetime,
    ) -> bool: ...

    async def mark_dispatched(self, session_id: uuid.UUID, *, now: datetime) -> bool: ...

    async def mark_running(self, session_id: uuid.UUID, *, now: datetime) -> bool: ...

    async def record_uncertain(
        self, session_id: uuid.UUID, *, error_code: str, now: datetime
    ) -> bool: ...

    async def touch(self, session_id: uuid.UUID, *, now: datetime) -> bool: ...

    async def complete(
        self,
        session_id: uuid.UUID,
        *,
        result_summary: str,
        now: datetime,
    ) -> bool: ...

    async def fail(
        self, session_id: uuid.UUID, *, error_code: str, now: datetime
    ) -> bool: ...

    async def request_stop(self, session_id: uuid.UUID, *, now: datetime) -> bool: ...

    async def mark_stopped(
        self,
        session_id: uuid.UUID,
        *,
        error_code: str | None,
        now: datetime,
    ) -> bool: ...


def _snapshot(row: SupervisorSession, task: Task) -> ClaimedSession:
    return ClaimedSession(
        supervisor_session_id=row.supervisor_session_id,
        display_id=row.display_id,
        task_id=row.task_id,
        revision_id=row.revision_id,
        state=row.state,
        remote_session_id=row.remote_session_id,
        prompt_digest=row.prompt_digest,
        prompt_bytes=row.prompt_bytes,
        result_summary=row.result_summary,
        error_code=row.error_code,
        dispatch_at=row.result_updated_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        task_display_id=task.display_id,
        task_title=task.title,
        task_objective=task.objective,
        task_execution_context=dict(task.execution_context or {}),
    )


def _claimable(now: datetime, lease_seconds: float) -> Any:
    cutoff = now - timedelta(seconds=lease_seconds)
    return (
        SupervisorSession.state.in_(CLAIMABLE_STATES)
        & (

                SupervisorSession.state.in_(
                    (
                        SupervisorState.PENDING,
                        SupervisorState.READY,
                        SupervisorState.STOP_REQUESTED,
                    )
                )
                | (SupervisorSession.updated_at <= cutoff)
        )
    )


class SqlSupervisorRepository:
    """PostgreSQL implementation; one short transaction per state write."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = session_factory

    async def claim_next(
        self, *, worker_id: str, lease_seconds: float, now: datetime
    ) -> ClaimedSession | None:
        del worker_id  # The durable lease is state + updated_at, not a worker id.
        priority = case(
            (SupervisorSession.state == "STOP_REQUESTED", 0),
            (SupervisorSession.state == "PENDING", 1),
            else_=2,
        )
        async with self._sessions() as session:
            result = await session.execute(
                select(SupervisorSession, Task)
                .join(Task, Task.task_id == SupervisorSession.task_id)
                .where(_claimable(now, lease_seconds))
                .order_by(priority, SupervisorSession.created_at)
                .limit(1)
                .with_for_update(skip_locked=True, of=SupervisorSession)
            )
            found = result.one_or_none()
            if found is None:
                return None
            row, task = found
            if row.state == "PENDING":
                row.state = "BINDING"
            row.updated_at = now
            await session.commit()
            return replace(
                _snapshot(row, task),
                lease_expires_at=now + timedelta(seconds=lease_seconds),
            )

    async def load(self, session_id: uuid.UUID) -> ClaimedSession | None:
        async with self._sessions() as session:
            result = await session.execute(
                select(SupervisorSession, Task)
                .join(Task, Task.task_id == SupervisorSession.task_id)
                .where(SupervisorSession.supervisor_session_id == session_id)
            )
            found = result.one_or_none()
            if found is None:
                return None
            row, task = found
            return _snapshot(row, task)

    async def _transition(
        self,
        session_id: uuid.UUID,
        *,
        expected: Sequence[str],
        now: datetime,
        values: dict[str, object],
    ) -> bool:
        async with self._sessions() as session:
            result = await session.execute(
                update(SupervisorSession)
                .where(
                    SupervisorSession.supervisor_session_id == session_id,
                    SupervisorSession.state.in_(expected),
                )
                .values(updated_at=now, **values)
            )
            await session.commit()
            return getattr(result, "rowcount", 0) == 1

    async def bind_remote(
        self, session_id: uuid.UUID, *, remote_session_id: str, now: datetime
    ) -> bool:
        return await self._transition(
            session_id,
            expected=("BINDING",),
            now=now,
            values={"state": "READY", "remote_session_id": remote_session_id},
        )

    async def mark_dispatched(self, session_id: uuid.UUID, *, now: datetime) -> bool:
        return await self._transition(
            session_id,
            expected=("READY",),
            now=now,
            values={
                "state": "DISPATCHED",
                "error_code": None,
                "result_updated_at": now,
            },
        )

    async def mark_running(self, session_id: uuid.UUID, *, now: datetime) -> bool:
        return await self._transition(
            session_id,
            expected=("DISPATCHED",),
            now=now,
            values={"state": "RUNNING"},
        )

    async def record_uncertain(
        self, session_id: uuid.UUID, *, error_code: str, now: datetime
    ) -> bool:
        return await self._transition(
            session_id,
            expected=WORK_STATES,
            now=now,
            values={"error_code": error_code},
        )

    async def touch(self, session_id: uuid.UUID, *, now: datetime) -> bool:
        return await self._transition(
            session_id,
            expected=WORK_STATES,
            now=now,
            values={},
        )

    async def complete(
        self, session_id: uuid.UUID, *, result_summary: str, now: datetime
    ) -> bool:
        return await self._transition(
            session_id,
            expected=WORK_STATES,
            now=now,
            values={
                "state": "COMPLETED",
                "result_summary": result_summary,
                "error_code": None,
                "result_updated_at": now,
            },
        )

    async def fail(
        self, session_id: uuid.UUID, *, error_code: str, now: datetime
    ) -> bool:
        return await self._transition(
            session_id,
            expected=ACTIVE_STATES,
            now=now,
            values={
                "state": "FAILED",
                "error_code": error_code,
                "result_updated_at": now,
            },
        )

    async def request_stop(self, session_id: uuid.UUID, *, now: datetime) -> bool:
        return await self._transition(
            session_id,
            expected=ACTIVE_STATES,
            now=now,
            values={"state": "STOP_REQUESTED"},
        )

    async def mark_stopped(
        self,
        session_id: uuid.UUID,
        *,
        error_code: str | None,
        now: datetime,
    ) -> bool:
        return await self._transition(
            session_id,
            expected=("STOP_REQUESTED",),
            now=now,
            values={
                "state": "STOPPED",
                "error_code": error_code,
                "result_updated_at": now,
            },
        )


__all__ = [
    "ACTIVE_STATES",
    "LEASABLE_STATES",
    "WORK_STATES",
    "ClaimedSession",
    "SqlSupervisorRepository",
    "SupervisorRepository",
]
