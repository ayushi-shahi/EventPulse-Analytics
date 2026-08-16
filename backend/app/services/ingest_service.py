# backend/app/services/ingest_service.py
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.event import Event
from app.models.api_key import APIKey
from app.schemas.ingest import EventCreate


class IngestionService:
    """
    Service for handling event ingestion.
    
    Responsibilities:
    - Validate events
    - Enqueue to Redis for background processing
    - (Later) Directly write small batches
    """
    
    def __init__(self, db: AsyncSession, redis_client: Redis):
        self.db = db
        self.redis = redis_client
    
    async def enqueue_event(
        self,
        event_data: EventCreate,
        api_key: APIKey
    ) -> dict:
        """
        Enqueue a single event to Redis for background processing.
        
        Args:
            event_data: Event data from request
            api_key: Authenticated API key
            
        Returns:
            Dict with status information
        """
        # Set event_time to now if not provided
        if event_data.event_time is None:
            event_data.event_time = datetime.now(timezone.utc)
        
        # Create event payload
        event_payload = {
            "id": str(uuid.uuid4()),  # Temporary ID for tracking
            "client_id": str(api_key.id),
            "user_id": event_data.user_id,
            "event_name": event_data.event_name,
            "properties": event_data.properties,
            "event_time": event_data.event_time.isoformat(),
            "received_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Push to Redis list (acts as a queue)
        # We'll use Redis Lists for simplicity (FIFO queue)
        await self.redis.rpush(
            "event_queue",
            json.dumps(event_payload, default=str)
        )
        
        return {
            "success": True,
            "queued": True,
            "event_id": event_payload["id"]
        }
    
    async def enqueue_events_batch(
        self,
        events: List[EventCreate],
        api_key: APIKey
    ) -> dict:
        """
        Enqueue multiple events in a batch.
        
        Args:
            events: List of event data
            api_key: Authenticated API key
            
        Returns:
            Dict with batch status
        """
        event_ids = []

        # Build the whole batch, then push it with a single variadic RPUSH.
        # A pipeline would still be billed one command per queued RPUSH on
        # managed Redis, so a 50-event batch cost 50 commands instead of 1.
        payloads = []

        for event_data in events:
            # Set event_time to now if not provided
            if event_data.event_time is None:
                event_data.event_time = datetime.now(timezone.utc)
            
            # Create event payload
            event_id = str(uuid.uuid4())
            event_payload = {
                "id": event_id,
                "client_id": str(api_key.id),
                "user_id": event_data.user_id,
                "event_name": event_data.event_name,
                "properties": event_data.properties,
                "event_time": event_data.event_time.isoformat(),
                "received_at": datetime.now(timezone.utc).isoformat()
            }
            
            payloads.append(json.dumps(event_payload, default=str))
            event_ids.append(event_id)

        # One command for the whole batch
        if payloads:
            await self.redis.rpush("event_queue", *payloads)

        return {
            "success": True,
            "queued": len(events),
            "event_ids": event_ids
        }
    
    async def get_queue_length(self) -> int:
        """Get current queue length (for monitoring)"""
        return await self.redis.llen("event_queue")