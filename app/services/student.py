"""학생 서비스: 편입 요청, 문서 업로드, 성적표 연결, 보완 자료, 심사 제출, 진행 상황 (FR-01, 02, 08, 15, 21)."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.base import utcnow
from app.documents import text as doc_text
from app.documents.storage import ObjectStorage
from app.errors import CreditBridgeError, NotFoundError, PermissionDeniedError, UploadRejectedError
from app.models import CourseEvaluation, Decision, Syllabus, TranscriptEntry, TransferRequest, User
from app.models.enums import RequestStatus, Role, SyllabusStatus
from app.repositories import catalog as catalog_repo
from app.repositories import decisions as decision_repo
from app.repositories import evaluations as evaluation_repo
from app.repositories import requests as request_repo
from app.repositories import syllabi as syllabus_repo
from app.services import analysis, audit


@dataclass(frozen=True)
class UploadedFile:
    filename: str
    data: bytes


def get_own_request(session: Session, student: User, request_id: int) -> TransferRequest:
    request = request_repo.get(session, request_id)
    if request is None:
        raise NotFoundError("편입 요청을 찾을 수 없어요.")
    if request.student_id != student.id:
        raise PermissionDeniedError("본인의 편입 요청만 볼 수 있어요.")
    return request


def create_request(session: Session, student: User, source_institution_id: int, major: str) -> TransferRequest:
    """MVP의 학생은 입학이 확정되어 대상 대학에 소속된 학생이다. 대상 대학은 학생의 소속 대학으로 정해진다."""
    target = catalog_repo.get_institution(session, student.institution_id) if student.institution_id else None
    if target is None or not target.is_target:
        raise CreditBridgeError("입학이 확정된 대학에 소속된 학생 계정만 편입 요청을 만들 수 있어요.")
    source = catalog_repo.get_institution(session, source_institution_id)
    if source is None or source.is_target:
        raise CreditBridgeError("다니던 대학을 다시 선택해 주세요.")
    if major not in catalog_repo.departments_of(session, target.id):
        raise CreditBridgeError("편입 전공을 다시 선택해 주세요.")
    request = request_repo.add(
        session,
        TransferRequest(
            student_id=student.id, source_institution_id=source.id, target_institution_id=target.id, major=major
        ),
    )
    audit.record(session, student, "request.create", "transfer_request", str(request.id), target=target.id, major=major)
    session.commit()
    return request


@dataclass(frozen=True)
class UploadResult:
    created: list[Syllabus]
    duplicates: list[Syllabus]  # 이 요청에 이미 올린 같은 문서 (저장된 분석 결과를 그대로 쓴다)


def add_syllabi(
    session: Session, storage: ObjectStorage, student: User, request: TransferRequest, files: list[UploadedFile]
) -> UploadResult:
    """파일을 검증해 객체 스토리지에 저장하고 강의계획서 행을 만든다. 분석 작업 등록은 호출자가 한다."""
    settings = get_settings()
    if request.status != RequestStatus.DRAFT:
        raise CreditBridgeError("심사에 제출한 요청에는 과목을 추가할 수 없어요.")
    if syllabus_repo.count_of_request(session, request.id) + len(files) > settings.max_syllabi_per_request:
        raise UploadRejectedError(f"강의계획서는 요청당 최대 {settings.max_syllabi_per_request}건까지 올릴 수 있어요.")
    validated = [(f, doc_text.validate_upload(f.filename, f.data, settings.max_upload_mb)) for f in files]
    created: list[Syllabus] = []
    duplicates: list[Syllabus] = []
    for f, ext in validated:
        digest = analysis.content_hash(f.data)
        existing = syllabus_repo.in_request_with_hash(session, request.id, digest)
        if existing is not None:
            duplicates.append(existing)
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
        created.append(syllabus)
        audit.record(session, student, "syllabus.upload", "syllabus", str(syllabus.id), request=request.id)
    session.commit()
    return UploadResult(created=created, duplicates=duplicates)


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
        raise NotFoundError("성적표 항목을 찾을 수 없어요.")
    if syllabus_id:
        syllabus = syllabus_repo.get(session, syllabus_id)
        if syllabus is None or syllabus.transfer_request_id != request.id:
            raise NotFoundError("강의계획서를 찾을 수 없어요.")
        entry.syllabus_id = syllabus.id
    else:
        entry.syllabus_id = None
    entry.link_confirmed = True
    audit.record(session, student, "transcript.link", "transfer_request", str(request.id), entry=entry.id)
    session.commit()
    return entry


def store_supplement(
    session: Session, storage: ObjectStorage, student: User, syllabus: Syllabus, file: UploadedFile
) -> str:
    """보완 자료 파일을 저장한다. 텍스트 추출과 재분석은 작업 큐(syllabus.supplement)가 맡는다 (FR-08)."""
    if syllabus.owner_id != student.id:
        raise PermissionDeniedError("본인의 강의계획서만 보완할 수 있어요.")
    if syllabus.status in (SyllabusStatus.UPLOADED, SyllabusStatus.PROCESSING, SyllabusStatus.DELETED):
        raise CreditBridgeError("분석이 끝난 강의계획서에만 보완 자료를 올릴 수 있어요.")
    ext = doc_text.validate_upload(file.filename, file.data, get_settings().max_upload_mb)
    key = storage.new_key("supplements", file.filename)
    storage.put(key, file.data, doc_text.CONTENT_TYPES[ext])
    # 원본이 바뀌었으므로 내용 해시도 새로 만든다 (이전 해시 + 보완 파일)
    syllabus.content_hash = analysis.content_hash(syllabus.content_hash.encode(), file.data)
    syllabus.status = SyllabusStatus.UPLOADED
    audit.record(session, student, "syllabus.supplement", "syllabus", str(syllabus.id))
    session.commit()
    return key


def submit_request(session: Session, student: User, request: TransferRequest) -> None:
    if request.status != RequestStatus.DRAFT:
        raise CreditBridgeError("이미 제출한 요청이에요.")
    syllabi = syllabus_repo.of_request(session, request.id)
    if not syllabi:
        raise CreditBridgeError("강의계획서를 한 건 이상 올려 주세요.")
    if any(s.status in (SyllabusStatus.UPLOADED, SyllabusStatus.PROCESSING) for s in syllabi):
        raise CreditBridgeError("분석이 끝난 뒤에 제출할 수 있어요.")
    request.status = RequestStatus.SUBMITTED
    request.submitted_at = utcnow()
    audit.record(session, student, "request.submit", "transfer_request", str(request.id), courses=len(syllabi))
    session.commit()


def delete_documents(session: Session, storage: ObjectStorage, student: User, request: TransferRequest) -> None:
    """개인정보 삭제 요청 (FR-13): 원본 파일과 추출 텍스트를 지운다. 판정 기록(개인정보 없음)은 감사용으로 남는다."""
    for syllabus in syllabus_repo.of_request(session, request.id):
        if syllabus.source_file_key:
            storage.delete(syllabus.source_file_key)
        syllabus.source_file_key = None
        syllabus.raw_text = ""
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
    audit.record(session, student, "privacy.delete_documents", "transfer_request", str(request.id))
    session.commit()


# ---------- 진행 상황 포털 (FR-21) ----------

STAGES = ["접수", "AI 분석", "교수 검토", "확정"]


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


def course_rows(session: Session, request: TransferRequest) -> list[CourseRow]:
    sla = timedelta(days=get_settings().review_sla_days)
    syllabi = syllabus_repo.of_request(session, request.id)
    grades = {e.syllabus_id: e.grade for e in request_repo.transcript_entries(session, request.id) if e.syllabus_id}
    evaluations = {s.id: evaluation_repo.latest_for_syllabus(session, s.id) for s in syllabi}
    decisions = decision_repo.for_evaluations(session, [e.id for e in evaluations.values() if e])
    courses = catalog_repo.courses_by_ids(
        session, [e.candidate_course_id for e in evaluations.values() if e and e.candidate_course_id]
    )
    rows = []
    for s in syllabi:
        ev = evaluations[s.id]
        decision = decisions.get(ev.id) if ev else None
        assigned = evaluation_repo.assigned_at(session, ev.id) if ev else None
        expected: datetime | None
        if decision:
            stage, expected = 3, decision.decided_at
        elif assigned:
            stage, expected = 2, assigned + sla
        elif ev and ev.status == "done":
            stage = 1
            expected = request.submitted_at + sla + timedelta(days=2) if request.submitted_at else None
        else:
            stage, expected = (1 if s.status == SyllabusStatus.READY else 0), None
        course = courses.get(ev.candidate_course_id) if ev and ev.candidate_course_id else None
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
            )
        )
    return rows


# ---------- 사전 시뮬레이션 (FR-15) ----------

PASSING = {"A+", "A", "A0", "A-", "B+", "B", "B0", "B-", "C+", "C", "C0", "P", "PASS", "S"}


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
        passing = row.transcript_grade is None or row.transcript_grade.upper() in PASSING
        if not passing:
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


def ensure_student(user: User) -> None:
    if user.role != Role.STUDENT:
        raise PermissionDeniedError("학생 계정으로 로그인해 주세요.")
