"""상단 메뉴 숫자 배지: 화면을 그릴 때 한 번만 계산하도록 request.state에 지연 계산 함수를 둔다."""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models import User
from backend.security.session import current_user
from backend.services import views


def nav_badges(request: Request, user: User = Depends(current_user), session: Session = Depends(get_db)) -> None:
    if request.method != "GET":
        return
    cache: list[dict[str, list[views.Badge]]] = []

    def badges() -> dict[str, list[views.Badge]]:
        if not cache:
            cache.append(views.nav_badges(session, user))
        return cache[0]

    request.state.nav_badges = badges
