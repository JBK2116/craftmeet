"""
Module implementing JWT access token middleware for FastAPI/Starlette.

Provides JWTMiddleware class to authenticate requests using JWT tokens
stored in cookies, validate user existence, and handle errors.

Usage:

    router = APIRouter(dependencies=[Depends(get_current_user)])
"""

import logging
import uuid

import jwt
from fastapi import (
    HTTPException,
    Path,
    Request,
    WebSocket,
    WebSocketException,
    status,
)
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import InvalidTokenError as AuthInvalidTokenError
from src.auth.repository import get_user
from src.auth.token import decode_access_token, decode_participants_meeting_access_token
from src.database import AsyncSessionLocal
from src.exceptions import DatabaseError
from src.models import Meeting, User
from src.types import DB, MeetingStatus
from src.utils import generate_participants_meeting_access_token_key

logger = logging.getLogger(__name__)


async def get_current_user(request: Request, db: DB) -> None:
    """Verify JWT from request cookies and attach the authenticated user to request.state.

    Extracts the access token from the request cookies, decodes it, and
    validates the user ID. If a valid user is found, attaches it to
    `request.state.user`. Otherwise, raises an HTTPException.

    Args:
        request: The incoming HTTP request containing the access token cookie.
        db: The database session dependency.

    Returns:
        None. The authenticated user is attached to `request.state.user`.

    Raises:
        HTTPException: If token is missing, invalid, or the user does not exist
            (status 401 UNAUTHORIZED).
        HTTPException: If a database error occurs (status 500 INTERNAL_SERVER_ERROR).
    """
    token = request.cookies.get("access_token")
    if token is None:
        logger.warning("access token missing from cookies")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="access token missing"
        )
    try:
        user = await _decode_access_token(token=token, db=db)
        if user is None:
            logger.warning("invalid access token", extra={"token_present": True})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid access token"
            )
        request.state.user = user
        logger.debug(
            "user authenticated via jwt",
            extra={"user_id": str(user.id), "email": user.email},
        )
    except DatabaseError as e:
        logger.exception("database error during jwt authentication")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error occurred",
        ) from e


async def get_current_user_websocket(websocket: WebSocket) -> None:
    """Verify JWT from WebSocket cookies and attach the authenticated user to websocket.state.

    Extracts the access token from the WebSocket cookies, decodes it, and
    validates the user ID. If a valid user is found, attaches it to
    `websocket.state.user`. Otherwise, raises a WebSocketException.

    Opens a short-lived DB session for the token lookup so no connection
    is held open for the lifetime of the WebSocket.

    Args:
        websocket: The incoming WebSocket connection containing the access token cookie.

    Returns:
        None. The authenticated user is attached to `websocket.state.user`.

    Raises:
        WebSocketException: If token is missing, invalid, or the user does not exist
            (code WS_1008_POLICY_VIOLATION).
        WebSocketException: If a database error occurs (code WS_1013_TRY_AGAIN_LATER).
    """
    token = websocket.cookies.get("access_token", None)
    if token is None:
        logger.warning("access token missing from websocket cookies")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="access token missing"
        )
    try:
        async with AsyncSessionLocal() as session:
            user = await _decode_access_token(token=token, db=session)
            if not user:
                logger.warning(
                    "invalid access token on websocket",
                    extra={"token_present": True},
                )
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION, reason="invalid access token"
                )
            websocket.state.user = user
            logger.debug(
                "websocket user authenticated via jwt",
                extra={"user_id": str(user.id), "email": user.email},
            )
    except DatabaseError as e:
        logger.exception("database error during websocket jwt authentication")
        raise WebSocketException(
            code=status.WS_1013_TRY_AGAIN_LATER, reason="database error occurred"
        ) from e


async def get_current_participant_websocket(
    websocket: WebSocket, meeting_id: uuid.UUID = Path()
) -> None:
    """
    Authenticate a WebSocket connection by retrieving and validating
    the participant access token from cookies.

    This dependency extracts the meeting-specific access token from the
    WebSocket's cookies, decodes it, and sets the authenticated
    participant ID on the websocket state alongside the meeting ID.

    Args:
        websocket: The active WebSocket connection.
        meeting_id: The unique identifier of the meeting, extracted
            from the path.

    Raises:
        WebSocketException: If the access token is missing or invalid
            (HTTP status 1008).
    """
    key = generate_participants_meeting_access_token_key(m_id=str(meeting_id))
    token = websocket.cookies.get(key, None)
    if token is None:
        logger.warning(
            "participant access token missing from websocket cookies",
            extra={"meeting_id": str(meeting_id)},
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="access token missing"
        )
    try:
        claims = decode_participants_meeting_access_token(token=token)
        p_id = uuid.UUID(claims["participant_id"])
        m_id = uuid.UUID(claims["meeting_id"])
        stmt = select(Meeting.id).where(
            Meeting.id == m_id,
            or_(
                Meeting.status == MeetingStatus.DRAFT,
                Meeting.status == MeetingStatus.LIVE,
            ),
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt)
            db_id = result.scalar_one_or_none()
        if db_id is None:
            logger.warning(
                "invalid participant access token: meeting not live or not found",
                extra={"meeting_id": str(m_id)},
            )
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION, reason="invalid access token"
            )
        if m_id != meeting_id:
            logger.warning(
                "participant access token meeting_id mismatch",
                extra={
                    "token_meeting_id": str(m_id),
                    "path_meeting_id": str(meeting_id),
                },
            )
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION, reason="invalid access token"
            )
        websocket.state.participant_id = p_id
        websocket.state.meeting_id = m_id
        logger.debug(
            "websocket participant authenticated",
            extra={
                "meeting_id": str(m_id),
                "participant_id": str(p_id),
            },
        )
    except AuthInvalidTokenError as e:
        logger.warning(
            "failed to decode participant access token",
            extra={"meeting_id": str(meeting_id)},
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="invalid access token"
        ) from e
    except KeyError as e:
        logger.warning(
            "participant access token missing required claim",
            extra={"meeting_id": str(meeting_id), "missing_key": str(e)},
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="invalid access token"
        ) from e


async def _decode_access_token(token: str, db: AsyncSession) -> User | None:
    """
    Decode and validate an access token, then retrieve the corresponding user.

    This function attempts to decode the provided JWT access token, extract the user ID
    from the token's claims, and fetch the matching user record from the database.
    If the token is invalid, expired, or malformed, or if the user does not exist,
    it returns None.

    Args:
        token (str): The JWT access token to decode.
        db (AsyncSession): The asynchronous database session for querying.

    Returns:
        User | None: The User object if the token is valid and the user exists, otherwise None.

    Raises:
        None: All exceptions are caught internally, and None is returned instead.
    """
    try:
        claims = decode_access_token(token=token)
        user_id = uuid.UUID(hex=claims["user_id"])
        user = await get_user(db=db, u_id=user_id)
        if user is None:
            logger.warning(
                "decoded access token but user not found",
                extra={"user_id": str(user_id)},
            )
        return user
    except (AuthInvalidTokenError, jwt.InvalidTokenError, ValueError):
        logger.debug("access token decode failed or invalid")
        return None
