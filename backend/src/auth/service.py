"""Authentication related services and management

This module provides authentication-related services and utilities for the application
including session management, token handling and more.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.crypto import check_password, hash_password
from src.auth.email import send_verification_email
from src.auth.exceptions import EmailExistsError, VerifyEmailTokenCooldownError
from src.auth.repository import (
    delete_verify_email_token,
    get_user_by_email,
    get_user_verify_email_token,
    insert_user,
    insert_verify_email_token,
    update_user_password,
    update_user_username,
)
from src.auth.schemas import SignupRequest
from src.auth.token import (
    check_verify_email_token_cooldown,
    generate_verify_email_token,
)
from src.models import User

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
        logger.debug(f"creating new user with email: {payload.email}")
        user = User(
            email=payload.email,
            username=payload.username,
            password=hash_password(payload.password),
        )
        user = await insert_user(db, user)
        logger.debug(
            f"creating new verify email token for user with email: {user.email}"
        )
        token = generate_verify_email_token(user.id)
        token = await insert_verify_email_token(db, token)
        logger.debug(f"sending verification email to user with email: {user.email}")
        await send_verification_email(user, token)
    else:
        logger.debug(f"user with email already exists: {user.email}")
        if user.verified:
            # verified user already exists so they are not permitted to signup again
            logger.debug(f"user with email is already verified: {user.email}")
            raise EmailExistsError(user.email)
        token = await get_user_verify_email_token(db, user.id)
        if token is None:
            # update the user password and username as well to remain consistent with what they expect
            if user.username != payload.username:
                logger.debug(f"updating username of user with email: {user.email}")
                user = await update_user_username(db, user.id, payload.username)
            if user.password:
                if not check_password(payload.password, user.password):
                    logger.debug(f"updating password of user with email: {user.email}")
                    user = await update_user_password(
                        db, user.id, hash_password(payload.password)
                    )
            # recreate the token to give the user another attempt to signup
            logger.debug(
                f"creating new verify email token for user with email: {user.email}"
            )
            token = generate_verify_email_token(user.id)
            token = await insert_verify_email_token(db, token)
            logger.debug(f"sending verification email to user with email: {user.email}")
            await send_verification_email(user, token)
            return
        # recreate the token only if enough time has passed since last attempt to prevent email spamming
        time_passed = check_verify_email_token_cooldown(token.created_at)
        if not time_passed:
            logger.debug(
                f"verify email token cooldown has not elapsed for user: {user.email}"
            )
            raise VerifyEmailTokenCooldownError(user.email)
        # update the user password and username as well to remain consistent with what they expect
        if user.username != payload.username:
            logger.debug(f"updating username of user with email: {user.email}")
            user = await update_user_username(db, user.id, payload.username)
        if user.password:
            if not check_password(payload.password, user.password):
                logger.debug(f"updating password of user with email: {user.email}")
                user = await update_user_password(
                    db, user.id, hash_password(payload.password)
                )
        logger.debug(f"deleting verify email token associated with user: {user.email}")
        await delete_verify_email_token(db, token)
        token = generate_verify_email_token(user.id)
        logger.debug(
            f"creating new verify email token for user with email: {user.email}"
        )
        token = await insert_verify_email_token(db, token)
        logger.debug(f"sending verification email to user with email: {user.email}")
        await send_verification_email(user, token)
