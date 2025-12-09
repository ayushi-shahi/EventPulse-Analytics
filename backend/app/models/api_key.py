# backend/app/models/api_key.py
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base, TimestampMixin


class APIKey(Base, TimestampMixin):
    """
    API keys for client applications to ingest events.
    Each key belongs to a user and has rate limiting.
    """
    __tablename__ = "api_keys"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    client_name = Column(
        String(255),
        nullable=False
    )  # Friendly name like "Mobile App", "Website"
    
    key_hash = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True
    )  # Hashed API key (never store plain)
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )  # Owner of this API key
    
    rate_limit = Column(
        Integer,
        default=1000,
        nullable=False
    )  # Requests per minute
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )  # Can be revoked
    
    # Relationship to user
    user = relationship("User", backref="api_keys")
    
    def __repr__(self):
        return f"<APIKey {self.client_name}>"