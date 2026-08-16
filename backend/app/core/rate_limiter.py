# backend/app/core/rate_limiter.py (complete rewrite with Lua)
import redis.asyncio as redis
from datetime import datetime, timezone
from time import monotonic
from typing import Optional, Tuple, Dict
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Redis-based rate limiter using Lua scripts for atomic operations.
    
    Advantages of Lua script:
    - Single round-trip to Redis
    - Atomic operation (no race conditions)
    - Better performance under high load
    """
    
    # Lua script for rate limiting (loaded once)
    RATE_LIMIT_SCRIPT = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    
    -- Remove old entries
    local window_start = now - window
    redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
    
    -- Count current entries
    local current = redis.call('ZCARD', key)
    
    -- Check if under limit
    if current < limit then
        -- Add new entry
        redis.call('ZADD', key, now, now)
        -- Set expiration
        redis.call('EXPIRE', key, window * 2)
        current = current + 1
        return {1, current, limit}  -- allowed, current, limit
    else
        return {0, current, limit}  -- not allowed, current, limit
    end
    """
    
    # When Redis is unreachable, wait this long before trying again. Without a
    # cooldown every single request would attempt a fresh connection and pay
    # the full connect timeout.
    INIT_RETRY_COOLDOWN_SECONDS = 30

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._script_sha: Optional[str] = None
        self._last_init_failure: float = 0.0

    async def initialize(self) -> bool:
        """
        Connect to Redis and load the Lua script.

        Never raises. Rate limiting is a protective layer, not a hard
        dependency — if Redis is unreachable (or the plan's command quota is
        exhausted) the limiter degrades to fail-open rather than taking the
        whole API down with it. Returns True when the limiter is usable.
        """
        if self.redis_client is not None:
            return True

        if monotonic() - self._last_init_failure < self.INIT_RETRY_COOLDOWN_SECONDS:
            return False

        client = None
        try:
            client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                socket_keepalive=True,
                max_connections=50  # Connection pool
            )

            # Load Lua script into Redis
            self._script_sha = await client.script_load(
                self.RATE_LIMIT_SCRIPT
            )

            self.redis_client = client
            self._last_init_failure = 0.0
            logger.info("✅ Rate limiter initialized with Lua script")
            return True

        except Exception as e:
            self._last_init_failure = monotonic()
            self._script_sha = None
            self.redis_client = None
            if client is not None:
                try:
                    await client.aclose()
                except Exception:
                    pass
            logger.warning(
                f"Rate limiter unavailable, failing open for the next "
                f"{self.INIT_RETRY_COOLDOWN_SECONDS}s: {e}"
            )
            return False

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Rate limiter Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing rate limiter: {e}")
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int = 60
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if a request is allowed under rate limit.
        
        Uses Lua script for atomic operation with single Redis call.
        
        Args:
            key: Unique identifier (e.g., API key ID)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds (default: 60s)
            
        Returns:
            Tuple of (is_allowed, info_dict)
            info_dict contains: current, limit, remaining, reset_at
        """
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp())

        if not await self.initialize():
            # Redis is down — allow the request rather than reject everyone.
            return True, {
                "current": 0,
                "limit": limit,
                "remaining": limit,
                "reset_at": timestamp + window_seconds,
                "degraded": True,
            }

        # Redis key for this rate limit
        redis_key = f"rate_limit:{key}"

        try:
            # Execute Lua script
            result = await self.redis_client.evalsha(
                self._script_sha,
                1,  # Number of keys
                redis_key,
                timestamp,
                window_seconds,
                limit
            )
            
            # Parse result: [allowed, current, limit]
            is_allowed = bool(result[0])
            current_count = int(result[1])
            
            # Calculate reset time
            reset_at = timestamp + window_seconds
            
            return is_allowed, {
                "current": current_count,
                "limit": limit,
                "remaining": max(0, limit - current_count),
                "reset_at": reset_at
            }
        
        except redis.exceptions.NoScriptError:
            # Redis restarted and dropped its script cache — reload once.
            # Reloading is itself a Redis call, so it gets the same fail-open
            # treatment rather than being allowed to escape as a 500.
            logger.warning("Lua script not found, reloading...")
            try:
                self._script_sha = await self.redis_client.script_load(
                    self.RATE_LIMIT_SCRIPT
                )
                result = await self.redis_client.evalsha(
                    self._script_sha, 1, redis_key, timestamp, window_seconds, limit
                )
                return bool(result[0]), {
                    "current": int(result[1]),
                    "limit": limit,
                    "remaining": max(0, limit - int(result[1])),
                    "reset_at": timestamp + window_seconds,
                }
            except Exception as e:
                return self._fail_open(limit, timestamp, window_seconds, e)

        except Exception as e:
            return self._fail_open(limit, timestamp, window_seconds, e)

    def _fail_open(self, limit, timestamp, window_seconds, exc):
        """Allow the request when Redis misbehaves, and back off reconnecting."""
        logger.error(f"Rate limit check failed, allowing request: {exc}")
        # Drop the client so the next call reconnects — and so the cooldown in
        # initialize() stops us hammering a Redis that is down or over quota.
        self.redis_client = None
        self._script_sha = None
        self._last_init_failure = monotonic()
        return True, {
            "current": 0,
            "limit": limit,
            "remaining": limit,
            "reset_at": timestamp + window_seconds,
            "degraded": True,
            "error": str(exc),
        }
    
    async def reset(self, key: str):
        """
        Reset rate limit for a key (admin function).
        
        Args:
            key: Rate limit key to reset
        """
        if self.redis_client is None:
            await self.initialize()
        
        redis_key = f"rate_limit:{key}"
        
        try:
            await self.redis_client.delete(redis_key)
            logger.info(f"Rate limit reset for key: {key}")
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
    
    async def get_stats(self, key: str) -> Dict[str, int]:
        """
        Get current rate limit statistics for a key.
        
        Args:
            key: Rate limit key
            
        Returns:
            Dict with current count and window info
        """
        if self.redis_client is None:
            await self.initialize()
        
        redis_key = f"rate_limit:{key}"
        
        try:
            count = await self.redis_client.zcard(redis_key)
            ttl = await self.redis_client.ttl(redis_key)
            
            return {
                "current": count,
                "ttl": ttl
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit stats: {e}")
            return {"current": 0, "ttl": -1}


# Global rate limiter instance
rate_limiter = RateLimiter()