import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import (
    EmailDeliveryError,
    EmailExistsError,
    EmailNotVerifiedError,
    InvalidTokenError,
    UserInvalidPasswordError,
    UserNotFoundError,
    VerifyEmailTokenCooldownError,
)
from src.auth.schemas import LoginRequest, SignupRequest, UserOut, VerifyEmailRequest
from src.auth.service import (
    handle_login,
    handle_me,
    handle_refresh,
    handle_signup,
    handle_verify_email,
)
from src.database import get_db
from src.exceptions import DatabaseError
from src.types import ErrorTypes

logger = logging.getLogger(__name__)

# Annotated values for reusability
DB = Annotated[AsyncSession, Depends(get_db)]
Access_Token = Annotated[str | None, Cookie()]
Refresh_Token = Annotated[str | None, Cookie()]

auth_router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    strict_content_type=True,
    include_in_schema=True,
)


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(db: DB, payload: SignupRequest):
    logger.debug(msg="Received signup payload", extra={"payload": payload})
    try:
        await handle_signup(db=db, payload=payload)
    except (DatabaseError, EmailDeliveryError):
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except EmailExistsError:
        return JSONResponse(
            content={
                "type": ErrorTypes.EMAIL_ALREADY_EXISTS.type,
                "message": ErrorTypes.EMAIL_ALREADY_EXISTS.message,
            },
            status_code=status.HTTP_409_CONFLICT,
        )
    except VerifyEmailTokenCooldownError:
        return JSONResponse(
            content={
                "type": ErrorTypes.VERIFY_EMAIL_TOKEN_COOLDOWN.type,
                "message": ErrorTypes.VERIFY_EMAIL_TOKEN_COOLDOWN.message,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@auth_router.post("/login", status_code=status.HTTP_200_OK, response_model=UserOut)
async def login(db: DB, response: Response, payload: LoginRequest):
    logger.debug(msg="Received login payload", extra={"payload": payload})
    try:
        user = await handle_login(db=db, payload=payload, response=response)
        return user

    except (DatabaseError, EmailDeliveryError):
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except EmailNotVerifiedError:
        return JSONResponse(
            content={
                "type": ErrorTypes.EMAIL_NOT_VERIFIED.type,
                "message": ErrorTypes.EMAIL_NOT_VERIFIED.message,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    except (UserNotFoundError, UserInvalidPasswordError):
        return JSONResponse(
            content={
                "type": ErrorTypes.INVALID_CREDENTIALS.type,
                "message": ErrorTypes.INVALID_CREDENTIALS.message,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


@auth_router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(db: DB, payload: VerifyEmailRequest):
    logger.debug(msg="Received verify email payload", extra={"payload": payload})
    try:
        await handle_verify_email(db=db, payload=payload)
    except DatabaseError:
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except InvalidTokenError:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)


@auth_router.get("/me", status_code=status.HTTP_200_OK, response_model=UserOut)
async def me(db: DB, access_token: Access_Token):
    logger.debug("Received access token", extra={"token": access_token})
    if access_token is None:
        raise InvalidTokenError
    try:
        user = await handle_me(db=db, access_token=access_token)
        return user
    except DatabaseError:
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except InvalidTokenError:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)


@auth_router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(db: DB, response: Response, refresh_token: Refresh_Token):
    logger.debug("Received refresh token", extra={"token": refresh_token})
    if refresh_token is None:
        raise InvalidTokenError
    try:
        await handle_refresh(db=db, response=response, refresh_token=refresh_token)
    except DatabaseError:
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except InvalidTokenError:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
