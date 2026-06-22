"""Meeting related services and management

This module provides meeting-related services and utilities for the application
including meeting creation, initialization and live logic.
"""

import logging
import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.meeting.exceptions import MeetingNotFoundError
from src.meeting.repository import (
    get_meeting,
    get_meetings,
    insert_meeting,
    insert_question,
    insert_stat,
    insert_sub_question,
)
from src.meeting.schemas import (
    MeetingIn,
    MeetingOut,
    MeetingUpdate,
    QuestionOut,
)
from src.meeting.utils import (
    SUB_QUESTION_ATTR,
    SubQuestion,
    _update_sub_question,
    build_meeting_out,
    build_question_out,
    generate_meeting_model,
    generate_question_model,
    generate_stat_model,
    generate_sub_question,
)
from src.models import (
    User,
)

logger = logging.getLogger(__name__)


async def handle_create_meeting(
    db: AsyncSession, request: Request, payload: MeetingIn
) -> MeetingOut:
    """Create a new meeting with questions and statistics.

    Args:
        db: The active asynchronous database session.
        request: The incoming FastAPI request, which carries the
            authenticated user via ``request.state.user``.
        payload: The validated meeting creation payload containing
            title, description, duration, participant cap, and a list
            of questions with their type-specific data.

    Returns:
        A fully populated MeetingOut schema representing the created
        meeting, including its questions, their sub-questions, and
        associated statistics.
    """
    user: User = request.state.user
    logger.info(
        "Creating meeting",
        extra={
            "user_id": str(user.id),
            "title": payload.title,
            "question_count": len(payload.questions),
        },
    )
    # start with saving the meeting object and work down the payload chain
    meeting = generate_meeting_model(u_id=user.id, meeting=payload)
    meeting = await insert_meeting(db=db, meeting=meeting)
    logger.debug(
        "Meeting inserted",
        extra={"meeting_id": str(meeting.id), "room_code": meeting.room_code},
    )
    # next is saving the question objects one by one
    questions_out: list[QuestionOut] = []
    for idx, q in enumerate(payload.questions, start=1):
        logger.debug(
            "Processing question",
            extra={
                "question_index": idx,
                "total_questions": len(payload.questions),
                "type": q.type.value,
            },
        )
        q_loaded = generate_question_model(meeting_id=meeting.id, question=q)
        q_loaded = await insert_question(db=db, question=q_loaded)
        sub_loaded = generate_sub_question(
            question_id=q_loaded.id,
            type=q.type,
            question=q.sub_question,
        )
        sub_loaded = await insert_sub_question(db=db, question=sub_loaded)
        # avoid lazy loading for responses as since this meeting is just created
        # it is guarenteed that responses for each sub question will be None
        sub_loaded.__dict__["responses"] = []
        questions_out.append(
            build_question_out(question=q_loaded, sub_question=sub_loaded)
        )
    # last is generating the stat model
    stat = generate_stat_model(meeting_id=meeting.id)
    stat = await insert_stat(db=db, stat=stat)
    logger.debug(
        "Stat inserted",
        extra={"stat_id": str(stat.id), "meeting_id": str(meeting.id)},
    )
    # build the meeting out payload and return it now
    meeting_out = build_meeting_out(
        meeting=meeting, questions_out=questions_out, stat=stat
    )
    # commit the transaction now as at this point, all information is loaded from the database
    await db.commit()
    logger.info(
        "Meeting created successfully",
        extra={
            "meeting_id": str(meeting.id),
            "room_code": meeting.room_code,
            "question_count": len(questions_out),
        },
    )
    return meeting_out


async def handle_get_meetings(
    db: AsyncSession, request: Request, limit: int, offset: int
) -> list[MeetingOut]:
    """Retrieve paginated meetings for the authenticated user.

    Args:
        db: The active asynchronous database session.
        request: The incoming FastAPI request, which carries the
            authenticated user via ``request.state.user``.
        limit: Maximum number of meetings to return.
        offset: Number of meetings to skip for pagination.

    Returns:
        A list of MeetingOut schemas, each fully populated with
        their questions, nested sub-questions, and statistics.
    """
    user: User = request.state.user
    logger.info(
        "Fetching meetings",
        extra={"user_id": str(user.id), "limit": limit, "offset": offset},
    )
    meetings = await get_meetings(db=db, u_id=user.id, limit=limit, offset=offset)
    logger.debug(
        "Meetings fetched",
        extra={"user_id": str(user.id), "count": len(meetings)},
    )
    meetings_out: list[MeetingOut] = []
    for idx, m in enumerate(meetings, start=1):
        logger.debug(
            "Processing meeting",
            extra={
                "meeting_index": idx,
                "total_meetings": len(meetings),
                "meeting_id": str(m.id),
                "question_count": len(m.questions),
            },
        )
        questions_out: list[QuestionOut] = []
        for q in m.questions:
            sub_question: SubQuestion = getattr(q, SUB_QUESTION_ATTR[q.type])
            assert sub_question is not None  # noqa: S101
            questions_out.append(
                build_question_out(question=q, sub_question=sub_question)
            )
        m_out = build_meeting_out(meeting=m, questions_out=questions_out, stat=m.stats)
        meetings_out.append(m_out)
    logger.info(
        "Meetings retrieved",
        extra={
            "user_id": str(user.id),
            "limit": limit,
            "offset": offset,
            "returned_count": len(meetings_out),
        },
    )
    return meetings_out


async def handle_get_meeting(db: AsyncSession, m_id: uuid.UUID) -> MeetingOut:
    """Retrieve a single meeting by its ID, including questions and statistics.

    Args:
        db: The active asynchronous database session.
        m_id: The UUID of the meeting to retrieve.

    Raises:
        MeetingNotFoundError: If no meeting with the given ID exists.

    Returns:
        A fully populated MeetingOut schema containing the meeting’s
        questions, nested sub-questions, and associated statistics.
    """
    logger.info(
        "Fetching meeting",
        extra={"meeting_id": str(m_id)},
    )
    meeting = await get_meeting(db=db, m_id=m_id)
    if meeting is None:
        logger.warning(
            "Meeting not found",
            extra={"meeting_id": str(m_id)},
        )
        raise MeetingNotFoundError
    logger.debug(
        "Meeting fetched",
        extra={"meeting_id": str(m_id), "question_count": len(meeting.questions)},
    )
    questions_out: list[QuestionOut] = []
    for q in meeting.questions:
        logger.debug(
            "Processing question",
            extra={
                "meeting_id": str(m_id),
                "question_id": str(q.id),
                "question_type": q.type.value,
            },
        )
        sub_question: SubQuestion = getattr(q, SUB_QUESTION_ATTR[q.type])
        assert sub_question is not None  # noqa: S101
        questions_out.append(build_question_out(question=q, sub_question=sub_question))
    m_out = build_meeting_out(
        meeting=meeting, questions_out=questions_out, stat=meeting.stats
    )
    logger.debug(
        "Meeting built",
        extra={
            "meeting_id": str(m_id),
            "question_count": len(questions_out),
        },
    )
    logger.info(
        "Meeting retrieved",
        extra={"meeting_id": str(m_id), "question_count": len(questions_out)},
    )
    return m_out


async def handle_update_meeting(
    db: AsyncSession, meeting_update: MeetingUpdate, m_id: uuid.UUID
) -> MeetingOut:
    """Update an existing meeting — title, description, duration, and questions.

    Uses a diff-and-merge pattern: existing questions with matching IDs are
    updated, new questions from the payload are inserted, and questions
    removed from the payload are deleted from the database.

    Args:
        db: The active asynchronous database session.
        meeting_update: The validated update payload containing the new
            title, description, duration, participant cap, and question list.
        m_id: The UUID of the meeting to update.

    Raises:
        MeetingNotFoundError: If no meeting with the given ID exists.

    Returns:
        A fully populated MeetingOut schema representing the updated
        meeting, including its questions, nested sub-questions, and
        associated statistics.
    """
    m_db = await get_meeting(db=db, m_id=m_id)
    if m_db is None:
        raise MeetingNotFoundError
    ## start with updating the meetings basic attributes
    ## values such as status, pdf_url, etc... are updated in endpoints
    ## that handle live meeting sessions
    m_db.title = meeting_update.title
    m_db.description = meeting_update.description
    m_db.total_questions = len(meeting_update.questions)
    m_db.duration = meeting_update.duration
    # update the questions following the diff & merge pattern scheme
    db_ids = {q.id: q for q in m_db.questions}
    visited_ids = set()
    q_out: list[QuestionOut] = []
    for q_up in meeting_update.questions:
        if q_up.id in db_ids:
            # update the existing question
            q_db = db_ids[q_up.id]
            q_db.prompt = q_up.prompt
            q_db.position = q_up.position
            sub_loaded = await _update_sub_question(q_db=q_db, sub_q=q_up.sub_question)
            visited_ids.add(q_up.id)
            q_out.append(build_question_out(question=q_db, sub_question=sub_loaded))
        else:
            # new question — insert it
            q_loaded = generate_question_model(meeting_id=m_id, question=q_up)
            q_loaded = await insert_question(db=db, question=q_loaded)
            sub_loaded = generate_sub_question(
                question_id=q_loaded.id,
                type=q_up.type,
                question=q_up.sub_question,
            )
            sub_loaded = await insert_sub_question(db=db, question=sub_loaded)
            sub_loaded.__dict__["responses"] = []
            visited_ids.add(q_loaded.id)
            q_out.append(build_question_out(question=q_loaded, sub_question=sub_loaded))
    # delete questions that were removed from the update payload
    for q_db in m_db.questions:
        if q_db.id not in visited_ids:
            logger.debug(
                "Deleting removed question",
                extra={"question_id": str(q_db.id)},
            )
            await db.delete(q_db)
    await db.refresh(m_db)
    # build the final meeting output
    m_out = build_meeting_out(meeting=m_db, questions_out=q_out, stat=m_db.stats)
    await db.commit()
    logger.info(
        "Meeting updated successfully",
        extra={
            "meeting_id": str(m_db.id),
            "room_code": m_db.room_code,
            "question_count": len(q_out),
        },
    )
    return m_out
