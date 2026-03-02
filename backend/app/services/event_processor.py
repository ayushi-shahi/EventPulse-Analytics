# backend/app/services/event_processor.py
"""
Event processor service.

Responsible for bulk-inserting events from the Redis queue into PostgreSQL
and broadcasting them to WebSocket clients via Redis Pub/Sub.

Design:
- Uses AsyncSessionLocal from app.database (the single session factory)
- No local engine or sessionmaker — avoids duplicate connection pools
- Broadcasting is best-effort: a failure there never blocks DB writes
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import redis.asyncio as aioredis
from sqlalchemy import insert

from app.database import AsyncSessionLocal
from app.models.event import Event
from app.config import settings

logger = logging.getLogger(__name__)


class EventProcessor:
    """
    Bulk-insert events into PostgreSQL and optionally broadcast them
    to connected WebSocket clients via Redis Pub/Sub.

    Lifecycle
    ---------
    Create one instance per task invocation, call process_events_batch(),
    then call close() to release the Redis connection.
    The DB session is managed internally per-call (no shared session state).
    """

    def __init__(self):
        self._redis: aioredis.Redis | None = None

    # ------------------------------------------------------------------
    # Redis connection (lazy, async)
    # ------------------------------------------------------------------

    async def _get_redis(self) -> aioredis.Redis:
        """Return a cached async Redis client, creating it on first call."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def close(self):
        """Release the Redis connection. Call after process_events_batch()."""
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self._redis = None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def process_events_batch(
        self,
        events_json: List[str],
        broadcast: bool = True,
    ) -> Dict[str, Any]:
        """
        Parse, validate, bulk-insert, and optionally broadcast a batch of events.

        Args:
            events_json: Raw JSON strings pulled from the Redis queue.
            broadcast:   If True, publish each event to Redis Pub/Sub so
                         WebSocket clients receive live updates.

        Returns:
            Dict with keys: processed, failed, errors
        """
        if not events_json:
            return {"processed": 0, "failed": 0, "errors": []}

        # --- Parse JSON ---
        parsed: List[Dict[str, Any]] = []
        failed = 0
        errors: List[str] = []

        for raw in events_json:
            try:
                parsed.append(json.loads(raw))
            except json.JSONDecodeError as e:
                failed += 1
                errors.append(f"JSON decode error: {e}")
                logger.warning(f"Skipping malformed event JSON: {e}")

        if not parsed:
            return {"processed": 0, "failed": failed, "errors": errors}

        # --- Build DB records ---
        records: List[Dict[str, Any]] = []
        for event in parsed:
            try:
                records.append({
                    "client_id": event["client_id"],
                    "user_id": event.get("user_id"),
                    "event_name": event["event_name"],
                    "properties": event.get("properties"),
                    "event_time": _parse_dt(event["event_time"]),
                    "received_at": _parse_dt(event["received_at"]),
                })
            except (KeyError, ValueError) as e:
                failed += 1
                errors.append(f"Invalid event structure: {e}")
                logger.warning(f"Skipping invalid event: {e}")

        if not records:
            return {"processed": 0, "failed": failed, "errors": errors}

        # --- Bulk insert ---
        processed = 0
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(insert(Event).values(records))
                await session.commit()
                processed = len(records)
                logger.info(f"Inserted {processed} events into DB")
            except Exception as e:
                await session.rollback()
                failed += len(records)
                errors.append(f"DB insert error: {e}")
                logger.error(f"Bulk insert failed: {e}", exc_info=True)
                # Return early — nothing to broadcast if insert failed
                return {"processed": 0, "failed": failed, "errors": errors}

        # --- Broadcast (best-effort, never raises) ---
        if broadcast and processed > 0:
            await self._broadcast_events(parsed)

        return {"processed": processed, "failed": failed, "errors": errors}

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def _broadcast_events(self, events: List[Dict[str, Any]]) -> None:
        """
        Publish processed events to Redis Pub/Sub channels so the
        WebSocketBroadcaster can forward them to connected clients.

        Failures here are logged but never propagate — broadcasting is
        best-effort and must not affect DB write success.
        """
        try:
            redis_client = await self._get_redis()

            # Group by client so we publish one message per client per event
            by_client: Dict[str, List[Dict[str, Any]]] = {}
            for event in events:
                cid = event["client_id"]
                by_client.setdefault(cid, []).append(event)

            # Use a pipeline for efficiency
            async with redis_client.pipeline(transaction=False) as pipe:
                for client_id, client_events in by_client.items():
                    channel = f"events:{client_id}"
                    for event in client_events:
                        pipe.publish(
                            channel,
                            json.dumps({"client_id": client_id, "event": event}),
                        )
                await pipe.execute()

        except Exception as e:
            logger.error(f"Broadcasting failed (non-fatal): {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_dt(value: str) -> datetime:
    """Parse an ISO-8601 datetime string, handling the trailing Z."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))