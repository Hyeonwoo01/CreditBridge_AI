"""audit_logs는 추가 전용 테이블: INSERT와 SELECT만 둔다."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AuditLog


def add(
    session: Session, actor_id: int | None, action: str, target_type: str, target_id: str, payload: dict[str, Any]
) -> None:
    session.add(
        AuditLog(actor_id=actor_id, action=action, target_type=target_type, target_id=target_id, payload_json=payload)
    )
    session.flush()


def recent(session: Session, limit: int = 200) -> list[AuditLog]:
    return list(session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)))


def for_target(session: Session, target_type: str, target_id: str) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.target_type == target_type, AuditLog.target_id == target_id)
        .order_by(AuditLog.id)
    )
    return list(session.scalars(stmt))
