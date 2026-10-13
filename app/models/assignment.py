from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, IdType, utcnow


class Assignment(IdMixin, Base):
    """교수 배정. 대리 재배정 시 reassigned_from에 원래 배정자를 남긴다."""

    __tablename__ = "assignments"

    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), index=True)
    assigned_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(default=utcnow)
    reassigned_from: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
