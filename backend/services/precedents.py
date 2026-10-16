"""선배 인정 사례 (학생용): 소속 대학의 기존 동등 과목표(FR-26)를 출신 대학·과목으로 찾아 보여 준다.

기관이 공식 기준으로 가져온 동등 과목표만 쓴다. CreditBridge에서 내린 다른 학생의 판정은 보여 주지 않는다
(FR-12: 학생은 본인 건만). 동등 과목표의 메모도 기관 내부용이라 보여 주지 않는다.
"""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from backend.errors import PermissionDeniedError
from backend.i18n import gettext as tr
from backend.models import Course, Institution, User
from backend.models.enums import Role
from backend.repositories import catalog as catalog_repo
from backend.repositories import equivalencies as equivalency_repo
from backend.repositories import requests as request_repo
from backend.services.equivalencies import course_key


@dataclass
class PrecedentRow:
    source_label: str
    target_course: Course | None
    result: str  # direct / elective / none
    latest: date | None = None  # 동등 과목표의 가장 최근 판정일


@dataclass
class PrecedentSearch:
    target: Institution | None
    sources: list[Institution]
    source: Institution | None
    query: str
    rows: list[PrecedentRow] = field(default_factory=list)


def search(session: Session, student: User, source_id: int | None, query: str) -> PrecedentSearch:
    if student.role != Role.STUDENT:
        raise PermissionDeniedError(tr("학생 계정만 사용할 수 있어요."))
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

    # 같은 과목·인정 과목·결과가 여러 줄이면 한 줄로 합치고 가장 최근 판정일을 남긴다
    groups: dict[tuple[str, int | None, str], PrecedentRow] = {}
    for e in equivalency_repo.of_pair(session, target.id, source.id):
        row = groups.setdefault(
            (course_key(e.source_course_label), e.target_course_id, e.result),
            PrecedentRow(e.source_course_label, None, e.result),
        )
        if e.decided_on and (row.latest is None or e.decided_on > row.latest):
            row.latest = e.decided_on
    courses = catalog_repo.courses_by_ids(session, [cid for _, cid, _ in groups if cid])
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
