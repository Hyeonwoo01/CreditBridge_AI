"""decisions는 추가 전용 테이블: 이 모듈에는 INSERT와 SELECT만 둔다."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CourseEvaluation, Decision, Syllabus, TransferRequest


def add(session: Session, decision: Decision) -> Decision:
    session.add(decision)
    session.flush()
    return decision


def for_evaluation(session: Session, evaluation_id: int) -> Decision | None:
    stmt = select(Decision).where(Decision.course_evaluation_id == evaluation_id).order_by(Decision.id.desc()).limit(1)
    return session.scalars(stmt).first()


def for_evaluations(session: Session, evaluation_ids: list[int]) -> dict[int, Decision]:
    if not evaluation_ids:
        return {}
    stmt = select(Decision).where(Decision.course_evaluation_id.in_(evaluation_ids)).order_by(Decision.id)
    return {d.course_evaluation_id: d for d in session.scalars(stmt)}


def history_for_course(
    session: Session, source_institution_id: int, course_key: str, exclude_evaluation_id: int | None = None
) -> list[tuple[Decision, CourseEvaluation, Syllabus]]:
    """같은 출신 대학·같은 과목(정규화된 과목 코드 또는 과목명)의 과거 판정 (FR-11)."""
    key_expr = func.lower(func.coalesce(func.nullif(Syllabus.course_code, ""), Syllabus.course_title))
    stmt = (
        select(Decision, CourseEvaluation, Syllabus)
        .join(CourseEvaluation, CourseEvaluation.id == Decision.course_evaluation_id)
        .join(Syllabus, Syllabus.id == CourseEvaluation.syllabus_id)
        .where(Syllabus.institution_id == source_institution_id, func.replace(key_expr, " ", "") == course_key)
        .order_by(Decision.decided_at.desc())
    )
    if exclude_evaluation_id is not None:
        stmt = stmt.where(Decision.course_evaluation_id != exclude_evaluation_id)
    return [(d, e, s) for d, e, s in session.execute(stmt)]


def all_for_institution(
    session: Session, target_institution_id: int
) -> list[tuple[Decision, CourseEvaluation, Syllabus]]:
    stmt = (
        select(Decision, CourseEvaluation, Syllabus)
        .join(CourseEvaluation, CourseEvaluation.id == Decision.course_evaluation_id)
        .join(Syllabus, Syllabus.id == CourseEvaluation.syllabus_id)
        .join(TransferRequest, TransferRequest.id == CourseEvaluation.transfer_request_id)
        .where(TransferRequest.target_institution_id == target_institution_id)
        .order_by(Decision.decided_at)
    )
    return [(d, e, s) for d, e, s in session.execute(stmt)]
