"""Unified success/error envelopes and correlation-id middleware.

Every ``/api/v1`` response is wrapped so consumers can tell authoritative
control-plane data from UI fixtures without inspecting individual fields.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..config import settings
from ..errors import ApiError

SOURCE = "control-plane"
SCHEMA_VERSION = "1.0"
CORRELATION_HEADER = "X-Correlation-ID"


def utc_iso(value: datetime | None = None) -> str:
    moment = value or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", None) or uuid.uuid4().hex


def success(request: Request, data: Any) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {
            "source": SOURCE,
            "schema_version": SCHEMA_VERSION,
            "server_authoritative": True,
            "mock": False,
            "generated_at": utc_iso(),
            "correlation_id": correlation_id(request),
        },
    }


def error_body(request: Request, exc: ApiError) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
            "correlation_id": correlation_id(request),
        }
    }
    if exc.details:
        body["error"]["details"] = exc.details
    return body


async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get(CORRELATION_HEADER) or uuid.uuid4().hex
    request.state.correlation_id = cid
    response = await call_next(request)
    response.headers[CORRELATION_HEADER] = cid
    return response


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_body(request, exc))


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if request.url.path.startswith(settings.api_prefix):
        api_exc = ApiError(
            exc.status_code,
            "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            str(exc.detail),
            retryable=exc.status_code >= 500,
        )
        return JSONResponse(status_code=exc.status_code, content=error_body(request, api_exc))
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Map body/query validation failures onto the stable error vocabulary."""

    api_exc = ApiError(
        400,
        "VALIDATION_ERROR",
        "Request validation failed",
        retryable=False,
        details={"errors": _safe_validation_errors(exc.errors())},
    )
    return JSONResponse(status_code=400, content=error_body(request, api_exc))


def _safe_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in errors:
        cleaned.append(
            {
                "loc": [str(part) for part in item.get("loc", ())],
                "type": item.get("type"),
                "msg": item.get("msg"),
            }
        )
    return cleaned
