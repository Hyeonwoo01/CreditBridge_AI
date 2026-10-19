"""audit_logs는 추가 전용 테이블: INSERT와 SELECT만 둔다."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import AuditLog, User


def add(
    session: Session, actor_id: int | None, action: str, target_type: str, target_id: str, payload: dict[str, Any]
) -> None:
    session.add(
        AuditLog(actor_id=actor_id, action=action, target_type=target_type, target_id=target_id, payload_json=payload)
    )
    session.flush()


def recent_for_institution(
    session: Session, institution_id: int, limit: int = 200, exclude_actions: tuple[str, ...] = ()
) -> list[AuditLog]:
    """그 기관 사용자가 남긴 최근 기록 (행위자가 없는 기록과 다른 기관의 기록은 빠진다)."""
    stmt = (
        select(AuditLog)
        .join(User, User.id == AuditLog.actor_id)
        .where(User.institution_id == institution_id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
    )
    if exclude_actions:
        stmt = stmt.where(AuditLog.action.not_in(exclude_actions))
    return list(session.scalars(stmt))


def for_target(session: Session, target_type: str, target_id: str) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.target_type == target_type, AuditLog.target_id == target_id)
        .order_by(AuditLog.id)
    )
    return list(session.scalars(stmt))


def last_at(session: Session, actor_id: int, action: str) -> datetime | None:
    stmt = select(func.max(AuditLog.created_at)).where(AuditLog.actor_id == actor_id, AuditLog.action == action)
    return session.scalar(stmt)


def search(
    session: Session,
    institution_id: int,
    action: str = "",
    target_type: str = "",
    target_id: str = "",
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """감사 로그 화면: 그 기관 사용자가 남긴 기록을 조건으로 거른다 (최신순). (행, 전체 건수)."""
    conditions = [User.institution_id == institution_id]
    if action:
        conditions.append(AuditLog.action == action)
    if target_type:
        conditions.append(AuditLog.target_type == target_type)
    if target_id:
        conditions.append(AuditLog.target_id == target_id)
    if since is not None:
        conditions.append(AuditLog.created_at >= since)
    if until is not None:
        conditions.append(AuditLog.created_at < until)
    base = select(AuditLog).join(User, User.id == AuditLog.actor_id).where(*conditions)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(AuditLog.id.desc()).limit(limit).offset(offset)
    return list(session.scalars(stmt)), total


def facets(session: Session, institution_id: int) -> tuple[list[str], list[str]]:
    """필터 선택지: 그 기관 기록에 나온 행위와 대상 종류."""
    joined = select(AuditLog).join(User, User.id == AuditLog.actor_id).where(User.institution_id == institution_id)
    sub = joined.subquery()
    actions = list(session.scalars(select(sub.c.action).distinct().order_by(sub.c.action)))
    targets = list(session.scalars(select(sub.c.target_type).distinct().order_by(sub.c.target_type)))
    return actions, targets
