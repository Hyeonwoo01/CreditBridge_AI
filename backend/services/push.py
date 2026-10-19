"""브라우저 웹 푸시 (FR-20 모바일 알림). 화면 알림을 구독한 기기에도 보낸다.

- 설정(VAPID 키)이 있을 때만 켜진다. 키가 없으면 화면·메일 알림만 쓴다.
- 푸시 내용은 알림 메시지와 같은 글(과목 코드·처리 내용)과 화면 주소만 담고, 이름·학번·성적은 넣지 않는다.
- 브라우저 푸시 서비스가 구독 만료(404·410)를 알리면 그 구독을 지운다.
- 로그에는 구독 id만 남기고 푸시 서비스 주소(endpoint)는 남기지 않는다.
"""

import json
import logging
from datetime import timedelta
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.db.base import utcnow
from backend.errors import CreditBridgeError
from backend.i18n import N_, translate_stored, use_locale
from backend.i18n import gettext as tr
from backend.models import PushSubscription, User
from backend.repositories import push as push_repo

logger = logging.getLogger(__name__)

TITLE = N_("CreditBridge 알림")
# 푸시 서비스가 기기에 전달하지 못하면 이 시간까지 들고 있다가 버린다 (초)
TTL_SECONDS = 24 * 60 * 60


class SubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=20, max_length=200)
    auth: str = Field(min_length=8, max_length=100)


class SubscriptionIn(BaseModel):
    """브라우저 PushSubscription.toJSON() 모양."""

    endpoint: str = Field(max_length=1000)
    keys: SubscriptionKeys

    @field_validator("endpoint")
    @classmethod
    def https_only(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("endpoint must be https")
        return value


class PushSubscriptionError(CreditBridgeError):
    pass


def push_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.vapid_public_key and settings.vapid_private_key)


def subscribe(session: Session, user: User, data: dict[str, Any]) -> PushSubscription:
    """이 기기(브라우저)의 구독을 저장한다. 같은 브라우저에서 다른 계정으로 로그인했으면 그 계정으로 옮긴다."""
    if not push_enabled():
        raise PushSubscriptionError(tr("이 서버에는 푸시 알림이 설정돼 있지 않아요."))
    try:
        body = SubscriptionIn.model_validate(data)
    except ValidationError as exc:
        raise PushSubscriptionError(tr("브라우저가 보낸 구독 정보가 올바르지 않아요.")) from exc
    existing = push_repo.by_endpoint(session, body.endpoint)
    if existing is not None:
        if existing.user_id != user.id:
            existing.created_at = utcnow()  # 새 사용자에게는 지금부터 온 알림만
        existing.user_id = user.id
        existing.p256dh = body.keys.p256dh
        existing.auth = body.keys.auth
        session.commit()
        return existing
    subscription = push_repo.add(
        session, PushSubscription(user_id=user.id, endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth)
    )
    session.commit()
    return subscription


def unsubscribe(session: Session, user: User, endpoint: str) -> bool:
    removed = push_repo.remove(session, user.id, endpoint[:1000])
    session.commit()
    return removed > 0


def device_count(session: Session, user: User) -> int:
    return push_repo.count_for(session, user.id)


def _payload(message: str, link: str, locale: str | None) -> str:
    with use_locale(locale):
        return json.dumps({"title": translate_stored(TITLE), "body": translate_stored(message), "link": link or "/"})


def deliver_pending(session: Session, settings: Settings | None = None) -> int:
    """아직 푸시하지 않은 알림을 구독한 기기에 보낸다. 보낸 푸시 수. 설정이 없으면 아무것도 하지 않는다."""
    settings = settings or get_settings()
    if not push_enabled(settings):
        return 0
    from pywebpush import WebPushException, webpush  # 무거운 의존성(aiohttp 등)은 보낼 때만 불러온다

    # 푸시를 나중에 켜도 오래된 알림이 한꺼번에 나가지 않게 최근 하루치만 보낸다
    pending = push_repo.pending(session, since=utcnow() - timedelta(days=1))
    sent = 0
    gone: set[int] = set()
    for notification, user, subscriptions in pending:
        data = _payload(notification.message, notification.link, user.locale)
        for subscription in subscriptions:
            if subscription.id in gone:
                continue
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                    },
                    data=data,
                    vapid_private_key=settings.vapid_private_key,
                    vapid_claims={"sub": settings.vapid_subject},
                    ttl=TTL_SECONDS,
                    timeout=10,
                )
            except WebPushException as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in (404, 410):  # 사용자가 권한을 거두었거나 구독이 만료됨
                    gone.add(subscription.id)
                    push_repo.remove_by_id(session, subscription.id)
                logger.warning("web push failed", extra={"subscription_id": subscription.id, "status": status})
                continue
            subscription.last_sent_at = utcnow()
            sent += 1
        # 실패한 기기에 다시 보내려고 붙잡지 않는다 (화면 알림과 메일은 그대로 남는다)
        notification.pushed_at = utcnow()
    session.commit()
    return sent
