from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of, utcnow
from backend.models.enums import EvidenceVerdict


class EvidenceFeedback(IdMixin, CreatedAtMixin, Base):
    """교수가 근거 구절마다 누른 맞음·틀림. AI 근거 정확도를 재고 기준값(UNVERIFIED_CAP 등)을 보정하는 데 쓴다.
    판정이 아니라 품질 표시라 다시 누르면 고친다 (교수 한 명당 구절 하나에 한 행)."""

    __tablename__ = "evidence_feedback"
    __table_args__ = (
        UniqueConstraint("evidence_span_id", "user_id", name="uq_evidence_feedback_span_user"),
        CheckConstraint(one_of("verdict", EvidenceVerdict), name="verdict_valid"),
    )

    evidence_span_id: Mapped[int] = mapped_column(IdType, ForeignKey("evidence_spans.id"), index=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    verdict: Mapped[str] = mapped_column(String(10))
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)
