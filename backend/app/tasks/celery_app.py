# backend/app/tasks/celery_app.py
from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "eventpulse",
    broker=settings.REDIS_URL,  # Use Redis as message broker
    backend=settings.REDIS_URL,  # Use Redis to store task results
    include=[
        "app.tasks.tasks_ingest",      # Import ingestion task modules
        "app.tasks.tasks_aggregates",  # Import aggregation task modules
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
    
    # Task routing (COMMENTED OUT - causes routing issues with default worker setup)
    # If you need separate queues later, you'll need to start workers for each queue
    # task_routes={
    #     "app.tasks.tasks_ingest.*": {"queue": "ingestion"},
    #     "app.tasks.tasks_aggregates.*": {"queue": "aggregates"},
    # },
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Compute minute-level aggregates every 60 seconds
    "compute-minute-aggregates": {
        "task": "app.tasks.tasks_aggregates.compute_minute_aggregates",
        "schedule": 60.0,  # Every 60 seconds
    },
    
    # Compute hourly aggregates every hour
    "compute-hourly-aggregates": {
        "task": "app.tasks.tasks_aggregates.compute_hourly_aggregates",
        "schedule": 3600.0,  # Every 3600 seconds (1 hour)
    },
    
    # Cleanup old aggregates daily
    "cleanup-old-aggregates": {
        "task": "app.tasks.tasks_aggregates.cleanup_old_aggregates",
        "schedule": 86400.0,  # Every 24 hours
        "kwargs": {"days_to_keep": 30}
    },
    
    "process-event-batch": {
        "task": "app.tasks.tasks_ingest.process_event_batch",
        "schedule": 5.0,  # Every 5 seconds
        "args": [100]
    },
}