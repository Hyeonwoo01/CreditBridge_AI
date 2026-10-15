from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.documents.storage import get_storage
from backend.models import User
from backend.security.session import current_user
from backend.services import appeals as appeal_service
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


@router.get("/appeal-files/{file_id}")
def appeal_file(file_id: int, user: User = Depends(current_user), session: Session = Depends(get_db)) -> Response:
    """이의 신청 근거 자료 내려받기: 학생 본인, 소속 심사관, 담당 학과 교수만."""
    file = appeal_service.file_for_download(session, user, file_id)
    assert file.file_key is not None
    return Response(
        get_storage().get(file.file_key),
        media_type=file.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file.original_filename)}",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
