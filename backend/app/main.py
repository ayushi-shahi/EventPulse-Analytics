# backend/app/main.py (update)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import auth, api_keys, ingest, health, admin
from app.core.rate_limiter import rate_limiter

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
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "EventPulse API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/v1/auth",
            "api_keys": "/api/v1/api-keys",
            "ingest": "/api/v1/ingest",
            "admin": "/api/v1/admin",
            "health": "/api/v1/health"
        }
    }


@app.on_event("startup")
async def startup_event():
    print("🚀 EventPulse starting...")
    print(f"Environment: {settings.APP_ENV}")
    print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    
    await rate_limiter.initialize()
    print("✅ Rate limiter initialized")


@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 EventPulse shutting down...")
    await rate_limiter.close()
    print("✅ Rate limiter closed")