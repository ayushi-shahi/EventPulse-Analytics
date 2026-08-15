"""
app/tasks/tasks_aggregates.py

Aggregate computation tasks — run as APScheduler async jobs.
No Celery, no asyncio.run(). Async functions called directly.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete, text

from app.models.api_key import APIKey
from app.models.aggregate import Aggregate
from app.models.event import Event
from app.services.metrics_service import MetricsService
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def compute_minute_aggregates():
    """Compute per-minute metrics for all active clients. Runs every 60s."""
    now = datetime.now(timezone.utc)
    interval_end = now.replace(second=0, microsecond=0)
    interval_start = interval_end - timedelta(minutes=1)

    logger.info(f"Minute aggregates: {interval_start} → {interval_end}")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(APIKey).where(APIKey.is_active == True))
        api_keys = result.scalars().all()
        if not api_keys:
            return

        service = MetricsService(db)
        for api_key in api_keys:
            client_id = str(api_key.id)
            try:
                events_data = await service.compute_events_per_minute(
                    client_id=client_id,
                    interval_start=interval_start,
                    interval_end=interval_end,
                )
                await service.save_aggregate(
                    client_id=client_id, metric_name="events_per_minute",
                    interval_start=interval_start, interval_end=interval_end,
                    value=events_data["rate"], meta_data={"count": events_data["count"]},
                )
                active_users = await service.compute_active_users(
                    client_id=client_id, window_start=interval_start, window_end=interval_end,
                )
                await service.save_aggregate(
                    client_id=client_id, metric_name="active_users_1m",
                    interval_start=interval_start, interval_end=interval_end,
                    value=float(active_users), meta_data={},
                )
            except Exception as e:
                logger.error(f"Minute agg error for {api_key.client_name}: {e}", exc_info=True)


async def compute_hourly_aggregates():
    """Compute per-hour metrics for all active clients. Runs every 3600s."""
    now = datetime.now(timezone.utc)
    interval_end = now.replace(minute=0, second=0, microsecond=0)
    interval_start = interval_end - timedelta(hours=1)

    logger.info(f"Hourly aggregates: {interval_start} → {interval_end}")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(APIKey).where(APIKey.is_active == True))
        api_keys = result.scalars().all()
        if not api_keys:
            return

        service = MetricsService(db)
        for api_key in api_keys:
            client_id = str(api_key.id)
            try:
                events_data = await service.compute_events_per_minute(
                    client_id=client_id, interval_start=interval_start, interval_end=interval_end,
                )
                await service.save_aggregate(
                    client_id=client_id, metric_name="events_per_hour",
                    interval_start=interval_start, interval_end=interval_end,
                    value=events_data["rate"] * 60, meta_data={"count": events_data["count"]},
                )
                active_users = await service.compute_active_users(
                    client_id=client_id, window_start=interval_start, window_end=interval_end,
                )
                await service.save_aggregate(
                    client_id=client_id, metric_name="active_users_1h",
                    interval_start=interval_start, interval_end=interval_end,
                    value=float(active_users), meta_data={},
                )
                top_events = await service.compute_top_events(
                    client_id=client_id, start_time=interval_start, end_time=interval_end, limit=10,
                )
                await service.save_aggregate(
                    client_id=client_id, metric_name="top_events_1h",
                    interval_start=interval_start, interval_end=interval_end,
                    value=float(len(top_events)), meta_data={"events": top_events},
                )
            except Exception as e:
                logger.error(f"Hourly agg error for {api_key.client_name}: {e}", exc_info=True)


async def cleanup_old_aggregates(days_to_keep: int = 30):
    """Delete aggregate rows older than `days_to_keep` days. Runs daily."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    logger.info(f"Cleaning aggregates older than {cutoff}")
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(delete(Aggregate).where(Aggregate.interval_start < cutoff))
            await db.commit()
            logger.info(f"Deleted {result.rowcount} old aggregate rows")
        except Exception as e:
            await db.rollback()
            logger.error(f"Cleanup failed: {e}", exc_info=True)


async def cleanup_old_events(days_to_keep: int = 90):
    """
    Delete raw events older than `days_to_keep` days. Runs daily.

    Aggregates were already pruned on a schedule, but the events table grew
    without bound. Rolling demo traffic adds roughly 1,700 rows a day, which
    fills a free-tier database inside a year — and a full database takes the
    whole platform down. Aggregates outlive the raw rows they were computed
    from, so historical charts survive the deletion.

    Deletes in chunks so a large backlog cannot hold one long transaction open
    against a small instance.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    logger.info(f"Cleaning events older than {cutoff}")

    total = 0
    async with AsyncSessionLocal() as db:
        try:
            while True:
                result = await db.execute(
                    text(
                        """
                        DELETE FROM events
                        WHERE id IN (
                            SELECT id FROM events WHERE event_time < :cutoff LIMIT 5000
                        )
                        """
                    ),
                    {"cutoff": cutoff},
                )
                await db.commit()
                deleted = result.rowcount or 0
                total += deleted
                if deleted < 5000:
                    break
            logger.info(f"Deleted {total} old event rows")
        except Exception as e:
            await db.rollback()
            logger.error(f"Event cleanup failed: {e}", exc_info=True)
