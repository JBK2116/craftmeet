"""
Module implementing JWT access token middleware for FastAPI/Starlette.

Provides JWTMiddleware class to authenticate requests using JWT tokens
stored in cookies, validate user existence, and handle errors.

Usage:

    router = APIRouter(dependencies=[Depends(get_current_user)])
"""

import uuid
from typing import Annotated

import jwt
from fastapi import (
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import InvalidTokenError as AuthInvalidTokenError
from src.auth.repository import get_user
from src.auth.token import decode_access_token
from src.database import get_db
from src.exceptions import DatabaseError
from src.models import User

DB = Annotated[AsyncSession, Depends(get_db)]


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="access token missing"
        )
    try:
        user = await _decode_access_token(token=token, db=db)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid access token"
            )
        request.state.user = user
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error occurred",
        ) from e


async def get_current_user_websocket(websocket: WebSocket, db: DB) -> None:
    """Verify JWT from WebSocket cookies and attach the authenticated user to websocket.state.

    Extracts the access token from the WebSocket cookies, decodes it, and
    validates the user ID. If a valid user is found, attaches it to
    `websocket.state.user`. Otherwise, raises a WebSocketException.

    Args:
        websocket: The incoming WebSocket connection containing the access token cookie.
        db: The database session dependency.

    Returns:
        None. The authenticated user is attached to `websocket.state.user`.

    Raises:
        WebSocketException: If token is missing, invalid, or the user does not exist
            (code WS_1008_POLICY_VIOLATION).
        WebSocketException: If a database error occurs (code WS_1013_TRY_AGAIN_LATER).
    """
    token = websocket.cookies.get("access_token", None)
    if token is None:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="access token missing"
        )
    try:
        user = await _decode_access_token(token=token, db=db)
        if not user:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION, reason="access token missing"
            )
        websocket.state.user = user
        return
    except DatabaseError as e:
        raise WebSocketException(
            code=status.WS_1013_TRY_AGAIN_LATER, reason="database error occurred"
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
        return user
    except (AuthInvalidTokenError, jwt.InvalidTokenError, ValueError):
        return None
