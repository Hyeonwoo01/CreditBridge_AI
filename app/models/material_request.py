from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin, IdType


class MaterialRequest(IdMixin, CreatedAtMixin, Base):
    """심사관·교수가 학생에게 보내는 보완 자료 요청 (FR-22)."""

    __tablename__ = "material_requests"

    syllabus_id: Mapped[int] = mapped_column(IdType, ForeignKey("syllabi.id"), index=True)
    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"))
    requested_by: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    items: Mapped[list[str]] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(default=None)
