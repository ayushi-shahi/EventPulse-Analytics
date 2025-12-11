# backend/app/tasks/tasks_aggregates.py
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List
from celery import Task
from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.models.api_key import APIKey
from app.services.metrics_service import MetricsService
from app.database import get_db


class AsyncTask(Task):
    """Custom Celery task that supports async functions"""
    def __call__(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run(*args, **kwargs))
    
    async def run(self, *args, **kwargs):
        raise NotImplementedError()


@celery_app.task(
    name="app.tasks.tasks_aggregates.compute_minute_aggregates",
    bind=True
)
def compute_minute_aggregates(self):
    """
    Compute 1-minute aggregates for all active clients.
    
    Scheduled to run every minute via Celery Beat.
    
    Computes:
    - events_per_minute
    - active_users_1m
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_compute_minute_aggregates_async())


async def _compute_minute_aggregates_async():
    """
    Async implementation of minute aggregates computation.
    """
    from app.database import engine, AsyncSessionLocal
    
    # Define the interval (previous complete minute)
    now = datetime.now(timezone.utc)
    interval_end = now.replace(second=0, microsecond=0)
    interval_start = interval_end - timedelta(minutes=1)
    
    print(f"Computing aggregates for interval: {interval_start} to {interval_end}")
    
    results = {
        "interval_start": interval_start.isoformat(),
        "interval_end": interval_end.isoformat(),
        "clients_processed": 0,
        "metrics_computed": 0,
        "errors": []
    }
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all active API keys (clients)
            result = await db.execute(
                select(APIKey).where(APIKey.is_active == True)
            )
            api_keys = result.scalars().all()
            
            if not api_keys:
                return {
                    **results,
                    "message": "No active clients found"
                }
            
            service = MetricsService(db)
            
            # Compute metrics for each client
            for api_key in api_keys:
                try:
                    client_id = str(api_key.id)
                    
                    # 1. Events per minute
                    events_data = await service.compute_events_per_minute(
                        client_id=client_id,
                        interval_start=interval_start,
                        interval_end=interval_end
                    )
                    
                    await service.save_aggregate(
                        client_id=client_id,
                        metric_name="events_per_minute",
                        interval_start=interval_start,
                        interval_end=interval_end,
                        value=events_data["rate"],
                        meta_data={"count": events_data["count"]}
                    )
                    
                    # 2. Active users in the minute
                    active_users = await service.compute_active_users(
                        client_id=client_id,
                        window_start=interval_start,
                        window_end=interval_end
                    )
                    
                    await service.save_aggregate(
                        client_id=client_id,
                        metric_name="active_users_1m",
                        interval_start=interval_start,
                        interval_end=interval_end,
                        value=float(active_users),
                        meta_data={}
                    )
                    
                    results["clients_processed"] += 1
                    results["metrics_computed"] += 2
                    
                    print(f"✅ Computed metrics for client {api_key.client_name}: "
                          f"{events_data['rate']} events/min, {active_users} active users")
                
                except Exception as e:
                    error_msg = f"Error processing client {api_key.client_name}: {str(e)}"
                    results["errors"].append(error_msg)
                    print(f"❌ {error_msg}")
            
            return results
        
        except Exception as e:
            results["errors"].append(f"Fatal error: {str(e)}")
            return results


@celery_app.task(
    name="app.tasks.tasks_aggregates.compute_hourly_aggregates",
    bind=True
)
def compute_hourly_aggregates(self):
    """
    Compute 1-hour aggregates for all active clients.
    
    Scheduled to run every hour via Celery Beat.
    
    Computes:
    - events_per_hour
    - active_users_1h
    - top_events_1h
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_compute_hourly_aggregates_async())


async def _compute_hourly_aggregates_async():
    """
    Async implementation of hourly aggregates computation.
    """
    from app.database import AsyncSessionLocal
    
    # Define the interval (previous complete hour)
    now = datetime.now(timezone.utc)
    interval_end = now.replace(minute=0, second=0, microsecond=0)
    interval_start = interval_end - timedelta(hours=1)
    
    print(f"Computing hourly aggregates for: {interval_start} to {interval_end}")
    
    results = {
        "interval_start": interval_start.isoformat(),
        "interval_end": interval_end.isoformat(),
        "clients_processed": 0,
        "metrics_computed": 0,
        "errors": []
    }
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all active API keys
            result = await db.execute(
                select(APIKey).where(APIKey.is_active == True)
            )
            api_keys = result.scalars().all()
            
            if not api_keys:
                return {
                    **results,
                    "message": "No active clients found"
                }
            
            service = MetricsService(db)
            
            # Compute metrics for each client
            for api_key in api_keys:
                try:
                    client_id = str(api_key.id)
                    
                    # 1. Events per hour
                    events_data = await service.compute_events_per_minute(
                        client_id=client_id,
                        interval_start=interval_start,
                        interval_end=interval_end
                    )
                    
                    # Convert to per-hour rate
                    events_per_hour = events_data["rate"] * 60
                    
                    await service.save_aggregate(
                        client_id=client_id,
                        metric_name="events_per_hour",
                        interval_start=interval_start,
                        interval_end=interval_end,
                        value=events_per_hour,
                        meta_data={"count": events_data["count"]}
                    )
                    
                    # 2. Active users in the hour
                    active_users = await service.compute_active_users(
                        client_id=client_id,
                        window_start=interval_start,
                        window_end=interval_end
                    )
                    
                    await service.save_aggregate(
                        client_id=client_id,
                        metric_name="active_users_1h",
                        interval_start=interval_start,
                        interval_end=interval_end,
                        value=float(active_users),
                        meta_data={}
                    )
                    
                    # 3. Top events in the hour
                    top_events = await service.compute_top_events(
                        client_id=client_id,
                        start_time=interval_start,
                        end_time=interval_end,
                        limit=10
                    )
                    
                    await service.save_aggregate(
                        client_id=client_id,
                        metric_name="top_events_1h",
                        interval_start=interval_start,
                        interval_end=interval_end,
                        value=float(len(top_events)),
                        meta_data={"events": top_events}
                    )
                    
                    results["clients_processed"] += 1
                    results["metrics_computed"] += 3
                    
                    print(f"✅ Computed hourly metrics for {api_key.client_name}")
                
                except Exception as e:
                    error_msg = f"Error processing client {api_key.client_name}: {str(e)}"
                    results["errors"].append(error_msg)
                    print(f"❌ {error_msg}")
            
            return results
        
        except Exception as e:
            results["errors"].append(f"Fatal error: {str(e)}")
            return results


@celery_app.task(
    name="app.tasks.tasks_aggregates.cleanup_old_aggregates",
    bind=True
)
def cleanup_old_aggregates(self, days_to_keep: int = 30):
    """
    Clean up old aggregate data.
    
    Deletes aggregates older than specified days.
    Scheduled to run daily.
    
    Args:
        days_to_keep: Number of days to retain (default: 30)
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_cleanup_old_aggregates_async(days_to_keep))


async def _cleanup_old_aggregates_async(days_to_keep: int):
    """
    Async implementation of aggregate cleanup.
    """
    from app.database import AsyncSessionLocal
    from app.models.aggregate import Aggregate
    from sqlalchemy import delete
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    
    print(f"Cleaning up aggregates older than {cutoff_date}")
    
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                delete(Aggregate)
                .where(Aggregate.interval_start < cutoff_date)
            )
            
            await db.commit()
            
            deleted_count = result.rowcount
            
            print(f"✅ Deleted {deleted_count} old aggregate records")
            
            return {
                "status": "success",
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }
        
        except Exception as e:
            await db.rollback()
            return {
                "status": "error",
                "error": str(e)
            }