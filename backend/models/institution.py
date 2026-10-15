from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin


class Institution(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(2))
    is_target: Mapped[bool] = mapped_column(Boolean, default=False)
    # 대상 대학 시뮬레이션 기본값
    tuition_per_credit: Mapped[int | None] = mapped_column(default=None)
    degree_credits: Mapped[int | None] = mapped_column(default=None)
    # 학사정보시스템 연동 토큰의 SHA-256 (FR-24). 원문 토큰은 발급 때 한 번만 보여준다
    sis_token_hash: Mapped[str | None] = mapped_column(String(64), default=None)
