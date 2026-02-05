"""Celery application configuration."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "demoday_worker",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    task_track_started=True,
    task_time_limit=300,  # 5 min max
    task_soft_time_limit=240,  # Soft limit for graceful shutdown
    broker_connection_retry_on_startup=True,
)
