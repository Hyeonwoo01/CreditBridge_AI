import csv
import io

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.session import get_db
from backend.documents.storage import get_storage
from backend.errors import CreditBridgeError
from backend.i18n import gettext as tr
from backend.models import User
from backend.models.enums import Role
from backend.security.csrf import check_csrf
from backend.security.session import require
from backend.services import appeals as appeal_service
from backend.services import equivalencies as equivalency_service
from backend.services import materials as material_service
from backend.services import privacy as privacy_service
from backend.services import review as review_service
from backend.services import sis as sis_service
from backend.services import stats as stats_service
from backend.services import student as student_service
from backend.services import views
from backend.services.csv_import import safe_cell
from backend.web.nav import nav_badges
from backend.web.notify import send_notifications
from backend.web.templating import flash, render
from backend.workers import tasks

router = APIRouter(prefix="/review", dependencies=[Depends(nav_badges)])
Evaluator = Depends(require(Role.EVALUATOR))


@router.get("")
def queue(
    request: Request,
    tab: str = Query("all", pattern="^(all|high|low|insufficient|conflict)$"),
    department: str = Query(""),
    sort: str = Query("submitted", pattern="^(submitted|coverage|department)$"),
    q: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
    user: User = Evaluator,
    session: Session = Depends(get_db),
) -> Response:
    view = review_service.queue(session, user, tab, department or None, sort, q, page)
    return render(
        request,
        "review/queue.html",
        user=user,
        view=view,
        tab=tab,
        tabs=review_service.TABS,
        department=department,
        sort=sort,
        q=q,
        stats=stats_service.institution_stats(session, user),
    )


@router.post("/assign")
def assign(
    request: Request,
    evaluation_ids: list[int] = Form([]),
    tab: str = Form("all"),
    csrf_token: str = Form(""),
    user: User = Evaluator,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    if not evaluation_ids:
        flash(request, tr("배정할 건을 선택해 주세요."), "error")
    else:
        count, problems = review_service.auto_assign(session, user, evaluation_ids)
        send_notifications()
        flash(request, tr("{count}건을 학과 담당 교수에게 배정했어요. 근거 요약이 함께 전달돼요.", count=count))
        for p in problems:
            flash(request, p, "error")
    return RedirectResponse(f"/review?tab={tab}", status_code=303)


@router.get("/evaluations/{evaluation_id}")
def evaluation_page(
    request: Request, evaluation_id: int, user: User = Evaluator, session: Session = Depends(get_db)
) -> Response:
    view = views.evaluation_view(session, user, evaluation_id, with_audit=True)
    options = review_service.assign_options(session, user, view.evaluation, view.request)
    return render(request, "review/evaluation.html", user=user, v=view, assign=options)


@router.post("/evaluations/{evaluation_id}/assign")
def assign_one(
    request: Request,
    evaluation_id: int,
    reviewer_id: int = Form(...),
    csrf_token: str = Form(""),
    user: User = Evaluator,
    session: Session = Depends(get_db),
) -> Response:
    """심사관이 교수를 골라 배정하거나 바꾼다 (후보 과목이 없어 학과로 자동 배정할 수 없는 건 포함)."""
    check_csrf(request, csrf_token)
    try:
        reviewer = review_service.assign_to(session, user, evaluation_id, reviewer_id)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
    else:
        send_notifications()
        flash(request, tr("{name} 교수에게 배정했어요.", name=reviewer.name))
    return RedirectResponse(f"/review/evaluations/{evaluation_id}", status_code=303)


@router.get("/export.csv")
def export_csv(user: User = Evaluator, session: Session = Depends(get_db)) -> Response:
    rows = views.export_rows(session, user)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=sis_service.FIELDS)
    writer.writeheader()
    writer.writerows({key: safe_cell(value) for key, value in row.items()} for row in rows)
    return Response(
        buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=decisions.csv", "Cache-Control": "no-store"},
    )


@router.post("/evaluations/{evaluation_id}/materials")
def request_materials(
    request: Request,
    evaluation_id: int,
    items: list[str] = Form([]),
    note: str = Form(""),
    csrf_token: str = Form(""),
    user: User = Evaluator,
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
        flash(request, tr("학생에게 보완 자료를 요청했어요. 자료가 오면 알림으로 알려 드려요."))
    return RedirectResponse(f"/review/evaluations/{evaluation_id}", status_code=303)


@router.post("/evaluations/{evaluation_id}/supplement")
def upload_supplement(
    request: Request,
    evaluation_id: int,
    file: UploadFile = File(...),
    csrf_token: str = Form(""),
    user: User = Evaluator,
    session: Session = Depends(get_db),
) -> Response:
    """학생 대신 보완 자료 올리기 (권한 매트릭스: 문서 업로드는 심사관 소속 기관 전체). 올리면 다시 분석한다."""
    check_csrf(request, csrf_token)
    try:
        if not file.filename:
            raise CreditBridgeError(tr("보완 자료 파일을 선택해 주세요."))
        uploaded = student_service.UploadedFile(filename=file.filename, data=file.file.read())
        syllabus, key = student_service.store_supplement_by_staff(session, get_storage(), user, evaluation_id, uploaded)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
        return RedirectResponse(f"/review/evaluations/{evaluation_id}#supplement", status_code=303)
    tasks.add_supplement.delay(syllabus.id, key)
    send_notifications()
    flash(
        request,
        tr("보완 자료를 올렸어요. 다시 분석한 결과는 심사 큐와 학생 화면에 반영돼요. 이전 결과는 기록으로 남아요."),
    )
    return RedirectResponse("/review", status_code=303)


@router.get("/appeals")
def appeals(request: Request, user: User = Evaluator, session: Session = Depends(get_db)) -> Response:
    return render(request, "review/appeals.html", user=user, rows=appeal_service.rows(session, user))


@router.post("/appeals/{appeal_id}")
def handle_appeal(
    request: Request,
    appeal_id: int,
    action: str = Form(...),
    reviewer_id: str = Form(""),
    note: str = Form(""),
    csrf_token: str = Form(""),
    user: User = Evaluator,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    try:
        if action == "accept":
            appeal_service.accept(session, user, appeal_id, int(reviewer_id) if reviewer_id.isdigit() else None, note)
            flash(request, tr("이의 신청을 받아들여 학과 교수에게 재판정을 배정했어요."))
        elif action == "dismiss":
            appeal_service.dismiss(session, user, appeal_id, note)
            flash(request, tr("이의 신청을 기각하고 학생에게 사유를 알렸어요."))
        else:
            raise CreditBridgeError(tr("처리 방법을 선택해 주세요."))
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
    else:
        send_notifications()
    return RedirectResponse("/review/appeals", status_code=303)


@router.get("/privacy")
def privacy_requests(request: Request, user: User = Evaluator, session: Session = Depends(get_db)) -> Response:
    return render(request, "privacy.html", user=user, rows=privacy_service.rows(session, user))


@router.post("/privacy/{privacy_id}")
def review_privacy(
    request: Request,
    privacy_id: int,
    csrf_token: str = Form(""),
    user: User = Evaluator,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    try:
        privacy_service.review(session, user, privacy_id)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
    else:
        send_notifications()
        flash(request, tr("처리 완료로 표시했어요. 기관 관리자가 승인하면 삭제돼요."))
    return RedirectResponse("/review/privacy", status_code=303)


@router.get("/equivalencies")
def equivalencies(
    request: Request,
    q: str = "",
    result: str = "",
    page: int = 1,
    user: User = Evaluator,
    session: Session = Depends(get_db),
) -> Response:
    """기관 동등 과목표: CSV 가져오기와 전체 이력 검색 (출신 과목·출신 대학·대상 과목, 판정 결과, 50건씩)."""
    return render(
        request,
        "review/equivalencies.html",
        user=user,
        view=equivalency_service.search(session, user, q, result, page),
        columns=equivalency_service.COLUMNS,
    )


@router.post("/equivalencies")
def import_equivalencies(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(""),
    user: User = Evaluator,
    session: Session = Depends(get_db),
) -> Response:
    """기존 동등 과목표 CSV 가져오기 (FR-26)."""
    check_csrf(request, csrf_token)
    try:
        result = equivalency_service.import_csv(session, user, file.filename or "", file.file.read())
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
        return RedirectResponse("/review/equivalencies", status_code=303)
    if result.errors:
        return render(
            request,
            "review/equivalencies.html",
            status_code=422,
            user=user,
            view=equivalency_service.search(session, user),
            columns=equivalency_service.COLUMNS,
            errors=result.errors,
        )
    flash(
        request, tr("동등 과목표 {imported}건을 가져왔어요. 과거 판정 이력에 함께 표시돼요.", imported=result.imported)
    )
    return RedirectResponse("/review/equivalencies", status_code=303)


@router.get("/stats")
def stats(request: Request, user: User = Evaluator, session: Session = Depends(get_db)) -> Response:
    return render(
        request,
        "stats.html",
        user=user,
        s=stats_service.institution_stats(session, user),
        reminders=views.reminder_preview(session, user),
        reminder_hour=get_settings().reminder_hour_utc,
    )
