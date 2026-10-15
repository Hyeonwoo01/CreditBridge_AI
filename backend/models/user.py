from datetime import date

from sqlalchemy import Boolean, ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType
from backend.models.institution import Institution


class User(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), index=True)
    institution_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("institutions.id"))
    department: Mapped[str | None] = mapped_column(String(50), index=True)
    # 부재 시 대리 심사자 (FR-19)
    delegate_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    away_until: Mapped[date | None] = mapped_column(default=None)
    # 관리자가 CSV로 만든 계정은 임시 비밀번호로 첫 로그인한 뒤 바로 바꿔야 한다
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    institution: Mapped[Institution | None] = relationship(lazy="joined")

    def is_away(self, today: date) -> bool:
        return self.away_until is not None and self.away_until >= today
