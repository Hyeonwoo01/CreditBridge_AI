"""Degree Audit: 졸업 요건 설정과 학생 홈 표시 (리뷰 v3 P1-6)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import DegreeProgram, GraduationRequirement
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
