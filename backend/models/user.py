from datetime import date, datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, false, text, true
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
    # 연속 로그인 실패 (성공·재설정하면 0). 5번이면 1분 잠금, 10번이면 비밀번호를 무효로 하고 재설정 메일
    failed_logins: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(default=None)
    # 졸업·퇴직 등으로 비활성화된 계정: 지우지 않고(감사 기록 보존) 로그인·배정·알림 메일에서 뺀다
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    deactivated_at: Mapped[datetime | None] = mapped_column(default=None)

    institution: Mapped[Institution | None] = relationship(lazy="joined")

    def is_away(self, today: date) -> bool:
        return self.away_until is not None and self.away_until >= today
