import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.meeting.schemas import MeetingIn, MeetingOut
from src.middleware.jwt import get_current_user

meeting_router = APIRouter(
    prefix="/meeting",
    tags=["meeting"],
    strict_content_type=True,
    include_in_schema=True,
    dependencies=[Depends(get_current_user)],
)

logger = logging.getLogger(__name__)

DB = Annotated[AsyncSession, Depends(get_db)]


@meeting_router.post("/create", response_model=MeetingOut, tags=["meeting"])
async def create_meeting(request: Request, db: DB, payload: MeetingIn):
    logger.debug("recieved create meeting payload", extra={"payload": payload})
    logger.debug(
        "current user found in request", extra={"user_email": request.state.user.email}
    )
    return Response(status_code=status.HTTP_200_OK)
