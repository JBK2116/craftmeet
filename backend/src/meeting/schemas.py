"""
This file contains the meeting related schemas exchanged between the frontend and backend.

Including:
    - Responses
    - Questions
    - Meetings

"""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.constants import (
    MAX_DESCRIPTION_LENGTH,
    MAX_LONG_ANSWER_LENGTH,
    MAX_MEETING_DURATION_MINUTES,
    MAX_OPTION_LENGTH,
    MAX_PARTICIPANT_CAP,
    MAX_PROMPT_LENGTH,
    MAX_QUESTION_CAP,
    MAX_RATING_SCALE_VALUE,
    MAX_TITLE_LENGTH,
    MIN_RATING_SCALE_VALUE,
)
from src.types import MeetingStatus, QuestionStatus, QuestionType

# DATA TO FRONTEND
# Includes
# - Questions
# - Responses
# - Meetings


class YesNoResponseOut(BaseModel):
    """Model representing a yes/no response sent to the frontend"""

    id: uuid.UUID
    question_id: uuid.UUID
    participant_id: uuid.UUID
    value: bool

    model_config = ConfigDict(from_attributes=True)


class YesNoQuestionOut(BaseModel):
    """Model representing a yes/no question sent to the frontend"""

    id: uuid.UUID
    question_id: uuid.UUID
    responses: list[YesNoResponseOut]

    model_config = ConfigDict(from_attributes=True)


class RatingScaleResponseOut(BaseModel):
    """Model representing a rating scale response sent to the frontend"""

    id: uuid.UUID
    question_id: uuid.UUID
    participant_id: uuid.UUID
    value: int

    model_config = ConfigDict(from_attributes=True)


class RatingScaleQuestionOut(BaseModel):
    """Model representing a rating scale question sent to the frontend"""

    id: uuid.UUID
    question_id: uuid.UUID
    min: int
    max: int
    responses: list[RatingScaleResponseOut]

    model_config = ConfigDict(from_attributes=True)


class RankedVotingResponseOut(BaseModel):
    """Model representing a ranked voting response sent to the frontend"""

    id: uuid.UUID
    question_id: uuid.UUID
    participant_id: uuid.UUID
    rank_1: int
    rank_2: int
    rank_3: int | None
    rank_4: int | None

    model_config = ConfigDict(from_attributes=True)


class RankedVotingQuestionOut(BaseModel):
    """Model representing a ranked voting question sent to the frontend"""

    id: uuid.UUID
    question_id: uuid.UUID
    item_1: str
    item_2: str
    item_3: str | None
    item_4: str | None
    responses: list[RankedVotingResponseOut]

    model_config = ConfigDict(from_attributes=True)


class LongAnswerResponseOut(BaseModel):
    """Model representing a long answer response sent to the frontend."""

    id: uuid.UUID
    question_id: uuid.UUID
    participant_id: uuid.UUID
    content: str

    model_config = ConfigDict(from_attributes=True)


class LongAnswerQuestionOut(BaseModel):
    """Model representing a long answer question sent to the frontend."""

    id: uuid.UUID
    question_id: uuid.UUID
    max_length: int
    responses: list[LongAnswerResponseOut]

    model_config = ConfigDict(from_attributes=True)


class MultipleChoiceResponseOut(BaseModel):
    """Model representing multiple choice responses sent to the frontend."""

    id: uuid.UUID
    question_id: uuid.UUID
    participant_id: uuid.UUID
    selected_options: list[int]

    model_config = ConfigDict(from_attributes=True)


class MultipleChoiceQuestionOut(BaseModel):
    """Model representing a multiple choice question sent to the frontend."""

    id: uuid.UUID
    question_id: uuid.UUID
    option_1: str
    option_2: str
    option_3: str | None
    option_4: str | None
    allow_multiple: bool
    responses: list[MultipleChoiceResponseOut]

    model_config = ConfigDict(from_attributes=True)


class QuestionOut(BaseModel):
    """Model representing a question sent to the frontend."""

    id: uuid.UUID
    meeting_id: uuid.UUID
    type: QuestionType
    prompt: str
    position: int
    status: QuestionStatus
    sub_question: (
        MultipleChoiceQuestionOut
        | LongAnswerQuestionOut
        | RankedVotingQuestionOut
        | RatingScaleQuestionOut
        | YesNoQuestionOut
    )

    model_config = ConfigDict(from_attributes=True)


class StatOut(BaseModel):
    """Model representing meeting statistics sent to the frontend."""

    id: uuid.UUID
    meeting_id: uuid.UUID
    # Statistics
    total_participants: int
    total_questions_asked: int
    total_responses_received: int
    average_response_rate: float
    duration_seconds: int | None

    model_config = ConfigDict(from_attributes=True)


class MeetingOut(BaseModel):
    """Model representing a meeting sent to the frontend."""

    id: uuid.UUID
    user_id: uuid.UUID
    # Metadata
    title: str
    description: str | None
    total_questions: int
    room_code: str
    status: MeetingStatus
    stats: StatOut
    duration: int
    # Status
    started_at: datetime.datetime | None
    ended_at: datetime.datetime | None
    participant_cap: int
    # questions
    questions: list[QuestionOut]
    # Time
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# DATA SENT FROM FRONTEND
# Includes
# - Questions
# - Responses
# - Meetings
class YesNoQuestionIn(BaseModel):
    """Model representing a yes no question sent by the frontend"""


class YesNoResponseIn(BaseModel):
    """Model representing a yes no response sent by the frontend"""

    question_id: uuid.UUID
    participant_id: uuid.UUID
    value: bool


class RatingScaleQuestionIn(BaseModel):
    """Model representing a rating scale question sent by the frontend"""

    min: int = Field(ge=MIN_RATING_SCALE_VALUE, le=MAX_RATING_SCALE_VALUE)
    max: int = Field(ge=MIN_RATING_SCALE_VALUE, le=MAX_RATING_SCALE_VALUE)


class RatingScaleResponseIn(BaseModel):
    """Model representing a rating scale response sent by the frontend"""

    question_id: uuid.UUID
    participant_id: uuid.UUID
    value: int = Field(ge=MIN_RATING_SCALE_VALUE, le=MAX_RATING_SCALE_VALUE)


class RankedVotingQuestionIn(BaseModel):
    """Model representing a ranked voting question sent by the frontend"""

    item_1: str = Field(min_length=1, max_length=MAX_OPTION_LENGTH)
    item_2: str = Field(min_length=1, max_length=MAX_OPTION_LENGTH)
    item_3: str | None = Field(default=None, min_length=1, max_length=MAX_OPTION_LENGTH)
    item_4: str | None = Field(default=None, min_length=1, max_length=MAX_OPTION_LENGTH)


class RankedVotingResponseIn(BaseModel):
    """Model representing a ranked voting response sent by the frontend"""

    question_id: uuid.UUID
    participant_id: uuid.UUID
    rank_1: int = Field(ge=1, le=4)
    rank_2: int = Field(ge=1, le=4)
    rank_3: int | None = Field(ge=1, le=4, default=None)
    rank_4: int | None = Field(ge=1, le=4, default=None)


class LongAnswerQuestionIn(BaseModel):
    """Model representing a long answer question sent by the frontend"""

    max_length: int = Field(
        ge=1, le=MAX_LONG_ANSWER_LENGTH, default=MAX_LONG_ANSWER_LENGTH
    )


class LongAnswerResponseIn(BaseModel):
    """Model representing a long answer response sent by the frontend"""

    question_id: uuid.UUID
    participant_id: uuid.UUID
    content: str = Field(min_length=1, max_length=MAX_LONG_ANSWER_LENGTH)


class MultipleChoiceQuestionIn(BaseModel):
    """Model representing a multiple choice question sent by the frontend"""

    option_1: str = Field(min_length=1, max_length=MAX_OPTION_LENGTH)
    option_2: str = Field(min_length=1, max_length=MAX_OPTION_LENGTH)
    option_3: str | None = Field(
        default=None, min_length=1, max_length=MAX_OPTION_LENGTH
    )
    option_4: str | None = Field(
        default=None, min_length=1, max_length=MAX_OPTION_LENGTH
    )
    allow_multiple: bool = Field(default=False)


class MultipleChoiceResponseIn(BaseModel):
    """Model representing a multiple choice response sent by the frontend"""

    question_id: uuid.UUID
    participant_id: uuid.UUID
    selected_options: list[int]


class QuestionIn(BaseModel):
    """Model representing a question sent by the frontend"""

    type: QuestionType
    prompt: str = Field(min_length=1, max_length=MAX_PROMPT_LENGTH)
    position: int = Field(ge=1)
    sub_question: (
        MultipleChoiceQuestionIn
        | LongAnswerQuestionIn
        | RankedVotingQuestionIn
        | RatingScaleQuestionIn
        | YesNoQuestionIn
    )

    @model_validator(mode="before")
    @classmethod
    def parse_sub_question(cls, values):
        question_type = values.get("type")
        sub = values.get("sub_question", {})
        map_ = {
            "multiple_choice": MultipleChoiceQuestionIn,
            "long_answer": LongAnswerQuestionIn,
            "ranked_voting": RankedVotingQuestionIn,
            "rating_scale": RatingScaleQuestionIn,
            "yes_no": YesNoQuestionIn,
        }
        if isinstance(question_type, str) and question_type in map_:
            values["sub_question"] = map_[question_type](**sub)
        elif isinstance(question_type, QuestionType):
            values["sub_question"] = map_[question_type.value](**sub)
        return values


class MeetingIn(BaseModel):
    """Model representing a meeting sent by the frontend"""

    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    description: str | None = Field(
        default=None, min_length=1, max_length=MAX_DESCRIPTION_LENGTH
    )
    participant_cap: int = Field(
        default=MAX_PARTICIPANT_CAP, le=MAX_PARTICIPANT_CAP, ge=1
    )
    duration: int = Field(ge=1, le=MAX_MEETING_DURATION_MINUTES)
    questions: list[QuestionIn] = Field(max_length=MAX_QUESTION_CAP, min_length=1)


# DATA SENT FROM FRONTEND TO UPDATE MEETINGS
# Includes
# - Questions
# - Responses
# - Meetings


class QuestionInUpdate(BaseModel):
    """Model representing an updated question sent by the frontend"""

    id: uuid.UUID | None = Field(default=None)
    type: QuestionType
    prompt: str = Field(min_length=1, max_length=MAX_PROMPT_LENGTH)
    position: int = Field(ge=1)
    sub_question: (
        MultipleChoiceQuestionIn
        | LongAnswerQuestionIn
        | RankedVotingQuestionIn
        | RatingScaleQuestionIn
        | YesNoQuestionIn
    )

    @model_validator(mode="before")
    @classmethod
    def parse_sub_question(cls, values):
        question_type = values.get("type")
        sub = values.get("sub_question", {})
        map_ = {
            "multiple_choice": MultipleChoiceQuestionIn,
            "long_answer": LongAnswerQuestionIn,
            "ranked_voting": RankedVotingQuestionIn,
            "rating_scale": RatingScaleQuestionIn,
            "yes_no": YesNoQuestionIn,
        }
        if isinstance(question_type, str) and question_type in map_:
            values["sub_question"] = map_[question_type](**sub)
        elif isinstance(question_type, QuestionType):
            values["sub_question"] = map_[question_type.value](**sub)
        return values


class MeetingUpdate(BaseModel):
    """Model representing a meeting sent by the frontend"""

    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    description: str | None = Field(
        default=None, min_length=1, max_length=MAX_DESCRIPTION_LENGTH
    )
    participant_cap: int = Field(
        default=MAX_PARTICIPANT_CAP, le=MAX_PARTICIPANT_CAP, ge=1
    )
    duration: int = Field(ge=1, le=MAX_MEETING_DURATION_MINUTES)
    questions: list[QuestionInUpdate]
