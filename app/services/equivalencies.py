"""기존 동등 과목표 가져오기 (FR-26). 기관이 보유한 판정 이력을 CSV로 올려 과거 판정 이력에 함께 보여준다.

엑셀 파일은 'CSV UTF-8'로 저장해 올린다(엑셀 라이브러리를 추가하지 않는다). 한 줄이라도 틀리면 아무것도 저장하지 않는다.
열: source_institution, source_course, target_course, result, decided_on, note
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.errors import CreditBridgeError, PermissionDeniedError
from app.models import Equivalency, User
from app.models.enums import Role
from app.repositories import catalog as catalog_repo
from app.repositories import equivalencies as equivalency_repo
from app.services import audit

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
MAX_BYTES = 5 * 1024 * 1024


@dataclass
class ImportResult:
    imported: int = 0
    errors: list[str] = field(default_factory=list)


def course_key(label: str) -> str:
    """decisions.course_key와 같은 정규화."""
    return label.lower().replace(" ", "")


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949"):  # 한국어 엑셀의 기본 CSV 인코딩까지
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CreditBridgeError("CSV 파일의 인코딩을 읽을 수 없어요. 'CSV UTF-8'로 저장해 올려 주세요.")


def import_csv(session: Session, evaluator: User, filename: str, data: bytes) -> ImportResult:
    if evaluator.role != Role.EVALUATOR or evaluator.institution_id is None:
        raise PermissionDeniedError("심사관 계정만 동등 과목표를 가져올 수 있어요.")
    if not filename.lower().endswith(".csv"):
        raise CreditBridgeError("CSV 파일만 올릴 수 있어요. 엑셀에서 '다른 이름으로 저장 → CSV UTF-8'을 골라 주세요.")
    if not data.strip():
        raise CreditBridgeError("빈 파일이에요.")
    if len(data) > MAX_BYTES:
        raise CreditBridgeError("파일이 5MB를 넘어요. 나눠서 올려 주세요.")
    reader = csv.DictReader(io.StringIO(_decode(data)))
    missing = [c for c in COLUMNS[:4] if c not in (reader.fieldnames or [])]
    if missing:
        raise CreditBridgeError(f"필수 열이 없어요: {', '.join(missing)}. 첫 줄은 {', '.join(COLUMNS)} 이어야 해요.")

    result = ImportResult()
    rows: list[Equivalency] = []
    for line_no, raw in enumerate(reader, start=2):
        if line_no - 1 > MAX_ROWS:
            result.errors.append(f"한 번에 {MAX_ROWS}줄까지만 가져올 수 있어요.")
            break
        row = {k: (v or "").strip() for k, v in raw.items() if k}
        if not any(row.values()):
            continue
        problems = []
        source = catalog_repo.source_institution_by_name(session, row.get("source_institution", ""))
        if source is None:
            problems.append("등록되지 않은 출신 대학")
        label = row.get("source_course", "")
        if not label:
            problems.append("출신 과목 없음")
        verdict = RESULTS.get(row.get("result", "").lower()) or RESULTS.get(row.get("result", ""))
        if verdict is None:
            problems.append("판정은 direct·elective·none 중 하나")
        target = None
        if row.get("target_course"):
            target = catalog_repo.course_by_code(session, evaluator.institution_id, row["target_course"])
            if target is None:
                problems.append(f"카탈로그에 없는 대상 과목({row['target_course']})")
        elif verdict == "direct":
            problems.append("직접 인정은 대상 과목이 필요")
        decided_on = None
        if row.get("decided_on"):
            try:
                decided_on = date.fromisoformat(row["decided_on"])
            except ValueError:
                problems.append("판정일은 YYYY-MM-DD")
        if problems or source is None or verdict is None:
            result.errors.append(f"{line_no}행: {', '.join(problems)}")
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
        raise CreditBridgeError("가져올 행이 없어요.")
    equivalency_repo.add_many(session, rows)
    audit.record(session, evaluator, "equivalency.import", "institution", str(evaluator.institution_id), rows=len(rows))
    session.commit()
    result.imported = len(rows)
    return result


def recent(session: Session, evaluator: User) -> list[Equivalency]:
    if evaluator.role != Role.EVALUATOR or evaluator.institution_id is None:
        raise PermissionDeniedError("심사관 계정만 사용할 수 있어요.")
    return equivalency_repo.of_institution(session, evaluator.institution_id)
