from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.i18n import COOKIE, get_locale, normalize, set_locale
from backend.security import session as auth_session
from backend.security.csrf import check_csrf
from backend.services import audit, notifications
from backend.services.auth import login_attempt, remember_locale
from backend.services.auth import set_locale as save_locale
from backend.web.templating import render
from backend.workers import tasks

router = APIRouter()

HOME = {"student": "/student", "evaluator": "/review", "professor": "/professor", "admin": "/admin/stats"}


@router.get("/")
def home(request: Request, session: Session = Depends(get_db)) -> Response:
    try:
        user = auth_session.current_user(request, session)
    except auth_session.LoginRequired:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse(HOME.get(user.role, "/login"), status_code=303)


@router.get("/login")
def login_form(request: Request) -> Response:
    return render(request, "login.html")


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    attempt = login_attempt(session, email, password)
    if attempt.send_reset_to is not None and notifications.email_enabled():
        tasks.send_password_reset.delay(attempt.send_reset_to, kind="lockout")
    user = attempt.user
    if user is None:
        return render(request, "login.html", status_code=attempt.status_code, error=attempt.error, email=email)
    auth_session.login(request, user)
    audit.record(session, user, "auth.login", "user", str(user.id))
    locale = remember_locale(user, get_locale())
    session.commit()
    target = auth_session.PASSWORD_PAGE if user.must_change_password else HOME.get(user.role, "/")
    response = RedirectResponse(target, status_code=303)
    set_language_cookie(response, locale)
    return response


def set_language_cookie(response: Response, locale: str) -> None:
    response.set_cookie(COOKIE, locale, max_age=60 * 60 * 24 * 365, samesite="lax", httponly=True)


@router.post("/lang")
def switch_language(
    request: Request,
    lang: str = Form(...),
    next: str = Form("/"),
    csrf_token: str = Form(""),
    session: Session = Depends(get_db),
) -> Response:
    """화면 위 언어 전환 (한국어·English). 로그인했으면 계정 언어(알림·메일)도 바꾼다."""
    check_csrf(request, csrf_token)
    locale = normalize(lang)
    if locale is None:
        return RedirectResponse("/", status_code=303)
    try:
        user = auth_session.current_user(request, session)
    except (auth_session.LoginRequired, auth_session.PasswordChangeRequired):
        user = None
    if user is not None:
        save_locale(session, user, locale)
    set_locale(locale)
    # 같은 사이트 안의 경로로만 돌아간다 (열린 리다이렉트 방지)
    target = next if next.startswith("/") and not next.startswith("//") and "\\" not in next else "/"
    response = RedirectResponse(target, status_code=303)
    set_language_cookie(response, locale)
    return response


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form("")) -> Response:
    check_csrf(request, csrf_token)
    auth_session.logout(request)
    return RedirectResponse("/login", status_code=303)
