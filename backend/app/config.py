# backend/app/config.py
from pydantic_settings import BaseSettings
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
    DATABASE_URL: str                   # async URL (postgresql+asyncpg)
    DATABASE_URL_SYNC: str | None = None   # <-- ADD THIS
    DB_ECHO: bool = False

    # ----------------------------
    # Redis (Caching & Celery)
    # ----------------------------
    REDIS_URL: str
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # ----------------------------
    # WebSockets (optional)
    # ----------------------------
    WS_HOST: str | None = None
    WS_PORT: int | None = None

    # ----------------------------
    # App Config
    # ----------------------------
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "UTC"
    
    # Monitoring & Observability
    # ----------------------------
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # 10% of transactions

    # ----------------------------
    # Email / Notifications
    # ----------------------------
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None

    # ----------------------------
    # Optional Analytics / ML / Extra Features
    # ----------------------------
    ELASTICSEARCH_URL: str | None = None
    ML_MODEL_PATH: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def access_token_expire(self) -> timedelta:
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

    @property
    def refresh_token_expire(self) -> timedelta:
        return timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)


settings = Settings()

# ----------------------------
# Generate SYNC DB URL automatically if missing
# ----------------------------
if settings.DATABASE_URL_SYNC is None:
    settings.DATABASE_URL_SYNC = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://",
        "postgresql://"
    )
