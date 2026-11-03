"""Regression tests for the supervisor's hard-pinned poor profile model.

The owner hard-pins the ``poor`` profile: ``listenai`` /
``deepseek-v4.1-flash-expires-on-0910``.  Every request must carry that pair,
and a missing or blank selection must fail closed instead of falling back.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest
from pydantic import ValidationError

from noahsark.integrations.opencode.config import ModelSelection
from noahsark.integrations.opencode.errors import (
    OpenCodeConfigError,
    OpenCodeValidationError,
)
from noahsark.integrations.opencode.fake import FakeOpenCodeProvider, FakeTurn
from noahsark.integrations.opencode.http_provider import (
    HTTPProviderConfig,
    OpenCodeHTTPProvider,
)
from noahsark.integrations.opencode.prompt import TaskPromptInput, build_task_prompt
from noahsark.supervisor.config import (
    POOR_PROFILE,
    SupervisorSettings,
    assert_poor_profile,
)

EXPECTED_PROVIDER_ID = "listenai"
EXPECTED_MODEL_ID = "deepseek-v4.1-flash-expires-on-0910"
MODEL = ModelSelection(
    provider_id=EXPECTED_PROVIDER_ID,
    model_id=EXPECTED_MODEL_ID,
)
PROMPT = build_task_prompt(
    TaskPromptInput(
        task_id="task-001",
        title="MVP",
        instructions="Implement the pinned model.",
    )
)
Handler = Callable[[httpx.Request], httpx.Response]


def _settings(**overrides: object) -> SupervisorSettings:
    return SupervisorSettings(_env_file=None, **overrides)


def _provider(
    handler: Handler, *, model: ModelSelection | None = MODEL
) -> OpenCodeHTTPProvider:
    return OpenCodeHTTPProvider(
        HTTPProviderConfig(
            base_url="http://127.0.0.1:4096",
            model=model,
        ),
        transport=httpx.MockTransport(handler),
    )


def test_supervisor_settings_default_to_poor_profile() -> None:
    settings = _settings(opencode_base_url="http://127.0.0.1:4096")

    assert settings.opencode_profile == POOR_PROFILE
    assert settings.opencode_provider_id == EXPECTED_PROVIDER_ID
    assert settings.opencode_model_id == EXPECTED_MODEL_ID
    assert settings.model_selection() == MODEL
    assert settings.provider_config().model == MODEL


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("opencode_provider_id", ""),
        ("opencode_provider_id", "   "),
        ("opencode_model_id", ""),
        ("opencode_model_id", " \t "),
        ("opencode_profile", ""),
        ("opencode_profile", "  "),
    ],
)
def test_enabled_supervisor_rejects_blank_model_or_profile(
    field: str, value: str
) -> None:
    with pytest.raises(ValidationError):
        _settings(
            enabled=True,
            database_url="postgresql://noahsark@127.0.0.1/noahsark",
            opencode_base_url="http://127.0.0.1:4096",
            **{field: value},
        )


def test_http_provider_always_sends_exact_model_on_create_and_prompt() -> None:
    bodies: dict[str, dict[str, object]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        if key == ("POST", "/session"):
            bodies["create"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"id": "oc-s1", "title": "MVP", "version": "1.19.4"},
            )
        if key == ("POST", "/session/oc-s1/prompt_async"):
            bodies["prompt"] = json.loads(request.content)
            return httpx.Response(204)
        raise AssertionError(f"unexpected request {key}")

    provider = _provider(handler)

    async def scenario() -> None:
        try:
            session = await provider.create_session(title="MVP")
            await provider.send_prompt(session.session_id, PROMPT)
        finally:
            await provider.aclose()

    asyncio.run(scenario())

    assert bodies["create"]["model"] == {
        "id": EXPECTED_MODEL_ID,
        "providerID": EXPECTED_PROVIDER_ID,
    }
    assert "modelID" not in bodies["create"]["model"]
    assert bodies["prompt"]["model"] == {
        "providerID": EXPECTED_PROVIDER_ID,
        "modelID": EXPECTED_MODEL_ID,
    }
    assert "id" not in bodies["prompt"]["model"]


def test_per_call_model_overrides_configured_model() -> None:
    bodies: dict[str, dict[str, object]] = {}
    override = ModelSelection(provider_id="other-provider", model_id="other-model")

    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        if key == ("POST", "/session"):
            bodies["create"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "oc-s1", "title": "MVP"})
        if key == ("POST", "/session/oc-s1/prompt_async"):
            bodies["prompt"] = json.loads(request.content)
            return httpx.Response(204)
        raise AssertionError(f"unexpected request {key}")

    provider = _provider(handler)

    async def scenario() -> None:
        try:
            session = await provider.create_session(title="MVP", model=override)
            await provider.send_prompt(session.session_id, PROMPT, model=override)
        finally:
            await provider.aclose()

    asyncio.run(scenario())

    assert bodies["create"]["model"] == {
        "id": "other-model",
        "providerID": "other-provider",
    }
    assert bodies["prompt"]["model"] == {
        "providerID": "other-provider",
        "modelID": "other-model",
    }


def test_missing_model_config_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"request must not be sent: {request.url}")

    provider = _provider(handler, model=None)

    async def scenario() -> None:
        try:
            with pytest.raises(OpenCodeValidationError):
                await provider.create_session(title="MVP")
            with pytest.raises(OpenCodeValidationError):
                await provider.send_prompt("oc-s1", PROMPT)
        finally:
            await provider.aclose()

    asyncio.run(scenario())


def test_blank_model_selection_fails_closed() -> None:
    with pytest.raises(OpenCodeConfigError):
        ModelSelection(provider_id="", model_id=EXPECTED_MODEL_ID)
    with pytest.raises(OpenCodeConfigError):
        ModelSelection(provider_id=EXPECTED_PROVIDER_ID, model_id="   ")


def test_profile_verification_accepts_only_poor(tmp_path) -> None:
    settings = _settings(opencode_base_url="http://127.0.0.1:4096")

    accepted = tmp_path / "profile.active"
    accepted.write_text("poor\n", encoding="utf-8")
    assert settings.verify_profile_file(str(accepted)) == "poor"

    rejected = tmp_path / "rich.active"
    rejected.write_text("rich\n", encoding="utf-8")
    with pytest.raises(OpenCodeConfigError):
        settings.verify_profile_file(str(rejected))

    blank = tmp_path / "blank.active"
    blank.write_text(" \n", encoding="utf-8")
    with pytest.raises(OpenCodeConfigError):
        settings.verify_profile_file(str(blank))

    with pytest.raises(OpenCodeConfigError):
        settings.verify_profile_file(str(tmp_path / "missing.active"))


def test_assert_poor_profile_rejects_other_names() -> None:
    assert_poor_profile("poor")
    with pytest.raises(OpenCodeConfigError):
        assert_poor_profile("rich")
    with pytest.raises(OpenCodeConfigError):
        assert_poor_profile("")


def test_fake_provider_records_model_for_create_and_prompt() -> None:
    fake = FakeOpenCodeProvider(turns=(FakeTurn(text="done"),), model=MODEL)

    async def scenario() -> None:
        session = await fake.create_session(title="MVP")
        await fake.send_prompt(session.session_id, PROMPT)

    asyncio.run(scenario())

    assert fake.model_calls() == (
        ("create", MODEL),
        ("prompt", MODEL),
    )


def test_http_send_message_always_sends_nested_pinned_model() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert (request.method, request.url.path) == (
            "POST",
            "/session/oc-s1/message",
        )
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "info": {
                    "id": "m1",
                    "sessionID": "oc-s1",
                    "role": "assistant",
                    "time": {"created": 1, "completed": 2},
                },
                "parts": [
                    {"id": "p1", "type": "text", "text": "4"},
                ],
            },
        )

    provider = _provider(handler)

    async def scenario() -> None:
        try:
            await provider.send_message("oc-s1", "What is 2+2?")
        finally:
            await provider.aclose()

    asyncio.run(scenario())

    assert bodies == [
        {
            "model": {
                "providerID": EXPECTED_PROVIDER_ID,
                "modelID": EXPECTED_MODEL_ID,
            },
            "parts": [{"type": "text", "text": "What is 2+2?"}],
        }
    ]
    assert "providerID" not in bodies[0]


def test_missing_model_config_blocks_send_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"request must not be sent: {request.url}")

    provider = _provider(handler, model=None)

    async def scenario() -> None:
        try:
            with pytest.raises(OpenCodeValidationError):
                await provider.send_message("oc-s1", "hello")
        finally:
            await provider.aclose()

    asyncio.run(scenario())


def test_fake_provider_records_model_and_text_for_send_message() -> None:
    fake = FakeOpenCodeProvider(turns=(FakeTurn(text="4"),), model=MODEL)

    async def scenario() -> tuple[str, str]:
        session = await fake.create_session(title="MVP")
        turn = await fake.send_message(session.session_id, "What is 2+2?")
        return session.session_id, turn.text

    session_id, text = asyncio.run(scenario())

    assert text == "4"
    assert fake.message_calls() == ((session_id, "What is 2+2?", None),)
    assert fake.model_calls() == (("create", MODEL), ("message", MODEL))
