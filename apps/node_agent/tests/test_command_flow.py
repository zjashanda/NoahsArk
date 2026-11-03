"""Agent service loop: a polled command is executed and its result posted."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from conftest import FakeControlPlane, build_agent, command_item


def _install_script(tmp_path: Path) -> dict[str, str]:
    directory = tmp_path / "usb-tree"
    directory.mkdir()
    executable = directory / "usbTree-cli.cmd"
    executable.write_text(
        "#!/bin/sh\nprintf 'device_id,vid,pid\\nTCL003,1a86,55d4\\n'\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return {"NOAHSARK_USBTREE_DIR": str(directory)}


def test_polled_command_runs_and_posts_stdout(
    tmp_path, signer, monkeypatch
) -> None:
    env = _install_script(tmp_path)
    monkeypatch.setenv("NOAHSARK_USBTREE_DIR", env["NOAHSARK_USBTREE_DIR"])
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    command_id = str(uuid4())
    fake.polls.append([command_item(command_id=command_id)])

    report = agent.run_cycle()

    assert report.commands_executed == 1
    assert report.commands_failed == 0
    assert len(fake.command_results) == 1
    result = fake.command_results[0]
    assert result["command_id"] == command_id
    assert result["status"] == "SUCCEEDED"
    assert result["exit_code"] == 0
    assert "TCL003" in result["stdout"]
    assert result["truncated"] is False


def test_unknown_tool_is_reported_as_failed(tmp_path, signer, monkeypatch) -> None:
    monkeypatch.setenv("NOAHSARK_USBTREE_DIR", str(tmp_path / "missing"))
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    fake.polls.append([command_item(command_id=str(uuid4()), tool_id="shell.exec")])

    report = agent.run_cycle()

    assert report.commands_failed == 1
    assert fake.command_results[0]["status"] == "FAILED"
    assert fake.command_results[0]["error_code"] == "UNKNOWN_TOOL"
