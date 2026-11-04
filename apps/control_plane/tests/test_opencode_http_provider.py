"""HTTP provider contract against the verified OpenCode 1.19.4 endpoints."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import Callable

import httpx
import pytest
from noahsark.integrations.opencode.errors import (
    OpenCodeConfigError,
    OpenCodeHTTPError,
    OpenCodeNotFoundError,
    OpenCodeProtocolError,
    OpenCodeTransportError,
)
from noahsark.integrations.opencode.http_provider import (
    BasicAuthCredentials,
    HTTPProviderConfig,
    ModelSelection,
    OpenCodeHTTPProvider,
    TimeoutConfig,
)
from noahsark.integrations.opencode.prompt import TaskPromptInput, build_task_prompt
from noahsark.integrations.opencode.protocol import (
    OpenCodeSession,
    PromptReceipt,
    SessionMessages,
    SessionObservation,
    SessionState,
    SessionStatus,
    SessionTurn,
)
from noahsark.integrations.opencode.wire import (
    PromptRequestWire,
    SessionCreateWire,
)

Handler = Callable[[httpx.Request], httpx.Response]
MODEL = ModelSelection(
    provider_id="listenai",
    model_id="deepseek-v4.1-flash-expires-on-0910",
)
PROMPT = build_task_prompt(
    TaskPromptInput(
        task_id="task-001",
        title="MVP",
        instructions="Implement the provider.",
        acceptance=("typed",),
    )
)


def _provider(
    handler: Handler,
    *,
    auth: BasicAuthCredentials | None = None,
    timeout: TimeoutConfig | None = None,
) -> OpenCodeHTTPProvider:
    config = HTTPProviderConfig(
        base_url="http://127.0.0.1:4096",
        model=MODEL,
        basic_auth=auth,
        timeout=timeout or TimeoutConfig(),
    )
    return OpenCodeHTTPProvider(config, transport=httpx.MockTransport(handler))


def _message(
    message_id: str,
    role: str,
    *,
    created: int,
    completed: int | None,
    text: str | None,
    error: dict[str, object] | None = None,
    synthetic: bool = False,
) -> dict[str, object]:
    parts: list[dict[str, object]] = [
        {
            "id": f"{message_id}-part",
            "type": "text" if text is not None else "tool",
            "text": text,
            "synthetic": synthetic,
        }
    ]
    return {
        "info": {
            "id": message_id,
            "sessionID": "oc-s1",
            "role": role,
            "time": {"created": created, "completed": completed},
            "error": error,
            "finish": "stop" if completed is not None and error is None else None,
        },
        "parts": parts,
    }


def test_http_provider_covers_verified_endpoints() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        key = (request.method, request.url.path)
        if key == ("POST", "/session"):
            body = SessionCreateWire.model_validate_json(request.content)
            assert body.title == "MVP"
            return httpx.Response(
                200,
                json={"id": "oc-s1", "title": "MVP", "version": "1.19.4"},
            )
        if key == ("POST", "/session/oc-s1/prompt_async"):
            payload = PromptRequestWire.model_validate_json(request.content)
            assert len(payload.parts) == 1
            assert payload.parts[0].text == PROMPT.text
            return httpx.Response(204)
        if key == ("GET", "/session/status"):
            return httpx.Response(200, json={"oc-s1": {"type": "idle"}})
        if key == ("GET", "/session/oc-s1/message"):
            return httpx.Response(
                200,
                json=[
                    _message(
                        "m1",
                        "user",
                        created=1,
                        completed=1,
                        text="do it",
                    ),
                    _message(
                        "m2",
                        "assistant",
                        created=2,
                        completed=3,
                        text="done",
                    ),
                ],
            )
        if key == ("POST", "/session/oc-s1/abort"):
            return httpx.Response(200, json=True)
        raise AssertionError(f"unexpected request {key}")

    auth = BasicAuthCredentials("operator", "secret")
    timeout = TimeoutConfig(connect=1.0, read=2.0, write=3.0, pool=4.0)
    provider = _provider(handler, auth=auth, timeout=timeout)

    async def scenario() -> tuple[
        OpenCodeSession,
        PromptReceipt,
        SessionStatus,
        SessionMessages,
        SessionObservation,
        bool,
    ]:
        try:
            session = await provider.create_session(title="MVP")
            receipt = await provider.send_prompt(session.session_id, PROMPT)
            status = await provider.session_status(session.session_id)
            messages = await provider.session_messages(session.session_id)
            observation = await provider.observe(session.session_id)
            aborted = await provider.abort_session(session.session_id)
            return session, receipt, status, messages, observation, aborted
        finally:
            await provider.aclose()

    session, receipt, status, messages, observation, aborted = asyncio.run(
        scenario()
    )

    assert session.session_id == "oc-s1"
    assert receipt.accepted is True
    assert receipt.http_status == 204
    assert receipt.completion_claimed is False
    assert receipt.prompt_digest == PROMPT.digest
    assert status.state is SessionState.IDLE
    assert [message.message_id for message in messages.messages] == ["m1", "m2"]
    assert messages.messages[1].visible_text == "done"
    assert messages.messages[1].completed is True
    assert observation.is_complete is True
    assert aborted is True

    expected_auth = "Basic " + base64.b64encode(b"operator:secret").decode()
    for request in requests:
        assert request.headers["authorization"] == expected_auth
        timeout_extension = request.extensions.get("timeout")
        assert timeout_extension == {
            "connect": 1.0,
            "read": 2.0,
            "write": 3.0,
            "pool": 4.0,
        }

    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/session"),
        ("POST", "/session/oc-s1/prompt_async"),
        ("GET", "/session/status"),
        ("GET", "/session/oc-s1/message"),
        ("GET", "/session/oc-s1/message"),
        ("GET", "/session/status"),
        ("POST", "/session/oc-s1/abort"),
    ]


def test_prompt_async_204_is_acceptance_not_completion() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/session/oc-s1/prompt_async":
            return httpx.Response(204)
        if request.url.path == "/session/status":
            return httpx.Response(200, json={"oc-s1": {"type": "busy"}})
        if request.url.path == "/session/oc-s1/message":
            return httpx.Response(
                200,
                json=[
                    _message(
                        "m2",
                        "assistant",
                        created=2,
                        completed=None,
                        text="still working",
                    )
                ],
            )
        raise AssertionError("unexpected path")

    provider = _provider(handler)

    async def scenario() -> tuple[PromptReceipt, SessionObservation]:
        try:
            receipt = await provider.send_prompt("oc-s1", PROMPT)
            observation = await provider.observe("oc-s1")
            return receipt, observation
        finally:
            await provider.aclose()

    receipt, observation = asyncio.run(scenario())

    assert receipt.completion_claimed is False
    assert observation.is_complete is False
    assert observation.completion_blockers == (
        "session_not_idle",
        "assistant_message_incomplete",
    )


def test_observation_requires_idle_completed_error_free_output() -> None:
    statuses: dict[str, object] = {
        "s-busy": {"type": "busy"},
        "s-incomplete": {"type": "idle"},
        "s-error": {"type": "idle"},
        "s-empty": {"type": "idle"},
        "s-ok": {"type": "idle"},
    }
    messages: dict[str, object] = {
        "s-busy": [
            _message("b1", "assistant", created=1, completed=2, text="done")
        ],
        "s-incomplete": [
            _message("i1", "assistant", created=1, completed=None, text="partial")
        ],
        "s-error": [
            _message(
                "e1",
                "assistant",
                created=1,
                completed=2,
                text="aborted",
                error={
                    "name": "MessageAbortedError",
                    "data": {"message": "aborted by user"},
                },
            )
        ],
        "s-empty": [
            _message("z1", "assistant", created=1, completed=2, text="")
        ],
        "s-ok": [
            _message("k1", "assistant", created=1, completed=2, text="done")
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/session/status":
            return httpx.Response(200, json=statuses)
        session_id = request.url.path.split("/")[2]
        return httpx.Response(200, json=messages[session_id])

    provider = _provider(handler)

    async def scenario() -> dict[str, tuple[str, ...]]:
        try:
            return {
                session_id: (await provider.observe(session_id)).completion_blockers
                for session_id in statuses
            }
        finally:
            await provider.aclose()

    blockers = asyncio.run(scenario())

    assert blockers["s-busy"] == ("session_not_idle",)
    assert blockers["s-incomplete"] == ("assistant_message_incomplete",)
    assert blockers["s-error"] == ("assistant_message_error",)
    assert blockers["s-empty"] == ("assistant_output_empty",)
    assert blockers["s-ok"] == ()


def test_status_variants_and_retry_redaction() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/session/status"
        return httpx.Response(
            200,
            json={
                "s-idle": {"type": "idle"},
                "s-busy": {"type": "busy"},
                "s-retry": {
                    "type": "retry",
                    "attempt": 3,
                    "message": "auth failed Bearer abcdefghijklmnop from /home/alice/x",
                    "next": 1234,
                },
            },
        )

    provider = _provider(handler)

    async def scenario() -> tuple[
        SessionStatus, SessionStatus, SessionStatus, SessionStatus
    ]:
        try:
            return (
                await provider.session_status("s-idle"),
                await provider.session_status("s-busy"),
                await provider.session_status("s-retry"),
                await provider.session_status("s-missing"),
            )
        finally:
            await provider.aclose()

    idle, busy, retry, missing = asyncio.run(scenario())

    assert idle.state is SessionState.IDLE
    assert busy.state is SessionState.BUSY
    assert retry.state is SessionState.RETRY
    assert retry.retry_attempt == 3
    assert retry.retry_next_ms == 1234
    assert "abcdefghijklmnop" not in (retry.retry_message or "")
    assert "/home/alice/x" not in (retry.retry_message or "")
    # OpenCode omits idle sessions; an absent entry means idle, not unknown.
    assert missing.state is SessionState.IDLE


def test_http_errors_are_typed_and_not_retried() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.url.path == "/session":
            return httpx.Response(500, json={"error": "boom"})
        return httpx.Response(404, json={"error": "missing"})

    provider = _provider(handler)

    async def scenario() -> tuple[int, int]:
        counts = [0, 0]
        try:
            try:
                await provider.create_session(title="MVP")
            except OpenCodeHTTPError as exc:
                counts[0] = exc.status_code
                assert exc.retryable is True
            try:
                await provider.session_messages("missing")
            except OpenCodeNotFoundError as exc:
                counts[1] = exc.status_code
            return counts[0], counts[1]
        finally:
            await provider.aclose()

    statuses = asyncio.run(scenario())

    assert statuses == (500, 404)
    assert calls == ["POST", "GET"]


def test_transport_error_is_typed_and_not_retried() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        raise httpx.ConnectError("refused", request=request)

    provider = _provider(handler)

    async def scenario() -> OpenCodeTransportError:
        try:
            try:
                await provider.create_session(title="MVP")
            except OpenCodeTransportError as exc:
                return exc
            raise AssertionError("expected transport error")
        finally:
            await provider.aclose()

    error = asyncio.run(scenario())

    assert error.retryable is True
    assert calls == ["POST"]


def test_malformed_response_is_protocol_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": 123})

    provider = _provider(handler)

    async def scenario() -> None:
        try:
            await provider.create_session(title="MVP")
        finally:
            await provider.aclose()

    with pytest.raises(OpenCodeProtocolError):
        asyncio.run(scenario())


def test_unexpected_prompt_async_status_is_protocol_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps({"ok": True}))

    provider = _provider(handler)

    async def scenario() -> None:
        try:
            await provider.send_prompt("oc-s1", PROMPT)
        finally:
            await provider.aclose()

    with pytest.raises(OpenCodeProtocolError):
        asyncio.run(scenario())


def test_config_validation_rejects_unsafe_values() -> None:
    with pytest.raises(OpenCodeConfigError):
        HTTPProviderConfig(base_url="ftp://opencode.local", model=MODEL)
    with pytest.raises(OpenCodeConfigError):
        HTTPProviderConfig(base_url="http://user:pass@opencode.local", model=MODEL)
    with pytest.raises(OpenCodeConfigError):
        HTTPProviderConfig(
            base_url="http://opencode.local?token=secret", model=MODEL
        )
    with pytest.raises(OpenCodeConfigError):
        HTTPProviderConfig(base_url="", model=MODEL)
    with pytest.raises(OpenCodeConfigError):
        TimeoutConfig(connect=0)
    with pytest.raises(OpenCodeConfigError):
        BasicAuthCredentials(" ", "secret")
    with pytest.raises(OpenCodeConfigError):
        ModelSelection(provider_id="listenai", model_id="   ")
    with pytest.raises(OpenCodeConfigError):
        ModelSelection(provider_id="", model_id="deepseek-v4.1-flash-expires-on-0910")


def test_send_message_posts_pinned_model_and_parses_assistant_reply() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert (request.method, request.url.path) == (
            "POST",
            "/session/oc-s1/message",
        )
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=_message(
                "m3",
                "assistant",
                created=10,
                completed=12,
                text="4",
            ),
        )

    provider = _provider(handler)

    async def scenario() -> SessionTurn:
        try:
            return await provider.send_message("oc-s1", "What is 2+2?")
        finally:
            await provider.aclose()

    turn = asyncio.run(scenario())

    assert turn.session_id == "oc-s1"
    assert turn.message_id == "m3"
    assert turn.role.value == "assistant"
    assert turn.text == "4"
    assert turn.created_at_ms == 10
    assert turn.completed_at_ms == 12
    assert bodies == [
        {
            "model": {
                "providerID": MODEL.provider_id,
                "modelID": MODEL.model_id,
            },
            "parts": [{"type": "text", "text": "What is 2+2?"}],
        }
    ]


def test_send_message_non_success_is_typed_and_not_retried() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(500, json={"error": "boom"})

    provider = _provider(handler)

    async def scenario() -> OpenCodeHTTPError:
        try:
            try:
                await provider.send_message("oc-s1", "hello")
            except OpenCodeHTTPError as exc:
                return exc
            raise AssertionError("expected HTTP error")
        finally:
            await provider.aclose()

    error = asyncio.run(scenario())

    assert error.status_code == 500
    assert error.retryable is True
    assert calls == ["POST"]


def test_send_message_rejects_non_assistant_reply() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json=_message("m3", "user", created=10, completed=10, text="echo"),
        )

    provider = _provider(handler)

    async def scenario() -> None:
        try:
            await provider.send_message("oc-s1", "hello")
        finally:
            await provider.aclose()

    with pytest.raises(OpenCodeProtocolError):
        asyncio.run(scenario())


def test_delete_session_uses_delete_endpoint_and_treats_404_as_success() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == "/session/oc-live":
            return httpx.Response(200, json=True)
        if request.url.path == "/session/oc-gone":
            return httpx.Response(404, json={"error": "missing"})
        return httpx.Response(503, json={"error": "unavailable"})

    provider = _provider(handler)

    async def scenario() -> tuple[bool, bool, int | None]:
        try:
            live = await provider.delete_session("oc-live")
            gone = await provider.delete_session("oc-gone")
            status: int | None = None
            try:
                await provider.delete_session("oc-error")
            except OpenCodeHTTPError as exc:
                status = exc.status_code
            return live, gone, status
        finally:
            await provider.aclose()

    live, gone, status = asyncio.run(scenario())

    assert live is True
    assert gone is True
    assert status == 503
    assert calls == [
        ("DELETE", "/session/oc-live"),
        ("DELETE", "/session/oc-gone"),
        ("DELETE", "/session/oc-error"),
    ]


def test_stream_events_parses_sse_and_filters_session() -> None:
    frames = [
        {"type": "message.part.delta", "properties": {"sessionID": "oc-s1", "delta": "Hel"}},
        {"type": "message.part.delta", "properties": {"sessionID": "other", "delta": "no"}},
        {"type": "session.status", "properties": {"sessionID": "oc-s1", "status": {"type": "busy"}}},
    ]
    body = "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        assert (request.method, request.url.path) == ("GET", "/event")
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    provider = _provider(handler)

    async def scenario() -> list[dict[str, object]]:
        try:
            return [event async for event in provider.stream_events("oc-s1")]
        finally:
            await provider.aclose()

    events = asyncio.run(scenario())
    assert [event["type"] for event in events] == ["message.part.delta", "session.status"]
    assert events[0]["properties"]["delta"] == "Hel"
