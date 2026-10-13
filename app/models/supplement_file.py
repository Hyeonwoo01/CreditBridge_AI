from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin, IdType


class SupplementFile(IdMixin, CreatedAtMixin, Base):
    """학생이 올린 보완 자료 원본. 개인정보 삭제 때 함께 지운다."""

    __tablename__ = "supplement_files"

    syllabus_id: Mapped[int] = mapped_column(IdType, ForeignKey("syllabi.id"), index=True)
    file_key: Mapped[str | None] = mapped_column(String(255))
    material_request_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("material_requests.id"))
