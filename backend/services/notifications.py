"""화면 알림과 알림 메일 (FR-19 대리 재배정 알림, FR-20 교수 알림, FR-22·23 학생 알림).

알림 메시지에는 과목 코드와 처리 내용만 넣고 이름·학번·성적은 넣지 않는다.
메일은 SMTP 설정이 있을 때만 작업 큐(notifications.deliver)가 보낸다.
"""

import logging
import smtplib
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from email.message import EmailMessage

from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.db.base import utcnow
from backend.i18n import translate_stored, use_locale
from backend.models import Notification, User
from backend.models.enums import Role
from backend.repositories import notifications as notification_repo
from backend.repositories import users as user_repo

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


# 학생 메뉴 배지: 판정 결과(내 편입 요청)와 이의 신청 처리 결과(이의 신청)
RESULT_KINDS = ["decision.created"]
APPEAL_RESULT_KINDS = ["appeal.accepted", "appeal.dismissed", "decision.redecided"]


def unread_of_kinds(session: Session, user: User, kinds: list[str]) -> int:
    return notification_repo.unread_by_kind(session, user.id, kinds)


def mark_seen(session: Session, user: User, link: str | None = None, kinds: list[str] | None = None) -> None:
    """알림이 가리키는 화면을 직접 열었으면 그 알림은 읽은 것으로 본다."""
    if notification_repo.mark_read_where(session, user.id, utcnow(), link=link, kinds=kinds):
        session.commit()


def inbox(session: Session, user: User) -> list[Notification]:
    """최근 알림을 돌려주고 모두 읽음으로 표시한다."""
    items = notification_repo.recent_for(session, user.id)
    notification_repo.mark_read(session, user.id, utcnow())
    session.commit()
    return items


def email_enabled(settings: Settings | None = None) -> bool:
    return bool((settings or get_settings()).smtp_host)


@contextmanager
def _smtp(settings: Settings) -> Iterator[smtplib.SMTP]:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        yield smtp


def send_email(to: str, subject: str, body: str, settings: Settings | None = None) -> bool:
    """알림함에 남기지 않는 메일 한 통 (비밀번호 재설정 링크처럼 DB에 저장하면 안 되는 내용). 보냈으면 True."""
    settings = settings or get_settings()
    if not email_enabled(settings):
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(body)
    try:
        with _smtp(settings) as smtp:
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("email failed", extra={"error": type(exc).__name__})
        return False
    return True


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
    with _smtp(settings) as smtp:
        for notification, user in pending:
            # 알림은 한국어 원문으로 저장돼 있다: 받는 사람의 언어로 바꿔 보낸다
            with use_locale(user.locale):
                text = translate_stored(notification.message)
            msg = EmailMessage()
            msg["Subject"] = "[CreditBridge] " + text[:80]
            msg["From"] = settings.smtp_from
            msg["To"] = user.email
            link = f"\n\n{settings.app_base_url.rstrip('/')}{notification.link}" if notification.link else ""
            msg.set_content(text + link)
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
