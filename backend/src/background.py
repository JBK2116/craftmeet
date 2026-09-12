import datetime
import logging
from pathlib import Path
from typing import Any, cast

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import CursorResult, select
from sqlalchemy.sql import update

from src.constants import MAX_MEETING_STORAGE_DURATION_SECONDS
from src.database import AsyncSessionLocal
from src.models import Meeting, User
from src.summary.save import CSV_DIR, PDF_DIR
from src.types import MeetingStatus

scheduler = AsyncIOScheduler()

logger = logging.getLogger(__name__)


def setup_scheduler() -> None:
    """
    Configures the background scheduler with all required jobs and starts it.
    :return: None
    """
    global scheduler

    scheduler.add_job(
        _reset_monthly_meetings_count_job,
        trigger=_reset_monthly_meetings_count_trigger(),
        replace_existing=True,
    )
    scheduler.add_job(
        _reset_malformed_meetings,
        trigger=_reset_malformed_meetings_trigger(),
        replace_existing=True,
        misfire_grace_time=5,
    )
    scheduler.add_job(
        _delete_expired_meeting_files,
        trigger=_delete_expired_meeting_files_trigger(),
        replace_existing=True,
    )

    scheduler.start()


def stop_scheduler() -> None:
    """Shut down the global scheduler."""
    global scheduler

    scheduler.shutdown()


async def _reset_monthly_meetings_count_job() -> None:
    """
    Resets the ``total_meetings_month`` column for all ``Users`` in the database table.
    :return: None
    """
    async with AsyncSessionLocal() as db:
        try:
            stmt = update(User).values(total_meetings_month=0)
            result = cast(
                CursorResult[Any], await db.execute(stmt)
            )  # cast here is purely for type checker
            await db.commit()
            logger.info(
                "Reset all values to 0 in database field",
                extra={
                    "table": "Users",
                    "field": "total_meetings_month",
                    "rows_affected": result.rowcount,
                },
            )
            return
        except Exception:
            await db.rollback()
            logger.error(
                "Failed to reset field in database",
                extra={"table": "Users", "field": "total_meetings_month"},
            )


def _reset_monthly_meetings_count_trigger() -> CronTrigger:
    """
    Returns the ``trigger`` for the ``_reset_monthly_meetings_count`` function.
    :return: CronTrigger
    """
    trigger = CronTrigger(day=1, hour=0, minute=0, timezone=datetime.UTC)
    return trigger


async def _reset_malformed_meetings() -> None:
    """
    Resets malformed meetings in the database if any.
    :return: None
    """
    async with AsyncSessionLocal() as db:
        try:
            stmt = (
                update(Meeting)
                .values(started_at=None, status=MeetingStatus.DRAFT)
                .where(
                    Meeting.status == MeetingStatus.LIVE,
                )
            )
            result = cast(
                CursorResult[Any], await db.execute(stmt)
            )  # cast here is purely for type checker
            await db.commit()
            logger.info(
                "Reset all malformed meetings in the database",
                extra={
                    "table": "Meetings",
                    "field": "status, started_at",
                    "rows_affected": result.rowcount,
                },
            )
        except Exception:
            await db.rollback()
            logger.error(
                "Failed to reset malformed meetings in database",
                extra={"table": "Meetings"},
            )


def _reset_malformed_meetings_trigger() -> DateTrigger:
    """
    Returns the ``trigger`` for the ``_reset_malformed_meetings`` function.
    :return: None
    """
    run_date = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=1)
    trigger = DateTrigger(run_date=run_date, timezone=datetime.UTC)
    return trigger


async def _delete_expired_meeting_files() -> None:
    """
    Delete meeting csvs and pdfs that have been stored on disk for over a certain period of time.
    :return: None
    """
    async with AsyncSessionLocal() as db:
        try:
            cutoff = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(
                seconds=MAX_MEETING_STORAGE_DURATION_SECONDS
            )
            stmt = select(Meeting).where(Meeting.last_exported_at < cutoff)
            meetings = (await db.execute(stmt)).scalars().all()
            count = len(meetings)
            if count == 0:
                logger.info(
                    "No meeting CSVs/PDFs to remove from disk",
                    extra={"Table": "Meeting", "File Count": count},
                )
                return
            removed_pdf = 0
            removed_csv = 0
            for m in meetings:
                pdf_path = PDF_DIR / f"{m.id}.pdf"
                if _delete_file(pdf_path):
                    removed_pdf += 1
                    m.pdf_url = None
                    m.last_exported_at = None
                csv_path = CSV_DIR / f"{m.id}.csv"
                if _delete_file(path=csv_path):
                    removed_csv += 1
            await db.commit()
            logger.info(
                "Removed expired CSVs/PDFs from disk",
                extra={
                    "Total PDF": count,
                    "Removed PDF": removed_pdf,
                    "Removed CSV": removed_csv,
                    "Table": "Meeting",
                },
            )
        except Exception:
            await db.rollback()
            logger.error(
                "Failed to delete expired meetings from local disk",
                extra={"table": "Meetings"},
            )


def _delete_expired_meeting_files_trigger() -> IntervalTrigger:
    """
    Return the ``trigger`` for the ``delete_expired_meeting_files`` function.
    :return: Interval Trigger
    """
    return IntervalTrigger(hours=1)


def _delete_file(path: Path) -> bool:
    """
    Deletes the file stored at the provided path.
    :param path: Path to the file
    :return: True if the file was removed, False otherwise.
    """
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        logger.warning("File not found to delete: %s", path)
        return False
    except OSError as e:
        logger.warning("Unable to delete file: %s", e)
        return False
