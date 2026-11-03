import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import devices, evidence, reports, runs
from .api.agents import router as agents_router
from .api.audit import router as audit_router
from .api.auth import router as auth_router
from .api.envelope import (
    api_error_handler,
    correlation_middleware,
    error_body,
    http_error_handler,
)
from .api.health import router as health_router
from .api.intake import router as intake_router
from .api.knowledge import router as knowledge_router
from .api.mission import router as mission_router
from .api.node_commands import router as node_commands_router
from .api.node_enrollment import router as node_enrollment_router
from .api.node_gateway import router as node_gateway_router
from .api.runtime import router as runtime_router
from .api.settings import router as settings_router
from .api.tasks import router as tasks_router
from .api.test_campaigns import router as test_campaigns_router
from .api.topology import router as topology_router
from .api.writes import router as writes_router
from .config import settings
from .db import get_session_factory
from .errors import ApiError
from .observability import access_log_middleware, configure_logging
from .services.node_health import sweep_node_staleness

logger = logging.getLogger("noahsark.node_health")

NODE_HEALTH_SWEEP_INTERVAL_SECONDS = 30
_NODE_HEALTH_BASELINE_COUNTS = {"stale": 0, "offline": 0}


async def _node_health_sweep_once() -> dict[str, int] | None:
    factory = get_session_factory()
    if factory is None:
        return None
    async with factory() as session:
        return await sweep_node_staleness(session)


async def _node_health_loop() -> None:
    """Expire silent nodes in the background until the app shuts down."""

    previous = dict(_NODE_HEALTH_BASELINE_COUNTS)
    while True:
        await asyncio.sleep(NODE_HEALTH_SWEEP_INTERVAL_SECONDS)
        try:
            counts = await _node_health_sweep_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("node staleness sweep failed")
            continue
        if counts is not None and counts != previous:
            logger.info(
                "node staleness sweep stale=%d offline=%d",
                counts["stale"],
                counts["offline"],
            )
            previous = counts


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    sweep_task = asyncio.create_task(_node_health_loop(), name="node-health-sweep")
    try:
        yield
    finally:
        sweep_task.cancel()
        with suppress(asyncio.CancelledError):
            await sweep_task


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    api_exc = ApiError(
        400,
        "VALIDATION_ERROR",
        "Request validation failed",
        retryable=False,
        details={"errors": jsonable_encoder(exc.errors())},
    )
    return JSONResponse(status_code=400, content=error_body(request, api_exc))


app = FastAPI(
    title="NoahsArk Control Plane",
    version="0.1.0",
    description="Phase 2 vertical-slice scaffold. Not a frozen production implementation.",
    lifespan=lifespan,
)

configure_logging()
app.middleware("http")(correlation_middleware)
app.middleware("http")(access_log_middleware)
app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

app.include_router(health_router)
app.include_router(node_gateway_router)
app.include_router(node_enrollment_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(mission_router, prefix=settings.api_prefix)
app.include_router(intake_router, prefix=settings.api_prefix)
app.include_router(tasks_router, prefix=settings.api_prefix)
app.include_router(writes_router, prefix=settings.api_prefix)
app.include_router(runs.router, prefix=settings.api_prefix)
app.include_router(evidence.router, prefix=settings.api_prefix)
app.include_router(devices.router, prefix=settings.api_prefix)
app.include_router(node_commands_router, prefix=settings.api_prefix)
app.include_router(test_campaigns_router, prefix=settings.api_prefix)
app.include_router(topology_router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(knowledge_router, prefix=settings.api_prefix)
app.include_router(runtime_router, prefix=settings.api_prefix)
app.include_router(agents_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)
app.include_router(settings_router, prefix=settings.api_prefix)
