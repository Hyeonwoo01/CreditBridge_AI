from datetime import datetime

from sqlalchemy import CheckConstraint, Computed, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import AppealStatus


class Appeal(IdMixin, CreatedAtMixin, Base):
    """학생 이의 신청 (FR-23). 심사관이 접수·처리하고, 받아들이면 교수가 재판정한다."""

    __tablename__ = "appeals"
    __table_args__ = (CheckConstraint(one_of("status", AppealStatus), name="status_valid"),)

    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"), index=True)
    decision_id: Mapped[int] = mapped_column(IdType, ForeignKey("decisions.id"))
    student_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="submitted", index=True)
    handled_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    handler_note: Mapped[str] = mapped_column(Text, default="")
    handled_at: Mapped[datetime | None] = mapped_column(default=None)
    # 심사 건당 처리 중(접수·수용) 이의 신청은 하나 (assignments.active_evaluation_id와 같은 방식)
    open_evaluation_id: Mapped[int | None] = mapped_column(
        IdType,
        Computed("IF(status IN ('submitted', 'accepted'), course_evaluation_id, NULL)", persisted=True),
        unique=True,
    )
