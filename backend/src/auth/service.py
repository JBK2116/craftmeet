"""Authentication related services and management

This module provides authentication-related services and utilities for the application
including session management, token handling and more.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import EmailExistsError
from src.auth.repository import email_exists
from src.auth.schemas import SignupRequest

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
    exists = await email_exists(db, payload.email)
    logger.debug(f"Email existence result: {exists}")
    if exists:
        raise EmailExistsError(payload.email)
    # TODO: Create the verify email token
    # TODO: Create and save the user object to the database
    # TODO: Send the user an email to verify their account now
