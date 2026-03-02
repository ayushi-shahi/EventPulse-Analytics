# backend/app/api/deps.py
"""
FastAPI dependencies for authentication and rate limiting.

API key lookup uses a direct hash-based query (single indexed lookup)
instead of loading the entire api_keys table into memory on every request.
"""
import asyncio
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.api_key import APIKey
from app.core.security import hash_api_key        # hash first, then query
from app.core.rate_limiter import rate_limiter
from app.services.websocket_broadcaster import broadcaster


# ---------------------------------------------------------------------------
# API KEY VALIDATION
# ---------------------------------------------------------------------------

async def get_api_key(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """
    Validate the API key supplied in the request headers.

    Accepts two formats:
      - X-API-Key: <key>
      - Authorization: ApiKey <key>

    The plain key is hashed with SHA-256 and looked up directly against
    the indexed `key_hash` column — O(log n) instead of a full table scan.
    """
    # --- Extract raw key from headers ---
    api_key_value: Optional[str] = None

    if x_api_key:
        api_key_value = x_api_key.strip()
    elif authorization and authorization.startswith("ApiKey "):
        api_key_value = authorization.removeprefix("ApiKey ").strip()

    if not api_key_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Supply it via X-API-Key header or "
                   "Authorization: ApiKey <key>",
        )

    # --- Hash and query directly — single indexed lookup ---
    key_hash = hash_api_key(api_key_value)

    result = await db.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        )
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    return api_key


# ---------------------------------------------------------------------------
# RATE LIMITING
# ---------------------------------------------------------------------------

async def check_rate_limit(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
) -> APIKey:
    """
    Enforce per-API-key rate limiting (requests per minute).

    Attaches rate limit info to request.state so route handlers
    can read it if needed (e.g. to set X-RateLimit-* response headers).

    On limit exceeded:
    - Publishes a rate_limit_exceeded event to the WebSocket broadcaster
    - Returns HTTP 429
    """
    is_allowed, info = await rate_limiter.is_allowed(
        key=str(api_key.id),
        limit=api_key.rate_limit,
        window_seconds=60,
    )

    # Always attach info so routes can expose it in response headers
    request.state.rate_limit_info = info

    if not is_allowed:
        # Fire-and-forget WebSocket notification — don't let this block the 429
        try:
            asyncio.create_task(
                broadcaster.publish_rate_limit_exceeded(
                    client_id=str(api_key.id),
                    limit=info["limit"],
                    reset_at=info.get("reset_at"),
                )
            )
        except RuntimeError:
            # No running event loop in test context — skip silently
            pass

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded: {info['limit']} requests/minute allowed. "
                f"Resets at epoch {info.get('reset_at')}."
            ),
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info.get("remaining", 0)),
                "X-RateLimit-Reset": str(info.get("reset_at", "")),
                "Retry-After": "60",
            },
        )

    return api_key