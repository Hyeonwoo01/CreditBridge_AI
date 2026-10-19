from datetime import datetime

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, IdMixin, IdType, utcnow


class Assignment(IdMixin, Base):
    """교수 배정. 대리 재배정 시 reassigned_from에 원래 배정자를 남긴다."""

    __tablename__ = "assignments"
    __table_args__ = (
        # 심사 건의 담당 교수, 교수의 진행 중 배정
        Index("ix_assignments_evaluation_active", "course_evaluation_id", "is_active"),
        Index("ix_assignments_reviewer_active", "reviewer_id", "is_active"),
        # 심사 건당 활성 배정은 하나 (PostgreSQL 조건부 유니크 인덱스)
        Index(
            "uq_assignments_active_evaluation", "course_evaluation_id", unique=True, postgresql_where=text("is_active")
        ),
    )

    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"))
    reviewer_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    assigned_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(default=utcnow)
    reassigned_from: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
