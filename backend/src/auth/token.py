"""Token creation and management

This module handles the creation and management of various token types used
throughout the authentication system, including:
- Access tokens: Short-lived tokens for API authentication
- Refresh tokens: Long-lived tokens for obtaining new access tokens
- Verify email tokens: Tokens for email verification workflows
- Password reset tokens: Tokens for password reset functionality
"""

import datetime
import secrets
import uuid
from typing import Any

import jwt

from src.auth.constants import (
    RESET_PASSWORD_COOLDOWN_DURATION_MINUTES,
    RESET_PASSWORD_TOKEN_BYTES,
    RESET_PASSWORD_TOKEN_MAX_DURATION_MINUTES,
    VERIFY_EMAIL_TOKEN_BYTES,
    VERIFY_EMAIL_TOKEN_COOLDOWN_DURATION_MINUTES,
    VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES,
)
from src.auth.exceptions import InvalidTokenError
from src.auth.models import RefreshToken, ResetPasswordToken, VerifyEmailToken
from src.config import get_settings

settings = get_settings()

JWT_ALGORITHM = "HS256"


def generate_verify_email_token(u_id: uuid.UUID) -> VerifyEmailToken:
    """
    Generates a verify email token for the given user.

    Creates a new VerifyEmailToken with a secure token hash and expiry time.
    This token is used for email verification workflows.

    Args:
        u_id: The user ID to associate with the token.

    Returns:
        VerifyEmailToken: A token object containing the user ID, token hash,
            and expiry datetime.
    """
    return VerifyEmailToken(
        user_id=u_id,
        token_hash=secrets.token_urlsafe(VERIFY_EMAIL_TOKEN_BYTES),
        expires_at=datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(minutes=VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES),
    )


def check_verify_email_token_cooldown(created_at: datetime.datetime) -> bool:
    """
    Checks if the cooldown period for verify email token has elapsed.

    Determines whether enough time has passed since the token was created
    to allow generating a new verify email token. This prevents abuse by
    limiting the frequency of token generation requests.

    Args:
        created_at: The datetime when the previous token was created.

    Returns:
        bool: True if the cooldown period has elapsed, False otherwise.
    """
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=datetime.UTC)
    return datetime.datetime.now(datetime.UTC) - created_at > datetime.timedelta(
        minutes=VERIFY_EMAIL_TOKEN_COOLDOWN_DURATION_MINUTES
    )


def check_verify_email_token_expiry(expires_at: datetime.datetime) -> bool:
    """
    Checks if the verify email token has expired.

    Determines whether the token's expiration time has passed by comparing
    it to the current time. This is used to validate whether a verify email
    token is still valid for use.

    Args:
        expires_at: The datetime when the token expires.

    Returns:
        bool: True if the token has expired, False otherwise.
    """
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.UTC)
    return expires_at > datetime.datetime.now(tz=datetime.UTC)


def generate_reset_password_token(u_id: uuid.UUID) -> ResetPasswordToken:
    """
    Generates a reset password token for the given user.

    Creates a new ResetPasswordToken with a secure token hash and expiry time.
    This token is used for password reset workflows.

    Args:
        u_id: The user ID to associate with the token.

    Returns:
        ResetPasswordToken: A token object containing the user ID, token hash,
            and expiry datetime.
    """
    return ResetPasswordToken(
        user_id=u_id,
        token_hash=secrets.token_urlsafe(RESET_PASSWORD_TOKEN_BYTES),
        expires_at=datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(minutes=RESET_PASSWORD_TOKEN_MAX_DURATION_MINUTES),
    )


def check_reset_password_cooldown(created_at: datetime.datetime) -> bool:
    """
    Checks if the cooldown period for reset password token has elapsed.

    Determines whether enough time has passed since the token was created
    to allow generating a new reset password token. This prevents abuse by
    limiting the frequency of token generation requests.

    Args:
        created_at: The datetime when the previous token was created.

    Returns:
        bool: True if the cooldown period has elapsed, False otherwise.
    """
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=datetime.UTC)
    return datetime.datetime.now(datetime.UTC) - created_at > datetime.timedelta(
        minutes=RESET_PASSWORD_COOLDOWN_DURATION_MINUTES
    )


def check_reset_password_token_expiry(expires_at: datetime.datetime) -> bool:
    """
    Checks if the reset password token has expired.

    Determines whether the token's expiration time has passed by comparing
    it to the current time. This is used to validate whether a reset password
    token is still valid for use.

    Args:
        expires_at: The datetime when the token expires.

    Returns:
        bool: True if the token has not expired, False otherwise.
    """
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.UTC)
    return expires_at > datetime.datetime.now(datetime.UTC)


def generate_access_token(u_id: uuid.UUID) -> str:
    """
    Generates a JWT access token for the given user.

    Creates a short-lived access token with user ID, expiration, and issuance
    timestamps. In production, includes issuer and JWT ID claims.

    Args:
        u_id: The user ID to encode in the token.

    Returns:
        str: A signed JWT access token.
    """
    now = datetime.datetime.now(datetime.UTC)
    expire = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES)
    payload = {
        "user_id": str(u_id),
        "exp": expire,
        "iat": now,
        "type": "access",
        "iss": settings.DOMAIN,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        payload=payload, key=settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates a JWT access token.

    Verifies the token signature and ensures the token type is "access".
    Raises InvalidTokenError if the token is invalid, expired, or has an
    incorrect type.

    Args:
        token: The JWT access token string to decode.

    Returns:
        dict: The decoded token claims.

    Raises:
        InvalidTokenError: If the token is invalid, expired, malformed,
            or does not have type "access".
    """
    try:
        claims = jwt.decode(
            jwt=token, key=settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        if claims["type"] != "access":
            raise InvalidTokenError
        return claims
    except jwt.PyJWTError as e:
        raise InvalidTokenError from e
    except Exception as e:
        raise InvalidTokenError from e


def generate_refresh_token(u_id: uuid.UUID) -> RefreshToken:
    """
    Generates a JWT refresh token for the given user.

    Creates a long-lived refresh token with user ID, expiration, and issuance
    timestamps. In production, includes issuer and JWT ID claims.

    Args:
        u_id: The user ID to encode in the token.

    Returns:
        RefreshToken: A RefreshToken model.
    """
    now = datetime.datetime.now(datetime.UTC)
    expire = now + datetime.timedelta(hours=settings.REFRESH_TOKEN_TTL_HOURS)
    payload = {
        "user_id": str(u_id),
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "iss": settings.DOMAIN,
        "jti": str(uuid.uuid4()),
    }
    token_hash = jwt.encode(
        payload=payload, key=settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
    )
    return RefreshToken(user_id=u_id, token_hash=token_hash, expires_at=expire)


def decode_refresh_token(token: str, return_anyway: bool = False) -> dict[str, Any]:
    """
    Decodes and validates a JWT refresh token.

    Verifies the token signature and ensures the token type is "refresh".
    Raises InvalidTokenError if the token is invalid, expired, or has an
    incorrect type.

    Args:
        token: The JWT refresh token string to decode.
        return_anyway: If True, return claims even if token is expired.

    Returns:
        dict: The decoded token claims.

    Raises:
        InvalidTokenError: If the token is invalid, expired, malformed,
            or does not have type "refresh".
    """
    try:
        claims = jwt.decode(
            jwt=token, key=settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        if claims["type"] != "refresh":
            raise InvalidTokenError
        return claims
    except jwt.ExpiredSignatureError as e:
        if return_anyway:
            # decode without verification to get claims from expired token
            claims = jwt.decode(
                jwt=token,
                key=settings.JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False},
            )
            if claims["type"] != "refresh":
                raise InvalidTokenError from e
            return claims
        raise InvalidTokenError from e
    except jwt.PyJWTError as e:
        raise InvalidTokenError from e
    except Exception as e:
        raise InvalidTokenError from e


def generate_participants_meeting_access_token(
    duration: int, m_id: uuid.UUID, p_id: uuid.UUID | None = None
) -> str:
    """
    Generate a JWT access token for a meeting participant.

    The token encodes the meeting and participant IDs, issues and expiry times,
    token type, issuer, and a unique JWT ID. The token is signed with the
    application's secret key using the configured JWT algorithm.

    Args:
        duration: Token lifetime in seconds.
        m_id: UUID of the meeting the participant will join.
        p_id: Optional existing UUID of the participant. If not provided, a new UUID is generated.

    Returns:
        A signed JWT string ready to be used as an access token.
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    expire = now + datetime.timedelta(seconds=duration)
    if p_id:
        u_id = p_id
    else:
        u_id = uuid.uuid4()
    payload = {
        "meeting_id": str(m_id),
        "participant_id": str(u_id),
        "exp": expire,
        "iat": now,
        "type": "access",
        "iss": settings.DOMAIN,
        "jti": str(u_id),
    }
    token_hash = jwt.encode(
        payload=payload, key=settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
    )
    return token_hash


def decode_participants_meeting_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a participants access token.

    This function decodes a JWT access token for a meeting participant,
    verifies its signature using the configured secret key, and checks
    that the token type is "access". It also validates that the meeting_id
    and participant_id are valid UUIDs.

    Args:
        token: The JWT access token string to decode.

    Returns:
        A dictionary containing the token claims.

    Raises:
        InvalidTokenError: If the token is invalid, expired, not an access
            token, or contains invalid UUIDs.
    """
    try:
        claims = jwt.decode(
            jwt=token, key=settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        if claims["type"] != "access":
            raise InvalidTokenError
        _ = uuid.UUID(claims["meeting_id"])
        _ = uuid.UUID(claims["participant_id"])
        return claims
    except jwt.PyJWTError as e:
        raise InvalidTokenError from e
    except Exception as e:
        raise InvalidTokenError from e
