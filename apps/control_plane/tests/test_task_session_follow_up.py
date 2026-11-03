"""Follow-up turn on an existing task session (write path).

Database-free: the route's session and provider dependencies are replaced with
an in-memory session that answers the exact query entities the service uses and
stores the idempotency row like PostgreSQL would.  This locks down the pinned
model, the terminal-state guard, text bounds, sanitization and idempotent replay.
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
from noahsark.integrations.opencode.config import ModelSelection
from noahsark.integrations.opencode.fake import FakeOpenCodeProvider, FakeTurn
from noahsark.main import app
from noahsark.models import (
    AuditEvent,
    IdempotencyKey,
    SupervisorSession,
    Task,
)

MODEL = ModelSelection(
    provider_id="listenai",
    model_id="deepseek-v4.1-flash-expires-on-0910",
)
HEADERS = {"X-NoahsArk-Role": "ADMIN", "X-NoahsArk-Actor": "admin-01"}
PATH = "/api/v1/tasks/{task_id}/session/messages"
FOLLOW_UP_TEXT = "What is 2+2? Reply with only the number."


class _Result:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


def _entity(statement: object) -> object | None:
    descriptions = getattr(statement, "column_descriptions", None)
    if not descriptions:
        return None
    return descriptions[0].get("entity")


class _FakeSession:
    """Answers Task, SupervisorSession, IdempotencyKey, User and AuditEvent."""

    def __init__(self, task: Task, row: SupervisorSession | None) -> None:
        self.task = task
        self.row = row
        self.idempotency: IdempotencyKey | None = None
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement: object) -> _Result:
        entity = _entity(statement)
        if entity is Task:
            return _Result(self.task)
        if entity is SupervisorSession:
            return _Result(self.row)
        if entity is IdempotencyKey:
            return _Result(self.idempotency)
        if entity is AuditEvent:
            return _Result(None)
        # User lookups (actor resolution) and any other scalar query.
        return _Result(None)

    def add(self, instance: object) -> None:
        self.added.append(instance)
        if isinstance(instance, IdempotencyKey):
            self.idempotency = instance

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _task() -> Task:
    now = datetime.now(UTC)
    return Task(
        task_id=uuid.uuid4(),
        display_id="tsk-follow-up",
        task_category="voice_interaction",
        title="Follow-up",
        objective="Continue the session.",
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


def _supervisor(
    task: Task,
    *,
    state: str = "COMPLETED",
    remote_session_id: str | None = "ses_e7433c9d9ffeOKE4khOpGa2Eh9",
) -> SupervisorSession:
    now = datetime.now(UTC)
    return SupervisorSession(
        supervisor_session_id=uuid.uuid4(),
        display_id="sup-follow-up",
        task_id=task.task_id,
        revision_id=uuid.uuid4(),
        state=state,
        remote_session_id=remote_session_id,
        prompt_digest="sha256:test",
        prompt_bytes=1,
        result_summary="2",
        error_code=None,
        result_updated_at=now,
        created_at=now,
        updated_at=now,
        source="control-plane",
        seed=False,
    )


def _provider(*, text: str = "4") -> tuple[FakeOpenCodeProvider, str]:
    provider = FakeOpenCodeProvider(turns=(FakeTurn(text=text),), model=MODEL)
    session = asyncio.run(provider.create_session(title="follow-up"))
    return provider, session.session_id


@pytest.fixture
def api():
    def build(
        db: _FakeSession, provider: FakeOpenCodeProvider
    ) -> TestClient:
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


def _headers(key: str = "follow-up-1", role: str = "ADMIN") -> dict[str, str]:
    headers = {"X-NoahsArk-Role": role, "X-NoahsArk-Actor": "admin-01"}
    headers["Idempotency-Key"] = key
    return headers


def test_follow_up_sends_pinned_model_and_returns_assistant_reply(api):
    task = _task()
    row = _supervisor(task)
    provider, remote = _provider(text="4")
    row.remote_session_id = remote
    db = _FakeSession(task, row)
    client = api(db, provider)

    response = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": FOLLOW_UP_TEXT},
        headers=_headers(),
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["task_id"] == str(task.task_id)
    assert data["supervisor_session_id"] == str(row.supervisor_session_id)
    assert data["remote_session_id"] == "fake***0001"
    assert data["remote_session_id_masked"] is True
    assert data["state"] == "COMPLETED"
    assert data["role"] == "assistant"
    assert data["text"] == "4"
    assert data["message_id"] == "fake-message-0002"
    assert data["created_at"].endswith("Z")
    assert data["read_only"] is False

    assert provider.message_calls() == ((remote, FOLLOW_UP_TEXT, None),)
    assert provider.model_calls() == (
        ("create", MODEL),
        ("message", MODEL),
    )
    # A follow-up never advances or reopens the business-task binding.
    assert row.state == "COMPLETED"
    assert db.commits == 1


@pytest.mark.parametrize("state", ["PENDING", "BINDING", "READY", "DISPATCHED", "RUNNING", "STOP_REQUESTED"])
def test_active_execution_states_are_busy_and_never_call_provider(api, state):
    task = _task()
    row = _supervisor(task, state=state)
    provider, remote = _provider()
    row.remote_session_id = remote
    db = _FakeSession(task, row)
    client = api(db, provider)

    response = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": FOLLOW_UP_TEXT},
        headers=_headers(key=f"busy-{state}"),
    )

    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "SESSION_BUSY"
    assert error["details"]["state"] == state
    assert provider.message_calls() == ()
    assert db.commits == 0


def test_unbound_session_returns_409_without_calling_provider(api):
    task = _task()
    row = _supervisor(task, remote_session_id=None)
    provider, _ = _provider()
    db = _FakeSession(task, row)
    client = api(db, provider)

    response = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": FOLLOW_UP_TEXT},
        headers=_headers(key="unbound"),
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "SESSION_NOT_BOUND"
    assert provider.message_calls() == ()
    assert db.commits == 0


def test_unknown_supervisor_row_returns_404(api):
    task = _task()
    provider, _ = _provider()
    db = _FakeSession(task, None)
    client = api(db, provider)

    response = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": FOLLOW_UP_TEXT},
        headers=_headers(key="missing-row"),
    )

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert provider.message_calls() == ()


@pytest.mark.parametrize(
    ("text", "status_code", "code"),
    [
        ("   ", 422, "SESSION_MESSAGE_EMPTY"),
        ("", 422, "SESSION_MESSAGE_EMPTY"),
        ("x" * 20_001, 413, "SESSION_MESSAGE_TOO_LARGE"),
    ],
)
def test_blank_and_oversized_text_are_rejected(api, text, status_code, code):
    task = _task()
    row = _supervisor(task)
    provider, remote = _provider()
    row.remote_session_id = remote
    db = _FakeSession(task, row)
    client = api(db, provider)

    response = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": text},
        headers=_headers(key=f"bounds-{code}-{len(text)}"),
    )

    assert response.status_code == status_code, response.text
    assert response.json()["error"]["code"] == code
    assert provider.message_calls() == ()
    assert db.commits == 0


def test_idempotent_replay_sends_only_once(api):
    task = _task()
    row = _supervisor(task)
    provider, remote = _provider(text="4")
    row.remote_session_id = remote
    db = _FakeSession(task, row)
    client = api(db, provider)

    first = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": FOLLOW_UP_TEXT},
        headers=_headers(key="replay-1"),
    )
    second = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": FOLLOW_UP_TEXT},
        headers=_headers(key="replay-1"),
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["data"] == second.json()["data"]
    assert provider.message_calls() == ((remote, FOLLOW_UP_TEXT, None),)
    assert db.commits == 1


def test_same_key_with_different_text_is_idempotency_conflict(api):
    task = _task()
    row = _supervisor(task)
    provider, remote = _provider()
    row.remote_session_id = remote
    db = _FakeSession(task, row)
    client = api(db, provider)

    client.post(
        PATH.format(task_id=task.display_id),
        json={"text": FOLLOW_UP_TEXT},
        headers=_headers(key="conflict-1"),
    )
    response = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": "another question"},
        headers=_headers(key="conflict-1"),
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert provider.message_calls() == ((remote, FOLLOW_UP_TEXT, None),)


def test_assistant_reply_is_sanitized_before_return(api):
    task = _task()
    row = _supervisor(task)
    provider, remote = _provider(
        text="Authorization: Bearer abcdefghijklmnop /home/bszheng/private/out.txt"
    )
    row.remote_session_id = remote
    db = _FakeSession(task, row)
    client = api(db, provider)

    response = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": FOLLOW_UP_TEXT},
        headers=_headers(key="sanitize-1"),
    )

    assert response.status_code == 200, response.text
    text = response.json()["data"]["text"]
    serialized = json.dumps(response.json())
    assert "abcdefghijklmnop" not in serialized
    assert "/home/bszheng" not in serialized
    assert "[REDACTED_SECRET]" in text
    assert "[REDACTED_PATH]" in text


def test_observer_cannot_send_follow_up(api):
    task = _task()
    row = _supervisor(task)
    provider, remote = _provider()
    row.remote_session_id = remote
    db = _FakeSession(task, row)
    client = api(db, provider)

    response = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": FOLLOW_UP_TEXT},
        headers=_headers(key="observer-1", role="OBSERVER"),
    )

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert provider.message_calls() == ()


def test_follow_up_requires_idempotency_key(api):
    task = _task()
    row = _supervisor(task)
    provider, remote = _provider()
    row.remote_session_id = remote
    db = _FakeSession(task, row)
    client = api(db, provider)

    response = client.post(
        PATH.format(task_id=task.display_id),
        json={"text": FOLLOW_UP_TEXT},
        headers={"X-NoahsArk-Role": "ADMIN", "X-NoahsArk-Actor": "admin-01"},
    )

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "IDEMPOTENCY_REQUIRED"
    assert provider.message_calls() == ()
