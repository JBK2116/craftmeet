"""Global SQLAlchemy ORM models

Defines the declarative base and all database models shared across the
application.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    UUID,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from src.constants import (
    MAX_DESCRIPTION_LENGTH,
    MAX_EMAIL_LENGTH,
    MAX_GOOGLE_ID_LENGTH,
    MAX_LONG_ANSWER_LENGTH,
    MAX_MEETING_DURATION_MINUTES,
    MAX_OPTION_LENGTH,
    MAX_PARTICIPANT_CAP,
    MAX_PASSWORD_LENGTH,
    MAX_PROMPT_LENGTH,
    MAX_RATING_SCALE_VALUE,
    MAX_TITLE_LENGTH,
    MAX_USERNAME_LENGTH,
    MEETING_CODE_LENGTH,
    MIN_RATING_SCALE_VALUE,
)
from src.database import Base
from src.types import MeetingPlan, MeetingStatus, QuestionStatus, QuestionType


class BaseClass(AsyncAttrs, Base):
    """Base class for all SQLAlchemy models"""

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        return cls.__name__.lower() + "s"


class User(BaseClass):
    """User Model"""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # User's unique username
    username: Mapped[str | None] = mapped_column(
        String(MAX_USERNAME_LENGTH), nullable=True
    )
    # User's email address (unique identifier)
    email: Mapped[str] = mapped_column(String(MAX_EMAIL_LENGTH), unique=True)
    # User's hashed password
    password: Mapped[str | None] = mapped_column(
        String(MAX_PASSWORD_LENGTH), nullable=True
    )
    # OAuth provider ID for Google authentication
    google_id: Mapped[str | None] = mapped_column(
        String(MAX_GOOGLE_ID_LENGTH), unique=True, nullable=True, index=True
    )
    # Flag indicating if user is currently in a live meeting
    live_meeting: Mapped[bool] = mapped_column(Boolean, default=False)
    # Total number of meetings held in the current month
    total_meetings_month: Mapped[int] = mapped_column(Integer, default=0)
    # Total number of meetings held by the user
    total_meetings: Mapped[int] = mapped_column(Integer, default=0)
    # Total number of participants across all meetings
    total_participants: Mapped[int] = mapped_column(Integer, default=0)
    # User's subscription plan tier
    meeting_plan: Mapped[MeetingPlan] = mapped_column(
        Enum(MeetingPlan, values_callable=lambda x: [e.value for e in x]),
        default=MeetingPlan.FREE,
    )
    # One user has many meetings, cascade delete removes all meetings on user delete
    meetings: Mapped[list["Meeting"]] = relationship(
        "Meeting", back_populates="user", cascade="all, delete", passive_deletes=True
    )
    # Account Verification Status
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Meeting(BaseClass):
    """Meeting Model"""

    # Unique identifier for the meeting, auto-generated UUID
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the user who created the meeting
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE")
    )
    # Relationship to the User model, enables access to meeting creator details
    user: Mapped["User"] = relationship(
        "User", back_populates="meetings", lazy="selectin"
    )
    # Title of the meeting, limited to MAX_TITLE_LENGTH characters
    title: Mapped[str] = mapped_column(String(MAX_TITLE_LENGTH))
    # Optional description of the meeting
    description: Mapped[str | None] = mapped_column(
        String(MAX_DESCRIPTION_LENGTH), nullable=True
    )
    # Total number of questions in the meeting
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    # Unique alphanumeric code for joining the meeting room
    room_code: Mapped[str] = mapped_column(String(MEETING_CODE_LENGTH), unique=True)
    # Current status of the meeting (DRAFT, LIVE, COMPLETED)
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, values_callable=lambda x: [e.value for e in x]),
        default=MeetingStatus.DRAFT,
    )
    # Timestamp when the meeting started, null if not yet started
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Timestamp when the meeting ended, null if still ongoing
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Max meeting duration in minutes
    duration: Mapped[int] = mapped_column(default=MAX_MEETING_DURATION_MINUTES)
    # URL pointing to the generated PDF export of the meeting (NULL meaning it hasn't been exported yet)
    pdf_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Timestamp of the most recent PDF export
    last_exported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Maximum number of participants allowed in the meeting, enforced at join time
    participant_cap: Mapped[int] = mapped_column(Integer, default=MAX_PARTICIPANT_CAP)
    # One-to-one relationship with Stat, cascade delete removes stats on meeting delete
    stats: Mapped["Stat"] = relationship(
        "Stat",
        back_populates="meeting",
        cascade="all, delete",
        passive_deletes=True,
        uselist=False,
    )
    # One meeting has many questions, cascade delete removes all questions on meeting delete
    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="meeting",
        cascade="all, delete",
        passive_deletes=True,
    )


class Stat(BaseClass):
    """Meeting Stats Model"""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the meeting
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("meetings.id", ondelete="CASCADE"), unique=True
    )
    # Relationship to the Meeting model
    meeting: Mapped["Meeting"] = relationship(
        "Meeting", back_populates="stats", lazy="selectin"
    )
    # Peak participant count during the session
    total_participants: Mapped[int] = mapped_column(Integer, default=0)
    # Total number of questions asked in the meeting
    total_questions_asked: Mapped[int] = mapped_column(Integer, default=0)
    # Total responses submitted across all questions
    total_responses_received: Mapped[int] = mapped_column(Integer, default=0)
    # Average responses per question relative to participant count
    average_response_rate: Mapped[float] = mapped_column(Float, default=0.0)
    # Session duration in seconds, derived from started_at/ended_at but stored for quick reads
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Question(BaseClass):
    """Base Question Model"""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the parent meeting
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("meetings.id", ondelete="CASCADE")
    )
    # Relationship to the Meeting model
    meeting: Mapped["Meeting"] = relationship(
        "Meeting", back_populates="questions", lazy="selectin"
    )
    # Question type enum determines which sub-table to join for full question shape
    type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, values_callable=lambda x: [e.value for e in x])
    )
    # Question prompt text shown to participants
    prompt: Mapped[str] = mapped_column(String(MAX_PROMPT_LENGTH))
    # Position in the meeting order, ascending
    position: Mapped[int] = mapped_column(Integer)
    # Current question status
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus, values_callable=lambda x: [e.value for e in x]),
        default=QuestionStatus.PENDING,
    )
    # Sub-question relationships (one-to-one), nullable since only one type will be set
    multiple_choice: Mapped["MultipleChoiceQuestion | None"] = relationship(
        "MultipleChoiceQuestion",
        back_populates="question",
        cascade="all, delete",
        passive_deletes=True,
        uselist=False,
    )
    long_answer: Mapped["LongAnswerQuestion | None"] = relationship(
        "LongAnswerQuestion",
        back_populates="question",
        cascade="all, delete",
        passive_deletes=True,
        uselist=False,
    )
    ranked_voting: Mapped["RankedVotingQuestion | None"] = relationship(
        "RankedVotingQuestion",
        back_populates="question",
        cascade="all, delete",
        passive_deletes=True,
        uselist=False,
    )
    rating_scale: Mapped["RatingScaleQuestion | None"] = relationship(
        "RatingScaleQuestion",
        back_populates="question",
        cascade="all, delete",
        passive_deletes=True,
        uselist=False,
    )
    yes_no: Mapped["YesNoQuestion | None"] = relationship(
        "YesNoQuestion",
        back_populates="question",
        cascade="all, delete",
        passive_deletes=True,
        uselist=False,
    )


class MultipleChoiceQuestion(BaseClass):
    """
    Multiple Choice Question Model

    Host defines up to 4 options
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the base question
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("questions.id", ondelete="CASCADE"), unique=True
    )
    # Relationship to the base Question model
    question: Mapped["Question"] = relationship(
        "Question", back_populates="multiple_choice", lazy="selectin"
    )
    # Host defined options option_1 and option_2 required, 3 and 4 optional
    option_1: Mapped[str] = mapped_column(String(MAX_OPTION_LENGTH))
    option_2: Mapped[str] = mapped_column(String(MAX_OPTION_LENGTH))
    option_3: Mapped[str | None] = mapped_column(
        String(MAX_OPTION_LENGTH), nullable=True
    )
    option_4: Mapped[str | None] = mapped_column(
        String(MAX_OPTION_LENGTH), nullable=True
    )
    # Whether participants can select more than one option
    allow_multiple: Mapped[bool] = mapped_column(Boolean, default=False)
    # Responses submitted to this question
    responses: Mapped[list["MultipleChoiceResponse"]] = relationship(
        "MultipleChoiceResponse",
        back_populates="question",
        cascade="all, delete",
        passive_deletes=True,
    )


class MultipleChoiceResponse(BaseClass):
    """
    Multiple Choice Response Model

    Stores selected option indexes per participant
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the multiple choice question
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("multiplechoicequestions.id", ondelete="CASCADE")
    )
    # Relationship to the MultipleChoiceQuestion model
    question: Mapped["MultipleChoiceQuestion"] = relationship(
        "MultipleChoiceQuestion", back_populates="responses", lazy="selectin"
    )
    # Participant identifier, scoped to meeting lifetime
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    # Array of selected option indexes (1-4), supports multi-select
    selected_options: Mapped[list[int]] = mapped_column(ARRAY(Integer))


class LongAnswerQuestion(BaseClass):
    """
    Long Answer Question Model
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the base question
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("questions.id", ondelete="CASCADE"), unique=True
    )
    # Relationship to the base Question model
    question: Mapped["Question"] = relationship(
        "Question", back_populates="long_answer", lazy="selectin"
    )
    # Maximum character length for responses
    max_length: Mapped[int] = mapped_column(Integer, default=MAX_LONG_ANSWER_LENGTH)
    # Responses submitted to this question
    responses: Mapped[list["LongAnswerResponse"]] = relationship(
        "LongAnswerResponse",
        back_populates="question",
        cascade="all, delete",
        passive_deletes=True,
    )


class LongAnswerResponse(BaseClass):
    """
    Long Answer Response Model

    Stores open text response per participant
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the long answer question
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("longanswerquestions.id", ondelete="CASCADE")
    )
    # Relationship to the LongAnswerQuestion model
    question: Mapped["LongAnswerQuestion"] = relationship(
        "LongAnswerQuestion", back_populates="responses", lazy="selectin"
    )
    # Participant identifier, scoped to meeting lifetime
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    # Open text response from the participant
    content: Mapped[str] = mapped_column(String(MAX_LONG_ANSWER_LENGTH))


class RankedVotingQuestion(BaseClass):
    """
    Ranked Voting Question Model

    Host defines up to 4 items for participants to priority rank
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the base question
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("questions.id", ondelete="CASCADE"), unique=True
    )
    # Relationship to the base Question model
    question: Mapped["Question"] = relationship(
        "Question", back_populates="ranked_voting", lazy="selectin"
    )
    # Host defined items to be ranked; item_1 and item_2 required, 3 and 4 optional
    item_1: Mapped[str] = mapped_column(String(MAX_OPTION_LENGTH))
    item_2: Mapped[str] = mapped_column(String(MAX_OPTION_LENGTH))
    item_3: Mapped[str | None] = mapped_column(String(MAX_OPTION_LENGTH), nullable=True)
    item_4: Mapped[str | None] = mapped_column(String(MAX_OPTION_LENGTH), nullable=True)
    # Responses submitted to this question
    responses: Mapped[list["RankedVotingResponse"]] = relationship(
        "RankedVotingResponse",
        back_populates="question",
        cascade="all, delete",
        passive_deletes=True,
    )


class RankedVotingResponse(BaseClass):
    """Ranked Voting Response Model

    Stores item number assigned to each rank position per participant.
    rank_1 = most important, rank_4 = least important.

    Value is the item number (1-4).
    e.g. rank_1 = 3 means the participant placed item_3 as their top priority.
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the ranked voting question
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("rankedvotingquestions.id", ondelete="CASCADE")
    )
    # Relationship to the RankedVotingQuestion model
    question: Mapped["RankedVotingQuestion"] = relationship(
        "RankedVotingQuestion", back_populates="responses", lazy="selectin"
    )
    # Participant identifier, scoped to meeting lifetime
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    # Item number assigned to each rank position (1-4), nullable mirrors optional items
    rank_1: Mapped[int] = mapped_column(Integer)
    rank_2: Mapped[int] = mapped_column(Integer)
    rank_3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_4: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RatingScaleQuestion(BaseClass):
    """Rating Scale Question Model"""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the base question
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("questions.id", ondelete="CASCADE"), unique=True
    )
    # Relationship to the base Question model
    question: Mapped["Question"] = relationship(
        "Question", back_populates="rating_scale", lazy="selectin"
    )
    # Scale range (defaults to 0-5)
    min: Mapped[int] = mapped_column(Integer, default=MIN_RATING_SCALE_VALUE)
    max: Mapped[int] = mapped_column(Integer, default=MAX_RATING_SCALE_VALUE)
    # Responses submitted to this question
    responses: Mapped[list["RatingScaleResponse"]] = relationship(
        "RatingScaleResponse",
        back_populates="question",
        cascade="all, delete",
        passive_deletes=True,
    )


class RatingScaleResponse(BaseClass):
    """Rating Scale Response Model

    Stores a single integer rating per participant
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the rating scale question
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("ratingscalequestions.id", ondelete="CASCADE")
    )
    # Relationship to the RatingScaleQuestion model
    question: Mapped["RatingScaleQuestion"] = relationship(
        "RatingScaleQuestion", back_populates="responses", lazy="selectin"
    )
    # Participant identifier, scoped to meeting lifetime
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    # Participant's rating value within the defined scale range
    value: Mapped[int] = mapped_column(Integer)


class YesNoQuestion(BaseClass):
    """
    Yes No Model

    Stores a direct reference to the Yes/No question posed by the host
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("questions.id", ondelete="CASCADE"), unique=True
    )
    question: Mapped["Question"] = relationship(
        "Question", back_populates="yes_no", lazy="selectin"
    )
    responses: Mapped[list["YesNoResponse"]] = relationship(
        "YesNoResponse",
        back_populates="question",
        cascade="all, delete",
        passive_deletes=True,
    )


class YesNoResponse(BaseClass):
    """Yes No Response Model

    Stores a boolean vote per participant, linked directly to base Question.
    No sub-question table needed as the prompt on Question is sufficient.
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("yesnoquestions.id", ondelete="CASCADE")
    )
    question: Mapped["YesNoQuestion"] = relationship(
        "YesNoQuestion", back_populates="responses", lazy="selectin"
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    value: Mapped[bool] = mapped_column(Boolean)
