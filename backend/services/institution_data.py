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
from backend.documents import text as doc_text
from backend.documents.storage import ObjectStorage
from backend.errors import CreditBridgeError, LLMError, NotFoundError, PermissionDeniedError
from backend.models import Course, Institution, Syllabus, User
from backend.models.enums import Role, SyllabusStatus
from backend.repositories import catalog as catalog_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.services import analysis, audit, csv_import
from backend.services.auth import RESET_AFTER, hash_password, temporary_password

logger = logging.getLogger(__name__)

ACCOUNT_COLUMNS = ["email", "name", "role", "department"]
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
    temporary_password: str


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
    courses: list[CourseRow]
    departments_without_professor: list[str]
    source_institutions: list[Institution]

    @property
    def missing_reference(self) -> int:
        return sum(1 for r in self.courses if r.course.reference_syllabus_id is None)


def ensure_admin(user: User) -> int:
    if user.role != Role.ADMIN or user.institution_id is None:
        raise PermissionDeniedError("기관 관리자만 사용할 수 있어요.")
    return user.institution_id


def overview(session: Session, admin: User) -> Overview:
    institution_id = ensure_admin(admin)
    institution = catalog_repo.get_institution(session, institution_id)
    if institution is None:
        raise NotFoundError("기관을 찾을 수 없어요.")
    courses = catalog_repo.courses_of(session, institution_id)
    uploads = syllabus_repo.latest_reference_uploads(session, institution_id)
    staffed = user_repo.professor_departments(session, institution_id)
    departments = sorted({c.department for c in courses})
    return Overview(
        institution=institution,
        role_counts=user_repo.role_counts(session, institution_id),
        pending_password=user_repo.pending_password_change(session, institution_id),
        locked_out=user_repo.locked_out_count(session, institution_id, RESET_AFTER),
        courses=[CourseRow(c, uploads.get(c.code)) for c in courses],
        departments_without_professor=[d for d in departments if d not in staffed],
        source_institutions=catalog_repo.source_institutions(session),
    )


# ---------- 계정 ----------


def import_accounts(session: Session, admin: User, filename: str, data: bytes) -> AccountImport:
    institution_id = ensure_admin(admin)
    departments = set(catalog_repo.departments_of(session, institution_id))
    result = AccountImport()
    pending: list[tuple[str, str, Role, str | None]] = []
    seen: set[str] = set()
    for line_no, row in csv_import.read_rows(filename, data, ACCOUNT_COLUMNS, ACCOUNT_COLUMNS[:3], MAX_ACCOUNT_ROWS):
        problems = []
        email = row.get("email", "").lower()
        name = row.get("name", "")
        role = ROLES.get(row.get("role", "").lower()) or ROLES.get(row.get("role", ""))
        department = row.get("department", "") or None
        if not _EMAIL.match(email) or len(email) > 255:
            problems.append("이메일 형식이 아님")
        elif email in seen:
            problems.append("파일 안에서 이메일이 중복됨")
        if not name:
            problems.append("이름 없음")
        elif len(name) > 100:
            problems.append("이름은 100자까지")
        if role is None:
            problems.append("역할은 student·evaluator·professor·admin(또는 학생·심사관·교수·관리자) 중 하나")
        if department and len(department) > 50:
            problems.append("학과는 50자까지")
        if role == Role.PROFESSOR:
            if not department:
                problems.append("교수는 학과가 필요(과목 배정 기준)")
            elif departments and department not in departments:
                problems.append(f"과목 목록에 없는 학과({department}). 과목 CSV의 학과명과 똑같이 써 주세요")
        if not problems:
            existing = user_repo.get_by_email(session, email)
            if existing is not None and existing.institution_id != institution_id:
                problems.append("다른 기관에 이미 있는 이메일")
            elif existing is not None:
                result.skipped.append(email)
                seen.add(email)
                continue
        seen.add(email)
        if problems or role is None:
            result.errors.append(f"{line_no}행: {', '.join(problems)}")
            continue
        pending.append((email, name, role, department))
    if result.errors:
        return result
    if not pending and not result.skipped:
        raise CreditBridgeError("가져올 행이 없어요.")
    for email, name, role, department in pending:
        password = temporary_password()
        user_repo.add(
            session,
            User(
                email=email,
                name=name,
                role=role,
                institution_id=institution_id,
                department=department,
                password_hash=hash_password(password),
                must_change_password=True,
            ),
        )
        result.created.append(CreatedAccount(email, name, role, password))
    audit.record(
        session,
        admin,
        "account.import",
        "institution",
        str(institution_id),
        created=len(result.created),
        skipped=len(result.skipped),
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
            problems.append("과목 코드 없음")
        elif len(code) > 30:
            problems.append("과목 코드는 30자까지")
        elif code in seen:
            problems.append("파일 안에서 과목 코드가 중복됨")
        if not title:
            problems.append("과목명 없음")
        elif len(title) > 200:
            problems.append("과목명은 200자까지")
        credits = 0.0
        try:
            credits = float(row.get("credits", ""))
        except ValueError:
            problems.append("학점은 숫자")
        else:
            if not 0 < credits <= 30:
                problems.append("학점은 0보다 크고 30 이하")
        if not department:
            problems.append("학과 없음")
        elif len(department) > 50:
            problems.append("학과는 50자까지")
        concepts = _concepts(row.get("concepts", ""))
        if not concepts:
            problems.append("필수 개념을 ;로 구분해 1개 이상")
        elif any(len(c) > 200 for c in concepts):
            problems.append("필수 개념 하나는 200자까지")
        seen.add(code)
        if problems:
            result.errors.append(f"{line_no}행: {', '.join(problems)}")
            continue
        parsed.append((code, title, credits, department, row.get("level", ""), concepts))
    if result.errors:
        return result
    if not parsed:
        raise CreditBridgeError("가져올 행이 없어요.")
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
                    department=department,
                    level=level,
                    concepts=concepts,
                ),
            )
            result.created += 1
        else:
            course.title, course.credits, course.department, course.concepts = title, credits, department, concepts
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
    ensure_admin(admin)
    name, country = name.strip(), country.strip().upper()
    if not name or len(name) > 200:
        raise CreditBridgeError("대학 이름을 200자 이내로 적어 주세요.")
    if not re.fullmatch(r"[A-Z]{2}", country):
        raise CreditBridgeError("국가는 두 글자 코드로 적어 주세요 (예: KR, US).")
    if catalog_repo.source_institution_by_name(session, name) is not None:
        raise CreditBridgeError("이미 등록된 출신 대학이에요.")
    institution = catalog_repo.add_institution(session, Institution(name=name, country=country, is_target=False))
    audit.record(session, admin, "institution.create", "institution", str(institution.id))
    session.commit()
    return institution


# ---------- 기준 강의계획서 ----------


def upload_reference(
    session: Session, storage: ObjectStorage, admin: User, course_id: int, filename: str, data: bytes
) -> tuple[Syllabus, Course]:
    """파일을 저장하고 강의계획서 행을 만든다. 텍스트 읽기 작업 등록은 호출자가 한다."""
    institution_id = ensure_admin(admin)
    course = catalog_repo.get_course(session, course_id)
    if course is None or course.institution_id != institution_id:
        raise NotFoundError("과목을 찾을 수 없어요.")
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


def process_reference(
    session: Session, syllabus_id: int, course_id: int, *, llm: LLMClient, storage: ObjectStorage
) -> None:
    """기준 강의계획서 텍스트를 읽어(스캔 페이지는 Claude 전사) 과목에 연결한다. 실패하면 이전 것을 그대로 쓴다."""
    syllabus = syllabus_repo.get(session, syllabus_id)
    course = catalog_repo.get_course(session, course_id)
    if syllabus is None or course is None or syllabus.source_file_key is None:
        return
    syllabus.status = SyllabusStatus.PROCESSING
    session.commit()
    try:
        text, quality = analysis.document_to_text(
            llm, storage.get(syllabus.source_file_key), syllabus.original_filename
        )
    except (CreditBridgeError, LLMError) as exc:
        logger.warning("reference syllabus failed", extra={"syllabus_id": syllabus_id, "error": type(exc).__name__})
        text, quality = "", 0.0
    if not text.strip():
        syllabus.status = SyllabusStatus.FAILED
        syllabus.error_message = "문서에서 글자를 읽지 못했어요. 텍스트가 있는 PDF나 더 선명한 스캔본을 올려 주세요."
        session.commit()
        return
    syllabus.raw_text = text
    syllabus.quality_score = quality
    syllabus.injection_flags = [f"{f.line_no}행: {f.text}" for f in detect(text)]
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
        raise CreditBridgeError("대학 이름을 200자 이내로 적어 주세요.")
    if not re.fullmatch(r"[A-Z]{2}", country):
        raise CreditBridgeError("국가는 두 글자 코드로 적어 주세요 (예: KR, US).")
    if not _EMAIL.match(email):
        raise CreditBridgeError("이메일 형식이 아니에요.")
    if not name or len(name) > 100:
        raise CreditBridgeError("이름을 100자 이내로 적어 주세요.")
    if user_repo.get_by_email(session, email) is not None:
        raise CreditBridgeError("이미 있는 이메일이에요.")
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
