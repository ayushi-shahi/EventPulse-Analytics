"""
app/tasks/scheduler.py

Replaces Celery worker + beat with APScheduler running inside the FastAPI process.
All jobs are async — no asyncio.run() needed (unlike the old Celery tasks).
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler():
    """Register all jobs and start the scheduler. Called from lifespan."""

    # Import here to avoid circular imports
    from app.tasks.tasks_ingest import process_event_batch
    from app.tasks.tasks_aggregates import (
        compute_minute_aggregates,
        compute_hourly_aggregates,
        cleanup_old_aggregates,
    )
    from app.tasks.tasks_alerts import evaluate_alerts

    scheduler.add_job(process_event_batch,        IntervalTrigger(seconds=5),     id="ingest",   replace_existing=True)
    scheduler.add_job(compute_minute_aggregates,  IntervalTrigger(seconds=60),    id="min_agg",  replace_existing=True)
    scheduler.add_job(compute_hourly_aggregates,  IntervalTrigger(seconds=3600),  id="hour_agg", replace_existing=True)
    scheduler.add_job(cleanup_old_aggregates,     IntervalTrigger(seconds=86400), id="cleanup",  replace_existing=True)
    scheduler.add_job(evaluate_alerts,            IntervalTrigger(seconds=60),    id="alerts",   replace_existing=True)

    scheduler.start()
    logger.info("APScheduler started with 5 jobs")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")