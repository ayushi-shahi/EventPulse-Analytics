# backend/app/schemas/alert.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal


class AlertExpression(BaseModel):
    """Alert condition expression"""
    metric: str = Field(..., description="Metric name (e.g., 'events_per_minute')")
    operator: Literal[">", "<", ">=", "<=", "==", "!="] = Field(..., description="Comparison operator")
    threshold: float = Field(..., description="Threshold value")
    window: Optional[str] = Field(default="1m", description="Time window (e.g., '1m', '5m', '1h')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metric": "events_per_minute",
                "operator": ">",
                "threshold": 1000,
                "window": "1m"
            }
        }


class NotificationChannels(BaseModel):
    """Notification delivery configuration"""
    websocket: bool = Field(default=True, description="Send via WebSocket")
    email: Optional[List[str]] = Field(default=None, description="Email addresses")
    
    class Config:
        json_schema_extra = {
            "example": {
                "websocket": True,
                "email": ["admin@example.com", "ops@example.com"]
            }
        }


class AlertCreate(BaseModel):
    """Schema for creating an alert"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    expression: AlertExpression
    severity: Literal["info", "warning", "error", "critical"] = Field(default="info")
    enabled: bool = Field(default=True)
    notification_channels: Optional[NotificationChannels] = Field(
        default=NotificationChannels(websocket=True)
    )
    cooldown_seconds: int = Field(default=300, ge=0, le=3600)


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    expression: Optional[AlertExpression] = None
    severity: Optional[Literal["info", "warning", "error", "critical"]] = None
    enabled: Optional[bool] = None
    notification_channels: Optional[NotificationChannels] = None
    cooldown_seconds: Optional[int] = Field(None, ge=0, le=3600)


class AlertResponse(BaseModel):
    """Schema for alert in responses"""
    id: str
    client_id: str
    name: str
    description: Optional[str]
    expression: Dict[str, Any]
    severity: str
    enabled: bool
    last_triggered: Optional[datetime]
    trigger_count: int
    notification_channels: Dict[str, Any]
    cooldown_seconds: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):
    """Schema for alert history in responses"""
    id: str
    alert_id: str
    client_id: str
    triggered_at: datetime
    severity: str
    message: str
    context: Optional[Dict[str, Any]]
    notification_sent: bool
    
    class Config:
        from_attributes = True


class AlertTestResponse(BaseModel):
    """Response when testing an alert"""
    alert_id: str
    would_trigger: bool
    current_value: float
    threshold: float
    operator: str
    message: str