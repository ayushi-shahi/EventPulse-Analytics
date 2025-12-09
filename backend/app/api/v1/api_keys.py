# backend/app/api/v1/api_keys.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.api_key import APIKey
from app.schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyWithSecret,
    APIKeyStats
)
from app.core.auth import get_current_user
from app.core.security import generate_api_key, hash_api_key

router = APIRouter()


@router.post("/", response_model=APIKeyWithSecret, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key.
    
    ⚠️ **IMPORTANT**: The plain API key is only shown ONCE.
    Save it immediately - you won't be able to see it again!
    
    - **client_name**: Friendly name for this key (e.g., "Mobile App", "Website")
    - **rate_limit**: Max requests per minute (default: 1000)
    """
    # Generate plain API key
    plain_key = generate_api_key()
    
    # Hash it for storage
    key_hash = hash_api_key(plain_key)
    
    # Create API key record
    new_key = APIKey(
        client_name=key_data.client_name,
        key_hash=key_hash,
        rate_limit=key_data.rate_limit,
        user_id=current_user.id
    )
    
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    
    # Return with plain key (ONLY TIME IT'S SHOWN!)
    return APIKeyWithSecret(
        id=str(new_key.id),
        client_name=new_key.client_name,
        rate_limit=new_key.rate_limit,
        is_active=new_key.is_active,
        created_at=new_key.created_at,
        api_key=plain_key  # Plain text key
    )


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all API keys for the current user.
    
    Note: The actual API key values are NOT shown (only shown once at creation).
    """
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == current_user.id)
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    
    return [
        APIKeyResponse(
            id=str(key.id),
            client_name=key.client_name,
            rate_limit=key.rate_limit,
            is_active=key.is_active,
            created_at=key.created_at,
            user_id=str(key.user_id) if key.user_id else None
        )
        for key in keys
    ]


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific API key.
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return APIKeyResponse(
        id=str(key.id),
        client_name=key.client_name,
        rate_limit=key.rate_limit,
        is_active=key.is_active,
        created_at=key.created_at,
        user_id=str(key.user_id) if key.user_id else None
    )


@router.patch("/{key_id}/revoke", response_model=APIKeyResponse)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke (disable) an API key.
    
    Revoked keys cannot be used for authentication.
    This is a soft delete - the key remains in the database.
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    if not key.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key is already revoked"
        )
    
    key.is_active = False
    await db.commit()
    await db.refresh(key)
    
    return APIKeyResponse(
        id=str(key.id),
        client_name=key.client_name,
        rate_limit=key.rate_limit,
        is_active=key.is_active,
        created_at=key.created_at,
        user_id=str(key.user_id) if key.user_id else None
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently delete an API key.
    
    ⚠️ This is irreversible! Consider revoking instead.
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    await db.delete(key)
    await db.commit()
    
    return None


@router.get("/{key_id}/stats", response_model=APIKeyStats)
async def get_api_key_stats(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage statistics for an API key.
    
    TODO: Implement actual usage tracking (will add in rate limiter later).
    For now, returns basic info.
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # TODO: Get actual usage from Redis/database
    # For now, return placeholder data
    return APIKeyStats(
        id=str(key.id),
        client_name=key.client_name,
        rate_limit=key.rate_limit,
        requests_today=0,  # Will implement with rate limiter
        last_used=None     # Will implement with rate limiter
    )