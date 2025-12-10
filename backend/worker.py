# backend/worker.py
"""
Celery worker startup script.

Run with:
    celery -A worker.celery_app worker --loglevel=info --pool=solo

For Windows, use --pool=solo
For Linux/Mac, you can use --pool=prefork for better performance
"""
from app.tasks.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start()