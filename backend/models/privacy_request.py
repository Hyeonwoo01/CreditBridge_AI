from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import PrivacyStatus


class PrivacyRequest(IdMixin, CreatedAtMixin, Base):
    """개인정보(문서) 삭제 요청 (FR-13). 학생 요청 → 심사관 처리 → 기관 관리자 승인 시 삭제. 기한(due_at)을 관리한다."""

    __tablename__ = "privacy_requests"
    __table_args__ = (
        CheckConstraint(one_of("status", PrivacyStatus), name="status_valid"),
        # 편입 요청당 처리 중(완료 전) 삭제 요청은 하나 (조건부 유니크 인덱스)
        Index(
            "uq_privacy_requests_open_request",
            "transfer_request_id",
            unique=True,
            postgresql_where=text("status <> 'completed'"),
        ),
    )

    transfer_request_id: Mapped[int] = mapped_column(IdType, ForeignKey("transfer_requests.id"), index=True)
    student_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="requested", index=True)
    due_at: Mapped[datetime]
    reviewed_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    approved_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
