import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import InvalidTokenError
from src.database import get_db
from src.exceptions import DatabaseError
from src.meeting.exceptions import MeetingNotFoundError, MeetingNotLiveError
from src.meeting.schemas import JoinMeetingPayload, MeetingIn, MeetingOut, MeetingUpdate
from src.meeting.service import (
    handle_create_meeting,
    handle_delete_meeting,
    handle_delete_meetings,
    handle_get_meeting,
    handle_get_meetings,
    handle_join_meeting,
    handle_leave_meeting,
    handle_update_meeting,
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

meeting_public_router = APIRouter(
    prefix="/meetings",
    tags=["meeting"],
    strict_content_type=True,
    include_in_schema=True,
    dependencies=[],
)

logger = logging.getLogger(__name__)

DB = Annotated[AsyncSession, Depends(get_db)]
LIMIT = Annotated[int, Query(ge=1, le=100)]
OFFSET = Annotated[int, Query(ge=0, le=1000)]
MEETING_ID = Annotated[uuid.UUID, Path(title="The id of the meeting to fetch")]
# arbitrary value to prevent client side mismanagement, will be updated as the app scales


@meeting_public_router.post("/join", status_code=status.HTTP_200_OK)
async def join_meeting(
    request: Request, response: Response, db: DB, payload: JoinMeetingPayload
):
    logger.debug("received join meeting payload", extra={"payload": payload})

    try:
        await handle_join_meeting(
            db=db, request=request, response=response, payload=payload
        )
    except MeetingNotFoundError:
        return JSONResponse(
            content="resource not found", status_code=status.HTTP_404_NOT_FOUND
        )
    except MeetingNotLiveError:
        return JSONResponse(
            content="meeting is not live", status_code=status.HTTP_400_BAD_REQUEST
        )
    except DatabaseError:
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@meeting_public_router.post(
    "/{meeting_id}/leave", status_code=status.HTTP_204_NO_CONTENT
)
async def leave_meeting(response: Response, meeting_id: MEETING_ID) -> None:
    logger.debug(
        "received leave meeting request", extra={"meeting_id": str(meeting_id)}
    )
    await handle_leave_meeting(response=response, m_id=meeting_id)


@meeting_router.post(
    "",
    response_model=MeetingOut,
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
        meeting = await handle_get_meeting(db=db, request=request, m_id=meeting_id)
        return meeting
    except MeetingNotFoundError:
        return JSONResponse(
            content="Resource not found", status_code=status.HTTP_404_NOT_FOUND
        )
    except InvalidTokenError:
        return JSONResponse(
            content="Invalid token provided", status_code=status.HTTP_401_UNAUTHORIZED
        )
    except DatabaseError:
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@meeting_router.patch(
    path="/{meeting_id}", response_model=MeetingOut, status_code=status.HTTP_200_OK
)
async def update_meeting(
    request: Request, db: DB, meeting_id: MEETING_ID, payload: MeetingUpdate
):
    logger.debug(
        "received update meeting payload",
        extra={"meeting_id": str(meeting_id), "payload": payload},
    )
    logger.debug(
        "current user found in request", extra={"user_email": request.state.user.email}
    )
    try:
        meeting_out = await handle_update_meeting(
            db=db, request=request, meeting_update=payload, m_id=meeting_id
        )
        return meeting_out
    except MeetingNotFoundError:
        return JSONResponse(
            content="Resource not found", status_code=status.HTTP_404_NOT_FOUND
        )
    except InvalidTokenError:
        return JSONResponse(
            content="Invalid token provided",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    except DatabaseError:
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@meeting_router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(request: Request, db: DB, meeting_id: MEETING_ID):
    logger.debug("received delete meeting request", extra={"id": meeting_id})
    logger.debug(
        "current user found in request", extra={"user_id": request.state.user.email}
    )
    try:
        await handle_delete_meeting(db=db, request=request, m_id=meeting_id)
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


@meeting_router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meetings(db: DB, request: Request):
    logger.debug("received delete meetings request")
    logger.debug(
        "current user found in request", extra={"user_email": request.state.user.email}
    )
    try:
        await handle_delete_meetings(db=db, request=request)
    except DatabaseError:
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
