from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import devices, evidence, reports, runs
from .api.agents import router as agents_router
from .api.audit import router as audit_router
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
from .api.runtime import router as runtime_router
from .api.settings import router as settings_router
from .api.tasks import router as tasks_router
from .api.writes import router as writes_router
from .config import settings
from .errors import ApiError


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
)

app.middleware("http")(correlation_middleware)
app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

app.include_router(health_router)
app.include_router(mission_router, prefix=settings.api_prefix)
app.include_router(intake_router, prefix=settings.api_prefix)
app.include_router(tasks_router, prefix=settings.api_prefix)
app.include_router(writes_router, prefix=settings.api_prefix)
app.include_router(runs.router, prefix=settings.api_prefix)
app.include_router(evidence.router, prefix=settings.api_prefix)
app.include_router(devices.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(knowledge_router, prefix=settings.api_prefix)
app.include_router(runtime_router, prefix=settings.api_prefix)
app.include_router(agents_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)
app.include_router(settings_router, prefix=settings.api_prefix)
