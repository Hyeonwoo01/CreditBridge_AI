"""보완 자료 요청 (FR-22): 심사관·배정 교수가 정보 부족 건에 필요한 자료를 지정해 학생에게 요청한다.

학생이 보완 자료를 올리면 요청은 처리됨으로 바뀌고, 다시 분석한 결과에 진행 중인 교수 배정이 그대로 이어진다.
"""

from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import MaterialRequest, Syllabus, User
from backend.models.enums import MaterialRequestStatus, Role
from backend.repositories import decisions as decision_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import materials as material_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.security.permissions import ensure_can_view_evaluation
from backend.services import audit, notifications

# 요청 화면에서 고를 수 있는 기본 항목. 분석이 제안한 자료(missing_materials)와 함께 보여준다
STANDARD_ITEMS = [
    N_("주차별 상세 강의 계획"),
    N_("교재 목차(다룬 장 표시)"),
    N_("시험지 또는 과제 샘플"),
    N_("실험·실습 보고서"),
    N_("학점·시수 확인 서류"),
]
MAX_ITEMS = 10


def request_materials(
    session: Session, actor: User, evaluation_id: int, items: list[str], note: str
) -> MaterialRequest:
    evaluation = evaluation_repo.get(session, evaluation_id)
    if evaluation is None:
        raise NotFoundError(tr("심사 건을 찾을 수 없어요."))
    if actor.role not in (Role.EVALUATOR, Role.PROFESSOR):
        raise PermissionDeniedError(tr("보완 자료 요청은 심사관과 배정된 교수만 할 수 있어요."))
    ensure_can_view_evaluation(session, actor, evaluation)
    if actor.role == Role.PROFESSOR:
        assignment = evaluation_repo.active_assignment(session, evaluation.id)
        if assignment is None or assignment.reviewer_id != actor.id:
            raise PermissionDeniedError(tr("본인에게 배정된 건만 보완 자료를 요청할 수 있어요."))
    if decision_repo.for_evaluation(session, evaluation.id) is not None:
        raise CreditBridgeError(tr("이미 판정된 건이에요. 보완 자료는 판정 전에만 요청할 수 있어요."))
    cleaned = list(dict.fromkeys(i.strip()[:200] for i in items if i.strip()))[:MAX_ITEMS]
    note = note.strip()
    if not cleaned and not note:
        raise CreditBridgeError(tr("요청할 자료를 하나 이상 고르거나 메모를 적어 주세요."))
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    request = request_repo.get(session, evaluation.transfer_request_id) if evaluation.transfer_request_id else None
    if syllabus is None or request is None:
        raise NotFoundError(tr("심사 건을 찾을 수 없어요."))
    material = material_repo.add(
        session,
        MaterialRequest(
            syllabus_id=syllabus.id,
            course_evaluation_id=evaluation.id,
            requested_by=actor.id,
            items=cleaned,
            note=note,
        ),
    )
    student = [u for u in [_user(session, request.student_id)] if u is not None]
    notifications.notify(
        session,
        student,
        "material.request",
        N_("{course} 과목에 보완 자료 요청이 왔어요: {items}").format(
            course=_course(syllabus), items=", ".join(cleaned) or note[:80]
        ),
        f"/student/evaluations/{evaluation.id}",
    )
    audit.record(session, actor, "material.request", "course_evaluation", str(evaluation.id), items=len(cleaned))
    session.commit()
    return material


def mark_fulfilled(session: Session, actor: User, syllabus: Syllabus) -> list[MaterialRequest]:
    """보완 자료가 올라왔을 때(학생 본인 또는 심사관 대신) 열려 있는 요청을 모두 처리됨으로 바꾸고 요청자에게 알린다.
    커밋은 호출자가 한다."""
    open_requests = material_repo.open_for_syllabus(session, syllabus.id)
    for m in open_requests:
        m.status = MaterialRequestStatus.FULFILLED
        m.fulfilled_at = utcnow()
        requester = _user(session, m.requested_by)
        if requester is not None:
            link = (
                f"/professor/evaluations/{m.course_evaluation_id}"
                if requester.role == Role.PROFESSOR
                else f"/review/evaluations/{m.course_evaluation_id}"
            )
            notifications.notify(
                session,
                [requester],
                "material.fulfilled",
                N_("{course} 보완 자료가 도착했어요. 다시 분석한 결과를 확인해 주세요.").format(
                    course=_course(syllabus)
                ),
                link,
            )
        audit.record(session, actor, "material.fulfilled", "material_request", str(m.id))
    return open_requests


def open_for_syllabus(session: Session, syllabus_id: int) -> list[MaterialRequest]:
    return material_repo.open_for_syllabus(session, syllabus_id)


def for_syllabi(session: Session, syllabus_ids: list[int]) -> list[MaterialRequest]:
    return material_repo.for_syllabi(session, syllabus_ids)


def _course(syllabus: Syllabus) -> str:
    return (syllabus.course_code or syllabus.course_title or N_("강의계획서")).strip()


def _user(session: Session, user_id: int) -> User | None:
    return user_repo.get_by_id(session, user_id)
