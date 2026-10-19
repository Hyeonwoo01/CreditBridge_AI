import base64
import csv
import io
import re
from datetime import date

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
from backend.services import accounts as account_service
from backend.services import auth as auth_service
from backend.services import institution_data, notifications, views
from backend.services import privacy as privacy_service
from backend.services import review as review_service
from backend.services import sis as sis_service
from backend.services import stats as stats_service
from backend.web.nav import nav_badges
from backend.web.notify import send_notifications
from backend.web.templating import flash, render
from backend.workers import tasks

router = APIRouter(prefix="/admin", dependencies=[Depends(nav_badges)])
Admin = Depends(require(Role.ADMIN))


def _day(value: str) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


@router.get("/audit")
def audit_log(
    request: Request,
    action: str = Query("", max_length=50),
    target_type: str = Query("", max_length=50),
    target_id: str = Query("", max_length=36),
    since: str = Query("", max_length=10),
    until: str = Query("", max_length=10),
    page: int = Query(1, ge=1),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """감사 로그 (FR-10): 행위·대상·기간(UTC 날짜) 필터, 50건씩."""
    filters = stats_service.AuditFilter(
        action.strip(), target_type.strip(), target_id.strip(), _day(since), _day(until)
    )
    return render(request, "admin/audit.html", user=user, view=stats_service.audit_page(session, user, filters, page))


# ---------- 교수 배정 (권한 매트릭스: 관리자도 배정·재배정) ----------


@router.get("/assignments")
def assignments(
    request: Request,
    show: str = Query("unassigned", pattern="^(unassigned|all)$"),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """판정 전 심사 건의 담당 교수. AI 분석 결과(추천·커버리지)는 보여 주지 않는다."""
    return render(
        request, "admin/assignments.html", user=user, board=review_service.assignment_board(session, user, show)
    )


@router.post("/assignments/auto")
def auto_assign(
    request: Request,
    evaluation_ids: list[int] = Form([]),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """고른 건을 학과 담당 교수에게 자동 배정 (심사관 일괄 배정과 같은 규칙)."""
    check_csrf(request, csrf_token)
    if not evaluation_ids:
        flash(request, tr("배정할 건을 선택해 주세요."), "error")
    else:
        count, problems = review_service.auto_assign(session, user, evaluation_ids)
        send_notifications()
        flash(request, tr("{count}건을 학과 담당 교수에게 배정했어요.", count=count))
        for p in problems:
            flash(request, p, "error")
    return RedirectResponse("/admin/assignments", status_code=303)


@router.post("/assignments/{evaluation_id}")
def assign_one(
    request: Request,
    evaluation_id: int,
    reviewer_id: int = Form(...),
    show: str = Form("unassigned"),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """한 건을 고른 교수에게 배정하거나 바꾼다."""
    check_csrf(request, csrf_token)
    try:
        reviewer = review_service.assign_to(session, user, evaluation_id, reviewer_id)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
    else:
        send_notifications()
        flash(request, tr("{name} 교수에게 배정했어요.", name=reviewer.name))
    return RedirectResponse(f"/admin/assignments?show={'all' if show == 'all' else 'unassigned'}", status_code=303)


# ---------- 계정 목록·수정 ----------


@router.get("/accounts")
def accounts(
    request: Request,
    q: str = Query("", max_length=100),
    role: str = Query(""),
    status: str = Query("active"),
    page: int = Query(1, ge=1),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """기관 계정 목록: 이메일 검색, 역할·상태 필터, 50건씩."""
    return render(
        request,
        "admin/accounts.html",
        user=user,
        view=account_service.list_accounts(session, user, q, role, status, page),
    )


@router.get("/accounts/{user_id}")
def account_page(request: Request, user_id: int, user: User = Admin, session: Session = Depends(get_db)) -> Response:
    return render(
        request,
        "admin/account_edit.html",
        user=user,
        form=account_service.account_form(session, user, user_id),
        email_enabled=notifications.email_enabled(),
    )


@router.post("/accounts/{user_id}")
def update_account(
    request: Request,
    user_id: int,
    name: str = Form(""),
    department_id: int | None = Form(None),
    delegate_user_id: int | None = Form(None),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """교직원 이름, 교수·심사관 학과, 교수 대리 심사자 수정 (역할은 바꾸지 않는다)."""
    check_csrf(request, csrf_token)
    try:
        changed = account_service.update_account(session, user, user_id, name, department_id, delegate_user_id)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
        return RedirectResponse(f"/admin/accounts/{user_id}", status_code=303)
    flash(request, tr("계정 정보를 저장했어요.") if changed else tr("바뀐 내용이 없어요."))
    return RedirectResponse(f"/admin/accounts/{user_id}", status_code=303)


@router.get("/stats")
def stats(request: Request, user: User = Admin, session: Session = Depends(get_db)) -> Response:
    """운영 통계 (FR-27)."""
    return render(
        request,
        "stats.html",
        user=user,
        s=stats_service.institution_stats(session, user),
        audit_rows=stats_service.recent_audit(session, user),
        retention_days=get_settings().privacy_deletion_days,
        reminders=views.reminder_preview(session, user),
        reminder_hour=get_settings().reminder_hour_utc,
    )


@router.get("/privacy")
def privacy_requests(request: Request, user: User = Admin, session: Session = Depends(get_db)) -> Response:
    return render(request, "privacy.html", user=user, rows=privacy_service.rows(session, user))


@router.post("/privacy/{privacy_id}")
def approve_privacy(
    request: Request,
    privacy_id: int,
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """삭제 승인: 승인 즉시 원본 파일과 추출 텍스트를 지운다 (FR-13)."""
    check_csrf(request, csrf_token)
    try:
        privacy_service.approve(session, user, get_storage(), privacy_id)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
    else:
        send_notifications()
        flash(request, tr("삭제를 승인했어요. 원본 파일과 추출 텍스트를 지웠어요."))
    return RedirectResponse("/admin/privacy", status_code=303)


@router.get("/sis")
def sis(request: Request, user: User = Admin, session: Session = Depends(get_db)) -> Response:
    return render(request, "admin/sis.html", user=user, has_token=sis_service.has_token(session, user))


@router.post("/sis")
def sis_token(
    request: Request,
    action: str = Form(...),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """학사정보시스템 연동 토큰 발급·폐기 (FR-24). 토큰 원문은 발급 화면에서 한 번만 보여준다."""
    check_csrf(request, csrf_token)
    if action == "revoke":
        sis_service.revoke_token(session, user)
        flash(request, tr("연동 토큰을 폐기했어요. 이 토큰으로는 더 이상 내보낼 수 없어요."))
        return RedirectResponse("/admin/sis", status_code=303)
    token = sis_service.issue_token(session, user)
    return render(request, "admin/sis.html", user=user, has_token=True, token=token)


# ---------- 기관 데이터: 계정·과목 CSV, 출신 대학, 기준 강의계획서 ----------


def _data_page(request: Request, user: User, session: Session, status_code: int = 200, **context: object) -> Response:
    return render(
        request,
        "admin/data.html",
        status_code=status_code,
        user=user,
        o=institution_data.overview(session, user),
        account_columns=institution_data.ACCOUNT_COLUMNS,
        course_columns=institution_data.COURSE_COLUMNS,
        email_enabled=notifications.email_enabled(),
        **context,
    )


@router.get("/data")
def data(request: Request, user: User = Admin, session: Session = Depends(get_db)) -> Response:
    return _data_page(request, user, session)


def _password_sheet(created: list[institution_data.CreatedAccount]) -> str:
    """임시 비밀번호 목록 CSV(엑셀용 BOM 포함)를 data URI로. 서버에는 남기지 않는다."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["email", "name", "role", "temporary_password"])
    for a in created:
        writer.writerow([a.email, a.name, a.role, a.temporary_password])
    encoded = base64.b64encode(("\ufeff" + out.getvalue()).encode()).decode()
    return f"data:text/csv;charset=utf-8;base64,{encoded}"


@router.post("/data/accounts")
def import_accounts(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    try:
        by_email = notifications.email_enabled()
        result = institution_data.import_accounts(session, user, file.filename or "", file.file.read(), by_email)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
        return RedirectResponse("/admin/data", status_code=303)
    if result.errors:
        return _data_page(request, user, session, status_code=422, account_errors=result.errors)
    if by_email:  # 각자의 메일로 72시간짜리 비밀번호 설정 링크를 보낸다 (관리자가 비밀번호를 전달하지 않는다)
        for created in result.created:
            tasks.send_password_reset.delay(created.user_id, kind="welcome")
    # 임시 비밀번호(메일을 못 쓸 때)는 이 응답에서 한 번만 보여준다. 브라우저·프록시에 남지 않게 캐시를 막는다
    response = _data_page(
        request,
        user,
        session,
        created=result.created,
        skipped=result.skipped,
        sheet=_password_sheet(result.created) if result.created and not by_email else None,
        by_email=by_email,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/data/courses")
def import_courses(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    try:
        result = institution_data.import_courses(session, user, file.filename or "", file.file.read())
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
        return RedirectResponse("/admin/data", status_code=303)
    if result.errors:
        return _data_page(request, user, session, status_code=422, course_errors=result.errors)
    flash(
        request,
        tr("과목 {created}건을 새로 만들고 {updated}건을 고쳤어요.", created=result.created, updated=result.updated),
    )
    return RedirectResponse("/admin/data#courses", status_code=303)


@router.post("/data/institutions")
def add_institution(
    request: Request,
    name: str = Form(...),
    country: str = Form(...),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    try:
        institution_data.add_source_institution(session, user, name, country)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
    else:
        flash(request, tr("출신 대학을 등록했어요. 학생이 편입 요청을 만들 때 고를 수 있어요."))
    return RedirectResponse("/admin/data#institutions", status_code=303)


@router.post("/data/courses/{course_id}/reference")
def upload_reference(
    request: Request,
    course_id: int,
    file: UploadFile = File(...),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    try:
        syllabus, course = institution_data.upload_reference(
            session, get_storage(), user, course_id, file.filename or "", file.file.read()
        )
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
    else:
        tasks.process_reference.delay(syllabus.id, course.id)
        flash(request, tr("{code} 기준 강의계획서를 받았어요. 글자를 읽으면 AI 비교에 쓰여요.", code=course.code))
    return RedirectResponse("/admin/data#courses", status_code=303)


@router.post("/data/accounts/active")
def account_active(
    request: Request,
    email: str = Form(...),
    action: str = Form(...),
    next_url: str = Form("", alias="next"),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """계정 비활성화·다시 활성화. 계정은 지우지 않는다. 계정 수정 화면에서 누르면 그 화면으로 돌아간다."""
    check_csrf(request, csrf_token)
    back = next_url if re.fullmatch(r"/admin/accounts/\d+", next_url) else "/admin/data#account-active"
    if action not in ("deactivate", "reactivate"):
        raise CreditBridgeError(tr("처리 방법을 골라 주세요."))
    try:
        change = institution_data.set_active(session, user, email, action == "reactivate")
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
        return RedirectResponse(back, status_code=303)
    send_notifications()
    target = change.user
    if action == "reactivate":
        flash(request, tr("{email} 계정을 다시 활성화했어요. 이전 비밀번호로 로그인할 수 있어요.", email=target.email))
    else:
        message = tr(
            "{email} 계정을 비활성화했어요. 로그인이 막히고 다른 기기의 로그인도 끊겼어요.", email=target.email
        )
        if change.moved:
            message += tr(" 진행 중인 심사 {moved}건을 같은 학과 다른 교수에게 넘겼어요.", moved=change.moved)
        if change.released:
            message += tr(
                " 심사 {released}건은 넘길 교수가 없어 심사관이 다시 배정해야 해요.", released=change.released
            )
        flash(request, message)
    return RedirectResponse(back, status_code=303)


@router.post("/data/password-reset")
def reset_password(
    request: Request,
    email: str = Form(...),
    csrf_token: str = Form(""),
    user: User = Admin,
    session: Session = Depends(get_db),
) -> Response:
    """비밀번호 초기화: 메일을 쓸 수 있으면 사용자에게 설정 링크를 보내고, 아니면 임시 비밀번호를 한 번만 보여준다."""
    check_csrf(request, csrf_token)
    by_email = notifications.email_enabled()
    try:
        target, password = auth_service.admin_reset_password(session, user, email, by_email)
    except CreditBridgeError as exc:
        session.rollback()
        flash(request, str(exc), "error")
        return RedirectResponse("/admin/data#password-reset", status_code=303)
    if password is None:
        tasks.send_password_reset.delay(target.id, kind="admin")
        flash(
            request,
            tr(
                "{email} 메일로 비밀번호 설정 링크(72시간 유효)를 보냈어요. 이전 비밀번호는 더 이상 쓸 수 없어요.",
                email=target.email,
            ),
        )
        return RedirectResponse("/admin/data#password-reset", status_code=303)
    reset = institution_data.CreatedAccount(target.email, target.name, target.role, password)
    response = _data_page(request, user, session, reset=reset)
    response.headers["Cache-Control"] = "no-store"
    return response
