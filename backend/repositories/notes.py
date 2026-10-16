from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models import EvaluationNote


def add(session: Session, note: EvaluationNote) -> EvaluationNote:
    session.add(note)
    session.flush()
    return note


def of_syllabus(session: Session, syllabus_id: int) -> list[EvaluationNote]:
    return list(
        session.scalars(
            select(EvaluationNote)
            .where(EvaluationNote.syllabus_id == syllabus_id)
            .order_by(EvaluationNote.created_at, EvaluationNote.id)
        )
    )


def delete_for_syllabi(session: Session, syllabus_ids: list[int]) -> None:
    """개인정보 삭제 요청 승인 때 문서와 함께 지운다."""
    if syllabus_ids:
        session.execute(delete(EvaluationNote).where(EvaluationNote.syllabus_id.in_(syllabus_ids)))
