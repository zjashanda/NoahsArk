"""Typed protocol for the OpenCode headless-session boundary.

The supervisor talks to :class:`OpenCodeProvider`, never to HTTP or JSON.  The
provider returns immutable dataclasses so a supervisor can require all three
completion facts independently:

* session status is ``idle``;
* the latest assistant message has ``time.completed``;
* the latest assistant message has no ``error`` and non-empty visible output.

``POST /session/{id}/prompt_async`` returning ``204`` is only acceptance; the
receipt therefore carries ``completion_claimed=False``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .config import ModelSelection
from .errors import OpenCodeProtocolError


class SessionState(StrEnum):
    IDLE = "idle"
    BUSY = "busy"
    RETRY = "retry"
    UNKNOWN = "unknown"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class SessionStatus:
    state: SessionState
    retry_attempt: int | None = None
    retry_message: str | None = None
    retry_next_ms: int | None = None

    @property
    def is_idle(self) -> bool:
        return self.state is SessionState.IDLE


@dataclass(frozen=True, slots=True)
class TextPart:
    part_id: str
    text: str
    synthetic: bool = False


@dataclass(frozen=True, slots=True)
class MessageView:
    message_id: str
    session_id: str
    role: MessageRole
    created_at_ms: int
    completed_at_ms: int | None
    error_name: str | None
    error_message: str | None
    finish: str | None
    parts: tuple[TextPart, ...]

    @property
    def is_assistant(self) -> bool:
        return self.role is MessageRole.ASSISTANT

    @property
    def completed(self) -> bool:
        return self.completed_at_ms is not None

    @property
    def has_error(self) -> bool:
        return self.error_name is not None

    @property
    def visible_text(self) -> str:
        """Model output only: synthetic/system parts are excluded."""

        return "\n".join(
            part.text for part in self.parts if not part.synthetic and part.text.strip()
        )


@dataclass(frozen=True, slots=True)
class SessionMessages:
    session_id: str
    messages: tuple[MessageView, ...]


@dataclass(frozen=True, slots=True)
class SessionTurn:
    """One completed assistant reply from a blocking follow-up message.

    The blocking ``POST /session/{id}/message`` endpoint answers only after the
    assistant turn finishes, so this value is already a result, not an
    acceptance receipt.
    """

    session_id: str
    message_id: str
    role: MessageRole
    text: str
    created_at_ms: int
    completed_at_ms: int | None


@dataclass(frozen=True, slots=True)
class SessionObservation:
    """A point-in-time snapshot that still requires explicit completion checks."""

    session_id: str
    status: SessionStatus
    messages: SessionMessages

    @property
    def assistant_messages(self) -> tuple[MessageView, ...]:
        return tuple(
            message for message in self.messages.messages if message.is_assistant
        )

    @property
    def latest_assistant(self) -> MessageView | None:
        assistants = self.assistant_messages
        return assistants[-1] if assistants else None

    @property
    def completion_blockers(self) -> tuple[str, ...]:
        """Deterministic reasons the observation is not a completed result."""

        blockers: list[str] = []
        if not self.status.is_idle:
            blockers.append("session_not_idle")
        latest = self.latest_assistant
        if latest is None:
            blockers.append("no_assistant_message")
            return tuple(blockers)
        if not latest.completed:
            blockers.append("assistant_message_incomplete")
        if latest.has_error:
            blockers.append("assistant_message_error")
        if not latest.visible_text.strip():
            blockers.append("assistant_output_empty")
        return tuple(blockers)

    @property
    def is_complete(self) -> bool:
        return not self.completion_blockers


def observe_from(status: SessionStatus, messages: SessionMessages) -> SessionObservation:
    """Combine one status and one message read without inventing completion."""

    if not messages.session_id:
        raise OpenCodeProtocolError("Session message snapshot has no session id")
    return SessionObservation(
        session_id=messages.session_id,
        status=status,
        messages=messages,
    )


@dataclass(frozen=True, slots=True)
class OpenCodeSession:
    session_id: str
    title: str


@dataclass(frozen=True, slots=True)
class BoundedPrompt:
    text: str
    digest: str
    max_bytes: int
    original_bytes: int
    truncated: bool

    @property
    def byte_length(self) -> int:
        return len(self.text.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class PromptReceipt:
    session_id: str
    prompt_digest: str
    http_status: int
    accepted: bool = True
    completion_claimed: bool = False


class OpenCodeProvider(Protocol):
    """The headless boundary the task supervisor is allowed to depend on."""

    async def create_session(
        self, *, title: str, model: ModelSelection | None = None
    ) -> OpenCodeSession: ...

    async def send_prompt(
        self,
        session_id: str,
        prompt: BoundedPrompt,
        *,
        model: ModelSelection | None = None,
    ) -> PromptReceipt: ...

    async def send_message(
        self,
        session_id: str,
        text: str,
        *,
        model: ModelSelection | None = None,
    ) -> SessionTurn: ...

    async def session_status(self, session_id: str) -> SessionStatus: ...

    async def session_messages(self, session_id: str) -> SessionMessages: ...

    async def abort_session(self, session_id: str) -> bool: ...

    async def delete_session(self, session_id: str) -> bool:
        """Delete the remote session; an already-missing session is success."""

        ...

    async def observe(self, session_id: str) -> SessionObservation: ...


__all__ = [
    "BoundedPrompt",
    "MessageRole",
    "MessageView",
    "ModelSelection",
    "OpenCodeProvider",
    "OpenCodeSession",
    "PromptReceipt",
    "SessionMessages",
    "SessionObservation",
    "SessionState",
    "SessionStatus",
    "SessionTurn",
    "TextPart",
    "observe_from",
]
