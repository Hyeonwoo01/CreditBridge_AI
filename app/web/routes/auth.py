from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security import session as auth_session
from app.security.csrf import check_csrf
from app.services import audit
from app.services.auth import authenticate
from app.web.templating import render

router = APIRouter()

HOME = {"student": "/student", "evaluator": "/review", "professor": "/professor", "admin": "/admin/audit"}


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
    user = authenticate(session, email, password)
    if user is None:
        return render(request, "login.html", status_code=401, error="이메일 또는 비밀번호가 맞지 않아요.", email=email)
    auth_session.login(request, user)
    audit.record(session, user, "auth.login", "user", user.public_id)
    session.commit()
    return RedirectResponse(HOME.get(user.role, "/"), status_code=303)


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form("")) -> Response:
    check_csrf(request, csrf_token)
    auth_session.logout(request)
    return RedirectResponse("/login", status_code=303)
