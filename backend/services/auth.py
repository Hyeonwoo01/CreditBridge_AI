"""로그인, 비밀번호 변경·재설정.

재설정 링크는 서버에 저장하지 않는 서명 토큰이다(itsdangerous). 30분 동안 유효하고, 토큰에 비밀번호 해시의
지문을 넣어 비밀번호가 바뀌면(재설정 완료 포함) 더는 쓸 수 없다 — 한 번만 쓸 수 있는 링크.
"""

import secrets
from datetime import timedelta
from urllib.parse import quote

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.db.base import utcnow
from backend.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from backend.models import User
from backend.models.enums import Role
from backend.repositories import audit as audit_repo
from backend.repositories import users as user_repo
from backend.security.session import password_fingerprint
from backend.services import audit, notifications

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def authenticate(session: Session, email: str, password: str) -> User | None:
    user = user_repo.get_by_email(session, email)
    if user is None:
        _hasher.hash(password)  # 존재하지 않는 계정도 같은 시간이 걸리게
        return None
    try:
        _hasher.verify(user.password_hash, password)
    except (VerificationError, InvalidHashError):
        return None
    return user


# 헷갈리는 글자(0·O·1·l·I)를 뺀 임시 비밀번호 글자
_TEMP_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
MIN_PASSWORD_LENGTH = 10


def temporary_password(length: int = 12) -> str:
    return "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(length))


def _check_new(new: str, confirm: str) -> None:
    if len(new) < MIN_PASSWORD_LENGTH:
        raise CreditBridgeError(f"새 비밀번호는 {MIN_PASSWORD_LENGTH}자 이상으로 정해 주세요.")
    if new != confirm:
        raise CreditBridgeError("새 비밀번호 확인이 일치하지 않아요.")


def change_password(session: Session, user: User, current: str, new: str, confirm: str) -> None:
    """현재 비밀번호를 확인하고 바꾼다. 임시 비밀번호로 만든 계정은 여기서 변경 표시가 풀린다."""
    try:
        _hasher.verify(user.password_hash, current)
    except (VerificationError, InvalidHashError):
        raise CreditBridgeError("현재 비밀번호가 맞지 않아요.") from None
    _check_new(new, confirm)
    if new == current:
        raise CreditBridgeError("지금과 다른 비밀번호로 정해 주세요.")
    user.password_hash = _hasher.hash(new)
    user.must_change_password = False
    audit.record(session, user, "auth.password_change", "user", str(user.id))
    session.commit()


# ---------- 비밀번호 재설정 ----------

RESET_MAX_AGE = 30 * 60  # 초
RESET_COOLDOWN = timedelta(minutes=5)  # 같은 계정에 재설정 메일을 연달아 보내지 않는다


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt="password-reset")


def reset_token(user: User, settings: Settings | None = None) -> str:
    return _serializer(settings or get_settings()).dumps({"u": user.id, "p": password_fingerprint(user)})


def user_for_reset_token(session: Session, token: str, settings: Settings | None = None) -> User | None:
    """유효한 토큰의 사용자. 서명이 틀렸거나 30분이 지났거나 이미 비밀번호가 바뀌었으면 None."""
    try:
        data = _serializer(settings or get_settings()).loads(token, max_age=RESET_MAX_AGE)
    except BadSignature:  # 만료(SignatureExpired)도 여기에 포함된다
        return None
    if not isinstance(data, dict) or not isinstance(data.get("u"), int):
        return None
    user = user_repo.get_by_id(session, data["u"])
    if user is None or data.get("p") != password_fingerprint(user):
        return None
    return user


def request_reset(session: Session, email: str) -> int | None:
    """재설정 메일을 보낼 사용자 id. 없는 이메일이거나 방금 보냈으면 None (화면에는 같은 안내를 보여준다)."""
    user = user_repo.get_by_email(session, email)
    if user is None:
        return None
    last = audit_repo.last_at(session, user.id, "auth.password_reset_request")
    if last is not None and utcnow() - last < RESET_COOLDOWN:
        return None
    audit.record(session, user, "auth.password_reset_request", "user", str(user.id))
    session.commit()
    return user.id


def send_reset_email(session: Session, user_id: int, settings: Settings | None = None) -> bool:
    """작업 큐에서 부른다. 토큰은 여기서 만들어 메일로만 보낸다(DB·작업 큐·로그에 남기지 않는다)."""
    settings = settings or get_settings()
    user = user_repo.get_by_id(session, user_id)
    if user is None:
        return False
    link = f"{settings.app_base_url.rstrip('/')}/account/reset?token={quote(reset_token(user, settings))}"
    body = (
        "CreditBridge AI 비밀번호 재설정 요청을 받았어요.\n"
        f"아래 링크에서 {RESET_MAX_AGE // 60}분 안에 새 비밀번호를 정해 주세요. 링크는 한 번만 쓸 수 있어요.\n"
        "요청하지 않았다면 이 메일을 무시하세요. 비밀번호는 바뀌지 않아요.\n\n"
        f"{link}\n"
    )
    return notifications.send_email(user.email, "[CreditBridge] 비밀번호 재설정", body, settings)


def reset_password(session: Session, token: str, new: str, confirm: str) -> User:
    user = user_for_reset_token(session, token)
    if user is None:
        raise CreditBridgeError("재설정 링크가 만료됐거나 이미 사용됐어요. 다시 요청해 주세요.")
    _check_new(new, confirm)
    user.password_hash = _hasher.hash(new)
    user.must_change_password = False
    audit.record(session, user, "auth.password_reset", "user", str(user.id))
    session.commit()
    return user


def admin_reset_password(session: Session, admin: User, email: str) -> tuple[User, str]:
    """기관 관리자가 소속 사용자에게 임시 비밀번호를 다시 발급한다. 다음 로그인 때 바꿔야 한다."""
    if admin.role != Role.ADMIN or admin.institution_id is None:
        raise PermissionDeniedError("기관 관리자만 사용할 수 있어요.")
    user = user_repo.get_by_email(session, email)
    if user is None or user.institution_id != admin.institution_id:
        raise NotFoundError("우리 기관에 그 이메일의 계정이 없어요.")
    if user.id == admin.id:
        raise CreditBridgeError("본인 비밀번호는 비밀번호 변경 화면에서 바꿔 주세요.")
    password = temporary_password()
    user.password_hash = _hasher.hash(password)
    user.must_change_password = True
    audit.record(session, admin, "account.password_reset_by_admin", "user", str(user.id))
    session.commit()
    return user, password
