"""증거 출처·진위·적용 학기 (리뷰 v3 P0-5).

- 파일 해시는 같은 파일인지만 알려 준다. 진위(발급 기관이 맞는지)는 심사관이 확인 방법과 함께 정한다.
- 강의계획서 학기와 성적표의 실제 수강 학기를 비교해 적용 여부를 정한다. 다른 학기 자료는 수강 당시 자료가 아니다.
- 진위가 의심되거나 채택하지 않은 자료는 자동으로 불인정하지 않는다. 판정을 보류하고 학생에게 소명·보완 자료를 받는다.
"""

import re
from typing import Any

from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import Syllabus, User
from backend.models.enums import Applicability, Authenticity, Role, SourceKind
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.security.permissions import ensure_can_view_evaluation
from backend.services import audit, notifications

SOURCE_LABELS = {
    SourceKind.STUDENT_UPLOADED: N_("학생 제출"),
    SourceKind.REGISTRAR_ISSUED: N_("출신 대학 학사처 발급"),
    SourceKind.INSTRUCTOR_CONFIRMED: N_("담당 교원 확인"),
    SourceKind.OFFICIAL_PORTAL: N_("출신 대학 공식 포털 확인"),
    SourceKind.PUBLIC_WEB: N_("공개 웹 자료(참고용)"),
    SourceKind.INSTITUTION_REFERENCE: N_("대상 대학 기준 문서"),
    SourceKind.OTHER: N_("기타"),
}
AUTHENTICITY_LABELS = {
    Authenticity.VERIFIED: N_("진위 확인됨"),
    Authenticity.PARTIALLY_VERIFIED: N_("일부 확인"),
    Authenticity.UNVERIFIED: N_("진위 미확인"),
    Authenticity.SUSPICIOUS: N_("진위 검토 중"),
    Authenticity.REJECTED: N_("증거로 채택 안 함"),
}
APPLICABILITY_LABELS = {
    Applicability.APPLICABLE: N_("수강 학기와 일치"),
    Applicability.MISMATCH: N_("수강 학기와 다름"),
    Applicability.UNKNOWN: N_("적용 학기 모름"),
}
HOLD = (Authenticity.SUSPICIOUS, Authenticity.REJECTED)

_SEASONS = {
    "1": "1", "spring": "1", "봄": "1", "1학기": "1",
    "2": "2", "fall": "2", "autumn": "2", "가을": "2", "2학기": "2",
    "summer": "S", "여름": "S", "여름학기": "S",
    "winter": "W", "겨울": "W", "겨울학기": "W",
}  # fmt: skip


def normalize_term(term: str | None) -> tuple[int, str] | None:
    """'2024-1', '2024 Fall', 'Spring 2024', '2024년 2학기', '2024 여름' → (연도, 학기 코드). 모르면 None."""
    if not term:
        return None
    text = term.strip().lower().replace("년", " ")
    year = re.search(r"(19|20)\d{2}", text)
    if year is None:
        return None
    rest = (text[: year.start()] + " " + text[year.end() :]).replace("-", " ").replace("/", " ").replace(".", " ")
    for token in rest.split():
        season = _SEASONS.get(token) or _SEASONS.get(token.rstrip("학기"))
        if season:
            return int(year.group()), season
    return None


def applicability(syllabus_term: str | None, taken_term: str | None) -> str:
    a, b = normalize_term(syllabus_term), normalize_term(taken_term)
    if a is None or b is None:
        return Applicability.UNKNOWN
    return Applicability.APPLICABLE if a == b else Applicability.MISMATCH


def taken_term(session: Session, syllabus: Syllabus) -> str | None:
    """성적표에 연결된 실제 수강 학기."""
    if syllabus.transfer_request_id is None:
        return None
    for entry in request_repo.transcript_entries(session, syllabus.transfer_request_id):
        if entry.syllabus_id == syllabus.id and entry.term:
            return entry.term
    return None


def snapshot(session: Session, syllabus: Syllabus | None) -> dict[str, Any] | None:
    """판정에 남길 증거 상태."""
    if syllabus is None:
        return None
    return {
        "syllabus_id": syllabus.id,
        "source_kind": syllabus.source_kind,
        "authenticity": syllabus.authenticity,
        "applicability": syllabus.applicability,
        "academic_term": syllabus.academic_term,
        "taken_term": taken_term(session, syllabus),
        "content_hash": syllabus.content_hash,
    }


def hold_reason(syllabus: Syllabus | None) -> str | None:
    """판정을 보류해야 하는 이유 (진위 검토 중·채택 안 함). 없으면 None."""
    if syllabus is None or syllabus.authenticity not in HOLD:
        return None
    if syllabus.authenticity == Authenticity.SUSPICIOUS:
        return N_("학사처가 이 자료의 진위를 검토하고 있어 지금은 판정할 수 없어요. 검토가 끝나면 판정해 주세요.")
    return N_("이 자료는 심사 증거로 채택하지 않았어요. 보완 자료를 받은 뒤 판정해 주세요.")


def update(
    session: Session,
    evaluator: User,
    evaluation_id: int,
    source_kind: str,
    authenticity_value: str,
    academic_term: str,
    method: str,
    note: str,
) -> Syllabus:
    """심사관이 증거의 출처·진위·적용 학기를 정한다. 진위를 의심·채택 안 함으로 바꾸면 학생에게 소명·보완을 안내한다."""
    if evaluator.role != Role.EVALUATOR:
        raise PermissionDeniedError(tr("심사관만 증거 상태를 바꿀 수 있어요."))
    evaluation = evaluation_repo.get(session, evaluation_id)
    if evaluation is None:
        raise NotFoundError(tr("심사 건을 찾을 수 없어요."))
    ensure_can_view_evaluation(session, evaluator, evaluation)
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    if syllabus is None:
        raise NotFoundError(tr("강의계획서를 찾을 수 없어요."))
    if source_kind not in set(SourceKind) or source_kind == SourceKind.INSTITUTION_REFERENCE:
        raise CreditBridgeError(tr("출처를 목록에서 골라 주세요."))
    if authenticity_value not in set(Authenticity):
        raise CreditBridgeError(tr("진위 상태를 목록에서 골라 주세요."))
    method, note, term = method.strip()[:200], note.strip()[:1000], academic_term.strip()[:50]
    if authenticity_value in (Authenticity.VERIFIED, Authenticity.PARTIALLY_VERIFIED) and not method:
        raise CreditBridgeError(tr("진위를 확인했다면 확인 방법을 적어 주세요 (예: 출신 대학 포털에서 대조)."))
    if authenticity_value in HOLD and not note:
        raise CreditBridgeError(tr("의심하거나 채택하지 않는 이유를 메모로 남겨 주세요 (학생에게는 보이지 않아요)."))
    before = syllabus.authenticity
    syllabus.source_kind = source_kind
    syllabus.authenticity = authenticity_value
    syllabus.academic_term = term or None
    syllabus.applicability = applicability(syllabus.academic_term, taken_term(session, syllabus))
    syllabus.verification_method = method
    syllabus.verification_note = note
    syllabus.verified_by = evaluator.id
    syllabus.verified_at = utcnow()
    audit.record(
        session,
        evaluator,
        "evidence.status",
        "syllabus",
        str(syllabus.id),
        source_kind=source_kind,
        authenticity=authenticity_value,
        applicability=syllabus.applicability,
    )
    if authenticity_value in HOLD and before not in HOLD and syllabus.owner_id:
        student = user_repo.get_by_id(session, syllabus.owner_id)
        if student is not None:
            notifications.notify(
                session,
                [student],
                "evidence",
                N_(
                    "{course} 강의계획서를 학사처가 확인하고 있어요. "
                    "공식 자료(학사처 발급본 등)를 보완 자료로 올려 주시면 빨리 진행돼요."
                ).format(course=syllabus.course_code or syllabus.course_title),
                f"/student/evaluations/{evaluation.id}",
            )
    session.commit()
    return syllabus
