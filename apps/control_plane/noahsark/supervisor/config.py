"""Configuration for the independent supervisor worker.

The worker is disabled by default.  Enabling it requires an explicit
``NOAHSARK_SUPERVISOR_ENABLED=true`` plus a PostgreSQL URL and an OpenCode base
URL.  Credentials are never logged and are read from ``SecretStr`` fields.
"""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..integrations.opencode.errors import OpenCodeConfigError
from ..integrations.opencode.http_provider import (
    BasicAuthCredentials,
    HTTPProviderConfig,
    ModelSelection,
    TimeoutConfig,
)

POOR_PROFILE = "poor"
DEFAULT_OPENCODE_PROFILE_FILE = "~/.config/opencode/profile.active"


def assert_poor_profile(profile_name: str) -> None:
    """Fail closed unless the active OpenCode profile is the required one."""

    clean = profile_name.strip()
    if not clean:
        raise OpenCodeConfigError(
            "OpenCode profile name must not be empty",
            details={"profile": "<blank>"},
        )
    if clean != POOR_PROFILE:
        raise OpenCodeConfigError(
            "OpenCode supervisor requires the 'poor' profile",
            details={"profile": clean},
        )


class SupervisorSettings(BaseSettings):
    """Environment-driven worker settings (``NOAHSARK_SUPERVISOR_*``)."""

    enabled: bool = False
    database_url: str | None = None

    opencode_base_url: str | None = None
    opencode_username: str | None = None
    opencode_password: SecretStr | None = None
    opencode_provider_id: str = "listenai"
    opencode_model_id: str = "deepseek-v4.1-flash-expires-on-0910"
    opencode_profile: str = POOR_PROFILE
    opencode_profile_file: str | None = None
    opencode_connect_timeout_seconds: float = 5.0
    opencode_read_timeout_seconds: float = 30.0
    opencode_write_timeout_seconds: float = 10.0
    opencode_pool_timeout_seconds: float = 5.0

    # A claim is durable in supervisor_sessions.state plus updated_at.  The
    # lease only controls when another worker may reclaim a stale row.
    claim_lease_seconds: float = 30.0
    poll_interval_seconds: float = 2.0
    completion_timeout_seconds: float = 900.0
    max_poll_attempts: int = 500
    max_consecutive_provider_errors: int = 3
    idle_sleep_seconds: float = 5.0

    max_prompt_bytes: int = 16_384
    result_max_chars: int = 4_000
    worker_id: str | None = None
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="NOAHSARK_SUPERVISOR_",
        env_file=".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _validate(self) -> SupervisorSettings:
        for name in (
            "claim_lease_seconds",
            "poll_interval_seconds",
            "completion_timeout_seconds",
            "idle_sleep_seconds",
            "opencode_connect_timeout_seconds",
            "opencode_read_timeout_seconds",
            "opencode_write_timeout_seconds",
            "opencode_pool_timeout_seconds",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a positive finite number")
        for name in ("max_poll_attempts", "max_consecutive_provider_errors"):
            if int(getattr(self, name)) < 1:
                raise ValueError(f"{name} must be at least 1")
        for name in ("max_prompt_bytes", "result_max_chars"):
            if int(getattr(self, name)) < 1:
                raise ValueError(f"{name} must be at least 1")
        if self.enabled:
            if not (self.database_url or "").strip():
                raise ValueError("database_url is required when the worker is enabled")
            if not (self.opencode_base_url or "").strip():
                raise ValueError(
                    "opencode_base_url is required when the worker is enabled"
                )
            if bool(self.opencode_username) != bool(self.opencode_password):
                raise ValueError(
                    "opencode_username and opencode_password must be set together"
                )
            if not self.opencode_provider_id.strip():
                raise ValueError(
                    "opencode_provider_id is required when the worker is enabled"
                )
            if not self.opencode_model_id.strip():
                raise ValueError(
                    "opencode_model_id is required when the worker is enabled"
                )
            if not self.opencode_profile.strip():
                raise ValueError(
                    "opencode_profile is required when the worker is enabled"
                )
        return self

    @property
    def profile_file_path(self) -> str:
        configured = (self.opencode_profile_file or "").strip()
        if configured:
            return configured
        return str(Path(DEFAULT_OPENCODE_PROFILE_FILE).expanduser())

    def verify_profile_file(self, path: str | None = None) -> str:
        """Read the active profile and fail closed on missing/mismatch.

        The file contents are never logged or echoed; only the resolved
        profile name appears in a returned value or error detail.
        """

        target = (path or "").strip() or self.profile_file_path
        try:
            raw = Path(target).expanduser().read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OpenCodeConfigError(
                "OpenCode profile file is missing or unreadable",
                details={"profile": "<unreadable>"},
            ) from exc
        name = raw.strip()
        if not name:
            raise OpenCodeConfigError(
                "OpenCode profile file is empty",
                details={"profile": "<blank>"},
            )
        if name != self.opencode_profile.strip():
            raise OpenCodeConfigError(
                "OpenCode profile does not match the configured supervisor profile",
                details={"profile": name, "required": self.opencode_profile},
            )
        assert_poor_profile(name)
        return name

    def model_selection(self) -> ModelSelection:
        """The provider/model pair every supervisor session must use."""

        return ModelSelection(
            provider_id=self.opencode_provider_id,
            model_id=self.opencode_model_id,
        )

    def provider_config(self) -> HTTPProviderConfig:
        """Build the concrete provider config, failing closed when incomplete."""

        if not (self.opencode_base_url or "").strip():
            raise OpenCodeConfigError("opencode_base_url is not configured")
        auth: BasicAuthCredentials | None = None
        if self.opencode_username and self.opencode_password is not None:
            auth = BasicAuthCredentials(
                username=self.opencode_username,
                password=self.opencode_password.get_secret_value(),
            )
        base_url = (self.opencode_base_url or "").strip()
        return HTTPProviderConfig(
            base_url=base_url,
            model=self.model_selection(),
            basic_auth=auth,
            timeout=TimeoutConfig(
                connect=self.opencode_connect_timeout_seconds,
                read=self.opencode_read_timeout_seconds,
                write=self.opencode_write_timeout_seconds,
                pool=self.opencode_pool_timeout_seconds,
            ),
        )


__all__ = [
    "DEFAULT_OPENCODE_PROFILE_FILE",
    "POOR_PROFILE",
    "SupervisorSettings",
    "assert_poor_profile",
]
