import datetime
import logging
import uuid

from src.auth.repository import update_user
from src.constants import MAX_PARTICIPANT_CAP
from src.database import AsyncSessionLocal
from src.meeting.repository import (
    get_meeting_duration,
    get_meeting_participant_cap,
    update_meeting,
)
from src.meeting.schemas import QuestionOut, ResponseIn
from src.types import MeetingStatus

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

    async def host_connected(self):
        """Mark the meeting as live when the host first connects (opens the host page)."""
        async with AsyncSessionLocal() as db:
            await db.begin()
            await update_meeting(
                db=db, m_id=self.meeting_id, status=MeetingStatus.LIVE
            )
            await update_user(db=db, u_id=self.host_id, live_meeting=True)
            await db.commit()
        logger.debug(
            "host connected, meeting set to live",
            extra={"meeting_id": str(self.meeting_id), "host_id": str(self.host_id)},
        )

    async def start_meeting(self):
        """Start the meeting — sets the started_at timestamp and begins the timer."""
        now = datetime.datetime.now(tz=datetime.UTC)
        async with AsyncSessionLocal() as db:
            await db.begin()
            await update_meeting(db=db, m_id=self.meeting_id, started_at=now)
            await db.commit()
        logger.debug(
            "meeting started in service layer",
            extra={"meeting_id": str(self.meeting_id), "host_id": str(self.host_id)},
        )
        return

    async def end_meeting(self):
        """End a meeting that was terminated manually."""
        async with AsyncSessionLocal() as db:
            await db.begin()
            await update_meeting(
                db=db, m_id=self.meeting_id, status=MeetingStatus.COMPLETED
            )
            await update_user(db=db, u_id=self.host_id, live_meeting=False)
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
            return
        if response.type != self.current_question.type:
            return
        self.responses.setdefault(response.question_id, []).append(response)

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
