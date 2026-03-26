# backend/app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User
from app.core.auth import get_current_active_admin
from app.tasks.tasks_ingest import process_event_batch, consume_queue_continuously
from app.tasks.tasks_aggregates import (
    compute_minute_aggregates,
    compute_hourly_aggregates,
    cleanup_old_aggregates,
)

router = APIRouter()


@router.post("/trigger-event-processing")
async def trigger_event_processing(
    batch_size: int = 100,
    current_user: User = Depends(get_current_active_admin),
):
    await process_event_batch(batch_size)
    return {"message": "Event processing complete", "batch_size": batch_size}


@router.post("/process-queue")
async def process_entire_queue(
    batch_size: int = 100,
    max_batches: int = 10,
    current_user: User = Depends(get_current_active_admin),
):
    result = await consume_queue_continuously(batch_size, max_batches)
    return {"message": "Queue processing complete", **result}


@router.post("/compute-aggregates")
async def trigger_aggregate_computation(
    interval: str = "minute",
    current_user: User = Depends(get_current_active_admin),
):
    if interval == "minute":
        await compute_minute_aggregates()
        message = "Minute aggregates computed"
    elif interval == "hourly":
        await compute_hourly_aggregates()
        message = "Hourly aggregates computed"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use 'minute' or 'hourly'")
    return {"message": message, "interval": interval}


@router.post("/cleanup-aggregates")
async def trigger_cleanup(
    days_to_keep: int = 30,
    current_user: User = Depends(get_current_active_admin),
):
    await cleanup_old_aggregates(days_to_keep)
    return {"message": f"Cleanup complete (kept last {days_to_keep} days)", "days_to_keep": days_to_keep}