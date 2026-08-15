# backend/app/api/deps.py
"""
FastAPI dependencies for authentication and rate limiting.

API key lookup uses a direct hash-based query (single indexed lookup)
instead of loading the entire api_keys table into memory on every request.
"""
import asyncio
import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.api_key import APIKey
from app.core.security import hash_api_key, decode_token   # hash first, then query
from app.core.rate_limiter import rate_limiter
from app.services.websocket_broadcaster import broadcaster


# ---------------------------------------------------------------------------
# API KEY VALIDATION
# ---------------------------------------------------------------------------

async def get_api_key(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    x_client_id: Optional[str] = Header(None),
    client_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """
    Resolve which API key (client) this request is scoped to.

    Two independent routes, for two different callers:

    1. **The SDK** presents the secret itself —
       `X-API-Key: <key>` or `Authorization: ApiKey <key>`.
       The plain key is SHA-256 hashed and matched against the indexed
       `key_hash` column: a single indexed lookup, no table scan.

    2. **The dashboard** presents the user's session —
       `Authorization: Bearer <jwt>` plus the key's id via `X-Client-Id`
       or `?client_id=`. Ownership is verified against the token's user.

       Route 2 exists because keys are stored hashed: the plaintext is shown
       exactly once, at creation. Without it, signing in from a new browser
       left you unable to read your own analytics — the dashboard had no way
       to name a key it could no longer produce the secret for. Proving you
       own the key with your session is both sufficient and safer than
       persisting secrets client-side.
    """
    # --- Route 1: the secret was supplied directly ---
    api_key_value: Optional[str] = None
    if x_api_key:
        api_key_value = x_api_key.strip()
    elif authorization and authorization.startswith("ApiKey "):
        api_key_value = authorization.removeprefix("ApiKey ").strip()

    if api_key_value:
        result = await db.execute(
            select(APIKey).where(
                APIKey.key_hash == hash_api_key(api_key_value),
                APIKey.is_active == True,  # noqa: E712 — SQL boolean, not Python
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
            )
        return api_key

    # --- Route 2: an authenticated owner naming one of their own keys ---
    requested_id = (x_client_id or client_id or "").strip()
    if authorization and authorization.startswith("Bearer ") and requested_id:
        token = authorization.removeprefix("Bearer ").strip()
        payload = decode_token(token)
        user_id = (payload or {}).get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session token is invalid or expired",
            )

        try:
            key_uuid = uuid.UUID(requested_id)
        except (ValueError, AttributeError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="client_id must be a valid API key id",
            )

        result = await db.execute(
            select(APIKey).where(
                APIKey.id == key_uuid,
                APIKey.is_active == True,  # noqa: E712
            )
        )
        api_key = result.scalar_one_or_none()

        # Same response whether the key is missing or owned by someone else,
        # so this cannot be used to probe for valid key ids.
        if api_key is None or str(api_key.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Provide an API key via X-API-Key, or sign in and pass "
               "X-Client-Id naming one of your keys",
    )


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