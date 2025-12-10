# backend/beat.py
"""
Celery beat scheduler startup script.

This runs periodic tasks (we'll use it for aggregates later).

Run with:
    celery -A beat.celery_app beat --loglevel=info
"""
from app.tasks.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start()