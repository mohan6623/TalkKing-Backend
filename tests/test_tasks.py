"""Tests for Celery app configuration and process_recording task."""
from app.tasks.celery_app import celery_app


def test_celery_app_name():
    """Celery app should be named 'talkking'."""
    assert celery_app.main == "talkking"


def test_celery_broker_configured():
    """Celery broker should point to Redis."""
    assert "redis" in celery_app.conf.broker_url


def test_celery_task_registered():
    """The process_recording task should be discoverable."""
    # Force task discovery
    from app.tasks import analysis  # noqa: F401
    task_names = list(celery_app.tasks.keys())
    matching = [t for t in task_names if "process_recording" in t]
    assert len(matching) >= 1


def test_celery_task_config():
    """Task should have retry and timeout settings."""
    from app.tasks.analysis import process_recording
    assert process_recording.max_retries == 2
    assert process_recording.soft_time_limit == 120
