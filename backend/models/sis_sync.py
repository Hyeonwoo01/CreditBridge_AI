from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of, utcnow
from backend.models.enums import SisSyncStatus


class SisSync(IdMixin, CreatedAtMixin, Base):
    """판정 하나가 학사정보시스템(SIS)에 반영됐는지 (리뷰 v3 P1-4). SIS가 보낸 반영 결과로 만들고 고친다.
    판정(decisions)은 추가 전용이라 반영 상태는 이 표에 따로 둔다. 행이 없으면 아직 결과를 받지 않은 '대기'다."""

    __tablename__ = "sis_syncs"
    __table_args__ = (
        UniqueConstraint("decision_id", name="uq_sis_syncs_decision"),
        CheckConstraint(one_of("status", SisSyncStatus), name="status_valid"),
    )

    decision_id: Mapped[int] = mapped_column(IdType, ForeignKey("decisions.id"))
    institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"), index=True)
    status: Mapped[str] = mapped_column(String(10), index=True)
    external_reference_id: Mapped[str | None] = mapped_column(String(100), default=None)  # SIS 쪽 기록 번호
    attempts: Mapped[int] = mapped_column(default=0)  # 실패로 보고된 횟수
    last_error: Mapped[str] = mapped_column(Text, default="")
    acknowledged_at: Mapped[datetime] = mapped_column(default=utcnow)  # 마지막 결과를 받은 시각
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


class SisAckRequest(IdMixin, CreatedAtMixin, Base):
    """SIS가 보낸 반영 결과 요청 (Idempotency-Key). 같은 키로 다시 보내면 처음 응답을 그대로 돌려준다."""

    __tablename__ = "sis_ack_requests"
    __table_args__ = (UniqueConstraint("institution_id", "idempotency_key", name="uq_sis_ack_requests_key"),)

    institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"))
    idempotency_key: Mapped[str] = mapped_column(String(100))
    request_hash: Mapped[str] = mapped_column(String(64))  # 같은 키에 다른 내용이 오면 거절
    response: Mapped[dict[str, Any]] = mapped_column(JSONB)
