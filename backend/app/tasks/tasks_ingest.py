# backend/app/tasks/tasks_ingest.py
import asyncio
import redis
from typing import List
from celery import Task

from app.tasks.celery_app import celery_app
from app.services.event_processor import EventProcessor
from app.config import settings


class AsyncTask(Task):
    """
    Custom Celery task that supports async functions.
    """
    def __call__(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run(*args, **kwargs))
    
    async def run(self, *args, **kwargs):
        raise NotImplementedError()


@celery_app.task(
    name="app.tasks.tasks_ingest.process_event_batch",
    bind=True,
    max_retries=3,
    default_retry_delay=60  # Retry after 60 seconds
)
def process_event_batch(self, batch_size: int = 100):
    """
    Celery task to process events from Redis queue.
    
    Args:
        batch_size: Number of events to process in one batch
        
    This task:
    1. Pulls events from Redis queue
    2. Batches them together
    3. Writes to PostgreSQL
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_process_event_batch_async(batch_size))


async def _process_event_batch_async(batch_size: int = 100):
    """
    Async implementation of event batch processing.
    """
    # Connect to Redis
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
    
    try:
        # Pull batch from queue (non-blocking)
        events = []
        for _ in range(batch_size):
            # LPOP removes and returns first element
            event_json = redis_client.rpop("event_queue")
            if event_json is None:
                break  # Queue is empty
            events.append(event_json)
        
        if not events:
            return {
                "status": "no_events",
                "processed": 0
            }
        
        # Process the batch
        processor = EventProcessor()
        result = await processor.process_events_batch(events)
        await processor.close()
        
        return {
            "status": "success",
            "processed": result["processed"],
            "failed": result["failed"],
            "errors": result["errors"],
            "batch_size": len(events)
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
    
    finally:
        redis_client.close()


@celery_app.task(
    name="app.tasks.tasks_ingest.consume_queue_continuously",
    bind=True
)
def consume_queue_continuously(self, batch_size: int = 100, max_batches: int = 10):
    """
    Continuously consume events from queue until empty or max_batches reached.
    
    This is useful for catching up when queue gets backed up.
    
    Args:
        batch_size: Events per batch
        max_batches: Maximum number of batches to process
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        _consume_queue_continuously_async(batch_size, max_batches)
    )


async def _consume_queue_continuously_async(
    batch_size: int = 100,
    max_batches: int = 10
):
    """
    Async implementation of continuous queue consumption.
    """
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
    
    processor = EventProcessor()
    
    total_processed = 0
    batches_processed = 0
    
    try:
        for _ in range(max_batches):
            # Check queue length
            queue_length = redis_client.llen("event_queue")
            if queue_length == 0:
                break
            
            # Pull batch
            events = []
            for _ in range(min(batch_size, queue_length)):
                event_json = redis_client.lpop("event_queue")
                if event_json:
                    events.append(event_json)
            
            if not events:
                break
            
            # Process batch
            result = await processor.process_events_batch(events)
            total_processed += result["processed"]
            batches_processed += 1
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        await processor.close()
        
        return {
            "status": "completed",
            "total_processed": total_processed,
            "batches_processed": batches_processed
        }
    
    except Exception as e:
        await processor.close()
        return {
            "status": "error",
            "error": str(e),
            "processed_before_error": total_processed
        }
    
    finally:
        redis_client.close()