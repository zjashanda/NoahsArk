"""SQLAlchemy 2 declarative base and shared column helpers.

All identifiers are UUIDs, all timestamps are timezone-aware UTC, and nested
domain payloads use PostgreSQL JSONB.  The naming convention is stable so
Alembic can emit deterministic constraint names.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    return datetime.now(UTC)


def enum_check(column: str, values: tuple[str, ...], name: str) -> str:
    """Build a PostgreSQL CHECK constraint for a closed string vocabulary."""
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class SchemaVersionMixin:
    schema_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="1.0", server_default=text("'1.0'")
    )


class ProvenanceMixin:
    """Marks prototype data so it can never be mistaken for real execution."""

    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="control-plane", server_default=text("'control-plane'")
    )
    seed: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=text("false")
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
