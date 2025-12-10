# backend/app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User
from app.core.auth import get_current_active_admin
from app.tasks.tasks_ingest import process_event_batch, consume_queue_continuously

router = APIRouter()


@router.post("/trigger-event-processing")
async def trigger_event_processing(
    batch_size: int = 100,
    current_user: User = Depends(get_current_active_admin)
):
    """
    Manually trigger event processing from queue (Admin only).
    
    Useful for:
    - Testing the worker
    - Processing backed-up queue
    - Manual intervention
    
    Args:
        batch_size: Number of events to process
    """
    # Trigger Celery task asynchronously
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
    
    Useful for catching up when queue is backed up.
    """
    task = consume_queue_continuously.delay(batch_size, max_batches)
    
    return {
        "message": "Queue processing task triggered",
        "task_id": task.id,
        "batch_size": batch_size,
        "max_batches": max_batches
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
        "result": task_result.result if task_result.ready() else None
    }