"""Development-baseline request observability.

The access log records only the HTTP method, the path (never the query string),
the status code, the duration and the sanitized correlation id. Request
headers, cookies, bodies and query strings are never logged, so tokens and
credentials cannot leak through this path.
"""

from __future__ import annotations

import logging
import time

from fastapi import Request

from .config import settings

ACCESS_LOGGER = logging.getLogger("noahsark.access")
_HTTP_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})


def configure_logging() -> None:
    """Apply the configured level to the application logger tree.

    Handlers are intentionally left to the process manager (systemd/journald
    or uvicorn) so this module does not own log destinations.
    """

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.getLogger("noahsark").setLevel(level)


async def access_log_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    method = request.method if request.method in _HTTP_METHODS else "OTHER"
    correlation = getattr(request.state, "correlation_id", "-")
    ACCESS_LOGGER.info(
        "request method=%s path=%s status=%s duration_ms=%.2f correlation_id=%s",
        method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        correlation,
    )
    return response
