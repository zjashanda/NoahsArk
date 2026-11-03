"""Database-free supervisor task -> session -> result flow tests.

The service is exercised against an in-memory implementation of the very
:class:`SupervisorRepository` protocol that :class:`SqlSupervisorRepository`
satisfies, plus the deterministic fake provider.  Nothing here opens a database
connection: the tests prove the state machine, the completion gates and the
model pinning without touching PostgreSQL.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta

from noahsark.integrations.opencode.errors import OpenCodeTransportError
from noahsark.integrations.opencode.fake import FakeOpenCodeProvider, FakeTurn
from noahsark.integrations.opencode.prompt import (
    TaskPromptInput,
    build_task_prompt,
    format_execution_context,
)
from noahsark.integrations.opencode.protocol import (
    ModelSelection,
    OpenCodeSession,
)
from noahsark.services.supervisor import (
    ProcessResult,
    SupervisorService,
    WorkerOutcome,
)
from noahsark.supervisor.config import SupervisorSettings
from noahsark.supervisor.repository import (
    ACTIVE_STATES,
    WORK_STATES,
    ClaimedSession,
    SupervisorRepository,
)
from noahsark.supervisor.state import SupervisorState, WorkerErrorCode

POOR_MODEL = ModelSelection(
    provider_id="listenai",
    model_id="deepseek-v4.1-flash-expires-on-0910",
)

_SESSION_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
_TASK_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a2")
_REVISION_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a3")
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

_CLAIM_PRIORITY = {
    SupervisorState.STOP_REQUESTED: 0,
    SupervisorState.PENDING: 1,
}
_ALWAYS_CLAIMABLE = (
    SupervisorState.PENDING,
    SupervisorState.READY,
    SupervisorState.STOP_REQUESTED,
)


@dataclass(slots=True)
class InMemorySupervisorRepository:
    """The narrow repository protocol backed by a dict, no SQLAlchemy session.

    Transitions intentionally mirror :class:`SqlSupervisorRepository`: every
    write is a compare-and-set on the expected previous state and returns
    ``False`` instead of overwriting a row that already moved on.
    """

    rows: dict[uuid.UUID, ClaimedSession] = field(default_factory=dict)

    def add(self, row: ClaimedSession) -> None:
        self.rows[row.supervisor_session_id] = row

    async def claim_next(
        self, *, worker_id: str, lease_seconds: float, now: datetime
    ) -> ClaimedSession | None:
        del worker_id
        cutoff = now - timedelta(seconds=lease_seconds)
        claimable = [
            row
            for row in self.rows.values()
            if row.state in ACTIVE_STATES
            and (
                row.state in _ALWAYS_CLAIMABLE or row.updated_at <= cutoff
            )
        ]
        if not claimable:
            return None
        row = min(
            claimable,
            key=lambda item: (
                _CLAIM_PRIORITY.get(item.state, 2),
                item.created_at,
            ),
        )
        promoted = row.state == SupervisorState.PENDING
        claimed = replace(
            row,
            state=SupervisorState.BINDING if promoted else row.state,
            updated_at=now,
        )
        self.rows[claimed.supervisor_session_id] = claimed
        return replace(
            claimed,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
        )

    async def load(self, session_id: uuid.UUID) -> ClaimedSession | None:
        return self.rows.get(session_id)

    async def bind_remote(
        self,
        session_id: uuid.UUID,
        *,
        remote_session_id: str,
        now: datetime,
    ) -> bool:
        return self._transition(
            session_id,
            expected=(SupervisorState.BINDING,),
            now=now,
            values={"state": "READY", "remote_session_id": remote_session_id},
        )

    async def mark_dispatched(self, session_id: uuid.UUID, *, now: datetime) -> bool:
        return self._transition(
            session_id,
            expected=(SupervisorState.READY,),
            now=now,
            values={
                "state": "DISPATCHED",
                "error_code": None,
                "dispatch_at": now,
            },
        )

    async def mark_running(self, session_id: uuid.UUID, *, now: datetime) -> bool:
        return self._transition(
            session_id,
            expected=(SupervisorState.DISPATCHED,),
            now=now,
            values={"state": "RUNNING"},
        )

    async def record_uncertain(
        self, session_id: uuid.UUID, *, error_code: str, now: datetime
    ) -> bool:
        return self._transition(
            session_id,
            expected=WORK_STATES,
            now=now,
            values={"error_code": error_code},
        )

    async def touch(self, session_id: uuid.UUID, *, now: datetime) -> bool:
        return self._transition(
            session_id, expected=WORK_STATES, now=now, values={}
        )

    async def complete(
        self,
        session_id: uuid.UUID,
        *,
        result_summary: str,
        now: datetime,
    ) -> bool:
        return self._transition(
            session_id,
            expected=WORK_STATES,
            now=now,
            values={
                "state": "COMPLETED",
                "result_summary": result_summary,
                "error_code": None,
                "dispatch_at": now,
            },
        )

    async def fail(
        self, session_id: uuid.UUID, *, error_code: str, now: datetime
    ) -> bool:
        return self._transition(
            session_id,
            expected=ACTIVE_STATES,
            now=now,
            values={
                "state": "FAILED",
                "error_code": error_code,
                "dispatch_at": now,
            },
        )

    async def request_stop(self, session_id: uuid.UUID, *, now: datetime) -> bool:
        return self._transition(
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
        return self._transition(
            session_id,
            expected=(SupervisorState.STOP_REQUESTED,),
            now=now,
            values={
                "state": "STOPPED",
                "error_code": error_code,
                "dispatch_at": now,
            },
        )

    def _transition(
        self,
        session_id: uuid.UUID,
        *,
        expected: Sequence[str],
        now: datetime,
        values: dict[str, object],
    ) -> bool:
        row = self.rows.get(session_id)
        if row is None or row.state not in expected:
            return False
        self.rows[session_id] = replace(row, updated_at=now, **values)
        return True


class UnreachableRuntimeProvider(FakeOpenCodeProvider):
    """A fake whose runtime is down before a remote session can ever exist."""

    async def create_session(
        self, *, title: str, model: ModelSelection | None = None
    ) -> OpenCodeSession:
        raise OpenCodeTransportError("OpenCode runtime is unreachable")


def _pending_session() -> ClaimedSession:
    return ClaimedSession(
        supervisor_session_id=_SESSION_ID,
        display_id="sup-flow-0001",
        task_id=_TASK_ID,
        revision_id=_REVISION_ID,
        state="PENDING",
        remote_session_id=None,
        prompt_digest="sha256:0000000000000000000000000000000000000000000000000000000000000000",
        prompt_bytes=64,
        result_summary=None,
        error_code=None,
        dispatch_at=None,
        created_at=_NOW,
        updated_at=_NOW,
        task_display_id="tsk-flow-0001",
        task_title="Supervisor task flow",
        task_objective="Return PONG from the deterministic fake runtime.",
    )


def _repo_with_pending() -> InMemorySupervisorRepository:
    repository: SupervisorRepository = InMemorySupervisorRepository()
    assert isinstance(repository, InMemorySupervisorRepository)
    repository.add(_pending_session())
    return repository


def _settings(**overrides: object) -> SupervisorSettings:
    base: dict[str, object] = {
        "worker_id": "test-worker",
        "poll_interval_seconds": 0.01,
        "idle_sleep_seconds": 0.01,
        "completion_timeout_seconds": 60.0,
    }
    base.update(overrides)
    return SupervisorSettings(_env_file=None, **base)  # type: ignore[arg-type]


async def _no_sleep(_seconds: float) -> None:
    return None


def _service(
    provider: FakeOpenCodeProvider,
    repository: InMemorySupervisorRepository,
    settings: SupervisorSettings,
) -> SupervisorService:
    return SupervisorService(
        provider,
        repository,
        settings,
        clock=lambda: _NOW,
        sleep=_no_sleep,
    )


def _expected_prompt():
    pending = _pending_session()
    return build_task_prompt(
        TaskPromptInput(
            task_id=pending.task_display_id,
            title=pending.task_title,
            instructions=pending.task_objective,
        ),
        max_bytes=_settings().max_prompt_bytes,
    )


def test_pending_task_completes_with_pinned_model_and_sanitized_result() -> None:
    assistant_text = (
        "PONG\napi_key=sk-live-abcdef0123456789\n/home/bszheng/secret.txt"
    )

    async def scenario() -> tuple[
        ProcessResult, ClaimedSession | None, FakeOpenCodeProvider
    ]:
        repository = _repo_with_pending()
        provider = FakeOpenCodeProvider(turns=(FakeTurn(text=assistant_text),))
        service = _service(provider, repository, _settings())
        result = await service.run_once()
        return result, await repository.load(_SESSION_ID), provider

    result, row, provider = asyncio.run(scenario())

    assert result.outcome is WorkerOutcome.COMPLETED
    assert result.state == SupervisorState.COMPLETED
    assert result.error_code is None
    assert row is not None
    assert row.state == SupervisorState.COMPLETED
    assert row.error_code is None
    assert row.result_summary is not None
    assert row.result_summary.startswith("PONG")
    assert "sk-live-abcdef0123456789" not in row.result_summary
    assert "/home/bszheng/secret.txt" not in row.result_summary
    assert "[REDACTED_SECRET]" in row.result_summary
    assert "[REDACTED_PATH]" in row.result_summary

    # The exact poor model reached both provider operations, in order.
    assert provider.model_calls() == (
        ("create", POOR_MODEL),
        ("prompt", POOR_MODEL),
    )
    assert row.remote_session_id is not None
    assert provider.prompt_digests(row.remote_session_id) == (
        _expected_prompt().digest,
    )


def test_dispatch_prompt_includes_selected_execution_resources() -> None:
    pending = _pending_session()
    context = {
        "nodes": [
            {
                "node_id": "00000000-0000-0000-0000-0000000000b1",
                "display_id": "win009",
                "hostname": "WIN009",
                "communication_state": "ONLINE",
            }
        ],
        "devices": [
            {
                "device_id": "00000000-0000-0000-0000-0000000000c1",
                "display_id": "usb",
                "node_id": "00000000-0000-0000-0000-0000000000b1",
                "identity": {"kind": "usb-board"},
                "endpoints": [
                    {"kind": "serial", "port": "COM3", "role": "A"},
                    {"kind": "serial", "port": "COM7", "role": "B"},
                ],
                "capabilities": ["serial"],
            }
        ],
    }

    async def scenario() -> tuple[
        ProcessResult, ClaimedSession | None, FakeOpenCodeProvider
    ]:
        repository = InMemorySupervisorRepository()
        repository.add(replace(pending, task_execution_context=context))
        provider = FakeOpenCodeProvider(turns=(FakeTurn(text="PONG"),))
        service = _service(provider, repository, _settings())
        result = await service.run_once()
        return result, await repository.load(_SESSION_ID), provider

    result, row, provider = asyncio.run(scenario())

    assert result.outcome is WorkerOutcome.COMPLETED
    assert row is not None
    assert row.remote_session_id is not None
    expected = build_task_prompt(
        TaskPromptInput(
            task_id=pending.task_display_id,
            title=pending.task_title,
            instructions=pending.task_objective,
            resources=format_execution_context(context),
        ),
        max_bytes=_settings().max_prompt_bytes,
    )
    assert provider.prompt_digests(row.remote_session_id) == (expected.digest,)
    assert "## Execution resources" in expected.text
    assert "- win009 (WIN009, ONLINE)" in expected.text
    assert "- usb [win009]: serial A=COM3, B=COM7" in expected.text


def test_unavailable_runtime_fails_without_fabricating_completion() -> None:
    async def scenario() -> tuple[
        ProcessResult, ClaimedSession | None, FakeOpenCodeProvider
    ]:
        repository = _repo_with_pending()
        provider = UnreachableRuntimeProvider(turns=(FakeTurn(text="never"),))
        service = _service(provider, repository, _settings())
        result = await service.run_once()
        return result, await repository.load(_SESSION_ID), provider

    result, row, provider = asyncio.run(scenario())

    assert result.outcome is WorkerOutcome.FAILED
    assert result.state == SupervisorState.FAILED
    assert result.error_code == WorkerErrorCode.PROVIDER_UNREACHABLE
    assert row is not None
    assert row.state == SupervisorState.FAILED
    assert row.error_code == WorkerErrorCode.PROVIDER_UNREACHABLE
    assert row.result_summary is None
    assert row.remote_session_id is None
    assert provider.model_calls() == ()


def test_assistant_error_fails_without_completion() -> None:
    async def scenario() -> tuple[
        ProcessResult, ClaimedSession | None, FakeOpenCodeProvider
    ]:
        repository = _repo_with_pending()
        provider = FakeOpenCodeProvider(
            turns=(
                FakeTurn(text="failed output", error_name="MessageAbortedError"),
            )
        )
        service = _service(provider, repository, _settings())
        result = await service.run_once()
        return result, await repository.load(_SESSION_ID), provider

    result, row, provider = asyncio.run(scenario())

    assert result.outcome is WorkerOutcome.FAILED
    assert result.state == SupervisorState.FAILED
    assert result.error_code == WorkerErrorCode.ASSISTANT_ERROR
    assert row is not None
    assert row.state == SupervisorState.FAILED
    assert row.error_code == WorkerErrorCode.ASSISTANT_ERROR
    assert row.result_summary is None
    # The prompt was accepted; the failure comes from the observation, not dispatch.
    assert [operation for operation, _ in provider.model_calls()] == [
        "create",
        "prompt",
    ]


def test_busy_session_never_transitions_to_completed() -> None:
    async def scenario() -> tuple[
        ProcessResult, ClaimedSession | None, FakeOpenCodeProvider
    ]:
        repository = _repo_with_pending()
        provider = FakeOpenCodeProvider(
            turns=(FakeTurn(text="still working"),),
            auto_complete=False,
        )
        service = _service(
            provider,
            repository,
            _settings(max_poll_attempts=1),
        )
        result = await service.run_once()
        return result, await repository.load(_SESSION_ID), provider

    result, row, provider = asyncio.run(scenario())

    assert result.outcome is WorkerOutcome.FAILED
    assert result.error_code == WorkerErrorCode.NO_ASSISTANT_COMPLETION
    assert row is not None
    assert row.state != SupervisorState.COMPLETED
    assert row.state == SupervisorState.FAILED
    assert row.error_code == WorkerErrorCode.NO_ASSISTANT_COMPLETION
    assert row.result_summary is None
    assert [operation for operation, _ in provider.model_calls()] == [
        "create",
        "prompt",
    ]
