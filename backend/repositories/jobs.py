"""백그라운드 작업 기록 (리뷰 v3 P1-3)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import BackgroundJob, LLMUsageRecord


def add(session: Session, job: BackgroundJob) -> BackgroundJob:
    session.add(job)
    session.flush()
    return job


def get(session: Session, job_id: int) -> BackgroundJob | None:
    return session.get(BackgroundJob, job_id)


def since(session: Session, institution_id: int, start: datetime) -> list[BackgroundJob]:
    return list(
        session.execute(
            select(BackgroundJob)
            .where(BackgroundJob.institution_id == institution_id, BackgroundJob.created_at >= start)
            .order_by(BackgroundJob.id.desc())
        ).scalars()
    )


def needing_attention(session: Session, institution_id: int, limit: int = 50) -> list[BackgroundJob]:
    """운영자가 볼 작업: 격리(dead_letter)와 실패, 최근 순."""
    return list(
        session.execute(
            select(BackgroundJob)
            .where(
                BackgroundJob.institution_id == institution_id,
                BackgroundJob.status.in_(("dead_letter", "failed")),
            )
            .order_by(BackgroundJob.id.desc())
            .limit(limit)
        ).scalars()
    )


def add_usage(session: Session, rows: list[LLMUsageRecord]) -> None:
    session.add_all(rows)
    session.flush()


def usage_since(session: Session, institution_id: int, start: datetime) -> list[tuple[str, str, int, int, int, int]]:
    """(용도, 모델)별 호출 수·입력 토큰·출력 토큰·작업 수."""
    stmt = (
        select(
            LLMUsageRecord.purpose,
            LLMUsageRecord.model,
            func.sum(LLMUsageRecord.calls),
            func.sum(LLMUsageRecord.input_tokens),
            func.sum(LLMUsageRecord.output_tokens),
            func.count(func.distinct(LLMUsageRecord.job_id)),
        )
        .where(LLMUsageRecord.institution_id == institution_id, LLMUsageRecord.created_at >= start)
        .group_by(LLMUsageRecord.purpose, LLMUsageRecord.model)
        .order_by(func.sum(LLMUsageRecord.input_tokens + LLMUsageRecord.output_tokens).desc())
    )
    return [(p, m, int(c), int(i), int(o), int(j)) for p, m, c, i, o, j in session.execute(stmt).all()]


def usage_job_count(session: Session, institution_id: int, start: datetime) -> int:
    """AI를 부른 작업 수 (문서 하나당 평균을 낼 때 분모)."""
    stmt = select(func.count(func.distinct(LLMUsageRecord.job_id))).where(
        LLMUsageRecord.institution_id == institution_id, LLMUsageRecord.created_at >= start
    )
    return int(session.execute(stmt).scalar_one())
