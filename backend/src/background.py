import datetime
import logging
from typing import Any, cast

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import CursorResult
from sqlalchemy.sql import update

from src.database import AsyncSessionLocal
from src.models import User

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
        id="1",
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
            query = update(User).values(total_meetings_month=0)
            result = cast(
                CursorResult[Any], await db.execute(query)
            )  # cast here is purely for type checker
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
            logger.error(
                "Failed to reset field in database",
                extra={"table": "Users", "field": "total_meetings_month"},
            )


def _reset_monthly_meetings_count_trigger() -> CronTrigger:
    """
    Returns the ``trigger`` for the ``_reset_monthly_meetings_count`` function.
    :return: DateTrigger
    """
    trigger = CronTrigger(day=1, hour=0, minute=0, timezone=datetime.UTC)
    return trigger
