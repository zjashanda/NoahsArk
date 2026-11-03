"""Task deletion: provider session, dependent rows, audit and route guards.

The service tests are database-free: an in-memory session answers the exact
selects the service uses and records every ``DELETE`` statement in execution
order.  The route tests reuse it to prove ADMIN-only access and the documented
second-call ``404``.
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
from noahsark.errors import ApiError
from noahsark.integrations.opencode.errors import (
    OpenCodeHTTPError,
    OpenCodeNotFoundError,
)
from noahsark.integrations.opencode.fake import FakeOpenCodeProvider
from noahsark.main import app
from noahsark.models import (
    AuditEvent,
    SupervisorSession,
    Task,
)
from noahsark.models import (
    TestCampaign as CampaignModel,
)
from noahsark.services import supervision
from sqlalchemy import Delete, Update

PATH = "/api/v1/tasks/{task_id}"


class _Scalars:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return list(self._values)


class _Result:
    def __init__(self, value: object, values: list[object] | None = None) -> None:
        self._value = value
        self._values = values

    def scalar_one_or_none(self) -> object:
        return self._value

    def scalars(self) -> _Scalars:
        if self._values is not None:
            return _Scalars(self._values)
        if self._value is None:
            return _Scalars([])
        return _Scalars([self._value])


class _DeleteResult:
    rowcount = 1


def _entity(statement: object) -> object | None:
    descriptions = getattr(statement, "column_descriptions", None)
    if not descriptions:
        return None
    return descriptions[0].get("entity")


class _FakeSession:
    """Answers Task/SupervisorSession/TestCampaign/AuditEvent selects and records deletes."""

    def __init__(
        self,
        task: Task | None,
        row: SupervisorSession | None,
        campaigns: list[CampaignModel] | None = None,
    ) -> None:
        self.task = task
        self.row = row
        self.campaigns = list(campaigns or [])
        self.deleted_tables: list[str] = []
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0
        self.lease_updates = 0
        self.task_deleted = False

    async def execute(self, statement: object) -> object:
        if isinstance(statement, Delete):
            self.deleted_tables.append(statement.table.name)
            return _DeleteResult()
        if isinstance(statement, Update):
            if statement.table.name == "resource_leases":
                self.lease_updates += 1
            return _DeleteResult()
        entity = _entity(statement)
        if entity is Task:
            return _Result(None if self.task_deleted else self.task)
        if entity is SupervisorSession:
            return _Result(self.row)
        if entity is CampaignModel:
            return _Result(None, self.campaigns)
        if entity is AuditEvent:
            return _Result(None)
        return _Result(None)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        self.commits += 1
        self.task_deleted = True

    async def rollback(self) -> None:
        self.rollbacks += 1


def _task() -> Task:
    now = datetime.now(UTC)
    return Task(
        task_id=uuid.uuid4(),
        display_id="tsk-delete",
        task_category="voice_interaction",
        title="Delete me",
        objective="Delete this completed task.",
        entry_mode="conversation",
        origin={},
        status="REPORTED",
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
    remote_session_id: str | None = None,
) -> SupervisorSession:
    now = datetime.now(UTC)
    return SupervisorSession(
        supervisor_session_id=uuid.uuid4(),
        display_id="sup-delete",
        task_id=task.task_id,
        revision_id=uuid.uuid4(),
        state=state,
        remote_session_id=remote_session_id,
        prompt_digest="sha256:test",
        prompt_bytes=1,
        result_summary="done",
        error_code=None,
        result_updated_at=now,
        created_at=now,
        updated_at=now,
        source="control-plane",
        seed=False,
    )


def _campaign(
    task: Task,
    *,
    status: str = "SUCCEEDED",
    command_id: uuid.UUID | None = None,
) -> CampaignModel:
    now = datetime.now(UTC)
    return CampaignModel(
        campaign_id=uuid.uuid4(),
        node_id=uuid.uuid4(),
        task_id=task.task_id,
        scenario="wake-recognition",
        rounds=1,
        bench="tcl003.json",
        title="linked campaign",
        status=status,
        command_id=command_id,
        summary=None,
        rounds_data=None,
        error_code=None,
        created_at=now,
        started_at=now,
        finished_at=now,
    )


def _provider_with_session() -> tuple[FakeOpenCodeProvider, str]:
    provider = FakeOpenCodeProvider()
    session = asyncio.run(provider.create_session(title="delete-me"))
    return provider, session.session_id


def _delete(
    db: _FakeSession, provider: object, identifier: str = "tsk-delete"
) -> dict:
    return asyncio.run(
        supervision.delete_task_and_session(
            db,  # type: ignore[arg-type]
            identifier,
            provider,  # type: ignore[arg-type]
            actor="admin-01",
            role="ADMIN",
            correlation_id="corr-delete",
            path="/api/v1/tasks/tsk-delete",
        )
    )


def test_terminal_task_delete_calls_provider_then_deletes_all_children() -> None:
    task = _task()
    provider, remote_id = _provider_with_session()
    row = _supervisor(task, remote_session_id=remote_id)
    db = _FakeSession(task, row)

    data = _delete(db, provider)

    assert data == {
        "task_id": str(task.task_id),
        "display_id": "tsk-delete",
        "deleted": True,
        "session_deleted": True,
        "campaigns_deleted": 0,
        "campaign_ids": [],
        "campaign_leases_released": 0,
    }
    assert provider.delete_calls() == (remote_id,)
    assert db.deleted_tables == [
        "supervisor_sessions",
        "evidence_items",
        "attempts",
        "evidence_manifests",
        "leases",
        "verdicts",
        "reports",
        "reviews",
        "gates",
        "approvals",
        "cases",
        "runs",
        "task_revisions",
        "tasks",
    ]
    assert db.commits == 1
    events = [item for item in db.added if isinstance(item, AuditEvent)]
    assert len(events) == 1
    event = events[0]
    assert event.action == "TASK_DELETE"
    assert event.object_type == "task"
    assert event.object_id == "tsk-delete"
    assert event.actor_role == "ADMIN"
    assert event.correlation_id == "corr-delete"
    assert event.correlation == {
        "path": "/api/v1/tasks/tsk-delete",
        "append_only": True,
    }
    assert event.after == {
        "task_id": str(task.task_id),
        "display_id": "tsk-delete",
        "deleted": True,
        "session_deleted": True,
    }
    serialized = json.dumps(event.before)
    assert remote_id not in serialized
    assert event.before["remote_session_id"] == "fake***0001"


def test_terminal_linked_campaign_is_deleted_before_task_rows() -> None:
    task = _task()
    provider, remote_id = _provider_with_session()
    row = _supervisor(task, remote_session_id=remote_id)
    campaign = _campaign(task, status="SUCCEEDED")
    db = _FakeSession(task, row, [campaign])

    data = _delete(db, provider)

    assert data["campaigns_deleted"] == 1
    assert data["campaign_ids"] == [str(campaign.campaign_id)]
    assert data["campaign_leases_released"] == 1
    assert db.lease_updates == 1
    assert db.deleted_tables[0] == "test_campaigns"
    assert db.deleted_tables.index("test_campaigns") < db.deleted_tables.index("tasks")
    assert db.commits == 1

    events = [item for item in db.added if isinstance(item, AuditEvent)]
    assert [item.action for item in events] == [
        "TEST_CAMPAIGN_DELETED",
        "TASK_DELETE",
    ]
    campaign_event = events[0]
    assert campaign_event.object_type == "test_campaign"
    assert campaign_event.object_id == str(campaign.campaign_id)
    assert campaign_event.reason == "TASK_DELETED"
    assert campaign_event.after["released_lease_count"] == 1
    assert campaign_event.after["deleted"] is True


@pytest.mark.parametrize("status", ["QUEUED", "RUNNING"])
def test_active_linked_campaign_blocks_task_delete(status: str) -> None:
    task = _task()
    provider, remote_id = _provider_with_session()
    row = _supervisor(task, remote_session_id=remote_id)
    campaign = _campaign(task, status=status)
    db = _FakeSession(task, row, [campaign])

    with pytest.raises(ApiError) as caught:
        _delete(db, provider)

    assert caught.value.status_code == 409
    assert caught.value.code == "CAMPAIGN_ACTIVE"
    details = caught.value.details
    assert details["task_id"] == str(task.task_id)
    assert details["campaigns"] == [
        {
            "campaign_id": str(campaign.campaign_id),
            "status": status,
            "stop_endpoint": f"/api/v1/test-campaigns/{campaign.campaign_id}/stop",
        }
    ]
    assert "hint" in details
    assert provider.delete_calls() == ()
    assert db.deleted_tables == []
    assert db.lease_updates == 0
    assert db.commits == 0
    assert db.added == []


def test_task_without_campaigns_keeps_previous_deletion_behavior() -> None:
    task = _task()
    provider, remote_id = _provider_with_session()
    row = _supervisor(task, remote_session_id=remote_id)
    db = _FakeSession(task, row)

    data = _delete(db, provider)

    assert data["campaigns_deleted"] == 0
    assert data["campaign_ids"] == []
    assert data["campaign_leases_released"] == 0
    assert "test_campaigns" not in db.deleted_tables
    assert db.deleted_tables == [
        "supervisor_sessions",
        "evidence_items",
        "attempts",
        "evidence_manifests",
        "leases",
        "verdicts",
        "reports",
        "reviews",
        "gates",
        "approvals",
        "cases",
        "runs",
        "task_revisions",
        "tasks",
    ]
    assert db.lease_updates == 0
    events = [item for item in db.added if isinstance(item, AuditEvent)]
    assert [item.action for item in events] == ["TASK_DELETE"]


@pytest.mark.parametrize(
    "state",
    ["PENDING", "BINDING", "READY", "DISPATCHED", "RUNNING", "STOP_REQUESTED"],
)
def test_active_task_is_rejected_without_provider_or_db_changes(state: str) -> None:
    task = _task()
    provider, remote_id = _provider_with_session()
    row = _supervisor(task, state=state, remote_session_id=remote_id)
    db = _FakeSession(task, row)

    with pytest.raises(ApiError) as caught:
        _delete(db, provider)

    assert caught.value.status_code == 409
    assert caught.value.code == "TASK_ACTIVE"
    assert caught.value.details["state"] == state
    assert provider.delete_calls() == ()
    assert db.deleted_tables == []
    assert db.commits == 0


def test_provider_404_is_idempotent_success_and_rows_are_deleted() -> None:
    task = _task()
    row = _supervisor(task, remote_session_id="ses_missing")

    class MissingProvider:
        async def delete_session(self, session_id: str) -> bool:
            raise OpenCodeNotFoundError(details={"session_id": session_id})

    db = _FakeSession(task, row)
    data = _delete(db, MissingProvider())

    assert data["session_deleted"] is True
    assert db.commits == 1
    assert "tasks" in db.deleted_tables


def test_provider_error_is_502_and_no_rows_are_deleted() -> None:
    task = _task()
    row = _supervisor(task, remote_session_id="ses_live")

    class BrokenProvider:
        async def delete_session(self, session_id: str) -> bool:
            raise OpenCodeHTTPError(
                status_code=503,
                code="OPENCODE_SERVER_ERROR",
                message="OpenCode is unavailable",
                retryable=True,
            )

    db = _FakeSession(task, row)
    with pytest.raises(ApiError) as caught:
        _delete(db, BrokenProvider())

    assert caught.value.status_code == 502
    assert caught.value.code == "PROVIDER_UNAVAILABLE"
    assert caught.value.retryable is True
    assert db.deleted_tables == []
    assert db.commits == 0


def test_missing_task_is_404() -> None:
    provider, _ = _provider_with_session()
    db = _FakeSession(None, None)

    with pytest.raises(ApiError) as caught:
        _delete(db, provider, identifier="tsk-does-not-exist")

    assert caught.value.status_code == 404
    assert caught.value.code == "NOT_FOUND"
    assert provider.delete_calls() == ()
    assert db.commits == 0


def test_unbound_terminal_task_deletes_rows_without_provider_call() -> None:
    task = _task()
    row = _supervisor(task, remote_session_id=None)
    db = _FakeSession(task, row)
    provider = FakeOpenCodeProvider()

    data = _delete(db, provider)

    assert data["session_deleted"] is False
    assert provider.delete_calls() == ()
    assert db.commits == 1
    assert "tasks" in db.deleted_tables


@pytest.fixture
def api():
    def build(db: _FakeSession, provider: FakeOpenCodeProvider) -> TestClient:
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


def test_delete_route_rejects_non_admin(api) -> None:
    task = _task()
    provider, remote_id = _provider_with_session()
    row = _supervisor(task, remote_session_id=remote_id)
    db = _FakeSession(task, row)
    client = api(db, provider)

    response = client.delete(
        PATH.format(task_id=task.display_id),
        headers={"X-NoahsArk-Role": "SESSION_MANAGER", "X-NoahsArk-Actor": "sm-01"},
    )

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert provider.delete_calls() == ()
    assert db.deleted_tables == []


def test_delete_route_deletes_once_then_second_call_is_404(api) -> None:
    task = _task()
    provider, remote_id = _provider_with_session()
    row = _supervisor(task, remote_session_id=remote_id)
    db = _FakeSession(task, row)
    client = api(db, provider)
    headers = {"X-NoahsArk-Role": "ADMIN", "X-NoahsArk-Actor": "admin-01"}

    first = client.delete(PATH.format(task_id=task.display_id), headers=headers)
    second = client.delete(PATH.format(task_id=task.display_id), headers=headers)

    assert first.status_code == 200, first.text
    assert first.json()["data"]["deleted"] is True
    assert first.json()["data"]["session_deleted"] is True
    assert second.status_code == 404, second.text
    assert second.json()["error"]["code"] == "NOT_FOUND"
    assert provider.delete_calls() == (remote_id,)
    assert db.deleted_tables.count("tasks") == 1
