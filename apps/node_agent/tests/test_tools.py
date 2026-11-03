"""Tool registry: allow-list, fixed argv, missing executable, timeout, cap."""

from __future__ import annotations

from pathlib import Path

import pytest

from noahsark_node.protocol import CommandMessage
from noahsark_node.tools import (
    ERROR_TOOL_TIMEOUT,
    ERROR_TOOL_UNAVAILABLE,
    ERROR_UNKNOWN_TOOL,
    MAX_OUTPUT_BYTES,
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    STATUS_TIMEOUT,
    InvalidToolArgsError,
    UnknownToolError,
    run_tool,
)


def _install(tmp_path: Path, body: str) -> dict[str, str]:
    directory = tmp_path / "usb-tree"
    directory.mkdir()
    executable = directory / "usbTree-cli.cmd"
    executable.write_text(body, encoding="utf-8")
    executable.chmod(0o755)
    return {"NOAHSARK_USBTREE_DIR": str(directory)}


def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(UnknownToolError):
        run_tool("shell.exec", {})


def test_arguments_are_rejected_for_usb_scan() -> None:
    with pytest.raises(InvalidToolArgsError):
        run_tool("usb.scan", {"command": "dir"})


def test_missing_executable_reports_tool_unavailable(tmp_path: Path) -> None:
    env = {"NOAHSARK_USBTREE_DIR": str(tmp_path / "missing")}

    result = run_tool("usb.scan", {}, env=env)

    assert result.status == STATUS_FAILED
    assert result.error_code == ERROR_TOOL_UNAVAILABLE
    assert result.exit_code is None
    assert "not found" in (result.stderr or "")


def test_usb_scan_runs_fixed_csv_arguments(tmp_path: Path) -> None:
    env = _install(
        tmp_path,
        "#!/bin/sh\n"
        "printf 'Bus 001 Device 002: ID 1a86:55d4 CH344\\nListenAI TCL003\\n'\n"
        'printf \'%s\\n\' "$*" >&2\n',
    )

    result = run_tool("usb.scan", {}, env=env)

    assert result.status == STATUS_SUCCEEDED
    assert result.exit_code == 0
    assert "CH344" in (result.stdout or "")
    assert "ListenAI" in (result.stdout or "")
    assert (result.stderr or "").strip() == "--all --format csv"
    assert result.truncated is False


def test_output_past_cap_is_truncated(tmp_path: Path) -> None:
    env = _install(
        tmp_path,
        "#!/bin/sh\nhead -c 1000050 /dev/zero | tr '\\0' 'a'\n",
    )

    result = run_tool("usb.scan", {}, env=env)

    assert result.status == STATUS_SUCCEEDED
    assert result.truncated is True
    assert len((result.stdout or "").encode("utf-8")) == MAX_OUTPUT_BYTES


def test_timeout_is_reported_as_timeout(tmp_path: Path) -> None:
    env = _install(tmp_path, "#!/bin/sh\nsleep 5\n")

    result = run_tool("usb.scan", {}, timeout_seconds=1, env=env)

    assert result.status == STATUS_TIMEOUT
    assert result.error_code == ERROR_TOOL_TIMEOUT


def test_command_message_parses_and_rejects_bad_args() -> None:
    message = CommandMessage.from_mapping(
        {
            "kind": "command",
            "command_id": "cmd-1",
            "tool_id": "usb.scan",
            "args": {},
            "timeout_seconds": 30,
        }
    )
    assert message.command_id == "cmd-1"
    assert message.tool_id == "usb.scan"
    assert message.timeout_seconds == 30

    with pytest.raises(ValueError):
        CommandMessage.from_mapping(
            {"command_id": "cmd-2", "tool_id": "usb.scan", "args": ["--all"]}
        )


def test_rejected_result_carries_the_error_code() -> None:
    from noahsark_node.tools import rejected_result

    result = rejected_result("shell.exec", ERROR_UNKNOWN_TOOL, "unknown tool")

    assert result.status == STATUS_FAILED
    assert result.error_code == ERROR_UNKNOWN_TOOL
    assert result.exit_code is None
