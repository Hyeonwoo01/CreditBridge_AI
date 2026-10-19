"""공개 데모 모드: 방문자가 데모 계정을 못 쓰게 만드는 동작을 막고, 로그인 화면에 데모 계정 버튼을 보여 준다."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import AuditLog, User
from tests.conftest import csrf_of, login


@pytest.fixture
def demo(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(get_settings(), "demo_mode", True)
    yield


def test_demo_login_page_and_banner(client: TestClient, seeded: Session, demo: None) -> None:
    page = client.get("/login").text
    assert "데모 계정으로 둘러보기" in page and "예시용 공개 데모" in page
    token = csrf_of(client)
    r = client.post("/login", data={"email": "rachel@msu.example", "password": "demo1234", "csrf_token": token})
    assert r.status_code == 200 and "예시용 공개 데모" in r.text


def test_demo_blocks_password_and_account_changes(client: TestClient, seeded: Session, demo: None) -> None:
    token = login(client, "jiwon@student.example")
    r = client.post(
        "/account/password",
        data={"current": "demo1234", "new": "another-pass-123", "confirm": "another-pass-123", "csrf_token": token},
    )
    assert "공개 데모에서는 비밀번호와 계정 상태를 바꿀 수 없어요" in r.text

    token = login(client, "admin@msu.example")
    for url, data in [
        ("/admin/data/password-reset", {"email": "jiwon@student.example"}),
        ("/admin/data/accounts/active", {"email": "jiwon@student.example", "action": "deactivate"}),
    ]:
        assert "공개 데모에서는" in client.post(url, data={**data, "csrf_token": token}).text
    seeded.expire_all()
    jiwon = seeded.scalars(select(User).where(User.email == "jiwon@student.example")).one()
    assert jiwon.is_active


def test_demo_failed_logins_only_lock_without_resetting_password(
    client: TestClient, seeded: Session, demo: None
) -> None:
    user = seeded.scalars(select(User).where(User.email == "dkim@msu.example")).one()
    before = user.password_hash
    client.cookies.clear()
    token = csrf_of(client)
    for _ in range(10):
        client.post("/login", data={"email": user.email, "password": "wrong-pass", "csrf_token": token})
    seeded.refresh(user)
    assert user.password_hash == before and user.locked_until is not None
    actions = {a.action for a in seeded.scalars(select(AuditLog).where(AuditLog.target_id == str(user.id)))}
    assert "auth.lockout_reset" not in actions and "auth.lockout" in actions
