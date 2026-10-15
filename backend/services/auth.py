"""로그인, 비밀번호 변경·재설정, 로그인 실패 잠금.

로그인 실패: 연속 5번 틀리면 1분 동안 잠그고, 그 뒤로도 틀려 연속 10번이 되면 비밀번호를 아무도 모르는 값으로
바꿔(다른 기기 로그인도 끊김) 메일 재설정 링크로만 새 비밀번호를 정하게 한다. 성공·재설정하면 횟수는 0이 된다.

재설정 링크는 서버에 저장하지 않는 서명 토큰이다(itsdangerous). 30분 동안 유효하고, 토큰에 비밀번호 해시의
지문을 넣어 비밀번호가 바뀌면(재설정 완료 포함) 더는 쓸 수 없다 — 한 번만 쓸 수 있는 링크.
"""

import math
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
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


LOCK_AFTER = 5  # 연속 실패가 이 횟수가 되면
LOCK_FOR = timedelta(minutes=1)  # 이만큼 로그인을 막는다
RESET_AFTER = 10  # 연속 실패가 이 횟수가 되면 비밀번호를 무효로 하고 메일 재설정만 허용
WRONG_PASSWORD = "이메일 또는 비밀번호가 맞지 않아요."


@dataclass(frozen=True)
class LoginAttempt:
    user: User | None = None  # 성공했을 때만
    error: str = ""
    status_code: int = 200
    send_reset_to: int | None = None  # 이번 실패로 비밀번호를 초기화해 재설정 메일을 보낼 사용자


def lockout_message(settings: Settings | None = None) -> str:
    how = (
        "가입한 이메일로 보낸 링크에서 새 비밀번호를 정해 주세요."
        if notifications.email_enabled(settings)
        else "기관 관리자에게 임시 비밀번호 발급을 요청해 주세요."
    )
    return f"로그인 실패가 {RESET_AFTER}번 이어져 보안을 위해 비밀번호를 초기화했어요. {how}"


def login_attempt(session: Session, email: str, password: str) -> LoginAttempt:
    user = user_repo.get_by_email(session, email)
    if user is None:
        _hasher.hash(password)  # 존재하지 않는 계정도 같은 시간이 걸리게
        return LoginAttempt(error=WRONG_PASSWORD, status_code=401)
    if user.failed_logins >= RESET_AFTER:
        _hasher.hash(password)
        return LoginAttempt(error=lockout_message(), status_code=423)
    now = utcnow()
    if user.locked_until is not None and user.locked_until > now:
        _hasher.hash(password)
        seconds = math.ceil((user.locked_until - now).total_seconds())
        return LoginAttempt(
            error=f"비밀번호를 {LOCK_AFTER}번 틀려 로그인이 잠겼어요. {seconds}초 뒤에 다시 시도해 주세요.",
            status_code=429,
        )
    try:
        _hasher.verify(user.password_hash, password)
    except (VerificationError, InvalidHashError):
        return _failed(session, user, now)
    user.failed_logins = 0
    user.locked_until = None
    return LoginAttempt(user=user)


def _failed(session: Session, user: User, now: datetime) -> LoginAttempt:
    count = user_repo.add_failed_login(session, user.id)
    session.refresh(user)
    if count >= RESET_AFTER:
        # 아무도 모르는 값으로 바꾼다: 비밀번호 지문이 바뀌어 이전 세션·재설정 링크도 모두 무효가 된다
        user.password_hash = _hasher.hash(secrets.token_urlsafe(32))
        user.locked_until = None
        audit.record(session, user, "auth.lockout_reset", "user", str(user.id), failed=count)
        session.commit()
        return LoginAttempt(error=lockout_message(), status_code=423, send_reset_to=user.id)
    if count == LOCK_AFTER:
        user.locked_until = now + LOCK_FOR
        audit.record(session, user, "auth.lockout", "user", str(user.id), failed=count)
        session.commit()
        return LoginAttempt(
            error=f"비밀번호를 {LOCK_AFTER}번 틀려 1분 동안 로그인할 수 없어요. "
            f"그 뒤로도 {RESET_AFTER - LOCK_AFTER}번 더 틀리면 비밀번호가 초기화돼요.",
            status_code=429,
        )
    session.commit()
    if count < LOCK_AFTER:
        left = LOCK_AFTER - count
        hint = f" {left}번 더 틀리면 1분 동안 로그인할 수 없어요." if left <= 2 else ""
    else:
        hint = f" {RESET_AFTER - count}번 더 틀리면 비밀번호가 초기화돼요."
    return LoginAttempt(error=WRONG_PASSWORD + hint, status_code=401)


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


def send_reset_email(session: Session, user_id: int, settings: Settings | None = None, lockout: bool = False) -> bool:
    """작업 큐에서 부른다. 토큰은 여기서 만들어 메일로만 보낸다(DB·작업 큐·로그에 남기지 않는다)."""
    settings = settings or get_settings()
    user = user_repo.get_by_id(session, user_id)
    if user is None:
        return False
    link = f"{settings.app_base_url.rstrip('/')}/account/reset?token={quote(reset_token(user, settings))}"
    intro = (
        f"로그인 실패가 {RESET_AFTER}번 이어져 보안을 위해 CreditBridge AI 비밀번호를 초기화했어요.\n"
        if lockout
        else "CreditBridge AI 비밀번호 재설정 요청을 받았어요.\n"
    )
    ignore = (
        "본인이 시도한 것이 아니라면 누군가 비밀번호를 추측하려 한 것일 수 있어요. 기관 관리자에게도 알려 주세요.\n"
        if lockout
        else "요청하지 않았다면 이 메일을 무시하세요. 비밀번호는 바뀌지 않아요.\n"
    )
    body = (
        intro
        + f"아래 링크에서 {RESET_MAX_AGE // 60}분 안에 새 비밀번호를 정해 주세요. 링크는 한 번만 쓸 수 있어요.\n"
        + ignore
        + f"\n{link}\n"
    )
    return notifications.send_email(user.email, "[CreditBridge] 비밀번호 재설정", body, settings)


def reset_password(session: Session, token: str, new: str, confirm: str) -> User:
    user = user_for_reset_token(session, token)
    if user is None:
        raise CreditBridgeError("재설정 링크가 만료됐거나 이미 사용됐어요. 다시 요청해 주세요.")
    _check_new(new, confirm)
    user.password_hash = _hasher.hash(new)
    user.must_change_password = False
    user.failed_logins, user.locked_until = 0, None
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
    user.failed_logins, user.locked_until = 0, None
    audit.record(session, admin, "account.password_reset_by_admin", "user", str(user.id))
    session.commit()
    return user, password
