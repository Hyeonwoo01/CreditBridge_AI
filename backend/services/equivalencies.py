"""기존 동등 과목표 가져오기 (FR-26). 기관이 보유한 판정 이력을 CSV로 올려 과거 판정 이력에 함께 보여준다.

파일 검사·인코딩은 services/csv_import.py. 한 줄이라도 틀리면 아무것도 저장하지 않는다.
열: source_institution, source_course, target_course, result, decided_on, note
"""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from backend.errors import CreditBridgeError, PermissionDeniedError
from backend.i18n import gettext as tr
from backend.models import Equivalency, User
from backend.models.enums import Role
from backend.repositories import catalog as catalog_repo
from backend.repositories import equivalencies as equivalency_repo
from backend.services import audit, csv_import

COLUMNS = ["source_institution", "source_course", "target_course", "result", "decided_on", "note"]
RESULTS = {
    "direct": "direct",
    "직접 인정": "direct",
    "elective": "elective",
    "선택 인정": "elective",
    "none": "none",
    "불인정": "none",
}
MAX_ROWS = 5000


@dataclass
class ImportResult:
    imported: int = 0
    errors: list[str] = field(default_factory=list)


def course_key(label: str) -> str:
    """decisions.course_key와 같은 정규화."""
    return label.lower().replace(" ", "")


def import_csv(session: Session, evaluator: User, filename: str, data: bytes) -> ImportResult:
    if evaluator.role != Role.EVALUATOR or evaluator.institution_id is None:
        raise PermissionDeniedError(tr("심사관 계정만 동등 과목표를 가져올 수 있어요."))
    result = ImportResult()
    rows: list[Equivalency] = []
    for line_no, row in csv_import.read_rows(filename, data, COLUMNS, COLUMNS[:4], MAX_ROWS):
        problems = []
        source = catalog_repo.source_institution_by_name(session, row.get("source_institution", ""))
        if source is None:
            problems.append(tr("등록되지 않은 출신 대학"))
        label = row.get("source_course", "")
        if not label:
            problems.append(tr("출신 과목 없음"))
        verdict = RESULTS.get(row.get("result", "").lower()) or RESULTS.get(row.get("result", ""))
        if verdict is None:
            problems.append(tr("판정은 direct·elective·none 중 하나"))
        target = None
        if row.get("target_course"):
            target = catalog_repo.course_by_code(session, evaluator.institution_id, row["target_course"])
            if target is None:
                problems.append(tr("카탈로그에 없는 대상 과목({target_course})", target_course=row["target_course"]))
        elif verdict == "direct":
            problems.append(tr("직접 인정은 대상 과목이 필요"))
        decided_on = None
        if row.get("decided_on"):
            try:
                decided_on = date.fromisoformat(row["decided_on"])
            except ValueError:
                problems.append(tr("판정일은 YYYY-MM-DD"))
        if problems or source is None or verdict is None:
            result.errors.append(tr("{line_no}행: {problems}", line_no=line_no, problems=", ".join(problems)))
            continue
        rows.append(
            Equivalency(
                target_institution_id=evaluator.institution_id,
                source_institution_id=source.id,
                source_course_key=course_key(label)[:100],
                source_course_label=label[:255],
                target_course_id=target.id if target else None,
                result=verdict,
                decided_on=decided_on,
                note=row.get("note", ""),
                imported_by=evaluator.id,
            )
        )
    if result.errors:
        return result
    if not rows:
        raise CreditBridgeError(tr("가져올 행이 없어요."))
    equivalency_repo.add_many(session, rows)
    audit.record(session, evaluator, "equivalency.import", "institution", str(evaluator.institution_id), rows=len(rows))
    session.commit()
    result.imported = len(rows)
    return result


def recent(session: Session, evaluator: User) -> list[Equivalency]:
    if evaluator.role != Role.EVALUATOR or evaluator.institution_id is None:
        raise PermissionDeniedError(tr("심사관 계정만 사용할 수 있어요."))
    return equivalency_repo.of_institution(session, evaluator.institution_id)
