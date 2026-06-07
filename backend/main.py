import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.auth.router import auth_router
from src.config import get_settings
from src.logging_config import get_logger, setup_logging

# initialise settings
settings = get_settings()

# intialise logger
setup_logging()
logging.getLogger("python_http_client").setLevel(logging.WARNING)
logger = get_logger(__name__)


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
)


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
