# backend/app/api/deps.py

import asyncio
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status

from app.main import API_KEY_CACHE
from app.core.rate_limiter import rate_limiter
from app.services.websocket_broadcaster import broadcaster

# -----------------------
# API KEY VALIDATION (NO DB)
# -----------------------
async def get_api_key(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
) -> str:
    api_key = None

    if x_api_key:
        api_key = x_api_key
    elif authorization and authorization.startswith("ApiKey "):
        api_key = authorization.replace("ApiKey ", "")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    if api_key not in API_KEY_CACHE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key

# -----------------------
# RATE LIMIT CHECK
# -----------------------
async def check_rate_limit(
    request: Request,
    api_key: str = Depends(get_api_key),
) -> str:
    is_allowed, info = await rate_limiter.is_allowed(
        key=api_key,
        limit=60,           # per minute (adjust)
        window_seconds=60,
    )

    request.state.rate_limit_info = info

    if not is_allowed:
        try:
            asyncio.create_task(
                broadcaster.publish_rate_limit_exceeded(
                    client_id=api_key,
                    limit=info["limit"],
                    reset_at=info.get("reset_at"),
                )
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": "0",
                "Retry-After": "60",
            },
        )

    return api_key
