"""
app/tasks/tasks_ingest.py

Event ingestion task — runs as an APScheduler async job every 5 seconds.
No Celery, no asyncio.run(), no sync Redis client needed.

Redis command budget
--------------------
Managed Redis is billed per command, and a pipeline costs one command per
queued call — not one for the pipeline. An earlier version pipelined
`batch_size` RPOPs on every tick, so an *idle* queue still cost 100 commands
every 5s (~1.7M/day) and exhausted a 500K/month plan in hours.

Polling an empty queue is pure waste, so this job mostly does not poll at all.
APScheduler runs inside the FastAPI process, so the ingest endpoint that writes
to the queue can just say so: `notify_pending()` sets an in-process flag and the
next 5s tick drains the queue immediately. No flag, no Redis call.

`IDLE_POLL_SECONDS` is only a safety net, for events queued by something other
than this process (a second instance, or a manual push). At the default of five
minutes the idle cost is **12 commands/hour**, and a locally ingested event is
still picked up within one 5s tick — faster than the old unconditional poll.

  idle commands/hour = 3600 / IDLE_POLL_SECONDS
"""
import logging
from time import monotonic
from typing import List, Optional

import redis.asyncio as aioredis

from app.services.event_processor import EventProcessor
from app.config import settings

logger = logging.getLogger(__name__)

# Safety-net poll interval for work this process was never told about.
IDLE_POLL_SECONDS = 300

# Set by notify_pending() when this process queues an event.
_pending = False
_last_poll = 0.0


def notify_pending() -> None:
    """
    Tell the poller there is work, so it drains on the next tick instead of
    waiting for the safety-net interval. Called after a successful enqueue.
    """
    global _pending
    _pending = True

# One shared connection, reused across invocations. Reconnecting every 5s
# meant a fresh TLS handshake and AUTH each time, for no benefit.
_client: Optional[aioredis.Redis] = None


def _get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
    return _client


async def _drop_client() -> None:
    """Discard the shared client so the next call reconnects cleanly."""
    global _client
    client, _client = _client, None
    if client is not None:
        try:
            await client.aclose()
        except Exception:
            pass


async def _dequeue_events(batch_size: int) -> List[str]:
    try:
        # Single RPOP ... COUNT — one command regardless of batch_size.
        events = await _get_client().rpop("event_queue", batch_size)
    except Exception as e:
        logger.error(f"Redis dequeue error: {e}", exc_info=True)
        await _drop_client()
        return []
    if not events:
        return []
    # rpop() returns a bare string when it pops exactly one element.
    return events if isinstance(events, list) else [events]


async def _requeue_events(events: List[str]) -> None:
    if not events:
        return
    try:
        # Variadic LPUSH — also a single command.
        await _get_client().lpush("event_queue", *reversed(events))
    except Exception as e:
        logger.error(f"_requeue_events failed: {e}", exc_info=True)
        await _drop_client()


async def process_event_batch(batch_size: int = 100):
    """Pull events from Redis and insert into PostgreSQL."""
    global _pending, _last_poll

    now = monotonic()
    if not _pending and (now - _last_poll) < IDLE_POLL_SECONDS:
        return

    # Clear before dequeuing: an enqueue racing with this call must re-arm the
    # flag rather than be swallowed by us clearing it afterwards.
    _pending = False
    _last_poll = now

    events = await _dequeue_events(batch_size)
    if not events:
        return

    # A full batch probably means more is waiting — come back next tick.
    if len(events) >= batch_size:
        _pending = True

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
