"""Async SQLAlchemy session wiring for the read-only API.

PostgreSQL is the only authority.  ``NullPool`` keeps tests and the dev server
from sharing pooled connections across event loops; the slice's query volume is
low enough that connection-per-request is the safer trade-off.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .config import settings
from .errors import ApiError


def _build_engine():
    url = settings.database_url
    if not url or url.startswith("sqlite"):
        return None
    return create_async_engine(url, poolclass=NullPool)


_engine = _build_engine()
_session_factory = async_sessionmaker(_engine, expire_on_commit=False) if _engine else None


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency.  Fails closed (503) instead of falling back to SQLite."""

    if _session_factory is None:
        raise ApiError(
            503,
            "DATABASE_UNAVAILABLE",
            "DATABASE_URL is not configured for PostgreSQL; read models are unavailable",
            retryable=True,
        )
    async with _session_factory() as session:
        yield session
