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

Two changes keep the steady-state cost flat:
  * `RPOP key COUNT n` pops the whole batch in a single command.
  * When the queue keeps coming back empty the job backs off (see
    `_SKIP_TICKS`) so an idle deployment polls once every 30s, not 5s.
A batch that returns events resets the backoff, so live traffic is still
drained at the full 5s cadence.
"""
import logging
from typing import List, Optional

import redis.asyncio as aioredis

from app.services.event_processor import EventProcessor
from app.config import settings

logger = logging.getLogger(__name__)

# Idle backoff, indexed by how many consecutive polls came back empty.
# Values are how many 5s ticks to skip before touching Redis again:
# 5s while busy, degrading to one poll per 30s when nothing is arriving.
_SKIP_TICKS = (0, 0, 0, 1, 2, 5)

_idle_streak = 0
_ticks_to_skip = 0

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
    global _idle_streak, _ticks_to_skip

    if _ticks_to_skip > 0:
        _ticks_to_skip -= 1
        return

    events = await _dequeue_events(batch_size)
    if not events:
        _idle_streak = min(_idle_streak + 1, len(_SKIP_TICKS) - 1)
        _ticks_to_skip = _SKIP_TICKS[_idle_streak]
        return

    _idle_streak = 0
    _ticks_to_skip = 0

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
