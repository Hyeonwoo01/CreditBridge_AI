"""영어 화면: 언어 고르기·전환, 역할별 화면, 저장된 알림 번역, 받는 사람 언어로 보내는 메일, 리포트 PDF."""

import re

import pymupdf
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import User
from tests.conftest import csrf_of, login
from tests.integration.test_review_extras import approve
from tests.integration.test_workflow import professor_for

HANGUL = re.compile(r"[가-힣]")


def switch(client: TestClient, lang: str, next_path: str = "/login") -> None:
    token = csrf_of(client, next_path)
    r = client.post("/lang", data={"lang": lang, "next": next_path, "csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == next_path


def test_browser_language_and_switch(client: TestClient, seeded: Session) -> None:
    page = client.get("/login").text
    assert '<html lang="ko">' in page and "로그인" in page and "English" in page  # 기본은 한국어

    page = client.get("/login", headers={"Accept-Language": "en-US,en;q=0.9"}).text
    assert '<html lang="en">' in page and "Sign in" in page and "한국어" in page

    switch(client, "en")
    page = client.get("/login").text
    assert "Evidence-based transfer credit" in page and "Incorrect" not in page
    r = client.post("/login", data={"email": "x@y.z", "password": "nope", "csrf_token": csrf_of(client)})
    assert "Incorrect email or password." in r.text

    # 열린 리다이렉트는 막는다
    token = csrf_of(client)
    r = client.post("/lang", data={"lang": "ko", "next": "//evil.example", "csrf_token": token}, follow_redirects=False)
    assert r.headers["location"] == "/"


def test_login_remembers_locale_and_each_role_reads_english(client: TestClient, seeded: Session) -> None:
    switch(client, "en")
    token = csrf_of(client)
    client.post("/login", data={"email": "rachel@msu.example", "password": "demo1234", "csrf_token": token})
    seeded.expire_all()
    rachel = seeded.scalars(select(User).where(User.email == "rachel@msu.example")).one()
    assert rachel.locale == "en"  # 처음 로그인할 때 그때 화면 언어를 계정에 저장

    client.cookies.clear()  # 다른 기기에서 로그인해도 계정 언어를 따른다
    login(client, "rachel@msu.example")
    page = client.get("/review").text
    assert '<html lang="en">' in page and "Review queue" in page and "Registrar review workspace" in page
    for path, text in (
        ("/review/appeals", "Appeals"),
        ("/review/stats", "Deadline reminders"),
        ("/notifications", "No new notifications."),
    ):
        assert text in client.get(path).text, path

    token = login(client, "admin@msu.example")
    switch(client, "en", "/admin/stats")
    for path, text in (
        ("/admin/stats", "Admin console"),
        ("/admin/data", "Deactivate account"),
        ("/admin/audit", "append-only"),
    ):
        assert text in client.get(path).text, path
    seeded.expire_all()
    assert seeded.scalars(select(User).where(User.email == "admin@msu.example")).one().locale == "en"

    login(client, "jiwon@student.example")  # 한국어 사용자는 그대로
    page = client.get("/student").text
    assert '<html lang="ko">' in page and "내 편입 요청" in page


def test_professor_flow_notifications_and_pdf_in_english(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    switch(client, "en", f"/professor/evaluations/{ev.id}")
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "Final decision" in page and "Approve as recommended" in page and "Internal notes" in page
    assert "Coverage and evidence by concept" in page and "Direct credit" in page
    # 화면 위 문구에 한글이 남지 않는다 (학생 이름·대학 이름·AI가 쓴 한국어 설명은 데이터라 제외하고 메뉴·제목만 본다)
    nav = page.split("<main", 1)[0]
    assert not HANGUL.search(re.sub(r"<script.*?</script>", "", nav, flags=re.S).replace("한국어", ""))

    token = csrf_of(client, f"/professor/evaluations/{ev.id}")
    r = client.post(f"/evaluations/{ev.id}/notes", data={"body": "checking", "csrf_token": token})
    assert "Note added. Students can&#39;t see it." in r.text
    approve(client, ev, token)
    pdf = client.get(f"/evaluations/{ev.id}/report.pdf").content
    text = "".join(p.get_text() for p in pymupdf.open("pdf", pdf))
    assert "Decision evidence report" in text and "faculty make the final decision" in text

    # 학생 알림은 한국어 원문으로 저장되고, 영어를 고른 학생에게는 영어로 보인다
    login(client, "jiwon@student.example")
    assert "판정 결과가 확정됐어요: 직접 인정" in client.get("/notifications").text
    switch(client, "en", "/notifications")
    page = client.get("/notifications").text
    assert "The decision for MATH 101 is final: Direct credit" in page
    seeded.expire_all()
    assert seeded.scalars(select(User).where(User.email == "jiwon@student.example")).one().locale == "en"


def test_notification_email_uses_recipient_language(seeded: Session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from backend.config import get_settings
    from backend.services import notifications

    sent: list[tuple[str, str]] = []

    class FakeSMTP:
        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, *a):  # type: ignore[no-untyped-def]
            return False

        def send_message(self, msg):  # type: ignore[no-untyped-def]
            sent.append((msg["To"], msg["Subject"]))

    settings = get_settings().model_copy(update={"smtp_host": "smtp.example", "app_base_url": "https://cb.example"})
    monkeypatch.setattr(notifications, "_smtp", lambda s: FakeSMTP())
    rachel = seeded.scalars(select(User).where(User.email == "rachel@msu.example")).one()
    dkim = seeded.scalars(select(User).where(User.email == "dkim@msu.example")).one()
    rachel.locale = "en"
    notifications.notify(
        seeded, [rachel, dkim], "reminder.evaluator", "기한 알림: 교수 배정을 기다리는 과목 2개", "/review"
    )
    seeded.commit()
    notifications.deliver_pending(seeded, settings)
    subjects = dict(sent)
    assert (
        subjects["rachel@msu.example"] == "[CreditBridge] Deadline reminder: 2 courses waiting for a faculty assignment"
    )
    assert subjects["dkim@msu.example"] == "[CreditBridge] 기한 알림: 교수 배정을 기다리는 과목 2개"
