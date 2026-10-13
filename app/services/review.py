"""심사관 업무: 심사 큐(FR-17), 교수 자동 배정(FR-18), 부재 시 대리 재배정(FR-19)."""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from app.models import Assignment, Course, CourseEvaluation, Syllabus, TransferRequest, User
from app.models.enums import Role
from app.repositories import catalog as catalog_repo
from app.repositories import evaluations as evaluation_repo
from app.repositories import users as user_repo
from app.services import audit

TABS = {"high": "고신뢰", "low": "저신뢰", "insufficient": "정보 부족"}


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


def tab_of(evaluation: CourseEvaluation) -> str:
    if evaluation.recommendation == "insufficient":
        return "insufficient"
    return "high" if evaluation.confidence == "high" else "low"


def ensure_evaluator(user: User) -> int:
    if user.role != Role.EVALUATOR or user.institution_id is None:
        raise PermissionDeniedError("심사관 계정만 사용할 수 있어요.")
    return user.institution_id


def queue(
    session: Session, evaluator: User, tab: str, department: str | None, sort: str
) -> tuple[list[QueueRow], dict[str, int], list[str]]:
    institution_id = ensure_evaluator(evaluator)
    raw = evaluation_repo.review_queue(session, institution_id)
    courses = catalog_repo.courses_by_ids(session, [e.candidate_course_id for e, _, _ in raw if e.candidate_course_id])
    rows: list[QueueRow] = []
    counts = dict.fromkeys(TABS, 0)
    departments: set[str] = set()
    for evaluation, syllabus, request in raw:
        course = courses.get(evaluation.candidate_course_id) if evaluation.candidate_course_id else None
        dept = course.department if course else "미분류"
        departments.add(dept)
        t = tab_of(evaluation)
        counts[t] += 1
        if t != tab or (department and dept != department):
            continue
        assignment = evaluation_repo.active_assignment(session, evaluation.id)
        reviewer = user_repo.get_by_id(session, assignment.reviewer_id) if assignment else None
        rows.append(
            QueueRow(
                evaluation,
                syllabus,
                request,
                course,
                dept,
                assignment,
                reviewer,
                bool(assignment and assignment.reassigned_from),
            )
        )
    if sort == "coverage":
        rows.sort(key=lambda r: r.evaluation.coverage or 0, reverse=True)
    elif sort == "department":
        rows.sort(key=lambda r: r.department)
    return rows, counts, sorted(departments)


def _pick_reviewer(session: Session, institution_id: int, department: str, today: date) -> tuple[User, User | None]:
    """담당 교수 중 배정이 가장 적은 사람. 부재 중이면 대리 심사자 (반환: 실제 배정자, 원래 배정자)."""
    professors = user_repo.professors_in(session, institution_id, department)
    if not professors:
        raise CreditBridgeError(f"{department} 학과에 등록된 심사 교수가 없어요.")
    available = [p for p in professors if not p.is_away(today)] or professors
    chosen = min(available, key=lambda p: len(evaluation_repo.active_assignments_for(session, p.id)))
    if chosen.is_away(today) and chosen.delegate_user_id:
        delegate = user_repo.get_by_id(session, chosen.delegate_user_id)
        if delegate is not None:
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
            reviewer, original = _pick_reviewer(session, institution_id, course.department, today)
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
    if target is not None:
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
    audit.record(session, professor, "professor.away", "user", str(professor.id), days=days, moved=moved)
    session.commit()
    return moved
