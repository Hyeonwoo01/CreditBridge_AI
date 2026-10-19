from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, false, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.department import Department
from backend.models.enums import Role
from backend.models.institution import Institution


class User(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(one_of("role", Role), name="role_valid"),
        CheckConstraint(one_of("locale", ("ko", "en"), nullable=True), name="locale_valid"),
        CheckConstraint("failed_logins >= 0", name="failed_logins_range"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), index=True)
    institution_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("institutions.id"))
    # 교수의 학과 (과목과 같은 학과 행이어야 자동 배정, FR-18). 심사관은 선택, 관리자는 비움.
    # 학생은 입학이 확정된 편입 전공 (관리자가 계정을 만들 때 정하고, 편입 요청에 그대로 쓴다)
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"), index=True)
    # 학생의 출신(전적) 대학. 관리자가 계정을 만들 때 정하고 학생은 바꾸지 않는다. 교직원은 비움
    source_institution_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("institutions.id"))
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
    # 화면·알림·메일 언어 (backend/i18n.py, ko/en). 처음 로그인할 때 그때 화면 언어로 정하고 언어 전환으로 바꾼다
    locale: Mapped[str | None] = mapped_column(String(5), default=None)

    institution: Mapped[Institution | None] = relationship(lazy="joined", foreign_keys=[institution_id])
    source_institution: Mapped[Institution | None] = relationship(lazy="joined", foreign_keys=[source_institution_id])
    dept: Mapped[Department | None] = relationship(lazy="joined")

    @property
    def department_name(self) -> str | None:
        return self.dept.name if self.dept else None

    def is_away(self, today: date) -> bool:
        return self.away_until is not None and self.away_until >= today
