from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class LLMUsageRecord(IdMixin, CreatedAtMixin, Base):
    """AI 호출 사용량 (리뷰 v3 13.7 비용 지표, H15).

    백그라운드 작업 한 번의 시도마다 (용도, 모델)별로 호출 수와 공급자 응답의 입력·출력 토큰 합계를 남긴다.
    검증 실패로 다시 부른 호출도 센다. 문서 내용·이름은 넣지 않는다."""

    __tablename__ = "llm_usage"
    __table_args__ = (Index("ix_llm_usage_institution_created", "institution_id", "created_at"),)

    institution_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("institutions.id"), default=None)
    job_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("background_jobs.id"), default=None, index=True)
    purpose: Mapped[str] = mapped_column(String(60))  # 출력 모델 이름 (SyllabusExtraction 등)
    model: Mapped[str] = mapped_column(String(100))  # 응답이 알려 준 실제 모델
    calls: Mapped[int] = mapped_column(default=0)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
