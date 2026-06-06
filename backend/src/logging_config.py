"""Global Logging Configuration

Flow

Two modes, decided on ``IS_DEV`` variable in .env:
  True = colourised, human-readable stdout.
  False = structured JSON for log aggregators.

Example Usage

    from src.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Meeting created", extra={"meeting_id": "abc-123"})
    logger.warning("Slow query", extra={"duration_ms": 1200})
    logger.exception("Unexpected error")   # attaches full traceback

Extra fields passed via ``extra={}`` appear as top-level JSON keys in
production and as ``key=value`` annotations in development"""

from __future__ import annotations

import logging
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter

from src.config import get_settings

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the active request ID, or ``""`` when called outside a request."""
    return _request_id_ctx.get()


def set_request_id(value: str) -> None:
    """Bind *value* as the request ID for the current async context.

    Called by :class:`src.middleware.request_logging.RequestLoggingMiddleware`.
    Application code should not need to call this directly.
    """
    _request_id_ctx.set(value)


class _RequestIdFilter(logging.Filter):
    """Add the current ``request_id`` to every :class:`logging.LogRecord`.

    The filter is attached to the stream handler so it runs for every record
    regardless of which logger emitted it.  When there is no active request
    (e.g. startup/shutdown logs) the attribute is simply omitted.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = _request_id_ctx.get("")
        if request_id:
            record.request_id = request_id
        return True


# Standard LogRecord attribute names
#
# Used by _DevFormatter to distinguish *extra* fields (application context)
# from the standard fields that the formatter already displays.
_STDLIB_ATTRS: frozenset[str] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "request_id",  # shown separately at the end of the line
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


def _extra_fields(record: logging.LogRecord) -> dict[str, object]:
    """Extract non-standard fields added via ``logger.info(..., extra=...)``."""
    return {
        k: v
        for k, v in record.__dict__.items()
        if not k.startswith("_") and k not in _STDLIB_ATTRS
    }


# Development formatter colourised, human-readable
_LEVEL_COLORS: dict[str, str] = {
    "DEBUG": "\033[36m",  # cyan
    "INFO": "\033[32m",  # green
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",  # red
    "CRITICAL": "\033[35m",  # magenta
}
_RESET = "\033[0m"


class _DevFormatter(logging.Formatter):
    """Human-readable, colourised formatter for local development.

    Example Output format::

        2026-06-01 12:00:00 INFO     src.api.rooms  Meeting created  meeting_id=abc-123  [req-id]
    """

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, "")
        line = super().format(record)
        # append structured extra fields after the message
        extras = _extra_fields(record)
        if extras:
            line += "  " + "  ".join(f"{k}={v}" for k, v in extras.items())
        # append request_id last
        request_id = getattr(record, "request_id", "")
        if request_id:
            line += f"  [{request_id}]"

        return f"{color}{line}{_RESET}"


def _build_json_formatter() -> JsonFormatter:
    """Return the production JSON formatter.

    Every record includes::

        {
          "timestamp": "2026-06-01T12:00:00.123456+00:00",  // UTC ISO-8601
          "level":     "INFO",
          "logger":    "src.api.rooms",
          "message":   "Meeting created",
          "service":   "craftmeet",          // from SERVICE_NAME env var
          "meeting_id": "abc-123",            // extra fields from the caller
          "request_id": "..."                // when inside a request context
        }
    """
    settings = get_settings()
    return JsonFormatter(
        # required logging fields
        fmt="%(levelname)s %(name)s %(message)s",
        rename_fields={"levelname": "level", "name": "logger"},
        # Adds a proper UTC ISO-8601 "timestamp" field automatically
        timestamp="timestamp",
        # Static metadata on every record
        static_fields={"service": settings.SERVICE_NAME},
    )


def setup_logging() -> None:
    """Configure application-wide logging

    Call **once** at startup, before the ASGI app is created.
    """
    settings = get_settings()
    # determine log level
    numeric_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    formatter: logging.Formatter = (
        _DevFormatter() if settings.IS_DEV else _build_json_formatter()
    )
    # configure handlers
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(_RequestIdFilter())
    # configure root handler
    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers = [handler]
    # configure uvicorn handler
    for name in ("uvicorn", "uvicorn.error"):
        uvi = logging.getLogger(name)
        uvi.handlers = [handler]
        uvi.propagate = False
    access_log = logging.getLogger("uvicorn.access")
    access_log.handlers = []
    access_log.propagate = False
    # logger health check
    logging.getLogger(__name__).debug(
        "Logging initialised",
        extra={"is_dev": settings.IS_DEV, "log_level": settings.LOG_LEVEL},
    )


def get_logger(name: str) -> logging.Logger:
    """Return a `logging.Logger` for *name*.

    Example Usage::

        logger = get_logger(__name__)

        logger.debug("Cache miss", extra={"key": "sessions:42"})
        logger.info("Room joined", extra={"room_id": "r1", "user_id": "u99"})
        logger.warning("Rate limit approaching", extra={"usage_pct": 92})
        logger.error("DB connection failed", extra={"host": "db:5432"})
        logger.exception("Unhandled error")   # includes full traceback
    """
    return logging.getLogger(name)
