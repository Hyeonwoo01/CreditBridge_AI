from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.errors import CreditBridgeError, DecisionValidationError
from backend.i18n import gettext as tr
from backend.models import User
from backend.models.enums import Role
from backend.security.csrf import check_csrf
from backend.security.session import require
from backend.services import decisions as decision_service
from backend.services import evidence_feedback as feedback_service
from backend.services import materials as material_service
from backend.services import review as review_service
from backend.services import views
from backend.web.nav import nav_badges
from backend.web.notify import send_notifications
from backend.web.templating import flash, render

router = APIRouter(prefix="/professor", dependencies=[Depends(nav_badges)])
Professor = Depends(require(Role.PROFESSOR))


@router.get("")
def index(request: Request, user: User = Professor, session: Session = Depends(get_db)) -> Response:
    return render(
        request,
        "professor/index.html",
        user=user,
        items=views.professor_items(session, user),
        colleagues=views.colleagues(session, user),
    )


@router.get("/evaluations/{evaluation_id}")
def evaluation_page(
    request: Request, evaluation_id: int, user: User = Professor, session: Session = Depends(get_db)
) -> Response:
    view = views.evaluation_view(session, user, evaluation_id)
    return render(request, "professor/evaluation.html", user=user, v=view)


@router.post("/evaluations/{evaluation_id}/decision")
def decide(
    request: Request,
    evaluation_id: int,
    action: str = Form(...),
    result: str = Form(""),
    target_course_id: str = Form(""),
    reason_codes: list[str] = Form([]),
    reason_memo: str = Form(""),
    acknowledge_conflict: bool = Form(False),
    csrf_token: str = Form(""),
    user: User = Professor,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    form = {
        "action": action,
        "result": result,
        "target_course_id": target_course_id,
        "reason_codes": reason_codes,
        "reason_memo": reason_memo,
    }
    try:
        decision_service.decide(
            session,
            user,
            evaluation_id,
            action,
            result or None,
            int(target_course_id) if target_course_id.isdigit() else None,
            reason_codes,
            reason_memo,
            acknowledge_conflict,
        )
    except decision_service.ConflictNeedsAcknowledgement as exc:
        session.rollback()
        view = views.evaluation_view(session, user, evaluation_id)
        return render(
            request, "professor/evaluation.html", status_code=409, user=user, v=view, conflict=str(exc), form=form
        )
    except DecisionValidationError as exc:
        session.rollback()
        view = views.evaluation_view(session, user, evaluation_id)
        return render(
            request, "professor/evaluation.html", status_code=422, user=user, v=view, error=str(exc), form=form
        )
    send_notifications()
    flash(request, tr("판정을 확정했어요. 학생 포털과 내보내기에 바로 반영돼요."))
    return RedirectResponse("/professor", status_code=303)


@router.post("/evaluations/{evaluation_id}/evidence/{span_id}")
def evidence_feedback(
    request: Request,
    evaluation_id: int,
    span_id: int,
    verdict: str = Form(""),
    csrf_token: str = Form(""),
    user: User = Professor,
    session: Session = Depends(get_db),
) -> Response:
    """근거 구절 맞음·틀림 (AI 근거 정확도 측정). HTMX면 버튼만 다시 그린다."""
    check_csrf(request, csrf_token)
    saved = feedback_service.record(session, user, evaluation_id, span_id, verdict)
    if request.headers.get("HX-Request"):
        return render(
            request,
            "partials/evidence_feedback.html",
            user=user,
            evaluation_id=evaluation_id,
            span_id=span_id,
            verdict=saved,
        )
    return RedirectResponse(f"/professor/evaluations/{evaluation_id}", status_code=303)


@router.post("/away")
def away(
    request: Request,
    days: int = Form(0),
    delegate_id: str = Form(""),
    csrf_token: str = Form(""),
    user: User = Professor,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    moved = review_service.set_away(session, user, days, int(delegate_id) if delegate_id.isdigit() else None)
    send_notifications()
    flash(
        request,
        tr("부재 기간을 저장했어요. 진행 중인 {moved}건을 대리 심사자에게 넘겼어요.", moved=moved)
        if days > 0
        else tr("복귀로 표시했어요."),
    )
    return RedirectResponse("/professor", status_code=303)


@router.post("/evaluations/{evaluation_id}/materials")
def request_materials(
    request: Request,
    evaluation_id: int,
    items: list[str] = Form([]),
    note: str = Form(""),
    csrf_token: str = Form(""),
    user: User = Professor,
    session: Session = Depends(get_db),
) -> Response:
    """보완 자료 요청 (FR-22)."""
    check_csrf(request, csrf_token)
    try:
        material_service.request_materials(session, user, evaluation_id, items, note)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
    else:
        send_notifications()
        flash(request, tr("학생에게 보완 자료를 요청했어요. 자료가 오면 다시 분석한 결과로 이어서 판정할 수 있어요."))
    return RedirectResponse(f"/professor/evaluations/{evaluation_id}", status_code=303)
