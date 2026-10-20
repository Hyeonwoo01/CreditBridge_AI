from celery import Celery
from celery.schedules import crontab

from backend.config import get_settings

settings = get_settings()

# 작업 하나의 시간 제한 (AI 호출 재시도 포함). 부드러운 제한을 넘으면 실패로 표시하고 다시 올리게 안내한다
TASK_SOFT_LIMIT = 8 * 60
TASK_HARD_LIMIT = 10 * 60
# worker가 작업 도중 강제로 죽으면(서버 재부팅·메모리 부족) Redis가 이 시간 뒤 작업을 다시 넘긴다 (기본 1시간).
# 가장 긴 작업(TASK_HARD_LIMIT)보다 길어야 살아 있는 작업이 두 번 돌지 않는다
VISIBILITY_TIMEOUT = 15 * 60
# 정상 종료(SIGQUIT: docker compose의 stop_signal)면 이만큼 기다린 뒤, 끝나지 않은 작업을 바로 대기열로 돌려놓고 끝낸다
SOFT_SHUTDOWN_SECONDS = 20

celery_app = Celery(
    "creditbridge", broker=settings.redis_url, backend=settings.redis_url, include=["backend.workers.tasks"]
)
celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=TASK_SOFT_LIMIT,
    task_time_limit=TASK_HARD_LIMIT,
    broker_transport_options={"visibility_timeout": VISIBILITY_TIMEOUT},
    result_backend_transport_options={"visibility_timeout": VISIBILITY_TIMEOUT},
    worker_soft_shutdown_timeout=SOFT_SHUTDOWN_SECONDS,
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
