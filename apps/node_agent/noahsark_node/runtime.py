"""Composition root for the development Node Agent."""

from __future__ import annotations

from .agent import NodeAgent
from .cleanup import CleanupManager
from .client import ControlPlaneClient
from .config import NodeAgentSettings
from .executor import SimulatedExecutor
from .spool import Spool
from .verifier import (
    ArtifactVerifier,
    HmacSignatureVerifier,
    RejectingSignatureVerifier,
    SignatureVerifier,
)


def build_signature_verifier(settings: NodeAgentSettings) -> SignatureVerifier:
    if settings.signature_secret:
        return HmacSignatureVerifier(settings.signature_secret.encode("utf-8"))
    return RejectingSignatureVerifier()


def build_agent(settings: NodeAgentSettings) -> NodeAgent:
    verifier = ArtifactVerifier(build_signature_verifier(settings))
    client = ControlPlaneClient(
        settings.control_plane_url,
        settings.node_token,
        settings.node_id,
        long_poll_timeout=settings.poll_timeout_seconds,
    )
    spool = Spool(settings.spool_path)
    executor = SimulatedExecutor(verifier)
    cleanup = CleanupManager(settings.node_id)
    return NodeAgent(
        client=client,
        spool=spool,
        verifier=verifier,
        executor=executor,
        cleanup=cleanup,
        node_id=settings.node_id,
    )
