"""관리자 계정 목록·수정(권한 매트릭스 "사용자·학과·대리자 설정")과 감사 로그 필터·페이지(FR-10)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AuditLog, Department, User
from tests.conftest import login


def dept(db: Session, name: str) -> int:
    return db.scalars(select(Department.id).where(Department.name == name)).one()


def user_of(db: Session, email: str) -> User:
    db.expire_all()
    return db.scalars(select(User).where(User.email == email)).one()


def test_account_list_filters_and_hides_student_names(client: TestClient, seeded: Session) -> None:
    login(client, "admin@msu.example")
    page = client.get("/admin/accounts").text
    assert "jiwon@student.example" in page and "Daniel Kim" in page
    assert "이지원" not in page  # 교수·관리자 화면에는 학생 이름을 보여 주지 않는다

    page = client.get("/admin/accounts?q=msu.example&role=professor").text
    assert "dkim@msu.example" in page and "jiwon@student.example" not in page and "rachel@msu.example" not in page

    page = client.get("/admin/accounts?status=inactive").text
    assert "조건에 맞는 계정이 없어요" in page

    login(client, "rachel@msu.example")
    assert client.get("/admin/accounts").status_code == 403


def test_admin_edits_professor_department_and_delegate(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    kim, wong = user_of(seeded, "dkim@msu.example"), user_of(seeded, "ewong@msu.example")
    page = client.get(f"/admin/accounts/{kim.id}").text
    assert f'value="{dept(seeded, "Mathematics")}" selected' in page and "Emily Wong" in page

    def save(**data: object) -> str:
        return client.post(f"/admin/accounts/{kim.id}", data={"csrf_token": token, **data}).text

    math, physics, retired = dept(seeded, "Mathematics"), dept(seeded, "Physics"), dept(seeded, "Retired")
    assert "과목에 있는 학과 이름을 골라 주세요" in save(name="Daniel Kim", department_id=retired)  # 과목 없는 학과
    assert "학과를 골라야" in save(name="Daniel Kim", department_id="")
    assert "다른 교수를 대리 심사자로" in save(name="Daniel Kim", department_id=math, delegate_user_id=kim.id)
    assert user_of(seeded, kim.email).department_name == "Mathematics"  # 실패하면 아무것도 바뀌지 않는다

    page = save(name="Daniel J. Kim", department_id=physics, delegate_user_id=wong.id)
    assert "계정 정보를 저장했어요" in page
    kim = user_of(seeded, kim.email)
    assert (kim.name, kim.department_name, kim.delegate_user_id) == ("Daniel J. Kim", "Physics", wong.id)
    log = seeded.scalars(select(AuditLog).where(AuditLog.action == "account.update")).one()
    assert log.target_id == str(kim.id) and log.payload_json == {"fields": ["name", "department", "delegate"]}
    assert "Daniel" not in str(log.payload_json)  # 감사 로그에는 바뀐 항목 이름만

    assert "바뀐 내용이 없어요" in save(name="Daniel J. Kim", department_id=physics, delegate_user_id=wong.id)
    assert client.post(f"/admin/accounts/{kim.id}", data={"name": "x"}).status_code in (400, 403)  # CSRF
    assert client.get("/admin/accounts/999999").status_code == 404


def test_student_account_page_hides_name_and_returns_after_deactivation(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    jiwon = user_of(seeded, "jiwon@student.example")
    page = client.get(f"/admin/accounts/{jiwon.id}").text
    assert "이지원" not in page and 'name="name"' not in page

    client.post(f"/admin/accounts/{jiwon.id}", data={"name": "다른 이름", "csrf_token": token})
    assert user_of(seeded, jiwon.email).name == "이지원"  # 학생 이름은 여기서 고치지 않는다

    r = client.post(
        "/admin/data/accounts/active",
        data={"email": jiwon.email, "action": "deactivate", "next": f"/admin/accounts/{jiwon.id}", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == f"/admin/accounts/{jiwon.id}"
    r = client.post(
        "/admin/data/accounts/active",
        data={"email": jiwon.email, "action": "reactivate", "next": "https://evil.example", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.headers["location"] == "/admin/data#account-active"  # 다른 곳으로는 돌려보내지 않는다


def test_audit_log_filters_by_action_target_and_date(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    kim = user_of(seeded, "dkim@msu.example")
    client.post(
        f"/admin/accounts/{kim.id}",
        data={"name": "Daniel Kim", "department_id": dept(seeded, "Physics"), "csrf_token": token},
    )

    page = client.get("/admin/audit").text
    assert "계정 정보 수정" in page and "로그인" in page
    page = client.get("/admin/audit?action=account.update").text
    assert f"user #{kim.id}" in page and "auth.login</div>" not in page
    page = client.get(f"/admin/audit?target_type=user&target_id={kim.id}").text
    assert "account.update" in page and "기록 1건 중 1–1" in page
    assert "조건에 맞는 기록이 없어요" in client.get("/admin/audit?since=2999-01-01").text
    assert "account.update" in client.get("/admin/audit?since=2000-01-01&until=2999-12-31&page=1").text
    assert client.get("/admin/audit?since=not-a-date").status_code == 200  # 잘못된 날짜는 무시

    login(client, "rachel@msu.example")
    assert client.get("/admin/audit").status_code == 403
