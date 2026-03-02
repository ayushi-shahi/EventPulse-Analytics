# backend/app/database.py
"""
Database engine and session factory.

Base is imported from app.models.base — the single source of truth.
All models register against that Base, so Alembic and the ORM
always see the same metadata.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.base import Base          # single Base — shared with all models
from app.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,       # test connections before handing them out
    pool_recycle=3600,        # recycle connections every hour
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_db():
    """
    Yield an AsyncSession for use in FastAPI route dependencies.
    Commits on success, rolls back on any exception, always closes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Re-export Base so any legacy import of `from app.database import Base`
# still works without pointing at a second, orphaned metadata object.
__all__ = ["engine", "AsyncSessionLocal", "get_db", "Base"]