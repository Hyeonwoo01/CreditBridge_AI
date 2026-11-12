from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import AllocationStatus, CreditSystem


class CreditAllocation(IdMixin, CreatedAtMixin, Base):
    """승인된 학점 배분 원장 (리뷰 v3 P0-3). 교수 판정 하나가 출신 과목(강의계획서)마다 한 줄씩 만든다.

    여러 출신 과목을 합쳐 하나로 인정하면(N:1) 과목마다 나눈 학점이 한 줄씩 생긴다. 학생의 확정 인정 학점은
    active 줄의 합계다. 재판정하면 이전 줄을 지우지 않고 superseded로 바꾸고 새 판정 줄을 더한다.
    한 출신 과목 학점의 이중 사용·같은 대상 과목의 이중 인정은 판정 서비스(services/decisions.py)가 막는다
    (N:1이면 한 판정의 여러 줄이 같은 대상 과목을 가리켜 DB 유니크 제약으로는 표현하지 않는다)."""

    __tablename__ = "credit_allocations"
    __table_args__ = (
        CheckConstraint(one_of("status", AllocationStatus), name="status_valid"),
        CheckConstraint(one_of("credit_unit", CreditSystem, nullable=True), name="credit_unit_valid"),
        CheckConstraint("credits > 0", name="credits_positive"),
    )

    student_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), index=True)
    decision_id: Mapped[int] = mapped_column(IdType, ForeignKey("decisions.id"), index=True)
    syllabus_id: Mapped[int] = mapped_column(IdType, ForeignKey("syllabi.id"), index=True)  # 출신 과목
    target_course_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("courses.id"))  # 선택 학점이면 없음
    credits: Mapped[float] = mapped_column(Numeric(5, 2, asdecimal=False))  # 대상 대학 단위
    credit_unit: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(12), default=AllocationStatus.ACTIVE, index=True)
    superseded_by_decision_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("decisions.id"))
    # 교수가 판정 때 고른 졸업 요건 (리뷰 v3 P1-6). 비우면 자동(과목 목록 기준) 배정.
    # 요건을 지우면 비워져 자동으로 돌아가고, 그때 고른 요건 이름·영역은 판정의 course_snapshot에 남는다
    requirement_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("graduation_requirements.id", ondelete="SET NULL"), default=None
    )
