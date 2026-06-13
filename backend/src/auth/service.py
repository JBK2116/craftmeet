"""Authentication related services and management

This module provides authentication-related services and utilities for the application
including session management, token handling and more.
"""

import datetime
import logging
import uuid

from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.crypto import check_password, hash_password
from src.auth.email import send_reset_password_email, send_verification_email
from src.auth.exceptions import (
    EmailExistsError,
    EmailNotVerifiedError,
    InvalidTokenError,
    UserInvalidPasswordError,
    UserNotFoundError,
    VerifyEmailTokenCooldownError,
)
from src.auth.repository import (
    delete_refresh_tokens,
    delete_reset_password_tokens,
    delete_verify_email_token,
    get_refresh_token,
    get_reset_password_token,
    get_user,
    get_verify_email_token,
    insert_refresh_token,
    insert_reset_password_token,
    insert_user,
    insert_verify_email_token,
    update_reset_password_token,
    update_user,
)
from src.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    VerifyEmailRequest,
)
from src.auth.token import (
    check_reset_password_cooldown,
    check_reset_password_token_expiry,
    check_verify_email_token_cooldown,
    check_verify_email_token_expiry,
    decode_access_token,
    decode_refresh_token,
    generate_access_token,
    generate_refresh_token,
    generate_reset_password_token,
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
    user = await get_user(db=db, email=payload.email)
    if not user:
        # create a new user, token and send the email to begin their signup process
        logger.debug("creating new user", extra={"email": payload.email})
        user = User(
            email=payload.email,
            username=payload.username,
            password=hash_password(raw=payload.password),
        )
        user = await insert_user(db=db, user=user)
        logger.debug("creating new verify email token", extra={"email": user.email})
        token = generate_verify_email_token(u_id=user.id)
        token = await insert_verify_email_token(db=db, token=token)
        logger.debug("sending verification email", extra={"email": user.email})
        await send_verification_email(user=user, token=token)
    else:
        logger.debug("user already exists", extra={"email": user.email})
        if user.verified:
            # verified user already exists so they are not permitted to signup again
            logger.debug("user is already verified", extra={"email": user.email})
            raise EmailExistsError(user.email)
        token = await get_verify_email_token(db=db, u_id=user.id)
        if token is None:
            # update the user password and username as well to remain consistent with what they expect
            if user.username != payload.username:
                logger.debug("updating username", extra={"email": user.email})
                user = await update_user(db=db, u_id=user.id, username=payload.username)
            if user.password:
                if not check_password(raw=payload.password, hashed=user.password):
                    logger.debug("updating password", extra={"email": user.email})
                    user = await update_user(
                        db=db,
                        u_id=user.id,
                        password=hash_password(raw=payload.password),
                    )
            # recreate the token to give the user another attempt to signup
            logger.debug("creating new verify email token", extra={"email": user.email})
            token = generate_verify_email_token(u_id=user.id)
            token = await insert_verify_email_token(db=db, token=token)
            logger.debug("sending verification email", extra={"email": user.email})
            await send_verification_email(user=user, token=token)
            return
        # recreate the token only if enough time has passed since last attempt to prevent email spamming
        time_passed = check_verify_email_token_cooldown(created_at=token.created_at)
        if not time_passed:
            logger.debug(
                "verify email token cooldown has not elapsed",
                extra={"email": user.email},
            )
            raise VerifyEmailTokenCooldownError(user.email)
        # update the user password and username as well to remain consistent with what they expect
        if user.username != payload.username:
            logger.debug("updating username", extra={"email": user.email})
            user = await update_user(db=db, u_id=user.id, username=payload.username)
        if user.password:
            if not check_password(raw=payload.password, hashed=user.password):
                logger.debug("updating password", extra={"email": user.email})
                user = await update_user(
                    db=db, u_id=user.id, password=hash_password(raw=payload.password)
                )
        logger.debug("deleting verify email token", extra={"email": user.email})
        await delete_verify_email_token(db=db, token=token)
        token = generate_verify_email_token(u_id=user.id)
        logger.debug("creating new verify email token", extra={"email": user.email})
        token = await insert_verify_email_token(db=db, token=token)
        logger.debug("sending verification email", extra={"email": user.email})
        await send_verification_email(user=user, token=token)


async def handle_login(
    db: AsyncSession, response: Response, payload: LoginRequest
) -> User:
    """
    Handle user login functionality.

    Authenticates a user by verifying their email and password credentials.
    If the user's email is not verified, resends a verification email.
    Upon successful authentication, generates JWT tokens (access and refresh)
    and sets them as HttpOnly cookies in the response.

    Args:
        db: Async database session
        payload: User login credentials (email and password)
        response: FastAPI Response object to set authentication cookies

    Returns:
        User: The authenticated user object

    Raises:
        UserNotFoundError: If the user does not exist in the database
        UserInvalidPasswordError: If the password is invalid or user signed up with OAuth
        EmailNotVerifiedError: If the user's email is not verified
    """
    user = await get_user(db=db, email=payload.email)
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
    ok = check_password(raw=payload.password, hashed=user.password)
    if not ok:
        logger.debug("invalid password provided", extra={"email": user.email})
        raise UserInvalidPasswordError(user.email)
    # resend a verify email message to the user prompting them to verify their account so they can login
    # only resend the message if the token cooldown has passed else, just prompt them to check their email to prevent spam
    if not user.verified:
        token = await get_verify_email_token(db=db, u_id=user.id)
        if token is None:
            logger.debug("creating new verify email token", extra={"email": user.email})
            token = generate_verify_email_token(u_id=user.id)
            token = await insert_verify_email_token(db=db, token=token)
            logger.debug("sending verification email", extra={"email": user.email})
            await send_verification_email(user=user, token=token)
            raise EmailNotVerifiedError(user.email)
        time_passed = check_verify_email_token_cooldown(created_at=token.created_at)
        if not time_passed:
            logger.debug(
                "verify email token cooldown has not elapsed",
                extra={"email": user.email},
            )
            raise EmailNotVerifiedError(user.email)
        await delete_verify_email_token(db=db, token=token)
        token = generate_verify_email_token(u_id=user.id)
        token = await insert_verify_email_token(db=db, token=token)
        logger.debug("resending verification email", extra={"email": user.email})
        await send_verification_email(user=user, token=token)
        raise EmailNotVerifiedError(user.email)
    # create the jwt tokens to handle user authentication now that they are logged in
    # tokens must be handled as HttpOnly on the frontend
    # additionally the user's refresh tokens must be cleared for security purposes
    logger.debug("creating jwt tokens", extra={"email": user.email})
    access_t = generate_access_token(u_id=user.id)
    refresh_t = generate_refresh_token(u_id=user.id)
    await delete_refresh_tokens(db=db, u_id=user.id)
    refresh_t = await insert_refresh_token(db=db, token=refresh_t)
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


async def handle_logout(db: AsyncSession, refresh_token: str) -> None:
    """
    Handle user logout functionality.

    Decodes the provided refresh token, validates it, and deletes all refresh tokens
    associated with the user from the database to invalidate all active sessions.

    Args:
        db: Async database session
        refresh_token: JWT refresh token string

    Raises:
        InvalidTokenError: If the token is invalid, malformed,
                          user_id is not found in claims, or user_id format is invalid
    """
    logger.debug("decoding refresh token")
    claims = decode_refresh_token(token=refresh_token, return_anyway=True)
    user_id = claims.get("user_id")
    if user_id is None:
        logger.debug("user_id not found in token claims")
        raise InvalidTokenError
    try:
        user_id = uuid.UUID(hex=user_id)
    except Exception as e:
        logger.debug("invalid user_id format in token", extra={"user_id": user_id})
        raise InvalidTokenError from e
    logger.debug("deleting all refresh tokens", extra={"user_id": user_id})
    await delete_refresh_tokens(db=db, u_id=user_id)
    logger.debug("user logout successful", extra={"user_id": user_id})
    return


async def handle_forgot_password(
    db: AsyncSession, payload: ForgotPasswordRequest
) -> None:
    """
    Handle forgot password functionality.

    Looks up the user by email and sends a password reset email if the user
    exists. If a reset token already exists, checks the cooldown period before
    rotating the token and resending the email. The response is always identical
    regardless of whether the email matches a real user, following security best
    practices to prevent email enumeration.

    Args:
        db: Async database session
        payload: Forgot password request containing the user's email

    Raises:
        EmailDeliveryError: If the reset password email fails to send
    """
    logger.debug("looking up user for password reset", extra={"email": payload.email})
    user = await get_user(db=db, email=payload.email)
    if user is None:
        # the provided email does not match an existing user
        # in cases like this, the frontend user must still think
        # the email got sent, this follows security best practices
        logger.debug(
            "user not found, silently returning", extra={"email": payload.email}
        )
        return
    logger.debug(
        "retrieving existing reset password token", extra={"email": user.email}
    )
    token = await get_reset_password_token(db=db, u_id=user.id)
    if token is None:
        # create a standard ResetPasswordToken for this user and send the email
        logger.debug(
            "no existing token found, creating reset password token",
            extra={"email": user.email},
        )
        token = generate_reset_password_token(u_id=user.id)
        token = await insert_reset_password_token(db=db, token=token)
        logger.debug("sending reset password email", extra={"email": user.email})
        await send_reset_password_email(user=user, token=token)
        return
    # check the token cooldown, if it has not elapsed, just return
    # as the user likely needs to re-check their email
    # if the cooldown has passed, rotate the tokens
    has_elapsed = check_reset_password_cooldown(created_at=token.created_at)
    if not has_elapsed:
        logger.debug(
            "reset password token cooldown has not elapsed", extra={"email": user.email}
        )
        return
    logger.debug("deleting existing reset password token", extra={"email": user.email})
    await delete_reset_password_tokens(db=db, u_id=user.id)
    logger.debug("creating new reset password token", extra={"email": user.email})
    token = generate_reset_password_token(u_id=user.id)
    token = await insert_reset_password_token(db=db, token=token)
    logger.debug("sending reset password email", extra={"email": user.email})
    await send_reset_password_email(user=user, token=token)


async def handle_reset_password(
    db: AsyncSession, payload: ResetPasswordRequest
) -> None:
    """
    Handle password reset functionality.

    Validates the provided reset password token, checks its expiry and usage status,
    updates the user's password, and invalidates all existing refresh tokens for security.
    The reset token is marked as used to prevent reuse.

    Args:
        db: Async database session
        payload: Reset password request containing the token and new password

    Raises:
        InvalidTokenError: If the token is not found, has expired,
                          has already been used, or is matched to a non-existing user
    """
    logger.debug("retrieving reset password token", extra={"token": payload.token})
    token = await get_reset_password_token(db=db, token_val=payload.token)
    if token is None:
        logger.debug("reset password token not found", extra={"token": payload.token})
        raise InvalidTokenError
    logger.debug("checking reset password token expiry", extra={"token": payload.token})
    not_expired = check_reset_password_token_expiry(expires_at=token.expires_at)
    if not not_expired:
        logger.debug(
            "reset password token has expired", extra={"user_id": token.user_id}
        )
        raise InvalidTokenError
    if token.used_at is not None:
        logger.debug(
            "reset password token has already been used",
            extra={"user_id": token.user_id},
        )
        raise InvalidTokenError
    logger.debug("retrieving user for password reset", extra={"user_id": token.user_id})
    user = await get_user(db=db, u_id=token.user_id)
    if user is None:
        logger.debug(
            "user not found for reset password token", extra={"user_id": token.user_id}
        )
        raise InvalidTokenError
    # at this point the token is valid and the password is valid via pydantic validation
    logger.debug("marking reset password token as used", extra={"email": user.email})
    _ = await update_reset_password_token(
        db=db, token_id=token.id, used_at=datetime.datetime.now(tz=datetime.UTC)
    )
    logger.debug("hashing new password", extra={"email": user.email})
    hashed_password = hash_password(raw=payload.password)
    logger.debug("updating user password", extra={"email": user.email})
    _ = await update_user(db=db, u_id=user.id, password=hashed_password)
    logger.debug("deleting all refresh tokens", extra={"email": user.email})
    await delete_refresh_tokens(db=db, u_id=user.id)
    logger.debug("password reset successful", extra={"email": user.email})
    return


async def handle_verify_email(db: AsyncSession, payload: VerifyEmailRequest) -> None:
    """
    Handle email verification for a user.

    Validates the provided email verification token, checks its expiry,
    and marks the user as verified if all conditions are met.
    The token is deleted after successful verification to prevent reuse.

    Args:
        db: Async database session
        payload: Email verification request containing the token

    Raises:
        InvalidTokenError: If the token is not found, has expired,
                          or is matched to a non-existing user
    """
    token = await get_verify_email_token(db=db, token_val=payload.token)
    if token is None:
        logger.debug("verify email token not found", extra={"token": payload.token})
        raise InvalidTokenError
    # all that's needed now is to ensure that the token is being used before it's expiry time
    # given that the token exists in our database we know that it is structurally valid
    valid = check_verify_email_token_expiry(expires_at=token.expires_at)
    if not valid:
        logger.debug("verify email token has expired", extra={"user_id": token.user_id})
        raise InvalidTokenError
    # update the users verification status now that they have proven ownership over their email address
    # also remove the verify email token to prevent possible reuse somehow
    await delete_verify_email_token(db=db, token=token)
    user = await get_user(db=db, u_id=token.user_id)
    if user is None:
        logger.debug(
            "user not found for verify email token", extra={"user_id": token.user_id}
        )
        raise InvalidTokenError  # token is somehow matched to a non-existing user
    logger.debug("marking user as verified", extra={"email": user.email})
    await update_user(
        db=db,
        u_id=user.id,
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    logger.debug("user email verification successful", extra={"email": user.email})
    return


async def handle_me(db: AsyncSession, access_token: str) -> User:
    """
    Handle retrieving the current authenticated user.

    Decodes the provided access token, validates it, and retrieves the associated user
    from the database. This endpoint is typically used to get the current user's information.

    Args:
        db: Async database session
        access_token: JWT access token string

    Returns:
        User: The authenticated user object

    Raises:
        InvalidTokenError: If the token is invalid, expired, malformed,
                          or the user_id is not found in the token claims
    """
    logger.debug("decoding access token")
    claims = decode_access_token(token=access_token)
    user_id = claims.get("user_id")
    if user_id is None:
        logger.debug("user_id not found in token claims")
        raise InvalidTokenError
    try:
        user_id = uuid.UUID(hex=user_id)
    except ValueError as e:
        logger.debug("invalid user_id format in token", extra={"user_id": user_id})
        raise InvalidTokenError from e
    logger.debug("retrieving user from database", extra={"user_id": user_id})
    user = await get_user(db=db, u_id=user_id)
    if user is None:
        # uuid embedded in access_token somehow is not linked to a valid user
        # this should never happen but necessary to check
        logger.debug("user not found for token user_id", extra={"user_id": user_id})
        raise InvalidTokenError
    logger.debug("user retrieved successfully", extra={"email": user.email})
    return user


async def handle_refresh(
    db: AsyncSession, response: Response, refresh_token: str
) -> None:
    """
    Handle refresh token rotation and token pair regeneration.

    Validates the provided refresh token, rotates it in the database following
    security best practices, and generates a new pair of access and refresh tokens.
    Both tokens are set as HttpOnly cookies in the response.

    Args:
        db: Async database session
        response: FastAPI Response object to set authentication cookies
        refresh_token: JWT refresh token string

    Raises:
        InvalidTokenError: If the token is invalid, malformed, expired,
                          user_id is not found in claims, or token is not in database
    """
    logger.debug("decoding refresh tokens")
    claims = decode_refresh_token(token=refresh_token, return_anyway=False)
    user_id = claims.get("user_id")
    if user_id is None:
        logger.debug("user_id not found in token claims")
        raise InvalidTokenError
    try:
        user_id = uuid.UUID(hex=user_id)
    except ValueError as e:
        logger.debug("invalid user_id format in token", extra={"user_id": user_id})
        raise InvalidTokenError from e
    logger.debug("retrieving refresh token from database", extra={"user_id": user_id})
    token = await get_refresh_token(db=db, token_hash=refresh_token)
    if token is None:
        logger.debug("refresh token not found in database", extra={"user_id": user_id})
        raise InvalidTokenError
    if user_id != token.user_id:
        logger.debug(
            "refresh token user_id mismatch",
            extra={"token_user_id": token.user_id, "claims_user_id": user_id},
        )
        raise InvalidTokenError
    # at this point the provided refresh token is valid
    # the refresh token must be rotated in the database to follow security best practices
    # and a new pair of access and refresh tokens must be resent to the frontend
    logger.debug("rotating refresh token", extra={"user_id": user_id})
    await delete_refresh_tokens(db=db, u_id=user_id)
    refresh_token = generate_refresh_token(u_id=user_id)
    refresh_token = await insert_refresh_token(db=db, token=refresh_token)
    access_token = generate_access_token(u_id=user_id)
    logger.debug("setting authentication cookies", extra={"user_id": user_id})
    # max_age expects seconds so adjust the value accordingly
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False if settings.IS_DEV else True,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_TTL_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token.token_hash,
        httponly=True,
        secure=False if settings.IS_DEV else True,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_TTL_HOURS * 60 * 60,
    )
    logger.debug("refresh token rotation successful", extra={"user_id": user_id})
    return None
