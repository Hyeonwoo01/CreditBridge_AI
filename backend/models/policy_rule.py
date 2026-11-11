from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.db.types import JSONB
from backend.models.enums import PolicyRuleType, PolicyStatus


class PolicyRule(IdMixin, CreatedAtMixin, Base):
    """대학 학칙을 데이터로 둔 규칙 (리뷰 v3 P0-4).

    적용 범위: 대학 전체, 학과(편입 전공), 입학연도. 비어 있으면 모두에 적용. 학생에게 맞는 승인된 규칙 중
    범위가 가장 구체적인 것을 쓰고, 같은 구체성에서 값이 다르면 충돌로 보류한다. 맞는 규칙이 없으면 기본값을 쓰지 않고
    미정으로 둔다. 승인한 규칙은 고치지 않고 끝낸 뒤 새로 만든다 (지난 판정의 정책 스냅샷이 바뀌지 않게)."""

    __tablename__ = "policy_rules"
    __table_args__ = (
        CheckConstraint(one_of("rule_type", PolicyRuleType), name="rule_type_valid"),
        CheckConstraint(one_of("status", PolicyStatus), name="status_valid"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="effective_range"),
        CheckConstraint("admission_year IS NULL OR admission_year BETWEEN 1990 AND 2100", name="admission_year_range"),
    )

    institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"), index=True)
    rule_type: Mapped[str] = mapped_column(String(30))
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"), default=None)
    admission_year: Mapped[int | None] = mapped_column(default=None)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB)
    effective_from: Mapped[date]
    effective_to: Mapped[date | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(10), default=PolicyStatus.DRAFT, index=True)
    source: Mapped[str] = mapped_column(Text, default="")  # 근거 학칙 조항·문서
    created_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"), default=None)
    approved_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"), default=None)
    approved_at: Mapped[datetime | None] = mapped_column(default=None)
