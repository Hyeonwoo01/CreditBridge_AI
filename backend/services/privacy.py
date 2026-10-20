"""개인정보(문서) 삭제 요청 (FR-13, NF-03).

학생이 요청하면 처리 기한(Settings.privacy_deletion_days)이 정해지고, 심사관이 처리 의견을 남긴 뒤
기관 관리자가 승인하면 원본 파일·추출 텍스트·성적표 정보를 지운다. 판정 기록과 감사 로그는 학사 기록으로 남는다.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.base import utcnow
from backend.documents.storage import ObjectStorage
from backend.errors import CreditBridgeError, DuplicateRowError, NotFoundError, PermissionDeniedError
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import PrivacyRequest, TransferRequest, User
from backend.models.enums import PrivacyStatus, RequestStatus, Role, SyllabusStatus
from backend.repositories import appeals as appeal_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import materials as material_repo
from backend.repositories import notes as note_repo
from backend.repositories import privacy as privacy_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.services import analysis, audit, notifications


@dataclass(frozen=True)
class PrivacyRow:
    privacy: PrivacyRequest
    request: TransferRequest
    student: User | None
    overdue: bool


def is_overdue(privacy: PrivacyRequest, now: datetime | None = None) -> bool:
    return privacy.status != PrivacyStatus.COMPLETED and privacy.due_at < (now or utcnow())


def request_deletion(session: Session, student: User, request: TransferRequest) -> PrivacyRequest:
    if request.student_id != student.id:
        raise PermissionDeniedError(tr("본인의 편입 요청만 삭제를 요청할 수 있어요."))
    if request.status == RequestStatus.CLOSED:
        raise CreditBridgeError(tr("이미 문서를 삭제한 요청이에요."))
    latest = privacy_repo.latest_for_request(session, request.id)
    if latest is not None and latest.status != PrivacyStatus.COMPLETED:
        raise CreditBridgeError(tr("이미 처리 중인 삭제 요청이 있어요."))
    now = utcnow()
    try:
        privacy = privacy_repo.add(
            session,
            PrivacyRequest(
                transfer_request_id=request.id,
                student_id=student.id,
                created_at=now,
                due_at=now + timedelta(days=get_settings().privacy_deletion_days),
            ),
        )
    except DuplicateRowError:
        raise CreditBridgeError(tr("이미 처리 중인 삭제 요청이 있어요.")) from None
    notifications.notify(
        session,
        notifications.staff(session, request.target_institution_id, Role.EVALUATOR),
        "privacy.requested",
        N_("문서 삭제 요청이 접수됐어요 (요청 #{id}). 기한 안에 처리해 주세요.").format(id=request.id),
        "/review/privacy",
    )
    # 승인은 기관 관리자가 하므로 접수 때부터 알린다 (기한이 급하면 심사관 처리 전에도 승인할 수 있다)
    notifications.notify(
        session,
        notifications.staff(session, request.target_institution_id, Role.ADMIN),
        "privacy.requested",
        N_("문서 삭제 요청이 접수됐어요 (요청 #{id}). 심사관 처리 뒤 승인해 주세요.").format(id=request.id),
        "/admin/privacy",
    )
    audit.record(session, student, "privacy.request", "transfer_request", str(request.id), privacy=privacy.id)
    session.commit()
    return privacy


def latest_for_request(session: Session, request: TransferRequest) -> PrivacyRequest | None:
    return privacy_repo.latest_for_request(session, request.id)


def _load(session: Session, user: User, privacy_id: int) -> tuple[PrivacyRequest, TransferRequest]:
    privacy = privacy_repo.get(session, privacy_id)
    request = request_repo.get(session, privacy.transfer_request_id) if privacy else None
    if privacy is None or request is None:
        raise NotFoundError(tr("삭제 요청을 찾을 수 없어요."))
    if user.institution_id != request.target_institution_id:
        raise PermissionDeniedError(tr("소속 기관의 요청만 처리할 수 있어요."))
    return privacy, request


def review(session: Session, evaluator: User, privacy_id: int) -> PrivacyRequest:
    """심사관 처리: 진행 중인 심사와 보관 의무를 확인하고 관리자 승인으로 넘긴다."""
    if evaluator.role != Role.EVALUATOR:
        raise PermissionDeniedError(tr("심사관만 삭제 요청을 처리할 수 있어요."))
    privacy, request = _load(session, evaluator, privacy_id)
    if privacy.status != PrivacyStatus.REQUESTED:
        raise CreditBridgeError(tr("이미 처리한 요청이에요."))
    privacy.status = PrivacyStatus.REVIEWED
    privacy.reviewed_by = evaluator.id
    privacy.reviewed_at = utcnow()
    notifications.notify(
        session,
        notifications.staff(session, request.target_institution_id, Role.ADMIN),
        "privacy.reviewed",
        N_("문서 삭제 요청(요청 #{id})이 처리돼 승인을 기다려요.").format(id=request.id),
        "/admin/privacy",
    )
    audit.record(session, evaluator, "privacy.review", "transfer_request", str(request.id), privacy=privacy.id)
    session.commit()
    return privacy


def approve(session: Session, admin: User, storage: ObjectStorage, privacy_id: int) -> PrivacyRequest:
    """관리자 승인: 승인 즉시 삭제를 실행한다. 심사관 처리 전이라도 기한이 급하면 승인할 수 있다."""
    if admin.role != Role.ADMIN:
        raise PermissionDeniedError(tr("기관 관리자만 삭제를 승인할 수 있어요."))
    privacy, request = _load(session, admin, privacy_id)
    if privacy.status == PrivacyStatus.COMPLETED:
        raise CreditBridgeError(tr("이미 삭제를 마친 요청이에요."))
    _delete_documents(session, storage, request)
    # 문서가 없으니 요청을 끝낸다: 학생 화면은 종료로, 심사 큐·교수 목록에서는 빠진다 (판정 기록은 그대로)
    request.status = RequestStatus.CLOSED
    reviewers = evaluation_repo.deactivate_assignments_of_request(session, request.id)
    notifications.notify(
        session,
        [u for u in (user_repo.get_by_id(session, r) for r in reviewers) if u is not None],
        "assignment.closed",
        N_("문서 삭제가 승인돼 요청 #{id}의 심사가 종료됐어요.").format(id=request.id),
        "/professor",
    )
    privacy.status = PrivacyStatus.COMPLETED
    privacy.approved_by = admin.id
    privacy.completed_at = utcnow()
    student = user_repo.get_by_id(session, request.student_id)
    notifications.notify(
        session,
        [student] if student else [],
        "privacy.completed",
        N_("요청한 문서 삭제를 마쳤어요. 원본 파일과 추출 텍스트가 지워졌어요."),
        f"/student/requests/{request.id}",
    )
    audit.record(
        session,
        admin,
        "privacy.delete_documents",
        "transfer_request",
        str(request.id),
        privacy=privacy.id,
        overdue=privacy.completed_at > privacy.due_at,
    )
    session.commit()
    return privacy


def _delete_documents(session: Session, storage: ObjectStorage, request: TransferRequest) -> None:
    """원본 파일(강의계획서·보완 자료·성적표·이의 신청 근거 자료)과 추출 텍스트·내부 메모를 지운다."""
    syllabi = syllabus_repo.of_request(session, request.id)
    for appeal_file in appeal_repo.files_of_request(session, request.id):
        if appeal_file.file_key:
            storage.delete(appeal_file.file_key)
        appeal_file.file_key = None
    for f in material_repo.files_of(session, [s.id for s in syllabi]):
        if f.file_key:
            storage.delete(f.file_key)
        f.file_key = None
    note_repo.delete_for_syllabi(session, [s.id for s in syllabi])
    for syllabus in syllabi:
        if syllabus.source_file_key:
            storage.delete(syllabus.source_file_key)
        syllabus.source_file_key = None
        syllabus.raw_text = ""
        syllabus.page_offsets = None
        syllabus.extracted_json = None
        syllabus.status = SyllabusStatus.DELETED
        # 삭제한 문서는 재사용 출처가 되지 않게 하고, 같은 파일을 다시 올릴 수 있게 해시를 비운다
        syllabus.content_hash = analysis.content_hash(f"deleted:{syllabus.id}".encode())
        syllabus_repo.replace_chunks(session, syllabus.id, [])
    if request.transcript_file_key:
        storage.delete(request.transcript_file_key)
        request.transcript_file_key = None
    request.transcript_masked_name = None
    request_repo.replace_transcript_entries(session, request.id, [])


def rows(session: Session, user: User) -> list[PrivacyRow]:
    if user.role not in (Role.EVALUATOR, Role.ADMIN) or user.institution_id is None:
        raise PermissionDeniedError(tr("심사관과 기관 관리자만 볼 수 있어요."))
    now = utcnow()
    out = []
    for privacy, request in privacy_repo.of_institution(session, user.institution_id):
        out.append(
            PrivacyRow(privacy, request, user_repo.get_by_id(session, request.student_id), is_overdue(privacy, now))
        )
    # 처리할 것(기한 임박 순)을 위로, 끝난 것은 아래로
    out.sort(key=lambda r: (r.privacy.status == PrivacyStatus.COMPLETED, r.privacy.due_at))
    return out


def pending_count(session: Session, user: User) -> int:
    """메뉴 배지: 심사관은 처리할 요청(requested), 기관 관리자는 끝나지 않은 요청 전부
    (심사관 처리 전 요청도 기관 관리자가 승인할 수 있고 처리 기한 책임이 있다)."""
    if user.role not in (Role.EVALUATOR, Role.ADMIN) or user.institution_id is None:
        raise PermissionDeniedError(tr("심사관과 기관 관리자만 볼 수 있어요."))
    waiting = (
        {PrivacyStatus.REQUESTED} if user.role == Role.EVALUATOR else {PrivacyStatus.REQUESTED, PrivacyStatus.REVIEWED}
    )
    return sum(1 for p, _ in privacy_repo.of_institution(session, user.institution_id) if p.status in waiting)
