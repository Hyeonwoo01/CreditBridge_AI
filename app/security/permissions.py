"""역할 기반 접근 제어 (FR-12). 학생은 본인 건, 교수는 배정 건, 심사관은 소속 기관 건만."""

from sqlalchemy.orm import Session

from app.errors import PermissionDeniedError
from app.models import CourseEvaluation, User
from app.models.enums import Role
from app.repositories import decisions as decision_repo
from app.repositories import evaluations as evaluation_repo
from app.repositories import requests as request_repo


def can_view_evaluation(session: Session, user: User, evaluation: CourseEvaluation) -> bool:
    request = request_repo.get(session, evaluation.transfer_request_id) if evaluation.transfer_request_id else None
    if request is None:
        return False
    if user.role == Role.STUDENT:
        return request.student_id == user.id
    if user.role == Role.EVALUATOR:
        return user.institution_id == request.target_institution_id and request.status != "draft"
    if user.role == Role.PROFESSOR:
        assignment = evaluation_repo.active_assignment(session, evaluation.id)
        decision = decision_repo.for_evaluation(session, evaluation.id)
        return (assignment is not None and assignment.reviewer_id == user.id) or (
            decision is not None and decision.decided_by == user.id
        )
    return False  # 기관 관리자는 통계만


def ensure_can_view_evaluation(session: Session, user: User, evaluation: CourseEvaluation) -> None:
    if not can_view_evaluation(session, user, evaluation):
        raise PermissionDeniedError("이 심사 건을 볼 권한이 없어요.")
