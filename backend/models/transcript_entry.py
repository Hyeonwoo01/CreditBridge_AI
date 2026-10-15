from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class TranscriptEntry(IdMixin, CreatedAtMixin, Base):
    """성적표에서 추출한 과목 한 줄과 연결된 강의계획서 (FR-02)."""

    __tablename__ = "transcript_entries"

    transfer_request_id: Mapped[int] = mapped_column(IdType, ForeignKey("transfer_requests.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    code: Mapped[str | None] = mapped_column(String(50))
    credits: Mapped[float | None] = mapped_column(Numeric(4, 1, asdecimal=False))
    grade: Mapped[str | None] = mapped_column(String(10))
    term: Mapped[str | None] = mapped_column(String(50))
    syllabus_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("syllabi.id"))
    link_score: Mapped[float | None] = mapped_column(Numeric(4, 3, asdecimal=False))
    # 자동 연결이 불확실하면 학생 확인 필요
    link_confirmed: Mapped[bool] = mapped_column(default=False)
