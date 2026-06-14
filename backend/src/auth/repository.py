"""Authentication repository related services and management

This module provides data access layer functionality for authentication-related
operations, including user credential management, session handling, and
authentication state persistence.
"""

import logging
import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import RefreshToken, ResetPasswordToken, VerifyEmailToken
from src.exceptions import DatabaseError
from src.models import User

logger = logging.getLogger(__name__)


async def get_user(
    db: AsyncSession, email: str | None = None, u_id: uuid.UUID | None = None
) -> User | None:
    """Retrieves a user from the database by email or user ID.

    Queries the database for a user matching either the provided email address
    or user ID. Exactly one of email or u_id should be provided.

    Args:
        db: Async database session.
        email: Email address to search for. Defaults to None.
        u_id: User ID to search for. Defaults to None.

    Returns:
        User object if found, None otherwise.

    Raises:
        DatabaseError: If an error occurs during the database execution process.
    """
    try:
        if email:
            logger.debug(f"getting user by email: {email}")
            stmt = select(User).where(User.email == email)
        elif u_id:
            logger.debug(f"getting user by user ID: {u_id}")
            stmt = select(User).where(User.id == u_id)
        else:
            logger.debug("no email or user ID provided, returning None")
            return None
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            logger.debug(f"user found with ID: {user.id}")
        else:
            logger.debug("no user found matching the provided criteria")
        return user
    except SQLAlchemyError as e:
        logger.exception(f"failed to get user with email: {email}")
        raise DatabaseError("database error occurred") from e


async def get_verify_email_token(
    db: AsyncSession, u_id: uuid.UUID | None = None, token_val: str | None = None
) -> VerifyEmailToken | None:
    """Retrieves the verify email token for a user.

    Args:
        db: Async database session.
        u_id: User ID to retrieve the verify email token for.
        token_val: Token hash to retrieve the verify email token for.

    Returns:
        VerifyEmailToken object if found, None otherwise.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        if u_id:
            logger.debug(f"getting verify email token for user ID: {u_id}")
            stmt = select(VerifyEmailToken).where(VerifyEmailToken.user_id == u_id)
        elif token_val:
            logger.debug("getting verify email token by token value")
            stmt = select(VerifyEmailToken).where(
                VerifyEmailToken.token_hash == token_val
            )
        else:
            logger.debug("no user ID or token provided, returning None")
            return None
        result = await db.execute(stmt)
        token_obj = result.scalar_one_or_none()
        if token_obj:
            logger.debug(f"verify email token found for user ID: {u_id}")
        else:
            logger.debug(f"no verify email token found for user ID: {u_id}")
        return token_obj
    except SQLAlchemyError as e:
        logger.exception(f"failed to retrieve verify email token for user ID: {u_id}")
        raise DatabaseError("database error occurred") from e


async def get_reset_password_token(
    db: AsyncSession, u_id: uuid.UUID | None = None, token_val: str | None = None
) -> ResetPasswordToken | None:
    """Retrieves the reset password token for a user.

    Queries the database for a reset password token matching either the provided
    user ID or token hash. Exactly one of u_id or token_val should be provided.

    Args:
        db: Async database session.
        u_id: User ID to retrieve the reset password token for. Defaults to None.
        token_val: Token hash to retrieve the reset password token for. Defaults to None.

    Returns:
        ResetPasswordToken object if found, None otherwise.

    Raises:
        DatabaseError: If an error occurs during the database execution process.
    """
    try:
        if u_id:
            logger.debug(f"getting reset password token for user ID: {u_id}")
            stmt = select(ResetPasswordToken).where(ResetPasswordToken.user_id == u_id)
        elif token_val:
            logger.debug("getting reset password token by token value")
            stmt = select(ResetPasswordToken).where(
                ResetPasswordToken.token_hash == token_val
            )
        else:
            logger.debug("no user ID or token provided, returning None")
            return None
        result = await db.execute(stmt)
        token_obj = result.scalar_one_or_none()
        if token_obj:
            logger.debug(f"reset password token found for user ID: {u_id}")
        else:
            logger.debug(f"no reset password token found for user ID: {u_id}")
        return token_obj
    except SQLAlchemyError as e:
        logger.exception(f"failed to retrieve reset password token for user ID: {u_id}")
        raise DatabaseError("database error occurred") from e


async def get_refresh_token(
    db: AsyncSession, u_id: uuid.UUID | None = None, token_hash: str | None = None
) -> RefreshToken | None:
    """Retrieves a refresh token from the database.

    Queries the database for a refresh token matching either the provided user ID
    or token hash. Exactly one of u_id or token_hash should be provided.

    Args:
        db: Async database session.
        u_id: User ID to retrieve the refresh token for. Defaults to None.
        token_hash: Token hash to retrieve the refresh token for. Defaults to None.

    Returns:
        RefreshToken object if found, None otherwise.

    Raises:
        DatabaseError: If an error occurs during the database execution process.
    """
    try:
        if u_id:
            logger.debug(f"getting refresh token for user ID: {u_id}")
            stmt = select(RefreshToken).where(RefreshToken.user_id == u_id)
        elif token_hash:
            logger.debug("getting refresh token by token hash")
            stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        else:
            logger.debug("no user ID or token hash provided, returning None")
            return None
        result = await db.execute(stmt)
        token = result.scalar_one_or_none()
        if token:
            logger.debug(
                "refresh token found", extra={"u_id": u_id, "token_hash": token_hash}
            )
        else:
            logger.debug(
                "refresh token not found",
                extra={"u_id": u_id, "token_hash": token_hash},
            )
        return token
    except SQLAlchemyError as e:
        logger.exception(f"failed to retrieve refresh token for user ID: {u_id}")
        raise DatabaseError("database error occurred") from e


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
        logger.debug(f"inserting new user with email: {user.email}")
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.debug(
            f"successfully inserted user with email: {user.email}, user_id: {user.id}"
        )
        return user
    except SQLAlchemyError as e:
        logger.exception(f"failed to insert user with email: {user.email}")
        raise DatabaseError("database error occurred") from e


async def insert_reset_password_token(
    db: AsyncSession, token: ResetPasswordToken
) -> ResetPasswordToken:
    """Inserts a new reset password token into the database.

    Args:
        db: Async database session.
        token: ResetPasswordToken object to insert.

    Returns:
        ResetPasswordToken object that was inserted.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        logger.debug(f"inserting reset password token for user ID: {token.user_id}")
        db.add(token)
        await db.flush()
        await db.refresh(token)
        logger.debug(
            f"successfully inserted reset password token for user ID: {token.user_id}"
        )
        return token
    except SQLAlchemyError as e:
        logger.exception(
            f"failed to insert reset password token for user ID: {token.user_id}"
        )
        raise DatabaseError("database error occurred") from e


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
        logger.debug(f"inserting verify email token for user ID: {token.user_id}")
        db.add(token)
        await db.flush()
        await db.refresh(token)
        logger.debug(
            f"successfully inserted verify email token for user ID: {token.user_id}"
        )
        return token
    except SQLAlchemyError as e:
        logger.exception(
            f"failed to insert verify email token for user ID: {token.user_id}"
        )
        raise DatabaseError("database error occurred") from e


async def insert_refresh_token(db: AsyncSession, token: RefreshToken) -> RefreshToken:
    """Inserts a new refresh token into the database.

    Args:
        db: Async database session.
        token: RefreshToken object to insert.

    Returns:
        RefreshToken object that was inserted.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        logger.debug(f"inserting refresh token for user ID: {token.user_id}")
        db.add(token)
        await db.flush()
        await db.refresh(token)
        logger.debug(
            f"successfully inserted refresh token for user ID: {token.user_id}"
        )
        return token
    except SQLAlchemyError as e:
        logger.exception(f"failed to insert refresh token for user ID: {token.user_id}")
        raise DatabaseError("database error occurred") from e


async def update_user(db: AsyncSession, u_id: uuid.UUID, **kwargs) -> User:
    """Updates a user in the database with the provided fields.

    Args:
        db: Async database session.
        u_id: User ID to update.
        **kwargs: Field names and values to update on the user.

    Returns:
        Updated User object if found, None otherwise.

    Raises:
        DatabaseError: If an error occurs during the database execution process.
    """
    try:
        logger.debug(f"updating user ID: {u_id} with fields: {list(kwargs.keys())}")
        stmt = update(User).where(User.id == u_id).values(**kwargs).returning(User)
        result = await db.execute(stmt)
        user = result.scalar_one()
        if user:
            logger.debug(f"successfully updated user ID: {u_id}")
        return user

    except SQLAlchemyError as e:
        logger.exception(f"failed to update user ID: {u_id}")
        raise DatabaseError("database error occurred") from e


async def update_reset_password_token(
    db: AsyncSession, token_id: uuid.UUID, **kwargs
) -> ResetPasswordToken:
    """Updates a reset password token in the database with the provided fields.

    Args:
        db: Async database session.
        token_id: Reset password token ID to update.
        **kwargs: Field names and values to update on the token.

    Returns:
        Updated ResetPasswordToken object if found, None otherwise.

    Raises:
        DatabaseError: If an error occurs during the database execution process.
    """
    try:
        logger.debug(
            f"updating reset password token ID: {token_id} with fields: {list(kwargs.keys())}"
        )
        stmt = (
            update(ResetPasswordToken)
            .where(ResetPasswordToken.id == token_id)
            .values(**kwargs)
            .returning(ResetPasswordToken)
        )
        result = await db.execute(stmt)
        token = result.scalar_one()
        if token:
            logger.debug(f"successfully updated reset password token ID: {token_id}")
        return token

    except SQLAlchemyError as e:
        logger.exception(f"failed to update reset password token ID: {token_id}")
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
        logger.debug(f"deleting verify email token for user ID: {token.user_id}")
        await db.delete(token)
        await db.flush()
        logger.debug(
            f"successfully deleted verify email token for user ID: {token.user_id}"
        )
    except SQLAlchemyError as e:
        logger.exception(
            f"failed to delete verify email token for user ID: {token.user_id}"
        )
        raise DatabaseError("database error occurred") from e


async def delete_refresh_tokens(db: AsyncSession, u_id: uuid.UUID) -> None:
    """Deletes all refresh tokens for a user.

    Args:
        db: Async database session.
        u_id: User ID to delete refresh tokens for.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        logger.debug(f"deleting all refresh tokens for user ID: {u_id}")
        stmt = delete(RefreshToken).where(RefreshToken.user_id == u_id)
        await db.execute(stmt)
        logger.debug(f"successfully deleted all refresh tokens for user ID: {u_id}")
    except SQLAlchemyError as e:
        logger.exception(f"failed to delete refresh tokens for user ID: {u_id}")
        raise DatabaseError("database error occurred") from e


async def delete_reset_password_tokens(db: AsyncSession, u_id: uuid.UUID) -> None:
    """Deletes all reset password tokens for a user.

    Args:
        db: Async database session.
        u_id: User ID to delete reset password tokens for.

    Raises:
        DatabaseError if an error occurs during the database execution process.
    """
    try:
        logger.debug(f"deleting all reset password tokens for user ID: {u_id}")
        stmt = delete(ResetPasswordToken).where(ResetPasswordToken.user_id == u_id)
        await db.execute(stmt)
        logger.debug(
            f"successfully deleted all reset password tokens for user ID: {u_id}"
        )

    except SQLAlchemyError as e:
        logger.exception(f"failed to delete reset password tokens for user ID: {u_id}")
        raise DatabaseError("database error occurred") from e
