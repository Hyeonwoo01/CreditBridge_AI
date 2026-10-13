from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Assignment, CourseEvaluation, Decision, EvidenceSpan, Syllabus, TransferRequest


def get(session: Session, evaluation_id: int) -> CourseEvaluation | None:
    return session.get(CourseEvaluation, evaluation_id)


def latest_for_syllabus(session: Session, syllabus_id: int) -> CourseEvaluation | None:
    stmt = (
        select(CourseEvaluation)
        .where(CourseEvaluation.syllabus_id == syllabus_id)
        .order_by(CourseEvaluation.created_at.desc(), CourseEvaluation.id.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def history_for_syllabus(session: Session, syllabus_id: int) -> list[CourseEvaluation]:
    stmt = (
        select(CourseEvaluation)
        .where(CourseEvaluation.syllabus_id == syllabus_id)
        .order_by(CourseEvaluation.created_at.desc(), CourseEvaluation.id.desc())
    )
    return list(session.scalars(stmt))


def find_by_input_hash(session: Session, input_hash: str) -> CourseEvaluation | None:
    stmt = (
        select(CourseEvaluation)
        .where(CourseEvaluation.input_hash == input_hash, CourseEvaluation.status == "done")
        .order_by(CourseEvaluation.id.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def add(session: Session, evaluation: CourseEvaluation) -> CourseEvaluation:
    session.execute(
        update(CourseEvaluation)
        .where(CourseEvaluation.syllabus_id == evaluation.syllabus_id, CourseEvaluation.is_latest.is_(True))
        .values(is_latest=False)
    )
    evaluation.is_latest = True
    session.add(evaluation)
    session.flush()
    return evaluation


def add_spans(session: Session, spans: list[EvidenceSpan]) -> None:
    session.add_all(spans)
    session.flush()


def spans_of(session: Session, evaluation_id: int) -> list[EvidenceSpan]:
    return list(session.scalars(select(EvidenceSpan).where(EvidenceSpan.course_evaluation_id == evaluation_id)))


def review_queue(
    session: Session, target_institution_id: int
) -> list[tuple[CourseEvaluation, Syllabus, TransferRequest]]:
    """제출된 요청의 최신 분석 결과 중 아직 판정되지 않은 것."""
    decided = select(Decision.course_evaluation_id)
    stmt = (
        select(CourseEvaluation, Syllabus, TransferRequest)
        .join(Syllabus, Syllabus.id == CourseEvaluation.syllabus_id)
        .join(TransferRequest, TransferRequest.id == CourseEvaluation.transfer_request_id)
        .where(
            TransferRequest.target_institution_id == target_institution_id,
            TransferRequest.status.in_(["submitted", "decided"]),
            CourseEvaluation.is_latest.is_(True),
            CourseEvaluation.status == "done",
            CourseEvaluation.id.not_in(decided),
        )
        .order_by(TransferRequest.submitted_at, CourseEvaluation.id)
    )
    return [(e, s, r) for e, s, r in session.execute(stmt)]


def active_assignment(session: Session, evaluation_id: int) -> Assignment | None:
    stmt = select(Assignment).where(Assignment.course_evaluation_id == evaluation_id, Assignment.is_active.is_(True))
    return session.scalars(stmt).first()


def active_assignments_for(session: Session, reviewer_id: int) -> list[Assignment]:
    stmt = (
        select(Assignment)
        .where(Assignment.reviewer_id == reviewer_id, Assignment.is_active.is_(True))
        .order_by(Assignment.assigned_at)
    )
    return list(session.scalars(stmt))


def add_assignment(session: Session, assignment: Assignment) -> Assignment:
    session.execute(
        update(Assignment)
        .where(Assignment.course_evaluation_id == assignment.course_evaluation_id, Assignment.is_active.is_(True))
        .values(is_active=False)
    )
    session.add(assignment)
    session.flush()
    return assignment


def assigned_at(session: Session, evaluation_id: int) -> datetime | None:
    a = active_assignment(session, evaluation_id)
    return a.assigned_at if a else None


def carry_assignment(session: Session, from_evaluation_id: int, to_evaluation_id: int) -> None:
    """재분석으로 새 결과가 생기면 진행 중인 교수 배정을 새 결과로 옮긴다 (배정 기록은 남는다)."""
    current = active_assignment(session, from_evaluation_id)
    if current is None:
        return
    current.is_active = False
    session.add(
        Assignment(
            course_evaluation_id=to_evaluation_id,
            reviewer_id=current.reviewer_id,
            assigned_by=current.assigned_by,
            reassigned_from=current.reassigned_from,
        )
    )
    session.flush()
