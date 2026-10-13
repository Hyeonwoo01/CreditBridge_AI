from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.security.session import current_user
from app.services import views
from app.web.templating import render

router = APIRouter()


@router.get("/evaluations/{public_id}/report")
def report(
    request: Request, public_id: str, user: User = Depends(current_user), session: Session = Depends(get_db)
) -> Response:
    """판정 근거 리포트 (FR-23): 판정자·일시·AI 추천값·근거 구절·사람 판정 사유."""
    view = views.evaluation_view(session, user, public_id, with_audit=True)
    return render(request, "report.html", user=user, v=view)
