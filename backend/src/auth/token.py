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

from src.auth.constants import (
    VERIFY_EMAIL_TOKEN_COOLDOWN_DURATION_MINUTES,
    VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES,
)
from src.auth.models import VerifyEmailToken


def generate_verify_email_token_hash() -> str:
    """
    Generates a secure 32 byte url safe string
    """
    return secrets.token_urlsafe(32)


def generate_verify_email_token_expiry() -> datetime.datetime:
    """
    Generates an expiry datetime for email verification tokens.

    Returns a datetime object set to the current time plus the maximum
    duration allowed for email verification tokens.

    Returns:
        datetime.datetime: The expiry datetime in UTC timezone.
    """
    return datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES
    )


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
        token_hash=generate_verify_email_token_hash(),
        expires_at=generate_verify_email_token_expiry(),
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
