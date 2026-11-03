"""Map verified OpenCode wire models onto protocol dataclasses."""

from __future__ import annotations

from typing import Literal, assert_never

from pydantic import BaseModel, ValidationError

from .errors import OpenCodeProtocolError
from .protocol import (
    MessageRole,
    MessageView,
    SessionState,
    SessionStatus,
    TextPart,
)
from .sanitizer import sanitize_text
from .wire import (
    BusyStatusWire,
    IdleStatusWire,
    MessageEnvelopeWire,
    MessageErrorWire,
    RetryStatusWire,
    StatusWire,
)


def parse_wire[WireModel: BaseModel](
    model: type[WireModel], content: bytes, *, path: str
) -> WireModel:
    try:
        return model.model_validate_json(content)
    except ValidationError as exc:
        raise OpenCodeProtocolError(
            "OpenCode response did not match the verified schema",
            details={"path": path, "error_count": exc.error_count()},
        ) from exc


def role_from_wire(role: Literal["user", "assistant"]) -> MessageRole:
    match role:
        case "user":
            return MessageRole.USER
        case "assistant":
            return MessageRole.ASSISTANT
        case _ as unreachable:
            assert_never(unreachable)


def text_parts(envelope: MessageEnvelopeWire) -> tuple[TextPart, ...]:
    parts: list[TextPart] = []
    for index, part in enumerate(envelope.parts):
        match part.type:
            case "text":
                if part.text is None or part.ignored:
                    continue
                parts.append(
                    TextPart(
                        part_id=part.id or f"{envelope.info.id}:text:{index}",
                        text=part.text,
                        synthetic=part.synthetic,
                    )
                )
            case _:
                continue
    return tuple(parts)


def error_message(error: MessageErrorWire | None) -> str | None:
    if error is None:
        return None
    raw = (error.data or {}).get("message")
    if not isinstance(raw, str):
        return None
    return sanitize_text(raw, max_chars=500).text


def message_from_wire(envelope: MessageEnvelopeWire) -> MessageView:
    info = envelope.info
    return MessageView(
        message_id=info.id,
        session_id=info.session_id,
        role=role_from_wire(info.role),
        created_at_ms=info.time.created,
        completed_at_ms=info.time.completed,
        error_name=info.error.name if info.error is not None else None,
        error_message=error_message(info.error),
        finish=info.finish,
        parts=text_parts(envelope),
    )


def status_from_wire(wire: StatusWire) -> SessionStatus:
    match wire:
        case IdleStatusWire():
            return SessionStatus(state=SessionState.IDLE)
        case BusyStatusWire():
            return SessionStatus(state=SessionState.BUSY)
        case RetryStatusWire():
            message = sanitize_text(wire.message, max_chars=500).text
            return SessionStatus(
                state=SessionState.RETRY,
                retry_attempt=wire.attempt,
                retry_message=message,
                retry_next_ms=wire.next_ms,
            )
        case _ as unreachable:
            assert_never(unreachable)


__all__ = [
    "error_message",
    "message_from_wire",
    "parse_wire",
    "role_from_wire",
    "status_from_wire",
    "text_parts",
]
