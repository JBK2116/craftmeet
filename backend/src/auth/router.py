import logging

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse

from src.auth.exceptions import (
    EmailDeliveryError,
    EmailExistsError,
    EmailNotVerifiedError,
    InvalidTokenError,
    UserInvalidPasswordError,
    UserNotFoundError,
    VerifyEmailTokenCooldownError,
)
from src.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    MeRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserOut,
    VerifyEmailRequest,
)
from src.auth.service import (
    handle_forgot_password,
    handle_google_login,
    handle_login,
    handle_logout,
    handle_me,
    handle_refresh,
    handle_reset_password,
    handle_signup,
    handle_update_me,
    handle_verify_email,
)
from src.config import get_settings
from src.exceptions import DatabaseError
from src.middleware.jwt import get_current_user
from src.types import DB, Access_Token, ErrorTypes, Refresh_Token

settings = get_settings()

logger = logging.getLogger(__name__)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid profile email"},
)

# Annotated values for reusability

auth_router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    strict_content_type=True,
    include_in_schema=True,
)


@auth_router.get("/google")
async def google_login(request: Request):
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)


@auth_router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: DB):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        logger.exception("Google OAuth token exchange failed")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND,
        )

    user_info = token.get("userinfo")
    if not user_info:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND,
        )

    redirect = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/dashboard",
        status_code=status.HTTP_302_FOUND,
    )
    try:
        await handle_google_login(db=db, user_info=user_info, response=redirect)
    except (DatabaseError, KeyError):
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND,
        )
    return redirect


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


@auth_router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(db: DB, response: Response, refresh_token: Refresh_Token):
    logger.debug(
        "received logout refresh token", extra={"refresh_token": refresh_token}
    )
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    try:
        if refresh_token is None:
            response.status_code = status.HTTP_204_NO_CONTENT
            return response
        await handle_logout(db=db, refresh_token=refresh_token)
        response.status_code = status.HTTP_204_NO_CONTENT
    except DatabaseError:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return response
    except InvalidTokenError:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response
    return response


@auth_router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(db: DB, payload: VerifyEmailRequest):
    logger.debug(msg="Received verify email payload", extra={"payload": payload})
    try:
        await handle_verify_email(db=db, payload=payload)
    except DatabaseError:
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except InvalidTokenError:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)


@auth_router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(db: DB, payload: ForgotPasswordRequest):
    logger.debug("Received forgot-password payload", extra={"payload": payload})
    try:
        await handle_forgot_password(db=db, payload=payload)
    except (DatabaseError, EmailDeliveryError):
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@auth_router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(db: DB, payload: ResetPasswordRequest):
    logger.debug("Received reset-password payload", extra={"payload": payload})
    try:
        await handle_reset_password(db=db, payload=payload)
    except DatabaseError:
        return JSONResponse(
            content={
                "type": ErrorTypes.SERVER.type,
                "message": ErrorTypes.SERVER.message,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except InvalidTokenError:
        return JSONResponse(
            content={
                "type": ErrorTypes.TOKEN.type,
                "message": ErrorTypes.TOKEN.message,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@auth_router.get("/me", status_code=status.HTTP_200_OK, response_model=UserOut)
async def me(db: DB, access_token: Access_Token = None):
    logger.debug("Received access token", extra={"token": access_token})
    if access_token is None:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        user = await handle_me(db=db, access_token=access_token)
        return user
    except DatabaseError:
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except InvalidTokenError:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)


@auth_router.patch(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserOut,
    dependencies=[Depends(get_current_user)],
)
async def update_me(db: DB, request: Request, payload: MeRequest):
    logger.debug("Received update user payload", extra={"payload": payload})
    logger.debug(
        "User found in request", extra={"user_email": request.state.user.email}
    )
    user = await handle_update_me(db=db, request=request, payload=payload)
    return user


@auth_router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(db: DB, response: Response, refresh_token: Refresh_Token = None):
    logger.debug("Received refresh token", extra={"token": refresh_token})
    if refresh_token is None:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        await handle_refresh(db=db, response=response, refresh_token=refresh_token)
    except DatabaseError:
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except InvalidTokenError:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
