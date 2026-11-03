"""Validated HTTP provider configuration (URL, auth, explicit timeouts)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

import httpx

from .errors import OpenCodeConfigError


@dataclass(frozen=True, slots=True)
class TimeoutConfig:
    connect: float = 5.0
    read: float = 30.0
    write: float = 10.0
    pool: float = 5.0

    def __post_init__(self) -> None:
        for name in ("connect", "read", "write", "pool"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0:
                raise OpenCodeConfigError(
                    "Every OpenCode timeout must be a positive finite number",
                    details={"field": name, "value": value},
                )

    def as_httpx(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect,
            read=self.read,
            write=self.write,
            pool=self.pool,
        )


@dataclass(frozen=True, slots=True)
class BasicAuthCredentials:
    username: str
    password: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.username.strip():
            raise OpenCodeConfigError("Basic auth username must not be empty")


def _normalise_base_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise OpenCodeConfigError("OpenCode base URL must not be empty")
    try:
        parsed = urlsplit(raw)
    except ValueError as exc:
        raise OpenCodeConfigError("OpenCode base URL is not a valid URL") from exc
    if parsed.scheme not in {"http", "https"}:
        raise OpenCodeConfigError(
            "OpenCode base URL must use http or https",
            details={"scheme": parsed.scheme},
        )
    if not parsed.netloc or not parsed.hostname:
        raise OpenCodeConfigError("OpenCode base URL must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise OpenCodeConfigError(
            "OpenCode base URL must not embed credentials; use basic_auth"
        )
    if parsed.query or parsed.fragment:
        raise OpenCodeConfigError(
            "OpenCode base URL must not include a query or fragment"
        )
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


@dataclass(frozen=True, slots=True)
class ModelSelection:
    """The exact OpenCode provider/model pair a session must run.

    Both parts are mandatory: the provider never falls back to the OpenCode
    default model, so a blank value is a configuration error rather than a
    silent substitution.
    """

    provider_id: str
    model_id: str

    def __post_init__(self) -> None:
        for name in ("provider_id", "model_id"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise OpenCodeConfigError(
                    "OpenCode model selection must not be empty",
                    details={"field": name},
                )
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class HTTPProviderConfig:
    base_url: str
    basic_auth: BasicAuthCredentials | None = None
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    model: ModelSelection | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", _normalise_base_url(self.base_url))
        if self.model is not None and not isinstance(self.model, ModelSelection):
            raise OpenCodeConfigError("model must be a ModelSelection")


__all__ = [
    "BasicAuthCredentials",
    "HTTPProviderConfig",
    "ModelSelection",
    "TimeoutConfig",
]
