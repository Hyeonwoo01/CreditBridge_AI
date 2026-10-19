from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class PushSubscription(IdMixin, CreatedAtMixin, Base):
    """브라우저 웹 푸시 구독 (FR-20 모바일 알림). 기기(브라우저)마다 한 줄. 푸시 서비스가 만료를 알리면 지운다."""

    __tablename__ = "push_subscriptions"

    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), index=True)
    # 브라우저 푸시 서비스 주소 (구독마다 다름)
    endpoint: Mapped[str] = mapped_column(String(1000), unique=True)
    # 내용 암호화 키 (RFC 8291)
    p256dh: Mapped[str] = mapped_column(String(200))
    auth: Mapped[str] = mapped_column(String(100))
    last_sent_at: Mapped[datetime | None] = mapped_column(default=None)
