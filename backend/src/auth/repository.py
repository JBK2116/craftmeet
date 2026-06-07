"""Authentication repository related services and management

This module provides data access layer functionality for authentication-related
operations, including user credential management, session handling, and
authentication state persistence.
"""

import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import VerifyEmailToken
from src.exceptions import DatabaseError
from src.models import User

logger = logging.getLogger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Retrieves the user with the provided email address.

    Args:
        db: Async database session.
        email: Email address to search for.

    Returns:
        User object if found, None otherwise.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        logger.debug(f"getting user with email: {email}")
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.exception(f"failed to get user with email: {str}")
        raise DatabaseError("database error occured") from e


async def get_user_verify_email_token(
    db: AsyncSession, u_id: uuid.UUID
) -> VerifyEmailToken | None:
    """Retrieves the verify email token for a user.

    Args:
        db: Async database session.
        u_id: User ID to retrieve the verify email token for.

    Returns:
        VerifyEmailToken object if found, None otherwise.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        logger.debug(f"getting verify email token of user with ID: {str(u_id)}")
        stmt = select(VerifyEmailToken).where(VerifyEmailToken.user_id == u_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.exception(f"failed to get verify email token of user with ID: {u_id}")
        raise DatabaseError("database error occured") from e


async def insert_user(db: AsyncSession, user: User) -> User:
    """Inserts a new user into the database.

    Args:
        db: Async database session.
        user: User object to insert.

    Returns:
        User object that was inserted.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.debug(f"inserted user with email into database: {user.email}")
        return user
    except SQLAlchemyError as e:
        await db.rollback()
        logger.exception(f"failed to insert user with email: {user.email}")
        raise DatabaseError("database error occured") from e


async def insert_verify_email_token(
    db: AsyncSession, token: VerifyEmailToken
) -> VerifyEmailToken:
    """Inserts a new verify email token into the database.

    Args:
        db: Async database session.
        token: VerifyEmailToken object to insert.

    Returns:
        VerifyEmailToken object that was inserted.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        db.add(token)
        await db.commit()
        await db.refresh(token)
        return token
    except SQLAlchemyError as e:
        await db.rollback()
        logger.exception("failed to insert verify email token")
        raise DatabaseError("database error occured") from e


async def update_user_username(db: AsyncSession, u_id: uuid.UUID, new: str) -> User:
    """Updates the username for a user.

    Args:
        db: Async database session.
        u_id: User ID to update the username for.
        new: New username value.

    Returns:
        User object with updated username.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        stmt = update(User).where(User.id == u_id).values(username=new).returning(User)
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.exception("failed to update user username")
        raise DatabaseError("database error occurred") from e


async def update_user_password(db: AsyncSession, u_id: uuid.UUID, new: str) -> User:
    """Updates the password for a user.

    Args:
        db: Async database session.
        u_id: User ID to update the password for.
        new: New password value.

    Returns:
        User object with updated password.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        stmt = update(User).where(User.id == u_id).values(password=new).returning(User)
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.exception("failed to update user password")
        raise DatabaseError("database error occurred") from e


async def delete_verify_email_token(db: AsyncSession, token: VerifyEmailToken) -> None:
    """Deletes the verify email token for a user.

    Args:
        db: Async database session.
        token: VerifyEmailToken object to delete.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        await db.delete(token)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.exception("failed to delete verify email token")
        raise DatabaseError("database error occured") from e
