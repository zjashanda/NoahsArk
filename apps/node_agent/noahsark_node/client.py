"""Outbound-only control-plane client.

There is deliberately no server, socket bind, or inbound listener in this module.
The node can only reach the control plane; the control plane cannot connect in.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import AGENT_VERSION
from .protocol import (
    PROTOCOL_VERSION,
    CommandMessage,
    JobMessage,
    LeaseTracker,
    StopSignal,
)
from .spool import UploadAck

JsonDict = dict[str, Any]


class ControlPlaneUnavailable(RuntimeError):
    """The control plane cannot be reached; facts stay in the local spool."""


class ControlPlaneRejected(RuntimeError):
    """The control plane rejected a request for a non-retryable reason."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True, slots=True)
class PollMessage:
    kind: str
    message_id: str
    payload: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> PollMessage:
        kind = str(raw.get("kind", ""))
        if kind == "stop":
            payload = raw.get("signal", raw)
        elif kind == "job":
            payload = raw.get("job", raw)
        elif kind == "lease":
            payload = raw.get("lease", raw)
        elif kind == "command":
            payload = raw.get("command", raw)
        else:
            payload = raw
        if not isinstance(payload, Mapping):
            raise ControlPlaneRejected(f"poll message {kind} payload must be an object")
        message_id = str(raw.get("message_id", payload.get("message_id", "")))
        return cls(kind=kind, message_id=message_id, payload=payload)

    def stop_signal(self) -> StopSignal:
        return StopSignal.from_mapping(self.payload)

    def job(self) -> JobMessage:
        return JobMessage.from_mapping(self.payload)

    def command(self) -> CommandMessage:
        return CommandMessage.from_mapping(self.payload)


class ControlPlaneClient:
    def __init__(
        self,
        base_url: str,
        node_token: str,
        node_id: str,
        *,
        timeout: float = 10.0,
        long_poll_timeout: float = 25.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.node_token = node_token
        self.node_id = node_id
        self.timeout = timeout
        self.long_poll_timeout = long_poll_timeout

    def _request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> JsonDict:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.node_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": AGENT_VERSION,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout if timeout is None else timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            if exc.code >= 500 or exc.code in {408, 425, 429}:
                raise ControlPlaneUnavailable(
                    f"control plane returned retryable HTTP {exc.code}"
                ) from exc
            raise ControlPlaneRejected(
                f"control plane returned HTTP {exc.code}", status=exc.code
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ControlPlaneUnavailable(str(exc)) from exc
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ControlPlaneRejected("control plane returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise ControlPlaneRejected("control plane response must be an object")
        return parsed

    def register(self) -> JsonDict:
        return self._request(
            "POST",
            "/node/v1/register",
            {
                "node_id": self.node_id,
                "agent_version": AGENT_VERSION,
                "protocol_version": PROTOCOL_VERSION,
            },
        )

    def heartbeat(self, status: Mapping[str, Any]) -> JsonDict:
        return self._request(
            "POST",
            "/node/v1/heartbeat",
            {
                "node_id": self.node_id,
                "agent_version": AGENT_VERSION,
                "protocol_version": PROTOCOL_VERSION,
                "status": dict(status),
            },
        )

    def poll(self, lease: LeaseTracker) -> list[PollMessage]:
        response = self._request(
            "POST",
            "/node/v1/poll",
            {
                "node_id": self.node_id,
                "lease_id": lease.lease_id,
                "epoch": lease.epoch,
                "timeout_seconds": self.long_poll_timeout,
            },
            timeout=self.long_poll_timeout + 5.0,
        )
        raw_messages = response.get("messages", [])
        if not isinstance(raw_messages, list):
            raise ControlPlaneRejected("poll messages must be a list")
        messages: list[PollMessage] = []
        for item in raw_messages:
            if not isinstance(item, Mapping):
                raise ControlPlaneRejected("poll message must be an object")
            messages.append(PollMessage.from_mapping(item))
        return messages

    def post_command_result(self, result: Mapping[str, Any]) -> JsonDict:
        return self._request("POST", "/node/v1/command-results", result)

    def post_receipt(self, receipt: Mapping[str, Any]) -> UploadAck:
        message_id = str(receipt.get("message_id", ""))
        try:
            response = self._request("POST", "/node/v1/receipts", receipt)
        except ControlPlaneRejected as exc:
            if exc.status == 409:
                return UploadAck(message_id=message_id, duplicate=True)
            raise
        return UploadAck(message_id=message_id, duplicate=bool(response.get("duplicate", False)))

    def reconcile(
        self,
        lease: LeaseTracker,
        *,
        executed_job_ids: list[str] | None = None,
    ) -> JsonDict:
        return self._request(
            "POST",
            "/node/v1/reconcile",
            {
                "node_id": self.node_id,
                "lease_id": lease.lease_id,
                "epoch": lease.epoch,
                "executed_job_ids": list(executed_job_ids or []),
            },
        )
