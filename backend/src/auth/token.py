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
    VERIFY_EMAIL_TOKEN_COOLDOWN_DURATION_MINUTES,
    VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES,
)
from src.auth.exceptions import InvalidTokenError
from src.auth.models import RefreshToken, VerifyEmailToken
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
        token_hash=secrets.token_urlsafe(32),
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
    return datetime.datetime.now(datetime.UTC) - created_at > datetime.timedelta(
        minutes=VERIFY_EMAIL_TOKEN_COOLDOWN_DURATION_MINUTES
    )


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
    }
    if not settings.IS_DEV:
        payload.update({"iss": settings.DOMAIN, "jti": str(uuid.uuid4())})
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
    }
    if not settings.IS_DEV:
        payload.update({"iss": settings.DOMAIN, "jti": str(uuid.uuid4())})
    token_hash = jwt.encode(
        payload=payload, key=settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
    )
    return RefreshToken(user_id=u_id, token_hash=token_hash, expires_at=expire)


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates a JWT refresh token.

    Verifies the token signature and ensures the token type is "refresh".
    Raises InvalidTokenError if the token is invalid, expired, or has an
    incorrect type.

    Args:
        token: The JWT refresh token string to decode.

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
    except jwt.PyJWTError as e:
        raise InvalidTokenError from e
    except Exception as e:
        raise InvalidTokenError from e
