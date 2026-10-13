"""화면에 필요한 데이터를 모으는 조회 서비스. web 계층은 repositories를 직접 부르지 않고 이 모듈을 쓴다."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import (
    Assignment,
    AuditLog,
    Course,
    CourseEvaluation,
    Decision,
    Institution,
    Syllabus,
    TranscriptEntry,
    TransferRequest,
    User,
)
from app.repositories import audit as audit_repo
from app.repositories import catalog as catalog_repo
from app.repositories import decisions as decision_repo
from app.repositories import evaluations as evaluation_repo
from app.repositories import requests as request_repo
from app.repositories import syllabi as syllabus_repo
from app.repositories import users as user_repo
from app.schemas.extraction import SyllabusExtraction
from app.schemas.results import CandidateResult, EvaluationResult
from app.security.permissions import ensure_can_view_evaluation
from app.services import student as student_service
from app.services.decisions import HistoryItem, history


@dataclass
class EvaluationView:
    evaluation: CourseEvaluation
    syllabus: Syllabus
    request: TransferRequest
    result: EvaluationResult | None
    extraction: SyllabusExtraction | None
    candidate: Course | None
    decision: Decision | None = None
    decided_by: User | None = None
    decided_target: Course | None = None
    assignment: Assignment | None = None
    reviewer: User | None = None
    history: list[HistoryItem] = field(default_factory=list)
    previous: list[CourseEvaluation] = field(default_factory=list)
    audit: list[AuditLog] = field(default_factory=list)
    target_courses: list[Course] = field(default_factory=list)

    @property
    def primary(self) -> CandidateResult | None:
        return self.result.candidates[0] if self.result and self.result.candidates else None


def evaluation_view(session: Session, user: User, evaluation_id: int, *, with_audit: bool = False) -> EvaluationView:
    evaluation = evaluation_repo.get(session, evaluation_id)
    if evaluation is None:
        raise NotFoundError("분석 결과를 찾을 수 없어요.")
    ensure_can_view_evaluation(session, user, evaluation)
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    request = request_repo.get(session, evaluation.transfer_request_id) if evaluation.transfer_request_id else None
    if syllabus is None or request is None:
        raise NotFoundError("분석 결과를 찾을 수 없어요.")
    decision = decision_repo.for_evaluation(session, evaluation.id)
    assignment = evaluation_repo.active_assignment(session, evaluation.id)
    view = EvaluationView(
        evaluation=evaluation,
        syllabus=syllabus,
        request=request,
        result=EvaluationResult.model_validate(evaluation.coverage_json) if evaluation.coverage_json else None,
        extraction=SyllabusExtraction.from_stored(syllabus.extracted_json),
        candidate=catalog_repo.get_course(session, evaluation.candidate_course_id)
        if evaluation.candidate_course_id
        else None,
        decision=decision,
        decided_by=user_repo.get_by_id(session, decision.decided_by) if decision else None,
        decided_target=catalog_repo.get_course(session, decision.target_course_id)
        if decision and decision.target_course_id
        else None,
        assignment=assignment,
        reviewer=user_repo.get_by_id(session, assignment.reviewer_id) if assignment else None,
        history=history(session, evaluation),
        previous=[e for e in evaluation_repo.history_for_syllabus(session, syllabus.id) if e.id != evaluation.id],
    )
    if with_audit:
        view.audit = audit_repo.for_target(session, "course_evaluation", str(evaluation.id))
    if user.role == "professor":
        view.target_courses = catalog_repo.courses_of(session, request.target_institution_id)
    return view


def latest_evaluation_id(session: Session, user: User, syllabus_id: int) -> int | None:
    syllabus = syllabus_repo.get(session, syllabus_id)
    if syllabus is None:
        return None
    ev = evaluation_repo.latest_for_syllabus(session, syllabus.id)
    if ev is None:
        return None
    ensure_can_view_evaluation(session, user, ev)
    return ev.id


@dataclass
class RequestView:
    request: TransferRequest
    rows: list[student_service.CourseRow]
    entries: list[TranscriptEntry]
    simulation: student_service.Simulation
    processing: bool


def request_view(
    session: Session, student: User, request_id: int, tuition: int | None, degree: int | None
) -> RequestView:
    request = student_service.get_own_request(session, student, request_id)
    rows = student_service.course_rows(session, request)
    target = request.target_institution
    simulation = student_service.simulate(
        rows,
        degree_credits=degree or target.degree_credits or 120,
        tuition_per_credit=tuition if tuition is not None else (target.tuition_per_credit or 1000),
    )
    processing = any(
        r.syllabus.status in ("uploaded", "processing")
        or (r.evaluation and r.evaluation.status in ("queued", "running"))
        for r in rows
    )
    return RequestView(request, rows, request_repo.transcript_entries(session, request.id), simulation, processing)


@dataclass
class StudentHome:
    requests: list[TransferRequest]
    sources: list[Institution]
    target: Institution | None  # 입학이 확정된 소속 대학
    majors: list[str]


def student_home(session: Session, student: User) -> StudentHome:
    target = catalog_repo.get_institution(session, student.institution_id) if student.institution_id else None
    if target is not None and not target.is_target:
        target = None
    return StudentHome(
        requests=request_repo.of_student(session, student.id),
        sources=catalog_repo.source_institutions(session),
        target=target,
        majors=catalog_repo.departments_of(session, target.id) if target else [],
    )


def own_syllabus(session: Session, student: User, syllabus_id: int) -> Syllabus:
    syllabus = syllabus_repo.get(session, syllabus_id)
    if syllabus is None or syllabus.owner_id != student.id:
        raise NotFoundError("강의계획서를 찾을 수 없어요.")
    return syllabus


@dataclass
class ProfessorItem:
    evaluation: CourseEvaluation
    syllabus: Syllabus
    candidate: Course | None
    assignment: Assignment
    delegated_from: User | None


def professor_items(session: Session, professor: User) -> list[ProfessorItem]:
    items = []
    for a in evaluation_repo.active_assignments_for(session, professor.id):
        ev = evaluation_repo.get(session, a.course_evaluation_id)
        if ev is None or decision_repo.for_evaluation(session, ev.id) is not None:
            continue
        syllabus = syllabus_repo.get(session, ev.syllabus_id)
        if syllabus is None:
            continue
        items.append(
            ProfessorItem(
                evaluation=ev,
                syllabus=syllabus,
                candidate=catalog_repo.get_course(session, ev.candidate_course_id) if ev.candidate_course_id else None,
                assignment=a,
                delegated_from=user_repo.get_by_id(session, a.reassigned_from) if a.reassigned_from else None,
            )
        )
    return items


def colleagues(session: Session, professor: User) -> list[User]:
    return [
        p
        for p in user_repo.professors_in(session, professor.institution_id or 0, professor.department or "")
        if p.id != professor.id
    ]


def recent_audit(session: Session) -> list[AuditLog]:
    return audit_repo.recent(session)


def export_rows(session: Session, evaluator: User) -> list[dict[str, Any]]:
    """확정 판정 CSV 내보내기 (FR-24, 모의 SIS 연동)."""
    rows = decision_repo.all_for_institution(session, evaluator.institution_id or 0)
    courses = catalog_repo.courses_by_ids(session, [d.target_course_id for d, _, _ in rows if d.target_course_id])
    out = []
    for d, e, s in rows:
        request = request_repo.get(session, e.transfer_request_id) if e.transfer_request_id else None
        student = user_repo.get_by_id(session, request.student_id) if request else None
        out.append(
            {
                "student_id": student.id if student else "",
                "source_course": s.course_code or s.course_title,
                "result": d.result,
                "target_course": courses[d.target_course_id].code if d.target_course_id in courses else "",
                "credits": s.credits if s.credits is not None else "",
                "decided_at": d.decided_at.isoformat(timespec="seconds"),
                "decision_id": d.id,
            }
        )
    return out


def request_id_of(session: Session, syllabus: Syllabus) -> int:
    request = request_repo.get(session, syllabus.transfer_request_id) if syllabus.transfer_request_id else None
    if request is None:
        raise NotFoundError("편입 요청을 찾을 수 없어요.")
    return request.id
