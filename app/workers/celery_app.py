from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "creditbridge", broker=settings.redis_url, backend=settings.redis_url, include=["app.workers.tasks"]
)
celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_expires=3600,
    timezone="UTC",
)
