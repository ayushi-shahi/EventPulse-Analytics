"""
app/tasks/tasks_ingest.py

Event ingestion task — runs as an APScheduler async job every 5 seconds.
No Celery, no asyncio.run(), no sync Redis client needed.
"""
import logging
from typing import List

import redis.asyncio as aioredis

from app.services.event_processor import EventProcessor
from app.config import settings

logger = logging.getLogger(__name__)


async def _dequeue_events(batch_size: int) -> List[str]:
    client = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        async with client.pipeline() as pipe:
            for _ in range(batch_size):
                pipe.rpop("event_queue")
            results = await pipe.execute()
        return [r for r in results if r is not None]
    except Exception as e:
        logger.error(f"Redis dequeue error: {e}", exc_info=True)
        return []
    finally:
        await client.aclose()


async def _requeue_events(events: List[str]) -> None:
    if not events:
        return
    client = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        async with client.pipeline() as pipe:
            for event in reversed(events):
                pipe.lpush("event_queue", event)
            await pipe.execute()
    except Exception as e:
        logger.error(f"_requeue_events failed: {e}", exc_info=True)
    finally:
        await client.aclose()


async def process_event_batch(batch_size: int = 100):
    """Pull events from Redis and insert into PostgreSQL."""
    events = await _dequeue_events(batch_size)
    if not events:
        return

    logger.info(f"process_event_batch: processing {len(events)} events")
    processor = EventProcessor()
    try:
        await processor.process_events_batch(events, broadcast=True)
    except Exception as e:
        logger.error(f"process_event_batch failed: {e}", exc_info=True)
        await _requeue_events(events)
    finally:
        await processor.close()


async def consume_queue_continuously(batch_size: int = 100, max_batches: int = 10):
    """Drain multiple batches — used by admin endpoint for catch-up."""
    total = 0
    for i in range(max_batches):
        events = await _dequeue_events(batch_size)
        if not events:
            break
        processor = EventProcessor()
        try:
            result = await processor.process_events_batch(events, broadcast=True)
            total += result.get("processed", 0)
        except Exception as e:
            logger.error(f"consume_queue batch {i+1} failed: {e}", exc_info=True)
            await _requeue_events(events)
            break
        finally:
            await processor.close()
    return {"status": "completed", "total_processed": total}