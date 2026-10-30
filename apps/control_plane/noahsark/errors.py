"""Domain/API errors that render through the unified error envelope."""

from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """Raised by services/dependencies; rendered as ``{error: {...}}``.

    ``retryable`` is intentionally explicit: clients must not guess whether a
    failed read can be retried.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


def not_found(object_type: str, identifier: str) -> ApiError:
    return ApiError(
        404,
        "NOT_FOUND",
        f"{object_type} {identifier!r} was not found",
        retryable=False,
        details={"object_type": object_type, "identifier": identifier},
    )


def forbidden(message: str, *, details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(403, "FORBIDDEN", message, retryable=False, details=details)


def unauthorized(
    message: str,
    *,
    code: str = "UNAUTHENTICATED",
    details: dict[str, Any] | None = None,
) -> ApiError:
    """Authentication failure.  Always fail closed: no anonymous fallback."""

    return ApiError(401, code, message, retryable=False, details=details)


def audit_immutable(operation: str) -> ApiError:
    return ApiError(
        405,
        "AUDIT_IMMUTABLE",
        "Audit events are append-only; corrections must be new compensating events",
        retryable=False,
        details={"operation": operation, "append_only": True},
    )


def validation_error(
    message: str, *, details: dict[str, Any] | None = None
) -> ApiError:
    return ApiError(400, "VALIDATION_ERROR", message, retryable=False, details=details)


def idempotency_required() -> ApiError:
    return ApiError(
        400,
        "IDEMPOTENCY_REQUIRED",
        "This write requires an Idempotency-Key header",
        retryable=False,
        details={"header": "Idempotency-Key"},
    )


def idempotency_conflict(
    *, key: str, scope: str, details: dict[str, Any] | None = None
) -> ApiError:
    payload = {"scope": scope, "key": key}
    if details:
        payload.update(details)
    return ApiError(
        409,
        "IDEMPOTENCY_CONFLICT",
        "Idempotency-Key was already used with a different payload",
        retryable=False,
        details=payload,
    )


def invalid_state_transition(
    message: str, *, details: dict[str, Any] | None = None
) -> ApiError:
    return ApiError(
        409, "INVALID_STATE_TRANSITION", message, retryable=False, details=details
    )


def release_precondition_failed(
    message: str, *, details: dict[str, Any] | None = None
) -> ApiError:
    return ApiError(
        409,
        "RELEASE_PRECONDITION_FAILED",
        message,
        retryable=False,
        details=details,
    )
