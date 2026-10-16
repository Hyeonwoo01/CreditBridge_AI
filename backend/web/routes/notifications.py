from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.i18n import gettext as tr
from backend.models import User
from backend.security.session import current_user
from backend.services import notifications
from backend.services import stats as stats_service
from backend.web.nav import nav_badges
from backend.web.templating import render

router = APIRouter(prefix="/notifications")


@router.get("", dependencies=[Depends(nav_badges)])
def inbox(request: Request, user: User = Depends(current_user), session: Session = Depends(get_db)) -> Response:
    return render(request, "notifications.html", user=user, items=notifications.inbox(session, user))


@router.get("/count")
def count(user: User = Depends(current_user), session: Session = Depends(get_db)) -> Response:
    """헤더 알림 배지 (HTMX가 주기적으로 불러온다)."""
    n = notifications.unread_count(session, user)
    badge = f'<span class="notify-count">{n if n < 100 else "99+"}</span>' if n else ""
    return HTMLResponse(badge)


@router.get("/workspace")
def workspace(user: User = Depends(current_user), session: Session = Depends(get_db)) -> Response:
    """상단 보조 바의 기관 집계 조각 (HTMX)."""
    counts = stats_service.workspace_counts(session, user)
    if counts is None:
        return HTMLResponse("")
    chips = [
        (tr("제출 요청"), counts.submitted, ""),
        (tr("심사 대기"), counts.waiting, ""),
        (tr("판정 완료"), counts.decided, "approve"),
    ]
    html = "".join(
        f'<span class="chip-count{" chip-count-" + tone if tone else ""}">{label} <b>{value}</b></span>'
        for label, value, tone in chips
    )
    return HTMLResponse(html)
