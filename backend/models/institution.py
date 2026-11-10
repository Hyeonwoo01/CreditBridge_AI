from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, one_of
from backend.models.enums import CreditSystem


class Institution(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "institutions"
    __table_args__ = (
        CheckConstraint(one_of("credit_system", CreditSystem, nullable=True), name="credit_system_valid"),
    )

    name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(2))
    is_target: Mapped[bool] = mapped_column(Boolean, default=False)
    # 대상 대학 시뮬레이션 기본값
    tuition_per_credit: Mapped[int | None] = mapped_column(default=None)
    degree_credits: Mapped[int | None] = mapped_column(default=None)
    # 편입으로 인정받을 수 있는 최대 학점 (비우면 60). 넘으면 학생이 졸업 학점에 넣을 과목을 고른다
    max_transfer_credits: Mapped[int | None] = mapped_column(default=None)
    # 학점 단위 (enums.CreditSystem). 비어 있으면 모름: 환산하지 않고 예상 학점 계산을 보류한다
    credit_system: Mapped[str | None] = mapped_column(String(20), default=None)
    # 학사정보시스템 연동 토큰의 SHA-256 (FR-24). 원문 토큰은 발급 때 한 번만 보여준다
    sis_token_hash: Mapped[str | None] = mapped_column(String(64), default=None)
