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
    # Fair scheduling: worker takes 1 task at a time
    worker_prefetch_multiplier=1,
    # Queue routing: heavy tasks go to separate queue
    task_default_queue="default",
    task_routes={
        "app.worker.tasks.cluster_projects_task": {"queue": "heavy"},
        "app.worker.tasks.run_matching_task": {"queue": "heavy"},
    },
)
