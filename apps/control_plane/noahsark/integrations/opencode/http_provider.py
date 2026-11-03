"""Concrete OpenCode 1.19.4 HTTP provider.

Endpoints (verified locally):

* ``POST /session``
* ``POST /session/{id}/prompt_async`` (``204`` = accepted, not complete)
* ``GET /session/status``
* ``GET /session/{id}/message``
* ``POST /session/{id}/abort``
* ``DELETE /session/{id}`` (``404`` means already deleted)

The client has an explicit timeout, optional basic auth, redirects disabled,
environment proxies ignored and ``retries=0``.  The provider makes exactly one
attempt per method call and never converts ``204`` into a completion claim.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from .config import (
    BasicAuthCredentials,
    HTTPProviderConfig,
    ModelSelection,
    TimeoutConfig,
)
from .errors import (
    OpenCodeHTTPError,
    OpenCodeNotFoundError,
    OpenCodeProtocolError,
    OpenCodeTransportError,
    OpenCodeValidationError,
)
from .protocol import (
    BoundedPrompt,
    OpenCodeProvider,
    OpenCodeSession,
    PromptReceipt,
    SessionMessages,
    SessionObservation,
    SessionState,
    SessionStatus,
    SessionTurn,
    observe_from,
)
from .wire import (
    AbortWire,
    MessageEnvelopeWire,
    MessageRequestWire,
    MessagesWire,
    PromptModelWire,
    PromptRequestWire,
    SessionCreateModelWire,
    SessionCreateWire,
    SessionWire,
    StatusMapWire,
    TextPartInputWire,
)
from .wire_mapping import message_from_wire, parse_wire, status_from_wire

_HTTP_METHODS = frozenset({"GET", "POST", "DELETE"})
_HTTP_STATUS_OK = 200
_HTTP_STATUS_NO_CONTENT = 204


def _ensure_success(response: httpx.Response, *, path: str) -> None:
    status = response.status_code
    if 200 <= status < 300:
        return
    if status in (301, 302, 303, 307, 308):
        raise OpenCodeHTTPError(
            status_code=status,
            code="OPENCODE_REDIRECT_REFUSED",
            message="OpenCode returned a redirect; redirects are not followed",
            retryable=False,
            details={"path": path},
        )
    if status == 404:
        raise OpenCodeNotFoundError(details={"path": path})
    if status == 400:
        code, retryable = "OPENCODE_BAD_REQUEST", False
    elif status in (401, 403):
        code, retryable = "OPENCODE_UNAUTHORIZED", False
    elif status == 429:
        code, retryable = "OPENCODE_RATE_LIMITED", True
    elif 400 <= status < 500:
        code, retryable = "OPENCODE_CLIENT_ERROR", status == 408
    else:
        code, retryable = "OPENCODE_SERVER_ERROR", True
    raise OpenCodeHTTPError(
        status_code=status,
        code=code,
        message=f"OpenCode returned HTTP {status}",
        retryable=retryable,
        details={"path": path},
    )


def _require_status(response: httpx.Response, *, expected: int, path: str) -> None:
    if response.status_code != expected:
        raise OpenCodeProtocolError(
            "OpenCode returned an unexpected success status",
            details={
                "path": path,
                "expected_status": expected,
                "status_code": response.status_code,
            },
        )


def _session_path(session_id: str, suffix: str = "") -> str:
    if not session_id.strip():
        raise OpenCodeValidationError("session_id must not be empty")
    return f"session/{quote(session_id, safe='')}{suffix}"


class OpenCodeHTTPProvider:
    """Single-attempt HTTP implementation of :class:`OpenCodeProvider`."""

    def __init__(
        self,
        config: HTTPProviderConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        auth: httpx.Auth | None = None
        if config.basic_auth is not None:
            auth = httpx.BasicAuth(
                config.basic_auth.username,
                config.basic_auth.password,
            )
        self._client = httpx.AsyncClient(
            base_url=config.base_url + "/",
            timeout=config.timeout.as_httpx(),
            auth=auth,
            transport=(
                transport
                if transport is not None
                else httpx.AsyncHTTPTransport(retries=0)
            ),
            follow_redirects=False,
            trust_env=False,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: BaseModel | None = None,
    ) -> httpx.Response:
        if method not in _HTTP_METHODS:
            raise OpenCodeValidationError(
                "Unsupported OpenCode HTTP method",
                details={"method": method},
            )
        headers = {"accept": "application/json"}
        content: bytes | None = None
        if payload is not None:
            content = payload.model_dump_json(
                by_alias=True, exclude_none=True
            ).encode("utf-8")
            headers["content-type"] = "application/json"
        try:
            return await self._client.request(
                method, path, content=content, headers=headers
            )
        except httpx.TransportError as exc:
            raise OpenCodeTransportError(
                "OpenCode request failed before a response was received",
                details={"method": method, "path": path},
            ) from exc

    def _resolve_model(self, model: ModelSelection | None) -> ModelSelection:
        """Per-call selection wins; the configured model is the only fallback."""

        selection = model if model is not None else self._config.model
        if selection is None:
            raise OpenCodeValidationError(
                "OpenCode model selection is not configured",
                code="OPENCODE_MODEL_REQUIRED",
            )
        return selection

    async def create_session(
        self,
        *,
        title: str,
        model: ModelSelection | None = None,
    ) -> OpenCodeSession:
        selection = self._resolve_model(model)
        clean_title = title.strip()
        if not clean_title:
            raise OpenCodeValidationError("session title must not be empty")
        path = "session"
        response = await self._request(
            "POST",
            path,
            payload=SessionCreateWire(
                title=clean_title,
                model=SessionCreateModelWire(
                    id=selection.model_id,
                    providerID=selection.provider_id,
                ),
            ),
        )
        _ensure_success(response, path=path)
        wire = parse_wire(SessionWire, response.content, path=path)
        if not wire.id.strip():
            raise OpenCodeProtocolError(
                "OpenCode session response has no id",
                details={"path": path},
            )
        return OpenCodeSession(session_id=wire.id, title=wire.title)

    async def send_prompt(
        self,
        session_id: str,
        prompt: BoundedPrompt,
        *,
        model: ModelSelection | None = None,
    ) -> PromptReceipt:
        selection = self._resolve_model(model)
        if not prompt.text.strip():
            raise OpenCodeValidationError("prompt text must not be empty")
        if prompt.byte_length > prompt.max_bytes:
            raise OpenCodeValidationError(
                "prompt exceeds its declared byte cap",
                details={
                    "byte_length": prompt.byte_length,
                    "max_bytes": prompt.max_bytes,
                },
            )
        path = _session_path(session_id, "/prompt_async")
        payload = PromptRequestWire(
            parts=[TextPartInputWire(text=prompt.text)],
            model=PromptModelWire(
                providerID=selection.provider_id,
                modelID=selection.model_id,
            ),
        )
        response = await self._request("POST", path, payload=payload)
        _ensure_success(response, path=path)
        _require_status(response, expected=_HTTP_STATUS_NO_CONTENT, path=path)
        return PromptReceipt(
            session_id=session_id,
            prompt_digest=prompt.digest,
            http_status=response.status_code,
            accepted=True,
            completion_claimed=False,
        )

    async def send_message(
        self,
        session_id: str,
        text: str,
        *,
        model: ModelSelection | None = None,
    ) -> SessionTurn:
        """Send one follow-up turn and return the completed assistant reply.

        This uses the blocking ``POST /session/{id}/message`` endpoint: a 2xx
        response is a finished turn, unlike ``prompt_async``'s 204 acceptance.
        The pinned model is sent explicitly so the runtime can never substitute
        its default model.
        """

        selection = self._resolve_model(model)
        if not text.strip():
            raise OpenCodeValidationError("message text must not be empty")
        path = _session_path(session_id, "/message")
        payload = MessageRequestWire(
            parts=[TextPartInputWire(text=text)],
            model=PromptModelWire(
                providerID=selection.provider_id,
                modelID=selection.model_id,
            ),
        )
        response = await self._request("POST", path, payload=payload)
        _ensure_success(response, path=path)
        _require_status(response, expected=_HTTP_STATUS_OK, path=path)
        wire = parse_wire(MessageEnvelopeWire, response.content, path=path)
        view = message_from_wire(wire)
        if not view.is_assistant:
            raise OpenCodeProtocolError(
                "OpenCode message endpoint returned a non-assistant message",
                details={"path": path},
            )
        return SessionTurn(
            session_id=view.session_id or session_id,
            message_id=view.message_id,
            role=view.role,
            text=view.visible_text,
            created_at_ms=view.created_at_ms,
            completed_at_ms=view.completed_at_ms,
        )

    async def session_status(self, session_id: str) -> SessionStatus:
        _session_path(session_id)
        path = "session/status"
        response = await self._request("GET", path)
        _ensure_success(response, path=path)
        wire = parse_wire(StatusMapWire, response.content, path=path)
        status_wire = wire.root.get(session_id)
        if status_wire is None:
            # OpenCode omits idle sessions from the status map; absence means
            # the session is not busy/retrying, i.e. idle.
            return SessionStatus(state=SessionState.IDLE)
        return status_from_wire(status_wire)

    async def session_messages(self, session_id: str) -> SessionMessages:
        path = _session_path(session_id, "/message")
        response = await self._request("GET", path)
        _ensure_success(response, path=path)
        wire = parse_wire(MessagesWire, response.content, path=path)
        return SessionMessages(
            session_id=session_id,
            messages=tuple(message_from_wire(item) for item in wire.root),
        )

    async def abort_session(self, session_id: str) -> bool:
        path = _session_path(session_id, "/abort")
        response = await self._request("POST", path)
        _ensure_success(response, path=path)
        _require_status(response, expected=_HTTP_STATUS_OK, path=path)
        wire = parse_wire(AbortWire, response.content, path=path)
        return wire.root

    async def delete_session(self, session_id: str) -> bool:
        """Delete the remote session; a 404 is idempotent success.

        OpenCode answers ``200`` with a bare JSON boolean.  A missing session is
        not an error for a delete: the desired end state already holds, so the
        provider reports success instead of raising.
        """

        path = _session_path(session_id)
        response = await self._request("DELETE", path)
        try:
            _ensure_success(response, path=path)
        except OpenCodeNotFoundError:
            return True
        _require_status(response, expected=_HTTP_STATUS_OK, path=path)
        wire = parse_wire(AbortWire, response.content, path=path)
        return wire.root

    async def observe(self, session_id: str) -> SessionObservation:
        # Messages first, then status: an idle status observed after the
        # message read cannot predate the message snapshot it describes.
        messages = await self.session_messages(session_id)
        status = await self.session_status(session_id)
        return observe_from(status, messages)


__all__ = [
    "BasicAuthCredentials",
    "HTTPProviderConfig",
    "ModelSelection",
    "OpenCodeHTTPProvider",
    "OpenCodeProvider",
    "TimeoutConfig",
]
