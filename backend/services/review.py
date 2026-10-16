"""심사관 업무: 심사 큐(FR-17), 교수 자동 배정(FR-18), 부재 시 대리 재배정(FR-19)."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from backend.models import Assignment, Course, CourseEvaluation, Syllabus, TransferRequest, User
from backend.models.enums import Role
from backend.repositories import catalog as catalog_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import materials as material_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.services import audit, notifications
from backend.services.decisions import HistoryItem, ai_result, conflicts, history

# 심사 큐 필터. all 외에는 겹치지 않는 신뢰도 구분이고, conflict는 과거 판정과 어긋나는 건만 따로 모아 본다
TABS = {"all": "전체", "high": "고신뢰", "low": "저신뢰", "insufficient": "정보 부족", "conflict": "일관성 경보"}
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
        raise PermissionDeniedError("심사관 계정만 사용할 수 있어요.")
    return user.institution_id


def unassigned_count(session: Session, evaluator: User) -> int:
    """심사관 메뉴 배지: 판정 전인데 담당 교수가 아직 없는 과목 수."""
    institution_id = ensure_evaluator(evaluator)
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
                department=course.department if course else "미분류",
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


def pick_reviewer(session: Session, institution_id: int, department: str, today: date) -> tuple[User, User | None]:
    """담당 교수 중 배정이 가장 적은 사람. 부재 중이면 대리 심사자 (반환: 실제 배정자, 원래 배정자)."""
    professors = user_repo.professors_in(session, institution_id, department)
    if not professors:
        raise CreditBridgeError(f"{department} 학과에 등록된 심사 교수가 없어요.")
    available = [p for p in professors if not p.is_away(today)] or professors
    chosen = min(available, key=lambda p: len(evaluation_repo.active_assignments_for(session, p.id)))
    if chosen.is_away(today) and chosen.delegate_user_id:
        delegate = user_repo.get_by_id(session, chosen.delegate_user_id)
        if delegate is not None and delegate.is_active:
            return delegate, chosen
    return chosen, None


def auto_assign(session: Session, evaluator: User, evaluation_ids: list[int]) -> tuple[int, list[str]]:
    institution_id = ensure_evaluator(evaluator)
    today = utcnow().date()
    assigned, problems = 0, []
    for evaluation_id in evaluation_ids:
        evaluation = evaluation_repo.get(session, evaluation_id)
        if evaluation is None:
            continue
        course = (
            catalog_repo.get_course(session, evaluation.candidate_course_id) if evaluation.candidate_course_id else None
        )
        if course is None or course.institution_id != institution_id:
            problems.append("후보 과목이 없는 건은 학과를 정할 수 없어 직접 배정해야 해요.")
            continue
        try:
            reviewer, original = pick_reviewer(session, institution_id, course.department, today)
        except CreditBridgeError as exc:
            problems.append(str(exc))
            continue
        evaluation_repo.add_assignment(
            session,
            Assignment(
                course_evaluation_id=evaluation.id,
                reviewer_id=reviewer.id,
                assigned_by=evaluator.id,
                reassigned_from=original.id if original else None,
            ),
        )
        notifications.notify(
            session,
            [reviewer],
            "assignment.created",
            f"새 심사가 배정됐어요: {_course(session, evaluation)} → {course.code}"
            + (" (부재 교수 대리)" if original else ""),
            f"/professor/evaluations/{evaluation.id}",
        )
        audit.record(
            session,
            evaluator,
            "assignment.create",
            "course_evaluation",
            str(evaluation.id),
            reviewer=reviewer.id,
            delegated_from=original.id if original else None,
        )
        assigned += 1
    session.commit()
    return assigned, sorted(set(problems))


def set_away(session: Session, professor: User, days: int, delegate_id: int | None) -> int:
    """부재 기간을 설정하고, 진행 중인 배정을 대리 심사자에게 넘긴다. 넘긴 건수를 돌려준다."""
    if professor.role != Role.PROFESSOR:
        raise PermissionDeniedError("교수 계정만 부재 기간을 설정할 수 있어요.")
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
                for p in user_repo.professors_in(session, professor.institution_id or 0, professor.department or "")
                if p.id == delegate_id and p.id != professor.id
            ),
            None,
        )
        if delegate is None:
            raise NotFoundError("같은 학과의 대리 심사 교수를 선택해 주세요.")
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
                f"부재 중인 교수의 심사 {moved}건이 대리 배정됐어요.",
                "/professor",
            )
            notifications.notify(
                session,
                notifications.staff(session, professor.institution_id or 0, Role.EVALUATOR),
                "assignment.delegated",
                f"{professor.department or ''} 교수 부재로 진행 중인 심사 {moved}건이 대리 재배정됐어요.",
                "/review",
            )
    audit.record(session, professor, "professor.away", "user", str(professor.id), days=days, moved=moved)
    session.commit()
    return moved


def _course(session: Session, evaluation: CourseEvaluation) -> str:
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    return (syllabus.course_code or syllabus.course_title).strip() if syllabus else "과목"
