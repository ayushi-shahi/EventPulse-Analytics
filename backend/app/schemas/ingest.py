# backend/app/schemas/ingest.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Dict, Any, List


class EventBase(BaseModel):
    """Base schema for event data"""
    event_name: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Name of the event (e.g., 'page_view', 'button_click')"
    )
    user_id: Optional[str] = Field(
        None, 
        max_length=255,
        description="Optional user identifier from your application"
    )
    properties: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional event properties as key-value pairs"
    )
    event_time: Optional[datetime] = Field(
        None,
        description="When the event occurred (defaults to server time if not provided)"
    )
    
    @field_validator('properties')
    @classmethod
    def validate_properties_size(cls, v):
        """Ensure properties JSON isn't too large"""
        if v is not None:
            # Rough check: limit to ~100KB of JSON
            import json
            if len(json.dumps(v)) > 100000:
                raise ValueError("Properties JSON too large (max 100KB)")
        return v


class EventCreate(EventBase):
    """Schema for creating a single event"""
    pass


class EventBatchCreate(BaseModel):
    """Schema for batch event ingestion"""
    events: List[EventCreate] = Field(
        ...,
        min_length=1,
        max_length=1000,  # Max 1000 events per batch
        description="Array of events to ingest"
    )


class EventResponse(BaseModel):
    """Schema for event in responses"""
    id: int
    client_id: str
    user_id: Optional[str]
    event_name: str
    properties: Optional[Dict[str, Any]]
    event_time: datetime
    received_at: datetime
    
    class Config:
        from_attributes = True


class IngestionResponse(BaseModel):
    """Response after successful ingestion"""
    success: bool
    message: str
    events_received: int
    request_id: Optional[str] = None


class IngestionError(BaseModel):
    """Error response for ingestion failures"""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None