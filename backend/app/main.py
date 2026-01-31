# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import logging
import time
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.config import settings
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
# Sentry
# -----------------------
if getattr(settings, "SENTRY_DSN", None):
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT or settings.APP_ENV,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        send_default_pii=False,
    )
    logger.info(f"Sentry initialized for environment: {settings.APP_ENV}")

# -----------------------
# FastAPI app
# -----------------------
app = FastAPI(
    title="EventPulse API",
    description="Real-Time Event & Anomaly Analytics Platform",
    version="1.0.0",
    debug=settings.DEBUG,
)

# -----------------------
# CORS
# -----------------------
app.add_middleware(
    CORSMiddleware,
   
#    allow_origins=[
#         "http://localhost:3000",
#         "https://eventpulse-frontend.onrender.com",
#     ],
allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    # allow_headers=[
    #     "Authorization",
    #     "Content-Type",
    #     "Accept",
    #     "Origin",
    #     "X-Requested-With",
    # ],
    allow_headers=["*"],
)



# -----------------------
# Request Logging Middleware
# -----------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Duration: {duration:.3f}s"
        )
        response.headers["X-Process-Time"] = str(duration)
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} - Error: {str(e)}")
        raise

# -----------------------
# Global Exception Handler
# -----------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
            "path": request.url.path
        }
    )

# -----------------------
# Include Routers
# -----------------------
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Keys"])
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Event Ingestion"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(websockets.router, prefix="/api/v1/ws", tags=["WebSockets"])

# ✅ Health router (from your updated health.py)
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])

# -----------------------
# Root Endpoint
# -----------------------
@app.get("/")
async def root():
    return {
        "name": "EventPulse API",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "websocket": "ws://localhost:8000/api/v1/ws/live/{client_id}?token=YOUR_API_KEY"
    }

# -----------------------
# Startup Event
# -----------------------
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("EventPulse starting...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")

    # Initialize rate limiter
    await rate_limiter.initialize()
    logger.info("Rate limiter initialized")

    # Initialize broadcaster
    await broadcaster.initialize()
    logger.info("WebSocket broadcaster initialized")

    # Start broadcaster task
    asyncio.create_task(broadcaster.subscribe_and_broadcast())
    logger.info("WebSocket broadcaster running")
    logger.info("=" * 60)

# -----------------------
# Shutdown Event
# -----------------------
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("=" * 60)
    logger.info("EventPulse shutting down...")

    await rate_limiter.close()
    logger.info("Rate limiter closed")

    await broadcaster.close()
    logger.info("WebSocket broadcaster closed")

    logger.info("Shutdown complete")
    logger.info("=" * 60)
