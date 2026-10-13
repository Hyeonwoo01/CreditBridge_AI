from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.security.session import current_user
from app.services import notifications
from app.web.templating import render

router = APIRouter(prefix="/notifications")


@router.get("")
def inbox(request: Request, user: User = Depends(current_user), session: Session = Depends(get_db)) -> Response:
    return render(request, "notifications.html", user=user, items=notifications.inbox(session, user))


@router.get("/count")
def count(user: User = Depends(current_user), session: Session = Depends(get_db)) -> Response:
    """헤더 알림 배지 (HTMX가 주기적으로 불러온다)."""
    n = notifications.unread_count(session, user)
    badge = f'<span class="notify-count">{n if n < 100 else "99+"}</span>' if n else ""
    return HTMLResponse(badge)
