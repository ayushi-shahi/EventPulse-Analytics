# backend/app/tasks/tasks_ingest.py
"""
Event ingestion Celery tasks.

Architecture:
- Celery tasks are SYNCHRONOUS by nature
- Redis dequeuing is done with the SYNC redis client (correct for Celery)
- Database writes are ASYNC (via EventProcessor) and are run with asyncio.run()
- There is no mixing of sync Redis inside async functions
"""
import asyncio
import json
import logging
from typing import List

import redis  # sync redis — correct for Celery context

from app.tasks.celery_app import celery_app
from app.services.event_processor import EventProcessor
from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dequeue_events(batch_size: int) -> List[str]:
    """
    Pull up to `batch_size` events from Redis queue using the SYNC client.

    This runs inside a Celery worker (sync context), so using the sync
    redis client is correct — no event loop involved here.

    Returns a list of raw JSON strings.
    """
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    events: List[str] = []
    try:
        # Use a pipeline for efficiency — single round-trip
        with redis_client.pipeline() as pipe:
            for _ in range(batch_size):
                pipe.rpop("event_queue")
            results = pipe.execute()

        # Filter out None values (queue had fewer items than batch_size)
        events = [r for r in results if r is not None]

    except Exception as e:
        logger.error(f"Redis dequeue error: {e}", exc_info=True)
    finally:
        redis_client.close()

    return events


async def _insert_events_async(events: List[str]) -> dict:
    """
    Insert a list of raw JSON event strings into the database.

    This is the ONLY async part of the pipeline. It runs inside
    asyncio.run() so it gets its own clean event loop — no sharing
    with any other coroutine.
    """
    processor = EventProcessor()
    try:
        result = await processor.process_events_batch(events, broadcast=True)
        return result
    finally:
        await processor.close()


# ---------------------------------------------------------------------------
# Celery Tasks
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.tasks_ingest.process_event_batch",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_event_batch(self, batch_size: int = 100):
    """
    Pull events from Redis queue and write them to PostgreSQL.

    Flow:
        1. Sync Redis RPOP  →  list of JSON strings   (sync, correct)
        2. asyncio.run()    →  async DB bulk insert    (async, isolated)

    No async/sync mixing occurs.
    """
    # Step 1 — dequeue (pure sync, uses sync Redis client)
    events = _dequeue_events(batch_size)

    if not events:
        logger.debug("process_event_batch: queue is empty, nothing to do")
        return {"status": "no_events", "processed": 0}

    logger.info(f"process_event_batch: dequeued {len(events)} events")

    # Step 2 — insert (pure async, isolated in its own event loop)
    try:
        result = asyncio.run(_insert_events_async(events))
    except Exception as exc:
        logger.error(f"process_event_batch: DB insert failed: {exc}", exc_info=True)
        # Retry the task; events are already off the queue so we re-push them
        # back before retrying so they aren't lost.
        _requeue_events(events)
        raise self.retry(exc=exc)

    return {
        "status": "success",
        "processed": result.get("processed", 0),
        "failed": result.get("failed", 0),
        "errors": result.get("errors", []),
        "batch_size": len(events),
    }


@celery_app.task(
    name="app.tasks.tasks_ingest.consume_queue_continuously",
    bind=True,
)
def consume_queue_continuously(self, batch_size: int = 100, max_batches: int = 10):
    """
    Drain the event queue in multiple sequential batches.

    Useful for catch-up after a backlog builds up.
    Each batch is a separate sync→async cycle with its own event loop,
    so there is no shared state between batches.
    """
    total_processed = 0
    batches_processed = 0

    # Check queue length once with sync client
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        queue_length = redis_client.llen("event_queue")
    finally:
        redis_client.close()

    logger.info(
        f"consume_queue_continuously: queue has {queue_length} events, "
        f"will process up to {max_batches} batches of {batch_size}"
    )

    for batch_num in range(max_batches):
        # Step 1 — dequeue
        events = _dequeue_events(batch_size)
        if not events:
            logger.info(f"consume_queue_continuously: queue empty after {batch_num} batches")
            break

        # Step 2 — insert
        try:
            result = asyncio.run(_insert_events_async(events))
            total_processed += result.get("processed", 0)
            batches_processed += 1
            logger.info(
                f"consume_queue_continuously: batch {batch_num + 1} done — "
                f"{result.get('processed')} inserted"
            )
        except Exception as exc:
            logger.error(
                f"consume_queue_continuously: batch {batch_num + 1} failed: {exc}",
                exc_info=True,
            )
            _requeue_events(events)
            break

    return {
        "status": "completed",
        "total_processed": total_processed,
        "batches_processed": batches_processed,
    }


# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------

def _requeue_events(events: List[str]) -> None:
    """
    Push events back onto the queue head so they aren't lost on task failure.
    Uses LPUSH so they'll be processed next (LIFO for failed batches).
    """
    if not events:
        return

    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        with redis_client.pipeline() as pipe:
            for event in reversed(events):   # reversed so order is preserved
                pipe.lpush("event_queue", event)
            pipe.execute()
        logger.info(f"_requeue_events: re-queued {len(events)} events")
    except Exception as e:
        logger.error(f"_requeue_events: failed to re-queue events: {e}", exc_info=True)
    finally:
        redis_client.close()