# backend/app/models/__init__.py
from app.models.base import Base
from app.models.user import User

# Export all models here as we create them
__all__ = ["Base", "User"]