"""선배 인정 사례 (학생용): 소속 대학이 같은 출신 대학 과목을 어떻게 인정해 왔는지 과목 단위로 모아 보여 준다.

기관의 기존 동등 과목표(FR-26)와 CreditBridge에서 확정된 판정(현재 판정만)을 과목·대상 과목·결과별 건수로 합친다.
누가 받은 판정인지, 사유·성적·메모는 보여 주지 않는다 (FR-12: 다른 학생의 심사 건 자체에는 접근하지 않는다).
"""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from backend.errors import PermissionDeniedError
from backend.models import Course, Institution, User
from backend.models.enums import Role
from backend.repositories import catalog as catalog_repo
from backend.repositories import decisions as decision_repo
from backend.repositories import equivalencies as equivalency_repo
from backend.repositories import requests as request_repo
from backend.services.equivalencies import course_key


@dataclass
class PrecedentRow:
    source_label: str
    target_course: Course | None
    result: str  # direct / elective / none
    decided: int = 0  # CreditBridge 확정 판정 건수
    listed: int = 0  # 기관 동등 과목표 건수
    latest: date | None = None


@dataclass
class PrecedentSearch:
    target: Institution | None
    sources: list[Institution]
    source: Institution | None
    query: str
    rows: list[PrecedentRow] = field(default_factory=list)


def search(session: Session, student: User, source_id: int | None, query: str) -> PrecedentSearch:
    if student.role != Role.STUDENT:
        raise PermissionDeniedError("학생 계정만 사용할 수 있어요.")
    target = catalog_repo.get_institution(session, student.institution_id) if student.institution_id else None
    if target is None or not target.is_target:
        return PrecedentSearch(None, [], None, query)
    sources = catalog_repo.source_institutions(session)
    if source_id is None:
        mine = request_repo.of_student(session, student.id)
        source_id = mine[0].source_institution_id if mine else None
    source = next((s for s in sources if s.id == source_id), sources[0] if sources else None)
    found = PrecedentSearch(target, sources, source, query.strip())
    if source is None:
        return found

    groups: dict[tuple[str, int | None, str], PrecedentRow] = {}
    course_ids: set[int] = set()

    def add(label: str, course_id: int | None, result: str, when: date | None, decided: bool) -> None:
        key = (course_key(label), course_id, result)
        row = groups.setdefault(key, PrecedentRow(label, None, result))
        if decided:
            row.decided += 1
        else:
            row.listed += 1
        if when and (row.latest is None or when > row.latest):
            row.latest = when
        if course_id:
            course_ids.add(course_id)

    for decision, syllabus in decision_repo.current_for_pair(session, target.id, source.id):
        label = " ".join(x for x in (syllabus.course_code, syllabus.course_title) if x).strip()
        if label:
            add(label, decision.target_course_id, decision.result, decision.decided_at.date(), True)
    for e in equivalency_repo.of_pair(session, target.id, source.id):
        add(e.source_course_label, e.target_course_id, e.result, e.decided_on, False)

    courses = catalog_repo.courses_by_ids(session, list(course_ids))
    needle = found.query.lower()
    for (_, course_id, _), row in groups.items():
        row.target_course = courses.get(course_id) if course_id else None
        course = row.target_course
        haystack = f"{row.source_label} {course.code} {course.title}" if course else row.source_label
        if needle and needle not in haystack.lower():
            continue
        found.rows.append(row)
    found.rows.sort(key=lambda r: (r.source_label.lower(), r.result != "direct", r.result != "elective"))
    return found
