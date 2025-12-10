# backend/app/models/event.py
from sqlalchemy import Column, String, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from datetime import datetime, timezone
from app.models.base import Base


class Event(Base):
    """
    Raw events ingested from client applications.
    
    This table is write-heavy and append-only.
    We'll partition it by time later if it grows large.
    """
    __tablename__ = "events"

    # Use BIGSERIAL for high-volume auto-increment
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )
    
    # Which client sent this event (links to api_keys.id)
    client_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True  # We query by client_id frequently
    )
    
    # Optional: end-user identifier from the client app
    user_id = Column(
        String(255),
        nullable=True,
        index=True  # For user-level analytics
    )
    
    # Event name/type (e.g., "page_view", "button_click", "purchase")
    event_name = Column(
        String(255),
        nullable=False,
        index=True  # We filter by event_name often
    )
    
    # Flexible JSON properties (any additional data)
    properties = Column(
        JSONB,
        nullable=True
    )
    
    # When the event actually occurred (client-provided)
    event_time = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True  # Time-range queries
    )
    
    # When we received it (server timestamp)
    received_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    # Composite indexes for common query patterns
    __table_args__ = (
        # Query by client + time range
        Index('idx_client_event_time', 'client_id', 'event_time'),
        # Query by client + event name + time
        Index('idx_client_event_name_time', 'client_id', 'event_name', 'event_time'),
    )

    def __repr__(self):
        return f"<Event {self.event_name} @ {self.event_time}>"