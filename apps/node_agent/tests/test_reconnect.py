"""Reconnect behavior: an auth rejection forces a fresh registration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from conftest import FakeControlPlane, build_agent

from noahsark_node.client import ControlPlaneRejected


class RejectingControlPlane(FakeControlPlane):
    def __init__(self, *, status: int = 401) -> None:
        super().__init__()
        self.reject_status = status
        self.reject_heartbeat = False

    def heartbeat(self, status: Mapping[str, Any]) -> dict[str, Any]:
        if self.reject_heartbeat:
            raise ControlPlaneRejected("token rejected", status=self.reject_status)
        return super().heartbeat(status)


def test_auth_rejection_resets_registration_and_reconnects(tmp_path, signer) -> None:
    fake = RejectingControlPlane(status=401)
    agent = build_agent(tmp_path, fake, signer=signer)

    agent.run_cycle()
    assert fake.registered == 1

    fake.reject_heartbeat = True
    rejected = agent.run_cycle()
    assert "heartbeat_unavailable" in rejected.steps

    fake.reject_heartbeat = False
    recovered = agent.run_cycle()
    assert "register" in recovered.steps
    assert fake.registered == 2


def test_non_auth_rejection_keeps_registration(tmp_path, signer) -> None:
    fake = RejectingControlPlane(status=400)
    agent = build_agent(tmp_path, fake, signer=signer)

    agent.run_cycle()
    fake.reject_heartbeat = True
    agent.run_cycle()
    fake.reject_heartbeat = False
    recovered = agent.run_cycle()

    assert "register" not in recovered.steps
    assert fake.registered == 1
