"""화면 알림과 알림 메일 (FR-19 대리 재배정 알림, FR-20 교수 알림, FR-22·23 학생 알림).

알림 메시지에는 과목 코드와 처리 내용만 넣고 이름·학번·성적은 넣지 않는다.
메일은 SMTP 설정이 있을 때만 작업 큐(notifications.deliver)가 보낸다.
"""

import logging
import smtplib
from datetime import timedelta
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.base import utcnow
from app.models import Notification, User
from app.models.enums import Role
from app.repositories import notifications as notification_repo
from app.repositories import users as user_repo

logger = logging.getLogger(__name__)


def notify(session: Session, users: list[User], kind: str, message: str, link: str = "") -> None:
    """알림을 쌓는다. 커밋은 호출한 서비스가 한다."""
    seen: set[int] = set()
    rows = []
    for user in users:
        if user.id in seen:
            continue
        seen.add(user.id)
        rows.append(Notification(user_id=user.id, kind=kind, message=message[:500], link=link[:255]))
    notification_repo.add_many(session, rows)


def staff(session: Session, institution_id: int, role: Role) -> list[User]:
    return user_repo.staff_of(session, institution_id, role)


def unread_count(session: Session, user: User) -> int:
    return notification_repo.unread_count(session, user.id)


def inbox(session: Session, user: User) -> list[Notification]:
    """최근 알림을 돌려주고 모두 읽음으로 표시한다."""
    items = notification_repo.recent_for(session, user.id)
    notification_repo.mark_read(session, user.id, utcnow())
    session.commit()
    return items


def email_enabled(settings: Settings | None = None) -> bool:
    return bool((settings or get_settings()).smtp_host)


def deliver_pending(session: Session, settings: Settings | None = None) -> int:
    """아직 메일로 보내지 않은 알림을 보낸다. SMTP 설정이 없으면 아무것도 하지 않는다."""
    settings = settings or get_settings()
    if not email_enabled(settings):
        return 0
    # 메일 설정을 나중에 켜도 오래된 알림이 한꺼번에 나가지 않게 최근 하루치만 보낸다
    pending = notification_repo.pending_email(session, since=utcnow() - timedelta(days=1))
    if not pending:
        return 0
    sent = 0
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        for notification, user in pending:
            msg = EmailMessage()
            msg["Subject"] = "[CreditBridge] " + notification.message[:80]
            msg["From"] = settings.smtp_from
            msg["To"] = user.email
            link = f"\n\n{settings.app_base_url.rstrip('/')}{notification.link}" if notification.link else ""
            msg.set_content(notification.message + link)
            try:
                smtp.send_message(msg)
            except smtplib.SMTPException as exc:
                logger.warning(
                    "notification email failed", extra={"notification_id": notification.id, "error": type(exc).__name__}
                )
                continue
            notification.emailed_at = utcnow()
            sent += 1
    session.commit()
    return sent
