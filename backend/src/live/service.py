import datetime
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import get_user, update_user
from src.constants import MAX_PARTICIPANT_CAP
from src.database import AsyncSessionLocal
from src.meeting.repository import (
    get_meeting_duration,
    get_meeting_lazy,
    get_meeting_participant_cap,
    get_stat,
    update_meeting,
)
from src.meeting.schemas import QuestionOut, ResponseIn
from src.models import (
    LongAnswerResponse,
    MultipleChoiceResponse,
    RankedVotingResponse,
    RatingScaleResponse,
    Stat,
    YesNoResponse,
)
from src.types import MeetingStatus, QuestionType

logger = logging.getLogger(__name__)


class LiveService:
    def __init__(self, host_id: uuid.UUID, meeting_id: uuid.UUID):
        self.host_id = host_id  # The unique identifier for the host of the meeting
        self.meeting_id = meeting_id  # The unique identifier for the meeting
        self.current_question: QuestionOut | None = (
            None  # The current question being asked, or None if no question
        )
        self.responses: dict[
            uuid.UUID, list[ResponseIn]
        ] = {}  # A dictionary mapping participant UUIDs to their list of responses
        self.total_questions_asked: int = 0

    async def host_connected(self):
        """Mark the meeting as live when the host first connects (opens the host page)."""
        async with AsyncSessionLocal() as db:
            await db.begin()
            await update_meeting(db=db, m_id=self.meeting_id, status=MeetingStatus.LIVE)
            await update_user(db=db, u_id=self.host_id, live_meeting=True)
            await db.commit()
        logger.debug(
            "host connected, meeting set to live",
            extra={"meeting_id": str(self.meeting_id), "host_id": str(self.host_id)},
        )

    async def start_meeting(self):
        """Start the meeting — sets the started_at timestamp and begins the timer."""
        now = datetime.datetime.now(tz=datetime.UTC)
        self.started_at = now
        async with AsyncSessionLocal() as db:
            await db.begin()
            await update_meeting(db=db, m_id=self.meeting_id, started_at=now)
            await db.commit()
        logger.debug(
            "meeting started in service layer",
            extra={"meeting_id": str(self.meeting_id), "host_id": str(self.host_id)},
        )
        return

    async def end_meeting(self, total_participants: int = 0):
        """End a meeting that was terminated manually."""
        async with AsyncSessionLocal() as db:
            await db.begin()
            await self._update_meeting_user(
                db=db, total_participants=total_participants
            )
            await self.__save_stats(db=db, total_participants=total_participants)
            await self.__save_responses(db=db)
            await db.commit()
        logger.debug(
            "meeting ended in service layer",
            extra={
                "meeting_id": str(self.meeting_id),
                "host_id": str(self.host_id),
            },
        )

    async def end_stale_meeting(self):
        """End a meeting that was terminated automatically due to host inactivity."""
        async with AsyncSessionLocal() as db:
            await db.begin()
            await update_meeting(
                db=db,
                m_id=self.meeting_id,
                started_at=None,
                status=MeetingStatus.COMPLETED,
            )
            await update_user(db=db, u_id=self.host_id, live_meeting=False)
            await db.commit()
        logger.debug(
            "stale meeting ended in service layer",
            extra={"meeting_id": str(self.meeting_id), "host_id": str(self.host_id)},
        )

    def add_response(self, response: ResponseIn) -> None:
        """
        Add a new response to the current questions response array
        """
        if self.current_question is None:
            logger.debug(
                "response dropped: no active question",
                extra={
                    "meeting_id": str(self.meeting_id),
                    "participant_id": str(response.participant_id),
                },
            )
            return
        if response.type != self.current_question.type:
            logger.debug(
                "response dropped: type mismatch",
                extra={
                    "meeting_id": str(self.meeting_id),
                    "expected": self.current_question.type.value,
                    "received": response.type.value,
                },
            )
            return
        self.responses.setdefault(response.question_id, []).append(response)
        logger.debug(
            "response added",
            extra={
                "meeting_id": str(self.meeting_id),
                "question_id": str(response.question_id),
                "participant_id": str(response.participant_id),
                "type": response.type.value,
            },
        )

    def get_current_responses(self) -> list[ResponseIn]:
        """returns the responses received for the current question"""
        if self.current_question is None:
            return []
        return self.responses.get(self.current_question.id, [])

    async def get_meeting_duration(self) -> int:
        """Get the meeting duration from the db"""
        async with AsyncSessionLocal() as db:
            duration = await get_meeting_duration(db=db, m_id=self.meeting_id)
            return duration

    async def get_meeting_participant_cap(self) -> int:
        """Get the meeting participant cap from the db and set it as an attribute"""
        async with AsyncSessionLocal() as db:
            cap = await get_meeting_participant_cap(db=db, m_id=self.meeting_id)
            if cap is None:
                cap = MAX_PARTICIPANT_CAP
            self.participant_cap = cap
            return cap

    async def __save_responses(self, db: AsyncSession) -> None:
        """Persist all collected responses to the database.

        Iterates over all stored response data, creates the appropriate ORM object
        for each response type, and adds them to the transaction.
        Flushes the changes to enable later transaction commit.
        Args:
            db: The active asynchronous database session.
        """
        total_responses = 0
        for q_id, responses in self.responses.items():
            for response in responses:
                match response.type:
                    case QuestionType.MULTIPLE_CHOICE:
                        obj = MultipleChoiceResponse(
                            question_id=q_id,
                            participant_id=response.participant_id,
                            selected_options=response.selected_options,
                        )
                    case QuestionType.LONG_ANSWER:
                        obj = LongAnswerResponse(
                            question_id=q_id,
                            participant_id=response.participant_id,
                            content=response.content,
                        )
                    case QuestionType.RANKED_VOTING:
                        obj = RankedVotingResponse(
                            question_id=q_id,
                            participant_id=response.participant_id,
                            rank_1=response.rank_1,
                            rank_2=response.rank_2,
                            rank_3=response.rank_3,
                            rank_4=response.rank_4,
                        )
                    case QuestionType.RATING_SCALE:
                        obj = RatingScaleResponse(
                            question_id=q_id,
                            participant_id=response.participant_id,
                            value=response.value,
                        )
                    case QuestionType.YES_NO:
                        obj = YesNoResponse(
                            question_id=q_id,
                            participant_id=response.participant_id,
                            value=response.value,
                        )
                db.add(obj)
                total_responses += 1
        await db.flush()
        logger.info(
            "responses persisted",
            extra={
                "meeting_id": str(self.meeting_id),
                "total_responses": total_responses,
            },
        )

    async def __save_stats(self, db: AsyncSession, total_participants: int) -> None:
        """Save meeting statistics to the database.

        Creates or updates a Stat record for the current meeting.
        The stats include participant count, questions asked, responses received,
        average response rate, and meeting duration.

        Args:
            db: The async database session used for persistence.
            total_participants: The total number of participants in the meeting.

        Returns:
            None
        """
        # create and save the meeting stats object
        now = datetime.datetime.now(tz=datetime.UTC)
        total_questions_asked = self.total_questions_asked
        total_responses_received = sum(len(v) for v in self.responses.values())
        average_response_rate = float(
            total_responses_received / total_participants if total_participants else 0.0
        )
        duration_seconds = int((now - self.started_at).total_seconds())
        stat = await get_stat(db=db, m_id=self.meeting_id)
        if stat is None:
            stat = Stat(
                meeting_id=self.meeting_id,
                total_participants=total_participants,
                total_questions_asked=total_questions_asked,
                total_responses_received=total_responses_received,
                average_response_rate=average_response_rate,
                duration_seconds=duration_seconds,
            )
        else:
            stat.total_participants = total_participants
            stat.total_questions_asked = total_questions_asked
            stat.total_responses_received = total_responses_received
            stat.average_response_rate = average_response_rate
            stat.duration_seconds = duration_seconds
        db.add(stat)
        await db.flush()
        logger.info(
            "meeting stats saved",
            extra={
                "meeting_id": str(self.meeting_id),
                "total_participants": total_participants,
                "total_questions_asked": total_questions_asked,
                "total_responses_received": total_responses_received,
                "average_response_rate": average_response_rate,
                "duration_seconds": duration_seconds,
            },
        )

    async def _update_meeting_user(
        self, db: AsyncSession, total_participants: int
    ) -> None:
        """
        Update user and meeting stats after a meeting ends.

        This function updates the host user's cumulative and monthly meeting statistics,
        and marks the meeting as completed with the current timestamp.

        Args:
            db: The database session for executing queries.
            total_participants: Total number of participants in the meeting.

        Returns:
            None
        """
        now = datetime.datetime.now(tz=datetime.UTC)
        # update the user stats
        user = await get_user(db=db, u_id=self.host_id)
        if user is None:
            logger.error(
                "host user not found during meeting end",
                extra={
                    "meeting_id": str(self.meeting_id),
                    "host_id": str(self.host_id),
                },
            )
            return

        user.live_meeting = False
        user.total_meetings += 1
        user.total_participants += total_participants

        if _is_same_month(year=user.current_year, month=user.current_month):
            user.total_meetings_month += 1
            logger.debug(
                "monthly meeting counter incremented",
                extra={
                    "host_id": str(self.host_id),
                    "month": user.current_month,
                    "year": user.current_year,
                    "count": user.total_meetings_month,
                },
            )
        else:
            user.current_year = now.year
            user.current_month = now.month
            user.total_meetings_month = 1
            logger.info(
                "monthly meeting counter reset for new month",
                extra={
                    "host_id": str(self.host_id),
                    "month": now.month,
                    "year": now.year,
                },
            )

        db.add(user)

        # update the meeting stats
        meeting = await get_meeting_lazy(db=db, m_id=self.meeting_id)
        if meeting is None:
            logger.error(
                "meeting not found during end",
                extra={
                    "meeting_id": str(self.meeting_id),
                    "host_id": str(self.host_id),
                },
            )
            return

        meeting.ended_at = now
        meeting.status = MeetingStatus.COMPLETED

        db.add(meeting)
        await db.flush()


def _is_same_month(year: int, month: int) -> bool:
    """Check if the given year and month match the current month and year.

    Args:
        year: The year to compare.
        month: The month to compare (1-12).

    Returns:
        True if the given year and month are the same as the current UTC year and month, False otherwise.
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    current_month = now.month
    current_year = now.year
    return year == current_year and month == current_month
