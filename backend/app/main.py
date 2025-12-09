# backend/app/main.py
from fastapi import FastAPI
from app.config import settings
from app.api.v1 import auth, health  # We'll add more routers later

app = FastAPI(
    title="EventPulse API",
    description="Real-Time Event & Anomaly Analytics Platform",
    version="1.0.0",
    debug=settings.DEBUG
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "EventPulse API",
        "version": "1.0.0",
        "status": "running"
    }


# Startup / shutdown events
@app.on_event("startup")
async def startup_event():
    print("EventPulse starting...")
    print(f"Environment: {settings.APP_ENV}")


@app.on_event("shutdown")
async def shutdown_event():
    print("EventPulse shutting down...")