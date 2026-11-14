import logging
import uuid
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import get_user
from src.config import get_settings
from src.exceptions import DatabaseError
from src.mcp.schemas import ListMeetingsResponse, MeetingSummary
from src.meeting.repository import (
    get_meetings,
    insert_meeting,
    insert_question,
    insert_stat,
    insert_sub_question,
)
from src.meeting.schemas import MeetingIn
from src.meeting.utils import (
    generate_meeting_model,
    generate_question_model,
    generate_stat_model,
    generate_sub_question,
)
from src.models import Meeting, User

settings = get_settings()
logger = logging.getLogger(__name__)

NO_ACCOUNT_MESSAGE = (
    "No CraftMeet account found for this Google login. "
    "Sign up at https://craftmeet.live first, then try again."
)
NO_ACCESS_TOKEN_MESSAGE = "No access token found"  # noqa: S105
ACCOUNT_LOOKUP_FAILED_MESSAGE = "Account lookup failed. Please try again soon."
VERIFY_ACCOUNT_MESSAGE = (
    "Account is not verified to use the mcp. Verify the account and try again."
)


async def get_mcp_user(db: AsyncSession) -> User:
    """
    Retrieves the user associated with the provided mcp request.
    :param db: AsyncSession for querying the database.
    :return: The user if found, else None
    :raises ToolError If the email is not valid or not associated with an existing verified user.
    """
    token = get_access_token()
    if token is None:
        raise ToolError(NO_ACCESS_TOKEN_MESSAGE)
    email = token.claims.get("email", None)

    if not email or token.claims.get("email_verified") is False:
        logger.debug("mcp login has no usable verified email address.")
        raise ToolError(NO_ACCOUNT_MESSAGE)

    try:
        user = await get_user(db=db, email=email)
    except DatabaseError as exc:
        raise ToolError(ACCOUNT_LOOKUP_FAILED_MESSAGE) from exc

    if user is None:
        logger.debug("no craftmeet found for mcp login", extra={"email": email})
        raise ToolError(NO_ACCOUNT_MESSAGE)

    if not user.verified:
        logger.debug(
            "user is not verified to use mcp functionality", extra={"email": user.email}
        )
        raise ToolError(VERIFY_ACCOUNT_MESSAGE)

    return user


async def create_meeting_for_user(
    db: AsyncSession, user: User, payload: MeetingIn
) -> dict[str, Any]:
    """
    Creates a meeting for the user using the provided payload.
    :param db: Database session for database queries
    :param user: The user of the meeting.
    :param payload: The contents of the meeting.
    :return:
    """
    logger.info(
        "creating meeting",
        extra={
            "user_id": str(user.id),
            "title": payload.title,
            "question_count": len(payload.questions),
        },
    )
    meeting = generate_meeting_model(u_id=user.id, meeting=payload)
    meeting = await insert_meeting(db=db, meeting=meeting)

    for q in payload.questions:
        q_loaded = generate_question_model(meeting_id=meeting.id, question=q)
        q_loaded = await insert_question(db=db, question=q_loaded)
        sub_loaded = generate_sub_question(
            question_id=q_loaded.id,
            question_type=q_loaded.type,
            question=q.sub_question,
        )
        await insert_sub_question(db=db, question=sub_loaded)

    stat = generate_stat_model(meeting_id=meeting.id)
    await insert_stat(db=db, stat=stat)

    out = {
        "url": build_meeting_url(meeting_id=meeting.id),
        "title": meeting.title,
        "question_count": len(payload.questions),
        "response": "meeting created!",
        "room_code": meeting.room_code,
        "meeting_id": str(meeting.id),
    }

    await db.commit()

    logger.info(
        "meeting created successfully via mcp",
        extra={
            "meeting_id": str(meeting.id),
            "room_code": meeting.room_code,
            "question_count": len(payload.questions),
        },
    )
    return out


async def list_meetings_for_user(
    db: AsyncSession, user: User, limit: int, offset: int
) -> ListMeetingsResponse:
    """
    Lists the user's meetings as lightweight summaries.
    :param db: Database session for database queries.
    :param user: The user whose meetings to list.
    :param limit: Maximum number of meetings to return.
    :param offset: Number of meetings to skip for pagination.
    :return: Paginated list of meeting summaries.
    """
    logger.info(
        "listing meetings",
        extra={"user_id": str(user.id), "limit": limit, "offset": offset},
    )
    meetings: list[Meeting] = await get_meetings(
        db=db, u_id=user.id, limit=limit, offset=offset
    )
    summaries = [
        MeetingSummary(
            id=meeting.id,
            title=meeting.title,
            status=meeting.status,
            room_code=meeting.room_code,
            created_at=meeting.created_at,
            question_count=meeting.total_questions,
            url=build_meeting_url(meeting_id=meeting.id),
        )
        for meeting in meetings
    ]
    has_more = len(meetings) == limit
    next_offset = offset + len(meetings) if has_more else None
    logger.info(
        "meetings listed via mcp",
        extra={
            "user_id": str(user.id),
            "total_returned": len(summaries),
            "has_more": has_more,
        },
    )
    return ListMeetingsResponse(
        meetings=summaries,
        total_returned=len(summaries),
        has_more=has_more,
        next_offset=next_offset,
    )


def build_meeting_url(meeting_id: uuid.UUID) -> str:
    """
    Builds the url that hosts the provided meeting.
    :param meeting_id: ID of the meeting to host.
    :return: URL of the hosted meeting.
    """
    if settings.IS_DEV:
        return f"https://{settings.DOMAIN}/meetings/{str(meeting_id)}/host"
    else:
        return f"{settings.FRONTEND_URL}/meetings/{str(meeting_id)}/host"
