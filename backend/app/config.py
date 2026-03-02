# backend/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from datetime import timedelta


class Settings(BaseSettings):
    # ----------------------------
    # Security & JWT
    # ----------------------------
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ----------------------------
    # Database
    # ----------------------------
    DATABASE_URL: str                    # async URL (postgresql+asyncpg)
    DATABASE_URL_SYNC: str | None = None
    DB_ECHO: bool = False

    # ----------------------------
    # Redis / Celery
    # ----------------------------
    REDIS_URL: str
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # ----------------------------
    # App Config
    # ----------------------------
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "UTC"

    # ----------------------------
    # Email (optional)
    # ----------------------------
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None

    # ----------------------------
    # Sentry (optional)
    # ----------------------------
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0

    # ----------------------------
    # Pydantic v2 config
    # ----------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

    # ----------------------------
    # Computed / derived fields
    # ----------------------------
    @computed_field
    @property
    def sync_database_url(self) -> str:
        """
        Synchronous DB URL for Alembic and sync SQLAlchemy usage.
        Uses DATABASE_URL_SYNC if explicitly set, otherwise derives it
        from DATABASE_URL by swapping the driver.
        """
        if self.DATABASE_URL_SYNC:
            return self.DATABASE_URL_SYNC
        return self.DATABASE_URL.replace(
            "postgresql+asyncpg://",
            "postgresql://"
        )

    @computed_field
    @property
    def celery_broker(self) -> str:
        """Celery broker URL — falls back to REDIS_URL if not explicitly set."""
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @computed_field
    @property
    def celery_backend(self) -> str:
        """Celery result backend — falls back to REDIS_URL if not explicitly set."""
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @property
    def access_token_expire(self) -> timedelta:
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

    @property
    def refresh_token_expire(self) -> timedelta:
        return timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)


settings = Settings()