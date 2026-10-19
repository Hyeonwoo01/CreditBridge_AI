from datetime import datetime

from sqlalchemy import Computed, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, IdMixin, IdType, utcnow


class Assignment(IdMixin, Base):
    """교수 배정. 대리 재배정 시 reassigned_from에 원래 배정자를 남긴다."""

    __tablename__ = "assignments"
    __table_args__ = (
        # 심사 건의 담당 교수, 교수의 진행 중 배정
        Index("ix_assignments_evaluation_active", "course_evaluation_id", "is_active"),
        Index("ix_assignments_reviewer_active", "reviewer_id", "is_active"),
    )

    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"))
    reviewer_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    assigned_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(default=utcnow)
    reassigned_from: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    # 심사 건당 활성 배정은 하나. MariaDB·MySQL에는 조건부 유니크 인덱스가 없어
    # 생성 컬럼에 UNIQUE를 건다 (NULL은 겹쳐도 된다)
    active_evaluation_id: Mapped[int | None] = mapped_column(
        IdType, Computed("IF(is_active, course_evaluation_id, NULL)", persisted=True), unique=True
    )
