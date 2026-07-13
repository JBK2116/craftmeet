"""Meeting repository related services and management

This module provides data access layer functionality for meeting-related
operations, including meeting management, live session handling, and
meeting state persistence.
"""

import logging
import uuid
from typing import cast

from sqlalchemy import CursorResult, delete, select, update
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


async def get_meeting_lazy(
    db: AsyncSession, m_id: uuid.UUID | None = None, code: str | None = None
) -> Meeting | None:
    """
    Retrieve a single meeting lazily by either its id or its room code.

    Args:
        db: The asynchronous SQLAlchemy session.
        m_id: The UUID of the meeting to fetch.
        code: The unique room code of the meeting.

    Returns:
        The Meeting instance if found, otherwise None.

    Raises:
        DatabaseError: If a database error occurs during the query.
    """
    try:
        if m_id:
            stmt = select(Meeting).where(Meeting.id == m_id)
            logger.info("fetching meeting by id", extra={"meeting_id": str(m_id)})
        elif code:
            stmt = select(Meeting).where(Meeting.room_code == code)
            logger.info("fetching meeting by code", extra={"room_code": code})
        else:
            logger.warning(
                "no select argument provided to get_meeting_lazy",
                extra={"m_id": m_id, "code": code},
            )
            return
        result = await db.execute(stmt)
        meeting = result.scalar_one_or_none()
        if meeting is not None:
            logger.info("meeting found", extra={"meeting_id": str(meeting.id)})
        else:
            logger.info(
                "meeting not found",
                extra={"m_id": str(m_id) if m_id else None, "code": code},
            )
        return meeting
    except SQLAlchemyError as e:
        logger.exception(
            "database error while fetching meeting",
            extra={"m_id": str(m_id) if m_id else None, "code": code},
        )
        raise DatabaseError("database error occurred") from e


async def get_stat(
    db: AsyncSession, m_id: uuid.UUID | None = None, s_id: uuid.UUID | None = None
) -> Stat | None:
    """
    Retrieve a Stat record by meeting_id (m_id) or by its own id (s_id).

    Args:
        db: The async database session.
        m_id: UUID of the meeting to look up stats for.
        s_id: UUID of the stat record.

    Returns:
        The Stat object if found, otherwise None.

    Raises:
        DatabaseError: If a SQLAlchemy error occurs.
    """
    try:
        if m_id:
            stmt = select(Stat).where(Stat.meeting_id == m_id)
        elif s_id:
            stmt = select(Stat).where(Stat.id == s_id)
        else:
            return None
        result = await db.execute(stmt)
        stat = result.scalar_one_or_none()
        logger.debug(f"get_stat: m_id={m_id}, s_id={s_id}, found={stat is not None}")
        return stat
    except SQLAlchemyError as e:
        logger.error(f"get_stat: database error for m_id={m_id}, s_id={s_id}: {e}")
        raise DatabaseError("database error occurred") from e


async def get_meeting_duration(db: AsyncSession, m_id: uuid.UUID) -> int:
    """
    Retrieve the duration of a meeting by its unique identifier.


    Args:
        db: The asynchronous SQLAlchemy session used to execute the query.
        m_id: The UUID of the meeting whose duration is to be fetched.

    Returns:
        The duration of the meeting as an integer.

    Raises:
        DatabaseError: If a SQLAlchemyError occurs during the query execution
    """
    try:
        stmt = select(Meeting.duration).where(Meeting.id == m_id)
        result = await db.execute(stmt)
        return result.scalar_one()
    except SQLAlchemyError as e:
        logger.exception("error fetching meeting (%s) field: %s", str(m_id), "duration")
        raise DatabaseError("database error occurred") from e


async def get_meeting_participant_cap(db: AsyncSession, m_id: uuid.UUID) -> int | None:
    """
    Retrieve the participant cap for a given meeting.

    Args:
        db: The async database session.
        m_id: The UUID of the meeting.

    Returns:
        The participant cap as an integer, or None if not found.

    Raises:
        DatabaseError: If a database error occurs.
    """
    try:
        logger.debug(f"fetching participant cap for meeting_id: {m_id}")
        stmt = select(Meeting.participant_cap).where(Meeting.id == m_id)
        result = await db.execute(stmt)
        participant_cap = result.scalar_one_or_none()
        logger.info(
            f"retrieved participant cap: {participant_cap} for meeting_id: {m_id}"
        )
        return participant_cap
    except SQLAlchemyError as e:
        logger.error(
            f"database error while fetching participant cap for meeting_id: {m_id}: {e}"
        )
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
        stmt = delete(Meeting).where((Meeting.id == m_id) & (Meeting.user_id == u_id))
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


async def delete_meetings(db: AsyncSession, u_id: uuid.UUID) -> None:
    """Delete all meetings belonging to a user.

    Args:
        db: The asynchronous SQLAlchemy session.
        u_id: The UUID of the user whose meetings to delete.

    Raises:
        DatabaseError: If a SQLAlchemy error occurs during the operation.
    """
    logger.debug("deleting all meetings for user %s", u_id)
    try:
        stmt = delete(Meeting).where(Meeting.user_id == u_id)
        result = cast(CursorResult, await db.execute(stmt))
        await db.commit()
        logger.debug(
            "all meetings deleted for user %s (affected rows: %d)",
            u_id,
            result.rowcount,
        )
        return
    except SQLAlchemyError as e:
        logger.exception("error deleting meetings for user %s: %s", u_id, e)
        raise DatabaseError from e


async def update_meeting(
    db: AsyncSession, m_id: uuid.UUID, returning: bool = False, **kwargs
):
    """
    Update a meeting record in the database.

    This function updates a meeting identified by its UUID with the provided
    keyword arguments. It optionally returns the updated meeting object or
    handles database errors by raising a custom DatabaseError.

    Args:
        db: The asynchronous database session.
        m_id: The UUID of the meeting to update.
        returning: If True, return the updated meeting object.
            Defaults to False.
        **kwargs: Additional fields to update on the meeting (e.g., title, date).

    Returns:
        Meeting | None: The updated meeting object if `returning` is True,
            otherwise None.

    Raises:
        DatabaseError: If a database error occurs during the update.
    """
    try:
        if returning:
            stmt = (
                update(Meeting)
                .where(Meeting.id == m_id)
                .values(**kwargs)
                .returning(Meeting)
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        else:
            stmt = update(Meeting).where(Meeting.id == m_id).values(**kwargs)
            await db.execute(stmt)
            return
    except SQLAlchemyError as e:
        raise DatabaseError from e
