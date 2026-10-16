from celery import Celery
from celery.schedules import crontab

from backend.config import get_settings

settings = get_settings()

celery_app = Celery(
    "creditbridge", broker=settings.redis_url, backend=settings.redis_url, include=["backend.workers.tasks"]
)
celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_expires=3600,
    timezone="UTC",
    # 기한 알림: 매일 한 번. beat 프로세스가 하나만 떠 있어야 한다 (docker compose의 beat 서비스)
    beat_schedule={
        "daily-reminders": {
            "task": "reminders.daily",
            "schedule": crontab(minute=0, hour=settings.reminder_hour_utc),
        }
    },
)
