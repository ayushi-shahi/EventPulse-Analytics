# backend/app/beat_health.py
from celery import Celery
import sys

celery_app = Celery("beat", broker="redis://eventpulse_redis:6379/0")

try:
    response = celery_app.control.ping(timeout=1)
    if response:
        sys.exit(0)  # healthy
    else:
        sys.exit(1)  # unhealthy
except Exception:
    sys.exit(1)
