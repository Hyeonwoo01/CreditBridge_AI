from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.documents.storage import get_storage
from app.errors import CreditBridgeError
from app.models import User
from app.models.enums import Role
from app.security.csrf import check_csrf
from app.security.session import require
from app.services import privacy as privacy_service
from app.services import sis as sis_service
from app.services import stats as stats_service
from app.services import views
from app.web.notify import send_emails
from app.web.templating import flash, render

router = APIRouter(prefix="/admin")
Admin = Depends(require(Role.ADMIN))


@router.get("/audit")
def audit_log(request: Request, user: User = Admin, session: Session = Depends(get_db)) -> Response:
    return render(request, "admin/audit.html", user=user, logs=views.recent_audit(session))


@router.get("/stats")
def stats(request: Request, user: User = Admin, session: Session = Depends(get_db)) -> Response:
    """운영 통계 (FR-27)."""
    return render(request, "stats.html", user=user, s=stats_service.institution_stats(session, user))


@router.get("/privacy")
def privacy_requests(request: Request, user: User = Admin, session: Session = Depends(get_db)) -> Response:
    return render(request, "privacy.html", user=user, rows=privacy_service.rows(session, user))


@router.post("/privacy/{privacy_id}")
def approve_privacy(
    request: Request,
    privacy_id: int,
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """삭제 승인: 승인 즉시 원본 파일과 추출 텍스트를 지운다 (FR-13)."""
    check_csrf(request, csrf_token)
    try:
        privacy_service.approve(session, user, get_storage(), privacy_id)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
    else:
        send_emails()
        flash(request, "삭제를 승인했어요. 원본 파일과 추출 텍스트를 지웠어요.")
    return RedirectResponse("/admin/privacy", status_code=303)


@router.get("/sis")
def sis(request: Request, user: User = Admin, session: Session = Depends(get_db)) -> Response:
    return render(request, "admin/sis.html", user=user, has_token=sis_service.has_token(session, user))


@router.post("/sis")
def sis_token(
    request: Request,
    action: str = Form(...),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """학사정보시스템 연동 토큰 발급·폐기 (FR-24). 토큰 원문은 발급 화면에서 한 번만 보여준다."""
    check_csrf(request, csrf_token)
    if action == "revoke":
        sis_service.revoke_token(session, user)
        flash(request, "연동 토큰을 폐기했어요. 이 토큰으로는 더 이상 내보낼 수 없어요.")
        return RedirectResponse("/admin/sis", status_code=303)
    token = sis_service.issue_token(session, user)
    return render(request, "admin/sis.html", user=user, has_token=True, token=token)
