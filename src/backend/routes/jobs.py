"""Scheduled-job trigger.

In production the in-process APScheduler is disabled (a scaled-to-zero container
can't fire it). Instead, an external scheduler (GitHub Actions cron) calls this
endpoint once a day. It's protected by a shared secret (JOB_TRIGGER_TOKEN) sent
in the `X-Job-Token` header. Running it also wakes the machine, doubling as a
keep-alive.
"""

from fastapi import APIRouter, Header, HTTPException, status

from src.backend.config import settings

router = APIRouter(prefix="/jobs", tags=["system"])


@router.post("/run-daily-forecast", summary="Run the daily forecast job (token-protected; for the scheduler)")
def run_daily_forecast(x_job_token: str | None = Header(default=None)):
    """Fetch the latest data and write today's forecasts. Returns a short summary.

    Synchronous on purpose: the caller (the cron) waits for completion, which
    keeps the container alive until the job finishes. A sync endpoint runs in a
    worker thread, so it won't block the event loop.
    """
    if not settings.job_trigger_token or x_job_token != settings.job_trigger_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing job token")

    from src.backend.jobs.daily_forecast import run_and_save
    results = run_and_save()
    return {"status": "ok", "parks_updated": len(results)}
