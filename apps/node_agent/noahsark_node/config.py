"""Environment-driven settings for the development Node Agent."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEV_NODE_ID = "00000000-0000-4000-8000-000000000001"


@dataclass(frozen=True, slots=True)
class NodeAgentSettings:
    control_plane_url: str
    node_id: str
    node_token: str
    spool_path: Path
    artifact_cache_dir: Path
    poll_timeout_seconds: float = 25.0
    heartbeat_interval_seconds: float = 15.0
    signature_key_id: str = "simulator:hmac-dev"
    signature_secret: str = ""

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> NodeAgentSettings:
        source = os.environ if env is None else env
        return cls(
            control_plane_url=source.get(
                "NOAHSARK_CONTROL_PLANE_URL", "http://127.0.0.1:8000"
            ).rstrip("/"),
            node_id=source.get("NOAHSARK_NODE_ID", DEV_NODE_ID),
            node_token=source.get("NOAHSARK_NODE_TOKEN", "dev-node-token"),
            spool_path=Path(source.get("NOAHSARK_SPOOL_PATH", "./var/node_spool.sqlite3")),
            artifact_cache_dir=Path(source.get("NOAHSARK_ARTIFACT_CACHE_DIR", "./var/artifacts")),
            poll_timeout_seconds=float(
                source.get("NOAHSARK_POLL_TIMEOUT_SECONDS", "25")
            ),
            heartbeat_interval_seconds=float(
                source.get("NOAHSARK_HEARTBEAT_INTERVAL_SECONDS", "15")
            ),
            signature_key_id=source.get("NOAHSARK_SIGNATURE_KEY_ID", "simulator:hmac-dev"),
            signature_secret=source.get("NOAHSARK_SIGNATURE_SECRET", ""),
        )
