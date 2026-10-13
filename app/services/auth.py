from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import users as user_repo

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
