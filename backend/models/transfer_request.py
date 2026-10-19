from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
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

    source_institution: Mapped[Institution] = relationship(foreign_keys=[source_institution_id], lazy="joined")
    target_institution: Mapped[Institution] = relationship(foreign_keys=[target_institution_id], lazy="joined")
