from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin


class Institution(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(2))
    is_target: Mapped[bool] = mapped_column(Boolean, default=False)
    # 대상 대학 시뮬레이션 기본값
    tuition_per_credit: Mapped[int | None] = mapped_column(default=None)
    degree_credits: Mapped[int | None] = mapped_column(default=None)
