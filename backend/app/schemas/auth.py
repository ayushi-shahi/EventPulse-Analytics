# backend/app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    role: Optional[str] = "user"  # Default to 'user', admin can set 'admin'


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user data in responses (no password!)"""
    id: str
    email: str
    is_active: bool
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True  # Allows creating from SQLAlchemy models


class TokenResponse(BaseModel):
    """Schema for token response after login"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)