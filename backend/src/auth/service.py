"""Authentication related services and management

This module provides authentication-related services and utilities for the application
including session management, token handling and more.
"""

import logging

from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.crypto import check_password, hash_password
from src.auth.email import send_verification_email
from src.auth.exceptions import (
    EmailExistsError,
    EmailNotVerifiedError,
    UserInvalidPasswordError,
    UserNotFoundError,
    VerifyEmailTokenCooldownError,
)
from src.auth.repository import (
    delete_refresh_tokens,
    delete_verify_email_token,
    get_user_by_email,
    get_user_verify_email_token,
    insert_refresh_token,
    insert_user,
    insert_verify_email_token,
    update_user_password,
    update_user_username,
)
from src.auth.schemas import LoginRequest, SignupRequest
from src.auth.token import (
    check_verify_email_token_cooldown,
    generate_access_token,
    generate_refresh_token,
    generate_verify_email_token,
)
from src.config import get_settings
from src.models import User

settings = get_settings()
logger = logging.getLogger(__name__)


async def handle_signup(db: AsyncSession, payload: SignupRequest) -> None:
    """
    Handle user signup functionality.

    Register the user for signup if all conditions are met.
    This results in the user receiving an email with a limited duration token,
    used to verify their email and then prompt them to login.

    Args:
        db: Async database session
        payload: User signup details
    """
    user = await get_user_by_email(db, payload.email)
    if not user:
        # create a new user, token and send the email to begin their signup process
        logger.debug("creating new user", extra={"email": payload.email})
        user = User(
            email=payload.email,
            username=payload.username,
            password=hash_password(payload.password),
        )
        user = await insert_user(db, user)
        logger.debug("creating new verify email token", extra={"email": user.email})
        token = generate_verify_email_token(user.id)
        token = await insert_verify_email_token(db, token)
        logger.debug("sending verification email", extra={"email": user.email})
        await send_verification_email(user, token)
    else:
        logger.debug("user already exists", extra={"email": user.email})
        if user.verified:
            # verified user already exists so they are not permitted to signup again
            logger.debug("user is already verified", extra={"email": user.email})
            raise EmailExistsError(user.email)
        token = await get_user_verify_email_token(db, user.id)
        if token is None:
            # update the user password and username as well to remain consistent with what they expect
            if user.username != payload.username:
                logger.debug("updating username", extra={"email": user.email})
                user = await update_user_username(db, user.id, payload.username)
            if user.password:
                if not check_password(payload.password, user.password):
                    logger.debug("updating password", extra={"email": user.email})
                    user = await update_user_password(
                        db, user.id, hash_password(payload.password)
                    )
            # recreate the token to give the user another attempt to signup
            logger.debug("creating new verify email token", extra={"email": user.email})
            token = generate_verify_email_token(user.id)
            token = await insert_verify_email_token(db, token)
            logger.debug("sending verification email", extra={"email": user.email})
            await send_verification_email(user, token)
            return
        # recreate the token only if enough time has passed since last attempt to prevent email spamming
        time_passed = check_verify_email_token_cooldown(token.created_at)
        if not time_passed:
            logger.debug(
                "verify email token cooldown has not elapsed",
                extra={"email": user.email},
            )
            raise VerifyEmailTokenCooldownError(user.email)
        # update the user password and username as well to remain consistent with what they expect
        if user.username != payload.username:
            logger.debug("updating username", extra={"email": user.email})
            user = await update_user_username(db, user.id, payload.username)
        if user.password:
            if not check_password(payload.password, user.password):
                logger.debug("updating password", extra={"email": user.email})
                user = await update_user_password(
                    db, user.id, hash_password(payload.password)
                )
        logger.debug("deleting verify email token", extra={"email": user.email})
        await delete_verify_email_token(db, token)
        token = generate_verify_email_token(user.id)
        logger.debug("creating new verify email token", extra={"email": user.email})
        token = await insert_verify_email_token(db, token)
        logger.debug("sending verification email", extra={"email": user.email})
        await send_verification_email(user, token)


async def handle_login(
    db: AsyncSession, payload: LoginRequest, response: Response
) -> User:
    user = await get_user_by_email(db, payload.email)
    if user is None:
        logger.debug("user not found in database", extra={"email": payload.email})
        raise UserNotFoundError(payload.email)
    # perform a standard password check to ensure the user has provided the correct credentials
    # if the password is None, then the user signed up with oauth so just provide a simple error message for security
    if user.password is None:
        logger.debug(
            "user signed up with oauth, cannot login with password",
            extra={"email": user.email},
        )
        raise UserInvalidPasswordError(user.email)
    ok = check_password(payload.password, user.password)
    if not ok:
        logger.debug("invalid password provided", extra={"email": user.email})
        raise UserInvalidPasswordError(user.email)
    # resend a verify email message to the user prompting them to verify their account so they can login
    # only resend the message if the token cooldown has passed else, just prompt them to check their email to prevent spam
    if not user.verified:
        token = await get_user_verify_email_token(db, user.id)
        if token is None:
            logger.debug("creating new verify email token", extra={"email": user.email})
            token = generate_verify_email_token(user.id)
            token = await insert_verify_email_token(db, token)
            logger.debug("sending verification email", extra={"email": user.email})
            await send_verification_email(user, token)
            raise EmailNotVerifiedError(user.email)
        time_passed = check_verify_email_token_cooldown(token.created_at)
        if not time_passed:
            logger.debug(
                "verify email token cooldown has not elapsed",
                extra={"email": user.email},
            )
            raise EmailNotVerifiedError(user.email)
        logger.debug("deleting verify email token", extra={"email": user.email})
        await delete_verify_email_token(db, token)
        token = generate_verify_email_token(user.id)
        token = await insert_verify_email_token(db, token)
        logger.debug("resending verification email", extra={"email": user.email})
        await send_verification_email(user, token)
        raise EmailNotVerifiedError(user.email)
    # create the jwt tokens to handle user authentication now that they are logged in
    # tokens must be handle as httponly on the frontend
    # additionally the user's refresh tokens must be cleared for security purposes
    logger.debug("creating jwt tokens", extra={"email": user.email})
    access_t = generate_access_token(user.id)
    refresh_t = generate_refresh_token(user.id)
    await delete_refresh_tokens(db, user.id)
    refresh_t = await insert_refresh_token(db, refresh_t)
    # max_age expects seconds so adjust the value accordingly
    response.set_cookie(
        key="access_token",
        value=access_t,
        httponly=True,
        secure=False if settings.IS_DEV else True,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_TTL_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_t.token_hash,
        httponly=True,
        secure=False if settings.IS_DEV else True,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_TTL_HOURS * 60 * 60,
    )
    logger.debug("user login successful", extra={"email": user.email})
    return user
