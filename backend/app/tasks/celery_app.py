# backend/app/tasks/celery_app.py
"""
Celery application factory.

Broker and result backend are sourced from settings so that:
- Local dev uses REDIS_URL from .env
- Docker uses CELERY_BROKER_URL / CELERY_RESULT_BACKEND from compose env vars
  (which point to the internal Docker service names)

Never hard-code Redis URLs here — always go through settings.
"""
from celery import Celery
from app.config import settings

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

celery_app = Celery(
    "eventpulse",
    broker=settings.celery_broker,          # CELERY_BROKER_URL → fallback REDIS_URL
    backend=settings.celery_backend,        # CELERY_RESULT_BACKEND → fallback REDIS_URL
    include=[
        "app.tasks.tasks_ingest",
        "app.tasks.tasks_aggregates",
        "app.tasks.tasks_alerts",
    ],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

celery_app.conf.update(
    # Timezone
    timezone=settings.TIMEZONE,
    enable_utc=True,

    # Serialization — always JSON, never pickle (safer)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Reliability
    task_acks_late=True,            # ACK only after the task completes (no lost tasks on crash)
    task_reject_on_worker_lost=True,# Re-queue if worker dies mid-task
    worker_prefetch_multiplier=1,   # One task at a time per worker slot — fairer under async load

    # Results
    result_expires=3600,            # Keep task results for 1 hour then auto-delete

    # Broker connection resilience
    broker_connection_retry_on_startup=True,   # Retry connecting to Redis on startup
    broker_connection_retry=True,
    broker_connection_max_retries=10,
)

# ---------------------------------------------------------------------------
# Beat schedule — periodic tasks
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    # Pull events from Redis queue → insert into PostgreSQL (every 5s)
    "process-event-batch": {
        "task": "app.tasks.tasks_ingest.process_event_batch",
        "schedule": 5.0,
        "args": [100],              # batch_size
    },

    # Compute per-minute metrics for all clients (every 60s)
    "compute-minute-aggregates": {
        "task": "app.tasks.tasks_aggregates.compute_minute_aggregates",
        "schedule": 60.0,
    },

    # Compute per-hour metrics for all clients (every 1h)
    "compute-hourly-aggregates": {
        "task": "app.tasks.tasks_aggregates.compute_hourly_aggregates",
        "schedule": 3600.0,
    },

    # Delete aggregates older than 30 days (every 24h)
    "cleanup-old-aggregates": {
        "task": "app.tasks.tasks_aggregates.cleanup_old_aggregates",
        "schedule": 86400.0,
        "kwargs": {"days_to_keep": 30},
    },

    # Evaluate all enabled alerts for all clients (every 60s)
    "evaluate-alerts": {
        "task": "app.tasks.tasks_alerts.evaluate_alerts",
        "schedule": 60.0,
    },
}