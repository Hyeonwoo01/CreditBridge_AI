from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, IdMixin, IdType


class SyllabusChunk(IdMixin, Base):
    """주차·개념 단위 텍스트와 원문 위치. (임베딩은 파일럿에서 추가)"""

    __tablename__ = "syllabus_chunks"
    __table_args__ = (
        CheckConstraint(
            "char_start IS NULL OR char_end IS NULL OR (char_start >= 0 AND char_start <= char_end)", name="span_range"
        ),
    )

    syllabus_id: Mapped[int] = mapped_column(IdType, ForeignKey("syllabi.id", ondelete="CASCADE"), index=True)
    week_no: Mapped[int | None] = mapped_column(default=None)
    concept: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    char_start: Mapped[int | None] = mapped_column(default=None)
    char_end: Mapped[int | None] = mapped_column(default=None)
