"""Allow-listed, bounded sanitizer for OpenCode output.

The sanitizer is the only path from raw external assistant text to a NoahsArk
result projection.  It is intentionally lossy:

* only allow-listed keys survive, so a model-authored ``verdict`` or
  ``approval`` field cannot become authoritative;
* control, format and private-use code points are removed;
* credentials and absolute paths are replaced with stable markers;
* every value is truncated to a bounded length;
* ``derivation.not_a_verdict`` is always ``true`` and cannot be constructed as
  ``false``.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .errors import OpenCodeSanitizerError

DEFAULT_MAX_CHARS = 4000
REDACTED_SECRET = "[REDACTED_SECRET]"
REDACTED_PATH = "[REDACTED_PATH]"
TRUNCATION_MARKER = "\n...[truncated]"
ALLOWLIST_VERSION = "result-allowlist-v1"
ALLOWED_RESULT_KEYS: frozenset[str] = frozenset(
    {
        "blockers",
        "commands",
        "details",
        "files_changed",
        "notes",
        "output",
        "status",
        "summary",
        "tests",
    }
)

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"-----BEGIN[^-]*PRIVATE KEY-----[\s\S]*?-----END[^-]*PRIVATE KEY-----"
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/=]{8,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|token|secret|password|passwd|pwd)"
        r"\b[ \t]*[:=][ \t]*[^\s,;]{4,}"
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"
    ),
)

_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bfile://[^\s'\"<>|]+"),
    re.compile(
        r"(?<![\w])/(?:home|root|tmp|var|etc|opt|srv|mnt|media|Users|usr|proc|dev)"
        r"/[^\s'\"`<>|]+"
    ),
    re.compile(r"(?<![\w])~/[^\s'\"<>|]+"),
    re.compile(r"\b[A-Za-z]:\\[^\s'\"<>|]+"),
    re.compile(r"\\\\[A-Za-z0-9._-]+\\[^\s'\"<>|]+"),
)

_DROPPED_CATEGORIES = frozenset({"Cc", "Cf", "Co", "Cs"})


@dataclass(frozen=True, slots=True)
class Derivation:
    """Provenance that makes the no-verdict invariant machine-checkable."""

    kind: str = "sanitized_observation"
    source: str = "opencode.assistant_text"
    allowlist_version: str = ALLOWLIST_VERSION
    not_a_verdict: bool = field(default=True, init=False)

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "source": self.source,
            "allowlist_version": self.allowlist_version,
            "not_a_verdict": self.not_a_verdict,
        }


@dataclass(frozen=True, slots=True)
class SanitizedText:
    text: str
    redaction_count: int
    truncated: bool
    source_chars: int


@dataclass(frozen=True, slots=True)
class SanitizedResult:
    values: Mapping[str, str]
    truncated: bool
    redaction_count: int
    source_chars: int
    dropped_keys: tuple[str, ...]
    derivation: Derivation

    def as_dict(self) -> dict[str, object]:
        return {
            "fields": dict(self.values),
            "truncated": self.truncated,
            "redaction_count": self.redaction_count,
            "source_chars": self.source_chars,
            "dropped_keys": list(self.dropped_keys),
            "derivation": self.derivation.as_dict(),
        }


def strip_control_characters(value: str) -> str:
    """Normalise newlines and remove control/format/private-use code points."""

    normalised = value.replace("\r\n", "\n").replace("\r", "\n")
    kept: list[str] = []
    for char in normalised:
        if char in ("\n", "\t"):
            kept.append(char)
            continue
        if unicodedata.category(char) in _DROPPED_CATEGORIES:
            continue
        kept.append(char)
    return "".join(kept)


def _replace_patterns(
    value: str, patterns: tuple[re.Pattern[str], ...], replacement: str
) -> tuple[str, int]:
    total = 0
    current = value
    for pattern in patterns:
        current, count = pattern.subn(replacement, current)
        total += count
    return current, total


def redact_sensitive(value: str) -> tuple[str, int]:
    """Strip controls, then redact secrets and absolute paths."""

    cleaned = strip_control_characters(value)
    cleaned, secret_count = _replace_patterns(
        cleaned, _SECRET_PATTERNS, REDACTED_SECRET
    )
    cleaned, path_count = _replace_patterns(cleaned, _PATH_PATTERNS, REDACTED_PATH)
    return cleaned, secret_count + path_count


def _truncate(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    if max_chars <= len(TRUNCATION_MARKER):
        return value[:max_chars], True
    return value[: max_chars - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER, True


def sanitize_text(value: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> SanitizedText:
    if max_chars < 1:
        raise OpenCodeSanitizerError(
            "max_chars must be at least 1",
            details={"max_chars": max_chars},
        )
    redacted, redaction_count = redact_sensitive(value)
    text, truncated = _truncate(redacted, max_chars)
    return SanitizedText(
        text=text,
        redaction_count=redaction_count,
        truncated=truncated,
        source_chars=len(value),
    )


def _render_value(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value) if math.isfinite(value) else None
    if isinstance(value, (list, tuple)):
        items: list[str] = []
        for item in value:
            if not isinstance(item, str):
                return None
            items.append(item)
        return "\n".join(items)
    return None


def sanitize_result(
    payload: Mapping[str, object],
    *,
    max_chars_per_field: int = DEFAULT_MAX_CHARS,
) -> SanitizedResult:
    """Project an untrusted mapping through the allow-list.

    Ordering is deterministic (keys are sorted), unsupported values are
    dropped, and the returned mapping is read-only.
    """

    if max_chars_per_field < 1:
        raise OpenCodeSanitizerError(
            "max_chars_per_field must be at least 1",
            details={"max_chars_per_field": max_chars_per_field},
        )

    values: dict[str, str] = {}
    dropped: list[str] = []
    redaction_count = 0
    source_chars = 0
    truncated = False

    for key in sorted(payload):
        if key not in ALLOWED_RESULT_KEYS:
            dropped.append(key)
            continue
        rendered = _render_value(payload[key])
        if rendered is None:
            dropped.append(key)
            continue
        sanitized = sanitize_text(rendered, max_chars=max_chars_per_field)
        values[key] = sanitized.text
        redaction_count += sanitized.redaction_count
        source_chars += sanitized.source_chars
        truncated = truncated or sanitized.truncated

    return SanitizedResult(
        values=MappingProxyType(values),
        truncated=truncated,
        redaction_count=redaction_count,
        source_chars=source_chars,
        dropped_keys=tuple(sorted(dropped)),
        derivation=Derivation(),
    )


def sanitize_output(
    text: str, *, max_chars: int = DEFAULT_MAX_CHARS
) -> SanitizedResult:
    """Convenience wrapper for a plain assistant-text result."""

    return sanitize_result({"output": text}, max_chars_per_field=max_chars)


__all__ = [
    "ALLOWED_RESULT_KEYS",
    "ALLOWLIST_VERSION",
    "DEFAULT_MAX_CHARS",
    "REDACTED_PATH",
    "REDACTED_SECRET",
    "Derivation",
    "SanitizedResult",
    "SanitizedText",
    "sanitize_output",
    "sanitize_result",
    "sanitize_text",
    "strip_control_characters",
]
