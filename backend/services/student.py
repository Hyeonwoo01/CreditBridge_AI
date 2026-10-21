"""학생 서비스: 편입 요청, 문서 업로드, 성적표 연결, 보완 자료, 심사 제출, 진행 상황 (FR-01, 02, 08, 15, 21)."""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.base import utcnow
from backend.documents import text as doc_text
from backend.documents.storage import ObjectStorage
from backend.errors import CreditBridgeError, NotFoundError, PermissionDeniedError, UploadRejectedError
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import (
    Appeal,
    CourseEvaluation,
    Decision,
    MaterialRequest,
    SupplementFile,
    Syllabus,
    TranscriptEntry,
    TransferRequest,
    User,
)
from backend.models.enums import PASSING_GRADES, RequestStatus, Role, SyllabusStatus
from backend.repositories import appeals as appeal_repo
from backend.repositories import catalog as catalog_repo
from backend.repositories import decisions as decision_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import materials as material_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.security.permissions import ensure_can_view_evaluation
from backend.services import analysis, audit, materials, notifications


@dataclass(frozen=True)
class UploadedFile:
    filename: str
    data: bytes


def get_own_request(session: Session, student: User, request_id: int) -> TransferRequest:
    request = request_repo.get(session, request_id)
    if request is None:
        raise NotFoundError(tr("편입 요청을 찾을 수 없어요."))
    if request.student_id != student.id:
        raise PermissionDeniedError(tr("본인의 편입 요청만 볼 수 있어요."))
    return request


def is_empty_draft(session: Session, request: TransferRequest) -> bool:
    """아직 아무 서류(성적표·강의계획서)도 올리지 않은 초안. 잘못 눌러 만든 요청은 이 상태로 남는다."""
    return (
        request.status == RequestStatus.DRAFT
        and not request.transcript_file_key
        and not syllabus_repo.of_request(session, request.id)
    )


def create_request(session: Session, student: User) -> tuple[TransferRequest, bool]:
    """MVP의 학생은 입학이 확정되어 대상 대학에 소속된 학생이다. 편입 대학(소속 대학)·출신 대학·편입 전공은
    학교가 계정을 만들 때 정한 값을 쓰고 학생이 고르지 않는다. 요청에는 그때의 값을 남긴다
    (나중에 계정이 바뀌어도 보존). 빈 초안이 있으면 그 요청을 돌려준다: (요청, 새로 만들었는지)."""
    target = catalog_repo.get_institution(session, student.institution_id) if student.institution_id else None
    if target is None or not target.is_target:
        raise CreditBridgeError(tr("입학이 확정된 대학에 소속된 학생 계정만 편입 요청을 만들 수 있어요."))
    source = student.source_institution
    major = student.department_name
    if source is None or source.is_target or not major:
        raise CreditBridgeError(
            tr("계정에 출신 대학·편입 전공이 아직 없어요. 학사처(기관 관리자)에 등록을 요청해 주세요.")
        )
    # 빈 초안이 이미 있으면 새로 만들지 않고 그 요청을 쓴다 (버튼을 잘못 눌러 빈 요청이 쌓이지 않게)
    for existing in request_repo.of_student(session, student.id):
        if is_empty_draft(session, existing):
            return existing, False
    request = request_repo.add(
        session,
        TransferRequest(
            student_id=student.id, source_institution_id=source.id, target_institution_id=target.id, major=major
        ),
    )
    audit.record(session, student, "request.create", "transfer_request", str(request.id), target=target.id, major=major)
    session.commit()
    return request, True


def delete_empty_request(session: Session, student: User, request_id: int) -> None:
    """학생이 서류를 하나도 올리지 않은 초안을 지운다. 서류가 있거나 심사를 요청한 요청은 지우지 않는다
    (문서 삭제는 개인정보 삭제 요청 절차로)."""
    request = get_own_request(session, student, request_id)
    if not is_empty_draft(session, request):
        raise CreditBridgeError(tr("서류를 올렸거나 심사를 요청한 요청은 지울 수 없어요."))
    request_repo.delete(session, request)
    audit.record(session, student, "request.delete", "transfer_request", str(request_id))
    session.commit()


@dataclass(frozen=True)
class UploadResult:
    created: list[Syllabus]
    duplicates: list[Syllabus]  # 이 요청에 이미 올린 같은 문서 (저장된 분석 결과를 그대로 쓴다)
    # 분석에 실패했던 같은 문서: 다시 올리면 다시 분석한다 (글자 읽기부터 / AI 비교만)
    reprocess: list[Syllabus] = field(default_factory=list)
    reevaluate: list[Syllabus] = field(default_factory=list)


def add_syllabi(
    session: Session, storage: ObjectStorage, student: User, request: TransferRequest, files: list[UploadedFile]
) -> UploadResult:
    """파일을 검증해 객체 스토리지에 저장하고 강의계획서 행을 만든다. 분석 작업 등록은 호출자가 한다."""
    settings = get_settings()
    if request.status == RequestStatus.CLOSED:
        raise CreditBridgeError(tr("문서를 삭제해 종료된 요청이에요. 새 요청을 만들어 주세요."))
    if request.status != RequestStatus.DRAFT:
        raise CreditBridgeError(tr("심사에 제출한 요청에는 과목을 추가할 수 없어요."))
    if syllabus_repo.count_of_request(session, request.id) + len(files) > settings.max_syllabi_per_request:
        raise UploadRejectedError(
            tr(
                "강의계획서는 요청당 최대 {max_syllabi_per_request}건까지 올릴 수 있어요.",
                max_syllabi_per_request=settings.max_syllabi_per_request,
            )
        )
    validated = [(f, doc_text.validate_upload(f.filename, f.data, settings.max_upload_mb)) for f in files]
    result = UploadResult(created=[], duplicates=[])
    for f, ext in validated:
        digest = analysis.content_hash(f.data)
        existing = syllabus_repo.in_request_with_hash(session, request.id, digest)
        if existing is not None:
            latest = evaluation_repo.latest_for_syllabus(session, existing.id)
            if existing.status == SyllabusStatus.FAILED:
                existing.status, existing.error_message = SyllabusStatus.UPLOADED, None
                result.reprocess.append(existing)
            elif existing.status == SyllabusStatus.READY and latest is not None and latest.status == "failed":
                result.reevaluate.append(existing)
            else:
                result.duplicates.append(existing)
                continue
            audit.record(session, student, "syllabus.retry", "syllabus", str(existing.id), request=request.id)
            continue
        key = storage.new_key("syllabi", f.filename)
        storage.put(key, f.data, doc_text.CONTENT_TYPES[ext])
        syllabus = syllabus_repo.add(
            session,
            Syllabus(
                institution_id=request.source_institution_id,
                transfer_request_id=request.id,
                owner_id=student.id,
                source_file_key=key,
                content_hash=digest,
                original_filename=f.filename[:255],
                course_title=f.filename[:255],
                status=SyllabusStatus.UPLOADED,
            ),
        )
        result.created.append(syllabus)
        audit.record(session, student, "syllabus.upload", "syllabus", str(syllabus.id), request=request.id)
    session.commit()
    return result


def set_transcript(
    session: Session, storage: ObjectStorage, student: User, request: TransferRequest, file: UploadedFile
) -> None:
    ext = doc_text.validate_upload(file.filename, file.data, get_settings().max_upload_mb)
    if request.transcript_file_key:
        storage.delete(request.transcript_file_key)
    key = storage.new_key("transcripts", file.filename)
    storage.put(key, file.data, doc_text.CONTENT_TYPES[ext])
    request.transcript_file_key = key
    audit.record(session, student, "transcript.upload", "transfer_request", str(request.id))
    session.commit()


def confirm_link(
    session: Session, student: User, request: TransferRequest, entry_id: int, syllabus_id: int | None
) -> TranscriptEntry:
    entry = request_repo.get_entry(session, entry_id)
    if entry is None or entry.transfer_request_id != request.id:
        raise NotFoundError(tr("성적표 항목을 찾을 수 없어요."))
    if syllabus_id:
        syllabus = syllabus_repo.get(session, syllabus_id)
        if syllabus is None or syllabus.transfer_request_id != request.id:
            raise NotFoundError(tr("강의계획서를 찾을 수 없어요."))
        entry.syllabus_id = syllabus.id
    else:
        entry.syllabus_id = None
    entry.link_confirmed = True
    audit.record(session, student, "transcript.link", "transfer_request", str(request.id), entry=entry.id)
    session.commit()
    from backend.services import review  # review → decisions → appeals → student 순환을 피해 여기서 불러온다

    review.release_grade_failed(session, request)
    return entry


def store_supplement(
    session: Session, storage: ObjectStorage, student: User, syllabus: Syllabus, file: UploadedFile
) -> str:
    """보완 자료 파일을 저장한다. 텍스트 추출과 재분석은 작업 큐(syllabus.supplement)가 맡는다 (FR-08, FR-22).

    제출 전에는 언제든, 제출 뒤에는 심사관·교수의 보완 자료 요청이 열려 있을 때만 올릴 수 있다.
    """
    if syllabus.owner_id != student.id:
        raise PermissionDeniedError(tr("본인의 강의계획서만 보완할 수 있어요."))
    if syllabus.status in (SyllabusStatus.UPLOADED, SyllabusStatus.PROCESSING, SyllabusStatus.DELETED):
        raise CreditBridgeError(tr("분석이 끝난 강의계획서에만 보완 자료를 올릴 수 있어요."))
    request = request_repo.get(session, syllabus.transfer_request_id) if syllabus.transfer_request_id else None
    if request is None:
        raise NotFoundError(tr("편입 요청을 찾을 수 없어요."))
    latest = evaluation_repo.latest_for_syllabus(session, syllabus.id)
    if latest is not None and decision_repo.for_evaluation(session, latest.id) is not None:
        raise CreditBridgeError(tr("판정이 끝난 과목이에요. 결과에 이의가 있으면 이의 신청을 해 주세요."))
    open_requests = materials.open_for_syllabus(session, syllabus.id)
    if request.status != RequestStatus.DRAFT and not open_requests:
        raise CreditBridgeError(
            tr("심사 중인 과목은 학사처나 교수의 보완 자료 요청이 있을 때만 자료를 올릴 수 있어요.")
        )
    key = _save_supplement(session, storage, student, syllabus, file, open_requests)
    audit.record(session, student, "syllabus.supplement", "syllabus", str(syllabus.id))
    session.commit()
    return key


def store_supplement_by_staff(
    session: Session, storage: ObjectStorage, evaluator: User, evaluation_id: int, file: UploadedFile
) -> tuple[Syllabus, str]:
    """심사관이 학생 대신 보완 자료를 올린다 (권한 매트릭스: 문서 업로드는 심사관 소속 기관 전체).

    학생이 메일·종이로 낸 자료를 심사관이 받은 경우. 심사 중(제출 뒤)·판정 전 과목만. 열린 보완 요청은 처리됨으로
    바뀌고 학생에게 알림이 간다. 재분석은 작업 큐(syllabus.supplement)가 맡는다."""
    if evaluator.role != Role.EVALUATOR:
        raise PermissionDeniedError(tr("심사관 계정만 학생 대신 자료를 올릴 수 있어요."))
    evaluation = evaluation_repo.get(session, evaluation_id)
    if evaluation is None:
        raise NotFoundError(tr("심사 건을 찾을 수 없어요."))
    ensure_can_view_evaluation(session, evaluator, evaluation)
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    request = request_repo.get(session, evaluation.transfer_request_id) if evaluation.transfer_request_id else None
    if syllabus is None or request is None:
        raise NotFoundError(tr("심사 건을 찾을 수 없어요."))
    latest = evaluation_repo.latest_for_syllabus(session, syllabus.id)
    if latest is None or latest.id != evaluation.id:
        raise CreditBridgeError(tr("최신 분석 화면에서 올려 주세요."))
    if decision_repo.for_evaluation(session, evaluation.id) is not None:
        raise CreditBridgeError(tr("판정이 끝난 과목에는 자료를 올릴 수 없어요. 이의 신청으로 다시 심사해요."))
    if syllabus.status in (SyllabusStatus.UPLOADED, SyllabusStatus.PROCESSING, SyllabusStatus.DELETED):
        raise CreditBridgeError(tr("분석이 끝난 강의계획서에만 보완 자료를 올릴 수 있어요."))
    open_requests = materials.open_for_syllabus(session, syllabus.id)
    key = _save_supplement(session, storage, evaluator, syllabus, file, open_requests)
    notifications.notify(
        session,
        [u for u in [user_repo.get_by_id(session, request.student_id)] if u is not None],
        "material.uploaded_by_staff",
        N_("학사처가 {course} 보완 자료를 대신 올렸어요. 다시 분석한 결과가 나오면 화면에 반영돼요.").format(
            course=(syllabus.course_code or syllabus.course_title or N_("강의계획서")).strip()
        ),
        f"/student/requests/{request.id}",
    )
    audit.record(session, evaluator, "syllabus.supplement", "syllabus", str(syllabus.id), by_staff=True)
    session.commit()
    return syllabus, key


def _save_supplement(
    session: Session,
    storage: ObjectStorage,
    actor: User,
    syllabus: Syllabus,
    file: UploadedFile,
    open_requests: list[MaterialRequest],
) -> str:
    ext = doc_text.validate_upload(file.filename, file.data, get_settings().max_upload_mb)
    key = storage.new_key("supplements", file.filename)
    storage.put(key, file.data, doc_text.CONTENT_TYPES[ext])
    material_repo.add_file(
        session,
        SupplementFile(
            syllabus_id=syllabus.id, file_key=key, material_request_id=open_requests[0].id if open_requests else None
        ),
    )
    # 원본이 바뀌었으므로 내용 해시도 새로 만든다 (이전 해시 + 보완 파일)
    syllabus.content_hash = analysis.content_hash(syllabus.content_hash.encode(), file.data)
    syllabus.status = SyllabusStatus.UPLOADED
    materials.mark_fulfilled(session, actor, syllabus)
    return key


def submit_request(session: Session, student: User, request: TransferRequest) -> int:
    """학사처에 심사를 요청한다. 정보가 충분한 과목은 바로 학과 교수에게 배정하고 그 건수를 돌려준다."""
    if request.status != RequestStatus.DRAFT:
        raise CreditBridgeError(tr("이미 제출한 요청이에요."))
    syllabi = syllabus_repo.of_request(session, request.id)
    if not syllabi:
        raise CreditBridgeError(tr("강의계획서를 한 건 이상 올려 주세요."))
    if any(s.status in (SyllabusStatus.UPLOADED, SyllabusStatus.PROCESSING) for s in syllabi):
        raise CreditBridgeError(tr("분석이 끝난 뒤에 제출할 수 있어요."))
    request.status = RequestStatus.SUBMITTED
    request.submitted_at = utcnow()
    audit.record(session, student, "request.submit", "transfer_request", str(request.id), courses=len(syllabi))
    session.commit()
    from backend.services import review  # review → decisions → appeals → student 순환을 피해 여기서 불러온다

    return review.assign_ready(session, request)


# ---------- 진행 상황 포털 (FR-21) ----------

STAGES = [N_("접수"), N_("AI 분석"), N_("교수 검토"), N_("확정")]


def grade_failed(grade: str | None) -> bool:
    """성적표 성적이 인정 최저 성적(C 이상·P/PASS/S) 미달인지. 성적이 없으면 미달이 아니다."""
    return grade is not None and grade.strip().upper() not in PASSING_GRADES


@dataclass(frozen=True)
class CourseRow:
    syllabus: Syllabus
    evaluation: CourseEvaluation | None
    decision: Decision | None
    stage: int  # STAGES 인덱스
    expected_done: datetime | None
    candidate_code: str | None
    candidate_credits: float | None
    transcript_grade: str | None
    appeal: Appeal | None = None
    open_materials: list[MaterialRequest] = field(default_factory=list)
    candidate_title: str | None = None
    candidate_department: str | None = None
    reviewer: User | None = None  # 판정했으면 판정 교수, 아니면 배정된 교수

    @property
    def grade_failed(self) -> bool:
        """성적이 인정 최저 성적 미달이라 심사 대상에서 빠진 과목 (판정 전일 때 화면에 '성적 기준 미달')."""
        return grade_failed(self.transcript_grade)

    @property
    def group(self) -> str:
        """학생 화면 필터: approved(인정 확정) / supplement(보완 필요) / review(심사 중) / other."""
        if self.decision is None and self.grade_failed:
            return "other"
        if self.decision is not None and not (self.appeal and self.appeal.status in ("submitted", "accepted")):
            return "approved" if self.decision.result in ("direct", "elective") else "other"
        if self.open_materials or (self.evaluation and self.evaluation.recommendation == "insufficient"):
            return "supplement"
        return "review"


def course_rows(session: Session, request: TransferRequest) -> list[CourseRow]:
    sla = timedelta(days=get_settings().review_sla_days)
    syllabi = syllabus_repo.of_request(session, request.id)
    grades = {e.syllabus_id: e.grade for e in request_repo.transcript_entries(session, request.id) if e.syllabus_id}
    evaluations = {s.id: evaluation_repo.latest_for_syllabus(session, s.id) for s in syllabi}
    decisions = decision_repo.for_evaluations(session, [e.id for e in evaluations.values() if e])
    courses = catalog_repo.courses_by_ids(
        session, [e.candidate_course_id for e in evaluations.values() if e and e.candidate_course_id]
    )
    appeals = appeal_repo.latest_for_evaluations(session, [e.id for e in evaluations.values() if e])
    open_materials: dict[int, list[MaterialRequest]] = {}
    for m in material_repo.for_syllabi(session, [s.id for s in syllabi]):
        if m.status == "open":
            open_materials.setdefault(m.syllabus_id, []).append(m)
    rows = []
    for s in syllabi:
        ev = evaluations[s.id]
        decision = decisions.get(ev.id) if ev else None
        assigned = evaluation_repo.assigned_at(session, ev.id) if ev else None
        expected: datetime | None
        appeal = appeals.get(ev.id) if ev else None
        if decision and appeal is not None and appeal.status == "accepted":
            stage, expected = 2, (assigned or appeal.created_at) + sla  # 이의 신청 재판정 대기
        elif decision:
            stage, expected = 3, decision.decided_at
        elif grade_failed(grades.get(s.id)):
            stage, expected = 3, None  # 성적 기준 미달: 심사 없이 제외로 끝남
        elif assigned:
            stage, expected = 2, assigned + sla
        elif ev and ev.status == "done":
            stage = 1
            expected = request.submitted_at + sla + timedelta(days=2) if request.submitted_at else None
        else:
            stage, expected = (1 if s.status == SyllabusStatus.READY else 0), None
        course = courses.get(ev.candidate_course_id) if ev and ev.candidate_course_id else None
        assignment = evaluation_repo.active_assignment(session, ev.id) if ev else None
        reviewer_id = decision.decided_by if decision else (assignment.reviewer_id if assignment else None)
        rows.append(
            CourseRow(
                syllabus=s,
                evaluation=ev,
                decision=decision,
                stage=stage,
                expected_done=expected,
                candidate_code=course.code if course else None,
                candidate_credits=course.credits if course else None,
                transcript_grade=grades.get(s.id),
                appeal=appeals.get(ev.id) if ev else None,
                open_materials=open_materials.get(s.id, []),
                candidate_title=course.title if course else None,
                candidate_department=course.department_name if course else None,
                reviewer=user_repo.get_by_id(session, reviewer_id) if reviewer_id else None,
            )
        )
    return rows


# ---------- 사전 시뮬레이션 (FR-15) ----------


@dataclass(frozen=True)
class Simulation:
    credits_low: float
    credits_high: float
    semesters_low: int
    semesters_high: int
    extra_cost_low: int
    extra_cost_high: int
    source_credits: float
    degree_credits: int
    tuition_per_credit: int


def simulate(
    rows: list[CourseRow], degree_credits: int, tuition_per_credit: int, credits_per_semester: int = 15
) -> Simulation:
    """예상 인정 학점·남은 학기·미인정 학점의 추가 비용을 범위값으로 계산한다 (예상치)."""
    low = high = source_total = 0.0
    for row in rows:
        ev = row.evaluation
        source = row.syllabus.credits or row.candidate_credits or 3.0
        source_total += source
        if ev is None or ev.status != "done":
            continue
        if row.grade_failed:
            continue
        credit = min(source, row.candidate_credits) if row.candidate_credits else source
        decided = row.decision.result if row.decision else None
        if decided:
            gained = credit if decided in ("direct", "elective") else 0.0
            low += gained
            high += gained
        elif ev.recommendation == "direct":
            high += credit
            low += credit if ev.confidence == "high" else 0.0
        elif ev.recommendation == "elective":
            high += source
            low += source if ev.confidence == "high" else 0.0
        elif ev.recommendation == "insufficient":
            high += credit
    remaining_high = max(degree_credits - low, 0)
    remaining_low = max(degree_credits - high, 0)
    return Simulation(
        credits_low=low,
        credits_high=high,
        semesters_low=math.ceil(remaining_low / credits_per_semester),
        semesters_high=math.ceil(remaining_high / credits_per_semester),
        extra_cost_low=round((source_total - high) * tuition_per_credit),
        extra_cost_high=round((source_total - low) * tuition_per_credit),
        source_credits=source_total,
        degree_credits=degree_credits,
        tuition_per_credit=tuition_per_credit,
    )


def merged_rows(groups: list[list[CourseRow]]) -> list[CourseRow]:
    """여러 편입 요청의 과목을 합친다 (학생 홈 전체 합계). groups는 최근 요청부터.

    같은 과목(같은 출신 대학의 같은 과목 코드, 코드가 없으면 같은 파일)을 여러 요청에 올렸으면 한 번만 센다:
    판정이 난 행을 쓰고, 없으면 가장 최근 요청의 행을 쓴다.
    """
    chosen: dict[str, CourseRow] = {}
    for rows in groups:
        for row in rows:
            code = "".join(row.syllabus.course_code.split()).upper()
            key = f"{row.syllabus.institution_id}:{code}" if code else f"hash:{row.syllabus.content_hash}"
            kept = chosen.get(key)
            if kept is None or (kept.decision is None and row.decision is not None):
                chosen[key] = row
    return list(chosen.values())


def ensure_student(user: User) -> None:
    if user.role != Role.STUDENT:
        raise PermissionDeniedError(tr("학생 계정으로 로그인해 주세요."))


# ---------- 대시보드: 할 일과 서류 준비율 ----------


@dataclass(frozen=True)
class Todo:
    kind: str  # missing: 학생이 채워야 할 서류(앰버) / action: 다음 단계(파랑)
    label: str
    href: str


@dataclass(frozen=True)
class Readiness:
    """편입 요청 하나의 서류 준비 상태. 준비율은 제출 전(초안)에만 센다."""

    request: TransferRequest
    done: int
    total: int
    todos: list[Todo]

    @property
    def percent(self) -> int | None:
        return round(self.done * 100 / self.total) if self.total else None

    @property
    def missing(self) -> int:
        return sum(1 for t in self.todos if t.kind == "missing")


def readiness(session: Session, request: TransferRequest) -> Readiness:
    """할 일: 보완 자료 요청, (초안이면) 성적표·강의계획서 누락과 연결 확인, 분석 실패, 심사 요청."""
    base = f"/student/requests/{request.id}"
    syllabi = syllabus_repo.of_request(session, request.id)
    todos: list[Todo] = []
    asked = {m.syllabus_id for m in material_repo.for_syllabi(session, [s.id for s in syllabi]) if m.status == "open"}
    for s in syllabi:
        if s.id in asked:
            course = (s.course_code or s.course_title or s.original_filename).strip()
            todos.append(Todo("missing", tr("{course} 보완 자료 제출", course=course), f"/student/syllabi/{s.id}"))
    done = total = 0
    if request.status == RequestStatus.DRAFT:
        entries = request_repo.transcript_entries(session, request.id)
        total += 1
        if request.transcript_file_key:
            done += 1
        else:
            todos.append(Todo("missing", tr("성적표 올리기"), f"{base}#transcript"))
        if entries:
            # 강의계획서 없이 확인한 과목(인정 신청하지 않는 과목)은 준비된 것으로 본다
            unlinked = sum(1 for e in entries if e.syllabus_id is None and not e.link_confirmed)
            unconfirmed = sum(1 for e in entries if e.syllabus_id is not None and not e.link_confirmed)
            total += len(entries)
            done += len(entries) - unlinked - unconfirmed
            if unlinked:
                todos.append(Todo("missing", tr("강의계획서 미등록 {unlinked}건", unlinked=unlinked), f"{base}#upload"))
            if unconfirmed:
                todos.append(
                    Todo(
                        "missing",
                        tr("성적표 과목 연결 확인 {unconfirmed}건", unconfirmed=unconfirmed),
                        f"{base}#transcript",
                    )
                )
        else:
            total += 1
            if syllabi:
                done += 1
            else:
                todos.append(Todo("missing", tr("강의계획서 올리기"), f"{base}#upload"))
        failed = sum(1 for s in syllabi if s.status == SyllabusStatus.FAILED)
        if failed:
            todos.append(Todo("missing", tr("분석하지 못한 강의계획서 {failed}건 다시 올리기", failed=failed), base))
        busy = any(s.status in (SyllabusStatus.UPLOADED, SyllabusStatus.PROCESSING) for s in syllabi)
        if syllabi and not busy and not any(t.kind == "missing" for t in todos):
            todos.append(Todo("action", tr("학사처에 심사 요청하기"), f"{base}#submit"))
    return Readiness(request, done, total, todos)
