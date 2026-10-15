from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models import User
from backend.security.session import current_user
from backend.services import views
from backend.web.templating import render

router = APIRouter()


@router.get("/evaluations/{evaluation_id}/report")
def report(
    request: Request, evaluation_id: int, user: User = Depends(current_user), session: Session = Depends(get_db)
) -> Response:
    """판정 근거 리포트 (FR-23): 판정자·일시·AI 추천값·근거 구절·사람 판정 사유."""
    view = views.evaluation_view(session, user, evaluation_id, with_audit=True)
    return render(request, "report.html", user=user, v=view)
