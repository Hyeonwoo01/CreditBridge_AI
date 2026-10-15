import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy.orm import Session

from backend.errors import CreditBridgeError
from backend.models import User
from backend.repositories import users as user_repo
from backend.services import audit

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


def change_password(session: Session, user: User, current: str, new: str, confirm: str) -> None:
    """현재 비밀번호를 확인하고 바꾼다. 임시 비밀번호로 만든 계정은 여기서 변경 표시가 풀린다."""
    try:
        _hasher.verify(user.password_hash, current)
    except (VerificationError, InvalidHashError):
        raise CreditBridgeError("현재 비밀번호가 맞지 않아요.") from None
    if len(new) < MIN_PASSWORD_LENGTH:
        raise CreditBridgeError(f"새 비밀번호는 {MIN_PASSWORD_LENGTH}자 이상으로 정해 주세요.")
    if new == current:
        raise CreditBridgeError("지금과 다른 비밀번호로 정해 주세요.")
    if new != confirm:
        raise CreditBridgeError("새 비밀번호 확인이 일치하지 않아요.")
    user.password_hash = _hasher.hash(new)
    user.must_change_password = False
    audit.record(session, user, "auth.password_change", "user", str(user.id))
    session.commit()
