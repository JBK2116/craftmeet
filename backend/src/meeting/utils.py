"""
This module provides meeting related utility functions for operations,
"""

import logging
import secrets
import string
import uuid

from src.constants import MEETING_CODE_LENGTH
from src.meeting.schemas import (
    LongAnswerQuestionIn,
    LongAnswerQuestionOut,
    MeetingIn,
    MeetingOut,
    MultipleChoiceQuestionIn,
    MultipleChoiceQuestionOut,
    QuestionIn,
    QuestionInUpdate,
    QuestionOut,
    RankedVotingQuestionIn,
    RankedVotingQuestionOut,
    RatingScaleQuestionIn,
    RatingScaleQuestionOut,
    StatOut,
    YesNoQuestionIn,
    YesNoQuestionOut,
)
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
from src.types import QuestionType

SubQuestionIn = (
    MultipleChoiceQuestionIn
    | LongAnswerQuestionIn
    | RankedVotingQuestionIn
    | RatingScaleQuestionIn
    | YesNoQuestionIn
)
SubQuestion = (
    MultipleChoiceQuestion
    | LongAnswerQuestion
    | RankedVotingQuestion
    | RatingScaleQuestion
    | YesNoQuestion
)

SubQuestionOut = (
    MultipleChoiceQuestionOut
    | LongAnswerQuestionOut
    | RankedVotingQuestionOut
    | RatingScaleQuestionOut
    | YesNoQuestionOut
)

SUB_QUESTION_ATTR = {
    QuestionType.MULTIPLE_CHOICE: "multiple_choice",
    QuestionType.LONG_ANSWER: "long_answer",
    QuestionType.RANKED_VOTING: "ranked_voting",
    QuestionType.RATING_SCALE: "rating_scale",
    QuestionType.YES_NO: "yes_no",
}


logger = logging.getLogger(__name__)


def build_meeting_out(
    meeting: Meeting, questions_out: list[QuestionOut], stat: Stat
) -> MeetingOut:
    """Build a MeetingOut response schema from ORM models.

    Validates the stat model into its output schema and constructs the full
    MeetingOut with all fields, including the pre-built question outputs.

    Args:
        meeting: The Meeting ORM instance.
        questions_out: A list of QuestionOut schemas already built from
            the meeting's questions and their sub-questions.
        stat: The Stat ORM instance associated with the meeting.

    Returns:
        A fully populated MeetingOut schema ready for API response.
    """
    logger.debug(
        "Building MeetingOut",
        extra={
            "meeting_id": str(meeting.id),
            "question_count": len(questions_out),
            "stat_id": str(stat.id) if stat else None,
        },
    )
    stat_out = StatOut.model_validate(stat)
    meeting_out = MeetingOut(
        id=meeting.id,
        user_id=meeting.user_id,
        title=meeting.title,
        description=meeting.description,
        total_questions=len(questions_out),
        room_code=meeting.room_code,
        status=meeting.status,
        stats=stat_out,
        duration=meeting.duration,
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        participant_cap=meeting.participant_cap,
        questions=questions_out,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )
    logger.info(
        "MeetingOut built",
        extra={
            "meeting_id": str(meeting.id),
            "status": meeting_out.status.value if meeting_out.status else None,
            "total_questions": meeting_out.total_questions,
        },
    )
    return meeting_out


def build_question_out(question: Question, sub_question: SubQuestion) -> QuestionOut:
    """Convert a question model with its sub-question into an output schema.

    Args:
        question: The parent question model instance.
        sub_question: The sub-question model instance corresponding to the question type.

    Returns:
        A QuestionOut instance containing the question data and the validated sub-question output.
    """
    match question.type.value:
        case QuestionType.MULTIPLE_CHOICE.value:
            assert isinstance(sub_question, MultipleChoiceQuestion)  # noqa: S101
            sub_q = MultipleChoiceQuestionOut.model_validate(sub_question)
        case QuestionType.LONG_ANSWER.value:
            assert isinstance(sub_question, LongAnswerQuestion)  # noqa: S101
            sub_q = LongAnswerQuestionOut.model_validate(sub_question)
        case QuestionType.RANKED_VOTING.value:
            assert isinstance(sub_question, RankedVotingQuestion)  # noqa: S101
            sub_q = RankedVotingQuestionOut.model_validate(sub_question)
        case QuestionType.RATING_SCALE.value:
            assert isinstance(sub_question, RatingScaleQuestion)  # noqa: S101
            sub_q = RatingScaleQuestionOut.model_validate(sub_question)
        case QuestionType.YES_NO.value:
            assert isinstance(sub_question, YesNoQuestion)  # noqa: S101
            sub_q = YesNoQuestionOut.model_validate(sub_question)
    return QuestionOut(
        id=question.id,
        meeting_id=question.meeting_id,
        type=question.type,
        prompt=question.prompt,
        position=question.position,
        status=question.status,
        sub_question=sub_q,
    )


async def _update_sub_question(q_db: Question, sub_q: SubQuestionIn) -> SubQuestion:
    match q_db.type.value:
        case QuestionType.MULTIPLE_CHOICE.value:
            assert q_db.multiple_choice is not None  # noqa: S101
            assert isinstance(sub_q, MultipleChoiceQuestionIn)  # noqa: S101
            q_db.multiple_choice.option_1 = sub_q.option_1
            q_db.multiple_choice.option_2 = sub_q.option_2
            q_db.multiple_choice.option_3 = sub_q.option_3
            q_db.multiple_choice.option_4 = sub_q.option_4
            q_db.multiple_choice.allow_multiple = sub_q.allow_multiple
            return q_db.multiple_choice
        case QuestionType.LONG_ANSWER.value:
            assert q_db.long_answer is not None  # noqa: S101
            assert isinstance(sub_q, LongAnswerQuestionIn)  # noqa: S101
            q_db.long_answer.max_length = sub_q.max_length
            return q_db.long_answer
        case QuestionType.RANKED_VOTING.value:
            assert q_db.ranked_voting is not None  # noqa: S101
            assert isinstance(sub_q, RankedVotingQuestionIn)  # noqa: S101
            q_db.ranked_voting.item_1 = sub_q.item_1
            q_db.ranked_voting.item_2 = sub_q.item_2
            q_db.ranked_voting.item_3 = sub_q.item_3
            q_db.ranked_voting.item_4 = sub_q.item_4
            return q_db.ranked_voting
        case QuestionType.RATING_SCALE.value:
            assert q_db.rating_scale is not None  # noqa: S101
            assert isinstance(sub_q, RatingScaleQuestionIn)  # noqa: S101
            q_db.rating_scale.min = sub_q.min
            q_db.rating_scale.max = sub_q.max
            return q_db.rating_scale
        case QuestionType.YES_NO.value:
            assert q_db.yes_no is not None  # noqa: S101
            assert isinstance(sub_q, YesNoQuestionIn)  # noqa: S101
            return q_db.yes_no


def generate_meeting_model(u_id: uuid.UUID, meeting: MeetingIn) -> Meeting:
    """Create a Meeting instance from a user and payload.

    Generates a unique room code and constructs a Meeting object with the
    provided user ID and meeting details from the payload.

    Args:
        u_id: The UUID of the user creating the meeting.
        meeting: The validated meeting input data containing title,
            optional description, duration, and participant cap.

    Returns:
        A new Meeting instance with the specified properties.
    """
    return Meeting(
        user_id=u_id,
        title=meeting.title,
        description=meeting.description if meeting.description else None,
        room_code=_generate_room_code(),
        duration=meeting.duration,
        participant_cap=meeting.participant_cap,
        total_questions=len(meeting.questions),
    )


def generate_stat_model(meeting_id: uuid.UUID) -> Stat:
    """
    Generate a Stat model for a meeting.

    Args:
        meeting_id (uuid.UUID): The unique identifier for the meeting.

    Returns:
        Stat: The generated Stat model.
    """
    return Stat(meeting_id=meeting_id)


def generate_question_model(
    meeting_id: uuid.UUID, question: QuestionIn | QuestionInUpdate
) -> Question:
    """Create a Question model instance for a meeting.

    Args:
        meeting_id: The UUID of the meeting to associate the question with.
        question: The input data for the question including type, prompt, and position.

    Returns:
        A Question object instantiated with the provided data.
    """
    return Question(
        meeting_id=meeting_id,
        type=question.type,
        prompt=question.prompt,
        position=question.position,
    )


def generate_sub_question(
    question_id: uuid.UUID,
    type: QuestionType,
    question: SubQuestionIn,
) -> SubQuestion:
    """Create a sub-question model (e.g. MultipleChoice, LongAnswer) based on question type.

    Dispatches to the correct sub-question model constructor by matching the
    question type against known types. Asserts that the provided question input
    is of the expected type before constructing the model.

    Args:
        question_id: The UUID of the parent question to associate with.
        type: The type of question being created (e.g. multiple choice,
            long answer, ranked voting, rating scale, yes/no).
        question: The validated input data for the sub-question, which must
            correspond to the specified type.

    Returns:
        A sub-question model instance (e.g. MultipleChoiceQuestion,
        LongAnswerQuestion, RankedVotingQuestion, RatingScaleQuestion,
        or YesNoQuestion) populated with the provided input.
    """
    logging.debug(
        "question_type and question",
        extra={"question_type": QuestionType, "question": question},
    )
    match type.value:
        case QuestionType.MULTIPLE_CHOICE.value:
            assert isinstance(question, MultipleChoiceQuestionIn)  # noqa: S101
            return MultipleChoiceQuestion(
                question_id=question_id,
                option_1=question.option_1,
                option_2=question.option_2,
                option_3=question.option_3,
                option_4=question.option_4,
                allow_multiple=question.allow_multiple,
            )
        case QuestionType.LONG_ANSWER.value:
            assert isinstance(question, LongAnswerQuestionIn)  # noqa: S101
            return LongAnswerQuestion(
                question_id=question_id, max_length=question.max_length
            )
        case QuestionType.RANKED_VOTING.value:
            assert isinstance(question, RankedVotingQuestionIn)  # noqa: S101
            return RankedVotingQuestion(
                question_id=question_id,
                item_1=question.item_1,
                item_2=question.item_2,
                item_3=question.item_3,
                item_4=question.item_4,
            )
        case QuestionType.RATING_SCALE.value:
            assert isinstance(question, RatingScaleQuestionIn)  # noqa: S101
            return RatingScaleQuestion(
                question_id=question_id, min=question.min, max=question.max
            )
        case QuestionType.YES_NO.value:
            assert isinstance(question, YesNoQuestionIn)  # noqa: S101
            return YesNoQuestion(question_id=question_id)


def _generate_room_code() -> str:
    """Generate a numeric random room code of specified length."""
    return "".join(secrets.choice(string.digits) for _ in range(MEETING_CODE_LENGTH))
