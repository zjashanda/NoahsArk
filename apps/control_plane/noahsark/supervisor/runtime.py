"""Runtime wiring for the standalone supervisor process."""

from __future__ import annotations

import logging
import os
import signal
import socket

import anyio
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from ..integrations.opencode.errors import OpenCodeConfigError
from ..integrations.opencode.http_provider import OpenCodeHTTPProvider
from ..services.supervisor import SupervisorService, WorkerOutcome
from .config import SupervisorSettings
from .repository import SqlSupervisorRepository

logger = logging.getLogger("noahsark.supervisor")


def worker_id(settings: SupervisorSettings) -> str:
    if settings.worker_id:
        return settings.worker_id
    return f"{socket.gethostname()}-{os.getpid()}"


def _database_url(settings: SupervisorSettings) -> str:
    raw = (settings.database_url or "").strip()
    if not raw:
        raise RuntimeError("database_url is not configured")
    if raw.startswith("sqlite"):
        raise RuntimeError("the supervisor worker requires PostgreSQL")
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw


def build_repository(
    settings: SupervisorSettings,
) -> tuple[SqlSupervisorRepository, AsyncEngine]:
    engine = create_async_engine(_database_url(settings), poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return SqlSupervisorRepository(factory), engine


def build_provider(settings: SupervisorSettings) -> OpenCodeHTTPProvider:
    return OpenCodeHTTPProvider(settings.provider_config())


async def _watch_signals(stop: anyio.Event) -> None:
    try:
        with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
            async for _ in signals:
                stop.set()
                return
    except RuntimeError:
        logger.warning("signal handling unavailable; relying on process manager")
        await anyio.sleep_forever()


async def _sleep_or_stop(stop: anyio.Event, seconds: float) -> None:
    with anyio.move_on_after(seconds):
        await stop.wait()


async def run_worker(settings: SupervisorSettings) -> None:
    """Run the claim/poll loop until SIGINT/SIGTERM or cancellation."""

    if not settings.enabled:
        logger.info(
            "supervisor worker disabled; set NOAHSARK_SUPERVISOR_ENABLED=true"
        )
        return

    try:
        profile = settings.verify_profile_file()
    except OpenCodeConfigError as exc:
        raise RuntimeError(
            "supervisor requires the OpenCode 'poor' profile: " + exc.message
        ) from exc
    logger.info("supervisor profile verified profile=%s", profile)

    repository, engine = build_repository(settings)
    provider = build_provider(settings)
    service = SupervisorService(provider, repository, settings)
    logger.info("supervisor worker starting id=%s", worker_id(settings))

    stop = anyio.Event()
    try:
        async with provider, anyio.create_task_group() as tasks:
            tasks.start_soon(_watch_signals, stop)
            while not stop.is_set():
                result = await service.run_once()
                if result.outcome is WorkerOutcome.IDLE:
                    await _sleep_or_stop(stop, settings.idle_sleep_seconds)
                else:
                    logger.info(
                        "supervisor session=%s outcome=%s state=%s code=%s",
                        result.session_id,
                        result.outcome.value,
                        result.state,
                        result.error_code,
                    )
            tasks.cancel_scope.cancel()
    finally:
        await engine.dispose()
        logger.info("supervisor worker stopped")


__all__ = [
    "build_provider",
    "build_repository",
    "run_worker",
    "worker_id",
]
