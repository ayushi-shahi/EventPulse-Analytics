# backend/app/main.py (update)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from app.config import settings
from app.api.v1 import auth, api_keys, ingest, admin, health, websockets, metrics
from app.core.rate_limiter import rate_limiter
from app.services.websocket_broadcaster import broadcaster

app = FastAPI(
    title="EventPulse API",
    description="Real-Time Event & Anomaly Analytics Platform",
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Keys"])
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Event Ingestion"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(websockets.router, prefix="/api/v1/ws", tags=["WebSockets"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "EventPulse API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "websocket": "ws://localhost:8000/api/v1/ws/live/{client_id}?token=YOUR_API_KEY"
    }


@app.on_event("startup")
async def startup_event():
    print("🚀 EventPulse starting...")
    print(f"Environment: {settings.APP_ENV}")
    
    # Initialize rate limiter
    await rate_limiter.initialize()
    print("✅ Rate limiter initialized")
    
    # Initialize broadcaster
    await broadcaster.initialize()
    print("✅ WebSocket broadcaster initialized")
    
    # Start broadcaster as background task
    asyncio.create_task(broadcaster.subscribe_and_broadcast())
    print("✅ WebSocket broadcaster running")


@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 EventPulse shutting down...")
    
    await rate_limiter.close()
    print("✅ Rate limiter closed")
    
    await broadcaster.close()
    print("✅ WebSocket broadcaster closed")