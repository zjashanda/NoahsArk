"""Deterministic fake provider behaviour and supervisor-facing completion gates."""

from __future__ import annotations

import asyncio

import pytest

from noahsark.integrations.opencode.errors import (
    OpenCodeNotFoundError,
    OpenCodeValidationError,
)
from noahsark.integrations.opencode.fake import FakeOpenCodeProvider, FakeTurn
from noahsark.integrations.opencode.prompt import TaskPromptInput, build_task_prompt
from noahsark.integrations.opencode.protocol import (
    OpenCodeSession,
    PromptReceipt,
    SessionMessages,
    SessionObservation,
    SessionState,
    SessionStatus,
)

PROMPT = build_task_prompt(
    TaskPromptInput(
        task_id="task-001",
        title="MVP",
        instructions="Implement the provider.",
    )
)


def test_fake_provider_is_deterministic() -> None:
    async def scenario() -> tuple[
        OpenCodeSession, OpenCodeSession, SessionMessages, SessionMessages
    ]:
        first = FakeOpenCodeProvider(turns=(FakeTurn(text="result one"),))
        second = FakeOpenCodeProvider(turns=(FakeTurn(text="result one"),))
        session_one = await first.create_session(title="MVP")
        session_two = await second.create_session(title="MVP")
        await first.send_prompt(session_one.session_id, PROMPT)
        await second.send_prompt(session_two.session_id, PROMPT)
        messages_one = await first.session_messages(session_one.session_id)
        messages_two = await second.session_messages(session_two.session_id)
        return session_one, session_two, messages_one, messages_two

    session_one, session_two, messages_one, messages_two = asyncio.run(scenario())

    assert session_one == session_two
    assert messages_one == messages_two
    assert messages_one.messages[0].message_id == "fake-message-0001"
    assert messages_one.messages[1].message_id == "fake-message-0002"


def test_fake_provider_full_loop_and_abort() -> None:
    async def scenario() -> tuple[
        OpenCodeSession,
        PromptReceipt,
        SessionStatus,
        SessionMessages,
        SessionObservation,
        bool,
        tuple[str, ...],
    ]:
        provider = FakeOpenCodeProvider(turns=(FakeTurn(text="done"),))
        session = await provider.create_session(title="MVP")
        receipt = await provider.send_prompt(session.session_id, PROMPT)
        status = await provider.session_status(session.session_id)
        messages = await provider.session_messages(session.session_id)
        observation = await provider.observe(session.session_id)
        aborted = await provider.abort_session(session.session_id)
        return (
            session,
            receipt,
            status,
            messages,
            observation,
            aborted,
            provider.prompt_digests(session.session_id),
        )

    (
        session,
        receipt,
        status,
        messages,
        observation,
        aborted,
        digests,
    ) = asyncio.run(scenario())

    assert session.session_id == "fake-session-0001"
    assert receipt.http_status == 204
    assert receipt.completion_claimed is False
    assert receipt.prompt_digest == PROMPT.digest
    assert status.state is SessionState.IDLE
    assert len(messages.messages) == 2
    assert messages.messages[1].visible_text == "done"
    assert observation.is_complete is True
    assert aborted is True
    assert digests == (PROMPT.digest,)


def test_fake_provider_204_is_not_completion_until_turn_finishes() -> None:
    async def scenario() -> tuple[
        PromptReceipt, SessionObservation, SessionObservation
    ]:
        provider = FakeOpenCodeProvider(
            turns=(FakeTurn(text="done"),),
            auto_complete=False,
        )
        session = await provider.create_session(title="MVP")
        receipt = await provider.send_prompt(session.session_id, PROMPT)
        busy = await provider.observe(session.session_id)
        provider.complete_pending(session.session_id)
        finished = await provider.observe(session.session_id)
        return receipt, busy, finished

    receipt, busy, finished = asyncio.run(scenario())

    assert receipt.completion_claimed is False
    assert busy.is_complete is False
    assert busy.completion_blockers == (
        "session_not_idle",
        "no_assistant_message",
    )
    assert finished.is_complete is True


def test_fake_provider_scripted_error_and_empty_output_block_completion() -> None:
    async def scenario() -> tuple[SessionObservation, SessionObservation]:
        errored = FakeOpenCodeProvider(
            turns=(FakeTurn(text="failed", error_name="MessageAbortedError"),)
        )
        errored_session = await errored.create_session(title="MVP")
        await errored.send_prompt(errored_session.session_id, PROMPT)
        errored_observation = await errored.observe(errored_session.session_id)

        empty = FakeOpenCodeProvider(turns=(FakeTurn(text=""),))
        empty_session = await empty.create_session(title="MVP")
        await empty.send_prompt(empty_session.session_id, PROMPT)
        empty_observation = await empty.observe(empty_session.session_id)
        return errored_observation, empty_observation

    errored_observation, empty_observation = asyncio.run(scenario())

    assert errored_observation.completion_blockers == ("assistant_message_error",)
    assert empty_observation.completion_blockers == ("assistant_output_empty",)


def test_fake_provider_status_control_helpers() -> None:
    async def scenario() -> tuple[SessionStatus, SessionObservation]:
        provider = FakeOpenCodeProvider()
        session = await provider.create_session(title="MVP")
        provider.set_status(
            session.session_id,
            SessionStatus(
                state=SessionState.RETRY,
                retry_attempt=2,
                retry_message="waiting",
                retry_next_ms=99,
            ),
        )
        status = await provider.session_status(session.session_id)
        observation = await provider.observe(session.session_id)
        return status, observation

    status, observation = asyncio.run(scenario())

    assert status.state is SessionState.RETRY
    assert status.retry_attempt == 2
    assert observation.completion_blockers == (
        "session_not_idle",
        "no_assistant_message",
    )


def test_fake_provider_rejects_unknown_sessions_and_pending_overlap() -> None:
    async def scenario() -> None:
        provider = FakeOpenCodeProvider(auto_complete=False)
        with pytest.raises(OpenCodeNotFoundError):
            await provider.session_status("missing")

        session = await provider.create_session(title="MVP")
        await provider.send_prompt(session.session_id, PROMPT)
        with pytest.raises(OpenCodeValidationError):
            await provider.send_prompt(session.session_id, PROMPT)
        provider.complete_pending(session.session_id)
        with pytest.raises(OpenCodeValidationError):
            provider.complete_pending(session.session_id)
        with pytest.raises(OpenCodeNotFoundError):
            await provider.session_status("fake-session-0002")

    asyncio.run(scenario())


def test_fake_provider_delete_session_records_and_removes_session() -> None:
    async def scenario() -> tuple[bool, bool, tuple[str, ...], bool]:
        provider = FakeOpenCodeProvider()
        session = await provider.create_session(title="MVP")
        first = await provider.delete_session(session.session_id)
        second = await provider.delete_session(session.session_id)
        gone = False
        try:
            await provider.session_status(session.session_id)
        except OpenCodeNotFoundError:
            gone = True
        return first, second, provider.delete_calls(), gone

    first, second, calls, gone = asyncio.run(scenario())

    assert first is True
    assert second is True
    assert calls == ("fake-session-0001", "fake-session-0001")
    assert gone is True
