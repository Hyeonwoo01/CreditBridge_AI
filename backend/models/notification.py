from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class Notification(IdMixin, CreatedAtMixin, Base):
    """화면 알림 (FR-19, FR-20). 메일 설정이 있으면 같은 내용을 메일로도 보낸다. 메시지에 개인정보를 넣지 않는다."""

    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(255), default="")
    read_at: Mapped[datetime | None] = mapped_column(default=None)
    emailed_at: Mapped[datetime | None] = mapped_column(default=None)
