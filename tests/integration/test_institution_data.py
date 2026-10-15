"""기관 데이터 준비: 계정·과목 CSV 가져오기, 첫 로그인 비밀번호 변경, 기준 강의계획서, 출신 대학."""

import re
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.errors import CreditBridgeError, LLMError
from backend.models import AuditLog, Course, Institution, Syllabus, User
from scripts.make_demo_pdfs import text_to_pdf
from tests.conftest import csrf_of, login
from tests.fakes import FakeLLM
from tests.integration.test_pipeline import new_request, upload


def post_csv(client: TestClient, path: str, token: str, body: str, encoding: str = "utf-8") -> Any:
    return client.post(
        path,
        files={"file": ("data.csv", body.encode(encoding), "text/csv")},
        data={"csrf_token": token},
        follow_redirects=False,
    )


def users(db: Session) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(User)) or 0


# ---------- 계정 ----------


def test_account_import_gives_one_time_passwords_and_forces_change(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    body = (
        "email,name,role,department\n"
        "New.Prof@msu.example,새교수,교수,Mathematics\n"
        "intake@msu.example,Intake Officer,evaluator,\n"
        "rachel@msu.example,Rachel Morgan,evaluator,\n"  # 이미 있는 계정은 건너뛴다
    )
    r = post_csv(client, "/admin/data/accounts", token, body, encoding="cp949")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert "새 계정 2개를 만들었어요" in r.text and "이미 있는 계정 1개는 건너뛰었어요" in r.text
    assert "임시 비밀번호 CSV 받기" in r.text and "data:text/csv" in r.text
    m = re.search(r"new\.prof@msu\.example</td>.*?font-mono\">([^<]+)</td>", r.text, re.S)
    assert m
    temp = m.group(1)

    seeded.expire_all()
    prof = seeded.scalars(select(User).where(User.email == "new.prof@msu.example")).one()
    assert prof.role == "professor" and prof.department == "Mathematics" and prof.must_change_password
    assert temp not in prof.password_hash  # 해시만 저장
    log = seeded.scalars(select(AuditLog).where(AuditLog.action == "account.import")).one()
    assert log.payload_json == {"created": 2, "skipped": 1, "by_email": False}  # 이름·이메일은 넣지 않는다
    # 다시 열면 임시 비밀번호는 보이지 않는다
    assert temp not in client.get("/admin/data").text

    # 임시 비밀번호로 로그인하면 비밀번호 변경 화면으로만 갈 수 있다
    client.cookies.clear()
    r = client.post(
        "/login",
        data={"email": "new.prof@msu.example", "password": temp, "csrf_token": csrf_of(client)},
        follow_redirects=False,
    )
    assert r.headers["location"] == "/account/password"
    assert client.get("/professor", follow_redirects=False).headers["location"] == "/account/password"
    hx = client.get("/notifications/count", headers={"HX-Request": "true"})
    assert hx.status_code == 204 and hx.headers["HX-Redirect"] == "/account/password"
    page = client.get("/account/password")
    assert "임시 비밀번호" in page.text and 'hx-get="/notifications/count"' not in page.text
    token = csrf_of(client, "/account/password")

    def change(current: str, new: str, confirm: str | None = None) -> Any:
        return client.post(
            "/account/password",
            data={"current": current, "new": new, "confirm": confirm or new, "csrf_token": token},
            follow_redirects=False,
        )

    assert "현재 비밀번호가 맞지 않아요" in change("wrong", "a-new-password").text
    assert "10자 이상" in change(temp, "short").text
    assert "일치하지 않아요" in change(temp, "a-new-password", "different-one").text
    r = change(temp, "a-new-password")
    assert r.status_code == 303 and r.headers["location"] == "/professor"
    assert client.get("/professor").status_code == 200
    seeded.expire_all()
    assert not seeded.get(User, prof.id).must_change_password  # type: ignore[union-attr]
    login(client, "new.prof@msu.example", "a-new-password")


def test_account_import_rejects_bad_rows_without_saving(client: TestClient, seeded: Session) -> None:
    other = Institution(name="Other State University", country="US", is_target=True)
    seeded.add(other)
    seeded.flush()
    seeded.add(User(email="taken@other.example", name="x", role="student", institution_id=other.id, password_hash="x"))
    seeded.commit()
    before = users(seeded)
    token = login(client, "admin@msu.example")
    body = (
        "email,name,role,department\n"
        "ok@msu.example,Fine,student,\n"
        "not-an-email,Bad,student,\n"
        "role@msu.example,Bad,dean,\n"
        "nodept@msu.example,Bad,professor,\n"
        "astro@msu.example,Bad,professor,Astrology\n"
        "ok@msu.example,Again,student,\n"
        "taken@other.example,Other,student,\n"
    )
    r = post_csv(client, "/admin/data/accounts", token, body)
    assert r.status_code == 422 and "아무것도 저장하지 않았어요" in r.text
    for text in (
        "3행: 이메일 형식이 아님",
        "4행: 역할은",
        "5행: 교수는 학과가 필요",
        "과목 목록에 없는 학과(Astrology)",
    ):
        assert text in r.text
    assert "7행: 파일 안에서 이메일이 중복됨" in r.text and "8행: 다른 기관에 이미 있는 이메일" in r.text
    assert users(seeded) == before
    r = post_csv(client, "/admin/data/accounts", token, "name,role\nx,student\n")
    assert r.status_code == 303 and "필수 열이 없어요" in client.get("/admin/data").text


def test_only_admin_manages_institution_data(client: TestClient, seeded: Session) -> None:
    login(client, "rachel@msu.example")
    assert client.get("/admin/data").status_code == 403
    token = login(client, "jiwon@student.example")
    assert post_csv(client, "/admin/data/accounts", token, "email,name,role\na@b.co,x,admin\n").status_code == 403


# ---------- 과목·기준 강의계획서 ----------


def test_course_import_and_reference_upload_feed_ai_comparison(
    client: TestClient, seeded: Session, fake_llm: FakeLLM
) -> None:
    token = login(client, "admin@msu.example")
    bad = "code,title,credits,department,level,concepts\nMATH 1,Bad,abc,Mathematics,,\n"
    r = post_csv(client, "/admin/data/courses", token, bad)
    assert r.status_code == 422 and "학점은 숫자" in r.text and "필수 개념을 ;로 구분해 1개 이상" in r.text

    body = (
        "code,title,credits,department,level,concepts\n"
        "MATH 2255,Differential Equations,3,Mathematics,Second-year ODE,First-order equations;Laplace transform\n"
        "MATH 1151,Calculus I (2027),4,Mathematics,,Limits;Derivatives;Integrals\n"
    )
    r = post_csv(client, "/admin/data/courses", token, body)
    assert r.status_code == 303
    page = client.get("/admin/data").text
    assert "과목 1건을 새로 만들고 1건을 고쳤어요" in page and "교수 계정이 없는 학과" not in page
    seeded.expire_all()
    calc = seeded.scalars(select(Course).where(Course.code == "MATH 1151")).one()
    assert calc.title == "Calculus I (2027)" and calc.concepts == ["Limits", "Derivatives", "Integrals"]
    assert calc.level  # level 칸을 비우면 기존 값을 그대로 둔다
    ode = seeded.scalars(select(Course).where(Course.code == "MATH 2255")).one()
    assert ode.reference_syllabus_id is None

    # 기준 강의계획서를 올리면 글자를 읽어 과목에 연결한다 (작업은 테스트에서 즉시 실행)
    reference = "MATH 2255 Differential Equations\nWeek 1: First-order equations\nWeek 2: Laplace transform\n"
    r = client.post(
        f"/admin/data/courses/{ode.id}/reference",
        files={"file": ("ode.pdf", text_to_pdf(reference), "application/pdf")},
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    seeded.expire_all()
    ode = seeded.get(Course, ode.id)  # type: ignore[assignment]
    assert ode.reference_syllabus_id is not None
    ref = seeded.get(Syllabus, ode.reference_syllabus_id)
    assert ref is not None and "Laplace transform" in ref.raw_text and ref.transfer_request_id is None
    assert "등록됨" in client.get("/admin/data").text
    r = client.post(
        f"/admin/data/courses/{ode.id}/reference",
        files={"file": ("notes.docx", b"x", "application/octet-stream")},
        data={"csrf_token": token},
    )
    assert "지원하지 않는 형식" in r.text
    # 스캔본 전사가 실패하면 실패로 표시하고 이전 기준 강의계획서를 그대로 쓴다
    fake_llm.fail_with = LLMError("unavailable")
    client.post(
        f"/admin/data/courses/{ode.id}/reference",
        files={"file": ("scan.pdf", text_to_pdf(" "), "application/pdf")},
        data={"csrf_token": token},
    )
    fake_llm.fail_with = None
    page = client.get("/admin/data").text
    assert "읽기 실패" in page and "이전 것을 계속 써요" in page
    seeded.expire_all()
    assert seeded.get(Course, ode.id).reference_syllabus_id == ref.id  # type: ignore[union-attr]

    # 학생 미적분 강의계획서를 분석하면 새 과목과 학과가 정한 필수 개념이 비교 후보로 들어간다
    student_token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, student_token)
    upload(client, rid, student_token, "calculus.txt")
    prompt = fake_llm.prompts("EvaluationOutput")[-1]
    assert '"course_code": "MATH 2255"' in prompt and '"First-order equations", "Laplace transform"' in prompt
    assert '"Limits", "Derivatives", "Integrals"' in prompt


# ---------- 출신 대학 ----------


def test_source_institution_registration(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")

    def add(name: str, country: str) -> str:
        r = client.post("/admin/data/institutions", data={"name": name, "country": country, "csrf_token": token})
        return r.text  # 리다이렉트를 따라간 화면에 결과 메시지가 한 번 나온다

    assert "두 글자 코드" in add("Seoul Tech", "KOR")
    assert "출신 대학을 등록했어요" in add("Seoul Tech (서울공대)", "kr")
    assert "이미 등록된 출신 대학이에요" in add("Seoul Tech (서울공대)", "KR")
    seeded.expire_all()
    added = seeded.scalars(select(Institution).where(Institution.name == "Seoul Tech (서울공대)")).one()
    assert added.country == "KR" and not added.is_target
    login(client, "jiwon@student.example")
    assert "Seoul Tech (서울공대)" in client.get("/student").text


# ---------- 첫 기관·관리자 ----------


def test_bootstrap_admin_starts_without_demo_data(client: TestClient, db: Session) -> None:
    from backend.services.institution_data import bootstrap_admin

    institution, admin = bootstrap_admin(db, "Real State University", "us", "First.Admin@rsu.edu", "관리자", 900, 128)
    assert institution.is_target and institution.tuition_per_credit == 900 and admin.email == "first.admin@rsu.edu"
    try:
        bootstrap_admin(db, "Real State University", "US", "first.admin@rsu.edu", "again")
    except CreditBridgeError as exc:
        assert "이미 있는 이메일" in str(exc)
    else:
        raise AssertionError("duplicate email accepted")
    client.cookies.clear()
    r = client.post(
        "/login",
        data={"email": "first.admin@rsu.edu", "password": admin.temporary_password, "csrf_token": csrf_of(client)},
        follow_redirects=False,
    )
    assert r.headers["location"] == "/account/password"
