import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import DatabaseError
from src.meeting.schemas import MeetingIn, MeetingOut
from src.meeting.service import handle_create_meeting
from src.middleware.jwt import get_current_user
from src.types import ErrorTypes

meeting_router = APIRouter(
    prefix="/meeting",
    tags=["meeting"],
    strict_content_type=True,
    include_in_schema=True,
    dependencies=[Depends(get_current_user)],
)

logger = logging.getLogger(__name__)

DB = Annotated[AsyncSession, Depends(get_db)]


@meeting_router.post(
    "/create",
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
