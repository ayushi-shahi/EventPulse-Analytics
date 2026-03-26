# backend/app/main.py
"""
FastAPI application entry point.

Startup and shutdown are handled via a single `lifespan` context manager
(the modern FastAPI/Starlette approach). The deprecated @app.on_event
decorator is not used anywhere.
"""
import asyncio
import time
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.config import settings
from app.api.v1 import auth, api_keys, ingest, metrics, alerts, admin, websockets, health
from app.core.rate_limiter import rate_limiter
from app.services.websocket_broadcaster import broadcaster
from app.logging_config import setup_logging, get_logger
from fastapi.staticfiles import StaticFiles


# ---------------------------------------------------------------------------
# Logging (must be first)
# ---------------------------------------------------------------------------

setup_logging()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Sentry (optional — only initialised when SENTRY_DSN is set)
# ---------------------------------------------------------------------------

if settings.SENTRY_DSN:
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
    logger.info(f"Sentry initialised (environment: {settings.APP_ENV})")

# ---------------------------------------------------------------------------
# Lifespan — replaces the deprecated @app.on_event("startup/shutdown")
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("EventPulse starting up...")
 
    await rate_limiter.initialize()
    logger.info("Rate limiter initialised")
 
    await broadcaster.initialize()
    broadcast_task = asyncio.create_task(broadcaster.subscribe_and_broadcast())
    logger.info("WebSocket broadcaster started")
 
    # Start APScheduler (replaces Celery worker + beat)
    from app.tasks.scheduler import start_scheduler
    start_scheduler()
 
    logger.info("EventPulse is ready")
 
    yield
 
    logger.info("EventPulse shutting down...")
 
    from app.tasks.scheduler import stop_scheduler
    stop_scheduler()
 
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
 
    await broadcaster.close()
    await rate_limiter.close()
 
    logger.info("EventPulse shutdown complete")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="EventPulse API",
    description="Real-Time Event & Anomaly Analytics Platform",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,          # ← modern approach
)

import os
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://event-pulse-analytics-frontend.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with method, path, status code and duration."""
    start = time.time()
    logger.info(f"→ {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            f"← {request.method} {request.url.path} "
            f"{response.status_code} ({duration:.3f}s)"
        )
        response.headers["X-Process-Time"] = f"{duration:.3f}"
        return response

    except Exception as e:
        duration = time.time() - start
        logger.error(
            f"✗ {request.method} {request.url.path} "
            f"failed after {duration:.3f}s — {e}"
        )
        raise


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception: {type(exc).__name__} — {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
            "path": request.url.path,
        },
    )

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router,       prefix="/api/v1/auth",       tags=["Authentication"])
app.include_router(api_keys.router,   prefix="/api/v1/api-keys",   tags=["API Keys"])
app.include_router(ingest.router,     prefix="/api/v1/ingest",     tags=["Event Ingestion"])
app.include_router(metrics.router,    prefix="/api/v1/metrics",    tags=["Metrics"])
app.include_router(alerts.router,     prefix="/api/v1/alerts",     tags=["Alerts"])
app.include_router(admin.router,      prefix="/api/v1/admin",      tags=["Admin"])
app.include_router(websockets.router, prefix="/api/v1/ws",         tags=["WebSockets"])
app.include_router(health.router,     prefix="/api/v1/health",     tags=["Health"])

# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "EventPulse API",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.APP_ENV,
        "docs": "/docs",
    }