"""화면에 필요한 데이터를 모으는 조회 서비스. web 계층은 repositories를 직접 부르지 않고 이 모듈을 쓴다."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.errors import NotFoundError, PermissionDeniedError
from backend.models import (
    Appeal,
    AppealFile,
    Assignment,
    AuditLog,
    Course,
    CourseEvaluation,
    Decision,
    Institution,
    MaterialRequest,
    PrivacyRequest,
    Syllabus,
    TranscriptEntry,
    TransferRequest,
    User,
)
from backend.models.enums import Role
from backend.repositories import audit as audit_repo
from backend.repositories import catalog as catalog_repo
from backend.repositories import decisions as decision_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.schemas.extraction import SyllabusExtraction
from backend.schemas.results import CandidateResult, EvaluationResult
from backend.security.permissions import ensure_can_view_evaluation
from backend.services import appeals as appeal_service
from backend.services import institution_data as institution_service
from backend.services import materials as material_service
from backend.services import notifications as notification_service
from backend.services import privacy as privacy_service
from backend.services import reminders as reminder_service
from backend.services import review as review_service
from backend.services import sis as sis_service
from backend.services import student as student_service
from backend.services.decisions import HistoryItem, history


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
    decisions: list[Decision] = field(default_factory=list)  # 원 판정과 이의 신청 재판정, 오래된 순
    appeals: list[Appeal] = field(default_factory=list)
    appeal_files: dict[int, list[AppealFile]] = field(default_factory=dict)  # 이의 신청 id -> 근거 자료
    material_requests: list[MaterialRequest] = field(default_factory=list)
    suggested_materials: list[str] = field(default_factory=list)
    target_text: str = ""  # 1순위 후보의 기준 강의계획서 원문 (근거 위치 이동, FR-25)
    users: dict[int, User] = field(default_factory=dict)  # 판정자·요청자 이름 표시용

    @property
    def primary(self) -> CandidateResult | None:
        return self.result.candidates[0] if self.result and self.result.candidates else None

    @property
    def open_appeal(self) -> Appeal | None:
        return next((a for a in self.appeals if a.status in ("submitted", "accepted")), None)

    @property
    def awaiting_redecision(self) -> bool:
        return any(a.status == "accepted" for a in self.appeals)

    @property
    def open_materials(self) -> list[MaterialRequest]:
        return [m for m in self.material_requests if m.status == "open"]

    @property
    def source_marks(self) -> list[tuple[int, int]]:
        if not self.result:
            return []
        return [
            (e.char_start, e.char_end) for c in self.result.candidates for k in c.concepts for e in k.source_evidence
        ]

    @property
    def target_marks(self) -> list[tuple[int, int]]:
        primary = self.primary
        if primary is None:
            return []
        return [(e.char_start, e.char_end) for k in primary.concepts for e in k.target_evidence]


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
    view.decisions = decision_repo.for_evaluation_all(session, evaluation.id)
    view.appeals = appeal_service.for_evaluation(session, evaluation.id)
    view.appeal_files = appeal_service.files_for(session, [a.id for a in view.appeals])
    view.material_requests = material_service.for_syllabi(session, [syllabus.id])
    suggested = view.result.missing_materials if view.result else []
    view.suggested_materials = list(dict.fromkeys([*suggested, *material_service.STANDARD_ITEMS]))
    if view.candidate is not None and view.candidate.reference_syllabus_id:
        reference = syllabus_repo.get(session, view.candidate.reference_syllabus_id)
        view.target_text = reference.raw_text if reference else ""
    user_ids = {d.decided_by for d in view.decisions} | {m.requested_by for m in view.material_requests}
    user_ids |= {a.handled_by for a in view.appeals if a.handled_by}
    view.users = {uid: u for uid in user_ids if (u := user_repo.get_by_id(session, uid)) is not None}
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
    privacy: PrivacyRequest | None = None
    show: str = "all"  # 과목 목록 필터: all / approved / supplement / review

    @property
    def open_materials(self) -> int:
        return sum(len(r.open_materials) for r in self.rows)

    @property
    def visible_rows(self) -> list[student_service.CourseRow]:
        return self.rows if self.show == "all" else [r for r in self.rows if r.group == self.show]

    @property
    def group_counts(self) -> dict[str, int]:
        counts = {"all": len(self.rows), "approved": 0, "supplement": 0, "review": 0, "other": 0}
        for r in self.rows:
            counts[r.group] += 1
        return counts

    @property
    def decided_count(self) -> int:
        return sum(1 for r in self.rows if r.decision is not None)

    @property
    def last_analyzed(self) -> datetime | None:
        times = [r.evaluation.created_at for r in self.rows if r.evaluation is not None]
        return max(times) if times else None

    @property
    def analysis_done(self) -> bool:
        return bool(self.rows) and not self.processing


def request_view(
    session: Session, student: User, request_id: int, tuition: int | None, degree: int | None, show: str = "all"
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
    return RequestView(
        request,
        rows,
        request_repo.transcript_entries(session, request.id),
        simulation,
        processing,
        privacy_service.latest_for_request(session, request),
        show if show in ("all", "approved", "supplement", "review") else "all",
    )


@dataclass(frozen=True)
class RequestSummary:
    """학생 홈 대시보드의 편입 요청 한 건: 예상 인정 학점, 판정 진행, 서류 준비율과 할 일."""

    request: TransferRequest
    simulation: student_service.Simulation
    readiness: student_service.Readiness
    courses: int
    decided: int


@dataclass
class StudentHome:
    requests: list[TransferRequest]
    sources: list[Institution]
    target: Institution | None  # 입학이 확정된 소속 대학
    majors: list[str]
    summaries: list[RequestSummary] = field(default_factory=list)
    unread_results: int = 0  # 아직 열어 보지 않은 판정 결과 알림

    @property
    def todos(self) -> list[tuple[TransferRequest, student_service.Todo]]:
        return [(s.request, t) for s in self.summaries for t in s.readiness.todos]


def student_home(session: Session, student: User) -> StudentHome:
    target = catalog_repo.get_institution(session, student.institution_id) if student.institution_id else None
    if target is not None and not target.is_target:
        target = None
    requests = request_repo.of_student(session, student.id)
    summaries = []
    for r in requests:
        rows = student_service.course_rows(session, r)
        inst = r.target_institution
        summaries.append(
            RequestSummary(
                r,
                student_service.simulate(rows, inst.degree_credits or 120, inst.tuition_per_credit or 1000),
                student_service.readiness(session, r),
                len(rows),
                sum(1 for row in rows if row.decision is not None),
            )
        )
    return StudentHome(
        requests=requests,
        sources=catalog_repo.source_institutions(session),
        target=target,
        majors=catalog_repo.departments_of(session, target.id) if target else [],
        summaries=summaries,
        unread_results=notification_service.unread_of_kinds(session, student, notification_service.RESULT_KINDS),
    )


@dataclass(frozen=True)
class StudentBadges:
    """학생 메뉴 배지. missing: 채워야 할 서류(앰버), results·appeal_results: 새로 도착한 결과(파랑),
    appealable: 이의 신청할 수 있는 과목 수(중립)."""

    missing: int
    results: int
    appeal_results: int
    appealable: int


def student_badges(session: Session, student: User) -> StudentBadges:
    missing = sum(student_service.readiness(session, r).missing for r in request_repo.of_student(session, student.id))
    return StudentBadges(
        missing,
        notification_service.unread_of_kinds(session, student, notification_service.RESULT_KINDS),
        notification_service.unread_of_kinds(session, student, notification_service.APPEAL_RESULT_KINDS),
        len(appeal_service.appealable(session, student)),
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
    appeal: Appeal | None = None  # 이의 신청 재판정 건


def professor_items(session: Session, professor: User) -> list[ProfessorItem]:
    items = []
    for a in evaluation_repo.active_assignments_for(session, professor.id):
        ev = evaluation_repo.get(session, a.course_evaluation_id)
        if ev is None or not ev.is_latest:
            continue
        appeal = appeal_service.accepted_for(session, ev.id)
        if decision_repo.for_evaluation(session, ev.id) is not None and appeal is None:
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
                appeal=appeal,
            )
        )
    return items


def colleagues(session: Session, professor: User) -> list[User]:
    return [
        p
        for p in user_repo.professors_in(session, professor.institution_id or 0, professor.department or "")
        if p.id != professor.id
    ]


def reminder_preview(session: Session, user: User) -> reminder_service.Plan:
    """운영 통계 화면의 '기한 알림' 카드: 오늘 기한 알림을 받을 대상 (심사관·관리자)."""
    if user.role not in (Role.EVALUATOR, Role.ADMIN) or user.institution_id is None:
        raise PermissionDeniedError("심사관과 기관 관리자만 볼 수 있어요.")
    return reminder_service.plan(session, user.institution_id)


def recent_audit(session: Session, admin: User) -> list[AuditLog]:
    """전체 감사 로그 화면: 관리자 소속 기관 사용자의 기록만 (다른 기관 기록은 보이지 않는다)."""
    if admin.role != Role.ADMIN or admin.institution_id is None:
        raise PermissionDeniedError("기관 관리자만 볼 수 있어요.")
    return audit_repo.recent_for_institution(session, admin.institution_id)


def export_rows(session: Session, evaluator: User) -> list[dict[str, Any]]:
    """확정 판정 CSV 내보내기 (FR-24, 모의 SIS 연동)."""
    return sis_service.export_rows(session, evaluator.institution_id or 0)


def request_id_of(session: Session, syllabus: Syllabus) -> int:
    request = request_repo.get(session, syllabus.transfer_request_id) if syllabus.transfer_request_id else None
    if request is None:
        raise NotFoundError("편입 요청을 찾을 수 없어요.")
    return request.id


# ---------- 메뉴 배지 ----------

# (숫자, 톤, 화면 읽기 프로그램용 설명). 톤: todo(앰버, 처리할 일) / new(파랑, 새 결과) / count(중립, 참고 개수)
Badge = tuple[int, str, str]


def nav_badges(session: Session, user: User) -> dict[str, list[Badge]]:
    """역할별 상단 메뉴 숫자 배지 (메뉴 주소 → 배지). 기관 전체 집계가 아니라 그 사람이 처리할 일만 센다."""
    if user.role == Role.STUDENT:
        b = student_badges(session, user)
        return {
            "/student": [
                (b.missing, "todo", f"채워야 할 서류 {b.missing}건"),
                (b.results, "new", f"새 판정 결과 {b.results}건"),
            ],
            "/student/appeals": [
                (b.appealable, "count", f"이의 신청할 수 있는 과목 {b.appealable}개"),
                (b.appeal_results, "new", f"새 이의 신청 결과 {b.appeal_results}건"),
            ],
        }
    if user.role == Role.EVALUATOR:
        unassigned = review_service.unassigned_count(session, user)
        appeals = appeal_service.submitted_count(session, user)
        privacy = privacy_service.pending_count(session, user)
        return {
            "/review": [(unassigned, "todo", f"교수 배정이 필요한 과목 {unassigned}개")],
            "/review/appeals": [(appeals, "todo", f"처리할 이의 신청 {appeals}건")],
            "/review/privacy": [(privacy, "todo", f"처리할 삭제 요청 {privacy}건")],
        }
    if user.role == Role.PROFESSOR:
        pending = len(professor_items(session, user))
        return {"/professor": [(pending, "todo", f"판정할 심사 {pending}건")]}
    if user.role == Role.ADMIN and user.institution_id is not None:
        overview = institution_service.overview(session, user)
        setup = overview.missing_reference + len(overview.departments_without_professor)
        privacy = privacy_service.pending_count(session, user)
        return {
            "/admin/data": [
                (
                    setup,
                    "todo",
                    f"준비가 필요한 항목 {setup}건 (기준 강의계획서 없는 과목 {overview.missing_reference}개, "
                    f"교수가 없는 학과 {len(overview.departments_without_professor)}개)",
                )
            ],
            "/admin/privacy": [(privacy, "todo", f"승인할 삭제 요청 {privacy}건")],
        }
    return {}
