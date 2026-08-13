import asyncio
import datetime
import logging
import uuid
from pathlib import Path

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.meeting.exceptions import MeetingNotFoundError
from src.meeting.repository import get_meeting
from src.models import Meeting
from src.summary.csv import generate_csv
from src.summary.exceptions import MeetingNotEndedError, OpenAiError
from src.summary.pdf import generate_pdf
from src.summary.prompt import generate_summary_prompt
from src.summary.save import CSV_DIR, PDF_DIR, get_csv_path, save_pdf
from src.summary.schemas import MeetingSummary
from src.types import ExportTypes, MeetingStatus

settings = get_settings()

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API)


async def handle_summary(
    db: AsyncSession, meeting_id: uuid.UUID, export: ExportTypes
) -> Path:
    """
    Handle summarization or parsing of meeting summary.
    :param db: Active database session.
    :param meeting_id: UUID of the completed meeting to summarize.
    :param export: Type of summarization or parsing.
    :return: Path to the meeting summary CSV or PDF file.
    """
    match export:
        case ExportTypes.PDF:
            return await handle_pdf_summary(db=db, meeting_id=meeting_id)
        case ExportTypes.CSV:
            return await handle_csv_summary(db=db, meeting_id=meeting_id)


async def handle_pdf_summary(db: AsyncSession, meeting_id: uuid.UUID) -> Path:
    """Return the file path of the meeting summary PDF, regenerating only if needed.

    Args:
        db: Active database session.
        meeting_id: UUID of the completed meeting to summarize.

    Returns:
        Absolute ``Path`` to the existing or newly generated PDF file.

    Raises:
        MeetingNotFoundError: No meeting with the given ID.
        MeetingNotEndedError: Meeting has not yet completed.
        OpenAiError: AI summarization or parsing failed.
        PdfGenerationError: PDF generation or storage failed.
    """
    meeting = await get_meeting(db=db, m_id=meeting_id)
    if meeting is None:
        raise MeetingNotFoundError
    if meeting.status != MeetingStatus.COMPLETED:
        raise MeetingNotEndedError(str(meeting_id))

    existing = _get_existing_pdf_path(meeting_id=meeting_id)
    if existing is not None:
        logger.info("returning existing PDF for meeting %s", meeting_id)
        return existing

    prompts = generate_summary_prompt(meeting=meeting)
    ai_summary = await _get_ai_summary(
        sys_prompt=prompts["system"], user_prompt=prompts["user"]
    )
    summary = _get_summary_object(summary=ai_summary)
    pdf_bytes = generate_pdf(summary=summary, meeting_title=meeting.title)
    logger.info("generated PDF of %d bytes", len(pdf_bytes))

    filepath = await _save_pdf(meeting_id=meeting_id, pdf_bytes=pdf_bytes)
    meeting.pdf_url = str(filepath)
    meeting.last_exported_at = datetime.datetime.now(tz=datetime.UTC)
    await db.commit()
    logger.info("saved PDF for meeting %s and updated meeting record", meeting_id)

    return filepath


async def handle_csv_summary(db: AsyncSession, meeting_id: uuid.UUID) -> Path:
    """
    Return the file path of the meeting summary CSV, regenerating only if needed.
    :param db: Active database Session.
    :param meeting_id: UUID of the completed meeting to summarize.
    :return: Absolute ``Path`` to the existing or newly generated CSV file.
    :raises MeetingNotFoundError: No meeting with the given ID.
    :raises MeetingNotEndedError: Meeting has not yet completed.
    :raises PdfGenerationError: PDF generation or storage failed.
    :raises OSError: PDF storage or file failed to be created.
    """
    meeting = await get_meeting(db=db, m_id=meeting_id)
    if meeting is None:
        raise MeetingNotFoundError
    if meeting.status != MeetingStatus.COMPLETED:
        raise MeetingNotEndedError(str(meeting.id))

    existing_path = _get_existing_csv_path(meeting_id=meeting.id)
    if existing_path is not None:
        logger.info("returning existing CSV for meeting %s", meeting_id)
        return existing_path

    file_path = get_csv_path(meeting_id=meeting.id)
    await _generate_csv(meeting=meeting, file_path=str(file_path))
    return file_path


def _get_existing_pdf_path(meeting_id: uuid.UUID) -> Path | None:
    """
    Return the PDF path if the file exists on disk, otherwise None.
    :param meeting_id: UUID of the meeting.
    :return: Path to the existing PDF file if found, otherwise None.
    """
    filepath = PDF_DIR / f"{meeting_id}.pdf"
    if filepath.is_file():
        return filepath
    logger.debug("PDF path is set but file missing for meeting %s", meeting_id)
    return None


def _get_existing_csv_path(meeting_id: uuid.UUID) -> Path | None:
    """
    Return the CSV path if the file exists on disk, otherwise None.
    :param meeting_id: UUID of the meeting.
    :return: Path to the existing CSV file if found, otherwise None.
    """
    filepath = CSV_DIR / f"{meeting_id}.csv"
    if filepath.is_file():
        return filepath
    logger.debug("CSV Path is set but file missing for meeting %s", meeting_id)
    return None


async def _get_ai_summary(sys_prompt: str, user_prompt: str) -> str:
    """Fetch an AI-generated summary using the OpenAI Responses API.

    Args:
        sys_prompt: System-level instruction for the model.
        user_prompt: User input to generate a response for.

    Returns:
        The text content of the AI's response.

    Raises:
        OpenAiError: If the API call fails for any reason.
    """
    logger.debug(
        "fetching AI summary with sys_prompt of length %d and user_prompt of length %d",
        len(sys_prompt),
        len(user_prompt),
    )
    try:
        response = await client.responses.create(
            model="gpt-4.1", instructions=sys_prompt, input=user_prompt
        )
        logger.info(
            "successfully received AI response of length %d", len(response.output_text)
        )
        return response.output_text
    except Exception as e:
        logger.exception("failed to get AI summary: %s", e)
        raise OpenAiError from e


def _get_summary_object(summary: str) -> MeetingSummary:
    """Validate and parse the AI-generated summary string into a MeetingSummary object.

    Args:
        summary: The raw JSON string returned by the AI model.

    Returns:
        A validated MeetingSummary instance.

    Raises:
        OpenAiError: If the summary cannot be parsed or validated.
    """
    try:
        return MeetingSummary.model_validate_json(summary)
    except Exception as e:
        logger.exception("failed to parse AI summary: %s", e)
        raise OpenAiError from e


async def _save_pdf(meeting_id: uuid.UUID, pdf_bytes: bytes) -> Path:
    """Save PDF bytes to a file asynchronously.

    Attempts to save the PDF using an executor to avoid blocking the event loop.
    Falls back to synchronous saving if no running event loop is available.

    Args:
        meeting_id: The unique identifier for the meeting.
        pdf_bytes: The raw PDF data to save.

    Returns:
        Path to the saved PDF file.

    Raises:
        OSError: If file writing fails.
    """
    try:
        loop = asyncio.get_running_loop()
        path = await loop.run_in_executor(None, save_pdf, meeting_id, pdf_bytes)
        logger.debug("pdf saved asynchronously for meeting %s", meeting_id)
        return path
    except RuntimeError:
        path = save_pdf(meeting_id, pdf_bytes)
        logger.debug("pdf saved synchronously for meeting %s", meeting_id)
        return path


async def _generate_csv(meeting: Meeting, file_path: str):
    """
    Generate the CSV file asynchronously.
    :param meeting: The meeting to generate CSV for.
    :param file_path: The path to create and write the CSV to.
    """
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, generate_csv, meeting, file_path)
    except RuntimeError:
        generate_csv(meeting=meeting, file_path=file_path)
