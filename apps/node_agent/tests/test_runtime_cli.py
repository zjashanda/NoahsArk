"""Runtime wiring, CLI entry point, and service wrappers that are safe on Linux."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from conftest import FakeControlPlane, build_agent

from noahsark_node import service
from noahsark_node.__main__ import main, run
from noahsark_node.config import NodeAgentSettings
from noahsark_node.runtime import build_agent as build_runtime_agent
from noahsark_node.runtime import build_signature_verifier
from noahsark_node.verifier import HmacSignatureVerifier, RejectingSignatureVerifier


def _settings(tmp_path: Path, **overrides: object) -> NodeAgentSettings:
    values: dict[str, object] = {
        "spool_path": tmp_path / "spool.sqlite3",
        "artifact_cache_dir": tmp_path / "artifacts",
        "signature_secret": "",
    }
    values.update(overrides)
    return NodeAgentSettings(
        control_plane_url="http://127.0.0.1:9",
        node_id="00000000-0000-4000-8000-000000000001",
        node_token="test-token",
        **values,  # type: ignore[arg-type]
    )


def test_build_signature_verifier_rejects_without_secret(tmp_path: Path) -> None:
    verifier = build_signature_verifier(_settings(tmp_path))
    assert isinstance(verifier, RejectingSignatureVerifier)
    assert verifier.verify("key", b"payload", "signature") is False


def test_build_signature_verifier_uses_hmac_when_configured(tmp_path: Path) -> None:
    verifier = build_signature_verifier(_settings(tmp_path, signature_secret="secret"))
    assert isinstance(verifier, HmacSignatureVerifier)
    signature = verifier.sign("key", b"payload")
    assert verifier.verify("key", b"payload", signature) is True


def test_runtime_builds_agent_and_closes_spool(tmp_path: Path) -> None:
    agent = build_runtime_agent(_settings(tmp_path))

    UUID(agent.node_boot_id)
    assert agent.lease.epoch == -1
    agent.spool.close()


def test_cli_run_once_executes_exactly_one_cycle(tmp_path: Path, capsys) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake)

    exit_code = run(agent, interval=0, once=True)

    assert exit_code == 0
    assert fake.poll_calls == 1
    assert capsys.readouterr().out.strip()


def test_cli_main_entry_point_is_callable() -> None:
    assert callable(main)


def test_service_refuses_to_run_without_pywin32() -> None:
    if service.PYWIN32_AVAILABLE:
        pytest.skip("pywin32 is present; this test covers the Linux fallback")
    with pytest.raises(RuntimeError, match="NSSM"):
        service.run_service()
    with pytest.raises(RuntimeError, match="NSSM"):
        service.install_service()


def test_service_constructor_is_safe_without_windows() -> None:
    if service.PYWIN32_AVAILABLE:
        pytest.skip("pywin32 is present; Windows SCM handles lifecycle")
    framework = service.NodeAgentWindowsService([])

    assert framework._stop_requested() is False


def test_cli_run_survives_a_cycle_exception(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake)
    calls: list[int] = []
    real_cycle = agent.run_cycle

    def flaky_cycle():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("transient failure")
        if len(calls) == 2:
            return real_cycle()
        raise KeyboardInterrupt

    monkeypatch.setattr(agent, "run_cycle", flaky_cycle)

    assert run(agent, interval=0, once=False) == 0
    assert len(calls) == 3
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.out
    assert fake.poll_calls == 1
