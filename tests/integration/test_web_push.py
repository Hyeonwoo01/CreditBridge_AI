"""브라우저 웹 푸시 (FR-20): 구독 저장·해제, 발송, 만료 구독 정리, 개인정보 없는 내용."""

import json
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
import pywebpush
from fastapi.testclient import TestClient
from py_vapid import Vapid
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.base import utcnow
from backend.models import Notification, PushSubscription, User
from backend.services import push
from scripts.generate_vapid_keys import generate
from tests.conftest import login

P256DH = "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM"
AUTH = "tBHItJI5svbpez7KI4CCXg"


def sub(n: int = 1) -> dict[str, Any]:
    return {"endpoint": f"https://push.example.com/send/device-{n}", "keys": {"p256dh": P256DH, "auth": AUTH}}


@pytest.fixture
def vapid(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    public_key, private_key = generate()
    monkeypatch.setenv("VAPID_PUBLIC_KEY", public_key)
    monkeypatch.setenv("VAPID_PRIVATE_KEY", private_key)
    get_settings.cache_clear()
    sent: list[dict[str, Any]] = []

    def fake_webpush(subscription_info: dict[str, Any], data: str, **kwargs: Any) -> None:
        if subscription_info["endpoint"].endswith("gone"):
            response = type("R", (), {"status_code": 410})()
            raise pywebpush.WebPushException("gone", response=response)
        sent.append({"endpoint": subscription_info["endpoint"], "data": json.loads(data), **kwargs})

    monkeypatch.setattr(pywebpush, "webpush", fake_webpush)
    yield sent
    get_settings.cache_clear()


def test_generated_keys_load_in_vapid() -> None:
    public_key, private_key = generate()
    assert Vapid.from_string(private_key).public_key is not None
    assert len(public_key) == 87  # 65바이트 압축하지 않은 점 (base64url)


def test_push_card_and_service_worker(client: TestClient, seeded: Session, vapid: list[dict[str, Any]]) -> None:
    login(client, "mbrown@msu.example")
    page = client.get("/notifications").text
    assert 'id="push-card"' in page and get_settings().vapid_public_key in page
    sw = client.get("/sw.js")
    assert sw.status_code == 200 and "showNotification" in sw.text and "javascript" in sw.headers["content-type"]


def test_push_card_hidden_without_keys(client: TestClient, seeded: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY"):
        monkeypatch.setenv(name, "")  # 개발자 .env에 키가 있어도 키 없는 서버로 본다
    get_settings.cache_clear()
    login(client, "mbrown@msu.example")
    assert 'id="push-card"' not in client.get("/notifications").text
    token = login(client, "mbrown@msu.example")
    r = client.post("/notifications/push/subscribe", json=sub(), headers={"X-CSRF-Token": token})
    assert r.status_code == 422


def test_subscribe_requires_csrf_and_valid_body(
    client: TestClient, seeded: Session, vapid: list[dict[str, Any]]
) -> None:
    token = login(client, "mbrown@msu.example")
    assert client.post("/notifications/push/subscribe", json=sub()).status_code == 403
    bad = {"endpoint": "http://insecure.example.com/x", "keys": {"p256dh": P256DH, "auth": AUTH}}
    assert client.post("/notifications/push/subscribe", json=bad, headers={"X-CSRF-Token": token}).status_code == 422
    r = client.post("/notifications/push/subscribe", json=sub(), headers={"X-CSRF-Token": token})
    assert r.status_code == 200 and r.json() == {"devices": 1}
    # 같은 브라우저 다시 구독 → 그대로 1대, 다른 계정으로 로그인해 구독하면 그 계정으로 옮겨 간다
    assert client.post("/notifications/push/subscribe", json=sub(), headers={"X-CSRF-Token": token}).json() == {
        "devices": 1
    }
    token = login(client, "dkim@msu.example")
    client.post("/notifications/push/subscribe", json=sub(), headers={"X-CSRF-Token": token})
    owners = seeded.scalars(select(PushSubscription.user_id)).all()
    dkim = seeded.scalars(select(User.id).where(User.email == "dkim@msu.example")).one()
    assert owners == [dkim]
    r = client.post(
        "/notifications/push/unsubscribe", json={"endpoint": sub()["endpoint"]}, headers={"X-CSRF-Token": token}
    )
    assert r.json() == {"devices": 0}


def test_deliver_sends_translated_payload_and_drops_gone_devices(seeded: Session, vapid: list[dict[str, Any]]) -> None:
    prof = seeded.scalars(select(User).where(User.email == "mbrown@msu.example")).one()
    prof.locale = "en"
    old = utcnow() - timedelta(minutes=5)
    seeded.add_all(
        [
            PushSubscription(user_id=prof.id, endpoint=sub(1)["endpoint"], p256dh=P256DH, auth=AUTH, created_at=old),
            PushSubscription(
                user_id=prof.id, endpoint="https://push.example.com/send/gone", p256dh=P256DH, auth=AUTH, created_at=old
            ),
        ]
    )
    seeded.flush()
    seeded.add(
        Notification(
            user_id=prof.id, kind="assignment.created", message="새 심사가 배정됐어요: PHY 101", link="/professor"
        )
    )
    # 구독하기 전에 온 알림은 보내지 않는다
    seeded.add(
        Notification(
            user_id=prof.id, kind="x", message="새 심사가 배정됐어요: OLD 1", created_at=old - timedelta(hours=1)
        )
    )
    seeded.commit()

    assert push.deliver_pending(seeded) == 1
    assert len(vapid) == 1
    payload = vapid[0]["data"]
    assert payload["link"] == "/professor" and "PHY 101" in payload["body"] and payload["body"].startswith("New review")
    assert vapid[0]["vapid_claims"]["sub"].startswith("mailto:") and vapid[0]["ttl"] > 0
    endpoints = seeded.scalars(select(PushSubscription.endpoint)).all()
    assert endpoints == [sub(1)["endpoint"]]  # 410을 돌려준 기기는 지운다
    assert push.deliver_pending(seeded) == 0  # 이미 보낸 알림은 다시 보내지 않는다


def test_deliver_does_nothing_without_keys(seeded: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "")
    get_settings.cache_clear()
    assert push.deliver_pending(seeded) == 0
    get_settings.cache_clear()
