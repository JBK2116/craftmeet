"""Meeting repository related services and management

This module provides data access layer functionality for meeting-related
operations, including meeting management, live session handling, and
meeting state persistence.
"""

import logging
import uuid
from typing import cast

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.exceptions import DatabaseError
from src.meeting.utils import SubQuestion
from src.models import (
    LongAnswerQuestion,
    Meeting,
    MultipleChoiceQuestion,
    Question,
    RankedVotingQuestion,
    RatingScaleQuestion,
    Stat,
    YesNoQuestion,
)

logger = logging.getLogger(__name__)


async def insert_meeting(db: AsyncSession, meeting: Meeting) -> Meeting:
    """Insert a meeting record into the database.

    Adds the meeting to the session, flushes to persist, and refreshes
    the instance to retrieve database-generated values.

    Args:
        db: The asynchronous SQLAlchemy session.
        meeting: The Meeting instance to be inserted.

    Returns:
        The persisted Meeting instance with updated attributes.

    Raises:
        DatabaseError: If a SQLAlchemy error occurs during the operation.
    """
    logging.debug("Inserting meeting: %s", meeting)
    try:
        db.add(meeting)
        logging.debug("meeting added to session")
        await db.flush()
        logging.debug("session flushed")
        await db.refresh(meeting)
        logging.debug("meeting refreshed: %s", meeting)
        return meeting
    except SQLAlchemyError as e:
        logging.exception("error inserting meeting: %s", e)
        raise DatabaseError("database error occurred") from e


async def insert_stat(db: AsyncSession, stat: Stat) -> Stat:
    """Insert a stat record into the database.

    Adds the stat to the session, flushes to persist, and refreshes
    the instance to retrieve database-generated values.

    Args:
        db: The asynchronous SQLAlchemy session.
        stat: The Stat instance to be inserted.

    Returns:
        The persisted Stat instance with updated attributes.

    Raises:
        DatabaseError: If a SQLAlchemy error occurs during the operation.
    """
    logging.debug("Inserting stat: %s", stat)
    try:
        db.add(stat)
        logging.debug("stat added to session")
        await db.flush()
        logging.debug("session flushed")
        await db.refresh(stat)
        logging.debug("stat refreshed: %s", stat)
        return stat
    except SQLAlchemyError as e:
        logging.exception("error inserting stat: %s", e)
        raise DatabaseError("database error occurred") from e


async def insert_question(db: AsyncSession, question: Question) -> Question:
    """Insert a question into the database.

    Args:
        db: The asynchronous database session.
        question: The question object to be inserted.

    Returns:
        The inserted question instance after flushing and refreshing.

    Raises:
        DatabaseError: If an SQLAlchemy error occurs during the insert.
    """

    try:
        logging.debug("inserting question: %s", question)
        db.add(question)
        await db.flush()
        await db.refresh(question)
        logging.debug("question successfully added to db")
        return question
    except SQLAlchemyError as e:
        logging.getLogger(__name__).exception("failed to insert question: %s", question)
        raise DatabaseError("database error occurred") from e


async def insert_sub_question(db: AsyncSession, question: SubQuestion) -> SubQuestion:
    """Insert a sub-question into the database.

    Args:
        db: The asynchronous database session.
        question: The sub-question output object to be inserted.

    Returns:
        The sub-question output instance after flushing and refreshing.

    Raises:
        DatabaseError: If an SQLAlchemy error occurs during the insert.
    """
    try:
        logging.debug("inserting sub-question: %s", question)
        db.add(question)
        await db.flush()
        await db.refresh(question)
        logging.debug("sub-question successfully added to db")
        return question
    except SQLAlchemyError as e:
        logging.exception("failed to insert sub-question: %s", question)
        raise DatabaseError("database error occurred") from e


async def get_meetings(
    db: AsyncSession, u_id: uuid.UUID, limit: int, offset: int
) -> list[Meeting]:
    """Retrieve a list of meetings for a given user with full related data.

    Args:
        db: The asynchronous SQLAlchemy session.
        u_id: The UUID of the user whose meetings to fetch.
        limit: Maximum number of meetings to return.
        offset: Number of meetings to skip for pagination.

    Returns:
        A list of Meeting instances with eagerly loaded questions, stats and responses.

    Raises:
        DatabaseError: If a database error occurs during the query.
    """
    logger.debug(
        "fetching meetings for user %s with limit=%d, offset=%d", u_id, limit, offset
    )
    try:
        stmt = (
            select(Meeting)
            .options(
                selectinload(Meeting.questions)
                .selectinload(Question.multiple_choice)
                .selectinload(MultipleChoiceQuestion.responses),
                selectinload(Meeting.questions)
                .selectinload(Question.long_answer)
                .selectinload(LongAnswerQuestion.responses),
                selectinload(Meeting.questions)
                .selectinload(Question.ranked_voting)
                .selectinload(RankedVotingQuestion.responses),
                selectinload(Meeting.questions)
                .selectinload(Question.rating_scale)
                .selectinload(RatingScaleQuestion.responses),
                selectinload(Meeting.questions)
                .selectinload(Question.yes_no)
                .selectinload(YesNoQuestion.responses),
                selectinload(Meeting.stats),
            )
            .where(Meeting.user_id == u_id)
            .order_by(Meeting.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        meetings = list(result.scalars().all())
        logger.debug("retrieved %d meetings for user %s", len(meetings), u_id)
        return meetings
    except SQLAlchemyError as e:
        logging.exception("error fetching meetings for user %s: %s", u_id, e)
        raise DatabaseError("database error occurred") from e


async def get_meeting(db: AsyncSession, m_id: uuid.UUID) -> Meeting | None:
    """Retrieve a single meeting by its ID with full related data.

    Args:
        db: The asynchronous SQLAlchemy session.
        m_id: The UUID of the meeting to fetch.

    Returns:
        The Meeting instance with eagerly loaded questions, stats and responses,
        or None if no meeting with the given ID exists.

    Raises:
        DatabaseError: If a database error occurs during the query.
    """
    logger.debug("fetching meeting %s", m_id)
    try:
        stmt = (
            select(Meeting)
            .options(
                selectinload(Meeting.questions)
                .selectinload(Question.multiple_choice)
                .selectinload(MultipleChoiceQuestion.responses),
                selectinload(Meeting.questions)
                .selectinload(Question.long_answer)
                .selectinload(LongAnswerQuestion.responses),
                selectinload(Meeting.questions)
                .selectinload(Question.ranked_voting)
                .selectinload(RankedVotingQuestion.responses),
                selectinload(Meeting.questions)
                .selectinload(Question.rating_scale)
                .selectinload(RatingScaleQuestion.responses),
                selectinload(Meeting.questions)
                .selectinload(Question.yes_no)
                .selectinload(YesNoQuestion.responses),
                selectinload(Meeting.stats),
            )
            .where(Meeting.id == m_id)
        )
        result = await db.execute(stmt)
        meeting = result.scalar_one_or_none()
        logger.debug("retrieved meeting %s: %s", m_id, meeting)
        return meeting
    except SQLAlchemyError as e:
        logger.exception("error fetching meeting %s: %s", m_id, e)
        raise DatabaseError("database error occurred") from e


async def delete_meeting(db: AsyncSession, m_id: uuid.UUID, u_id: uuid.UUID) -> bool:
    """Delete a meeting by its ID, scoped to the owning user.

    Args:
        db: The asynchronous SQLAlchemy session.
        m_id: The UUID of the meeting to delete.
        u_id: The UUID of the meeting owner.

    Returns:
        True if a meeting was deleted, False if no matching meeting existed.

    Raises:
        DatabaseError: If a SQLAlchemy error occurs during the operation.
    """
    try:
        logger.debug("deleting meeting %s for user %s", m_id, u_id)
        stmt = delete(Meeting).where(Meeting.id == m_id and Meeting.user_id == u_id)
        # this cast is harmless, it correctly assigns the result to a CursorResult
        # following the official documentation
        # this fixes the type mismatch from the installed sqlalchemy stubs
        result = cast(CursorResult, await db.execute(stmt))
        await db.commit()
        logger.debug(
            "meeting %s deleted for user %s (affected rows: %d)",
            m_id,
            u_id,
            result.rowcount,
        )
        return result.rowcount > 0
    except SQLAlchemyError as e:
        logger.exception("error deleting meeting %s for user %s: %s", m_id, u_id, e)
        raise DatabaseError from e
