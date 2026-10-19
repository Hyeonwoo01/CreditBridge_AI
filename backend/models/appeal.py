from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import AppealStatus


class Appeal(IdMixin, CreatedAtMixin, Base):
    """학생 이의 신청 (FR-23). 심사관이 접수·처리하고, 받아들이면 교수가 재판정한다."""

    __tablename__ = "appeals"
    __table_args__ = (
        CheckConstraint(one_of("status", AppealStatus), name="status_valid"),
        # 심사 건당 처리 중(접수·수용) 이의 신청은 하나 (조건부 유니크 인덱스)
        Index(
            "uq_appeals_open_evaluation",
            "course_evaluation_id",
            unique=True,
            postgresql_where=text("status IN ('submitted', 'accepted')"),
        ),
    )

    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"), index=True)
    decision_id: Mapped[int] = mapped_column(IdType, ForeignKey("decisions.id"))
    student_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="submitted", index=True)
    handled_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    handler_note: Mapped[str] = mapped_column(Text, default="")
    handled_at: Mapped[datetime | None] = mapped_column(default=None)
