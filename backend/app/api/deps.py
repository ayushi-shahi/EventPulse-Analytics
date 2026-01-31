# backend/app/api/deps.py

import asyncio
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.api_key import APIKey
from app.core.security import verify_api_key
from app.core.rate_limiter import rate_limiter
from app.services.websocket_broadcaster import broadcaster

# -----------------------
# API KEY VALIDATION
# -----------------------
async def get_api_key(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> APIKey:

    api_key_value = None

    if x_api_key:
        api_key_value = x_api_key
    elif authorization and authorization.startswith("ApiKey "):
        api_key_value = authorization.replace("ApiKey ", "")

    if not api_key_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True)
    )
    api_keys = result.scalars().all()

    for key in api_keys:
        if verify_api_key(api_key_value, key.key_hash):
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )

# -----------------------
# RATE LIMIT
# -----------------------
async def check_rate_limit(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
) -> APIKey:

    is_allowed, info = await rate_limiter.is_allowed(
        key=str(api_key.id),
        limit=api_key.rate_limit,
        window_seconds=60,
    )

    request.state.rate_limit_info = info

    if not is_allowed:
        try:
            asyncio.create_task(
                broadcaster.publish_rate_limit_exceeded(
                    client_id=str(api_key.id),
                    limit=info["limit"],
                    reset_at=info.get("reset_at"),
                )
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {info['limit']} requests per minute",
        )

    return api_key
