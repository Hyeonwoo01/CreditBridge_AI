from typing import Any

from sqlalchemy import JSON, CheckConstraint, Computed, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of, ratio
from backend.models.enums import Confidence, EvaluationStatus, Recommendation


class CourseEvaluation(IdMixin, CreatedAtMixin, Base):
    """과목별 AI 분석 결과. 재분석 시 새 행을 추가해 이전 결과를 보존한다."""

    __tablename__ = "course_evaluations"
    __table_args__ = (
        # 강의계획서의 최신 분석 찾기 (재분석하면 이전 결과는 is_latest=False로 남는다)
        Index("ix_course_evaluations_syllabus_latest", "syllabus_id", "is_latest"),
        CheckConstraint(one_of("status", EvaluationStatus), name="status_valid"),
        CheckConstraint(one_of("recommendation", Recommendation, nullable=True), name="recommendation_valid"),
        CheckConstraint(one_of("confidence", Confidence, nullable=True), name="confidence_valid"),
        CheckConstraint(one_of("level_flag", ("same", "lower", "higher"), nullable=True), name="level_flag_valid"),
        CheckConstraint(ratio("coverage"), name="coverage_range"),
    )

    transfer_request_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("transfer_requests.id"), index=True)
    syllabus_id: Mapped[int] = mapped_column(IdType, ForeignKey("syllabi.id"))
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
    # 강의계획서당 최신 분석은 하나 (assignments.active_evaluation_id와 같은 방식)
    latest_syllabus_id: Mapped[int | None] = mapped_column(
        IdType, Computed("IF(is_latest, syllabus_id, NULL)", persisted=True), unique=True
    )
