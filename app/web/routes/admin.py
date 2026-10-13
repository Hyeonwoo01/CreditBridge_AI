from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.models.enums import Role
from app.security.session import require
from app.services import views
from app.web.templating import render

router = APIRouter(prefix="/admin")
Admin = Depends(require(Role.ADMIN))


@router.get("/audit")
def audit_log(request: Request, user: User = Admin, session: Session = Depends(get_db)) -> Response:
    return render(request, "admin/audit.html", user=user, logs=views.recent_audit(session))
