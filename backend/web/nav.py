"""학생 메뉴 배지: 화면을 그릴 때 한 번만 계산하도록 request.state에 지연 계산 함수를 둔다."""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models import User
from backend.models.enums import Role
from backend.security.session import current_user
from backend.services import views


def student_badges(request: Request, user: User = Depends(current_user), session: Session = Depends(get_db)) -> None:
    if request.method == "GET" and user.role == Role.STUDENT:
        cache: list[views.StudentBadges] = []

        def badges() -> views.StudentBadges:
            if not cache:
                cache.append(views.student_badges(session, user))
            return cache[0]

        request.state.student_badges = badges
