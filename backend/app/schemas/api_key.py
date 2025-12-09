# backend/app/schemas/api_key.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class APIKeyCreate(BaseModel):
    """Schema for creating a new API key"""
    client_name: str = Field(..., min_length=1, max_length=255)
    rate_limit: Optional[int] = Field(default=1000, ge=1, le=100000)


class APIKeyResponse(BaseModel):
    """Schema for API key in responses (without the actual key!)"""
    id: str
    client_name: str
    rate_limit: int
    is_active: bool
    created_at: datetime
    user_id: Optional[str]
    
    class Config:
        from_attributes = True


class APIKeyWithSecret(BaseModel):
    """
    Schema for API key response with the plain key.
    ONLY returned once during creation!
    """
    id: str
    client_name: str
    rate_limit: int
    is_active: bool
    created_at: datetime
    api_key: str  # Plain text key - shown ONCE
    
    class Config:
        from_attributes = True


class APIKeyStats(BaseModel):
    """Schema for API key usage statistics"""
    id: str
    client_name: str
    rate_limit: int
    requests_today: int = 0  # Will implement in rate limiter
    last_used: Optional[datetime] = None