from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.session import get_db
from backend.i18n import gettext as tr
from backend.models import User
from backend.security.csrf import check_csrf
from backend.security.session import current_user
from backend.services import notifications, push
from backend.services import stats as stats_service
from backend.web.nav import nav_badges
from backend.web.templating import render

router = APIRouter(prefix="/notifications")


@router.get("", dependencies=[Depends(nav_badges)])
def inbox(
    request: Request, page: int = 1, user: User = Depends(current_user), session: Session = Depends(get_db)
) -> Response:
    view = notifications.inbox(session, user, page)
    return render(
        request,
        "notifications.html",
        user=user,
        items=view.items,
        view=view,
        push_key=get_settings().vapid_public_key if push.push_enabled() else "",
        push_devices=push.device_count(session, user),
    )


@router.post("/push/subscribe")
def push_subscribe(
    request: Request,
    body: Annotated[dict[str, Any], Body()],
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> Response:
    """이 기기에서 웹 푸시 받기 (FR-20). 화면 스크립트가 브라우저 구독 정보를 X-CSRF-Token 헤더와 함께 보낸다."""
    check_csrf(request, None)
    try:
        push.subscribe(session, user, body)
    except push.PushSubscriptionError as exc:
        session.rollback()
        return JSONResponse({"detail": str(exc)}, status_code=422)
    return JSONResponse({"devices": push.device_count(session, user)})


@router.post("/push/unsubscribe")
def push_unsubscribe(
    request: Request,
    body: Annotated[dict[str, Any], Body()],
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> Response:
    """이 기기의 웹 푸시 끄기."""
    check_csrf(request, None)
    push.unsubscribe(session, user, str(body.get("endpoint", "")))
    return JSONResponse({"devices": push.device_count(session, user)})


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
