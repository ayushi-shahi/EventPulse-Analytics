# backend/app/api/v1/admin.py (update)
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User
from app.core.auth import get_current_active_admin
from app.tasks.tasks_ingest import process_event_batch, consume_queue_continuously
from app.tasks.tasks_aggregates import (
    compute_minute_aggregates,
    compute_hourly_aggregates,
    cleanup_old_aggregates
)

router = APIRouter()


@router.post("/trigger-event-processing")
async def trigger_event_processing(
    batch_size: int = 100,
    current_user: User = Depends(get_current_active_admin)
):
    """
    Manually trigger event processing from queue (Admin only).
    """
    task = process_event_batch.delay(batch_size)
    
    return {
        "message": "Event processing task triggered",
        "task_id": task.id,
        "batch_size": batch_size
    }


@router.post("/process-queue")
async def process_entire_queue(
    batch_size: int = 100,
    max_batches: int = 10,
    current_user: User = Depends(get_current_active_admin)
):
    """
    Process multiple batches from queue (Admin only).
    """
    task = consume_queue_continuously.delay(batch_size, max_batches)
    
    return {
        "message": "Queue processing task triggered",
        "task_id": task.id,
        "batch_size": batch_size,
        "max_batches": max_batches
    }


@router.post("/compute-aggregates")
async def trigger_aggregate_computation(
    interval: str = "minute",  # "minute" or "hourly"
    current_user: User = Depends(get_current_active_admin)
):
    """
    Manually trigger aggregate computation (Admin only).
    
    Args:
        interval: "minute" or "hourly"
    """
    if interval == "minute":
        task = compute_minute_aggregates.delay()
        message = "Minute aggregates computation triggered"
    elif interval == "hourly":
        task = compute_hourly_aggregates.delay()
        message = "Hourly aggregates computation triggered"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid interval. Use 'minute' or 'hourly'"
        )
    
    return {
        "message": message,
        "task_id": task.id,
        "interval": interval
    }


@router.post("/cleanup-aggregates")
async def trigger_cleanup(
    days_to_keep: int = 30,
    current_user: User = Depends(get_current_active_admin)
):
    """
    Manually trigger cleanup of old aggregates (Admin only).
    
    Args:
        days_to_keep: Number of days to retain (default: 30)
    """
    task = cleanup_old_aggregates.delay(days_to_keep)
    
    return {
        "message": f"Cleanup triggered (keeping last {days_to_keep} days)",
        "task_id": task.id,
        "days_to_keep": days_to_keep
    }


@router.get("/task-status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_admin)
):
    """
    Check status of a Celery task (Admin only).
    """
    from celery.result import AsyncResult
    from app.tasks.celery_app import celery_app
    
    task_result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": task_result.state,
        "result": task_result.result if task_result.ready() else None,
        "info": task_result.info
    }