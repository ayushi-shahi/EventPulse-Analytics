# backend/app/core/rate_limiter.py (complete rewrite with Lua)
import redis.asyncio as redis
from datetime import datetime, timezone
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
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._script_sha: Optional[str] = None
    
    async def initialize(self):
        """Initialize Redis connection and load Lua script"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    max_connections=50  # Connection pool
                )
                
                # Load Lua script into Redis
                self._script_sha = await self.redis_client.script_load(
                    self.RATE_LIMIT_SCRIPT
                )
                
                logger.info("✅ Rate limiter initialized with Lua script")
            
            except Exception as e:
                logger.error(f"Failed to initialize rate limiter: {e}", exc_info=True)
                raise
    
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
        if self.redis_client is None:
            await self.initialize()
        
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp())
        
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
            # Script not loaded, reload it
            logger.warning("Lua script not found, reloading...")
            self._script_sha = await self.redis_client.script_load(
                self.RATE_LIMIT_SCRIPT
            )
            # Retry
            return await self.is_allowed(key, limit, window_seconds)
        
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}", exc_info=True)
            # Fail open (allow request) to prevent service disruption
            return True, {
                "current": 0,
                "limit": limit,
                "remaining": limit,
                "reset_at": timestamp + window_seconds,
                "error": str(e)
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