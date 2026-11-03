"""Deterministic, byte-bounded task prompt construction.

The same :class:`TaskPromptInput` always produces the same text and digest.
The cap is enforced on UTF-8 bytes (not characters) so the value sent to
OpenCode cannot exceed the transport budget after encoding.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .errors import OpenCodePromptError
from .protocol import BoundedPrompt
from .sanitizer import strip_control_characters

PROMPT_SCHEMA = "noahsark.opencode.task-prompt.v1"
DEFAULT_MAX_PROMPT_BYTES = 16_384
_PROMPT_MARKER = "\n...[prompt truncated]"


@dataclass(frozen=True, slots=True)
class PromptResources:
    """Pre-formatted execution-resource lines for the prompt section."""

    nodes: tuple[str, ...] = ()
    devices: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.nodes and not self.devices


@dataclass(frozen=True, slots=True)
class TaskPromptInput:
    task_id: str
    title: str
    instructions: str
    acceptance: tuple[str, ...] = ()
    resources: PromptResources = PromptResources()


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _endpoint_summary(endpoints: Any) -> str:
    """Render device endpoints compactly and deterministically.

    Serial endpoints become ``serial A=COM3, B=COM7``; audio endpoints become
    ``audio capture 8ch`` / ``audio render 2ch``.  Unknown kinds fall back to
    their kind plus binding so no selected endpoint disappears from the prompt.
    """

    if not isinstance(endpoints, Sequence) or isinstance(endpoints, (str, bytes)):
        return ""
    serial: list[str] = []
    audio: list[str] = []
    other: list[str] = []
    for endpoint in endpoints:
        if not isinstance(endpoint, Mapping):
            continue
        kind = _text(endpoint.get("kind")).lower()
        if kind == "serial":
            role = _text(endpoint.get("role"))
            port = _text(endpoint.get("port")) or _text(endpoint.get("binding"))
            if not port:
                continue
            serial.append(f"{role}={port}" if role else port)
            continue
        if kind.startswith("audio"):
            direction = _text(endpoint.get("direction")).lower()
            if not direction and kind in {"audio_capture", "audio_input"}:
                direction = "capture"
            if not direction and kind in {"audio_playback", "audio_output"}:
                direction = "render"
            channels = endpoint.get("channels")
            segment = "audio"
            if direction:
                segment += f" {direction}"
            if isinstance(channels, int) and not isinstance(channels, bool):
                segment += f" {channels}ch"
            device_key = _text(endpoint.get("device_key"))
            if device_key:
                segment += f" [{device_key}]"
            name = _text(endpoint.get("name"))
            if name:
                segment += f" {name}"
            if segment not in audio:
                audio.append(segment)
            continue
        label = kind or "endpoint"
        binding = _text(endpoint.get("binding")) or _text(endpoint.get("port"))
        other.append(f"{label}={binding}" if binding else label)
    groups: list[str] = []
    if serial:
        groups.append("serial " + ", ".join(serial))
    if audio:
        groups.append("; ".join(audio))
    if other:
        groups.append("; ".join(other))
    return "; ".join(groups)


def format_execution_context(execution_context: Mapping[str, Any]) -> PromptResources:
    """Turn a persisted task execution-context snapshot into prompt lines."""

    raw_nodes = execution_context.get("nodes")
    raw_devices = execution_context.get("devices")
    node_rows = raw_nodes if isinstance(raw_nodes, list) else []
    device_rows = raw_devices if isinstance(raw_devices, list) else []

    node_labels: dict[str, str] = {}
    nodes: list[str] = []
    for node in sorted(
        (row for row in node_rows if isinstance(row, Mapping)),
        key=lambda row: _text(row.get("display_id")),
    ):
        display_id = _text(node.get("display_id"))
        if not display_id:
            continue
        node_labels[_text(node.get("node_id"))] = display_id
        hostname = _text(node.get("hostname")) or display_id
        state = _text(node.get("communication_state")) or "UNKNOWN"
        nodes.append(f"- {display_id} ({hostname}, {state})")

    devices: list[str] = []
    for device in sorted(
        (row for row in device_rows if isinstance(row, Mapping)),
        key=lambda row: _text(row.get("display_id")),
    ):
        display_id = _text(device.get("display_id"))
        if not display_id:
            continue
        node_label = node_labels.get(_text(device.get("node_id")), "unknown-node")
        summary = _endpoint_summary(device.get("endpoints"))
        line = f"- {display_id} [{node_label}]"
        devices.append(f"{line}: {summary}" if summary else line)

    return PromptResources(nodes=tuple(nodes), devices=tuple(devices))


def _truncate_utf8(value: str, max_bytes: int, marker: str) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value, False
    marker_bytes = marker.encode("utf-8")
    if len(marker_bytes) >= max_bytes:
        return encoded[:max_bytes].decode("utf-8", "ignore"), True
    budget = max_bytes - len(marker_bytes)
    head = encoded[:budget].decode("utf-8", "ignore")
    return head + marker, True


def build_task_prompt(
    task: TaskPromptInput, *, max_bytes: int = DEFAULT_MAX_PROMPT_BYTES
) -> BoundedPrompt:
    if max_bytes < 1:
        raise OpenCodePromptError(
            "max_bytes must be at least 1",
            details={"max_bytes": max_bytes},
        )

    task_id = strip_control_characters(task.task_id).strip()
    if not task_id:
        raise OpenCodePromptError("task_id is required")
    title = strip_control_characters(task.title).strip() or "(untitled)"
    instructions = strip_control_characters(task.instructions).strip()
    if not instructions:
        raise OpenCodePromptError(
            "instructions are required",
            details={"task_id": task_id},
        )
    acceptance = tuple(
        item
        for item in (
            strip_control_characters(value).strip() for value in task.acceptance
        )
        if item
    )

    resources = PromptResources(
        nodes=tuple(
            line
            for line in (
                strip_control_characters(value).strip() for value in task.resources.nodes
            )
            if line
        ),
        devices=tuple(
            line
            for line in (
                strip_control_characters(value).strip()
                for value in task.resources.devices
            )
            if line
        ),
    )

    lines = [
        f"schema: {PROMPT_SCHEMA}",
        f"task_id: {task_id}",
        f"title: {title}",
        "",
        "## Instructions",
        instructions,
    ]
    if not resources.is_empty:
        lines.append("")
        lines.append("## Execution resources")
        if resources.nodes:
            lines.append("Nodes:")
            lines.extend(resources.nodes)
        if resources.devices:
            lines.append("Devices:")
            lines.extend(resources.devices)
    lines.extend(["", "## Acceptance criteria"])
    if acceptance:
        lines.extend(f"- {item}" for item in acceptance)
    else:
        lines.append("(none provided)")
    original = "\n".join(lines)
    original_bytes = len(original.encode("utf-8"))
    text, truncated = _truncate_utf8(original, max_bytes, _PROMPT_MARKER)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    return BoundedPrompt(
        text=text,
        digest=digest,
        max_bytes=max_bytes,
        original_bytes=original_bytes,
        truncated=truncated,
    )


__all__ = [
    "DEFAULT_MAX_PROMPT_BYTES",
    "PROMPT_SCHEMA",
    "PromptResources",
    "TaskPromptInput",
    "build_task_prompt",
    "format_execution_context",
]
