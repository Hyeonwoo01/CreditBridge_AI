"""학생의 출신 대학·편입 전공은 관리자가 계정에 정한다 (계정 CSV·계정 수정), 관리자 '계정 목록' 배지."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AuditLog, Institution, User
from tests.conftest import login
from tests.integration.test_institution_data import post_csv

HANKUK = "Hankuk University (한국대학교)"
HEADER = "email,name,role,department,source_institution\n"


def test_account_csv_sets_student_source_and_major(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    bad = (
        HEADER
        + "a@student.example,학생A,student,Astrology,\n"  # 과목에 없는 전공
        + "b@student.example,학생B,student,Mathematics,No Such Univ\n"  # 등록 안 된 출신 대학
        + "c@msu.example,교수C,professor,Mathematics,Hankuk University (한국대학교)\n"  # 교직원은 출신 대학 없음
    )
    r = post_csv(client, "/admin/data/accounts", token, bad)
    assert r.status_code == 422
    assert "편입 전공(Astrology)" in r.text and "출신 대학(No Such Univ)" in r.text and "학생 계정에만" in r.text

    good = (
        HEADER + f"new@student.example,새학생,student,Mathematics,{HANKUK}\nlater@student.example,나중학생,student,,\n"
    )
    r = post_csv(client, "/admin/data/accounts", token, good)
    assert "새 계정 2개를 만들었어요" in r.text
    seeded.expire_all()
    new = seeded.scalars(select(User).where(User.email == "new@student.example")).one()
    assert new.department_name == "Mathematics" and new.source_institution is not None
    assert new.source_institution.name == HANKUK


def test_admin_edits_student_info_and_sees_attention_badge(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    post_csv(client, "/admin/data/accounts", token, HEADER + "later@student.example,나중학생,student,,\n")
    seeded.expire_all()
    student = seeded.scalars(select(User).where(User.email == "later@student.example")).one()

    # 출신 대학·편입 전공이 빈 학생은 '계정 목록' 배지와 '확인 필요' 칩에 나온다
    page = client.get("/admin/accounts").text
    assert "확인이 필요한 계정 1개" in page
    attention = client.get("/admin/accounts", params={"status": "attention"}).text
    assert "later@student.example" in attention and "편입 정보 없음" in attention
    assert "jiwon@student.example" not in attention  # 이미 정해진 학생은 아님

    form = client.get(f"/admin/accounts/{student.id}").text
    assert "편입 정보" in form and "나중학생" not in form  # 학생 이름은 보이지 않는다
    hankuk = seeded.scalars(select(Institution).where(Institution.name == HANKUK)).one()
    msu = seeded.scalars(select(Institution).where(Institution.is_target.is_(True))).one()
    r = client.post(
        f"/admin/accounts/{student.id}",
        data={"source_institution_id": msu.id, "department_id": "", "csrf_token": token},
    )
    assert "등록된 출신 대학을 골라 주세요" in r.text  # 대상 대학은 출신 대학이 될 수 없다

    dept = seeded.scalars(select(User).where(User.email == "jiwon@student.example")).one().department_id
    r = client.post(
        f"/admin/accounts/{student.id}",
        data={"source_institution_id": hankuk.id, "department_id": dept, "csrf_token": token},
    )
    assert "계정 정보를 저장했어요" in r.text
    seeded.expire_all()
    student = seeded.get(User, student.id)
    assert student is not None and student.source_institution_id == hankuk.id and student.department_id == dept
    log = seeded.scalars(select(AuditLog).where(AuditLog.action == "account.update")).all()[-1]
    assert log.payload_json == {"fields": ["major", "source_institution"]}
    assert "확인이 필요한 계정" not in client.get("/admin/accounts").text
