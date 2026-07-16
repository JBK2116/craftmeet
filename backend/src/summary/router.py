import logging
import uuid

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import FileResponse, JSONResponse

from src.exceptions import DatabaseError
from src.limiter import limiter
from src.meeting.exceptions import MeetingNotFoundError
from src.middleware.jwt import get_current_user
from src.models import User
from src.summary.exceptions import MeetingNotEndedError, OpenAiError, PdfGenerationError
from src.summary.service import handle_summary
from src.types import DB
from src.utils import ip_or_user_key_func

summary_router = APIRouter(
    prefix="/meetings",
    tags=["summary"],
    strict_content_type=True,
    include_in_schema=True,
    dependencies=[Depends(get_current_user)],
)

logger = logging.getLogger(__name__)


@summary_router.post("/{meeting_id}/summary")
@limiter.limit("5/hour", key_func=ip_or_user_key_func)
async def summarize_meeting(request: Request, db: DB, meeting_id: uuid.UUID):
    user: User = request.state.user
    logger.debug("received summarize meeting request", extra={"meeting_id": meeting_id})
    logger.debug("user found in request", extra={"user": user.email})
    try:
        path = await handle_summary(db=db, meeting_id=meeting_id)
        return FileResponse(
            path=str(path),
            media_type="application/pdf",
            filename=f"craftmeet-summary-{str(meeting_id)}.pdf",
            status_code=status.HTTP_200_OK,
        )
    except MeetingNotFoundError:
        return JSONResponse(
            content="meeting has not been found", status_code=status.HTTP_404_NOT_FOUND
        )
    except MeetingNotEndedError:
        return JSONResponse(
            content="meeting has not ended yet", status_code=status.HTTP_400_BAD_REQUEST
        )
    except OpenAiError:
        return JSONResponse(
            content="error generating summary",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except PdfGenerationError:
        return JSONResponse(
            content="error generating pdf summary",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except DatabaseError:
        return JSONResponse(
            content="database error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
