"""HTTP Request / Response Middleware

Flow

1. Reads the incoming ``X-Request-ID`` header (or generates a fresh UUID) and
   binds it to the current async context via :func:`src.logging_config.set_request_id`.
   Every log record emitted while the request is being processed automatically
   carries that ID.

2. Logs two lines per request:

   *  ``inbound METHOD /path`` when the request arrives.
   *  ``outbound METHOD /path STATUS  duration_ms=N`` when the response leaves.
      Lines for 4xx / 5xx are emitted at WARNING / ERROR level so alerting
      rules can target severity rather than parsing status codes.

3. Writes the resolved ``X-Request-ID`` back into the response headers so
   clients can correlate their own traces with server logs.

Example Usage

    from fastapi import FastAPI
    from src.middleware.request_logging import RequestLoggingMiddleware

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from src.logging_config import get_logger, set_request_id

logger = get_logger(__name__)

# paths skipped entirely no request/response log lines are emitted.
_SILENT_PATHS: frozenset[str] = frozenset({"/health", "/healthz", "/metrics"})

# type alias matching Starlette's RequestResponseEndpoint
_NextCall = Callable[[Request], Awaitable[Response]]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request / response logger for FastAPI / Starlette."""

    def __init__(
        self, app: ASGIApp, *, silent_paths: frozenset[str] = _SILENT_PATHS
    ) -> None:
        super().__init__(app)
        self._silent = silent_paths

    async def dispatch(self, request: Request, call_next: _NextCall) -> Response:
        # skip noisy liveness / readiness / metrics paths
        if request.url.path in self._silent:
            return await call_next(request)
        # resolve or generate the request ID and bind it to this async context
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        logger.info(
            "→ %s %s",
            request.method,
            request.url.path,
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                # Only include query string when present to keep logs tidy
                **({"http_query": str(request.url.query)} if request.url.query else {}),
            },
        )
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # fastAPI's exception handlers have not yet run, log at ERROR
            # and re-raise so they can return the appropriate HTTP response.
            duration_ms = _ms(start)
            logger.error(
                "← %s %s 500",
                request.method,
                request.url.path,
                exc_info=True,
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": 500,
                    "duration_ms": duration_ms,
                },
            )
            raise
        duration_ms = _ms(start)
        status = response.status_code
        # Use WARNING for client errors, ERROR for server errors
        if status >= 500:
            level = logging.ERROR
        elif status >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO

        logger.log(
            level,
            "← %s %s %d",
            request.method,
            request.url.path,
            status,
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": status,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response


def _ms(start: float) -> float:
    """Return elapsed milliseconds since *start* (from time.perf_counter)."""
    return round((time.perf_counter() - start) * 1000, 2)
