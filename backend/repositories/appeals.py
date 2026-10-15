from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Appeal, CourseEvaluation, Syllabus, TransferRequest


def add(session: Session, appeal: Appeal) -> Appeal:
    session.add(appeal)
    session.flush()
    return appeal


def get(session: Session, appeal_id: int) -> Appeal | None:
    return session.get(Appeal, appeal_id)


def for_evaluation(session: Session, evaluation_id: int) -> list[Appeal]:
    stmt = select(Appeal).where(Appeal.course_evaluation_id == evaluation_id).order_by(Appeal.id)
    return list(session.scalars(stmt))


def latest_for_evaluations(session: Session, evaluation_ids: list[int]) -> dict[int, Appeal]:
    if not evaluation_ids:
        return {}
    stmt = select(Appeal).where(Appeal.course_evaluation_id.in_(evaluation_ids)).order_by(Appeal.id)
    return {a.course_evaluation_id: a for a in session.scalars(stmt)}


def of_institution(
    session: Session, target_institution_id: int
) -> list[tuple[Appeal, CourseEvaluation, Syllabus, TransferRequest]]:
    stmt = (
        select(Appeal, CourseEvaluation, Syllabus, TransferRequest)
        .join(CourseEvaluation, CourseEvaluation.id == Appeal.course_evaluation_id)
        .join(Syllabus, Syllabus.id == CourseEvaluation.syllabus_id)
        .join(TransferRequest, TransferRequest.id == CourseEvaluation.transfer_request_id)
        .where(TransferRequest.target_institution_id == target_institution_id)
        .order_by(Appeal.id.desc())
    )
    return [(a, e, s, r) for a, e, s, r in session.execute(stmt)]
