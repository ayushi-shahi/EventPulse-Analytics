# backend/app/api/deps.py (update)
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.models.api_key import APIKey
from app.core.security import verify_api_key
from app.core.rate_limiter import rate_limiter


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
    
    # Query all active API keys
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


async def check_rate_limit(
    request: Request,
    api_key: APIKey = Depends(get_api_key)
) -> APIKey:
    """
    Dependency that checks rate limits for an API key.
    
    Returns:
        APIKey object if under limit
        
    Raises:
        HTTPException: If rate limit exceeded (429)
    """
    # Check rate limit
    is_allowed, info = await rate_limiter.is_allowed(
        key=str(api_key.id),
        limit=api_key.rate_limit,
        window_seconds=60  # 1 minute window
    )
    
    # Add rate limit headers to response
    request.state.rate_limit_info = info
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {info['limit']} requests per minute",
            headers={
                "X-RateLimit-Limit": str(info['limit']),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(info['reset_at']),
                "Retry-After": "60"
            }
        )
    
    return api_key