"""데모 데이터: 대상 대학(MSU) 카탈로그와 기준 강의계획서, 출신 대학, 데모 계정, 작년 선형대수 판정 이력.

실행: uv run python -m scripts.seed_demo   (DB 마이그레이션 후)
비밀번호는 모두 demo1234 — 로컬 데모 전용이다.
"""

from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.ai.evidence import locate
from backend.db.base import utcnow
from backend.db.session import SessionLocal
from backend.models import (
    Course,
    CourseEvaluation,
    CreditConversionRule,
    Decision,
    Institution,
    InstitutionSource,
    PolicyRule,
    Syllabus,
    SyllabusChunk,
    TransferRequest,
    User,
)
from backend.models.enums import Authenticity, ConversionMethod, CreditSystem, PolicyRuleType, PolicyStatus, SourceKind
from backend.services.analysis import content_hash
from backend.services.auth import hash_password
from backend.services.institution_data import department_named
from scripts.catalog_data import MSU_COURSES, reference_syllabus_text

DEMO_PASSWORD = "demo1234"
DEMO_DATA = Path(__file__).parent / "demo_data"


def _user(
    session: Session,
    email: str,
    name: str,
    role: str,
    institution: Institution | None,
    department: str | None = None,
    source: Institution | None = None,
) -> User:
    user = session.scalars(select(User).where(User.email == email)).first()
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            name=name,
            role=role,
            institution_id=institution.id if institution else None,
            department_id=department_named(session, institution.id, department).id
            if institution and department
            else None,
            source_institution_id=source.id if source else None,
        )
        session.add(user)
        session.flush()
    return user


def seed(session: Session) -> None:
    if session.scalars(select(Institution).where(Institution.name == "Midwest State University")).first():
        print("already seeded")
        return
    msu = Institution(
        name="Midwest State University",
        country="US",
        is_target=True,
        tuition_per_credit=1350,
        degree_credits=120,
        credit_system=CreditSystem.US_SEMESTER,
    )
    hankuk = Institution(
        name="Hankuk University (한국대학교)", country="KR", is_target=False, credit_system=CreditSystem.KR_CREDIT
    )
    session.add_all([msu, hankuk])
    session.flush()
    session.add(InstitutionSource(institution_id=msu.id, source_institution_id=hankuk.id))

    for c in MSU_COURSES:
        text = reference_syllabus_text(c)
        ref = Syllabus(
            institution_id=msu.id,
            raw_text=text,
            content_hash=content_hash(text.encode()),
            course_code=c.code,
            course_title=c.title,
            credits=c.credits,
            status="ready",
            original_filename=f"{c.code}.txt",
            source_kind=SourceKind.INSTITUTION_REFERENCE,
            authenticity=Authenticity.VERIFIED,
            verification_method="대상 대학 기준 강의계획서",
        )
        session.add(ref)
        session.flush()
        for week, (name, sentence) in enumerate(c.concepts, start=1):
            span = locate(text, sentence)
            session.add(
                SyllabusChunk(
                    syllabus_id=ref.id,
                    week_no=week,
                    concept=name,
                    text=sentence,
                    char_start=span.start if span else None,
                    char_end=span.end if span else None,
                )
            )
        session.add(
            Course(
                institution_id=msu.id,
                code=c.code,
                title=c.title,
                credits=c.credits,
                department_id=department_named(session, msu.id, c.department).id,
                level=c.level,
                reference_syllabus_id=ref.id,
            )
        )
    session.flush()

    # MVP의 학생은 입학이 확정되어 대상 대학에 소속된 학생이다. 출신 대학·편입 전공은 학교가 계정에 정해 둔다
    cse = "Computer Science and Engineering"
    _user(session, "jiwon@student.example", "이지원", "student", msu, cse, hankuk)
    _user(session, "rachel@msu.example", "Rachel Morgan", "evaluator", msu)
    admin = _user(session, "admin@msu.example", "MSU Admin", "admin", msu)
    # 예시 환산 규칙: 한국 1학점 = 미국 학기제 1학점 (실제 운영에서는 대학이 승인한 규칙을 관리자가 넣는다)
    session.add(
        CreditConversionRule(
            target_institution_id=msu.id,
            source_system=CreditSystem.KR_CREDIT,
            target_system=CreditSystem.US_SEMESTER,
            factor=1.0,
            method=ConversionMethod.APPROVED_TABLE,
            effective_from=date(2020, 1, 1),
            approved_by=admin.id,
            note="데모용 예시 규칙",
        )
    )
    # 예시 학칙 정책 (승인됨): C 이상·P/PASS/S 인정, 편입 학점 상한 60, 졸업 120, 학기당 15
    for rule_type, params in (
        (PolicyRuleType.MIN_GRADE, {"min_grade": "C", "accept_pass": True}),
        (PolicyRuleType.TRANSFER_CAP, {"credits": 60}),
        (PolicyRuleType.DEGREE_CREDITS, {"credits": 120}),
        (PolicyRuleType.SEMESTER_LOAD, {"credits": 15}),
        (PolicyRuleType.APPEAL_WINDOW, {"days": 30}),
        (PolicyRuleType.APPEAL_REVIEW, {"days": 14}),
    ):
        session.add(
            PolicyRule(
                institution_id=msu.id,
                rule_type=rule_type,
                parameters=params,
                effective_from=date(2020, 1, 1),
                status=PolicyStatus.APPROVED,
                source="데모용 예시 학칙",
                created_by=admin.id,
                approved_by=admin.id,
                approved_at=utcnow(),
            )
        )
    professors = {
        "Mathematics": [("dkim@msu.example", "Daniel Kim"), ("lchen@msu.example", "Laura Chen")],
        "Computer Science and Engineering": [("oali@msu.example", "Omar Ali"), ("spark@msu.example", "Sarah Park")],
        "Physics": [("mbrown@msu.example", "Mike Brown"), ("ewong@msu.example", "Emily Wong")],
        "Chemistry": [("alopez@msu.example", "Ana Lopez")],
        "English": [("jreed@msu.example", "Jane Reed")],
        "History": [("twhite@msu.example", "Tom White")],
    }
    created = {
        dept: [_user(session, e, n, "professor", msu, dept) for e, n in people] for dept, people in professors.items()
    }

    # 작년에 다른 학생의 같은 선형대수 강의계획서가 직접 인정된 이력 (일관성 경보 시나리오, TS-05)
    senior = _user(session, "senior@student.example", "선배 학생", "student", msu, cse, hankuk)
    retired = _user(session, "retired@msu.example", "Prof. Emeritus Hall", "professor", msu, "Retired")
    last_year = utcnow() - timedelta(days=365)
    past_request = TransferRequest(
        student_id=senior.id,
        source_institution_id=hankuk.id,
        target_institution_id=msu.id,
        major="Computer Science and Engineering",
        status="decided",
        submitted_at=last_year,
    )
    session.add(past_request)
    session.flush()
    past_text = (DEMO_DATA / "linear_algebra_detailed.txt").read_text(encoding="utf-8")
    past_syllabus = Syllabus(
        institution_id=hankuk.id,
        transfer_request_id=past_request.id,
        owner_id=senior.id,
        raw_text=past_text,
        content_hash=content_hash(b"archived:", past_text.encode()),
        course_code="MATH 201",
        course_title="Linear Algebra",
        credits=3,
        status="ready",
        original_filename="MATH201.pdf",
        created_at=last_year,
    )
    session.add(past_syllabus)
    session.flush()
    linalg = session.scalars(select(Course).where(Course.code == "MATH 2568")).one()
    past_eval = CourseEvaluation(
        transfer_request_id=past_request.id,
        syllabus_id=past_syllabus.id,
        candidate_course_id=linalg.id,
        status="done",
        recommendation="direct",
        confidence="high",
        coverage=0.9,
        created_at=last_year,
    )
    session.add(past_eval)
    session.flush()
    session.add(
        Decision(
            course_evaluation_id=past_eval.id,
            decided_by=retired.id,
            action="approve",
            result="direct",
            target_course_id=linalg.id,
            reason_codes=[],
            ai_recommendation_snapshot={"recommendation": "direct"},
            decided_at=last_year,
        )
    )
    session.commit()
    professor_count = sum(len(v) for v in created.values())
    print(f"seeded {len(MSU_COURSES)} courses, {professor_count} professors; password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    with SessionLocal() as s:
        seed(s)
