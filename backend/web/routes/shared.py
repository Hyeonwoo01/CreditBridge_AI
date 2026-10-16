import re
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.db.session import get_db
from backend.documents.pdf import html_to_pdf
from backend.documents.storage import get_storage
from backend.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from backend.i18n import gettext as tr
from backend.models import User
from backend.models.enums import Role
from backend.security.csrf import check_csrf
from backend.security.session import current_user
from backend.services import appeals as appeal_service
from backend.services import notes as note_service
from backend.services import originals, views
from backend.web.nav import nav_badges
from backend.web.templating import TEMPLATES, flash, render

LOGO_DIR = Path(__file__).resolve().parents[3] / "frontend" / "static" / "img"
EVALUATION_PAGES = {Role.EVALUATOR: "/review/evaluations/", Role.PROFESSOR: "/professor/evaluations/"}

router = APIRouter()


@router.get("/evaluations/{evaluation_id}/report", dependencies=[Depends(nav_badges)])
def report(
    request: Request, evaluation_id: int, user: User = Depends(current_user), session: Session = Depends(get_db)
) -> Response:
    """판정 근거 리포트 (FR-23): 판정자·일시·AI 추천값·근거 구절·사람 판정 사유."""
    view = views.evaluation_view(session, user, evaluation_id, with_audit=True)
    return render(request, "report.html", user=user, v=view)


@router.get("/evaluations/{evaluation_id}/report.pdf")
def report_pdf(evaluation_id: int, user: User = Depends(current_user), session: Session = Depends(get_db)) -> Response:
    """판정 근거 리포트 PDF 내려받기: 화면 리포트와 같은 내용, 같은 권한."""
    view = views.evaluation_view(session, user, evaluation_id, with_audit=True)
    html = TEMPLATES.get_template("report_pdf.html").render(v=view, generated_at=utcnow())
    code = re.sub(r"[^A-Za-z0-9]+", "", view.syllabus.course_code) or "course"
    pdf = html_to_pdf(
        html,
        title=f"Transfer Credit Evaluation Report #{evaluation_id}",
        footer=tr(
            "CreditBridge AI 판정 근거 리포트 #{evaluation_id} · AI는 추천만 하고 최종 판정은 학과 교수가 합니다.",
            evaluation_id=evaluation_id,
        ),
        assets=LOGO_DIR,
    )
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="creditbridge-report-{code}-{evaluation_id}.pdf"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/evaluations/{evaluation_id}/original/{side}")
def original(
    evaluation_id: int, side: str, user: User = Depends(current_user), session: Session = Depends(get_db)
) -> Response:
    """근거 구절의 원본 파일 (FR-25). 브라우저에서 바로 열고, PDF는 주소 끝 #page=N으로 그 쪽을 연다."""
    file = originals.open_original(session, user, evaluation_id, side)
    return Response(
        get_storage().get(file.file_key),
        media_type=file.content_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(file.filename)}",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/evaluations/{evaluation_id}/notes")
def add_note(
    request: Request,
    evaluation_id: int,
    body: str = Form(""),
    csrf_token: str = Form(""),
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> Response:
    """심사 건 내부 메모 남기기 (심사관·담당 교수)."""
    check_csrf(request, csrf_token)
    try:
        note_service.add(session, user, evaluation_id, body)
    except (NotFoundError, PermissionDeniedError):
        raise
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
    else:
        flash(request, tr("메모를 남겼어요. 학생에게는 보이지 않아요."))
    return RedirectResponse(f"{EVALUATION_PAGES[Role(user.role)]}{evaluation_id}#notes", status_code=303)


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
