"""
app/tasks/tasks_aggregates.py

Aggregate computation tasks — run as APScheduler async jobs.
No Celery, no asyncio.run(). Async functions called directly.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete

from app.models.api_key import APIKey
from app.models.aggregate import Aggregate
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