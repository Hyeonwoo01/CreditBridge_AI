"""비밀번호 재설정: 메일 링크(서명 토큰, 30분·한 번만), 관리자 임시 비밀번호 재발급,
비밀번호가 바뀌면 다른 세션 끊기."""

import re
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import User
from backend.services import auth, notifications
from tests.conftest import csrf_of, login


class FakeSMTP:
    sent: list[Any] = []  # noqa: RUF012

    def __init__(self, host: str, port: int, timeout: int) -> None:
        pass

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def starttls(self) -> None:
        pass

    def login(self, user: str, password: str) -> None:
        pass

    def send_message(self, msg: Any) -> None:
        FakeSMTP.sent.append(msg)


@pytest.fixture
def smtp(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Any]]:
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("APP_BASE_URL", "https://cb.test")
    monkeypatch.setattr(notifications.smtplib, "SMTP", FakeSMTP)
    FakeSMTP.sent = []
    get_settings.cache_clear()
    yield FakeSMTP.sent
    get_settings.cache_clear()


def reset_mails(sent: list[Any]) -> list[Any]:
    return [m for m in sent if m["Subject"] == "[CreditBridge] 비밀번호 재설정"]


def forgot(client: TestClient, email: str) -> str:
    client.cookies.clear()
    r = client.post("/account/forgot", data={"email": email, "csrf_token": csrf_of(client)})
    return r.text


def test_email_reset_link_works_once_and_ends_other_sessions(
    client: TestClient, seeded: Session, smtp: list[Any]
) -> None:
    from backend.main import app

    assert "비밀번호를 잊으셨나요?" in client.get("/login").text
    other = TestClient(app)  # 다른 기기에서 로그인해 둔 세션
    login(other, "jiwon@student.example")
    assert other.get("/student").status_code == 200

    assert "등록된 이메일이면 재설정 링크를 보냈어요" in forgot(client, "Jiwon@student.example")
    assert "등록된 이메일이면 재설정 링크를 보냈어요" in forgot(client, "nobody@student.example")  # 같은 안내
    forgot(client, "jiwon@student.example")  # 5분 안에 다시 요청하면 메일을 또 보내지 않는다
    mails = reset_mails(smtp)
    assert len(mails) == 1 and mails[0]["To"] == "jiwon@student.example"
    body = mails[0].get_content()
    assert "이지원" not in body and "30분" in body  # 메일에 이름을 넣지 않는다
    link = re.search(r"https://cb\.test/account/reset\?token=\S+", body)
    assert link
    path = link.group(0).removeprefix("https://cb.test")

    page = client.get(path)
    assert page.status_code == 200 and "새 비밀번호 정하기" in page.text
    assert page.headers["referrer-policy"] == "no-referrer" and page.headers["cache-control"] == "no-store"
    token = re.search(r'name="token" value="([^"]+)"', page.text).group(1)  # type: ignore[union-attr]
    csrf_box = [csrf_of(client, path)]

    def reset(new: str, confirm: str | None = None) -> Any:
        data = {"token": token, "new": new, "confirm": confirm or new, "csrf_token": csrf_box[0]}
        return client.post("/account/reset", data=data, follow_redirects=False)

    r = reset("short")
    assert r.status_code == 422 and "10자 이상" in r.text and 'name="token"' in r.text
    r = reset("brand-new-password")
    assert r.status_code == 303 and r.headers["location"] == "/login"

    assert other.get("/student", follow_redirects=False).headers["location"] == "/login"  # 다른 세션은 끊긴다
    used = client.get(path)
    assert used.status_code == 400 and "만료됐거나 이미 사용됐어요" in used.text
    csrf_box[0] = csrf_of(client)  # 재설정이 끝나면 세션을 비우므로 새 토큰으로 다시 시도
    r = reset("another-password-1")
    assert r.status_code == 422 and "만료됐거나 이미 사용됐어요" in r.text
    client.cookies.clear()
    r = client.post(
        "/login",
        data={"email": "jiwon@student.example", "password": "demo1234", "csrf_token": csrf_of(client)},
    )
    assert r.status_code == 401
    login(client, "jiwon@student.example", "brand-new-password")


def test_reset_token_rejects_tampering_and_expiry(seeded: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    user = seeded.scalars(select(User).where(User.email == "jiwon@student.example")).one()
    token = auth.reset_token(user)
    assert auth.user_for_reset_token(seeded, token) is user
    assert auth.user_for_reset_token(seeded, token[:-2] + "xx") is None
    monkeypatch.setattr(auth, "RESET_MAX_AGE", -1)
    assert auth.user_for_reset_token(seeded, token) is None


def test_without_smtp_users_are_sent_to_their_admin(client: TestClient, seeded: Session) -> None:
    page = client.get("/account/forgot").text
    assert "메일 발송이 설정되어 있지 않아요" in page and 'action="/account/forgot"' not in page
    assert "소속 기관 관리자" in forgot(client, "jiwon@student.example")


def test_admin_reissues_temporary_password(client: TestClient, seeded: Session) -> None:
    from backend.main import app

    prof = TestClient(app)
    login(prof, "dkim@msu.example")
    token = login(client, "admin@msu.example")

    def reissue(email: str) -> Any:
        return client.post("/admin/data/password-reset", data={"email": email, "csrf_token": token})

    r = reissue("dkim@msu.example")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    temp = re.search(r'font-mono text-\[17px\]">([^<]+)</code>', r.text).group(1)  # type: ignore[union-attr]
    assert prof.get("/professor", follow_redirects=False).headers["location"] == "/login"
    assert "우리 기관에 그 이메일의 계정이 없어요" in reissue("nobody@msu.example").text
    assert "본인 비밀번호는" in reissue("admin@msu.example").text

    client.cookies.clear()
    r = client.post(
        "/login",
        data={"email": "dkim@msu.example", "password": temp, "csrf_token": csrf_of(client)},
        follow_redirects=False,
    )
    assert r.headers["location"] == "/account/password"
    token = login(client, "rachel@msu.example")
    r = client.post("/admin/data/password-reset", data={"email": "dkim@msu.example", "csrf_token": token})
    assert r.status_code == 403


def test_changing_password_keeps_this_session_and_ends_others(client: TestClient, seeded: Session) -> None:
    from backend.main import app

    other = TestClient(app)
    login(other, "rachel@msu.example")
    token = login(client, "rachel@msu.example")
    r = client.post(
        "/account/password",
        data={"current": "demo1234", "new": "rachel-new-pass", "confirm": "rachel-new-pass", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303 and client.get("/review").status_code == 200
    assert other.get("/review", follow_redirects=False).headers["location"] == "/login"


def link_path(mail: Any) -> str:
    m = re.search(r"https://cb\.test(/account/reset\?token=\S+)", mail.get_content())
    assert m
    return m.group(1)


def set_password(client: TestClient, path: str, new: str) -> Any:
    client.cookies.clear()
    page = client.get(path)
    assert page.status_code == 200, page.text
    token = re.search(r'name="token" value="([^"]+)"', page.text).group(1)  # type: ignore[union-attr]
    data = {"token": token, "new": new, "confirm": new, "csrf_token": csrf_of(client, path)}
    return client.post("/account/reset", data=data, follow_redirects=False)


def test_with_mail_new_accounts_get_setup_links_instead_of_passwords(
    client: TestClient, seeded: Session, smtp: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    token = login(client, "admin@msu.example")
    body = "email,name,role,department\nnew.eval@msu.example,New Evaluator,evaluator,\n"
    r = client.post(
        "/admin/data/accounts",
        files={"file": ("a.csv", body.encode(), "text/csv")},
        data={"csrf_token": token},
    )
    assert r.status_code == 200 and "비밀번호 설정 링크(72시간 유효" in r.text
    assert "임시 비밀번호 CSV 받기" not in r.text and 'font-mono">' not in r.text.split("새로 만든 계정")[1][:3000]
    mails = [m for m in smtp if m["Subject"] == "[CreditBridge] 계정이 만들어졌어요"]
    assert (
        len(mails) == 1 and mails[0]["To"] == "new.eval@msu.example" and "New Evaluator" not in mails[0].get_content()
    )

    monkeypatch.setattr(auth, "RESET_MAX_AGE", -1)  # 30분짜리 재설정 기한이 지나도 계정 설정 링크(72시간)는 유효
    assert set_password(client, link_path(mails[0]), "evaluator-pass-1").status_code == 303
    login(client, "new.eval@msu.example", "evaluator-pass-1")
    assert client.get("/review").status_code == 200  # 링크로 정했으니 첫 로그인 변경 화면을 거치지 않는다


def test_with_mail_admin_reset_sends_link_and_shows_no_password(
    client: TestClient, seeded: Session, smtp: list[Any]
) -> None:
    token = login(client, "admin@msu.example")
    r = client.post("/admin/data/password-reset", data={"email": "dkim@msu.example", "csrf_token": token})
    assert "dkim@msu.example 메일로 비밀번호 설정 링크(72시간 유효)를 보냈어요" in r.text
    assert "font-mono text-[17px]" not in r.text
    mails = [m for m in smtp if m["To"] == "dkim@msu.example"]
    assert len(mails) == 1 and "기관 관리자가 CreditBridge AI 비밀번호를 초기화했어요" in mails[0].get_content()
    client.cookies.clear()
    r = client.post(
        "/login",
        data={"email": "dkim@msu.example", "password": "demo1234", "csrf_token": csrf_of(client)},
    )
    assert r.status_code == 401  # 이전 비밀번호는 무효
    assert set_password(client, link_path(mails[0]), "dkim-new-pass-1").status_code == 303
    login(client, "dkim@msu.example", "dkim-new-pass-1")
