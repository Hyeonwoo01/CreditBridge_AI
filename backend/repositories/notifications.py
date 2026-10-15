from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.models import Notification, User


def add_many(session: Session, notifications: list[Notification]) -> None:
    session.add_all(notifications)
    session.flush()


def unread_count(session: Session, user_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
    )
    return int(session.scalar(stmt) or 0)


def recent_for(session: Session, user_id: int, limit: int = 50) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id).order_by(Notification.id.desc()).limit(limit)
    return list(session.scalars(stmt))


def mark_read(session: Session, user_id: int, now: datetime) -> None:
    session.execute(
        update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None)).values(read_at=now)
    )


def pending_email(session: Session, since: datetime, limit: int = 100) -> list[tuple[Notification, User]]:
    stmt = (
        select(Notification, User)
        .join(User, User.id == Notification.user_id)
        .where(Notification.emailed_at.is_(None), Notification.created_at >= since)
        .order_by(Notification.id)
        .limit(limit)
    )
    return [(n, u) for n, u in session.execute(stmt)]
