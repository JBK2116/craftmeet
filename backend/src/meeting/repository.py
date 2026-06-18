"""Meeting repository related services and management

This module provides data access layer functionality for meeting-related
operations, including meeting management, live session handling, and
meeting state persistence.
"""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import DatabaseError
from src.meeting.utils import SubQuestion
from src.models import Meeting, Question, Stat

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
