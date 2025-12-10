# backend/app/services/event_processor.py (update)
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import insert
import json
import redis.asyncio as redis

from app.models.event import Event
from app.config import settings


class EventProcessor:
    """
    Service for processing events from the queue.
    Handles batch insertion into the database and broadcasting.
    """
    
    def __init__(self):
        # Database engine
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO,
            pool_size=5,
            max_overflow=10
        )
        
        self.AsyncSessionLocal = sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession
        )
        
        # Redis for broadcasting
        self.redis_client = None
    
    async def _get_redis(self):
        """Get or create Redis client"""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
    
    async def process_events_batch(
        self, 
        events_json: List[str],
        broadcast: bool = True
    ) -> Dict[str, Any]:
        """
        Process a batch of events from the queue.
        
        Args:
            events_json: List of JSON strings from Redis queue
            broadcast: Whether to broadcast events to WebSocket clients
            
        Returns:
            Dict with processing statistics
        """
        if not events_json:
            return {
                "processed": 0,
                "failed": 0,
                "errors": []
            }
        
        processed = 0
        failed = 0
        errors = []
        
        # Parse JSON events
        parsed_events = []
        for event_str in events_json:
            try:
                event_data = json.loads(event_str)
                parsed_events.append(event_data)
            except json.JSONDecodeError as e:
                failed += 1
                errors.append(f"JSON decode error: {str(e)}")
        
        if not parsed_events:
            return {
                "processed": 0,
                "failed": failed,
                "errors": errors
            }
        
        # Batch insert into database
        async with self.AsyncSessionLocal() as session:
            try:
                # Prepare event records for bulk insert
                event_records = []
                for event_data in parsed_events:
                    # Parse ISO timestamp strings back to datetime
                    event_time = datetime.fromisoformat(
                        event_data["event_time"].replace("Z", "+00:00")
                    )
                    received_at = datetime.fromisoformat(
                        event_data["received_at"].replace("Z", "+00:00")
                    )
                    
                    event_records.append({
                        "client_id": event_data["client_id"],
                        "user_id": event_data.get("user_id"),
                        "event_name": event_data["event_name"],
                        "properties": event_data.get("properties"),
                        "event_time": event_time,
                        "received_at": received_at
                    })
                
                # Bulk insert using SQLAlchemy Core
                stmt = insert(Event).values(event_records)
                await session.execute(stmt)
                await session.commit()
                
                processed = len(event_records)
                
                # Broadcast events to WebSocket clients (if enabled)
                if broadcast and processed > 0:
                    await self._broadcast_events(parsed_events)
                
            except Exception as e:
                await session.rollback()
                failed = len(parsed_events)
                errors.append(f"Database error: {str(e)}")
        
        return {
            "processed": processed,
            "failed": failed,
            "errors": errors
        }
    
    async def _broadcast_events(self, events: List[dict]):
        """
        Broadcast processed events to WebSocket clients via Redis Pub/Sub.
        
        Args:
            events: List of event data dicts
        """
        try:
            redis_client = await self._get_redis()
            
            # Group events by client_id for efficient broadcasting
            events_by_client = {}
            for event in events:
                client_id = event["client_id"]
                if client_id not in events_by_client:
                    events_by_client[client_id] = []
                events_by_client[client_id].append(event)
            
            # Publish to Redis channels
            for client_id, client_events in events_by_client.items():
                channel = f"events:{client_id}"
                
                # Send each event separately (or batch if you prefer)
                for event in client_events:
                    message = json.dumps({
                        "client_id": client_id,
                        "event": event
                    })
                    await redis_client.publish(channel, message)
        
        except Exception as e:
            print(f"Error broadcasting events: {e}")
    
    async def close(self):
        """Close database and Redis connections"""
        await self.engine.dispose()
        if self.redis_client:
            await self.redis_client.close()