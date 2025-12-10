# backend/app/core/rate_limiter.py
import redis.asyncio as redis
from datetime import datetime, timezone
from typing import Optional
from app.config import settings


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.
    
    For each API key, we track requests in a time window.
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection"""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int = 60
    ) -> tuple[bool, dict]:
        """
        Check if a request is allowed under rate limit.
        
        Args:
            key: Unique identifier (e.g., API key ID)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds (default: 60s = 1 minute)
            
        Returns:
            Tuple of (is_allowed, info_dict)
            info_dict contains: current_count, limit, reset_time
        """
        if self.redis_client is None:
            await self.initialize()
        
        now = datetime.now(timezone.utc)
        window_start = int(now.timestamp()) - window_seconds
        
        # Redis key for this rate limit
        redis_key = f"rate_limit:{key}"
        
        # Use sorted set with timestamps as scores
        # Remove old entries outside the window
        await self.redis_client.zremrangebyscore(
            redis_key, 
            '-inf', 
            window_start
        )
        
        # Count requests in current window
        current_count = await self.redis_client.zcard(redis_key)
        
        # Check if under limit
        is_allowed = current_count < limit
        
        if is_allowed:
            # Add current request
            timestamp = now.timestamp()
            await self.redis_client.zadd(
                redis_key,
                {f"{timestamp}": timestamp}
            )
            
            # Set expiration on the key (cleanup)
            await self.redis_client.expire(redis_key, window_seconds * 2)
            
            current_count += 1
        
        # Calculate when the limit resets
        reset_time = int(now.timestamp()) + window_seconds
        
        return is_allowed, {
            "current": current_count,
            "limit": limit,
            "remaining": max(0, limit - current_count),
            "reset_at": reset_time
        }


# Global rate limiter instance
rate_limiter = RateLimiter()