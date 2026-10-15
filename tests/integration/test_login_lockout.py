"""로그인 실패 잠금: 연속 5번 틀리면 1분 잠금, 그 뒤로도 틀려 연속 10번이면 비밀번호를 초기화하고 메일로만 재설정."""

import re
from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.models import AuditLog, User
from tests.conftest import csrf_of, login
from tests.integration.test_password_reset import reset_mails, smtp  # noqa: F401  (메일 대역 fixture)


def attempt(client: TestClient, email: str, password: str) -> Any:
    client.cookies.clear()
    return client.post(
        "/login", data={"email": email, "password": password, "csrf_token": csrf_of(client)}, follow_redirects=False
    )


def user(db: Session, email: str) -> User:
    db.expire_all()
    return db.scalars(select(User).where(User.email == email)).one()


def unlock(db: Session, email: str) -> None:
    """1분이 지난 것처럼 잠금 해제 시각을 앞당긴다."""
    u = user(db, email)
    u.locked_until = utcnow() - timedelta(seconds=1)
    db.commit()


def test_five_failures_lock_login_for_a_minute(client: TestClient, seeded: Session) -> None:
    email = "rachel@msu.example"
    texts = [attempt(client, email, "wrong").text for _ in range(4)]
    assert "번 더" not in texts[0] and "번 더" not in texts[1]
    assert "2번 더 틀리면 1분 동안 로그인할 수 없어요" in texts[2]
    assert "1번 더 틀리면 1분 동안 로그인할 수 없어요" in texts[3]
    r = attempt(client, email, "wrong")
    assert r.status_code == 429 and "5번 틀려 1분 동안 로그인할 수 없어요" in r.text
    assert "5번 더 틀리면 비밀번호가 초기화돼요" in r.text
    r = attempt(client, email, "demo1234")  # 맞는 비밀번호도 잠긴 동안은 안 된다
    assert r.status_code == 429 and "초 뒤에 다시 시도해 주세요" in r.text
    assert user(seeded, email).locked_until is not None

    unlock(seeded, email)
    assert attempt(client, email, "demo1234").status_code == 303  # 성공하면 횟수가 0으로
    u = user(seeded, email)
    assert u.failed_logins == 0 and u.locked_until is None
    assert seeded.scalars(select(AuditLog).where(AuditLog.action == "auth.lockout")).first() is not None


def test_ten_failures_reset_password_and_mail_a_reset_link(
    client: TestClient,
    seeded: Session,
    smtp: list[Any],  # noqa: F811
) -> None:
    from backend.main import app

    email = "rachel@msu.example"
    other = TestClient(app)
    login(other, email)  # 다른 기기의 세션
    for _ in range(5):
        attempt(client, email, "wrong")
    unlock(seeded, email)
    texts = [attempt(client, email, "wrong").text for _ in range(4)]  # 6~9번째
    assert "4번 더 틀리면 비밀번호가 초기화돼요" in texts[0] and "1번 더 틀리면 비밀번호가 초기화돼요" in texts[3]
    r = attempt(client, email, "wrong")  # 10번째
    assert r.status_code == 423 and "비밀번호를 초기화했어요" in r.text and "가입한 이메일로 보낸 링크" in r.text

    assert other.get("/review", follow_redirects=False).headers["location"] == "/login"  # 다른 세션은 끊긴다
    r = attempt(client, email, "demo1234")  # 예전 비밀번호로는 더 이상 안 된다
    assert r.status_code == 423
    mails = reset_mails(smtp)
    assert len(mails) == 1 and mails[0]["To"] == email
    body = mails[0].get_content()
    assert "로그인 실패가 10번 이어져" in body and "Rachel" not in body
    path = re.search(r"https://cb\.test(/account/reset\?token=\S+)", body).group(1)  # type: ignore[union-attr]
    log = seeded.scalars(select(AuditLog).where(AuditLog.action == "auth.lockout_reset")).one()
    assert log.payload_json == {"failed": 10}

    # 메일 링크로 새 비밀번호를 정하면 다시 로그인할 수 있다
    client.cookies.clear()
    page = client.get(path)
    token = re.search(r'name="token" value="([^"]+)"', page.text).group(1)  # type: ignore[union-attr]
    r = client.post(
        "/account/reset",
        data={
            "token": token,
            "new": "fresh-password-1",
            "confirm": "fresh-password-1",
            "csrf_token": csrf_of(client, path),
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert user(seeded, email).failed_logins == 0
    login(client, email, "fresh-password-1")


def test_lockout_without_mail_sends_user_to_admin(client: TestClient, seeded: Session) -> None:
    email = "dkim@msu.example"
    for _ in range(5):
        attempt(client, email, "wrong")
    unlock(seeded, email)
    for _ in range(4):
        attempt(client, email, "wrong")
    r = attempt(client, email, "wrong")
    assert r.status_code == 423 and "기관 관리자에게 임시 비밀번호 발급을 요청해 주세요" in r.text

    token = login(client, "admin@msu.example")
    assert "로그인 실패로 비밀번호가 초기화된 계정 1명" in client.get("/admin/data").text
    r = client.post("/admin/data/password-reset", data={"email": email, "csrf_token": token})
    temp = re.search(r'font-mono text-\[17px\]">([^<]+)</code>', r.text).group(1)  # type: ignore[union-attr]
    assert user(seeded, email).failed_logins == 0
    assert attempt(client, email, temp).headers["location"] == "/account/password"


def test_unknown_email_never_locks(client: TestClient, seeded: Session) -> None:
    for _ in range(7):
        r = attempt(client, "nobody@msu.example", "wrong")
        assert r.status_code == 401 and "이메일 또는 비밀번호가 맞지 않아요." in r.text and "번 더" not in r.text
