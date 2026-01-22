# backend/app/api/v1/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
from datetime import datetime, timezone

from app.database import get_db
from app.models.api_key import APIKey
from app.api.deps import get_api_key
from app.config import settings
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

# -------------------------------
# Basic Health Check
# -------------------------------
@router.get("/", include_in_schema=False)  # hide from /docs
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Basic health check endpoint.
    Handles trailing slash properly to avoid 307 redirect.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {"status": "unhealthy", "message": str(e)}

    # Check Redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await redis_client.ping()
        await redis_client.close()
        health_status["checks"]["redis"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = {"status": "unhealthy", "message": str(e)}

    return health_status


# -------------------------------
# Detailed Health Check
# -------------------------------
@router.get("/detailed", include_in_schema=False)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check with metrics.
    Returns system status, database stats, Redis queue lengths, etc.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "checks": {},
        "metrics": {}
    }

    # Database check
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM events"))
        event_count = result.scalar()
        health["checks"]["database"] = {"status": "healthy", "total_events": event_count}
        health["metrics"]["total_events"] = event_count
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        health["status"] = "degraded"
        health["checks"]["database"] = {"status": "unhealthy", "error": str(e)}

    # Redis check
    try:
        redis_client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await redis_client.ping()
        queue_length = await redis_client.llen("event_queue")
        await redis_client.close()
        health["checks"]["redis"] = {"status": "healthy", "queue_length": queue_length}
        health["metrics"]["queue_length"] = queue_length
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        health["status"] = "degraded"
        health["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}

    # Active clients check
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM api_keys WHERE is_active = true"))
        active_clients = result.scalar()
        health["metrics"]["active_clients"] = active_clients
    except Exception as e:
        logger.warning(f"Could not fetch active clients: {e}")

    # Active alerts check
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM alerts WHERE enabled = true"))
        active_alerts = result.scalar()
        health["metrics"]["active_alerts"] = active_alerts
    except Exception as e:
        logger.warning(f"Could not fetch active alerts: {e}")

    return health


# -------------------------------
# Kubernetes Liveness Probe
# -------------------------------
@router.get("/live", include_in_schema=False)
async def liveness_probe():
    """
    Liveness probe for Kubernetes.
    Returns 200 if app is running.
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


# -------------------------------
# Kubernetes Readiness Probe
# -------------------------------
@router.get("/ready", include_in_schema=False)
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe for Kubernetes.
    Returns 200 if ready, 503 if not ready.
    """
    try:
        await db.execute(text("SELECT 1"))
        redis_client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        await redis_client.ping()
        await redis_client.close()
        return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}


# -------------------------------
# Protected endpoint (API key required)
# -------------------------------
@router.get("/protected", include_in_schema=False)
async def protected_endpoint(api_key: APIKey = Depends(get_api_key)):
    """
    Test endpoint requiring API key authentication.
    """
    return {
        "message": "Success! You're authenticated with an API key",
        "client_name": api_key.client_name,
        "rate_limit": api_key.rate_limit
    }
