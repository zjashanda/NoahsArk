"""Supervisor state machine over the typed OpenCode provider boundary.

The service consumes durable rows and never invents completion.  A successful
dispatch is only a ``204`` acceptance; ``COMPLETED`` requires an idle session,
a completed assistant message, no assistant error and non-empty visible text.
All terminal writes are compare-and-set, so a restart or a second worker can
only observe, never overwrite, an already-terminal row.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

import anyio

from ..integrations.opencode.errors import (
    OpenCodeError,
    OpenCodePromptError,
    OpenCodeSanitizerError,
)
from ..integrations.opencode.prompt import (
    TaskPromptInput,
    build_task_prompt,
    format_execution_context,
)
from ..integrations.opencode.protocol import (
    OpenCodeProvider,
    SessionObservation,
)
from ..integrations.opencode.sanitizer import sanitize_output
from ..supervisor.config import SupervisorSettings
from ..supervisor.repository import ClaimedSession, SupervisorRepository
from ..supervisor.state import (
    TERMINAL_STATES,
    ProviderPhase,
    SupervisorState,
    WorkerErrorCode,
    dispatch_failure_is_uncertain,
    is_transient,
    provider_error_code,
    timeout_code,
)

logger = logging.getLogger("noahsark.supervisor")


class WorkerOutcome(StrEnum):
    IDLE = "idle"
    BOUND = "bound"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    DEFERRED = "deferred"


@dataclass(frozen=True, slots=True)
class ProcessResult:
    outcome: WorkerOutcome
    session_id: str
    state: str | None = None
    error_code: str | None = None


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def _default_sleep(seconds: float) -> None:
    await anyio.sleep(seconds)


class SupervisorService:
    def __init__(
        self,
        provider: OpenCodeProvider,
        repository: SupervisorRepository,
        settings: SupervisorSettings,
        *,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._settings = settings
        self._clock = clock or _utcnow
        self._sleep = sleep or _default_sleep

    async def request_stop(self, session_id: uuid.UUID) -> bool:
        return await self._repository.request_stop(session_id, now=self._clock())

    async def run_once(self) -> ProcessResult:
        now = self._clock()
        claim = await self._repository.claim_next(
            worker_id=self._settings.worker_id or "worker",
            lease_seconds=self._settings.claim_lease_seconds,
            now=now,
        )
        if claim is None:
            return ProcessResult(WorkerOutcome.IDLE, "")
        return await self.process(claim)

    async def process(self, claim: ClaimedSession) -> ProcessResult:
        try:
            state = SupervisorState(claim.state)
        except ValueError:
            logger.error(
                "supervisor session=%s has invalid state=%s",
                claim.display_id,
                claim.state,
            )
            return ProcessResult(
                WorkerOutcome.DEFERRED,
                claim.display_id,
                claim.state,
                WorkerErrorCode.INVALID_STATE,
            )

        match state:
            case SupervisorState.BINDING:
                bound = await self._bind(claim)
                if bound is None or bound.state != SupervisorState.READY:
                    return self._result(bound)
                return await self._dispatch(bound)
            case SupervisorState.READY:
                return await self._dispatch(claim)
            case SupervisorState.DISPATCHED | SupervisorState.RUNNING:
                return await self._poll(claim)
            case SupervisorState.STOP_REQUESTED:
                return await self._stop(claim)
            case SupervisorState.PENDING:
                # claim_next promotes PENDING to BINDING before returning.
                return ProcessResult(
                    WorkerOutcome.DEFERRED,
                    claim.display_id,
                    claim.state,
                    WorkerErrorCode.INVALID_STATE,
                )
            case SupervisorState.COMPLETED | SupervisorState.FAILED | SupervisorState.STOPPED:
                return self._result(claim)

    async def _bind(self, claim: ClaimedSession) -> ClaimedSession | None:
        remote_id = claim.remote_session_id
        if remote_id is None:
            try:
                model = self._settings.model_selection()
                session = await self._provider.create_session(
                    title=f"NoahsArk supervisor {claim.task_display_id}",
                    model=model,
                )
            except OpenCodeError as exc:
                code = provider_error_code(exc, phase=ProviderPhase.BIND)
                await self._fail(claim.supervisor_session_id, code)
                logger.warning(
                    "supervisor session=%s bind failed code=%s",
                    claim.display_id,
                    code.value,
                )
                # ``_fail`` persisted a terminal row; return it so the caller
                # reports FAILED instead of DEFERRED with an empty session id.
                return await self._repository.load(claim.supervisor_session_id)
            remote_id = session.session_id

        if not await self._repository.bind_remote(
            claim.supervisor_session_id, remote_session_id=remote_id, now=self._clock()
        ):
            return await self._repository.load(claim.supervisor_session_id)
        logger.info("supervisor session=%s bound", claim.display_id)
        return await self._repository.load(claim.supervisor_session_id)

    async def _dispatch(self, claim: ClaimedSession) -> ProcessResult:
        remote_id = claim.remote_session_id
        if remote_id is None:
            await self._fail(
                claim.supervisor_session_id, WorkerErrorCode.PROVIDER_VALIDATION_ERROR
            )
            return ProcessResult(
                WorkerOutcome.FAILED,
                claim.display_id,
                SupervisorState.FAILED,
                WorkerErrorCode.PROVIDER_VALIDATION_ERROR,
            )

        try:
            prompt = build_task_prompt(
                TaskPromptInput(
                    task_id=claim.task_display_id,
                    title=claim.task_title,
                    instructions=claim.task_objective,
                    resources=format_execution_context(
                        claim.task_execution_context
                    ),
                ),
                max_bytes=self._settings.max_prompt_bytes,
            )
        except OpenCodePromptError:
            await self._fail(
                claim.supervisor_session_id, WorkerErrorCode.PROMPT_BUILD_FAILED
            )
            return ProcessResult(
                WorkerOutcome.FAILED,
                claim.display_id,
                SupervisorState.FAILED,
                WorkerErrorCode.PROMPT_BUILD_FAILED,
            )

        # Persist the dispatch intent BEFORE sending.  If the process dies
        # between this commit and the HTTP call, restart polls instead of
        # resending, which is the at-most-once side of the trade-off.
        if not await self._repository.mark_dispatched(
            claim.supervisor_session_id, now=self._clock()
        ):
            loaded = await self._repository.load(claim.supervisor_session_id)
            return self._result(loaded)

        try:
            model = self._settings.model_selection()
            receipt = await self._provider.send_prompt(
                remote_id, prompt, model=model
            )
        except OpenCodeError as exc:
            code = provider_error_code(exc, phase=ProviderPhase.DISPATCH)
            if dispatch_failure_is_uncertain(exc):
                await self._repository.record_uncertain(
                    claim.supervisor_session_id, error_code=code.value, now=self._clock()
                )
                logger.warning(
                    "supervisor session=%s dispatch uncertain code=%s",
                    claim.display_id,
                    code.value,
                )
            else:
                await self._fail(claim.supervisor_session_id, code)
                return ProcessResult(
                    WorkerOutcome.FAILED,
                    claim.display_id,
                    SupervisorState.FAILED,
                    code,
                )
        else:
            if not receipt.accepted:
                await self._fail(
                    claim.supervisor_session_id, WorkerErrorCode.PROVIDER_REJECTED
                )
                return ProcessResult(
                    WorkerOutcome.FAILED,
                    claim.display_id,
                    SupervisorState.FAILED,
                    WorkerErrorCode.PROVIDER_REJECTED,
                )
            logger.info("supervisor session=%s prompt accepted", claim.display_id)

        loaded = await self._repository.load(claim.supervisor_session_id)
        if loaded is None:
            return ProcessResult(WorkerOutcome.DEFERRED, claim.display_id)
        return await self._poll(loaded)

    async def _poll(self, claim: ClaimedSession) -> ProcessResult:
        remote_id = claim.remote_session_id
        if remote_id is None:
            return await self._fail_with(
                claim, WorkerErrorCode.PROVIDER_VALIDATION_ERROR
            )

        observed: SessionObservation | None = None
        transient_errors = 0
        attempts = 0
        while True:
            now = self._clock()
            current = await self._repository.load(claim.supervisor_session_id)
            if current is None:
                return ProcessResult(WorkerOutcome.DEFERRED, claim.display_id)
            if current.state == SupervisorState.STOP_REQUESTED:
                return await self._stop(current)
            if current.state in TERMINAL_STATES:
                return self._result(current)

            dispatch_at = current.dispatch_at or current.updated_at
            deadline_seconds = self._settings.completion_timeout_seconds
            if (now - dispatch_at).total_seconds() >= deadline_seconds:
                return await self._timeout(current, observed)
            if attempts >= self._settings.max_poll_attempts:
                return await self._timeout(current, observed)

            try:
                observed = await self._provider.observe(remote_id)
            except OpenCodeError as exc:
                if not is_transient(exc):
                    code = provider_error_code(exc, phase=ProviderPhase.POLL)
                    return await self._fail_with(current, code)
                transient_errors += 1
                code = provider_error_code(exc, phase=ProviderPhase.POLL)
                await self._repository.record_uncertain(
                    current.supervisor_session_id, error_code=code.value, now=now
                )
                if (
                    transient_errors
                    >= self._settings.max_consecutive_provider_errors
                ):
                    return await self._fail_with(
                        current, WorkerErrorCode.PROVIDER_UNREACHABLE
                    )
                logger.warning(
                    "supervisor session=%s poll transient error code=%s",
                    current.display_id,
                    code.value,
                )
                await self._sleep(self._settings.poll_interval_seconds)
                attempts += 1
                continue

            transient_errors = 0
            if observed.is_complete:
                result = await self._complete(current, observed)
                if result is not None:
                    return result
                continue

            latest = observed.latest_assistant
            if latest is not None and latest.has_error:
                return await self._fail_with(current, WorkerErrorCode.ASSISTANT_ERROR)

            if current.state == SupervisorState.DISPATCHED:
                await self._repository.mark_running(
                    current.supervisor_session_id, now=now
                )
            await self._repository.touch(current.supervisor_session_id, now=now)
            await self._sleep(self._settings.poll_interval_seconds)
            attempts += 1

    async def _complete(
        self, claim: ClaimedSession, observation: SessionObservation
    ) -> ProcessResult | None:
        latest = observation.latest_assistant
        text = latest.visible_text if latest is not None else ""
        try:
            sanitized = sanitize_output(
                text, max_chars=self._settings.result_max_chars
            )
        except OpenCodeSanitizerError:
            return await self._fail_with(
                claim, WorkerErrorCode.ASSISTANT_OUTPUT_EMPTY
            )
        summary = sanitized.values.get("output", "")
        if not summary.strip():
            return await self._fail_with(
                claim, WorkerErrorCode.ASSISTANT_OUTPUT_EMPTY
            )

        written = await self._repository.complete(
            claim.supervisor_session_id, result_summary=summary, now=self._clock()
        )
        if written:
            logger.info("supervisor session=%s completed", claim.display_id)
            return ProcessResult(
                WorkerOutcome.COMPLETED,
                claim.display_id,
                SupervisorState.COMPLETED,
            )
        loaded = await self._repository.load(claim.supervisor_session_id)
        if loaded is not None and loaded.state in TERMINAL_STATES:
            return self._result(loaded)
        return None

    async def _timeout(
        self, claim: ClaimedSession, observation: SessionObservation | None
    ) -> ProcessResult:
        blockers = observation.completion_blockers if observation is not None else ()
        code = timeout_code(blockers)
        if claim.remote_session_id is not None:
            await self._abort(claim)
        return await self._fail_with(claim, code)

    async def _stop(self, claim: ClaimedSession) -> ProcessResult:
        abort_ok = True
        if claim.remote_session_id is not None:
            abort_ok = await self._abort(claim)
        code = None if abort_ok else WorkerErrorCode.REMOTE_ABORT_FAILED
        written = await self._repository.mark_stopped(
            claim.supervisor_session_id,
            error_code=code.value if code is not None else None,
            now=self._clock(),
        )
        if written:
            logger.info("supervisor session=%s stopped", claim.display_id)
            return ProcessResult(
                WorkerOutcome.STOPPED,
                claim.display_id,
                SupervisorState.STOPPED,
                code,
            )
        loaded = await self._repository.load(claim.supervisor_session_id)
        return self._result(loaded)

    async def _abort(self, claim: ClaimedSession) -> bool:
        remote_id = claim.remote_session_id
        if remote_id is None:
            return True
        try:
            await self._provider.abort_session(remote_id)
        except OpenCodeError as exc:
            logger.warning(
                "supervisor session=%s abort failed code=%s",
                claim.display_id,
                exc.code,
            )
            return False
        return True

    async def _fail(
        self, session_id: uuid.UUID, code: WorkerErrorCode
    ) -> bool:
        return await self._repository.fail(
            session_id, error_code=code.value, now=self._clock()
        )

    async def _fail_with(
        self, claim: ClaimedSession, code: WorkerErrorCode
    ) -> ProcessResult:
        written = await self._fail(claim.supervisor_session_id, code)
        if written:
            return ProcessResult(
                WorkerOutcome.FAILED,
                claim.display_id,
                SupervisorState.FAILED,
                code,
            )
        loaded = await self._repository.load(claim.supervisor_session_id)
        if loaded is not None and loaded.state == SupervisorState.STOP_REQUESTED:
            return await self._stop(loaded)
        return self._result(loaded)

    def _result(self, claim: ClaimedSession | None) -> ProcessResult:
        if claim is None:
            return ProcessResult(WorkerOutcome.DEFERRED, "")
        match SupervisorState(claim.state):
            case SupervisorState.COMPLETED:
                return ProcessResult(
                    WorkerOutcome.COMPLETED, claim.display_id, claim.state
                )
            case SupervisorState.FAILED:
                return ProcessResult(
                    WorkerOutcome.FAILED,
                    claim.display_id,
                    claim.state,
                    claim.error_code,
                )
            case SupervisorState.STOPPED:
                return ProcessResult(
                    WorkerOutcome.STOPPED,
                    claim.display_id,
                    claim.state,
                    claim.error_code,
                )
            case _:
                return ProcessResult(
                    WorkerOutcome.RUNNING, claim.display_id, claim.state
                )


__all__ = ["ProcessResult", "SupervisorService", "WorkerOutcome"]
