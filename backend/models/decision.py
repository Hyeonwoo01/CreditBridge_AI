from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, IdMixin, IdType, one_of, utcnow
from backend.db.types import JSONB
from backend.models.enums import CreditBasis, CreditSystem, DecisionAction, DecisionResult


class Decision(IdMixin, Base):
    """사람의 최종 판정. 추가 전용(INSERT만) — 수정·삭제 코드를 작성하지 않는다."""

    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint(one_of("action", DecisionAction), name="action_valid"),
        CheckConstraint(one_of("result", DecisionResult), name="result_valid"),
        CheckConstraint(one_of("credit_basis", CreditBasis, nullable=True), name="credit_basis_valid"),
        CheckConstraint(one_of("credit_unit", CreditSystem, nullable=True), name="credit_unit_valid"),
        CheckConstraint("accepted_credits IS NULL OR accepted_credits >= 0", name="accepted_credits_range"),
    )

    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"), index=True)
    decided_by: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(10))
    result: Mapped[str] = mapped_column(String(10))
    target_course_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("courses.id"))
    # 선택형 사유 코드 (반려·AI 추천과 다른 판정이면 1개 이상), 기타일 때만 메모 필수
    reason_codes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    reason_memo: Mapped[str] = mapped_column(Text, default="")
    ai_recommendation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    conflict_acknowledged: Mapped[bool] = mapped_column(default=False)
    # 이의 신청으로 다시 내린 판정이면 그 이의 신청 (FR-23). 이전 판정은 지우지 않고 그대로 남는다
    appeal_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("appeals.id", use_alter=True))
    decided_at: Mapped[datetime] = mapped_column(default=utcnow)
    # 교수가 확정한 인정 학점 (0009부터, 그 전 판정은 비어 있음). 단위는 대상 대학 학점 단위,
    # 출신 학점과 적용한 환산 규칙을 함께 남겨 나중에 같은 계산을 다시 할 수 있게 한다
    accepted_credits: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False), default=None)
    credit_unit: Mapped[str | None] = mapped_column(String(20), default=None)
    credit_basis: Mapped[str | None] = mapped_column(String(12), default=None)
    source_credits: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False), default=None)
    source_credit_unit: Mapped[str | None] = mapped_column(String(20), default=None)
    conversion_rule_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("credit_conversion_rules.id"), default=None
    )
    # 판정 때 이 학생에게 적용된 학칙 정책 (규칙 종류 → 규칙 id·값, 0011부터). 정책이 바뀌어도 이 기록은 그대로다
    policy_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    # 판정 때 증거 상태 (출처·진위·적용 학기·학기·파일 해시, 0012부터)
    evidence_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    # 판정 때 대상·출신 과목, 환산 규칙, 추천 규칙 버전 (0013부터). 카탈로그가 바뀌어도 내보내기·리포트는 이 값을 쓴다
    course_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    # 분야별 심사 체크리스트 (0016부터, 리뷰 v3 P1-1): 분야·확인한 항목·자료 없는 항목. 판정을 대신하지 않는 기록
    review_checklist: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
