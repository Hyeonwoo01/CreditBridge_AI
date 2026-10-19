from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.models import Notification, PushSubscription, User


def by_endpoint(session: Session, endpoint: str) -> PushSubscription | None:
    return session.scalars(select(PushSubscription).where(PushSubscription.endpoint == endpoint)).first()


def add(session: Session, subscription: PushSubscription) -> PushSubscription:
    session.add(subscription)
    session.flush()
    return subscription


def remove(session: Session, user_id: int, endpoint: str) -> int:
    stmt = delete(PushSubscription).where(PushSubscription.user_id == user_id, PushSubscription.endpoint == endpoint)
    return int(session.execute(stmt).rowcount or 0)  # type: ignore[attr-defined]


def remove_by_id(session: Session, subscription_id: int) -> None:
    session.execute(delete(PushSubscription).where(PushSubscription.id == subscription_id))


def count_for(session: Session, user_id: int) -> int:
    stmt = select(func.count()).select_from(PushSubscription).where(PushSubscription.user_id == user_id)
    return int(session.scalar(stmt) or 0)


def pending(
    session: Session, since: datetime, limit: int = 200
) -> list[tuple[Notification, User, list[PushSubscription]]]:
    """아직 푸시하지 않은 최근 알림과 받을 기기. 알림보다 나중에 구독한 기기에는 보내지 않는다."""
    stmt = (
        select(Notification, User)
        .join(User, User.id == Notification.user_id)
        .where(
            Notification.pushed_at.is_(None),
            Notification.created_at >= since,
            User.is_active.is_(True),
            select(PushSubscription.id)
            .where(
                PushSubscription.user_id == Notification.user_id,
                PushSubscription.created_at <= Notification.created_at,
            )
            .exists(),
        )
        .order_by(Notification.id)
        .limit(limit)
    )
    rows = list(session.execute(stmt))
    user_ids = {n.user_id for n, _ in rows}
    subscriptions: dict[int, list[PushSubscription]] = {}
    if user_ids:
        for s in session.scalars(select(PushSubscription).where(PushSubscription.user_id.in_(user_ids))):
            subscriptions.setdefault(s.user_id, []).append(s)
    return [(n, u, [s for s in subscriptions.get(n.user_id, []) if s.created_at <= n.created_at]) for n, u in rows]
