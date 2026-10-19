from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class AuditLog(IdMixin, CreatedAtMixin, Base):
    """주요 행위 기록. 추가 전용(INSERT만). payload에 개인정보를 넣지 않는다."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        # 심사 건 처리 기록·리포트 (계속 쌓이는 테이블이라 대상별로 바로 찾는다)
        Index("ix_audit_logs_target", "target_type", "target_id"),
        # 행위자의 마지막 행위 시각 (예: 비밀번호 재설정 메일 간격)
        Index("ix_audit_logs_actor_action", "actor_id", "action"),
    )

    actor_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50), index=True)
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[str] = mapped_column(String(36))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
