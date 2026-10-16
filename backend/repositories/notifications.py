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


def unread_by_kind(session: Session, user_id: int, kinds: list[str]) -> int:
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None), Notification.kind.in_(kinds))
    )
    return int(session.scalar(stmt) or 0)


def mark_read_where(
    session: Session, user_id: int, now: datetime, link: str | None = None, kinds: list[str] | None = None
) -> int:
    stmt = update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
    if link is not None:
        stmt = stmt.where(Notification.link == link)
    if kinds is not None:
        stmt = stmt.where(Notification.kind.in_(kinds))
    return int(session.execute(stmt.values(read_at=now)).rowcount or 0)  # type: ignore[attr-defined]


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
        .where(Notification.emailed_at.is_(None), Notification.created_at >= since, User.is_active.is_(True))
        .order_by(Notification.id)
        .limit(limit)
    )
    return [(n, u) for n, u in session.execute(stmt)]


def sent_since(session: Session, user_id: int, kind: str, since: datetime) -> bool:
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.kind == kind, Notification.created_at >= since)
    )
    return bool(session.scalar(stmt))
