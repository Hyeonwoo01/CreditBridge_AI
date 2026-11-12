"""Degree Audit: 졸업 요건 설정과 학생 홈 표시 (리뷰 v3 P1-6)."""

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import CreditAllocation, Decision, DegreeProgram, GraduationRequirement
from tests.conftest import login
from tests.integration.test_review_extras import approve
from tests.integration.test_workflow import professor_for


def test_confirmed_credit_fills_requirement_on_student_home(client: TestClient, seeded: Session) -> None:
    login(client, "jiwon@student.example")
    page = client.get("/student").text
    assert "data-degree" in page and "B.S. Computer Science and Engineering" in page  # 데모 프로그램
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    approve(client, ev, token)  # MATH 101 → MATH 1151 직접 인정 (4학점 대상, 3학점 인정)
    login(client, "jiwon@student.example")
    page = client.get("/student").text
    math_row = page.split('data-requirement="major_required"', 1)[1].split("</tr>", 1)[0]
    assert "Math core" in math_row and "MATH 101 → MATH 1151" in math_row
    assert "공식 졸업 판정은 학사 담당자의 확인이 필요해요" in page


def test_no_matching_program_is_undetermined(client: TestClient, seeded: Session) -> None:
    for r in seeded.scalars(select(GraduationRequirement)):
        seeded.delete(r)
    for p in seeded.scalars(select(DegreeProgram)):
        seeded.delete(p)
    seeded.commit()
    login(client, "jiwon@student.example")
    page = client.get("/student").text
    assert "졸업 요건: 미정" in page and "졸업 프로그램이 아직 등록되지 않았어요" in page


def test_admin_manages_programs_and_requirements(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    assert "B.S. Computer Science and Engineering" in client.get("/admin/data").text
    client.post(
        "/admin/data/programs",
        data={"name": "B.S. Physics", "department": "Physics", "catalog_year": "2026", "csrf_token": token},
    )
    program = seeded.scalars(select(DegreeProgram).where(DegreeProgram.name == "B.S. Physics")).one()
    assert program.catalog_year == 2026
    program_id = program.id
    bad = client.post(
        f"/admin/data/programs/{program.id}/requirements",
        data={
            "area": "major_required",
            "name": "Core",
            "credits": "8",
            "course_codes": "PHYSICS 1250, NOPE 1",
            "csrf_token": token,
        },
    )
    assert "카탈로그에 없는 과목 코드" in bad.text and "NOPE 1" in bad.text
    client.post(
        f"/admin/data/programs/{program.id}/requirements",
        data={
            "area": "major_required",
            "name": "Core",
            "credits": "8",
            "course_codes": "PHYSICS 1250",
            "csrf_token": token,
        },
    )
    rq = seeded.scalars(select(GraduationRequirement).where(GraduationRequirement.program_id == program.id)).one()
    assert rq.course_codes == ["PHYSICS 1250"] and float(rq.required_credits) == 8
    client.post(f"/admin/data/requirements/{rq.id}/remove", data={"csrf_token": token})
    client.post(f"/admin/data/programs/{program_id}/remove", data={"csrf_token": token})
    seeded.expire_all()
    assert seeded.get(DegreeProgram, program_id) is None
    evaluator = login(client, "rachel@msu.example")
    assert client.post("/admin/data/programs", data={"name": "x", "csrf_token": evaluator}).status_code == 403


def requirement_named(db: Session, name: str) -> GraduationRequirement:
    return db.scalars(select(GraduationRequirement).where(GraduationRequirement.name == name)).one()


def decide_with_requirement(client: TestClient, ev_id: int, token: str, requirement_id: int | str) -> Response:
    return client.post(
        f"/professor/evaluations/{ev_id}/decision",
        data={"action": "approve", "requirement_id": str(requirement_id), "csrf_token": token},
        follow_redirects=False,
    )


def test_professor_chooses_requirement_area(client: TestClient, seeded: Session) -> None:
    """교수가 판정 때 고른 요건에 확정 학점이 들어간다 (자동이면 과목 목록 기준, 리뷰 v3 P1-6)."""
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "data-requirement-select" in page and "자동 (과목 목록 기준)" in page and "Natural science" in page
    science = requirement_named(seeded, "Natural science")
    assert decide_with_requirement(client, ev.id, token, science.id).status_code == 303

    allocation = seeded.scalars(select(CreditAllocation)).one()
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    assert allocation.requirement_id == science.id
    assert decision.course_snapshot["requirement"] == {
        "id": science.id,
        "program_id": science.program_id,
        "area": "general_education",
        "name": "Natural science",
    }
    assert "졸업 요건: 교양 · Natural science" in client.get(f"/professor/evaluations/{ev.id}").text

    login(client, "jiwon@student.example")
    page = client.get("/student").text
    science_row = page.split('data-requirement="general_education"', 1)[1].split("</tr>", 1)[0]
    math_row = page.split('data-requirement="major_required"', 1)[1].split("</tr>", 1)[0]
    assert "MATH 101 → MATH 1151" in science_row and "MATH 101" not in math_row  # 자동이었다면 Math core


def test_requirement_outside_student_program_is_refused(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    msu = seeded.scalars(select(DegreeProgram)).first()
    assert msu is not None
    other = DegreeProgram(institution_id=msu.institution_id, name="Other", catalog_year=1999)
    seeded.add(other)
    seeded.flush()
    stray = GraduationRequirement(
        program_id=other.id, area="major_elective", name="Stray", required_credits=3, course_codes=[], sort=0
    )
    seeded.add(stray)
    seeded.commit()
    r = decide_with_requirement(client, ev.id, token, stray.id)
    assert r.status_code == 422 and "졸업 프로그램 목록에서 골라 주세요" in r.text
    assert seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).first() is None
    # JSON API도 같은 규칙
    body = client.get(f"/api/v1/evaluations/{ev.id}").json()
    r = client.post(
        "/api/v1/decisions",
        json={
            "evaluation_id": ev.id,
            "action": "approve",
            "requirement_id": stray.id,
            "case_token": body["case_token"],
        },
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 422


def test_deleted_requirement_falls_back_to_automatic(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    science = requirement_named(seeded, "Natural science")
    decide_with_requirement(client, ev.id, token, science.id)
    admin = login(client, "admin@msu.example")
    client.post(f"/admin/data/requirements/{science.id}/remove", data={"csrf_token": admin})
    seeded.expire_all()
    assert seeded.scalars(select(CreditAllocation)).one().requirement_id is None  # 지우면 자동으로
    login(client, "jiwon@student.example")
    page = client.get("/student").text
    math_row = page.split('data-requirement="major_required"', 1)[1].split("</tr>", 1)[0]
    assert "MATH 101 → MATH 1151" in math_row
    # 판정 기록에는 그때 고른 요건이 남는다
    assert "졸업 요건: 교양 · Natural science" in client.get(f"/student/evaluations/{ev.id}").text
