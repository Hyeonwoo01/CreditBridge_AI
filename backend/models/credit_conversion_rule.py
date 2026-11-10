from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import ConversionMethod, CreditSystem


class CreditConversionRule(IdMixin, CreatedAtMixin, Base):
    """대상 대학이 승인한 학점 환산 규칙 (출신 단위 × factor = 대상 단위).

    규칙이 없거나 같은 날짜에 겹치면 환산하지 않고 보류한다. 고치지 않고 끝내는 날(effective_to)을 정한 뒤
    새 규칙을 추가해, 지난 판정에 쓴 규칙(decisions.conversion_rule_id)이 그대로 남게 한다."""

    __tablename__ = "credit_conversion_rules"
    __table_args__ = (
        CheckConstraint(one_of("source_system", CreditSystem), name="source_system_valid"),
        CheckConstraint(one_of("target_system", CreditSystem), name="target_system_valid"),
        CheckConstraint(one_of("method", ConversionMethod), name="method_valid"),
        CheckConstraint("factor > 0", name="factor_positive"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="effective_range"),
    )

    target_institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"), index=True)
    source_system: Mapped[str] = mapped_column(String(20))
    target_system: Mapped[str] = mapped_column(String(20))
    factor: Mapped[float] = mapped_column(Numeric(6, 3, asdecimal=False))
    method: Mapped[str] = mapped_column(String(20))
    effective_from: Mapped[date]
    effective_to: Mapped[date | None] = mapped_column(default=None)
    approved_by: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    note: Mapped[str] = mapped_column(Text, default="")
