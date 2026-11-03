"""Contract guard: task creation must never accept an existing session id.

The platform binds a supervisor by creating its own OpenCode session during
``_bind``.  Allowing a caller to pass a session id would let the platform attach
to a local TUI session, which breaks the session isolation boundary.
"""

from __future__ import annotations

import uuid

import pytest
from noahsark.api.writes import TaskCreate
from pydantic import ValidationError


def _payload(**overrides):
    body = {
        "title": "Session isolation guard",
        "objective": "Reject caller-supplied OpenCode session ids.",
        "lead_agent_id": "agt-planner",
        "lead_session_id": uuid.uuid4(),
        "prompt": "Create a task.",
    }
    body.update(overrides)
    return body


@pytest.mark.parametrize("field", ["remote_session_id", "opencode_session_id"])
def test_task_create_rejects_caller_supplied_session_id(field):
    with pytest.raises(ValidationError) as exc_info:
        TaskCreate(**_payload(**{field: "ses_e6442b5ffffeJldY7d4ZmKwsI4"}))

    errors = exc_info.value.errors()
    assert errors[0]["type"] == "extra_forbidden"
    assert errors[0]["loc"] == (field,)


def test_task_create_accepts_the_platform_contract():
    task = TaskCreate(**_payload())

    assert task.lead_session_id is not None
    assert not hasattr(task, "remote_session_id")
