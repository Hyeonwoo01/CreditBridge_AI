from typing import Any

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class CourseEvaluation(IdMixin, CreatedAtMixin, Base):
    """과목별 AI 분석 결과. 재분석 시 새 행을 추가해 이전 결과를 보존한다."""

    __tablename__ = "course_evaluations"

    transfer_request_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("transfer_requests.id"), index=True)
    syllabus_id: Mapped[int] = mapped_column(IdType, ForeignKey("syllabi.id"), index=True)
    candidate_course_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("courses.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    recommendation: Mapped[str | None] = mapped_column(String(20), index=True)
    # 1순위 후보 과목의 개념 커버리지 0~1 (MVP는 판정 확률을 계산하지 않는다)
    coverage: Mapped[float | None] = mapped_column(Numeric(4, 3, asdecimal=False))
    confidence: Mapped[str | None] = mapped_column(String(10), index=True)
    level_flag: Mapped[str | None] = mapped_column(String(10))  # same / lower / higher
    # 상위 후보 3개와 개념별 커버리지, 정보 부족 진단, 경고
    coverage_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(Text, default="")
    # 같은 입력이면 같은 결과를 재사용하기 위한 키 (반복 실행 동일성)
    input_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    model: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(500))
    is_latest: Mapped[bool] = mapped_column(default=True, index=True)
