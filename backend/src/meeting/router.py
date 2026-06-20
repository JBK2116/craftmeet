import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import DatabaseError
from src.meeting.exceptions import MeetingNotFoundError
from src.meeting.schemas import MeetingIn, MeetingOut
from src.meeting.service import (
    handle_create_meeting,
    handle_get_meeting,
    handle_get_meetings,
)
from src.middleware.jwt import get_current_user
from src.types import ErrorTypes

meeting_router = APIRouter(
    prefix="/meetings",
    tags=["meeting"],
    strict_content_type=True,
    include_in_schema=True,
    dependencies=[Depends(get_current_user)],
)

logger = logging.getLogger(__name__)

DB = Annotated[AsyncSession, Depends(get_db)]
LIMIT = Annotated[int, Query(ge=1, le=100)]
OFFSET = Annotated[int, Query(ge=0, le=1000)]
MEETING_ID = Annotated[uuid.UUID, Path(title="The id of the meeting to fetch")]
# arbitrary value to prevent client side mismanagement, will be updated as the app scales


@meeting_router.post(
    "",
    response_model=MeetingOut,
    tags=["meeting"],
    status_code=status.HTTP_201_CREATED,
)
async def create_meeting(request: Request, db: DB, payload: MeetingIn):
    logger.debug("received create meeting payload", extra={"payload": payload})
    logger.debug(
        "current user found in request", extra={"user_email": request.state.user.email}
    )
    try:
        meeting_out = await handle_create_meeting(
            db=db, request=request, payload=payload
        )
        return meeting_out
    except (DatabaseError, ValidationError):
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@meeting_router.get("", response_model=list[MeetingOut], status_code=status.HTTP_200_OK)
async def get_meetings(request: Request, db: DB, limit: LIMIT = 20, offset: OFFSET = 0):
    logging.debug(
        "received get meetings payload", extra={"limit": limit, "offset": offset}
    )
    logger.debug(
        "current user found in request", extra={"user_email": request.state.user.email}
    )
    try:
        meetings = await handle_get_meetings(
            db=db, request=request, limit=limit, offset=offset
        )
        return meetings
    except DatabaseError:
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@meeting_router.get(
    "/{meeting_id}", response_model=MeetingOut, status_code=status.HTTP_200_OK
)
async def get_meeting(request: Request, db: DB, meeting_id: MEETING_ID):
    logger.debug("received get meeting payload", extra={"meeting_id": str(meeting_id)})
    logger.debug(
        "current user found in request", extra={"user_email": request.state.user.email}
    )
    try:
        meeting = await handle_get_meeting(db=db, m_id=meeting_id)
        return meeting
    except MeetingNotFoundError:
        return JSONResponse(
            content="Resource not found", status_code=status.HTTP_404_NOT_FOUND
        )
    except DatabaseError:
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
