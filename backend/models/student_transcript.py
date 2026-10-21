from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.db.types import JSONB
from backend.models.enums import TranscriptStatus


class StudentTranscript(IdMixin, CreatedAtMixin, Base):
    """학생 계정의 성적표 (학생당 하나). 처음 들어오면 먼저 올리고, 편입 요청을 만들거나 바꿔 올리면
    아직 제출하지 않은 요청에 과목 목록(transcript_entries)을 복사한다. 제출한 요청은 그때의 목록으로 고정된다.

    요청 문서 삭제는 그 요청의 사본만 지우고 계정 성적표는 남긴다."""

    __tablename__ = "student_transcripts"
    __table_args__ = (CheckConstraint(one_of("status", TranscriptStatus), name="status_valid"),)

    student_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), unique=True)
    # 원본은 객체 스토리지에만, DB에는 키와 마스킹된 이름, 추출한 과목 줄(과목명·코드·학점·성적·학기)만
    file_key: Mapped[str | None] = mapped_column(String(255))
    masked_name: Mapped[str | None] = mapped_column(String(100))
    lines: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    status: Mapped[str] = mapped_column(String(20), default=TranscriptStatus.PROCESSING)
    error_message: Mapped[str | None] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column()
