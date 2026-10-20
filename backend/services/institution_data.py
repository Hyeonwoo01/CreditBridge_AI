"""기관 데이터 준비 (기관 관리자): 계정·과목 CSV 가져오기, 출신 대학 등록, 과목별 기준 강의계획서.

- 계정 CSV: 새 계정은 임시 비밀번호로 만들고 첫 로그인 때 바꾸게 한다. 임시 비밀번호는 가져온 직후 한 번만
  관리자에게 보여주고 저장하지 않는다(해시만 저장). 이미 있는 이메일은 건너뛴다.
- 과목 CSV: 과목 코드 기준으로 새로 만들거나 고친다. 필수 개념은 학과가 정해 `;`로 구분해 적는다.
- 기준 강의계획서가 없는 과목은 AI 비교 후보에서 빠진다(services/analysis.py::_references).
CSV 파일 검사·인코딩은 services/csv_import.py. 한 줄이라도 틀리면 아무것도 저장하지 않는다.
"""

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.ai.injection import detect
from backend.ai.llm_client import LLMClient
from backend.config import get_settings
from backend.db.base import utcnow
from backend.documents import text as doc_text
from backend.documents.storage import ObjectStorage
from backend.errors import CreditBridgeError, LLMError, LLMNotConfiguredError, NotFoundError, PermissionDeniedError
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import Assignment, Course, Department, Institution, Syllabus, User
from backend.models.enums import Role, SyllabusStatus
from backend.repositories import catalog as catalog_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.services import analysis, audit, csv_import, notifications, review
from backend.services.auth import RESET_AFTER, ensure_not_demo, hash_password, temporary_password, unusable_password

logger = logging.getLogger(__name__)

# department: 교수·심사관은 소속 학과, 학생은 편입 전공. source_institution: 학생의 출신 대학(등록된 이름 그대로)
ACCOUNT_COLUMNS = ["email", "name", "role", "department", "source_institution"]
COURSE_COLUMNS = ["code", "title", "credits", "department", "level", "concepts"]
ROLES = {
    "student": Role.STUDENT,
    "학생": Role.STUDENT,
    "evaluator": Role.EVALUATOR,
    "심사관": Role.EVALUATOR,
    "professor": Role.PROFESSOR,
    "교수": Role.PROFESSOR,
    "admin": Role.ADMIN,
    "관리자": Role.ADMIN,
}
MAX_ACCOUNT_ROWS = 2000
MAX_COURSE_ROWS = 3000
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class CreatedAccount:
    email: str
    name: str
    role: str
    temporary_password: str  # 메일로 설정 링크를 보내는 경우 빈 문자열
    user_id: int = 0


@dataclass
class AccountImport:
    created: list[CreatedAccount] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # 이미 있는 이메일
    errors: list[str] = field(default_factory=list)


@dataclass
class CourseImport:
    created: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CourseRow:
    course: Course
    latest_upload: Syllabus | None  # 가장 최근에 올린 기준 강의계획서 (처리 중·실패 포함)

    @property
    def concepts(self) -> list[str]:
        return list(self.course.concepts or [])

    @property
    def reference_status(self) -> str:
        """ready(등록됨) / processing(읽는 중) / failed(실패, 이전 것이 있으면 그대로 사용) / missing(없음)."""
        upload = self.latest_upload
        if upload is not None and upload.id != self.course.reference_syllabus_id:
            if upload.status in (SyllabusStatus.UPLOADED, SyllabusStatus.PROCESSING):
                return "processing"
            if upload.status == SyllabusStatus.FAILED:
                return "failed"
        return "ready" if self.course.reference_syllabus_id else "missing"


@dataclass(frozen=True)
class Overview:
    institution: Institution
    role_counts: dict[str, int]
    pending_password: int
    locked_out: int  # 로그인 실패가 이어져 비밀번호가 초기화된 계정
    inactive: int  # 비활성화된 계정 (역할별 계정 수에서 빠진다)
    courses: list[CourseRow]
    departments_without_professor: list[str]
    source_institutions: list[Institution]
    used_source_ids: set[int] = field(default_factory=set)  # 학생·요청·동등 과목표가 가리켜 지울 수 없는 출신 대학

    @property
    def missing_reference(self) -> int:
        return sum(1 for r in self.courses if r.course.reference_syllabus_id is None)


def department_named(session: Session, institution_id: int, name: str) -> Department:
    """그 이름의 학과 행. 없으면 만든다 (과목 CSV·계정 CSV)."""
    found = catalog_repo.department_by_name(session, institution_id, name)
    return found or catalog_repo.add_department(session, Department(institution_id=institution_id, name=name))


def ensure_admin(user: User) -> int:
    if user.role != Role.ADMIN or user.institution_id is None:
        raise PermissionDeniedError(tr("기관 관리자만 사용할 수 있어요."))
    return user.institution_id


def overview(session: Session, admin: User) -> Overview:
    institution_id = ensure_admin(admin)
    institution = catalog_repo.get_institution(session, institution_id)
    if institution is None:
        raise NotFoundError(tr("기관을 찾을 수 없어요."))
    courses = catalog_repo.courses_of(session, institution_id)
    uploads = syllabus_repo.latest_reference_uploads(session, institution_id)
    staffed = user_repo.professor_departments(session, institution_id)
    departments = catalog_repo.course_departments(session, institution_id)
    return Overview(
        institution=institution,
        role_counts=user_repo.role_counts(session, institution_id),
        pending_password=user_repo.pending_password_change(session, institution_id),
        locked_out=user_repo.locked_out_count(session, institution_id, RESET_AFTER),
        inactive=user_repo.inactive_count(session, institution_id),
        courses=[CourseRow(c, uploads.get(c.code)) for c in courses],
        departments_without_professor=[d.name for d in departments if d.id not in staffed],
        source_institutions=catalog_repo.source_institutions(session, institution_id),
        used_source_ids=catalog_repo.used_source_institution_ids(session, institution_id),
    )


# ---------- 계정 ----------


@dataclass(frozen=True)
class ActiveChange:
    user: User
    moved: int = 0  # 다른 교수에게 넘긴 진행 중 심사
    released: int = 0  # 같은 학과에 다른 교수가 없어 배정을 비운 심사


def set_active(session: Session, admin: User, email: str, active: bool) -> ActiveChange:
    """계정 비활성화·다시 활성화. 계정은 지우지 않는다(판정·감사 기록이 그 사람을 가리킨다).

    비활성화하면 로그인·배정·알림 메일에서 빠지고 다른 기기의 로그인도 끊긴다. 교수였다면 진행 중인 심사를
    같은 학과의 다른 교수에게 넘기고, 넘길 사람이 없으면 배정을 비워 심사관이 다시 배정하게 한다."""
    institution_id = ensure_admin(admin)
    ensure_not_demo()
    user = user_repo.get_by_email(session, email)
    if user is None or user.institution_id != institution_id:
        raise NotFoundError(tr("우리 기관에 그 이메일의 계정이 없어요."))
    if user.id == admin.id:
        raise CreditBridgeError(tr("본인 계정은 비활성화할 수 없어요."))
    if user.is_active == active:
        raise CreditBridgeError(tr("이미 활성 상태인 계정이에요.") if active else tr("이미 비활성화된 계정이에요."))
    user.is_active = active
    user.deactivated_at = None if active else utcnow()
    session.flush()
    moved = released = 0
    if not active and user.role == Role.PROFESSOR:
        moved, released = _hand_over_reviews(session, admin, user)
    audit.record(
        session,
        admin,
        "account.reactivate" if active else "account.deactivate",
        "user",
        str(user.id),
        moved=moved,
        released=released,
    )
    session.commit()
    return ActiveChange(user, moved, released)


def _hand_over_reviews(session: Session, admin: User, professor: User) -> tuple[int, int]:
    today = utcnow().date()
    moved, released = 0, 0
    receivers: dict[int, tuple[User, int]] = {}
    for a in evaluation_repo.active_assignments_for(session, professor.id):
        try:
            reviewer, _ = review.pick_reviewer(session, admin.institution_id or 0, professor.dept, today)
        except CreditBridgeError:
            evaluation_repo.release_assignment(session, a)
            released += 1
            continue
        evaluation_repo.add_assignment(
            session,
            Assignment(
                course_evaluation_id=a.course_evaluation_id,
                reviewer_id=reviewer.id,
                assigned_by=admin.id,
                reassigned_from=professor.id,
            ),
        )
        receivers[reviewer.id] = (reviewer, receivers.get(reviewer.id, (reviewer, 0))[1] + 1)
        moved += 1
    for reviewer, n in receivers.values():
        notifications.notify(
            session,
            [reviewer],
            "assignment.delegated",
            N_("교수 계정 변경으로 진행 중인 심사 {n}건이 배정됐어요.").format(n=n),
            "/professor",
        )
    if moved or released:
        if moved and released:
            template = N_(
                "{dept} 교수 계정이 비활성화돼 진행 중인 심사 중 {moved}건은 같은 학과 다른 교수에게 넘겼어요, "
                "{released}건은 교수 배정이 필요해요."
            )
        elif moved:
            template = N_(
                "{dept} 교수 계정이 비활성화돼 진행 중인 심사 중 {moved}건은 같은 학과 다른 교수에게 넘겼어요."
            )
        else:
            template = N_("{dept} 교수 계정이 비활성화돼 진행 중인 심사 중 {released}건은 교수 배정이 필요해요.")
        notifications.notify(
            session,
            notifications.staff(session, admin.institution_id or 0, Role.EVALUATOR),
            "assignment.delegated",
            template.format(dept=professor.department_name or "", moved=moved, released=released),
            "/review",
        )
    return moved, released


def import_accounts(session: Session, admin: User, filename: str, data: bytes, by_email: bool = False) -> AccountImport:
    """by_email이면 비밀번호를 아무도 모르는 값으로 두고(호출자가 설정 링크 메일을 보낸다)
    임시 비밀번호를 만들지 않는다."""
    institution_id = ensure_admin(admin)
    departments = set(catalog_repo.departments_of(session, institution_id))
    result = AccountImport()
    pending: list[tuple[str, str, Role, str | None, int | None]] = []
    seen: set[str] = set()
    for line_no, row in csv_import.read_rows(filename, data, ACCOUNT_COLUMNS, ACCOUNT_COLUMNS[:3], MAX_ACCOUNT_ROWS):
        problems = []
        email = row.get("email", "").lower()
        name = row.get("name", "")
        role = ROLES.get(row.get("role", "").lower()) or ROLES.get(row.get("role", ""))
        department = row.get("department", "") or None
        source_name = row.get("source_institution", "")
        source_id: int | None = None
        if not _EMAIL.match(email) or len(email) > 255:
            problems.append(tr("이메일 형식이 아님"))
        elif email in seen:
            problems.append(tr("파일 안에서 이메일이 중복됨"))
        if not name:
            problems.append(tr("이름 없음"))
        elif len(name) > 100:
            problems.append(tr("이름은 100자까지"))
        if role is None:
            problems.append(tr("역할은 student·evaluator·professor·admin(또는 학생·심사관·교수·관리자) 중 하나"))
        if department and len(department) > 50:
            problems.append(tr("학과는 50자까지"))
        if role == Role.PROFESSOR:
            if not department:
                problems.append(tr("교수는 학과가 필요(과목 배정 기준)"))
            elif departments and department not in departments:
                problems.append(
                    tr(
                        "과목 목록에 없는 학과({department}). 과목 CSV의 학과명과 똑같이 써 주세요",
                        department=department,
                    )
                )
        if role == Role.STUDENT:
            # 학생의 department는 편입 전공: 과목이 있는 학과여야 후보 과목·배정이 맞는다
            if department and departments and department not in departments:
                problems.append(
                    tr(
                        "과목 목록에 없는 편입 전공({department}). 과목 CSV의 학과명과 똑같이 써 주세요",
                        department=department,
                    )
                )
            if source_name:
                source = catalog_repo.source_institution_by_name(session, institution_id, source_name)
                if source is None:
                    problems.append(
                        tr(
                            "등록되지 않은 출신 대학({source}). ④ 출신 대학에 먼저 등록해 주세요",
                            source=source_name,
                        )
                    )
                else:
                    source_id = source.id
        elif source_name:
            problems.append(tr("출신 대학은 학생 계정에만 적어요"))
        if not problems:
            existing = user_repo.get_by_email(session, email)
            if existing is not None and existing.institution_id != institution_id:
                problems.append(tr("다른 기관에 이미 있는 이메일"))
            elif existing is not None:
                result.skipped.append(email)
                seen.add(email)
                continue
        seen.add(email)
        if problems or role is None:
            result.errors.append(tr("{line_no}행: {problems}", line_no=line_no, problems=", ".join(problems)))
            continue
        pending.append((email, name, role, department, source_id))
    if result.errors:
        return result
    if not pending and not result.skipped:
        raise CreditBridgeError(tr("가져올 행이 없어요."))
    for email, name, role, department, source_id in pending:
        password = "" if by_email else temporary_password()
        created = user_repo.add(
            session,
            User(
                email=email,
                name=name,
                role=role,
                institution_id=institution_id,
                department_id=department_named(session, institution_id, department).id if department else None,
                source_institution_id=source_id,
                password_hash=unusable_password() if by_email else hash_password(password),
                must_change_password=True,
            ),
        )
        result.created.append(CreatedAccount(email, name, role, password, created.id))
    audit.record(
        session,
        admin,
        "account.import",
        "institution",
        str(institution_id),
        created=len(result.created),
        skipped=len(result.skipped),
        by_email=by_email,
    )
    session.commit()
    return result


# ---------- 과목 ----------


def _concepts(value: str) -> list[str]:
    return list(dict.fromkeys(c.strip() for c in value.split(";") if c.strip()))


def import_courses(session: Session, admin: User, filename: str, data: bytes) -> CourseImport:
    institution_id = ensure_admin(admin)
    result = CourseImport()
    parsed: list[tuple[str, str, float, str, str, list[str]]] = []
    seen: set[str] = set()
    required = ["code", "title", "credits", "department", "concepts"]
    for line_no, row in csv_import.read_rows(filename, data, COURSE_COLUMNS, required, MAX_COURSE_ROWS):
        problems = []
        code, title, department = row.get("code", ""), row.get("title", ""), row.get("department", "")
        if not code:
            problems.append(tr("과목 코드 없음"))
        elif len(code) > 30:
            problems.append(tr("과목 코드는 30자까지"))
        elif code in seen:
            problems.append(tr("파일 안에서 과목 코드가 중복됨"))
        if not title:
            problems.append(tr("과목명 없음"))
        elif len(title) > 200:
            problems.append(tr("과목명은 200자까지"))
        credits = 0.0
        try:
            credits = float(row.get("credits", ""))
        except ValueError:
            problems.append(tr("학점은 숫자"))
        else:
            if not 0 < credits <= 30:
                problems.append(tr("학점은 0보다 크고 30 이하"))
        if not department:
            problems.append(tr("학과 없음"))
        elif len(department) > 50:
            problems.append(tr("학과는 50자까지"))
        concepts = _concepts(row.get("concepts", ""))
        if not concepts:
            problems.append(tr("필수 개념을 ;로 구분해 1개 이상"))
        elif any(len(c) > 200 for c in concepts):
            problems.append(tr("필수 개념 하나는 200자까지"))
        seen.add(code)
        if problems:
            result.errors.append(tr("{line_no}행: {problems}", line_no=line_no, problems=", ".join(problems)))
            continue
        parsed.append((code, title, credits, department, row.get("level", ""), concepts))
    if result.errors:
        return result
    if not parsed:
        raise CreditBridgeError(tr("가져올 행이 없어요."))
    for code, title, credits, department, level, concepts in parsed:
        course = catalog_repo.course_by_code(session, institution_id, code)
        if course is None:
            catalog_repo.add_course(
                session,
                Course(
                    institution_id=institution_id,
                    code=code,
                    title=title,
                    credits=credits,
                    department_id=department_named(session, institution_id, department).id,
                    level=level,
                    concepts=concepts,
                ),
            )
            result.created += 1
        else:
            course.title, course.credits, course.concepts = title, credits, concepts
            course.department_id = department_named(session, institution_id, department).id
            if level:
                course.level = level
            result.updated += 1
    audit.record(
        session,
        admin,
        "course.import",
        "institution",
        str(institution_id),
        created=result.created,
        updated=result.updated,
    )
    session.commit()
    return result


# ---------- 출신 대학 ----------


def add_source_institution(session: Session, admin: User, name: str, country: str) -> Institution:
    """④ 출신 대학 목록에 올린다. 다른 대학이 같은 이름으로 먼저 만든 행이 있으면 그 행을 함께 쓴다."""
    institution_id = ensure_admin(admin)
    name, country = name.strip(), country.strip().upper()
    if not name or len(name) > 200:
        raise CreditBridgeError(tr("대학 이름을 200자 이내로 적어 주세요."))
    if not re.fullmatch(r"[A-Z]{2}", country):
        raise CreditBridgeError(tr("국가는 두 글자 코드로 적어 주세요 (예: KR, US)."))
    if catalog_repo.source_institution_by_name(session, institution_id, name) is not None:
        raise CreditBridgeError(tr("이미 등록된 출신 대학이에요."))
    institution = catalog_repo.shared_source_by_name(session, name)
    if institution is None:
        institution = catalog_repo.add_institution(session, Institution(name=name, country=country, is_target=False))
    catalog_repo.add_source_link(session, institution_id, institution.id)
    audit.record(session, admin, "institution.create", "institution", str(institution.id))
    session.commit()
    return institution


def delete_source_institution(session: Session, admin: User, source_id: int) -> str:
    """잘못 등록한 출신 대학을 우리 대학 목록에서 지운다. 우리 학생 계정·편입 요청·동등 과목표가 가리키면 지우지 않는다.
    다른 대학도 쓰지 않는 행이면 행까지 지운다. 지운 대학 이름을 돌려준다."""
    institution_id = ensure_admin(admin)
    institution = catalog_repo.get_institution(session, source_id)
    if institution is None or catalog_repo.source_link(session, institution_id, source_id) is None:
        raise NotFoundError(tr("출신 대학을 찾을 수 없어요."))
    usage = catalog_repo.source_usage(session, institution_id, source_id)
    if any(usage.values()):
        labels = {
            "students": tr("학생 계정 {n}개", n=usage["students"]),
            "requests": tr("편입 요청 {n}건", n=usage["requests"]),
            "equivalencies": tr("동등 과목표 {n}건", n=usage["equivalencies"]),
        }
        parts = [label for key, label in labels.items() if usage[key]]
        raise CreditBridgeError(
            tr("{name}은(는) 쓰이고 있어 지울 수 없어요 ({uses}).", name=institution.name, uses=", ".join(parts))
        )
    name = institution.name
    catalog_repo.remove_source_link(session, institution_id, source_id)
    if not catalog_repo.institution_referenced(session, source_id):
        catalog_repo.delete_institution(session, institution)
    audit.record(session, admin, "institution.delete", "institution", str(source_id), name=name)
    session.commit()
    return name


# ---------- 기준 강의계획서 ----------


def upload_reference(
    session: Session, storage: ObjectStorage, admin: User, course_id: int, filename: str, data: bytes
) -> tuple[Syllabus, Course]:
    """파일을 저장하고 강의계획서 행을 만든다. 텍스트 읽기 작업 등록은 호출자가 한다."""
    institution_id = ensure_admin(admin)
    course = catalog_repo.get_course(session, course_id)
    if course is None or course.institution_id != institution_id:
        raise NotFoundError(tr("과목을 찾을 수 없어요."))
    ext = doc_text.validate_upload(filename, data, get_settings().max_upload_mb)
    key = storage.new_key("references", filename)
    storage.put(key, data, doc_text.CONTENT_TYPES[ext])
    syllabus = syllabus_repo.add(
        session,
        Syllabus(
            institution_id=institution_id,
            source_file_key=key,
            content_hash=analysis.content_hash(b"reference:", data),
            original_filename=filename[:255],
            course_code=course.code,
            course_title=course.title,
            credits=course.credits,
            status=SyllabusStatus.UPLOADED,
        ),
    )
    audit.record(session, admin, "course.reference_upload", "course", str(course.id), syllabus=syllabus.id)
    session.commit()
    return syllabus, course


def remove_reference(session: Session, admin: User, course_id: int) -> Course:
    """과목에서 기준 강의계획서를 뺀다. 과목은 AI 비교 후보에서 빠지고, 이미 낸 분석 결과·판정은 그대로 둔다.
    파일과 강의계획서 행은 기록으로 남긴다(지우지 않음)."""
    institution_id = ensure_admin(admin)
    course = catalog_repo.get_course(session, course_id)
    if course is None or course.institution_id != institution_id:
        raise NotFoundError(tr("과목을 찾을 수 없어요."))
    if course.reference_syllabus_id is None:
        raise CreditBridgeError(tr("{code}에는 뺄 기준 강의계획서가 없어요.", code=course.code))
    removed = course.reference_syllabus_id
    course.reference_syllabus_id = None
    audit.record(session, admin, "course.reference_remove", "course", str(course.id), syllabus=removed)
    session.commit()
    return course


def process_reference(
    session: Session, syllabus_id: int, course_id: int, *, llm: LLMClient, storage: ObjectStorage
) -> None:
    """기준 강의계획서 텍스트를 읽어(스캔 페이지는 AI 전사) 과목에 연결한다. 실패하면 이전 것을 그대로 쓴다."""
    syllabus = syllabus_repo.get(session, syllabus_id)
    course = catalog_repo.get_course(session, course_id)
    if syllabus is None or course is None or syllabus.source_file_key is None:
        return
    syllabus.status = SyllabusStatus.PROCESSING
    session.commit()
    try:
        doc = analysis.document_to_text(llm, storage.get(syllabus.source_file_key), syllabus.original_filename)
    except (CreditBridgeError, LLMError) as exc:
        logger.warning("reference syllabus failed", extra={"syllabus_id": syllabus_id, "error": type(exc).__name__})
        doc = analysis.DocumentText("", 0.0, [])
        if isinstance(exc, LLMNotConfiguredError):  # 스캔본은 AI로 전사하는데 설정이 없다
            syllabus.status = SyllabusStatus.FAILED
            syllabus.error_message = analysis.NOT_CONFIGURED
            session.commit()
            return
    text, quality = doc.text, doc.quality
    if not text.strip():
        syllabus.status = SyllabusStatus.FAILED
        syllabus.error_message = N_(
            "문서에서 글자를 읽지 못했어요. 텍스트가 있는 PDF나 더 선명한 스캔본을 올려 주세요."
        )
        session.commit()
        return
    syllabus.raw_text = text
    syllabus.quality_score = quality
    syllabus.page_offsets = doc.page_offsets
    syllabus.injection_flags = [N_("{line}행: {text}").format(line=f.line_no, text=f.text) for f in detect(text)]
    syllabus.status = SyllabusStatus.READY
    course.reference_syllabus_id = syllabus.id
    session.commit()


# ---------- 첫 기관·관리자 (서버에서 한 번 실행: scripts/create_admin.py) ----------


def bootstrap_admin(
    session: Session,
    institution_name: str,
    country: str,
    email: str,
    name: str,
    tuition_per_credit: int | None = None,
    degree_credits: int | None = None,
) -> tuple[Institution, CreatedAccount]:
    """대상 대학(없으면 새로)과 그 기관의 관리자 계정을 만든다. 나머지 계정·과목은 관리자가 화면에서 가져온다."""
    institution_name, country, email, name = (
        institution_name.strip(),
        country.strip().upper(),
        email.strip().lower(),
        name.strip(),
    )
    if not institution_name or len(institution_name) > 200:
        raise CreditBridgeError(tr("대학 이름을 200자 이내로 적어 주세요."))
    if not re.fullmatch(r"[A-Z]{2}", country):
        raise CreditBridgeError(tr("국가는 두 글자 코드로 적어 주세요 (예: KR, US)."))
    if not _EMAIL.match(email):
        raise CreditBridgeError(tr("이메일 형식이 아니에요."))
    if not name or len(name) > 100:
        raise CreditBridgeError(tr("이름을 100자 이내로 적어 주세요."))
    if user_repo.get_by_email(session, email) is not None:
        raise CreditBridgeError(tr("이미 있는 이메일이에요."))
    institution = catalog_repo.target_institution_by_name(session, institution_name)
    if institution is None:
        institution = catalog_repo.add_institution(
            session,
            Institution(
                name=institution_name,
                country=country,
                is_target=True,
                tuition_per_credit=tuition_per_credit,
                degree_credits=degree_credits,
            ),
        )
    password = temporary_password()
    admin = user_repo.add(
        session,
        User(
            email=email,
            name=name,
            role=Role.ADMIN,
            institution_id=institution.id,
            password_hash=hash_password(password),
            must_change_password=True,
        ),
    )
    audit.record(session, None, "account.bootstrap", "user", str(admin.id), institution=institution.id)
    session.commit()
    return institution, CreatedAccount(email, name, Role.ADMIN, password)
