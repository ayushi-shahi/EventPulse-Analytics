# backend/app/models/user.py
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    User model for platform authentication.
    These are the admins/users who manage the platform, not end-user events.
    """
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        nullable=False
    )
    
    email = Column(
        String(255), 
        unique=True, 
        nullable=False,
        index=True
    )
    
    hashed_password = Column(
        String(255), 
        nullable=False
    )
    
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False
    )
    
    role = Column(
        String(20), 
        default='user',
        nullable=False
    )
    
    # Relationship is defined in APIKey model with backref
    # So user.api_keys will work automatically

    def __repr__(self):
        return f"<User {self.email}>"