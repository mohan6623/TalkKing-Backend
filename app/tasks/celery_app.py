"""Celery application configuration for TalkKing background task processing."""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "talkking",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.analysis"],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Result expiry (1 hour)
    result_expires=3600,

    # Task routing
    task_default_queue="default",

    # Memory management
    worker_max_tasks_per_child=100,
)
