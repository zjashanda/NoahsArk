"""Deterministic in-memory provider for provider-level tests and demos.

The fake mirrors the HTTP provider's *contract*, not the real runtime: ids,
timestamps and content are reproducible, and it never retries or claims
completion.  ``auto_complete=False`` keeps a turn busy until
:meth:`complete_pending` is called, which lets a supervisor test the
"``204`` is not completion" rule without a network.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .config import ModelSelection
from .errors import OpenCodeNotFoundError, OpenCodeValidationError
from .protocol import (
    BoundedPrompt,
    MessageRole,
    MessageView,
    OpenCodeSession,
    PromptReceipt,
    SessionMessages,
    SessionObservation,
    SessionState,
    SessionStatus,
    SessionTurn,
    TextPart,
    observe_from,
)

_FAKE_HTTP_STATUS_NO_CONTENT = 204
_CLOCK_STEP_MS = 1_000


@dataclass(frozen=True, slots=True)
class FakeTurn:
    text: str
    error_name: str | None = None
    complete: bool = True
    synthetic_text: str = ""


@dataclass(slots=True)
class _FakeSession:
    session_id: str
    title: str
    status: SessionStatus
    messages: list[MessageView] = field(default_factory=list)
    prompt_digests: list[str] = field(default_factory=list)
    pending_turn: FakeTurn | None = None
    turn_index: int = 0


class FakeOpenCodeProvider:
    def __init__(
        self,
        *,
        turns: Sequence[FakeTurn] = (),
        auto_complete: bool = True,
        clock_start_ms: int = 1_700_000_000_000,
        model: ModelSelection | None = None,
    ) -> None:
        self._turns = tuple(turns)
        self._auto_complete = auto_complete
        self._clock_ms = clock_start_ms
        self._model = model
        self._model_calls: list[tuple[str, ModelSelection]] = []
        self._message_calls: list[tuple[str, str, ModelSelection | None]] = []
        self._delete_calls: list[str] = []
        self._session_counter = 0
        self._message_counter = 0
        self._sessions: dict[str, _FakeSession] = {}

    # -- deterministic ids / clock ------------------------------------
    def _tick(self) -> int:
        self._clock_ms += _CLOCK_STEP_MS
        return self._clock_ms

    def _next_session_id(self) -> str:
        self._session_counter += 1
        return f"fake-session-{self._session_counter:04d}"

    def _next_message_id(self) -> str:
        self._message_counter += 1
        return f"fake-message-{self._message_counter:04d}"

    def _session(self, session_id: str) -> _FakeSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise OpenCodeNotFoundError(details={"session_id": session_id})
        return session

    # -- provider contract --------------------------------------------
    async def create_session(
        self, *, title: str, model: ModelSelection | None = None
    ) -> OpenCodeSession:
        clean_title = title.strip()
        if not clean_title:
            raise OpenCodeValidationError("session title must not be empty")
        self._record_model("create", model)
        session_id = self._next_session_id()
        self._sessions[session_id] = _FakeSession(
            session_id=session_id,
            title=clean_title,
            status=SessionStatus(state=SessionState.IDLE),
        )
        return OpenCodeSession(session_id=session_id, title=clean_title)

    async def send_prompt(
        self,
        session_id: str,
        prompt: BoundedPrompt,
        *,
        model: ModelSelection | None = None,
    ) -> PromptReceipt:
        if not prompt.text.strip():
            raise OpenCodeValidationError("prompt text must not be empty")
        if prompt.byte_length > prompt.max_bytes:
            raise OpenCodeValidationError(
                "prompt exceeds its declared byte cap",
                details={
                    "byte_length": prompt.byte_length,
                    "max_bytes": prompt.max_bytes,
                },
            )
        session = self._session(session_id)
        if session.pending_turn is not None:
            raise OpenCodeValidationError(
                "a previous fake turn is still pending",
                details={"session_id": session_id},
            )

        self._record_model("prompt", model)
        timestamp = self._tick()
        session.messages.append(
            MessageView(
                message_id=self._next_message_id(),
                session_id=session_id,
                role=MessageRole.USER,
                created_at_ms=timestamp,
                completed_at_ms=timestamp,
                error_name=None,
                error_message=None,
                finish=None,
                parts=(
                    TextPart(
                        part_id=f"{session_id}:user-prompt",
                        text=prompt.text,
                    ),
                ),
            )
        )
        session.prompt_digests.append(prompt.digest)
        turn = self._next_turn(session)
        session.status = SessionStatus(state=SessionState.BUSY)
        if self._auto_complete:
            self._append_turn(session, turn)
            session.status = SessionStatus(state=SessionState.IDLE)
        else:
            session.pending_turn = turn
        return PromptReceipt(
            session_id=session_id,
            prompt_digest=prompt.digest,
            http_status=_FAKE_HTTP_STATUS_NO_CONTENT,
            accepted=True,
            completion_claimed=False,
        )

    async def send_message(
        self,
        session_id: str,
        text: str,
        *,
        model: ModelSelection | None = None,
    ) -> SessionTurn:
        """Deterministic blocking follow-up: records the call, replies at once."""

        if not text.strip():
            raise OpenCodeValidationError("message text must not be empty")
        session = self._session(session_id)
        self._record_model("message", model)
        self._message_calls.append((session_id, text, model))
        timestamp = self._tick()
        session.messages.append(
            MessageView(
                message_id=self._next_message_id(),
                session_id=session_id,
                role=MessageRole.USER,
                created_at_ms=timestamp,
                completed_at_ms=timestamp,
                error_name=None,
                error_message=None,
                finish=None,
                parts=(
                    TextPart(
                        part_id=f"{session_id}:user-follow-up",
                        text=text,
                    ),
                ),
            )
        )
        turn = self._next_turn(session)
        self._append_turn(session, turn)
        session.status = SessionStatus(state=SessionState.IDLE)
        assistant = session.messages[-1]
        return SessionTurn(
            session_id=session_id,
            message_id=assistant.message_id,
            role=assistant.role,
            text=assistant.visible_text,
            created_at_ms=assistant.created_at_ms,
            completed_at_ms=assistant.completed_at_ms,
        )

    async def session_status(self, session_id: str) -> SessionStatus:
        return self._session(session_id).status

    async def session_messages(self, session_id: str) -> SessionMessages:
        session = self._session(session_id)
        return SessionMessages(
            session_id=session_id,
            messages=tuple(session.messages),
        )

    async def abort_session(self, session_id: str) -> bool:
        session = self._session(session_id)
        session.status = SessionStatus(state=SessionState.IDLE)
        session.pending_turn = None
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Record the call and drop the fake session; already gone is success."""

        if not session_id.strip():
            raise OpenCodeValidationError("session_id must not be empty")
        self._delete_calls.append(session_id)
        self._sessions.pop(session_id, None)
        return True

    async def observe(self, session_id: str) -> SessionObservation:
        messages = await self.session_messages(session_id)
        status = await self.session_status(session_id)
        return observe_from(status, messages)

    # -- deterministic control helpers --------------------------------
    def complete_pending(self, session_id: str) -> None:
        session = self._session(session_id)
        turn = session.pending_turn
        if turn is None:
            raise OpenCodeValidationError(
                "fake session has no pending turn",
                details={"session_id": session_id},
            )
        session.pending_turn = None
        self._append_turn(session, turn)
        session.status = SessionStatus(state=SessionState.IDLE)

    def set_status(self, session_id: str, status: SessionStatus) -> None:
        self._session(session_id).status = status

    def prompt_digests(self, session_id: str) -> tuple[str, ...]:
        return tuple(self._session(session_id).prompt_digests)

    def model_calls(self) -> tuple[tuple[str, ModelSelection], ...]:
        """Every model selection the fake received, in call order."""

        return tuple(self._model_calls)

    def message_calls(self) -> tuple[tuple[str, str, ModelSelection | None], ...]:
        """Every follow-up message the fake received, in call order."""

        return tuple(self._message_calls)

    def delete_calls(self) -> tuple[str, ...]:
        """Every session id passed to ``delete_session``, in call order."""

        return tuple(self._delete_calls)

    # -- internals -----------------------------------------------------
    def _record_model(
        self, operation: str, model: ModelSelection | None
    ) -> None:
        selection = model if model is not None else self._model
        if selection is not None:
            self._model_calls.append((operation, selection))

    def _next_turn(self, session: _FakeSession) -> FakeTurn:
        index = session.turn_index
        session.turn_index += 1
        if index < len(self._turns):
            return self._turns[index]
        return FakeTurn(text=f"deterministic fake result {index + 1}")

    def _append_turn(self, session: _FakeSession, turn: FakeTurn) -> None:
        created = self._tick()
        completed = self._tick() if turn.complete else None
        parts: list[TextPart] = []
        if turn.text:
            parts.append(
                TextPart(
                    part_id=f"{session.session_id}:assistant:{created}",
                    text=turn.text,
                )
            )
        if turn.synthetic_text:
            parts.append(
                TextPart(
                    part_id=f"{session.session_id}:synthetic:{created}",
                    text=turn.synthetic_text,
                    synthetic=True,
                )
            )
        session.messages.append(
            MessageView(
                message_id=self._next_message_id(),
                session_id=session.session_id,
                role=MessageRole.ASSISTANT,
                created_at_ms=created,
                completed_at_ms=completed,
                error_name=turn.error_name,
                error_message=None,
                finish="stop" if completed is not None and not turn.error_name else None,
                parts=tuple(parts),
            )
        )


__all__ = ["FakeOpenCodeProvider", "FakeTurn"]
