from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import JobStatus


class BackgroundJob(IdMixin, CreatedAtMixin, Base):
    """백그라운드 분석 작업 하나의 상태와 시도 기록 (리뷰 v3 P1-3, 13.7).

    재시도할 수 있는 오류(AI 공급자 한도·시간 초과·연결·서버 오류)는 간격을 늘려 다시 하고, 정해진 횟수를 넘기면
    격리(dead_letter)한다. 다시 해도 안 되는 오류(읽을 수 없는 파일·설정 없음)는 곧바로 실패. 기록에는 오류 코드와
    대상 id만 남기고 문서 내용·이름은 넣지 않는다."""

    __tablename__ = "background_jobs"
    __table_args__ = (
        CheckConstraint(one_of("status", JobStatus), name="status_valid"),
        Index("ix_background_jobs_institution_created", "institution_id", "created_at"),
    )

    institution_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("institutions.id"), default=None)
    job_type: Mapped[str] = mapped_column(String(40))  # syllabus.process 등 작업 이름
    subject_type: Mapped[str] = mapped_column(String(20))  # syllabus · student
    subject_id: Mapped[int] = mapped_column(IdType)
    status: Mapped[str] = mapped_column(String(12), index=True)
    attempt_count: Mapped[int] = mapped_column(default=0)
    error_code: Mapped[str] = mapped_column(String(60), default="")
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    duration_ms: Mapped[int | None] = mapped_column(default=None)  # 마지막 시도의 처리 시간
    task_args: Mapped[list[Any]] = mapped_column(JSONB, default=list)  # 다시 처리할 때 넘길 인자 (id·파일 키만)
