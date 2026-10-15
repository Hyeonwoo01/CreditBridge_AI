from datetime import date

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class Equivalency(IdMixin, CreatedAtMixin, Base):
    """기관이 보유한 기존 동등 과목표에서 가져온 판정 이력 (FR-26). 강의계획서가 없어 유사도 비교는 하지 않는다."""

    __tablename__ = "equivalencies"

    target_institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"), index=True)
    source_institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"))
    # decisions.course_key와 같은 정규화 (소문자, 공백 제거)
    source_course_key: Mapped[str] = mapped_column(String(100), index=True)
    source_course_label: Mapped[str] = mapped_column(String(255))
    target_course_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("courses.id"))
    result: Mapped[str] = mapped_column(String(10))
    decided_on: Mapped[date | None] = mapped_column(default=None)
    note: Mapped[str] = mapped_column(Text, default="")
    imported_by: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
