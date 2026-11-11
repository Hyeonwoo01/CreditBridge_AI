"""백그라운드 작업 기록 (리뷰 v3 P1-3)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import BackgroundJob


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
