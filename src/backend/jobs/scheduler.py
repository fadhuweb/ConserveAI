"""APScheduler setup — runs the daily forecast job at 03:00 Lagos time (UTC+1).

The scheduler is started from main.py on app startup and shut down on app shutdown.
Job failures are caught inside run_and_save() and logged; the scheduler itself
keeps running so the next day's job is not affected.
"""

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

logger    = logging.getLogger(__name__)
LAGOS_TZ  = ZoneInfo("Africa/Lagos")
scheduler = BackgroundScheduler(timezone=LAGOS_TZ)


def _daily_job():
    try:
        from src.backend.jobs.daily_forecast import run_and_save
        results = run_and_save()
        logger.info("Daily forecast job finished — %d parks updated.", len(results))
    except Exception:
        logger.exception("Daily forecast job raised an unhandled exception.")


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(_daily_job, "cron", hour=3, minute=0, id="daily_forecast", replace_existing=True)
        scheduler.start()
        logger.info("Scheduler started — daily forecast job at 03:00 Lagos time.")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")