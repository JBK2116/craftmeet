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
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import get_user
from src.auth.token import decode_access_token
from src.database import get_db
from src.exceptions import DatabaseError

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        claims = decode_access_token(token=token)
        user_id = uuid.UUID(hex=claims["user_id"])
        user = await get_user(db=db, u_id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        request.state.user = user
    except (jwt.InvalidTokenError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from e
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e
