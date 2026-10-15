from sqlalchemy import JSON, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class Course(IdMixin, CreatedAtMixin, Base):
    """대상 대학 카탈로그 과목."""

    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("institution_id", "code"),)

    institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"), index=True)
    code: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    credits: Mapped[float] = mapped_column(Numeric(4, 1, asdecimal=False))
    department: Mapped[str] = mapped_column(String(50), index=True)
    # 과목 수준 설명 (예: "이공계 1학년 미적분") — 수준 차이 판별(FR-16)에 사용
    level: Mapped[str] = mapped_column(Text, default="")
    reference_syllabus_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("syllabi.id", use_alter=True))
    # 학과가 정한 필수 개념 (과목 CSV). 비어 있으면 기준 강의계획서 청크의 개념을 쓴다
    concepts: Mapped[list[str] | None] = mapped_column(JSON, default=None)
