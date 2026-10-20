"""관리자 '계정·과목' 화면: 기준 강의계획서 빼기, 잘못 등록한 출신 대학 지우기 (쓰이는 대학은 지우지 않음)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AuditLog, Course, Institution, Syllabus
from tests.conftest import login
from tests.fakes import FakeLLM
from tests.integration.test_pipeline import new_request, upload

HANKUK = "Hankuk University (한국대학교)"


def test_remove_reference_takes_course_out_of_ai_candidates(
    client: TestClient, seeded: Session, fake_llm: FakeLLM
) -> None:
    calc = seeded.scalars(select(Course).where(Course.code == "MATH 1151")).one()
    old_reference = calc.reference_syllabus_id
    assert old_reference is not None

    login(client, "rachel@msu.example")  # 관리자만
    token = login(client, "jiwon@student.example")
    assert client.post(f"/admin/data/courses/{calc.id}/reference/remove", data={"csrf_token": token}).status_code == 403

    token = login(client, "admin@msu.example")
    page = client.get("/admin/data").text
    assert "기준 강의계획서 빼기" in page
    r = client.post(f"/admin/data/courses/{calc.id}/reference/remove", data={"csrf_token": token})
    assert "MATH 1151 기준 강의계획서를 뺐어요" in r.text
    seeded.expire_all()
    assert seeded.get(Course, calc.id).reference_syllabus_id is None  # type: ignore[union-attr]
    assert seeded.get(Syllabus, old_reference) is not None  # 강의계획서 행·파일은 기록으로 남는다
    log = seeded.scalars(select(AuditLog).where(AuditLog.action == "course.reference_remove")).one()
    assert log.target_id == str(calc.id) and log.payload_json == {"syllabus": old_reference}
    r = client.post(f"/admin/data/courses/{calc.id}/reference/remove", data={"csrf_token": token})
    assert "뺄 기준 강의계획서가 없어요" in r.text

    # 기준 강의계획서가 빠진 과목은 학생 강의계획서 분석에서 비교 후보로 들어가지 않는다
    student = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, student)
    upload(client, rid, student, "calculus.txt")
    prompt = fake_llm.prompts("EvaluationOutput")[-1]
    assert '"course_code": "MATH 1151"' not in prompt


def test_delete_source_institution_only_when_unused(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    client.post("/admin/data/institutions", data={"name": "Typo Univ", "country": "KR", "csrf_token": token})
    seeded.expire_all()
    typo = seeded.scalars(select(Institution).where(Institution.name == "Typo Univ")).one()
    hankuk = seeded.scalars(select(Institution).where(Institution.name == HANKUK)).one()
    msu = seeded.scalars(select(Institution).where(Institution.is_target.is_(True))).first()
    assert msu is not None
    typo_id, hankuk_id = typo.id, hankuk.id

    page = client.get("/admin/data").text
    assert f"/admin/data/institutions/{typo.id}/delete" in page
    assert f"/admin/data/institutions/{hankuk.id}/delete" not in page and "사용 중" in page

    # 학생 계정·편입 요청이 가리키는 대학은 지우지 않고 이유를 보여 준다
    r = client.post(f"/admin/data/institutions/{hankuk.id}/delete", data={"csrf_token": token})
    assert "쓰이고 있어 지울 수 없어요" in r.text and "학생 계정" in r.text
    # 대상 대학은 이 경로로 지울 수 없다
    r = client.post(f"/admin/data/institutions/{msu.id}/delete", data={"csrf_token": token})
    assert "출신 대학을 찾을 수 없어요" in r.text

    r = client.post(f"/admin/data/institutions/{typo.id}/delete", data={"csrf_token": token})
    assert "출신 대학 Typo Univ을(를) 지웠어요" in r.text
    seeded.expire_all()
    assert seeded.get(Institution, typo_id) is None and seeded.get(Institution, hankuk_id) is not None
    log = seeded.scalars(select(AuditLog).where(AuditLog.action == "institution.delete")).one()
    assert log.target_id == str(typo_id) and log.payload_json == {"name": "Typo Univ"}
