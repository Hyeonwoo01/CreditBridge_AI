"""이의 신청 (FR-23): 학생 신청 → 심사관 접수·처리(받아들임·기각) → 받아들이면 교수 재판정.

재판정은 새 판정 행으로 남고 원래 판정은 지우지 않는다 (decisions 추가 전용).
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from app.models import Appeal, Assignment, CourseEvaluation, Syllabus, TransferRequest, User
from app.models.enums import AppealStatus, Role
from app.repositories import appeals as appeal_repo
from app.repositories import catalog as catalog_repo
from app.repositories import decisions as decision_repo
from app.repositories import evaluations as evaluation_repo
from app.repositories import requests as request_repo
from app.repositories import syllabi as syllabus_repo
from app.repositories import users as user_repo
from app.services import audit, notifications

MIN_REASON_CHARS = 20
OPEN = (AppealStatus.SUBMITTED, AppealStatus.ACCEPTED)


@dataclass(frozen=True)
class AppealRow:
    appeal: Appeal
    evaluation: CourseEvaluation
    syllabus: Syllabus
    request: TransferRequest
    reviewer_options: list[User]  # 재판정을 맡길 수 있는 학과 교수
    default_reviewer_id: int | None  # 원 판정 교수 (부재면 대리 심사자)


def _course(syllabus: Syllabus) -> str:
    return (syllabus.course_code or syllabus.course_title or "강의계획서").strip()


def file_appeal(session: Session, student: User, evaluation_id: int, reason: str) -> Appeal:
    evaluation = evaluation_repo.get(session, evaluation_id)
    request = (
        request_repo.get(session, evaluation.transfer_request_id)
        if evaluation and evaluation.transfer_request_id
        else None
    )
    if evaluation is None or request is None:
        raise NotFoundError("심사 건을 찾을 수 없어요.")
    if student.role != Role.STUDENT or request.student_id != student.id:
        raise PermissionDeniedError("본인의 판정에만 이의 신청을 할 수 있어요.")
    decision = decision_repo.for_evaluation(session, evaluation.id)
    if decision is None:
        raise CreditBridgeError("판정이 확정된 과목만 이의 신청을 할 수 있어요.")
    if any(a.status in OPEN for a in appeal_repo.for_evaluation(session, evaluation.id)):
        raise CreditBridgeError("이미 처리 중인 이의 신청이 있어요.")
    reason = reason.strip()
    if len(reason) < MIN_REASON_CHARS:
        raise CreditBridgeError(f"이의 사유를 {MIN_REASON_CHARS}자 이상 구체적으로 적어 주세요.")
    appeal = appeal_repo.add(
        session,
        Appeal(course_evaluation_id=evaluation.id, decision_id=decision.id, student_id=student.id, reason=reason),
    )
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    notifications.notify(
        session,
        notifications.staff(session, request.target_institution_id, Role.EVALUATOR),
        "appeal.submitted",
        f"{_course(syllabus) if syllabus else '과목'} 판정에 이의 신청이 접수됐어요.",
        "/review/appeals",
    )
    audit.record(session, student, "appeal.submit", "course_evaluation", str(evaluation.id), appeal=appeal.id)
    session.commit()
    return appeal


def _load(session: Session, evaluator: User, appeal_id: int) -> tuple[Appeal, CourseEvaluation, TransferRequest]:
    if evaluator.role != Role.EVALUATOR:
        raise PermissionDeniedError("이의 신청은 심사관이 접수·처리해요.")
    appeal = appeal_repo.get(session, appeal_id)
    evaluation = evaluation_repo.get(session, appeal.course_evaluation_id) if appeal else None
    request = (
        request_repo.get(session, evaluation.transfer_request_id)
        if evaluation and evaluation.transfer_request_id
        else None
    )
    if appeal is None or evaluation is None or request is None:
        raise NotFoundError("이의 신청을 찾을 수 없어요.")
    if request.target_institution_id != evaluator.institution_id:
        raise PermissionDeniedError("소속 기관의 이의 신청만 처리할 수 있어요.")
    if appeal.status != AppealStatus.SUBMITTED:
        raise CreditBridgeError("이미 처리한 이의 신청이에요.")
    return appeal, evaluation, request


def _department_professors(session: Session, evaluation: CourseEvaluation, institution_id: int) -> list[User]:
    """재판정을 맡길 수 있는 교수: 판정한 대상 과목(없으면 AI 후보 과목)의 학과, 그것도 없으면 원 판정 교수의 학과."""
    decision = decision_repo.for_evaluation(session, evaluation.id)
    course_id = (decision.target_course_id if decision else None) or evaluation.candidate_course_id
    course = catalog_repo.get_course(session, course_id) if course_id else None
    department = course.department if course else None
    if department is None and decision is not None:
        decider = user_repo.get_by_id(session, decision.decided_by)
        department = decider.department if decider else None
    return user_repo.professors_in(session, institution_id, department) if department else []


def accept(session: Session, evaluator: User, appeal_id: int, reviewer_id: int | None, note: str) -> Appeal:
    """이의 신청을 받아들이고 재판정할 교수에게 배정한다."""
    appeal, evaluation, request = _load(session, evaluator, appeal_id)
    professors = _department_professors(session, evaluation, request.target_institution_id)
    reviewer = next((p for p in professors if p.id == reviewer_id), None)
    if reviewer is None:
        raise CreditBridgeError("재판정할 학과 교수를 선택해 주세요.")
    evaluation_repo.add_assignment(
        session, Assignment(course_evaluation_id=evaluation.id, reviewer_id=reviewer.id, assigned_by=evaluator.id)
    )
    appeal.status = AppealStatus.ACCEPTED
    appeal.handled_by = evaluator.id
    appeal.handler_note = note.strip()
    appeal.handled_at = utcnow()
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    course = _course(syllabus) if syllabus else "과목"
    notifications.notify(
        session,
        [reviewer],
        "appeal.redecide",
        f"{course} 판정에 대한 이의 신청이 받아들여져 재판정이 배정됐어요.",
        f"/professor/evaluations/{evaluation.id}",
    )
    student = user_repo.get_by_id(session, request.student_id)
    notifications.notify(
        session,
        [student] if student else [],
        "appeal.accepted",
        f"{course} 이의 신청이 접수돼 학과 교수가 다시 판정해요.",
        f"/student/evaluations/{evaluation.id}",
    )
    audit.record(
        session,
        evaluator,
        "appeal.accept",
        "course_evaluation",
        str(evaluation.id),
        appeal=appeal.id,
        reviewer=reviewer.id,
    )
    session.commit()
    return appeal


def dismiss(session: Session, evaluator: User, appeal_id: int, note: str) -> Appeal:
    appeal, evaluation, request = _load(session, evaluator, appeal_id)
    note = note.strip()
    if not note:
        raise CreditBridgeError("기각할 때는 학생에게 전할 사유를 적어 주세요.")
    appeal.status = AppealStatus.DISMISSED
    appeal.handled_by = evaluator.id
    appeal.handler_note = note
    appeal.handled_at = utcnow()
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    student = user_repo.get_by_id(session, request.student_id)
    notifications.notify(
        session,
        [student] if student else [],
        "appeal.dismissed",
        f"{_course(syllabus) if syllabus else '과목'} 이의 신청이 기각됐어요. 사유를 확인해 주세요.",
        f"/student/evaluations/{evaluation.id}",
    )
    audit.record(session, evaluator, "appeal.dismiss", "course_evaluation", str(evaluation.id), appeal=appeal.id)
    session.commit()
    return appeal


def accepted_for(session: Session, evaluation_id: int) -> Appeal | None:
    """재판정을 기다리는 이의 신청."""
    return next(
        (a for a in appeal_repo.for_evaluation(session, evaluation_id) if a.status == AppealStatus.ACCEPTED), None
    )


def for_evaluation(session: Session, evaluation_id: int) -> list[Appeal]:
    return appeal_repo.for_evaluation(session, evaluation_id)


def rows(session: Session, evaluator: User) -> list[AppealRow]:
    if evaluator.role != Role.EVALUATOR or evaluator.institution_id is None:
        raise PermissionDeniedError("심사관 계정만 사용할 수 있어요.")
    today = utcnow().date()
    out = []
    for appeal, evaluation, syllabus, request in appeal_repo.of_institution(session, evaluator.institution_id):
        professors = _department_professors(session, evaluation, evaluator.institution_id)
        appealed = decision_repo.get(session, appeal.decision_id)
        original = user_repo.get_by_id(session, appealed.decided_by) if appealed else None
        default = original
        if original is not None and original.is_away(today) and original.delegate_user_id:
            default = user_repo.get_by_id(session, original.delegate_user_id)
        out.append(
            AppealRow(
                appeal,
                evaluation,
                syllabus,
                request,
                professors,
                default.id if default and any(p.id == default.id for p in professors) else None,
            )
        )
    out.sort(key=lambda r: (r.appeal.status != AppealStatus.SUBMITTED, -r.appeal.id))
    return out
