"""Shared W8 integration harness.

This harness bridges the control-plane pure rules and the node-agent test
doubles. It is simulation-only: no sockets, sleeps, network calls, credentials,
real devices, or RPO/RTO claims.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "apps" / "control_plane", ROOT / "apps" / "node_agent"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _load_node_agent_helpers() -> ModuleType:
    """Load the node-agent conftest under a unique name to avoid collision."""

    path = ROOT / "apps" / "node_agent" / "tests" / "conftest.py"
    spec = importlib.util.spec_from_file_location("w8_node_agent_test_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load node-agent test helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


NODE_HELPERS = _load_node_agent_helpers()
FakeControlPlane = NODE_HELPERS.FakeControlPlane
SECRET = NODE_HELPERS.SECRET
HmacSignatureVerifier = NODE_HELPERS.HmacSignatureVerifier
job_item = NODE_HELPERS.job_item
lease_item = NODE_HELPERS.lease_item
receipt_statuses = NODE_HELPERS.receipt_statuses
stop_item = NODE_HELPERS.stop_item
flush_receipts = NODE_HELPERS.flush_receipts


@pytest.fixture
def signer() -> Any:
    return HmacSignatureVerifier(SECRET)


@pytest.fixture
def make_agent(tmp_path: Path) -> Iterator[Callable[..., Any]]:
    """Build simulated agents and always close their SQLite spools."""

    agents: list[Any] = []

    def _make(
        fake: Any,
        *,
        signer: Any = None,
        spool_name: str = "spool.sqlite3",
    ) -> Any:
        agent = NODE_HELPERS.build_agent(
            tmp_path, fake, signer=signer, spool_name=spool_name
        )
        agents.append(agent)
        return agent

    yield _make
    for agent in agents:
        agent.spool.close()
