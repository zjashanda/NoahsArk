"""Pydantic wire models for the verified OpenCode 1.19.4 HTTP API.

Only this module knows the response JSON shape.  Internal code receives the
typed dataclasses from :mod:`noahsark.integrations.opencode.protocol`, so a
schema drift fails here as a protocol error instead of leaking ``dict`` values
into the supervisor.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

_IGNORE_EXTRA = ConfigDict(extra="ignore")
_IGNORE_EXTRA_BY_NAME = ConfigDict(extra="ignore", populate_by_name=True)
_FORBID_BY_NAME = ConfigDict(extra="forbid", populate_by_name=True)


class IdleStatusWire(BaseModel):
    model_config = _IGNORE_EXTRA
    type: Literal["idle"]


class BusyStatusWire(BaseModel):
    model_config = _IGNORE_EXTRA
    type: Literal["busy"]


class RetryStatusWire(BaseModel):
    model_config = _IGNORE_EXTRA_BY_NAME
    type: Literal["retry"]
    attempt: int
    message: str
    next_ms: int = Field(alias="next")


StatusWire = Annotated[
    IdleStatusWire | BusyStatusWire | RetryStatusWire,
    Field(discriminator="type"),
]


class StatusMapWire(RootModel[dict[str, StatusWire]]):
    """``GET /session/status`` answers with a session-id keyed map."""


class MessageTimeWire(BaseModel):
    model_config = _IGNORE_EXTRA
    created: int
    completed: int | None = None


class MessageErrorWire(BaseModel):
    model_config = _IGNORE_EXTRA
    name: str
    data: dict[str, object] | None = None


class PartWire(BaseModel):
    model_config = _IGNORE_EXTRA
    id: str | None = None
    type: str
    text: str | None = None
    synthetic: bool = False
    ignored: bool = False


class MessageWire(BaseModel):
    model_config = _IGNORE_EXTRA_BY_NAME
    id: str
    session_id: str = Field(alias="sessionID")
    role: Literal["user", "assistant"]
    time: MessageTimeWire
    error: MessageErrorWire | None = None
    finish: str | None = None


class MessageEnvelopeWire(BaseModel):
    model_config = _IGNORE_EXTRA
    info: MessageWire
    parts: list[PartWire]


class MessagesWire(RootModel[list[MessageEnvelopeWire]]):
    """``GET /session/{id}/message`` answers with an ordered envelope list."""


class SessionWire(BaseModel):
    model_config = _IGNORE_EXTRA
    id: str
    title: str = ""
    version: str = ""


class SessionCreateModelWire(BaseModel):
    """``POST /session`` uses ``{id, providerID, variant?}`` for its model."""

    model_config = _FORBID_BY_NAME
    id: str
    provider_id: str = Field(alias="providerID")


class SessionCreateWire(BaseModel):
    model_config = _FORBID_BY_NAME
    title: str
    model: SessionCreateModelWire


class TextPartInputWire(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["text"] = "text"
    text: str


class PromptModelWire(BaseModel):
    """``POST /session/{id}/prompt_async`` uses ``{providerID, modelID}``."""

    model_config = _FORBID_BY_NAME
    provider_id: str = Field(alias="providerID")
    model_id: str = Field(alias="modelID")


class PromptRequestWire(BaseModel):
    model_config = _FORBID_BY_NAME
    parts: list[TextPartInputWire]
    model: PromptModelWire


class MessageRequestWire(BaseModel):
    """``POST /session/{id}/message`` pins the model under ``model``.

    The blocking endpoint uses the same nested ``{providerID, modelID}`` pair as
    ``prompt_async``.  ``model`` is mandatory here: omitting it would let
    OpenCode fall back to its default model.
    """

    model_config = _FORBID_BY_NAME
    parts: list[TextPartInputWire]
    model: PromptModelWire


class AbortWire(RootModel[bool]):
    """``POST /session/{id}/abort`` answers with a bare JSON boolean."""


__all__ = [
    "AbortWire",
    "BusyStatusWire",
    "IdleStatusWire",
    "MessageEnvelopeWire",
    "MessageErrorWire",
    "MessageRequestWire",
    "MessageTimeWire",
    "MessageWire",
    "MessagesWire",
    "PartWire",
    "PromptModelWire",
    "PromptRequestWire",
    "RetryStatusWire",
    "SessionCreateModelWire",
    "SessionCreateWire",
    "SessionWire",
    "StatusMapWire",
    "StatusWire",
    "TextPartInputWire",
]
