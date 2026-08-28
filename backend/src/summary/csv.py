import csv
import logging
import os
from dataclasses import astuple, dataclass

from src.models import (
    LongAnswerQuestion,
    LongAnswerResponse,
    Meeting,
    MultipleChoiceQuestion,
    MultipleChoiceResponse,
    Question,
    RankedVotingQuestion,
    RankedVotingResponse,
    RatingScaleQuestion,
    RatingScaleResponse,
    YesNoQuestion,
    YesNoResponse,
)
from src.summary.exceptions import CSVGenerationError
from src.types import QuestionType

logger = logging.getLogger(__name__)


@dataclass
class CSVRow:
    """
    CSV Response Model representing one data row
    """

    question_id: str
    question_type: str
    question_text: str
    question_options: str
    participant_id: str
    answer: str
    timestamp: str


def generate_csv(meeting: Meeting, file_path: str):
    """
    Generates a CSV file for the provided meeting
    :param file_path: The path to create and write the CSV file
    :param meeting: The meeting to generate CSV for
    """
    logger.debug("starting CSV generation for meeting %r", meeting.title)
    headers = [
        "question_id",
        "question_type",
        "question_text",
        "question_options",
        "participant_id",
        "answer",
        "timestamp",
    ]
    csv_rows = []
    ordered = sorted(meeting.questions, key=lambda x: x.position)
    for q in ordered:
        q: Question
        csv_responses = _get_responses(q)
        csv_rows.extend(csv_responses)
    logger.debug("writing CSV from %d rows", len(csv_rows))
    tmp_path = f"{file_path}.tmp"
    with open(tmp_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        for row in csv_rows:
            writer.writerow(astuple(row))
    if not _verify_generation(file_path=tmp_path, expected_row_count=1 + len(csv_rows)):
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise CSVGenerationError
    os.replace(tmp_path, file_path)
    logger.info(
        "successfully generated CSV for meeting %r (%d rows)",
        meeting.title,
        len(csv_rows),
    )
    return


def _verify_generation(file_path: str, expected_row_count: int) -> bool:
    """
    Verifies that the generated CSV file has the correct format
    :param file_path: Path to the generated CSV file
    :param expected_row_count: Expected Number of rows in the generated CSV file
    :return: True if the CSV file has the correct format, False otherwise
    """
    # Ensure that the file has some data written to it.
    try:
        if not os.path.getsize(file_path) > 0:
            return False
        with open(file_path) as csvfile:
            row_count = sum(1 for _ in csv.reader(csvfile))
            if row_count != expected_row_count:
                logger.warning(
                    "CSV verification failed: expected %d rows, found %d",
                    expected_row_count,
                    row_count,
                )
                return False
        return True
    except FileNotFoundError:
        return False
    except PermissionError:
        return False
    except OSError:
        return False
    # Ensure that the row count matches the expected


def _format_long_answer(
    _: LongAnswerQuestion, r: LongAnswerResponse
) -> tuple[str, str]:
    """
    Formats the answer given a LongAnswerResponse
    :param r: LongAnswerResponse
    :return: Formatted answer
    """
    answer = str(r.content)
    options = ""
    return answer, options


def _format_multiple_choice(
    sub_q: MultipleChoiceQuestion, r: MultipleChoiceResponse
) -> tuple[str, str]:
    """
    Formats the answer given a MultipleChoiceResponse
    :param sub_q: MultipleChoiceQuestion
    :param r: MultipleChoiceResponse
    :return: Formatted answer and options
    """
    selected = []
    for c in r.selected_options:
        c: int
        selected.append(str(c))
    answer = ",".join(str(c) for c in selected if c is not None)
    opts = [sub_q.option_1, sub_q.option_2, sub_q.option_3, sub_q.option_4]
    options = ",".join(str(c) for c in opts if c is not None)
    return answer, options


def _format_ranked_voting(
    sub_q: RankedVotingQuestion, r: RankedVotingResponse
) -> tuple[str, str]:
    """
    Formats the answer given a RankedVotingResponse
    :param sub_q: RankedVotingQuestion
    :param r: RankedVotingResponse
    :return: Formatted answer and options
    """
    ranks = [r.rank_1, r.rank_2, r.rank_3, r.rank_4]
    answer = ",".join(str(c) for c in ranks if c is not None)
    items = [sub_q.item_1, sub_q.item_2, sub_q.item_3, sub_q.item_4]
    options = ",".join(str(i) for i in items if i is not None)
    return answer, options


def _format_rating_scale(
    sub_q: RatingScaleQuestion, r: RatingScaleResponse
) -> tuple[str, str]:
    """
    Formats the answer given a RatingScaleResponse
    :param sub_q: RatingScaleQuestion
    :param r: RatingScaleResponse
    :return: Formatted answer and options
    """
    answer = str(r.value)
    options = f"{sub_q.min}, {sub_q.max}"
    return answer, options


def _format_yes_no(_: YesNoQuestion, r: YesNoResponse) -> tuple[str, str]:
    """
    Formats the answer given a Yes/No response
    :param r: Yes/No response
    :return: Formatted answer and options
    """
    answer = "yes" if r.value else "no"
    options = "no, yes"
    return answer, options


def _get_responses(ques: Question) -> list[CSVRow]:
    """
    Extracts all responses to the provided question and converts them into a list of ``CSVResponse`` objects.
    :param ques: Question to extract responses from
    :return: List of ``CSVResponse`` objects
    """
    sub_q_map = {
        QuestionType.LONG_ANSWER: (ques.long_answer, _format_long_answer),
        QuestionType.MULTIPLE_CHOICE: (ques.multiple_choice, _format_multiple_choice),
        QuestionType.RANKED_VOTING: (ques.ranked_voting, _format_ranked_voting),
        QuestionType.RATING_SCALE: (ques.rating_scale, _format_rating_scale),
        QuestionType.YES_NO: (ques.yes_no, _format_yes_no),
    }
    sub_q, formatter = sub_q_map[ques.type]
    if sub_q is None:
        return []
    rows = []
    for r in sub_q.responses:
        values: tuple[str, str] = formatter(sub_q, r)
        csv_row = CSVRow(
            question_id=str(ques.id),
            question_text=str(ques.prompt),
            question_type=str(ques.type),
            question_options=values[1],
            participant_id=str(r.participant_id),
            answer=values[0],
            timestamp=str(r.created_at.isoformat()),
        )
        rows.append(csv_row)
    return rows
