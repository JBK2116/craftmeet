import logging

from fastapi import FastAPI, Request, status
from fastapi.concurrency import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from src.auth.router import (  # noqa: F401 - ensures oauth is registered at app startup
    auth_router,
    oauth,
)
from src.cache import close_redis, setup_redis
from src.config import get_settings
from src.limiter import limiter
from src.live.router import websocket_router
from src.logging_config import get_logger, setup_logging
from src.meeting.router import meeting_public_router, meeting_router
from src.middleware.request_logging import RequestLoggingMiddleware
from src.summary.router import summary_router

# initialise settings
settings = get_settings()

# intialise logger
setup_logging()
logging.getLogger("python_http_client").setLevel(logging.WARNING)
logger = get_logger(__name__)


# initialise redis
@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_redis()  # NOTE: ensure that redis server is started locally
    yield
    await close_redis()


app = FastAPI(
    debug=settings.IS_DEV,
    title="Craftmeet API",
    summary="Real-time meeting orchestration and AI-powered idea synthesis.",
    description=(
        "Craftmeet is a dynamic real-time meeting application designed to host structured, "
        "idea-driven sessions. Build meetings with a flexible set of interactive question formats, "
        "launch them live with your group, and walk away with an AI-generated summary of every "
        "idea your room produced. This API serves as the core backend powering session management, "
        "real-time collaboration, and intelligent summarisation."
    ),
    version="0.0.1",
    openapi_url="/openai.json",
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=True,
    root_path="/api/v1",
    strict_content_type=True,
    lifespan=lifespan,
)

# rate limiting integration
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # ty:ignore[invalid-argument-type]


# initialise middleware
if not settings.IS_DEV:
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.STARLETTE_SESSION_KEY,
    https_only=False if settings.IS_DEV else True,
)
app.add_middleware(RequestLoggingMiddleware)


# global exception handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    """
    Custom global exception handler designed to fail fast.

    Returns only the first validation error in the array of validation errors.
    """
    error = exc.errors()[0]
    field = error["loc"][-1]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "type": field,  # field name that failed validation
            "message": error["msg"].replace(
                "Value error, ", ""
            ),  # custom message returned from validators
        },
    )


# initialise sub routers
app.include_router(auth_router)
app.include_router(websocket_router)
app.include_router(meeting_router)
app.include_router(meeting_public_router)
app.include_router(summary_router)
