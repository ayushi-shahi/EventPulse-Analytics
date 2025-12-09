# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.models.api_key import APIKey
from app.core.security import verify_api_key


async def get_api_key(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> APIKey:
    """
    Dependency to validate API key from headers.
    Accepts key in either:
    - X-API-Key header
    - Authorization: ApiKey <key> header
    
    Returns:
        APIKey object if valid
        
    Raises:
        HTTPException: If key is missing or invalid
    """
    api_key_value = None
    
    # Check X-API-Key header
    if x_api_key:
        api_key_value = x_api_key
    
    # Check Authorization header (format: "ApiKey <key>")
    elif authorization and authorization.startswith("ApiKey "):
        api_key_value = authorization.replace("ApiKey ", "")
    
    if not api_key_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via X-API-Key header or Authorization: ApiKey <key>"
        )
    
    # Query all API keys (we'll optimize this later with caching)
    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True)
    )
    api_keys = result.scalars().all()
    
    # Find matching key
    for key in api_keys:
        if verify_api_key(api_key_value, key.key_hash):
            return key
    
    # No match found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )