from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import MaterialRequestStatus


class MaterialRequest(IdMixin, CreatedAtMixin, Base):
    """심사관·교수가 학생에게 보내는 보완 자료 요청 (FR-22)."""

    __tablename__ = "material_requests"
    __table_args__ = (CheckConstraint(one_of("status", MaterialRequestStatus), name="status_valid"),)

    syllabus_id: Mapped[int] = mapped_column(IdType, ForeignKey("syllabi.id"), index=True)
    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"))
    requested_by: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    items: Mapped[list[str]] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(default=None)
