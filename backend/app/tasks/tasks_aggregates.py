# backend/app/tasks/tasks_aggregates.py
"""
Aggregate computation Celery tasks.

All Celery tasks here are synchronous entry points.
Async work (DB queries) runs inside asyncio.run() — giving each task
its own clean, isolated event loop. No get_event_loop() used anywhere.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete

from app.tasks.celery_app import celery_app
from app.models.api_key import APIKey
from app.models.aggregate import Aggregate
from app.services.metrics_service import MetricsService
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# compute_minute_aggregates
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.tasks_aggregates.compute_minute_aggregates",
    bind=True,
)
def compute_minute_aggregates(self):
    """
    Compute 1-minute aggregates for all active clients.
    Scheduled every 60 seconds via Celery Beat.

    Metrics computed:
    - events_per_minute
    - active_users_1m
    """
    return asyncio.run(_compute_minute_aggregates_async())


async def _compute_minute_aggregates_async():
    now = datetime.now(timezone.utc)
    interval_end = now.replace(second=0, microsecond=0)
    interval_start = interval_end - timedelta(minutes=1)

    logger.info(f"Computing minute aggregates: {interval_start} → {interval_end}")

    results = {
        "interval_start": interval_start.isoformat(),
        "interval_end": interval_end.isoformat(),
        "clients_processed": 0,
        "metrics_computed": 0,
        "errors": [],
    }

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(APIKey).where(APIKey.is_active == True)
            )
            api_keys = result.scalars().all()

            if not api_keys:
                logger.info("No active clients found — skipping minute aggregates")
                return {**results, "message": "No active clients found"}

            service = MetricsService(db)

            for api_key in api_keys:
                client_id = str(api_key.id)
                try:
                    # 1. events_per_minute
                    events_data = await service.compute_events_per_minute(
                        client_id=client_id,
                        interval_start=interval_start,
                        interval_end=interval_end,
                    )
                    await service.save_aggregate(
                        client_id=client_id,
                        metric_name="events_per_minute",
                        interval_start=interval_start,
                        interval_end=interval_end,
                        value=events_data["rate"],
                        meta_data={"count": events_data["count"]},
                    )

                    # 2. active_users_1m
                    active_users = await service.compute_active_users(
                        client_id=client_id,
                        window_start=interval_start,
                        window_end=interval_end,
                    )
                    await service.save_aggregate(
                        client_id=client_id,
                        metric_name="active_users_1m",
                        interval_start=interval_start,
                        interval_end=interval_end,
                        value=float(active_users),
                        meta_data={},
                    )

                    results["clients_processed"] += 1
                    results["metrics_computed"] += 2

                    logger.info(
                        f"✅ {api_key.client_name}: "
                        f"{events_data['rate']} events/min, "
                        f"{active_users} active users"
                    )

                except Exception as e:
                    msg = f"Error processing client {api_key.client_name}: {e}"
                    logger.error(msg, exc_info=True)
                    results["errors"].append(msg)

        except Exception as e:
            msg = f"Fatal error in minute aggregates: {e}"
            logger.error(msg, exc_info=True)
            results["errors"].append(msg)

    return results


# ---------------------------------------------------------------------------
# compute_hourly_aggregates
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.tasks_aggregates.compute_hourly_aggregates",
    bind=True,
)
def compute_hourly_aggregates(self):
    """
    Compute 1-hour aggregates for all active clients.
    Scheduled every 3600 seconds via Celery Beat.

    Metrics computed:
    - events_per_hour
    - active_users_1h
    - top_events_1h
    """
    return asyncio.run(_compute_hourly_aggregates_async())


async def _compute_hourly_aggregates_async():
    now = datetime.now(timezone.utc)
    interval_end = now.replace(minute=0, second=0, microsecond=0)
    interval_start = interval_end - timedelta(hours=1)

    logger.info(f"Computing hourly aggregates: {interval_start} → {interval_end}")

    results = {
        "interval_start": interval_start.isoformat(),
        "interval_end": interval_end.isoformat(),
        "clients_processed": 0,
        "metrics_computed": 0,
        "errors": [],
    }

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(APIKey).where(APIKey.is_active == True)
            )
            api_keys = result.scalars().all()

            if not api_keys:
                logger.info("No active clients found — skipping hourly aggregates")
                return {**results, "message": "No active clients found"}

            service = MetricsService(db)

            for api_key in api_keys:
                client_id = str(api_key.id)
                try:
                    # 1. events_per_hour
                    events_data = await service.compute_events_per_minute(
                        client_id=client_id,
                        interval_start=interval_start,
                        interval_end=interval_end,
                    )
                    events_per_hour = events_data["rate"] * 60
                    await service.save_aggregate(
                        client_id=client_id,
                        metric_name="events_per_hour",
                        interval_start=interval_start,
                        interval_end=interval_end,
                        value=events_per_hour,
                        meta_data={"count": events_data["count"]},
                    )

                    # 2. active_users_1h
                    active_users = await service.compute_active_users(
                        client_id=client_id,
                        window_start=interval_start,
                        window_end=interval_end,
                    )
                    await service.save_aggregate(
                        client_id=client_id,
                        metric_name="active_users_1h",
                        interval_start=interval_start,
                        interval_end=interval_end,
                        value=float(active_users),
                        meta_data={},
                    )

                    # 3. top_events_1h
                    top_events = await service.compute_top_events(
                        client_id=client_id,
                        start_time=interval_start,
                        end_time=interval_end,
                        limit=10,
                    )
                    await service.save_aggregate(
                        client_id=client_id,
                        metric_name="top_events_1h",
                        interval_start=interval_start,
                        interval_end=interval_end,
                        value=float(len(top_events)),
                        meta_data={"events": top_events},
                    )

                    results["clients_processed"] += 1
                    results["metrics_computed"] += 3

                    logger.info(f"✅ Hourly metrics computed for {api_key.client_name}")

                except Exception as e:
                    msg = f"Error processing client {api_key.client_name}: {e}"
                    logger.error(msg, exc_info=True)
                    results["errors"].append(msg)

        except Exception as e:
            msg = f"Fatal error in hourly aggregates: {e}"
            logger.error(msg, exc_info=True)
            results["errors"].append(msg)

    return results


# ---------------------------------------------------------------------------
# cleanup_old_aggregates
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.tasks_aggregates.cleanup_old_aggregates",
    bind=True,
)
def cleanup_old_aggregates(self, days_to_keep: int = 30):
    """
    Delete aggregate rows older than `days_to_keep` days.
    Scheduled daily via Celery Beat.
    """
    return asyncio.run(_cleanup_old_aggregates_async(days_to_keep))


async def _cleanup_old_aggregates_async(days_to_keep: int):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    logger.info(f"Cleaning up aggregates older than {cutoff} ({days_to_keep}d retention)")

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                delete(Aggregate).where(Aggregate.interval_start < cutoff)
            )
            await db.commit()
            deleted = result.rowcount
            logger.info(f"✅ Deleted {deleted} old aggregate records")
            return {
                "status": "success",
                "deleted_count": deleted,
                "cutoff_date": cutoff.isoformat(),
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Cleanup failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}