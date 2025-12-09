# backend/app/api/v1/health.py (update)
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.models.api_key import APIKey
from app.api.deps import get_api_key

router = APIRouter()


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    
    Checks:
    - API is running
    - Database connection is working
    """
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
    api_key: APIKey = Depends(get_api_key)
):
    """
    Test endpoint that requires API key authentication.
    
    Use either:
    - Header: X-API-Key: your_key_here
    - Header: Authorization: ApiKey your_key_here
    """
    return {
        "message": "Success! You're authenticated with an API key",
        "client_name": api_key.client_name,
        "rate_limit": api_key.rate_limit
    }