from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.security import session as auth_session
from backend.security.csrf import check_csrf
from backend.services import audit, notifications
from backend.services.auth import login_attempt
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
    session.commit()
    if user.must_change_password:
        return RedirectResponse(auth_session.PASSWORD_PAGE, status_code=303)
    return RedirectResponse(HOME.get(user.role, "/"), status_code=303)


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form("")) -> Response:
    check_csrf(request, csrf_token)
    auth_session.logout(request)
    return RedirectResponse("/login", status_code=303)
