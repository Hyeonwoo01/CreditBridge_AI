from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin, IdType


class PrivacyRequest(IdMixin, CreatedAtMixin, Base):
    """개인정보(문서) 삭제 요청 (FR-13). 학생 요청 → 심사관 처리 → 기관 관리자 승인 시 삭제. 기한(due_at)을 관리한다."""

    __tablename__ = "privacy_requests"

    transfer_request_id: Mapped[int] = mapped_column(IdType, ForeignKey("transfer_requests.id"), index=True)
    student_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="requested", index=True)
    due_at: Mapped[datetime]
    reviewed_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    approved_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
