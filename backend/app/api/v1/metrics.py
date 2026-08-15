# backend/app/api/v1/metrics.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from typing import Optional
import math

from app.database import get_db
from app.models.api_key import APIKey
from app.api.deps import get_api_key
from app.services.metrics_service import MetricsService
from app.schemas.metrics import (
    OverviewMetrics,
    TopEventsMetric,
    ActiveUsersMetric,
    TimeSeriesMetric,
    MetricDataPoint,
    CursorPaginatedResponse,
    PaginatedResponse
)
from app.schemas.ingest import EventResponse

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
        
@router.get("/time-series/{metric_name}/paginated")
async def get_time_series_paginated(
    metric_name: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(default=100, ge=1, le=1000),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Get time-series data with cursor-based pagination.
    
    **Cursor-based pagination** is better for time-series data as it:
    - Handles real-time updates correctly
    - Doesn't skip or duplicate data
    - More efficient for large datasets
    
    **Usage**:
    1. First request: Don't provide cursor
    2. Subsequent requests: Use `next_cursor` from previous response
    
    **Example**:
```
    GET /metrics/time-series/events_per_minute/paginated?limit=100
    # Response includes next_cursor
    GET /metrics/time-series/events_per_minute/paginated?cursor=ABC123&limit=100
```
    """
    service = MetricsService(db)
    
    # Default time range
    if end_time is None:
        end_time = datetime.now(timezone.utc)
    if start_time is None:
        start_time = end_time - timedelta(hours=1)
    
    try:
        data_points, next_cursor, has_next = await service.get_time_series_paginated(
            client_id=str(api_key.id),
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            cursor=cursor,
            limit=limit
        )
        
        return CursorPaginatedResponse(
            items=[MetricDataPoint(**dp) for dp in data_points],
            next_cursor=next_cursor,
            has_next=has_next,
            count=len(data_points)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve time series: {str(e)}"
        )


@router.get("/events", response_model=PaginatedResponse[EventResponse])
async def get_events(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    event_name: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Get raw events with pagination.
    
    **Filters**:
    - `start_time`, `end_time`: Time range
    - `event_name`: Filter by event type
    - `user_id`: Filter by user
    
    **Pagination**:
    - `page`: Page number (1-indexed)
    - `page_size`: Items per page (max 1000)
    
    **Example**:
```
    GET /metrics/events?event_name=page_view&page=1&page_size=50
```
    """
    service = MetricsService(db)
    
    # Default time range
    if end_time is None:
        end_time = datetime.now(timezone.utc)
    if start_time is None:
        start_time = end_time - timedelta(hours=24)
    
    try:
        events, total = await service.get_events_paginated(
            client_id=str(api_key.id),
            start_time=start_time,
            end_time=end_time,
            event_name=event_name,
            user_id=user_id,
            page=page,
            page_size=page_size
        )
        
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        return PaginatedResponse(
            items=[
                EventResponse(
                    id=e.id,
                    client_id=str(e.client_id),
                    user_id=e.user_id,
                    event_name=e.event_name,
                    properties=e.properties,
                    event_time=e.event_time,
                    received_at=e.received_at
                )
                for e in events
            ],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve events: {str(e)}"
        )

@router.get("/breakdown")
async def get_breakdown(
    property: str = Query(..., description="Event property to group by, e.g. device, country, plan"),
    period: str = Query(default="last_24h", description="last_hour | last_24h | last_7d | last_30d"),
    event_name: Optional[str] = Query(default=None, description="Optional: restrict to one event type"),
    limit: int = Query(default=12, ge=1, le=50),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Group events by a single property and return counts, unique users and share.

    Powers the "top devices / countries / plans" style views. The property must
    be one of a fixed allow-list — see `/metrics/breakdown/properties`.
    """
    service = MetricsService(db)
    try:
        return await service.get_breakdown(
            client_id=str(api_key.id),
            prop=property,
            period=period,
            event_name=event_name,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/breakdown/properties")
async def list_breakdown_properties(
    api_key: APIKey = Depends(get_api_key),
):
    """Properties that may be used with /metrics/breakdown."""
    return {"properties": sorted(MetricsService.ALLOWED_BREAKDOWN_PROPERTIES)}


@router.get("/funnel")
async def get_funnel(
    steps: str = Query(
        ...,
        description="Comma-separated event names in order, e.g. "
                    "signup_started,signup_completed,checkout_started,purchase_completed",
    ),
    period: str = Query(default="last_7d"),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Conversion funnel across ordered event types, counted in unique users.

    A user is counted at a step only if they also reached every preceding step.
    """
    parsed = [s.strip() for s in steps.split(",") if s.strip()]
    if not 2 <= len(parsed) <= 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provide between 2 and 8 steps",
        )
    service = MetricsService(db)
    return await service.get_funnel(client_id=str(api_key.id), steps=parsed, period=period)
