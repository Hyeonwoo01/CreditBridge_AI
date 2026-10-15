from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.errors import CreditBridgeError
from backend.models import User
from backend.security import session as auth_session
from backend.security.csrf import check_csrf
from backend.security.session import current_user
from backend.services import auth, notifications
from backend.web.nav import student_badges
from backend.web.routes.auth import HOME
from backend.web.templating import flash, render
from backend.workers import tasks

router = APIRouter(prefix="/account")


@router.get("/password", dependencies=[Depends(student_badges)])
def password_form(request: Request, user: User = Depends(current_user)) -> Response:
    return render(request, "account/password.html", user=user, min_length=auth.MIN_PASSWORD_LENGTH)


@router.post("/password")
def password_change(
    request: Request,
    current: str = Form(...),
    new: str = Form(...),
    confirm: str = Form(...),
    csrf_token: str = Form(""),
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    try:
        auth.change_password(session, user, current, new, confirm)
    except CreditBridgeError as exc:
        session.rollback()
        return render(
            request,
            "account/password.html",
            status_code=422,
            user=user,
            min_length=auth.MIN_PASSWORD_LENGTH,
            error=str(exc),
        )
    auth_session.login(request, user)  # 이 기기는 로그인을 유지하고, 다른 기기의 세션은 끊긴다
    flash(request, "비밀번호를 바꿨어요. 다른 기기에 로그인돼 있었다면 다시 로그인해야 해요.")
    return RedirectResponse(HOME.get(user.role, "/"), status_code=303)


# ---------- 비밀번호를 잊었을 때 ----------


def _no_trace(response: Response) -> Response:
    """재설정 화면은 캐시하지 않고, 외부 글꼴 요청에 주소(토큰)가 Referer로 새지 않게 한다."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get("/forgot")
def forgot_form(request: Request) -> Response:
    return render(request, "account/forgot.html", email_enabled=notifications.email_enabled())


@router.post("/forgot")
def forgot(
    request: Request,
    email: str = Form(...),
    csrf_token: str = Form(""),
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    if notifications.email_enabled():
        user_id = auth.request_reset(session, email)
        if user_id is not None:
            tasks.send_password_reset.delay(user_id)
    # 계정이 있는지 알려주지 않도록 항상 같은 안내를 보여준다
    return render(request, "account/forgot.html", email_enabled=notifications.email_enabled(), sent=True)


@router.get("/reset")
def reset_form(request: Request, token: str = Query(""), session: Session = Depends(get_db)) -> Response:
    valid = auth.user_for_reset_token(session, token) is not None
    return _no_trace(
        render(
            request,
            "account/reset.html",
            status_code=200 if valid else 400,
            token=token if valid else "",
            min_length=auth.MIN_PASSWORD_LENGTH,
        )
    )


@router.post("/reset")
def reset(
    request: Request,
    token: str = Form(...),
    new: str = Form(...),
    confirm: str = Form(...),
    csrf_token: str = Form(""),
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    try:
        auth.reset_password(session, token, new, confirm)
    except CreditBridgeError as exc:
        session.rollback()
        still_valid = auth.user_for_reset_token(session, token) is not None
        return _no_trace(
            render(
                request,
                "account/reset.html",
                status_code=422,
                token=token if still_valid else "",
                min_length=auth.MIN_PASSWORD_LENGTH,
                error=str(exc),
            )
        )
    auth_session.logout(request)
    flash(request, "비밀번호를 바꿨어요. 새 비밀번호로 로그인해 주세요.")
    return RedirectResponse("/login", status_code=303)
