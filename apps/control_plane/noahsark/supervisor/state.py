"""Closed state vocabulary and explicit error mapping for the worker.

The state names mirror ``noahsark.models.supervisor`` exactly.  Keeping them in
one place lets the service use exhaustive matching instead of ad-hoc string
comparisons, and lets tests assert the persisted vocabulary.
"""

from __future__ import annotations

from enum import StrEnum

from ..integrations.opencode.errors import (
    OpenCodeConfigError,
    OpenCodeError,
    OpenCodeHTTPError,
    OpenCodeNotFoundError,
    OpenCodePromptError,
    OpenCodeProtocolError,
    OpenCodeTransportError,
    OpenCodeValidationError,
)


class SupervisorState(StrEnum):
    PENDING = "PENDING"
    BINDING = "BINDING"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOP_REQUESTED = "STOP_REQUESTED"
    STOPPED = "STOPPED"


ACTIVE_STATES: tuple[str, ...] = (
    SupervisorState.PENDING,
    SupervisorState.BINDING,
    SupervisorState.READY,
    SupervisorState.DISPATCHED,
    SupervisorState.RUNNING,
    SupervisorState.STOP_REQUESTED,
)
WORK_STATES: tuple[str, ...] = (
    SupervisorState.DISPATCHED,
    SupervisorState.RUNNING,
)
LEASABLE_STATES: tuple[str, ...] = (
    SupervisorState.BINDING,
    SupervisorState.DISPATCHED,
    SupervisorState.RUNNING,
)
TERMINAL_STATES: tuple[str, ...] = (
    SupervisorState.COMPLETED,
    SupervisorState.FAILED,
    SupervisorState.STOPPED,
)


class WorkerErrorCode(StrEnum):
    PROVIDER_UNREACHABLE = "PROVIDER_UNREACHABLE"
    PROVIDER_UNAUTHORIZED = "PROVIDER_UNAUTHORIZED"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_REJECTED = "PROVIDER_REJECTED"
    PROVIDER_PROTOCOL_ERROR = "PROVIDER_PROTOCOL_ERROR"
    PROVIDER_CONFIG_INVALID = "PROVIDER_CONFIG_INVALID"
    PROVIDER_VALIDATION_ERROR = "PROVIDER_VALIDATION_ERROR"
    REMOTE_SESSION_NOT_FOUND = "REMOTE_SESSION_NOT_FOUND"
    DISPATCH_UNCERTAIN = "DISPATCH_UNCERTAIN"
    PROMPT_BUILD_FAILED = "PROMPT_BUILD_FAILED"
    COMPLETION_TIMEOUT = "COMPLETION_TIMEOUT"
    NO_ASSISTANT_COMPLETION = "NO_ASSISTANT_COMPLETION"
    ASSISTANT_INCOMPLETE = "ASSISTANT_INCOMPLETE"
    ASSISTANT_OUTPUT_EMPTY = "ASSISTANT_OUTPUT_EMPTY"
    ASSISTANT_ERROR = "ASSISTANT_ERROR"
    SESSION_NOT_IDLE = "SESSION_NOT_IDLE"
    REMOTE_ABORT_FAILED = "REMOTE_ABORT_FAILED"
    INVALID_STATE = "INVALID_STATE"


class ProviderPhase(StrEnum):
    BIND = "bind"
    DISPATCH = "dispatch"
    POLL = "poll"


def provider_error_code(exc: OpenCodeError, *, phase: ProviderPhase) -> WorkerErrorCode:
    """Map a typed provider failure to a stable, non-secret worker code."""

    match exc:
        case OpenCodeTransportError():
            if phase is ProviderPhase.DISPATCH:
                return WorkerErrorCode.DISPATCH_UNCERTAIN
            return WorkerErrorCode.PROVIDER_UNREACHABLE
        case OpenCodeNotFoundError():
            return WorkerErrorCode.REMOTE_SESSION_NOT_FOUND
        case OpenCodePromptError():
            return WorkerErrorCode.PROMPT_BUILD_FAILED
        case OpenCodeConfigError():
            return WorkerErrorCode.PROVIDER_CONFIG_INVALID
        case OpenCodeProtocolError():
            return WorkerErrorCode.PROVIDER_PROTOCOL_ERROR
        case OpenCodeValidationError():
            return WorkerErrorCode.PROVIDER_VALIDATION_ERROR
        case OpenCodeHTTPError():
            if exc.status_code in (401, 403):
                return WorkerErrorCode.PROVIDER_UNAUTHORIZED
            if exc.status_code == 429:
                return WorkerErrorCode.PROVIDER_RATE_LIMITED
            if exc.status_code >= 500:
                return WorkerErrorCode.PROVIDER_UNAVAILABLE
            return WorkerErrorCode.PROVIDER_REJECTED
        case _:
            return WorkerErrorCode.PROVIDER_PROTOCOL_ERROR


def is_transient(exc: OpenCodeError) -> bool:
    """Whether polling may retry without losing or inventing a result."""

    if isinstance(exc, OpenCodeTransportError):
        return True
    if isinstance(exc, OpenCodeHTTPError):
        return exc.retryable
    return False


def dispatch_failure_is_uncertain(exc: OpenCodeError) -> bool:
    """A transport/5xx/odd-2xx dispatch may have been accepted: never resend."""

    if isinstance(exc, (OpenCodeTransportError, OpenCodeProtocolError)):
        return True
    if isinstance(exc, OpenCodeHTTPError):
        return exc.retryable
    return False


def timeout_code(blockers: tuple[str, ...]) -> WorkerErrorCode:
    """Name the missing completion fact instead of claiming success."""

    if "no_assistant_message" in blockers:
        return WorkerErrorCode.NO_ASSISTANT_COMPLETION
    if "assistant_message_error" in blockers:
        return WorkerErrorCode.ASSISTANT_ERROR
    if "assistant_message_incomplete" in blockers:
        return WorkerErrorCode.ASSISTANT_INCOMPLETE
    if "assistant_output_empty" in blockers:
        return WorkerErrorCode.ASSISTANT_OUTPUT_EMPTY
    if "session_not_idle" in blockers:
        return WorkerErrorCode.SESSION_NOT_IDLE
    return WorkerErrorCode.COMPLETION_TIMEOUT


__all__ = [
    "ACTIVE_STATES",
    "LEASABLE_STATES",
    "TERMINAL_STATES",
    "WORK_STATES",
    "ProviderPhase",
    "SupervisorState",
    "WorkerErrorCode",
    "dispatch_failure_is_uncertain",
    "is_transient",
    "provider_error_code",
    "timeout_code",
]
