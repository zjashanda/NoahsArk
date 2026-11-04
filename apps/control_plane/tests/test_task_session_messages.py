"""Read-only session transcript projection tests.

The suite is database-free: the route's session and provider dependencies are
overridden, and only the service projection plus the fake provider's messages
are exercised.  It locks down sanitization, masking, ordering, the unbound
session contract and bounded truncation.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from noahsark.api.deps import get_opencode_provider
from noahsark.db import get_optional_session, get_session
from noahsark.integrations.opencode.errors import (
    OpenCodeNotFoundError,
    OpenCodeTransportError,
)
from noahsark.integrations.opencode.fake import FakeOpenCodeProvider, FakeTurn
from noahsark.integrations.opencode.protocol import (
    BoundedPrompt,
    MessageRole,
    MessageView,
    SessionMessages,
    SessionState,
    SessionStatus,
    TextPart,
)
from noahsark.main import app
from noahsark.models import SupervisorSession, Task

REMOTE_ID = "ses_e7433c9d9ffeOKE4khOpGa2Eh9"
HEADERS = {"X-NoahsArk-Role": "ADMIN", "X-NoahsArk-Actor": "admin-01"}
PATH = "/api/v1/tasks/{task_id}/session/messages"


class _ScalarResult:
    def __init__(self, row: object) -> None:
        self._row = row

    def scalar_one_or_none(self) -> object:
        return self._row


class _FakeDb:
    """Minimal AsyncSession stand-in: task lookup then supervisor lookup."""

    def __init__(self, task: Task, row: SupervisorSession | None) -> None:
        self._task = task
        self._row = row
        self._calls = 0

    async def execute(self, statement: object) -> _ScalarResult:
        del statement
        self._calls += 1
        return _ScalarResult(self._task if self._calls == 1 else self._row)


class _StaticProvider:
    def __init__(self, messages: SessionMessages) -> None:
        self.messages = messages
        self.calls = 0
        self.last_session_id: str | None = None

    async def session_messages(self, session_id: str) -> SessionMessages:
        self.calls += 1
        self.last_session_id = session_id
        return self.messages

    async def session_status(self, session_id: str) -> SessionStatus:
        del session_id
        return SessionStatus(state=SessionState.IDLE)


class _FailingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def session_messages(self, session_id: str) -> SessionMessages:
        del session_id
        self.calls += 1
        raise OpenCodeTransportError("opencode is down")


class _NotFoundProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def session_messages(self, session_id: str) -> SessionMessages:
        del session_id
        self.calls += 1
        raise OpenCodeNotFoundError()


def _task() -> Task:
    now = datetime.now(UTC)
    return Task(
        task_id=uuid.uuid4(),
        display_id="tsk-session-messages",
        task_category="voice_interaction",
        title="Session transcript",
        objective="Return the bound conversation.",
        entry_mode="conversation",
        origin={},
        status="DRAFT",
        lead_agent_id=uuid.uuid4(),
        lead_session_id=uuid.uuid4(),
        current_revision_id=None,
        revision_ids=[],
        updated_at=now,
        created_at=now,
        source="control-plane",
        seed=False,
    )


def _supervisor(task: Task, *, remote_session_id: str | None) -> SupervisorSession:
    now = datetime.now(UTC)
    return SupervisorSession(
        supervisor_session_id=uuid.uuid4(),
        display_id="sup-session-messages",
        task_id=task.task_id,
        revision_id=uuid.uuid4(),
        state="COMPLETED",
        remote_session_id=remote_session_id,
        prompt_digest="sha256:test",
        prompt_bytes=1,
        result_summary="PONG",
        error_code=None,
        result_updated_at=now,
        created_at=now,
        updated_at=now,
        source="control-plane",
        seed=False,
    )


def _fake_conversation() -> SessionMessages:
    prompt = BoundedPrompt(
        text=(
            "Reply PONG. token=supersecret123 "
            "/home/bszheng/private/secret.txt"
        ),
        digest="sha256:test",
        max_bytes=10_000,
        original_bytes=80,
        truncated=False,
    )

    async def scenario() -> SessionMessages:
        provider = FakeOpenCodeProvider(
            turns=(
                FakeTurn(
                    text=(
                        "PONG\nAuthorization: Bearer abcdefghijklmnop "
                        "/home/bszheng/private/result.txt"
                    )
                ),
            )
        )
        session = await provider.create_session(title="Session transcript")
        await provider.send_prompt(session.session_id, prompt)
        produced = await provider.session_messages(session.session_id)
        return SessionMessages(session_id=REMOTE_ID, messages=produced.messages)

    return asyncio.run(scenario())


def _plain_messages(count: int, *, text: str = "hello") -> SessionMessages:
    messages = tuple(
        MessageView(
            message_id=f"msg-{index:04d}",
            session_id=REMOTE_ID,
            role=MessageRole.USER if index % 2 == 0 else MessageRole.ASSISTANT,
            created_at_ms=1_700_000_000_000 + index,
            completed_at_ms=1_700_000_000_000 + index,
            error_name=None,
            error_message=None,
            finish="stop",
            parts=(TextPart(part_id=f"part-{index:04d}", text=text),),
        )
        for index in range(count)
    )
    return SessionMessages(session_id=REMOTE_ID, messages=messages)


@pytest.fixture
def api():
    def build(provider: object, task: Task, row: SupervisorSession) -> TestClient:
        db = _FakeDb(task, row)

        async def override_session():
            yield db

        async def override_optional_session():
            yield None

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_optional_session] = override_optional_session
        app.dependency_overrides[get_opencode_provider] = lambda: provider
        return TestClient(app)

    yield build
    app.dependency_overrides.clear()


def test_returns_sanitized_ordered_conversation(api):
    task = _task()
    provider = _StaticProvider(_fake_conversation())
    client = api(provider, task, _supervisor(task, remote_session_id=REMOTE_ID))

    response = client.get(PATH.format(task_id=task.display_id), headers=HEADERS)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["task_id"] == str(task.task_id)
    assert data["supervisor_session_id"]
    assert data["remote_session_id"] == "ses_***2Eh9"
    assert data["remote_session_id_masked"] is True
    assert data["state"] == "COMPLETED"
    assert data["state_is_terminal"] is True
    assert data["session_status"]["state"] == "idle"
    assert data["message_count"] == 2
    assert data["truncated"] is False
    assert data["read_only"] is True
    assert [message["role"] for message in data["messages"]] == [
        "user",
        "assistant",
    ]
    assert [message["message_id"] for message in data["messages"]] == [
        "fake-message-0001",
        "fake-message-0002",
    ]
    assert data["messages"][1]["parts"][0]["type"] == "text"
    assert "PONG" in data["messages"][1]["parts"][0]["text"]
    assert provider.calls == 1
    assert provider.last_session_id == REMOTE_ID

    serialized = json.dumps(data)
    assert "supersecret123" not in serialized
    assert "abcdefghijklmnop" not in serialized
    assert "/home/bszheng" not in serialized
    assert REMOTE_ID not in serialized
    assert "[REDACTED_SECRET]" in serialized
    assert "[REDACTED_PATH]" in serialized


def test_unbound_session_returns_409_without_calling_provider(api):
    task = _task()
    provider = _StaticProvider(_fake_conversation())
    client = api(provider, task, _supervisor(task, remote_session_id=None))

    response = client.get(PATH.format(task_id=task.display_id), headers=HEADERS)

    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "SESSION_NOT_BOUND"
    assert error["retryable"] is False
    assert provider.calls == 0


def test_unknown_supervisor_row_returns_404(api):
    task = _task()
    provider = _StaticProvider(_fake_conversation())
    client = api(provider, task, None)

    response = client.get(PATH.format(task_id=task.display_id), headers=HEADERS)

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert provider.calls == 0


def test_provider_unknown_session_returns_typed_404(api):
    task = _task()
    provider = _NotFoundProvider()
    client = api(provider, task, _supervisor(task, remote_session_id=REMOTE_ID))

    response = client.get(PATH.format(task_id=task.display_id), headers=HEADERS)

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"
    assert provider.calls == 1


def test_provider_transport_error_returns_typed_502_without_content(api):
    task = _task()
    provider = _FailingProvider()
    client = api(provider, task, _supervisor(task, remote_session_id=REMOTE_ID))

    response = client.get(PATH.format(task_id=task.display_id), headers=HEADERS)

    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "PROVIDER_UNAVAILABLE"
    assert error["retryable"] is True
    assert "messages" not in response.json()
    assert "PONG" not in response.text
    assert provider.calls == 1


def test_more_than_200_messages_is_truncated(api):
    task = _task()
    provider = _StaticProvider(_plain_messages(201))
    client = api(provider, task, _supervisor(task, remote_session_id=REMOTE_ID))

    response = client.get(PATH.format(task_id=task.display_id), headers=HEADERS)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["truncated"] is True
    assert data["message_count"] == 200
    assert len(data["messages"]) == 200


def test_more_than_200k_chars_is_truncated(api):
    task = _task()
    provider = _StaticProvider(_plain_messages(2, text="A" * 200_100))
    client = api(provider, task, _supervisor(task, remote_session_id=REMOTE_ID))

    response = client.get(PATH.format(task_id=task.display_id), headers=HEADERS)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["truncated"] is True
    total = sum(
        len(part["text"])
        for message in data["messages"]
        for part in message["parts"]
    )
    assert total <= 200_000
