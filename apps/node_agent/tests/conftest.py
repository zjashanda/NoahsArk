"""Shared W5 test helpers: a deterministic fake control plane and builders."""

from __future__ import annotations

import base64
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from noahsark_node.agent import NodeAgent  # noqa: E402
from noahsark_node.cleanup import CleanupManager  # noqa: E402
from noahsark_node.client import PollMessage  # noqa: E402
from noahsark_node.executor import SimulatedExecutor  # noqa: E402
from noahsark_node.spool import Spool, UploadAck  # noqa: E402
from noahsark_node.verifier import (  # noqa: E402
    ArtifactVerifier,
    HmacSignatureVerifier,
)

NODE_ID = "00000000-0000-4000-8000-000000000001"
SECRET = b"w5-test-secret"
KEY_ID = "simulator:hmac-dev"


class FakeControlPlane:
    """No sockets, no sleeps: deterministic stand-in for ControlPlaneClient."""

    def __init__(self) -> None:
        self.polls: list[list[dict[str, Any]]] = []
        self.uploaded_order: list[str] = []
        self.receipts: list[dict[str, Any]] = []
        self.actions: list[dict[str, Any]] = []
        self.command_results: list[dict[str, Any]] = []
        self.fail_uploads: list[Exception] = []
        self.reconciled = False
        self.registered = 0
        self.poll_calls = 0
        self.lease_mapping: dict[str, Any] | None = None

    def register(self) -> dict[str, Any]:
        self.registered += 1
        if self.lease_mapping is None:
            return {}
        return {"lease": dict(self.lease_mapping)}

    def heartbeat(self, status: Mapping[str, Any]) -> dict[str, Any]:
        return {}

    def poll(self, lease: object) -> list[PollMessage]:
        self.poll_calls += 1
        batch = self.polls.pop(0) if self.polls else []
        return [PollMessage.from_mapping(item) for item in batch]

    def post_command_result(self, result: Mapping[str, Any]) -> dict[str, Any]:
        self.command_results.append(dict(result))
        return {"ok": True}

    def post_receipt(self, receipt: Mapping[str, Any]) -> UploadAck:
        if self.fail_uploads:
            raise self.fail_uploads.pop(0)
        message_id = str(receipt.get("message_id", ""))
        if receipt.get("message_type") == "receipt":
            self.receipts.append(dict(receipt))
            self.uploaded_order.append("receipt")
        else:
            self.actions.append(dict(receipt))
            self.uploaded_order.append("stop_action")
        return UploadAck(message_id=message_id)

    def reconcile(
        self, lease: object, *, executed_job_ids: list[str] | None = None
    ) -> dict[str, Any]:
        return {"occupancy_reconciled": self.reconciled}


@pytest.fixture
def signer() -> HmacSignatureVerifier:
    return HmacSignatureVerifier(SECRET)


def build_agent(
    tmp_path: Path,
    fake: FakeControlPlane,
    *,
    signer: HmacSignatureVerifier | None = None,
    spool_name: str = "spool.sqlite3",
) -> NodeAgent:
    spool = Spool(tmp_path / spool_name)
    verifier = ArtifactVerifier(signer or HmacSignatureVerifier(SECRET))
    return NodeAgent(
        client=cast(Any, fake),
        spool=spool,
        verifier=verifier,
        executor=SimulatedExecutor(verifier),
        cleanup=CleanupManager(NODE_ID),
        node_id=NODE_ID,
    )


def make_artifact(
    content: bytes,
    signer: HmacSignatureVerifier,
    *,
    artifact_id: str | None = None,
    signature: str | None | object = ...,
    digest: str | None = None,
    size_bytes: int | None = None,
) -> dict[str, Any]:
    from noahsark_node.verifier import sha256_hex

    resolved_signature = (
        signer.sign(KEY_ID, content) if signature is ... else signature
    )
    return {
        "artifact_id": artifact_id or str(uuid4()),
        "uri": "sim://artifact/test",
        "sha256": digest or sha256_hex(content),
        "size_bytes": len(content) if size_bytes is None else size_bytes,
        "signature": resolved_signature,
        "key_id": KEY_ID,
        "content_b64": base64.b64encode(content).decode("ascii"),
    }


def job_item(
    *,
    job_id: str,
    lease_id: str,
    epoch: int,
    artifacts: list[dict[str, Any]] | None = None,
    attempt: int = 1,
) -> dict[str, Any]:
    return {
        "kind": "job",
        "message_id": str(uuid4()),
        "job": {
            "job_id": job_id,
            "lease_id": lease_id,
            "epoch": epoch,
            "attempt": attempt,
            "run_id": job_id,
            "artifacts": artifacts or [],
        },
    }


def stop_item(
    *,
    signal_id: str,
    job_id: str,
    lease_id: str,
    epoch: int,
    reason: str = "control_plane_stop",
) -> dict[str, Any]:
    return {
        "kind": "stop",
        "message_id": signal_id,
        "signal": {
            "signal_id": signal_id,
            "job_id": job_id,
            "lease_id": lease_id,
            "epoch": epoch,
            "reason": reason,
        },
    }


def lease_item(
    *, lease_id: str, epoch: int, job_id: str | None = None
) -> dict[str, Any]:
    return {
        "kind": "lease",
        "message_id": str(uuid4()),
        "lease": {"lease_id": lease_id, "epoch": epoch, "job_id": job_id},
    }


def command_item(
    *,
    command_id: str,
    tool_id: str = "usb.scan",
    args: dict[str, Any] | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    return {
        "kind": "command",
        "message_id": command_id,
        "command_id": command_id,
        "tool_id": tool_id,
        "args": args or {},
        "timeout_seconds": timeout_seconds,
    }


def receipt_statuses(
    fake: FakeControlPlane, job_id: str
) -> list[str]:
    return [
        str(receipt["payload"]["status"])
        for receipt in fake.receipts
        if receipt["payload"]["job_id"] == job_id
    ]


def flush_receipts(agent: NodeAgent, fake: FakeControlPlane) -> object:
    """Run an empty poll so receipts spooled during resume are uploaded.

    The agent deliberately uploads after polling so a STOP in the same poll is
    handled before any pending receipt. Job receipts therefore leave the spool
    on the next cycle.
    """
    fake.polls.append([])
    return agent.run_cycle()
