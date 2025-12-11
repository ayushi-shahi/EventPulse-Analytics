# backend/app/schemas/metrics.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List


class MetricDataPoint(BaseModel):
    """Single data point in a time series"""
    timestamp: datetime
    value: float
    meta_data: Optional[Dict[str, Any]] = None


class TimeSeriesMetric(BaseModel):
    """Time series metric response"""
    metric_name: str
    interval: str  # e.g., "1m", "5m", "1h"
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
                        "value": 1250.5
                    },
                    {
                        "timestamp": "2024-12-10T10:01:00Z",
                        "value": 1430.2
                    }
                ],
                "total_points": 2
            }
        }


class OverviewMetrics(BaseModel):
    """Dashboard overview metrics"""
    client_id: str
    period: str  # e.g., "last_hour", "last_24h"
    
    # Core metrics
    total_events: int
    events_per_minute: float
    active_users: int
    unique_event_types: int
    
    # Top events
    top_events: List[Dict[str, Any]]
    
    # Time range
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
                    {"event_name": "button_click", "count": 18920}
                ],
                "start_time": "2024-12-10T09:00:00Z",
                "end_time": "2024-12-10T10:00:00Z"
            }
        }


class TopEventsMetric(BaseModel):
    """Top events by count"""
    client_id: str
    period: str
    top_events: List[Dict[str, Any]]
    total_event_types: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "550e8400-...",
                "period": "last_hour",
                "top_events": [
                    {
                        "event_name": "page_view",
                        "count": 32150,
                        "percentage": 42.6
                    },
                    {
                        "event_name": "button_click",
                        "count": 18920,
                        "percentage": 25.1
                    }
                ],
                "total_event_types": 12
            }
        }


class ActiveUsersMetric(BaseModel):
    """Active users in a time window"""
    client_id: str
    window: str  # e.g., "1h", "24h"
    active_users: int
    start_time: datetime
    end_time: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "550e8400-...",
                "window": "1h",
                "active_users": 1523,
                "start_time": "2024-12-10T09:00:00Z",
                "end_time": "2024-12-10T10:00:00Z"
            }
        }


class MetricQuery(BaseModel):
    """Query parameters for metrics"""
    client_id: str
    metric_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    interval: Optional[str] = Field(default="1m", description="1m, 5m, 1h, 1d")
    limit: Optional[int] = Field(default=100, ge=1, le=1000)