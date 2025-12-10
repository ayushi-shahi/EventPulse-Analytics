# backend/app/tasks/celery_app.py
from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "eventpulse",
    broker=settings.REDIS_URL,  # Use Redis as message broker
    backend=settings.REDIS_URL,  # Use Redis to store task results
    include=[
        "app.tasks.tasks_ingest",  # Import our task modules
    ]
)

# Celery configuration
celery_app.conf.update(
    # Timezone
    timezone=settings.TIMEZONE,
    enable_utc=True,
    
    # Task settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # Performance settings
    task_acks_late=True,  # Acknowledge tasks after completion (safer)
    worker_prefetch_multiplier=4,  # How many tasks to prefetch
    
    # Results
    result_expires=3600,  # Results expire after 1 hour
    
    # Task routing (we'll add more later)
    # task_routes={
    #     "app.tasks.tasks_ingest.*": {"queue": "ingestion"},
    # },
)

# Optional: Beat schedule for periodic tasks (we'll use this later for aggregates)
celery_app.conf.beat_schedule = {
    # Example: run every minute
    # "compute-aggregates": {
    #     "task": "app.tasks.tasks_aggregates.compute_minute_aggregates",
    #     "schedule": 60.0,  # Every 60 seconds
    # },
}