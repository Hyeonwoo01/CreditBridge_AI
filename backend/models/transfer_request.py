from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import RequestStatus
from backend.models.institution import Institution


class TransferRequest(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "transfer_requests"
    __table_args__ = (CheckConstraint(one_of("status", RequestStatus), name="status_valid"),)

    student_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), index=True)
    source_institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"))
    target_institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"), index=True)
    # 편입 전공 (대상 대학 학과명)
    major: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(default=None)
    # 원본 성적표는 객체 스토리지에만, DB에는 키와 마스킹된 값만
    transcript_file_key: Mapped[str | None] = mapped_column(String(255))
    transcript_masked_name: Mapped[str | None] = mapped_column(String(100))
    # 계정 성적표(student_transcripts)의 과목 목록을 이 요청에 복사한 시각. transcript_file_key는 예전에
    # 요청마다 올리던 성적표(이 요청만의 파일)에만 있다
    transcript_copied_at: Mapped[datetime | None] = mapped_column(default=None)
    # 성적표 과목 하나로 자동으로 만든 요청이면 그 과목의 키 (코드, 없으면 과목명). 학생이 직접 만든
    # 예전 요청(여러 과목)은 비어 있다. 성적표를 다시 올려도 같은 과목 요청을 또 만들지 않는다
    course_key: Mapped[str | None] = mapped_column(String(300))
    # 편입 학점 상한을 넘을 때 학생이 졸업 학점에 넣기로 고른 과목인지 (기본 넣음)
    counted: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    source_institution: Mapped[Institution] = relationship(foreign_keys=[source_institution_id], lazy="joined")
    target_institution: Mapped[Institution] = relationship(foreign_keys=[target_institution_id], lazy="joined")
