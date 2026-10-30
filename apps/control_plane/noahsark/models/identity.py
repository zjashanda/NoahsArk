"""Actors, roles, agents, reviews and settings rows."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, ProvenanceMixin, SchemaVersionMixin


class Role(Base, ProvenanceMixin):
    __tablename__ = "roles"

    role_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(String(200), nullable=False)
    access_level: Mapped[str] = mapped_column(String(64), nullable=False)
    capabilities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "role_code IN ('SUPER_ADMIN','SESSION_MANAGER','APPROVER','OBSERVER')",
            name="role_code_closed",
        ),
    )


class User(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    """A human or service actor.  Named ``users`` to match the W1 table list."""

    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="human")
    role_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("roles.role_code"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("actor_kind IN ('human','agent','service')", name="actor_kind_closed"),
        CheckConstraint("status IN ('ACTIVE','DISABLED')", name="status_closed"),
    )


class Agent(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "agents"

    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(300), nullable=False)
    model_binding: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','PAUSED','RETIRED')", name="status_closed"),
    )


class Review(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "reviews"

    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_revisions.revision_id"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    consensus: Mapped[str] = mapped_column(String(32), nullable=False)
    open_risks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SessionToken(Base, ProvenanceMixin, CreatedAtMixin):
    """Server-side session record.

    Only a SHA-256 hash of the bearer token is persisted.  The plaintext token
    is returned once at issuance and never stored, logged or audited.
    """

    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    actor: Mapped[str | None] = mapped_column(String(200))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    role_code: Mapped[str] = mapped_column(String(32), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("expires_at > issued_at", name="expiry_after_issue"),
    )


class Setting(Base, SchemaVersionMixin, ProvenanceMixin):
    __tablename__ = "settings"

    setting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("category", "key", name="uq_settings_category_key"),)
