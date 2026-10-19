from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class Department(IdMixin, CreatedAtMixin, Base):
    """대상 대학의 학과. 과목과 교수가 같은 행을 가리켜야 자동 배정된다 (철자 차이로 어긋나지 않게).

    과목 CSV를 가져올 때 새 학과명이면 만든다. 계정 CSV·관리자 계정 수정은 이미 있는 학과만 고를 수 있다."""

    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("institution_id", "name"),)

    institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"))
    name: Mapped[str] = mapped_column(String(50))
