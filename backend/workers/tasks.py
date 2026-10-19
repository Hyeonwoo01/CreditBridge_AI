"""오래 걸리는 AI 처리. 작업당 DB 세션 하나."""

import logging

from sqlalchemy.orm import Session

from backend.ai.llm_client import get_llm
from backend.db.session import SessionLocal
from backend.documents.storage import get_storage
from backend.errors import LLMError
from backend.services import analysis, auth, institution_data, notifications, push, reminders
from backend.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _deliver(session: Session) -> None:
    """분석 뒤 자동 배정으로 쌓인 교수 알림을 메일·푸시로도 보낸다 (설정이 없으면 아무것도 하지 않는다)."""
    notifications.deliver_pending(session)
    push.deliver_pending(session)


@celery_app.task(name="syllabus.process")
def process_syllabus(syllabus_id: int) -> None:
    with SessionLocal() as session:
        analysis.process_syllabus(session, syllabus_id, llm=get_llm(), storage=get_storage())
        _deliver(session)


@celery_app.task(name="syllabus.supplement")
def add_supplement(syllabus_id: int, file_key: str) -> None:
    with SessionLocal() as session:
        analysis.add_supplement(session, syllabus_id, file_key, llm=get_llm(), storage=get_storage())
        _deliver(session)


@celery_app.task(name="syllabus.evaluate")
def evaluate_syllabus(syllabus_id: int) -> None:
    with SessionLocal() as session:
        analysis.evaluate_syllabus(session, syllabus_id, llm=get_llm())
        _deliver(session)


@celery_app.task(name="transcript.process")
def process_transcript(request_id: int) -> None:
    with SessionLocal() as session:
        try:
            analysis.process_transcript(session, request_id, llm=get_llm(), storage=get_storage())
        except LLMError as exc:
            logger.warning(
                "transcript processing failed", extra={"request_id": request_id, "error": type(exc).__name__}
            )


@celery_app.task(name="notifications.deliver")
def deliver_notifications() -> None:
    with SessionLocal() as session:
        notifications.deliver_pending(session)
        push.deliver_pending(session)


@celery_app.task(name="reference.process")
def process_reference(syllabus_id: int, course_id: int) -> None:
    with SessionLocal() as session:
        institution_data.process_reference(session, syllabus_id, course_id, llm=get_llm(), storage=get_storage())


@celery_app.task(name="auth.password_reset_email")
def send_password_reset(user_id: int, kind: str = "reset") -> None:
    # 토큰은 작업 안에서 만든다: 작업 큐(Redis)에는 사용자 id와 메일 종류만 지나간다
    with SessionLocal() as session:
        auth.send_reset_email(session, user_id, kind=kind)


@celery_app.task(name="reminders.daily")
def send_daily_reminders() -> None:
    """매일 한 번 (celery beat, Settings.reminder_hour_utc): 기한 알림을 쌓고 메일 설정이 있으면 바로 보낸다."""
    with SessionLocal() as session:
        sent = reminders.send_daily(session)
        logger.info("daily reminders", extra={"notifications": sent})
        notifications.deliver_pending(session)
        push.deliver_pending(session)
