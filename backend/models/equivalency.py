from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import DecisionResult


class Equivalency(IdMixin, CreatedAtMixin, Base):
    """기관이 보유한 기존 동등 과목표에서 가져온 판정 이력 (FR-26). 강의계획서가 없어 유사도 비교는 하지 않는다."""

    __tablename__ = "equivalencies"
    __table_args__ = (
        # 출신 과목 하나의 인정 이력 찾기 (학생 사전 조회·선배 사례·분석 화면)
        Index("ix_equivalencies_pair_course", "target_institution_id", "source_institution_id", "source_course_key"),
        CheckConstraint(one_of("result", DecisionResult), name="result_valid"),
    )

    target_institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"))
    source_institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"))
    # decisions.course_key와 같은 정규화 (소문자, 공백 제거)
    source_course_key: Mapped[str] = mapped_column(String(100), index=True)
    source_course_label: Mapped[str] = mapped_column(String(255))
    target_course_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("courses.id"))
    result: Mapped[str] = mapped_column(String(10))
    decided_on: Mapped[date | None] = mapped_column(default=None)
    note: Mapped[str] = mapped_column(Text, default="")
    imported_by: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
