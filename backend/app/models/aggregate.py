# backend/app/models/aggregate.py
from sqlalchemy import Column, String, Float, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from app.models.base import Base, TimestampMixin


class Aggregate(Base, TimestampMixin):
    """
    Precomputed aggregate metrics.
    
    Stores metrics like:
    - events_per_minute
    - active_users_1h
    - top_events
    - error_rate
    
    Computed periodically by background tasks.
    """
    __tablename__ = "aggregates"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),  # ← Changed: wrap in text()
        nullable=False
    )
    
    # Which client this metric belongs to
    client_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Metric name (e.g., "events_per_minute", "active_users_1h")
    metric_name = Column(
        String(255),
        nullable=False,
        index=True
    )
    
    # Time interval this metric covers
    interval_start = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True
    )
    
    interval_end = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True
    )
    
    # The computed value
    value = Column(
        Float,
        nullable=True
    )
    
    # Additional metadata (e.g., breakdown by event type)
    meta_data = Column(
        JSONB,
        nullable=True
    )
    
    # Composite indexes for efficient queries
    __table_args__ = (
        # Unique constraint: one metric per client per time interval
        UniqueConstraint(
            'client_id', 
            'metric_name', 
            'interval_start',
            name='uq_client_metric_interval'
        ),
        # Query by client + metric + time range
        Index(
            'idx_client_metric_time',
            'client_id',
            'metric_name',
            'interval_start'
        ),
    )

    def __repr__(self):
        return f"<Aggregate {self.metric_name} @ {self.interval_start}>"