"""데모 데이터: 대상 대학(MSU) 카탈로그, 출신 대학, 데모 계정, 작년 선형대수 판정 이력.

실행: uv run python -m scripts.seed_demo   (DB 마이그레이션 후, 임베딩 모델 bge-m3 필요)
비밀번호는 모두 demo1234 — 로컬 데모 전용이다.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embedding import Embedder, get_embedder
from app.ai.evidence import locate
from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models import Course, CourseEvaluation, Decision, Institution, Syllabus, SyllabusChunk, TransferRequest, User
from app.services.auth import hash_password
from scripts.catalog_data import MSU_COURSES, reference_syllabus_text

DEMO_PASSWORD = "demo1234"


def _user(
    session: Session, email: str, name: str, role: str, institution: Institution | None, department: str | None = None
) -> User:
    user = session.scalars(select(User).where(User.email == email)).first()
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            name=name,
            role=role,
            institution_id=institution.id if institution else None,
            department=department,
        )
        session.add(user)
        session.flush()
    return user


def seed(session: Session, embedder: Embedder) -> None:
    if session.scalars(select(Institution).where(Institution.name == "Midwest State University")).first():
        print("already seeded")
        return
    msu = Institution(
        name="Midwest State University", country="US", is_target=True, tuition_per_credit=1350, degree_credits=120
    )
    hankuk = Institution(name="Hankuk University (한국대학교)", country="KR", is_target=False)
    session.add_all([msu, hankuk])
    session.flush()

    for c in MSU_COURSES:
        text = reference_syllabus_text(c)
        ref = Syllabus(
            institution_id=msu.id,
            raw_text=text,
            course_code=c.code,
            course_title=c.title,
            credits=c.credits,
            status="ready",
            original_filename=f"{c.code}.txt",
        )
        session.add(ref)
        session.flush()
        sentences = [sentence for _, sentence in c.concepts]
        vectors = embedder.embed([f"{name}: {sentence}" for name, sentence in c.concepts])
        for (name, sentence), vec, week in zip(c.concepts, vectors, range(1, len(sentences) + 1), strict=True):
            span = locate(text, sentence)
            session.add(
                SyllabusChunk(
                    syllabus_id=ref.id,
                    week_no=week,
                    concept=name,
                    text=sentence,
                    char_start=span.start if span else None,
                    char_end=span.end if span else None,
                    embedding=vec,
                )
            )
        session.add(
            Course(
                institution_id=msu.id,
                code=c.code,
                title=c.title,
                credits=c.credits,
                department=c.department,
                level=c.level,
                reference_syllabus_id=ref.id,
            )
        )
    session.flush()

    _user(session, "jiwon@student.example", "이지원", "student", None)
    _user(session, "rachel@msu.example", "Rachel Morgan", "evaluator", msu)
    _user(session, "admin@msu.example", "MSU Admin", "admin", msu)
    professors = {
        "Mathematics": [("dkim@msu.example", "Daniel Kim"), ("lchen@msu.example", "Laura Chen")],
        "Computer Science and Engineering": [("oali@msu.example", "Omar Ali"), ("spark@msu.example", "Sarah Park")],
        "Physics": [("mbrown@msu.example", "Mike Brown")],
        "Chemistry": [("alopez@msu.example", "Ana Lopez")],
        "English": [("jreed@msu.example", "Jane Reed")],
        "History": [("twhite@msu.example", "Tom White")],
    }
    created = {
        dept: [_user(session, e, n, "professor", msu, dept) for e, n in people] for dept, people in professors.items()
    }

    # 작년에 다른 학생의 같은 선형대수 과목이 직접 인정된 이력 (일관성 경보 시나리오, TS-05)
    senior = _user(session, "senior@student.example", "선배 학생", "student", None)
    retired = _user(session, "retired@msu.example", "Prof. Emeritus Hall", "professor", msu, "Retired")
    last_year = utcnow() - timedelta(days=365)
    past_request = TransferRequest(
        student_id=senior.id,
        source_institution_id=hankuk.id,
        target_institution_id=msu.id,
        status="decided",
        submitted_at=last_year,
    )
    session.add(past_request)
    session.flush()
    past_syllabus = Syllabus(
        institution_id=hankuk.id,
        transfer_request_id=past_request.id,
        owner_id=senior.id,
        raw_text="(archived)",
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
        probability=88,
        confidence="high",
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
            reason="",
            ai_recommendation_snapshot={"recommendation": "direct"},
            decided_at=last_year,
        )
    )
    session.commit()
    professor_count = sum(len(v) for v in created.values())
    print(f"seeded {len(MSU_COURSES)} courses, {professor_count} professors; password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    with SessionLocal() as s:
        seed(s, get_embedder())
