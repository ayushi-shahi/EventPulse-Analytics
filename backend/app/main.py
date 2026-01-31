# backend/app/main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import asyncio
import time
import sentry_sdk

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.config import settings
from app.database import engine
from app.models.api_key import APIKey

from app.api.v1 import auth, api_keys, ingest, metrics, alerts, admin, websockets, health
from app.core.rate_limiter import rate_limiter
from app.services.websocket_broadcaster import broadcaster
from app.logging_config import setup_logging, get_logger

# -----------------------
# Logging
# -----------------------
setup_logging()
logger = get_logger(__name__)

# -----------------------
# API Key Cache (GLOBAL)
# -----------------------
API_KEY_CACHE: set[str] = set()

# -----------------------
# Sentry (safe)
# -----------------------
if getattr(settings, "SENTRY_DSN", None):
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=getattr(settings, "SENTRY_ENVIRONMENT", settings.APP_ENV),
        traces_sample_rate=getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.0),
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        send_default_pii=False,
    )
    logger.info("Sentry initialized")

# -----------------------
# FastAPI App
# -----------------------
app = FastAPI(
    title="EventPulse API",
    description="Real-Time Event & Anomaly Analytics Platform",
    version="1.0.0",
    debug=settings.DEBUG,
)

# -----------------------
# CORS (ALLOW ALL for ingestion)
# -----------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # MUST be False with "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Request Logging Middleware
# -----------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} "
        f"{response.status_code} {duration:.3f}s"
    )

    response.headers["X-Process-Time"] = str(duration)
    return response

# -----------------------
# Global Exception Handler
# -----------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# -----------------------
# Routers
# -----------------------
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Keys"])
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Event Ingestion"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(websockets.router, prefix="/api/v1/ws", tags=["WebSockets"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])

# -----------------------
# Root
# -----------------------
@app.get("/")
async def root():
    return {
        "name": "EventPulse API",
        "status": "running",
        "env": settings.APP_ENV,
    }

# -----------------------
# STARTUP: Load API Keys ONCE
# -----------------------
@app.on_event("startup")
async def startup_event():
    logger.info("Starting EventPulse")

    # Load API keys into memory
    async with AsyncSession(engine) as db:
        result = await db.execute(
            select(APIKey.key).where(APIKey.is_active == True)
        )
        for row in result:
            API_KEY_CACHE.add(row[0])

    logger.info(f"Loaded {len(API_KEY_CACHE)} API keys into cache")

    # Init rate limiter
    await rate_limiter.initialize()

    # Init WebSocket broadcaster
    await broadcaster.initialize()
    asyncio.create_task(broadcaster.subscribe_and_broadcast())

# -----------------------
# SHUTDOWN
# -----------------------
@app.on_event("shutdown")
async def shutdown_event():
    await rate_limiter.close()
    await broadcaster.close()
    logger.info("EventPulse shutdown complete")
