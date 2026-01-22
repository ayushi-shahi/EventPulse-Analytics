# backend/app/schemas/metrics.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List, Generic, TypeVar, Literal
import math

T = TypeVar("T")

# -------------------- PAGINATION --------------------

class PaginationParams(BaseModel):
    """Offset-based pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=100, ge=1, le=1000, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def from_query(
        cls,
        *,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ):
        total_pages = math.ceil(total / page_size) if page_size else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 150,
                "page": 1,
                "page_size": 50,
                "total_pages": 3,
                "has_next": True,
                "has_prev": False,
            }
        }


# -------------------- CURSOR PAGINATION --------------------

class CursorPaginationParams(BaseModel):
    """Cursor-based pagination (recommended for real-time data)"""
    cursor: Optional[str] = Field(
        None,
        description="Opaque cursor for next page",
    )
    limit: int = Field(default=100, ge=1, le=1000)


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based paginated response"""
    items: List[T]
    next_cursor: Optional[str] = None
    has_next: bool = False
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "next_cursor": "eyJ0aW1lc3RhbXAiOiIyMDI0LTEyLTEwVDEwOjMwOjAwWiJ9",
                "has_next": True,
                "count": 100,
            }
        }


# -------------------- METRIC DATA --------------------

class MetricDataPoint(BaseModel):
    """Single data point in a time series"""
    timestamp: datetime
    value: float
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for the data point",
        alias="meta_data",
    )

    class Config:
        allow_population_by_field_name = True


class TimeSeriesMetric(BaseModel):
    """Time series metric response"""
    metric_name: str
    interval: Literal["1m", "5m", "15m", "1h", "1d"] = "1m"
    data_points: List[MetricDataPoint]
    total_points: int

    class Config:
        json_schema_extra = {
            "example": {
                "metric_name": "events_per_minute",
                "interval": "1m",
                "data_points": [
                    {
                        "timestamp": "2024-12-10T10:00:00Z",
                        "value": 1250.5,
                    },
                    {
                        "timestamp": "2024-12-10T10:01:00Z",
                        "value": 1430.2,
                    },
                ],
                "total_points": 2,
            }
        }


# -------------------- DASHBOARD METRICS --------------------

class TopEvent(BaseModel):
    event_name: str
    count: int
    percentage: Optional[float] = None


class OverviewMetrics(BaseModel):
    """Dashboard overview metrics"""
    client_id: str
    period: Literal["last_hour", "last_24h", "last_7d"]

    total_events: int
    events_per_minute: float
    active_users: int
    unique_event_types: int

    top_events: List[TopEvent]

    start_time: datetime
    end_time: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "550e8400-...",
                "period": "last_hour",
                "total_events": 75420,
                "events_per_minute": 1257.0,
                "active_users": 1523,
                "unique_event_types": 12,
                "top_events": [
                    {"event_name": "page_view", "count": 32150},
                    {"event_name": "button_click", "count": 18920},
                ],
                "start_time": "2024-12-10T09:00:00Z",
                "end_time": "2024-12-10T10:00:00Z",
            }
        }


class TopEventsMetric(BaseModel):
    """Top events by count"""
    client_id: str
    period: Literal["last_hour", "last_24h", "last_7d"]
    top_events: List[TopEvent]
    total_event_types: int


class ActiveUsersMetric(BaseModel):
    """Active users in a time window"""
    client_id: str
    window: Literal["1h", "24h", "7d"]
    active_users: int
    start_time: datetime
    end_time: datetime


# -------------------- QUERY PARAMS --------------------

class MetricQuery(BaseModel):
    """Query parameters for metrics APIs"""
    metric_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    interval: Literal["1m", "5m", "15m", "1h", "1d"] = "1m"
    limit: int = Field(default=100, ge=1, le=1000)
