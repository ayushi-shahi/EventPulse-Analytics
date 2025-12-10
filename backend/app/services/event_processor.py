# backend/app/services/event_processor.py
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import insert
import json

from app.models.event import Event
from app.config import settings


class EventProcessor:
    """
    Service for processing events from the queue.
    Handles batch insertion into the database.
    """
    
    def __init__(self):
        # Create a separate async engine for the worker
        # Workers run in different processes, so they need their own connections
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
    
    async def process_events_batch(self, events_json: List[str]) -> Dict[str, Any]:
        """
        Process a batch of events from the queue.
        
        Args:
            events_json: List of JSON strings from Redis queue
            
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
                # Prepare event objects for bulk insert
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
                
                # Bulk insert using SQLAlchemy Core (faster than ORM)
                stmt = insert(Event).values(event_records)
                await session.execute(stmt)
                await session.commit()
                
                processed = len(event_records)
                
            except Exception as e:
                await session.rollback()
                failed = len(parsed_events)
                errors.append(f"Database error: {str(e)}")
        
        return {
            "processed": processed,
            "failed": failed,
            "errors": errors
        }
    
    async def close(self):
        """Close database connections"""
        await self.engine.dispose()