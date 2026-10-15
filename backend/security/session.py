"""서명 쿠키 세션 기반 현재 사용자."""

import hashlib

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.errors import PermissionDeniedError
from backend.models import User
from backend.models.enums import Role
from backend.repositories import users as user_repo


class LoginRequired(Exception):
    pass


class PasswordChangeRequired(Exception):
    """임시 비밀번호 계정은 비밀번호를 바꾸기 전까지 다른 화면을 쓸 수 없다."""


PASSWORD_PAGE = "/account/password"
_ALLOWED_BEFORE_CHANGE = {PASSWORD_PAGE, "/logout"}


def password_fingerprint(user: User) -> str:
    """비밀번호 해시에서 뽑은 짧은 값. 비밀번호가 바뀌면 달라져 이전 세션·재설정 링크가 무효가 된다."""
    return hashlib.sha256(user.password_hash.encode()).hexdigest()[:16]


def current_user(request: Request, session: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    user = user_repo.get_by_id(session, int(user_id)) if user_id else None
    if user is None or request.session.get("pwd") != password_fingerprint(user):
        # 다른 곳에서 비밀번호를 바꾸거나 재설정했으면 이 세션은 끊는다
        request.session.clear()
        raise LoginRequired
    if user.must_change_password and request.url.path not in _ALLOWED_BEFORE_CHANGE:
        raise PasswordChangeRequired
    return user


def require(*roles: Role):  # type: ignore[no-untyped-def]
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise PermissionDeniedError("이 화면을 사용할 권한이 없어요.")
        return user

    return dependency


def login(request: Request, user: User) -> None:
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["pwd"] = password_fingerprint(user)


def logout(request: Request) -> None:
    request.session.clear()
