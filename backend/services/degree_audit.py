"""Degree Audit 기본 기능 (리뷰 v3 P1-6, 13.9): 인정 학점을 졸업 요건에 연결한다.

학점 인정 심사와 따로 둔다. 인정이 끝났다고 졸업 요건 충족을 확정하지 않으며, 화면에는 '공식 졸업 판정은 학사 담당자
확인이 필요하다'고 쓴다.

- 학생 프로그램: 학생의 편입 전공(학과)·입학연도가 맞는 프로그램 중 가장 구체적인 것. 없거나 같은 구체성에서 둘 이상이면
  미정(unresolved)으로 두고 졸업 가능 여부를 단정하지 않는다.
- 배정 규칙(같은 학점을 두 요건에 세지 않음): 승인된 배분 원장의 줄마다 대상 과목이 요건의 과목 목록에 있으면 그 요건
  (정렬 순서상 처음), 아니면 일반 선택. 필요 학점을 넘는 학점은 일반 선택으로 넘기고, 일반 선택이 없으면 '배정 안 됨'.
- 확정 학점(원장)과 심사 중 예상 학점(AI 추천, 판정 전)은 따로 센다. 예상치는 확정 합계에 넣지 않는다.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.errors import CreditBridgeError, NotFoundError
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import DegreeProgram, GraduationRequirement, User
from backend.models.enums import RequirementArea
from backend.repositories import allocations as allocation_repo
from backend.repositories import catalog as catalog_repo
from backend.repositories import degree as degree_repo
from backend.services import audit
from backend.services.student import CourseRow

AREA_LABELS = {
    RequirementArea.MAJOR_REQUIRED: N_("전공 필수"),
    RequirementArea.MAJOR_ELECTIVE: N_("전공 선택"),
    RequirementArea.GENERAL_EDUCATION: N_("교양"),
    RequirementArea.FREE_ELECTIVE: N_("일반 선택"),
}
SATISFIED, IN_PROGRESS, PENDING_REVIEW, UNMET = "satisfied", "in_progress", "pending_review", "unmet"
STATUS_LABELS = {
    SATISFIED: N_("충족"),
    IN_PROGRESS: N_("일부 충족"),
    PENDING_REVIEW: N_("심사 결과 대기"),
    UNMET: N_("미충족"),
}


@dataclass
class RequirementProgress:
    requirement: GraduationRequirement
    confirmed: float = 0.0  # 확정 인정 학점 (원장)
    pending: float = 0.0  # 심사 중 예상 학점 (판정 전 AI 추천)
    courses: list[str] = field(default_factory=list)  # 이 요건에 배정된 확정 과목 코드·이름

    @property
    def remaining(self) -> float:
        return max(float(self.requirement.required_credits) - self.confirmed, 0.0)

    @property
    def status(self) -> str:
        if self.confirmed >= float(self.requirement.required_credits):
            return SATISFIED
        if self.pending > 0:
            return PENDING_REVIEW
        return IN_PROGRESS if self.confirmed > 0 else UNMET


@dataclass
class Audit:
    program: DegreeProgram | None
    unresolved_reason: str | None = None  # 프로그램을 고르지 못한 이유 (N_ 원문)
    rows: list[RequirementProgress] = field(default_factory=list)
    unassigned: float = 0.0  # 어느 요건에도 배정되지 않은 확정 학점

    @property
    def confirmed_total(self) -> float:
        return round(sum(r.confirmed for r in self.rows), 2)

    @property
    def required_total(self) -> float:
        return round(sum(float(r.requirement.required_credits) for r in self.rows), 2)


NO_PROGRAM = N_("편입 전공·입학연도에 맞는 졸업 프로그램이 아직 등록되지 않았어요.")
PROGRAM_CONFLICT = N_("편입 전공·입학연도에 맞는 졸업 프로그램이 둘 이상이라 하나로 정할 수 없어요.")


def program_for(session: Session, student: User, institution_id: int) -> tuple[DegreeProgram | None, str | None]:
    candidates = [
        p
        for p in degree_repo.programs_of(session, institution_id)
        if (p.department_id is None or p.department_id == student.department_id)
        and (p.catalog_year is None or p.catalog_year == student.admission_year)
    ]
    if not candidates:
        return None, NO_PROGRAM
    best = max((p.department_id is not None) + (p.catalog_year is not None) for p in candidates)
    top = [p for p in candidates if (p.department_id is not None) + (p.catalog_year is not None) == best]
    return (top[0], None) if len(top) == 1 else (None, PROGRAM_CONFLICT)


def _place(
    rows: list[RequirementProgress], code: str | None, credits: float, attr: str, label: str | None = None
) -> float:
    """학점을 요건에 배정하고 배정하지 못한 학점을 돌려준다 (필요 학점을 넘으면 일반 선택으로 넘김)."""
    target = next((r for r in rows if code and code in (r.requirement.course_codes or [])), None)
    free = next((r for r in rows if r.requirement.area == RequirementArea.FREE_ELECTIVE), None)
    left = credits
    if target is not None and target is not free:
        taken = target.confirmed if attr == "confirmed" else target.confirmed + target.pending
        used = min(max(float(target.requirement.required_credits) - taken, 0.0), left)
        if used:
            setattr(target, attr, round(getattr(target, attr) + used, 2))
            if label and attr == "confirmed":
                target.courses.append(label)
            left = round(left - used, 2)
    if left > 0 and free is not None:
        setattr(free, attr, round(getattr(free, attr) + left, 2))
        if label and attr == "confirmed":
            free.courses.append(label)
        left = 0.0
    return left


def audit_for(session: Session, student: User, institution_id: int, rows: list[CourseRow]) -> Audit:
    """학생의 졸업 요건 진행. rows는 학생 홈 전체 합계에 쓰는 과목 행 (같은 과목은 한 번)."""
    program, reason = program_for(session, student, institution_id)
    if program is None:
        return Audit(None, reason)
    out = Audit(program, rows=[RequirementProgress(r) for r in degree_repo.requirements_of(session, [program.id])])
    ledger = allocation_repo.active_for_student(session, student.id)
    courses = catalog_repo.courses_by_ids(session, [a.target_course_id for a, _ in ledger if a.target_course_id])
    for allocation, source in ledger:
        course = courses.get(allocation.target_course_id) if allocation.target_course_id else None
        label = f"{source.course_code or source.course_title} → {course.code if course else tr('일반 선택')}"
        out.unassigned += _place(
            out.rows, course.code if course else None, float(allocation.credits), "confirmed", label
        )
    if not get_settings().ai_limited:  # 추천 범위 제한 중에는 예상치를 만들지 않는다 (P1-7)
        for row in rows:
            ev, conv = row.evaluation, row.conversion
            if row.decision is not None or row.allocated is not None or row.grade_failed or ev is None:
                continue
            if ev.status != "done" or ev.recommendation not in ("direct", "elective") or conv is None or not conv.known:
                continue
            value = float(conv.value or 0.0)
            credit = min(value, float(row.candidate_credits)) if row.candidate_credits else value
            code = row.candidate_code if ev.recommendation == "direct" else None
            _place(out.rows, code, credit, "pending")
    out.unassigned = round(out.unassigned, 2)
    return out


# ---------- 관리자: 프로그램·요건 관리 ----------


def _ensure_admin(admin: User) -> int:
    from backend.services.institution_data import ensure_admin

    return ensure_admin(admin)


def add_program(session: Session, admin: User, name: str, department: str, catalog_year: str) -> DegreeProgram:
    institution_id = _ensure_admin(admin)
    name, year = name.strip(), catalog_year.strip()
    if not name or len(name) > 200:
        raise CreditBridgeError(tr("프로그램 이름을 200자 이내로 적어 주세요."))
    if year and not (year.isdigit() and 1990 <= int(year) <= 2100):
        raise CreditBridgeError(tr("적용 입학연도는 네 자리 연도로 적어 주세요."))
    dept = None
    if department.strip():
        dept = catalog_repo.department_by_name(session, institution_id, department.strip())
        if dept is None:
            raise CreditBridgeError(tr("학과를 목록에서 골라 주세요."))
    program = DegreeProgram(
        institution_id=institution_id,
        name=name,
        department_id=dept.id if dept else None,
        catalog_year=int(year) if year else None,
    )
    degree_repo.add(session, program)
    audit.record(session, admin, "degree.program_add", "degree_program", str(program.id))
    session.commit()
    return program


def _own_program(session: Session, admin: User, program_id: int) -> DegreeProgram:
    institution_id = _ensure_admin(admin)
    program = degree_repo.get_program(session, program_id)
    if program is None or program.institution_id != institution_id:
        raise NotFoundError(tr("졸업 프로그램을 찾을 수 없어요."))
    return program


def add_requirement(
    session: Session, admin: User, program_id: int, area: str, name: str, credits: str, course_codes: str
) -> GraduationRequirement:
    program = _own_program(session, admin, program_id)
    if area not in set(RequirementArea):
        raise CreditBridgeError(tr("요건 영역을 목록에서 골라 주세요."))
    try:
        value = float(credits)
    except ValueError:
        value = 0.0
    if not 0 < value <= 300:
        raise CreditBridgeError(tr("필요 학점은 0보다 크고 300 이하로 적어 주세요."))
    codes = [c.strip() for c in course_codes.replace(";", ",").split(",") if c.strip()]
    unknown = [c for c in codes if catalog_repo.course_by_code(session, program.institution_id, c) is None]
    if unknown:
        raise CreditBridgeError(tr("카탈로그에 없는 과목 코드예요: {codes}", codes=", ".join(unknown[:5])))
    existing = degree_repo.requirements_of(session, [program.id])
    row = GraduationRequirement(
        program_id=program.id,
        area=area,
        name=name.strip()[:200] or tr(AREA_LABELS[RequirementArea(area)]),
        required_credits=value,
        course_codes=codes,
        sort=len(existing),
    )
    degree_repo.add(session, row)
    audit.record(session, admin, "degree.requirement_add", "degree_program", str(program.id), area=area)
    session.commit()
    return row


def remove_requirement(session: Session, admin: User, requirement_id: int) -> None:
    row = degree_repo.get_requirement(session, requirement_id)
    if row is None:
        raise NotFoundError(tr("졸업 요건을 찾을 수 없어요."))
    program = _own_program(session, admin, row.program_id)
    degree_repo.delete(session, row)
    audit.record(session, admin, "degree.requirement_remove", "degree_program", str(program.id))
    session.commit()


def remove_program(session: Session, admin: User, program_id: int) -> None:
    program = _own_program(session, admin, program_id)
    for row in degree_repo.requirements_of(session, [program.id]):
        degree_repo.delete(session, row)
    degree_repo.delete(session, program)
    audit.record(session, admin, "degree.program_remove", "degree_program", str(program_id))
    session.commit()


@dataclass(frozen=True)
class ProgramView:
    program: DegreeProgram
    department: str | None
    requirements: list[GraduationRequirement]


def programs_view(session: Session, admin: User) -> list[ProgramView]:
    institution_id = _ensure_admin(admin)
    programs = degree_repo.programs_of(session, institution_id)
    departments = {d.id: d.name for d in catalog_repo.department_rows(session, institution_id)}
    requirements = degree_repo.requirements_of(session, [p.id for p in programs])
    return [
        ProgramView(
            p,
            departments.get(p.department_id) if p.department_id else None,
            [r for r in requirements if r.program_id == p.id],
        )
        for p in programs
    ]
