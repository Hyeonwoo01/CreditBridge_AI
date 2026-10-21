"""심사관 업무: 심사 큐(FR-17), 교수 자동 배정(FR-18), 부재 시 대리 재배정(FR-19)."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import Assignment, Course, CourseEvaluation, Department, Syllabus, TransferRequest, User
from backend.models.enums import EvaluationStatus, Recommendation, RequestStatus, Role
from backend.repositories import catalog as catalog_repo
from backend.repositories import decisions as decision_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import materials as material_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.services import audit, notifications
from backend.services.decisions import HistoryItem, ai_result, close_request_if_done, conflicts, history

# 심사 큐 필터. all 외에는 겹치지 않는 신뢰도 구분이고, conflict는 과거 판정과 어긋나는 건만 따로 모아 본다
TABS = {
    "all": N_("전체"),
    "high": N_("고신뢰"),
    "low": N_("저신뢰"),
    "insufficient": N_("정보 부족"),
    "conflict": N_("일관성 경보"),
}
PAGE_SIZE = 20


@dataclass(frozen=True)
class QueueRow:
    evaluation: CourseEvaluation
    syllabus: Syllabus
    request: TransferRequest
    course: Course | None
    department: str
    assignment: Assignment | None
    reviewer: User | None
    delegated: bool
    student: User | None = None
    # 같은 출신 과목·대상 과목·유사한 강의계획서로 내린 과거 판정 중 AI 추천과 결과가 다른 것
    conflicts: list[HistoryItem] = field(default_factory=list)
    open_materials: int = 0

    @property
    def tab(self) -> str:
        return tab_of(self.evaluation)


@dataclass(frozen=True)
class QueueView:
    rows: list[QueueRow]  # 현재 페이지
    counts: dict[str, int]
    departments: list[tuple[str, int]]
    total: int  # 필터 적용 후 전체 건수
    page: int
    pages: int


def tab_of(evaluation: CourseEvaluation) -> str:
    if evaluation.recommendation == "insufficient":
        return "insufficient"
    return "high" if evaluation.confidence == "high" else "low"


def ensure_evaluator(user: User) -> int:
    if user.role != Role.EVALUATOR or user.institution_id is None:
        raise PermissionDeniedError(tr("심사관 계정만 사용할 수 있어요."))
    return user.institution_id


def ensure_assigner(user: User) -> int:
    """교수 배정·재배정: 심사관과 기관 관리자 (권한 매트릭스)."""
    if user.role not in (Role.EVALUATOR, Role.ADMIN) or user.institution_id is None:
        raise PermissionDeniedError(tr("심사관이나 기관 관리자만 교수를 배정할 수 있어요."))
    return user.institution_id


def unassigned_count(session: Session, user: User) -> int:
    """심사관·관리자 메뉴 배지: 판정 전인데 담당 교수가 아직 없는 과목 수."""
    institution_id = ensure_assigner(user)
    return sum(
        1
        for evaluation, _, _ in evaluation_repo.review_queue(session, institution_id)
        if evaluation_repo.active_assignment(session, evaluation.id) is None
    )


def _matches(row: QueueRow, q: str) -> bool:
    haystack = " ".join(
        [
            row.student.name if row.student else "",
            row.syllabus.course_code,
            row.syllabus.course_title,
            row.request.source_institution.name,
            row.course.code if row.course else "",
            row.course.title if row.course else "",
            f"#{row.request.id}",
        ]
    ).lower()
    return all(term in haystack for term in q.lower().split())


def queue(
    session: Session,
    evaluator: User,
    tab: str,
    department: str | None,
    sort: str,
    q: str = "",
    page: int = 1,
) -> QueueView:
    institution_id = ensure_evaluator(evaluator)
    raw = evaluation_repo.review_queue(session, institution_id)
    courses = catalog_repo.courses_by_ids(session, [e.candidate_course_id for e, _, _ in raw if e.candidate_course_id])
    materials = material_repo.for_syllabi(session, [s.id for _, s, _ in raw])
    open_by_syllabus: dict[int, int] = {}
    for m in materials:
        if m.status == "open":
            open_by_syllabus[m.syllabus_id] = open_by_syllabus.get(m.syllabus_id, 0) + 1
    rows: list[QueueRow] = []
    for evaluation, syllabus, request in raw:
        course = courses.get(evaluation.candidate_course_id) if evaluation.candidate_course_id else None
        assignment = evaluation_repo.active_assignment(session, evaluation.id)
        reviewer = user_repo.get_by_id(session, assignment.reviewer_id) if assignment else None
        rows.append(
            QueueRow(
                evaluation=evaluation,
                syllabus=syllabus,
                request=request,
                course=course,
                department=course.department_name if course else tr("미분류"),
                assignment=assignment,
                reviewer=reviewer,
                delegated=bool(assignment and assignment.reassigned_from),
                student=user_repo.get_by_id(session, request.student_id),
                conflicts=conflicts(history(session, evaluation), ai_result(evaluation)),
                open_materials=open_by_syllabus.get(syllabus.id, 0),
            )
        )
    counts = dict.fromkeys(TABS, 0)
    dept_counts: dict[str, int] = {}
    for r in rows:
        counts["all"] += 1
        counts[r.tab] += 1
        counts["conflict"] += bool(r.conflicts)
        dept_counts[r.department] = dept_counts.get(r.department, 0) + 1
    picked = [
        r
        for r in rows
        if (tab == "all" or (r.conflicts if tab == "conflict" else r.tab == tab))
        and (not department or r.department == department)
        and (not q.strip() or _matches(r, q))
    ]
    if sort == "coverage":
        picked.sort(key=lambda r: r.evaluation.coverage or 0, reverse=True)
    elif sort == "department":
        picked.sort(key=lambda r: r.department)
    pages = max((len(picked) + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(max(page, 1), pages)
    return QueueView(
        rows=picked[(page - 1) * PAGE_SIZE : page * PAGE_SIZE],
        counts=counts,
        departments=sorted(dept_counts.items()),
        total=len(picked),
        page=page,
        pages=pages,
    )


def pick_reviewer(
    session: Session, institution_id: int, department: Department | None, today: date
) -> tuple[User, User | None]:
    """담당 교수 중 배정이 가장 적은 사람. 부재 중이면 대리 심사자 (반환: 실제 배정자, 원래 배정자)."""
    professors = user_repo.professors_in(session, institution_id, department.id if department else None)
    if not professors:
        name = department.name if department else tr("미분류")
        raise CreditBridgeError(tr("{department} 학과에 등록된 심사 교수가 없어요.", department=name))
    available = [p for p in professors if not p.is_away(today)] or professors
    chosen = min(available, key=lambda p: len(evaluation_repo.active_assignments_for(session, p.id)))
    if chosen.is_away(today) and chosen.delegate_user_id:
        delegate = user_repo.get_by_id(session, chosen.delegate_user_id)
        if delegate is not None and delegate.is_active:
            return delegate, chosen
    return chosen, None


def _assign_by_department(
    session: Session, institution_id: int, evaluation: CourseEvaluation, actor: User | None
) -> str | None:
    """후보 과목의 학과 교수 중 배정이 가장 적은 사람에게 배정한다. 못 하면 이유(화면 문구)를 돌려준다.
    actor가 None이면 학생 제출 때의 자동 배정(시스템)."""
    course = (
        catalog_repo.get_course(session, evaluation.candidate_course_id) if evaluation.candidate_course_id else None
    )
    if course is None or course.institution_id != institution_id:
        return tr(
            "후보 과목이 없는 건은 학과를 정할 수 없어요. 심사 건 화면의 '담당 교수 배정'에서 교수를 골라 주세요."
        )
    try:
        reviewer, original = pick_reviewer(session, institution_id, course.dept, utcnow().date())
    except CreditBridgeError as exc:
        return str(exc)
    evaluation_repo.add_assignment(
        session,
        Assignment(
            course_evaluation_id=evaluation.id,
            reviewer_id=reviewer.id,
            assigned_by=actor.id if actor else None,
            reassigned_from=original.id if original else None,
        ),
    )
    notifications.notify(
        session,
        [reviewer],
        "assignment.created",
        (
            N_("새 심사가 배정됐어요: {course} → {code} (부재 교수 대리)")
            if original
            else N_("새 심사가 배정됐어요: {course} → {code}")
        ).format(course=_course(session, evaluation), code=course.code),
        f"/professor/evaluations/{evaluation.id}",
    )
    audit.record(
        session,
        actor,
        "assignment.create",
        "course_evaluation",
        str(evaluation.id),
        reviewer=reviewer.id,
        delegated_from=original.id if original else None,
        auto=actor is None,
    )
    return None


def auto_assign(session: Session, evaluator: User, evaluation_ids: list[int]) -> tuple[int, list[str]]:
    """학과 담당 교수 중 배정이 가장 적은 사람에게 배정한다 (심사관·관리자). 이미 교수가 있는 건(제출 때 자동
    배정된 건 포함)은 건너뛴다 — 담당 교수를 바꾸려면 교수 지정 배정(assign_to)을 쓴다."""
    institution_id = ensure_assigner(evaluator)
    assigned, problems = 0, []
    for evaluation_id in evaluation_ids:
        evaluation = evaluation_repo.get(session, evaluation_id)
        if evaluation is None or evaluation_repo.active_assignment(session, evaluation.id) is not None:
            continue
        problem = _assign_by_department(session, institution_id, evaluation, evaluator)
        if problem:
            problems.append(problem)
        else:
            assigned += 1
    session.commit()
    return assigned, sorted(set(problems))


AUTO_ASSIGNABLE = (Recommendation.DIRECT, Recommendation.ELECTIVE, Recommendation.NONE)


def assign_ready(session: Session, request: TransferRequest) -> int:
    """학생이 심사를 요청했을 때(그리고 제출 뒤 보완 자료로 다시 분석이 끝났을 때), 정보가 충분한 과목은
    심사관을 거치지 않고 학과 교수에게 바로 배정한다. 배정한 건수를 돌려준다.

    정보가 충분하다 = 분석이 끝났고, 정보 부족이 아니고, 대응 과목(학과)을 찾았고, 열린 보완 요청이 없다.
    나머지(정보 부족·대응 과목 없음·학과에 교수 없음)는 심사 큐에 남아 심사관이 처리한다."""
    if request.status != RequestStatus.SUBMITTED:
        return 0
    syllabi = syllabus_repo.of_request(session, request.id)
    asked = {m.syllabus_id for m in material_repo.for_syllabi(session, [s.id for s in syllabi]) if m.status == "open"}
    failed = request_repo.grade_failed_syllabus_ids(session, [s.id for s in syllabi])
    assigned = 0
    for syllabus in syllabi:
        evaluation = evaluation_repo.latest_for_syllabus(session, syllabus.id)
        if (
            evaluation is None
            or syllabus.id in asked
            or syllabus.id in failed
            or evaluation.status != EvaluationStatus.DONE
            or evaluation.recommendation not in AUTO_ASSIGNABLE
            or evaluation.candidate_course_id is None
            or evaluation_repo.active_assignment(session, evaluation.id) is not None
            or decision_repo.for_evaluation(session, evaluation.id) is not None
        ):
            continue
        if _assign_by_department(session, request.target_institution_id, evaluation, None) is None:
            assigned += 1
    close_request_if_done(session, request)  # 모든 과목이 성적 기준 미달이면 판정할 것이 없다
    session.commit()
    return assigned


def release_grade_failed(session: Session, request: TransferRequest) -> int:
    """성적표 연결로 성적 기준 미달이 된 과목은 심사 대상에서 빠진다: 판정 전 배정을 끝내고 담당 교수에게 알린다.
    판정 기록은 만들지 않는다 (최종 판정은 사람만). 해제한 배정 수를 돌려준다."""
    if request.status != RequestStatus.SUBMITTED:
        return 0
    syllabi = syllabus_repo.of_request(session, request.id)
    released = 0
    for syllabus_id in request_repo.grade_failed_syllabus_ids(session, [s.id for s in syllabi]):
        evaluation = evaluation_repo.latest_for_syllabus(session, syllabus_id)
        if evaluation is None or decision_repo.for_evaluation(session, evaluation.id) is not None:
            continue
        reviewer_id = evaluation_repo.deactivate_assignment(session, evaluation.id)
        reviewer = user_repo.get_by_id(session, reviewer_id) if reviewer_id else None
        if reviewer is None:
            continue
        released += 1
        audit.record(session, None, "assignment.release", "course_evaluation", str(evaluation.id), reason="grade")
        notifications.notify(
            session,
            [reviewer],
            "assignment.closed",
            N_("성적 기준 미달로 심사 대상에서 빠져 요청 #{id}의 과목 배정이 해제됐어요.").format(id=request.id),
            "/professor",
        )
    close_request_if_done(session, request)
    session.commit()
    return released


def set_away(session: Session, professor: User, days: int, delegate_id: int | None) -> int:
    """부재 기간을 설정하고, 진행 중인 배정을 대리 심사자에게 넘긴다. 넘긴 건수를 돌려준다."""
    if professor.role != Role.PROFESSOR:
        raise PermissionDeniedError(tr("교수 계정만 부재 기간을 설정할 수 있어요."))
    if days <= 0:
        professor.away_until = None
        audit.record(session, professor, "professor.back", "user", str(professor.id))
        session.commit()
        return 0
    delegate = None
    if delegate_id:
        delegate = next(
            (
                p
                for p in user_repo.professors_in(session, professor.institution_id or 0, professor.department_id)
                if p.id == delegate_id and p.id != professor.id
            ),
            None,
        )
        if delegate is None:
            raise NotFoundError(tr("같은 학과의 대리 심사 교수를 선택해 주세요."))
        professor.delegate_user_id = delegate.id
    professor.away_until = utcnow().date() + timedelta(days=days)
    moved = 0
    target = delegate or (
        user_repo.get_by_id(session, professor.delegate_user_id) if professor.delegate_user_id else None
    )
    if target is not None and target.is_active:
        for a in evaluation_repo.active_assignments_for(session, professor.id):
            evaluation_repo.add_assignment(
                session,
                Assignment(
                    course_evaluation_id=a.course_evaluation_id,
                    reviewer_id=target.id,
                    assigned_by=professor.id,
                    reassigned_from=professor.id,
                ),
            )
            moved += 1
        if moved:
            # 대리 재배정 알림: 대리 심사자와 소속 기관 심사관 (FR-19, TC-15)
            notifications.notify(
                session,
                [target],
                "assignment.delegated",
                N_("부재 중인 교수의 심사 {n}건이 대리 배정됐어요.").format(n=moved),
                "/professor",
            )
            notifications.notify(
                session,
                notifications.staff(session, professor.institution_id or 0, Role.EVALUATOR),
                "assignment.delegated",
                N_("{dept} 교수 부재로 진행 중인 심사 {n}건이 대리 재배정됐어요.").format(
                    dept=professor.department_name or "", n=moved
                ),
                "/review",
            )
    audit.record(session, professor, "professor.away", "user", str(professor.id), days=days, moved=moved)
    session.commit()
    return moved


def _course(session: Session, evaluation: CourseEvaluation) -> str:
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    return (syllabus.course_code or syllabus.course_title).strip() if syllabus else N_("과목")


# ---------- 관리자 교수 배정 (권한 매트릭스: 교수 배정·재배정은 심사관·관리자) ----------


@dataclass(frozen=True)
class BoardRow:
    """관리자 배정 화면의 한 줄. 관리자는 AI 분석 결과를 보지 않으므로 추천·커버리지·후보 과목은 담지 않는다."""

    evaluation: CourseEvaluation
    syllabus: Syllabus
    request: TransferRequest
    department: Department | None  # 배정 기준 학과 (후보 과목의 학과)
    reviewer: User | None
    assigned_at: date | None
    delegated: bool
    default_reviewer_id: int | None  # 선택 상자 기본값: 지금 담당 교수, 없으면 그 학과 첫 교수
    auto: bool = False  # 학생이 심사를 요청할 때 시스템이 학과 교수에게 자동 배정


@dataclass(frozen=True)
class AssignmentBoard:
    rows: list[BoardRow]
    show: str  # unassigned / all
    unassigned: int
    total: int
    professors: list[User]  # 같은 기관 활성 교수 (학과·이름 순)


def assignment_board(session: Session, admin: User, show: str) -> AssignmentBoard:
    """판정 전 심사 건과 담당 교수. 관리자 전용."""
    if admin.role != Role.ADMIN or admin.institution_id is None:
        raise PermissionDeniedError(tr("기관 관리자만 사용할 수 있어요."))
    institution_id = admin.institution_id
    queue_rows = evaluation_repo.review_queue(session, institution_id)
    courses = catalog_repo.courses_by_ids(
        session, [e.candidate_course_id for e, _, _ in queue_rows if e.candidate_course_id]
    )
    professors = user_repo.professors_of(session, institution_id)
    first_of: dict[int, int] = {}
    for p in professors:
        if p.department_id is not None:
            first_of.setdefault(p.department_id, p.id)
    rows = []
    for evaluation, syllabus, request in queue_rows:
        course = courses.get(evaluation.candidate_course_id) if evaluation.candidate_course_id else None
        assignment = evaluation_repo.active_assignment(session, evaluation.id)
        reviewer = user_repo.get_by_id(session, assignment.reviewer_id) if assignment else None
        rows.append(
            BoardRow(
                evaluation=evaluation,
                syllabus=syllabus,
                request=request,
                department=course.dept if course else None,
                reviewer=reviewer,
                assigned_at=assignment.assigned_at.date() if assignment else None,
                delegated=bool(assignment and assignment.reassigned_from),
                default_reviewer_id=reviewer.id
                if reviewer
                else (first_of.get(course.department_id) if course else None),
                auto=bool(assignment and assignment.assigned_by is None),
            )
        )
    unassigned = sum(1 for r in rows if r.reviewer is None)
    show = show if show in ("unassigned", "all") else "unassigned"
    picked = [r for r in rows if show == "all" or r.reviewer is None]
    return AssignmentBoard(picked, show, unassigned, len(rows), professors)


@dataclass(frozen=True)
class AssignOptions:
    """심사관 심사 건 화면의 '담당 교수 배정' 선택 상자."""

    professors: list[User]  # 같은 기관 활성 교수 (학과·이름 순)
    default_reviewer_id: int | None  # 지금 담당 교수 → 후보 과목 학과 첫 교수 → 학생 편입 전공 학과 첫 교수


def assign_options(
    session: Session, user: User, evaluation: CourseEvaluation, request: TransferRequest
) -> AssignOptions:
    institution_id = ensure_assigner(user)
    professors = user_repo.professors_of(session, institution_id)
    current = evaluation_repo.active_assignment(session, evaluation.id)
    if current is not None:
        return AssignOptions(professors, current.reviewer_id)
    course = (
        catalog_repo.get_course(session, evaluation.candidate_course_id) if evaluation.candidate_course_id else None
    )
    # 후보 과목이 없으면(선택 인정·대응 과목 없음) 학생의 편입 전공 학과 교수를 먼저 보여 준다
    department = course.dept.name if course and course.dept else request.major
    default = next((p.id for p in professors if p.department_name == department), None)
    return AssignOptions(professors, default)


def assign_to(session: Session, user: User, evaluation_id: int, reviewer_id: int) -> User:
    """특정 교수에게 배정하거나 다른 교수로 바꾼다 (심사관·관리자). 이전 배정은 기록으로 남는다."""
    institution_id = ensure_assigner(user)
    evaluation = evaluation_repo.get(session, evaluation_id)
    in_queue = {e.id for e, _, _ in evaluation_repo.review_queue(session, institution_id)}
    if evaluation is None or evaluation.id not in in_queue:
        raise NotFoundError(tr("판정 전인 소속 기관 심사 건만 배정할 수 있어요."))
    reviewer = user_repo.get_by_id(session, reviewer_id)
    if (
        reviewer is None
        or reviewer.institution_id != institution_id
        or reviewer.role != Role.PROFESSOR
        or not reviewer.is_active
    ):
        raise CreditBridgeError(tr("우리 기관의 활성 교수를 골라 주세요."))
    current = evaluation_repo.active_assignment(session, evaluation.id)
    if current is not None and current.reviewer_id == reviewer.id:
        raise CreditBridgeError(tr("이미 그 교수에게 배정돼 있어요."))
    evaluation_repo.add_assignment(
        session,
        Assignment(
            course_evaluation_id=evaluation.id,
            reviewer_id=reviewer.id,
            assigned_by=user.id,
            # reassigned_from은 부재 대리 표시에 쓰므로 비운다. 이전 교수는 비활성 배정 행과 감사 로그에 남는다
        ),
    )
    notifications.notify(
        session,
        [reviewer],
        "assignment.created",
        N_("새 심사가 배정됐어요: {course}").format(course=_course(session, evaluation)),
        f"/professor/evaluations/{evaluation.id}",
    )
    if current is not None:
        previous = user_repo.get_by_id(session, current.reviewer_id)
        if previous is not None:
            notifications.notify(
                session,
                [previous],
                "assignment.moved",
                N_("{course} 심사가 다른 교수에게 넘어갔어요.").format(course=_course(session, evaluation)),
                "/professor",
            )
    audit.record(
        session,
        user,
        "assignment.create",
        "course_evaluation",
        str(evaluation.id),
        reviewer=reviewer.id,
        previous=current.reviewer_id if current else None,
    )
    session.commit()
    return reviewer
