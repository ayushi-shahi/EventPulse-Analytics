# backend/app/models/alert.py
from sqlalchemy import Column, String, Boolean, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from datetime import datetime, timezone
from app.models.base import Base, TimestampMixin
import uuid



class Alert(Base, TimestampMixin):
    """
    Alert definitions and configuration.
    
    Alerts monitor metrics and trigger notifications when conditions are met.
    Examples:
    - Events per minute > 1000
    - Active users < 10
    - Error rate > 5%
    """
    __tablename__ = "alerts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Which client this alert belongs to
    client_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Alert name (user-friendly)
    name = Column(
        String(255),
        nullable=False
    )
    
    # Description (optional)
    description = Column(
        String(1000),
        nullable=True
    )
    
    # Alert expression/condition as JSON
    # Example: {"metric": "events_per_minute", "operator": ">", "threshold": 1000}
    expression = Column(
        JSONB,
        nullable=False
    )
    
    # Severity level: info, warning, error, critical
    severity = Column(
        String(20),
        nullable=False,
        default='info'
    )
    
    # Is this alert enabled?
    enabled = Column(
        Boolean,
        nullable=False,
        default=True
    )
    
    # Last time this alert was triggered
    last_triggered = Column(
        TIMESTAMP(timezone=True),
        nullable=True
    )
    
    # How many times triggered (counter)
    trigger_count = Column(
        Integer,
        nullable=False,
        default=0
    )
    
    # Notification channels as JSON
    # Example: {"websocket": true, "email": ["admin@example.com"]}
    notification_channels = Column(
        JSONB,
        nullable=True,
        default={"websocket": True}
    )
    
    # Cooldown period in seconds (prevent spam)
    cooldown_seconds = Column(
        Integer,
        nullable=False,
        default=300  # 5 minutes default
    )
    
    # Composite indexes
    __table_args__ = (
        Index('idx_client_enabled', 'client_id', 'enabled'),
    )

    def __repr__(self):
        return f"<Alert {self.name}>"


class AlertHistory(Base, TimestampMixin):
    """
    History of alert triggers.
    
    Stores when alerts fired and what values triggered them.
    """
    __tablename__ = "alert_history"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Which alert triggered
    alert_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Which client
    client_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # When it triggered
    triggered_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    # Severity at time of trigger
    severity = Column(
        String(20),
        nullable=False
    )
    
    # Alert message
    message = Column(
        String(1000),
        nullable=False
    )
    
    # Context data (metric values, etc.)
    context = Column(
        JSONB,
        nullable=True
    )
    
    # Was notification sent successfully?
    notification_sent = Column(
        Boolean,
        nullable=False,
        default=False
    )
    
    # Composite indexes
    __table_args__ = (
        Index('idx_alert_time', 'alert_id', 'triggered_at'),
        Index('idx_client_time', 'client_id', 'triggered_at'),
    )

    def __repr__(self):
        return f"<AlertHistory {self.triggered_at}>"