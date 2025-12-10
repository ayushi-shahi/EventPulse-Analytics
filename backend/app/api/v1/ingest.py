# backend/app/api/v1/ingest.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.database import get_db
from app.models.api_key import APIKey
from app.api.deps import check_rate_limit
from app.schemas.ingest import (
    EventCreate,
    EventBatchCreate,
    IngestionResponse
)
from app.services.ingest_service import IngestionService
from app.config import settings
from app.core.rate_limiter import rate_limiter

router = APIRouter()

# Global Redis client for event storage (separate from rate limiter)
_event_redis_client: redis.Redis | None = None


async def get_event_redis() -> redis.Redis:
    """Dependency to get Redis client for event storage"""
    global _event_redis_client
    
    if _event_redis_client is None:
        _event_redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False  # Keep as bytes for JSON storage
        )
    
    return _event_redis_client


@router.post("/events", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    event: EventCreate,
    request: Request,
    api_key: APIKey = Depends(check_rate_limit),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_event_redis)
):
    """
    Ingest a single event.
    
    **Authentication**: Requires API key (X-API-Key header or Authorization: ApiKey <key>)
    
    **Rate Limiting**: Subject to your API key's rate limit
    
    **Request Body**:
    - **event_name**: Name of the event (e.g., "page_view", "button_click")
    - **user_id**: Optional user identifier from your application
    - **properties**: Optional JSON object with additional data
    - **event_time**: Optional timestamp (defaults to server time)
    
    **Response**: 202 Accepted (event queued for processing)
    
    **Example**:
```json
    {
      "event_name": "page_view",
      "user_id": "user_123",
      "properties": {
        "page": "/dashboard",
        "referrer": "https://google.com"
      }
    }
```
    """
    # Create service
    service = IngestionService(db, redis_client)
    
    try:
        # Enqueue event
        result = await service.enqueue_event(event, api_key)
        
        # Get queue stats
        queue_length = await service.get_queue_length()
        
        # Add rate limit headers to response
        if hasattr(request.state, 'rate_limit_info'):
            info = request.state.rate_limit_info
            return IngestionResponse(
                success=True,
                message=f"Event queued successfully. Queue length: {queue_length}",
                events_received=1,
                request_id=result.get("event_id")
            )
        
        return IngestionResponse(
            success=True,
            message=f"Event queued successfully. Queue length: {queue_length}",
            events_received=1,
            request_id=result.get("event_id")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue event: {str(e)}"
        )


@router.post("/events/batch", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_events_batch(
    batch: EventBatchCreate,
    request: Request,
    api_key: APIKey = Depends(check_rate_limit),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_event_redis)
):
    """
    Ingest multiple events in a single request (batch ingestion).
    
    **Limits**: 
    - Minimum 1 event
    - Maximum 1000 events per batch
    
    **Best Practice**: Batch events every 10-30 seconds for optimal performance
    
    **Request Body**:
```json
    {
      "events": [
        {
          "event_name": "page_view",
          "user_id": "user_123",
          "properties": {"page": "/home"}
        },
        {
          "event_name": "button_click",
          "user_id": "user_123",
          "properties": {"button_id": "cta_signup"}
        }
      ]
    }
```
    """
    # Validate batch size
    if len(batch.events) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size exceeds maximum of 1000 events"
        )
    
    # Create service
    service = IngestionService(db, redis_client)
    
    try:
        # Enqueue batch
        result = await service.enqueue_events_batch(batch.events, api_key)
        
        # Get queue stats
        queue_length = await service.get_queue_length()
        
        return IngestionResponse(
            success=True,
            message=f"Batch queued successfully. Queue length: {queue_length}",
            events_received=len(batch.events)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue batch: {str(e)}"
        )


@router.get("/status")
async def get_ingestion_status(
    api_key: APIKey = Depends(check_rate_limit),
    redis_client: redis.Redis = Depends(get_event_redis)
):
    """
    Get ingestion pipeline status.
    
    Shows:
    - Queue length (pending events)
    - Your API key info
    - Rate limit status
    """
    service = IngestionService(None, redis_client)
    queue_length = await service.get_queue_length()
    
    return {
        "status": "operational",
        "queue_length": queue_length,
        "api_key": {
            "client_name": api_key.client_name,
            "rate_limit": f"{api_key.rate_limit} requests/minute"
        }
    }


@router.get("/test-redis")
async def test_redis_connection(
    redis_client: redis.Redis = Depends(get_event_redis)
):
    """Test Redis connection and operations"""
    try:
        # Test basic operations
        await redis_client.set("test_key", "test_value")
        value = await redis_client.get("test_key")
        await redis_client.delete("test_key")
        
        # Test queue operations
        await redis_client.rpush("test_queue", "test_event")
        length = await redis_client.llen("test_queue")
        items = await redis_client.lrange("test_queue", 0, -1)
        await redis_client.delete("test_queue")
        
        return {
            "redis_connected": True,
            "test_value": value.decode() if value else None,
            "test_queue_length": length,
            "test_queue_items": [item.decode() for item in items] if items else []
        }
    except Exception as e:
        return {
            "redis_connected": False,
            "error": str(e),
            "error_type": type(e).__name__
        }