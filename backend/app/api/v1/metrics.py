# backend/app/api/v1/metrics.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.database import get_db
from app.models.api_key import APIKey
from app.api.deps import get_api_key
from app.services.metrics_service import MetricsService
from app.schemas.metrics import (
    OverviewMetrics,
    TopEventsMetric,
    ActiveUsersMetric,
    TimeSeriesMetric
)

router = APIRouter()


@router.get("/overview", response_model=OverviewMetrics)
async def get_overview(
    period: str = Query(
        default="last_hour",
        description="Time period: last_hour, last_24h, last_7d"
    ),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overview metrics for dashboard.
    
    Returns:
    - Total events
    - Events per minute
    - Active users
    - Unique event types
    - Top 5 events
    
    **Periods**:
    - `last_hour`: Last 60 minutes
    - `last_24h`: Last 24 hours
    - `last_7d`: Last 7 days
    """
    service = MetricsService(db)
    
    try:
        metrics = await service.get_overview_metrics(
            client_id=str(api_key.id),
            period=period
        )
        
        return OverviewMetrics(**metrics)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute metrics: {str(e)}"
        )


@router.get("/top-events", response_model=TopEventsMetric)
async def get_top_events(
    period: str = Query(default="last_hour"),
    limit: int = Query(default=10, ge=1, le=100),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top events by count.
    
    Args:
    - **period**: Time period (last_hour, last_24h, last_7d)
    - **limit**: Number of top events to return (1-100)
    """
    service = MetricsService(db)
    
    # Calculate time range
    end_time = datetime.now(timezone.utc)
    if period == "last_hour":
        start_time = end_time - timedelta(hours=1)
    elif period == "last_24h":
        start_time = end_time - timedelta(hours=24)
    elif period == "last_7d":
        start_time = end_time - timedelta(days=7)
    else:
        start_time = end_time - timedelta(hours=1)
    
    try:
        top_events = await service.compute_top_events(
            client_id=str(api_key.id),
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        return TopEventsMetric(
            client_id=str(api_key.id),
            period=period,
            top_events=top_events,
            total_event_types=len(top_events)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute top events: {str(e)}"
        )


@router.get("/active-users", response_model=ActiveUsersMetric)
async def get_active_users(
    window: str = Query(
        default="1h",
        description="Time window: 1h, 24h, 7d"
    ),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Get count of active users in a time window.
    
    Active user = any user_id that had at least one event.
    
    **Windows**:
    - `1h`: Last hour
    - `24h`: Last 24 hours
    - `7d`: Last 7 days
    """
    service = MetricsService(db)
    
    # Calculate time range
    end_time = datetime.now(timezone.utc)
    if window == "1h":
        start_time = end_time - timedelta(hours=1)
    elif window == "24h":
        start_time = end_time - timedelta(hours=24)
    elif window == "7d":
        start_time = end_time - timedelta(days=7)
    else:
        start_time = end_time - timedelta(hours=1)
    
    try:
        active_users = await service.compute_active_users(
            client_id=str(api_key.id),
            window_start=start_time,
            window_end=end_time
        )
        
        return ActiveUsersMetric(
            client_id=str(api_key.id),
            window=window,
            active_users=active_users,
            start_time=start_time,
            end_time=end_time
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute active users: {str(e)}"
        )


@router.get("/time-series/{metric_name}", response_model=TimeSeriesMetric)
async def get_time_series(
    metric_name: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    interval: str = Query(default="1m", description="1m, 5m, 1h"),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Get time-series data for a specific metric.
    
    Retrieves precomputed aggregates from the database.
    
    Args:
    - **metric_name**: Name of metric (e.g., "events_per_minute")
    - **start_time**: Start of range (defaults to 1 hour ago)
    - **end_time**: End of range (defaults to now)
    - **interval**: Data point interval (1m, 5m, 1h)
    """
    service = MetricsService(db)
    
    # Default time range: last hour
    if end_time is None:
        end_time = datetime.now(timezone.utc)
    if start_time is None:
        start_time = end_time - timedelta(hours=1)
    
    try:
        data_points = await service.get_time_series(
            client_id=str(api_key.id),
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )
        
        return TimeSeriesMetric(
            metric_name=metric_name,
            interval=interval,
            data_points=data_points,
            total_points=len(data_points)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve time series: {str(e)}"
        )