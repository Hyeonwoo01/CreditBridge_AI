from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, IdType


class EvidenceSpan(IdMixin, Base):
    """근거 구절의 원문 위치. 원문 문자열 검증을 통과한 구절만 저장한다."""

    __tablename__ = "evidence_spans"

    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"), index=True)
    side: Mapped[str] = mapped_column(String(10))
    syllabus_id: Mapped[int] = mapped_column(IdType, ForeignKey("syllabi.id"))
    char_start: Mapped[int]
    char_end: Mapped[int]
    concept: Mapped[str] = mapped_column(String(255))
    verified: Mapped[bool] = mapped_column(Boolean, default=True)
