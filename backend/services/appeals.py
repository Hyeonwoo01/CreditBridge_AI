"""이의 신청 (FR-23): 학생 신청 → 심사관 접수·처리(받아들임·기각) → 받아들이면 교수 재판정.

재판정은 새 판정 행으로 남고 원래 판정은 지우지 않는다 (decisions 추가 전용).
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.base import utcnow
from backend.documents import text as doc_text
from backend.documents.storage import ObjectStorage
from backend.errors import CreditBridgeError, DuplicateRowError, NotFoundError, PermissionDeniedError
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import Appeal, AppealFile, Assignment, CourseEvaluation, Decision, Syllabus, TransferRequest, User
from backend.models.enums import AppealStatus, Role
from backend.repositories import appeals as appeal_repo
from backend.repositories import catalog as catalog_repo
from backend.repositories import decisions as decision_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.security.permissions import can_view_evaluation
from backend.services import audit, notifications
from backend.services import student as student_service
from backend.services.student import UploadedFile

MIN_REASON_CHARS = 20
MAX_REASON_CHARS = 3000
MAX_FILES = 3  # 이의 신청 근거 자료
OPEN = (AppealStatus.SUBMITTED, AppealStatus.ACCEPTED)


@dataclass(frozen=True)
class AppealRow:
    appeal: Appeal
    evaluation: CourseEvaluation
    syllabus: Syllabus
    request: TransferRequest
    reviewer_options: list[User]  # 재판정을 맡길 수 있는 학과 교수
    default_reviewer_id: int | None  # 원 판정 교수 (부재면 대리 심사자)
    files: list[AppealFile] = field(default_factory=list)


def _course(syllabus: Syllabus) -> str:
    return (syllabus.course_code or syllabus.course_title or N_("강의계획서")).strip()


def file_appeal(
    session: Session,
    student: User,
    evaluation_id: int,
    reason: str,
    files: list[UploadedFile] | None = None,
    storage: ObjectStorage | None = None,
) -> Appeal:
    """이의 신청. 근거 자료(PDF·JPG·PNG, 최대 3개)는 검증을 모두 통과해야 저장한다."""
    files = files or []
    evaluation = evaluation_repo.get(session, evaluation_id)
    request = (
        request_repo.get(session, evaluation.transfer_request_id)
        if evaluation and evaluation.transfer_request_id
        else None
    )
    if evaluation is None or request is None:
        raise NotFoundError(tr("심사 건을 찾을 수 없어요."))
    if student.role != Role.STUDENT or request.student_id != student.id:
        raise PermissionDeniedError(tr("본인의 판정에만 이의 신청을 할 수 있어요."))
    decision = decision_repo.for_evaluation(session, evaluation.id)
    if decision is None:
        raise CreditBridgeError(tr("판정이 확정된 과목만 이의 신청을 할 수 있어요."))
    if any(a.status in OPEN for a in appeal_repo.for_evaluation(session, evaluation.id)):
        raise CreditBridgeError(tr("이미 처리 중인 이의 신청이 있어요."))
    reason = reason.strip()
    if len(reason) < MIN_REASON_CHARS:
        raise CreditBridgeError(
            tr("이의 사유를 {min_reason_chars}자 이상 구체적으로 적어 주세요.", min_reason_chars=MIN_REASON_CHARS)
        )
    if len(reason) > MAX_REASON_CHARS:
        raise CreditBridgeError(
            tr("이의 사유는 {max_reason_chars}자까지 적을 수 있어요.", max_reason_chars=MAX_REASON_CHARS)
        )
    if len(files) > MAX_FILES:
        raise CreditBridgeError(tr("근거 자료는 {max_files}개까지 올릴 수 있어요.", max_files=MAX_FILES))
    max_mb = get_settings().max_upload_mb
    checked = [(f, doc_text.validate_upload(f.filename, f.data, max_mb)) for f in files]
    if checked and storage is None:
        raise CreditBridgeError(tr("파일 저장소를 쓸 수 없어요."))
    try:
        appeal = appeal_repo.add(
            session,
            Appeal(course_evaluation_id=evaluation.id, decision_id=decision.id, student_id=student.id, reason=reason),
        )
    except DuplicateRowError:
        raise CreditBridgeError(tr("이미 처리 중인 이의 신청이 있어요.")) from None
    for f, ext in checked:
        assert storage is not None
        key = storage.new_key("appeals", f.filename)
        storage.put(key, f.data, doc_text.CONTENT_TYPES[ext])
        appeal_repo.add_file(
            session,
            AppealFile(
                appeal_id=appeal.id,
                file_key=key,
                original_filename=f.filename[:255],
                content_type=doc_text.CONTENT_TYPES[ext],
                size=len(f.data),
            ),
        )
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    notifications.notify(
        session,
        notifications.staff(session, request.target_institution_id, Role.EVALUATOR),
        "appeal.submitted",
        N_("{course} 판정에 이의 신청이 접수됐어요.").format(course=_course(syllabus) if syllabus else N_("과목")),
        "/review/appeals",
    )
    audit.record(
        session, student, "appeal.submit", "course_evaluation", str(evaluation.id), appeal=appeal.id, files=len(checked)
    )
    session.commit()
    return appeal


def _load(session: Session, evaluator: User, appeal_id: int) -> tuple[Appeal, CourseEvaluation, TransferRequest]:
    if evaluator.role != Role.EVALUATOR:
        raise PermissionDeniedError(tr("이의 신청은 심사관이 접수·처리해요."))
    appeal = appeal_repo.get(session, appeal_id)
    evaluation = evaluation_repo.get(session, appeal.course_evaluation_id) if appeal else None
    request = (
        request_repo.get(session, evaluation.transfer_request_id)
        if evaluation and evaluation.transfer_request_id
        else None
    )
    if appeal is None or evaluation is None or request is None:
        raise NotFoundError(tr("이의 신청을 찾을 수 없어요."))
    if request.target_institution_id != evaluator.institution_id:
        raise PermissionDeniedError(tr("소속 기관의 이의 신청만 처리할 수 있어요."))
    if appeal.status != AppealStatus.SUBMITTED:
        raise CreditBridgeError(tr("이미 처리한 이의 신청이에요."))
    return appeal, evaluation, request


def _department_professors(session: Session, evaluation: CourseEvaluation, institution_id: int) -> list[User]:
    """재판정을 맡길 수 있는 교수: 판정한 대상 과목(없으면 AI 후보 과목)의 학과, 그것도 없으면 원 판정 교수의 학과."""
    decision = decision_repo.for_evaluation(session, evaluation.id)
    course_id = (decision.target_course_id if decision else None) or evaluation.candidate_course_id
    course = catalog_repo.get_course(session, course_id) if course_id else None
    department_id = course.department_id if course else None
    if department_id is None and decision is not None:
        decider = user_repo.get_by_id(session, decision.decided_by)
        department_id = decider.department_id if decider else None
    return user_repo.professors_in(session, institution_id, department_id)


def accept(session: Session, evaluator: User, appeal_id: int, reviewer_id: int | None, note: str) -> Appeal:
    """이의 신청을 받아들이고 재판정할 교수에게 배정한다."""
    appeal, evaluation, request = _load(session, evaluator, appeal_id)
    professors = _department_professors(session, evaluation, request.target_institution_id)
    reviewer = next((p for p in professors if p.id == reviewer_id), None)
    if reviewer is None:
        raise CreditBridgeError(tr("재판정할 학과 교수를 선택해 주세요."))
    evaluation_repo.add_assignment(
        session, Assignment(course_evaluation_id=evaluation.id, reviewer_id=reviewer.id, assigned_by=evaluator.id)
    )
    appeal.status = AppealStatus.ACCEPTED
    appeal.handled_by = evaluator.id
    appeal.handler_note = note.strip()
    appeal.handled_at = utcnow()
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    course = _course(syllabus) if syllabus else N_("과목")
    notifications.notify(
        session,
        [reviewer],
        "appeal.redecide",
        N_("{course} 판정에 대한 이의 신청이 받아들여져 재판정이 배정됐어요.").format(course=course),
        f"/professor/evaluations/{evaluation.id}",
    )
    student = user_repo.get_by_id(session, request.student_id)
    notifications.notify(
        session,
        [student] if student else [],
        "appeal.accepted",
        N_("{course} 이의 신청이 접수돼 학과 교수가 다시 판정해요.").format(course=course),
        f"/student/evaluations/{evaluation.id}",
    )
    audit.record(
        session,
        evaluator,
        "appeal.accept",
        "course_evaluation",
        str(evaluation.id),
        appeal=appeal.id,
        reviewer=reviewer.id,
    )
    session.commit()
    return appeal


def dismiss(session: Session, evaluator: User, appeal_id: int, note: str) -> Appeal:
    appeal, evaluation, request = _load(session, evaluator, appeal_id)
    note = note.strip()
    if not note:
        raise CreditBridgeError(tr("기각할 때는 학생에게 전할 사유를 적어 주세요."))
    appeal.status = AppealStatus.DISMISSED
    appeal.handled_by = evaluator.id
    appeal.handler_note = note
    appeal.handled_at = utcnow()
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    student = user_repo.get_by_id(session, request.student_id)
    notifications.notify(
        session,
        [student] if student else [],
        "appeal.dismissed",
        N_("{course} 이의 신청이 기각됐어요. 사유를 확인해 주세요.").format(
            course=_course(syllabus) if syllabus else N_("과목")
        ),
        f"/student/evaluations/{evaluation.id}",
    )
    audit.record(session, evaluator, "appeal.dismiss", "course_evaluation", str(evaluation.id), appeal=appeal.id)
    session.commit()
    return appeal


def accepted_for(session: Session, evaluation_id: int) -> Appeal | None:
    """재판정을 기다리는 이의 신청."""
    return next(
        (a for a in appeal_repo.for_evaluation(session, evaluation_id) if a.status == AppealStatus.ACCEPTED), None
    )


def for_evaluation(session: Session, evaluation_id: int) -> list[Appeal]:
    return appeal_repo.for_evaluation(session, evaluation_id)


def rows(session: Session, evaluator: User) -> list[AppealRow]:
    if evaluator.role != Role.EVALUATOR or evaluator.institution_id is None:
        raise PermissionDeniedError(tr("심사관 계정만 사용할 수 있어요."))
    today = utcnow().date()
    out = []
    found = appeal_repo.of_institution(session, evaluator.institution_id)
    files = appeal_repo.files_for(session, [a.id for a, _, _, _ in found])
    for appeal, evaluation, syllabus, request in found:
        professors = _department_professors(session, evaluation, evaluator.institution_id)
        appealed = decision_repo.get(session, appeal.decision_id)
        original = user_repo.get_by_id(session, appealed.decided_by) if appealed else None
        default = original
        if original is not None and original.is_away(today) and original.delegate_user_id:
            default = user_repo.get_by_id(session, original.delegate_user_id)
        out.append(
            AppealRow(
                appeal,
                evaluation,
                syllabus,
                request,
                professors,
                default.id if default and any(p.id == default.id for p in professors) else None,
                files.get(appeal.id, []),
            )
        )
    out.sort(key=lambda r: (r.appeal.status != AppealStatus.SUBMITTED, -r.appeal.id))
    return out


@dataclass(frozen=True)
class StudentAppealRow:
    appeal: Appeal
    evaluation: CourseEvaluation
    syllabus: Syllabus
    request: TransferRequest
    appealed: Decision | None  # 이의를 신청한 원 판정
    redecided: Decision | None  # 재판정이 끝났으면 새 판정
    files: list[AppealFile] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.appealed and self.redecided and self.redecided.result != self.appealed.result)


def student_rows(session: Session, student: User) -> list[StudentAppealRow]:
    """학생 본인이 낸 이의 신청 (최근 순)."""
    if student.role != Role.STUDENT:
        raise PermissionDeniedError(tr("학생 계정만 사용할 수 있어요."))
    out = []
    found = appeal_repo.of_student(session, student.id)
    files = appeal_repo.files_for(session, [a.id for a, _, _, _ in found])
    for appeal, evaluation, syllabus, request in found:
        current = decision_repo.for_evaluation(session, evaluation.id)
        redecided = current if current is not None and current.appeal_id == appeal.id else None
        appealed = decision_repo.get(session, appeal.decision_id)
        out.append(
            StudentAppealRow(appeal, evaluation, syllabus, request, appealed, redecided, files.get(appeal.id, []))
        )
    return out


@dataclass(frozen=True)
class Appealable:
    """이의 신청할 수 있는 과목: 판정이 확정됐고 처리 중인 이의 신청이 없다."""

    evaluation: CourseEvaluation
    syllabus: Syllabus
    request: TransferRequest
    decision: Decision


def appealable(session: Session, student: User) -> list[Appealable]:
    if student.role != Role.STUDENT:
        raise PermissionDeniedError(tr("학생 계정만 사용할 수 있어요."))
    out = []
    for request in request_repo.of_student(session, student.id):
        for row in student_service.course_rows(session, request):
            if row.evaluation is None or row.decision is None:
                continue
            if row.appeal is not None and row.appeal.status in OPEN:
                continue
            out.append(Appealable(row.evaluation, row.syllabus, request, row.decision))
    return out


def files_for(session: Session, appeal_ids: list[int]) -> dict[int, list[AppealFile]]:
    return appeal_repo.files_for(session, appeal_ids)


def file_for_download(session: Session, user: User, file_id: int) -> AppealFile:
    """근거 자료 내려받기: 그 심사 건을 볼 수 있는 사람(학생 본인·소속 심사관·담당 교수)만.

    열람할 때마다 감사 로그를 남긴다."""
    file = appeal_repo.get_file(session, file_id)
    appeal = appeal_repo.get(session, file.appeal_id) if file else None
    evaluation = evaluation_repo.get(session, appeal.course_evaluation_id) if appeal else None
    if file is None or evaluation is None:
        raise NotFoundError(tr("파일을 찾을 수 없어요."))
    if not can_view_evaluation(session, user, evaluation):
        raise PermissionDeniedError(tr("이 파일을 볼 권한이 없어요."))
    if file.file_key is None:
        raise NotFoundError(tr("개인정보 삭제 요청으로 지워진 파일이에요."))
    # 누가 언제 학생 파일을 열어 봤는지 감사 로그에 남긴다 (파일 이름은 넣지 않는다)
    audit.record(
        session,
        user,
        "appeal_file.download",
        "appeal_file",
        str(file.id),
        appeal=file.appeal_id,
        evaluation=evaluation.id,
    )
    session.commit()
    return file


def submitted_count(session: Session, evaluator: User) -> int:
    """심사관 메뉴 배지: 접수돼 처리를 기다리는 이의 신청 수."""
    if evaluator.role != Role.EVALUATOR or evaluator.institution_id is None:
        raise PermissionDeniedError(tr("심사관 계정만 사용할 수 있어요."))
    return sum(
        1
        for appeal, _, _, _ in appeal_repo.of_institution(session, evaluator.institution_id)
        if appeal.status == AppealStatus.SUBMITTED
    )
