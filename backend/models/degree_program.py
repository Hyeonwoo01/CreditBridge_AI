from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import RequirementArea


class DegreeProgram(IdMixin, CreatedAtMixin, Base):
    """졸업 프로그램 (리뷰 v3 P1-6, 13.9): 대상 대학의 학과·적용 입학연도(카탈로그 연도)별 졸업 요건 묶음.
    학생에게는 학과·입학연도가 맞는 것 중 가장 구체적인 프로그램을 쓰고, 없거나 둘 이상이면 '미정'으로 둔다."""

    __tablename__ = "degree_programs"
    __table_args__ = (
        CheckConstraint("catalog_year IS NULL OR catalog_year BETWEEN 1990 AND 2100", name="catalog_year_range"),
    )

    institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("departments.id"), default=None
    )  # 없으면 모든 학과
    catalog_year: Mapped[int | None] = mapped_column(default=None)


class GraduationRequirement(IdMixin, CreatedAtMixin, Base):
    """졸업 요건 하나: 영역(전공 필수·전공 선택·교양·일반 선택), 필요 학점, 그 요건을 채우는 대상 과목 코드."""

    __tablename__ = "graduation_requirements"
    __table_args__ = (
        CheckConstraint(one_of("area", RequirementArea), name="area_valid"),
        CheckConstraint("required_credits > 0", name="required_credits_positive"),
    )

    program_id: Mapped[int] = mapped_column(IdType, ForeignKey("degree_programs.id"), index=True)
    area: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    required_credits: Mapped[float] = mapped_column(Numeric(5, 1, asdecimal=False))  # 대상 대학 학점 단위
    course_codes: Mapped[list[Any]] = mapped_column(JSONB, default=list)  # 이 요건을 채우는 대상 과목 코드
    sort: Mapped[int] = mapped_column(default=0)
