# backend/app/api/v1/health.py (update)
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.models.api_key import APIKey
from app.api.deps import get_api_key, check_rate_limit

router = APIRouter()


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint - no authentication required"""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status
    }


@router.get("/protected")
async def protected_endpoint(
    api_key: APIKey = Depends(check_rate_limit)  # Now with rate limiting!
):
    """
    Test endpoint with API key authentication AND rate limiting.
    
    Try calling this repeatedly to see rate limiting in action!
    """
    return {
        "message": "Success! You're authenticated and under rate limit",
        "client_name": api_key.client_name,
        "rate_limit": f"{api_key.rate_limit} requests/minute"
    }