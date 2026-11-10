"""승인된 학점 배분 원장 (credit_allocations). 줄은 지우지 않고 재판정이면 superseded로 바꾼다."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.models import CreditAllocation, Decision, Syllabus
from backend.models.enums import AllocationStatus


def add_all(session: Session, rows: list[CreditAllocation]) -> None:
    session.add_all(rows)
    session.flush()


def active_for_student(session: Session, student_id: int) -> list[tuple[CreditAllocation, Syllabus]]:
    """학생의 지금 유효한 배분과 그 출신 과목."""
    stmt = (
        select(CreditAllocation, Syllabus)
        .join(Syllabus, Syllabus.id == CreditAllocation.syllabus_id)
        .where(CreditAllocation.student_id == student_id, CreditAllocation.status == AllocationStatus.ACTIVE)
        .order_by(CreditAllocation.id)
    )
    return [(a, s) for a, s in session.execute(stmt)]


def for_decisions(session: Session, decision_ids: list[int]) -> list[CreditAllocation]:
    if not decision_ids:
        return []
    stmt = select(CreditAllocation).where(CreditAllocation.decision_id.in_(decision_ids))
    return list(session.scalars(stmt.order_by(CreditAllocation.id)))


def supersede_for_evaluation(session: Session, evaluation_id: int, by_decision_id: int) -> int:
    """이 심사 건의 이전 판정이 만든 유효한 배분을 대체됨으로 바꾼다 (재판정). 바꾼 줄 수."""
    earlier = select(Decision.id).where(Decision.course_evaluation_id == evaluation_id, Decision.id != by_decision_id)
    result = session.execute(
        update(CreditAllocation)
        .where(CreditAllocation.decision_id.in_(earlier), CreditAllocation.status == AllocationStatus.ACTIVE)
        .values(status=AllocationStatus.SUPERSEDED, superseded_by_decision_id=by_decision_id)
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]
