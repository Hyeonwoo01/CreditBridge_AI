from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, IdType, utcnow


class Decision(IdMixin, Base):
    """사람의 최종 판정. 추가 전용(INSERT만) — 수정·삭제 코드를 작성하지 않는다."""

    __tablename__ = "decisions"

    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"), index=True)
    decided_by: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(10))
    result: Mapped[str] = mapped_column(String(10))
    target_course_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("courses.id"))
    # 선택형 사유 코드 (반려·AI 추천과 다른 판정이면 1개 이상), 기타일 때만 메모 필수
    reason_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    reason_memo: Mapped[str] = mapped_column(Text, default="")
    ai_recommendation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    conflict_acknowledged: Mapped[bool] = mapped_column(default=False)
    decided_at: Mapped[datetime] = mapped_column(default=utcnow)
