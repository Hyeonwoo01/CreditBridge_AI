"""관리자 '계정·과목' 화면: 기준 강의계획서 빼기, 대학별 출신 대학 목록과 지우기 (쓰이는 대학은 지우지 않음)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.errors import CreditBridgeError, NotFoundError
from backend.models import AuditLog, Course, Institution, Syllabus, User
from backend.services import institution_data
from backend.services.institution_data import bootstrap_admin
from tests.conftest import login
from tests.fakes import FakeLLM
from tests.integration.test_pipeline import new_request, upload

HANKUK = "Hankuk University (한국대학교)"
HEADER = "email,name,role,department,source_institution\n"


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


def test_each_institution_sees_only_its_own_source_list(client: TestClient, seeded: Session) -> None:
    bootstrap_admin(seeded, "Other State University", "US", "admin@osu.edu", "OSU 관리자")
    osu = seeded.scalars(select(User).where(User.email == "admin@osu.edu")).one()
    msu_admin = seeded.scalars(select(User).where(User.email == "admin@msu.example")).one()

    # 다른 대학(MSU)이 쓰는 출신 대학은 OSU 목록에 없다
    assert institution_data.overview(seeded, osu).source_institutions == []
    institution_data.add_source_institution(seeded, msu_admin, "Typo Univ", "KR")
    assert [i.name for i in institution_data.overview(seeded, osu).source_institutions] == []
    r = institution_data.import_accounts(
        seeded, osu, "a.csv", (HEADER + "s@osu.edu,학생,student,,Typo Univ\n").encode(), by_email=False
    )
    assert r.errors and "등록되지 않은 출신 대학(Typo Univ)" in r.errors[0]

    # 같은 이름을 OSU가 등록하면 행 하나를 함께 쓰고, OSU 목록에만 더해진다
    institution_data.add_source_institution(seeded, osu, HANKUK, "KR")
    assert len(seeded.scalars(select(Institution).where(Institution.name == HANKUK)).all()) == 1
    assert [i.name for i in institution_data.overview(seeded, osu).source_institutions] == [HANKUK]
    with pytest.raises(CreditBridgeError, match="이미 등록된"):
        institution_data.add_source_institution(seeded, osu, HANKUK, "KR")

    # OSU는 아직 쓰지 않으니 자기 목록에서 지울 수 있고, MSU가 쓰는 행은 그대로 남는다
    hankuk = seeded.scalars(select(Institution).where(Institution.name == HANKUK)).one()
    institution_data.delete_source_institution(seeded, osu, hankuk.id)
    assert institution_data.overview(seeded, osu).source_institutions == []
    assert seeded.get(Institution, hankuk.id) is not None
    assert HANKUK in [i.name for i in institution_data.overview(seeded, msu_admin).source_institutions]
    # 목록에 없는 대학은 지울 수 없다
    with pytest.raises(NotFoundError):
        institution_data.delete_source_institution(seeded, osu, hankuk.id)
