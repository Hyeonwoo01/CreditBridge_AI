from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.errors import CreditBridgeError
from backend.models import User
from backend.security.csrf import check_csrf
from backend.security.session import current_user
from backend.services.auth import MIN_PASSWORD_LENGTH, change_password
from backend.web.routes.auth import HOME
from backend.web.templating import flash, render

router = APIRouter(prefix="/account")


@router.get("/password")
def password_form(request: Request, user: User = Depends(current_user)) -> Response:
    return render(request, "account/password.html", user=user, min_length=MIN_PASSWORD_LENGTH)


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
        change_password(session, user, current, new, confirm)
    except CreditBridgeError as exc:
        session.rollback()
        return render(
            request, "account/password.html", status_code=422, user=user, min_length=MIN_PASSWORD_LENGTH, error=str(exc)
        )
    flash(request, "비밀번호를 바꿨어요.")
    return RedirectResponse(HOME.get(user.role, "/"), status_code=303)
