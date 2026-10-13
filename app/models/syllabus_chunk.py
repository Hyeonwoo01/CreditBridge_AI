from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.db.base import Base, IdMixin, IdType
from app.db.types import Vector


class SyllabusChunk(IdMixin, Base):
    """주차·개념 단위 텍스트와 bge-m3 임베딩."""

    __tablename__ = "syllabus_chunks"

    syllabus_id: Mapped[int] = mapped_column(IdType, ForeignKey("syllabi.id", ondelete="CASCADE"), index=True)
    week_no: Mapped[int | None] = mapped_column(default=None)
    concept: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    char_start: Mapped[int | None] = mapped_column(default=None)
    char_end: Mapped[int | None] = mapped_column(default=None)
    embedding: Mapped[list[float]] = mapped_column(Vector(get_settings().embedding_dim))
