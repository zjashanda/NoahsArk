"""Typed errors for the OpenCode provider boundary.

These errors deliberately do not inherit from FastAPI's ``ApiError``: the
integration must stay importable without the HTTP API layer and must never
render an OpenCode response body (which can contain credentials or absolute
paths) into a NoahsArk API error.
"""

from __future__ import annotations

from collections.abc import Mapping


class OpenCodeError(Exception):
    """Base class with a stable code, retry hint and non-secret details."""

    code: str
    retryable: bool
    details: Mapping[str, object]

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "details": dict(self.details),
        }


class OpenCodeConfigError(OpenCodeError):
    """Invalid provider configuration; never retryable."""

    def __init__(
        self, message: str, *, details: Mapping[str, object] | None = None
    ) -> None:
        super().__init__(
            "OPENCODE_CONFIG_INVALID",
            message,
            retryable=False,
            details=details,
        )


class OpenCodeValidationError(OpenCodeError):
    """Caller supplied an invalid value to the provider boundary."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "OPENCODE_VALIDATION_ERROR",
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(code, message, retryable=False, details=details)


class OpenCodePromptError(OpenCodeValidationError):
    """The bounded prompt builder rejected its input or size cap."""

    def __init__(
        self, message: str, *, details: Mapping[str, object] | None = None
    ) -> None:
        super().__init__(
            message,
            code="OPENCODE_PROMPT_INVALID",
            details=details,
        )


class OpenCodeSanitizerError(OpenCodeValidationError):
    """The result sanitizer rejected its limit configuration."""

    def __init__(
        self, message: str, *, details: Mapping[str, object] | None = None
    ) -> None:
        super().__init__(
            message,
            code="OPENCODE_SANITIZER_INVALID",
            details=details,
        )


class OpenCodeTransportError(OpenCodeError):
    """The request never produced an HTTP response.

    ``retryable`` is True as a *caller hint*; the provider itself never
    retries, so a supervisor remains in control of backoff and idempotency.
    """

    def __init__(
        self, message: str, *, details: Mapping[str, object] | None = None
    ) -> None:
        super().__init__(
            "OPENCODE_TRANSPORT_ERROR",
            message,
            retryable=True,
            details=details,
        )


class OpenCodeHTTPError(OpenCodeError):
    """A non-success HTTP status with no response body retained."""

    status_code: int

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        retryable: bool,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(code, message, retryable=retryable, details=details)
        self.status_code = status_code


class OpenCodeNotFoundError(OpenCodeHTTPError):
    """The external session (or endpoint) does not exist."""

    def __init__(
        self,
        message: str = "OpenCode session was not found",
        *,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(
            status_code=404,
            code="OPENCODE_NOT_FOUND",
            message=message,
            retryable=False,
            details=details,
        )


class OpenCodeProtocolError(OpenCodeError):
    """The response was well-formed HTTP but not the verified OpenCode schema."""

    def __init__(
        self, message: str, *, details: Mapping[str, object] | None = None
    ) -> None:
        super().__init__(
            "OPENCODE_PROTOCOL_ERROR",
            message,
            retryable=False,
            details=details,
        )


__all__ = [
    "OpenCodeConfigError",
    "OpenCodeError",
    "OpenCodeHTTPError",
    "OpenCodeNotFoundError",
    "OpenCodePromptError",
    "OpenCodeProtocolError",
    "OpenCodeSanitizerError",
    "OpenCodeTransportError",
    "OpenCodeValidationError",
]
