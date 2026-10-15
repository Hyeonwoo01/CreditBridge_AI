from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class AppealFile(IdMixin, CreatedAtMixin, Base):
    """이의 신청에 학생이 붙인 근거 자료 원본. 개인정보 삭제 때 파일을 지우고 키를 비운다."""

    __tablename__ = "appeal_files"

    appeal_id: Mapped[int] = mapped_column(IdType, ForeignKey("appeals.id"), index=True)
    file_key: Mapped[str | None] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
