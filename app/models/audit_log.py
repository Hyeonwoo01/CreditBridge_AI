from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin, IdType


class AuditLog(IdMixin, CreatedAtMixin, Base):
    """주요 행위 기록. 추가 전용(INSERT만). payload에 개인정보를 넣지 않는다."""

    __tablename__ = "audit_logs"

    actor_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[str] = mapped_column(String(36))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
