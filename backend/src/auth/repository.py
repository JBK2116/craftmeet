"""Authentication repository related services and management

This module provides data access layer functionality for authentication-related
operations, including user credential management, session handling, and
authentication state persistence.
"""

import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import DatabaseError
from src.models import User

logger = logging.getLogger(__name__)


async def email_exists(db: AsyncSession, email: str) -> bool:
    """Check if a user with the given email already exists in the database.

    Args:
        db: Async database session.
        email: Email address to check.

    Returns:
        True if a user with the email exists, False otherwise.

    Raises:
        DatabaseError if an error occurs during the database execution process
    """
    try:
        logger.debug(f"Checking email existence for {email}")
        stmt = select(User).where(User.email == email).exists().select()
        result = await db.execute(stmt)
        return bool(result.scalar())
    except SQLAlchemyError as e:
        logger.exception(f"Failed to check email existence for {email}")
        raise DatabaseError("database error occurred") from e
