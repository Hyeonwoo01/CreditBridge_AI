from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.documents.storage import get_storage
from app.errors import CreditBridgeError
from app.models import User
from app.models.enums import Role
from app.security.csrf import check_csrf
from app.security.session import require
from app.services import student as student_service
from app.services import views
from app.web.templating import flash, render
from app.workers import tasks

router = APIRouter(prefix="/student")
Student = Depends(require(Role.STUDENT))


def _read(files: list[UploadFile]) -> list[student_service.UploadedFile]:
    return [
        student_service.UploadedFile(filename=f.filename or "upload", data=f.file.read()) for f in files if f.filename
    ]


@router.get("")
def index(request: Request, user: User = Student, session: Session = Depends(get_db)) -> Response:
    return render(request, "student/index.html", user=user, home=views.student_home(session, user))


@router.post("/requests")
def create_request(
    request: Request,
    source_institution_id: int = Form(...),
    major: str = Form(...),
    csrf_token: str = Form(""),
    user: User = Student,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    created = student_service.create_request(session, user, source_institution_id, major)
    return RedirectResponse(f"/student/requests/{created.id}", status_code=303)


@router.get("/requests/{request_id}")
def request_page(
    request: Request,
    request_id: int,
    tuition: int | None = Query(None, ge=0),
    degree: int | None = Query(None, ge=1, le=300),
    user: User = Student,
    session: Session = Depends(get_db),
) -> Response:
    view = views.request_view(session, user, request_id, tuition, degree)
    template = "partials/course_list.html" if request.headers.get("HX-Request") else "student/request.html"
    return render(request, template, user=user, view=view, stages=student_service.STAGES)


@router.post("/requests/{request_id}/syllabi")
def upload_syllabi(
    request: Request,
    request_id: int,
    files: list[UploadFile] = File(...),
    csrf_token: str = Form(""),
    user: User = Student,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    transfer = student_service.get_own_request(session, user, request_id)
    try:
        result = student_service.add_syllabi(session, get_storage(), user, transfer, _read(files))
    except CreditBridgeError as exc:
        flash(request, str(exc), "error")
    else:
        for s in result.created:
            tasks.process_syllabus.delay(s.id)
        if result.created:
            flash(request, f"강의계획서 {len(result.created)}건을 받았어요. AI 분석이 끝나면 결과가 표시돼요.")
        if result.duplicates:
            names = ", ".join(s.original_filename for s in result.duplicates)
            flash(request, f"이미 올린 문서라 저장된 분석 결과를 그대로 보여드려요: {names}")
    return RedirectResponse(f"/student/requests/{request_id}", status_code=303)


@router.post("/requests/{request_id}/transcript")
def upload_transcript(
    request: Request,
    request_id: int,
    file: UploadFile = File(...),
    csrf_token: str = Form(""),
    user: User = Student,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    transfer = student_service.get_own_request(session, user, request_id)
    uploaded = _read([file])
    try:
        if not uploaded:
            raise CreditBridgeError("성적표 파일을 선택해 주세요.")
        student_service.set_transcript(session, get_storage(), user, transfer, uploaded[0])
    except CreditBridgeError as exc:
        flash(request, str(exc), "error")
    else:
        tasks.process_transcript.delay(transfer.id)
        flash(request, "성적표를 받았어요. 과목과 강의계획서를 자동으로 연결할게요.")
    return RedirectResponse(f"/student/requests/{request_id}", status_code=303)


@router.post("/requests/{request_id}/entries/{entry_id}")
def link_entry(
    request: Request,
    request_id: int,
    entry_id: int,
    syllabus_id: str = Form(""),
    csrf_token: str = Form(""),
    user: User = Student,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    transfer = student_service.get_own_request(session, user, request_id)
    student_service.confirm_link(session, user, transfer, entry_id, int(syllabus_id) if syllabus_id.isdigit() else None)
    return RedirectResponse(f"/student/requests/{request_id}#transcript", status_code=303)


@router.post("/requests/{request_id}/submit")
def submit(
    request: Request,
    request_id: int,
    csrf_token: str = Form(""),
    user: User = Student,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    transfer = student_service.get_own_request(session, user, request_id)
    try:
        student_service.submit_request(session, user, transfer)
        flash(request, "학사처에 심사를 요청했어요. 진행 상황은 이 화면에서 확인할 수 있어요.")
    except CreditBridgeError as exc:
        flash(request, str(exc), "error")
    return RedirectResponse(f"/student/requests/{request_id}", status_code=303)


@router.post("/requests/{request_id}/delete-documents")
def delete_documents(
    request: Request,
    request_id: int,
    csrf_token: str = Form(""),
    user: User = Student,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    transfer = student_service.get_own_request(session, user, request_id)
    student_service.delete_documents(session, get_storage(), user, transfer)
    flash(request, "올린 원본 파일과 추출한 텍스트를 삭제했어요.")
    return RedirectResponse(f"/student/requests/{request_id}", status_code=303)


@router.get("/syllabi/{syllabus_id}")
def syllabus_result(
    request: Request, syllabus_id: int, user: User = Student, session: Session = Depends(get_db)
) -> Response:
    evaluation_id = views.latest_evaluation_id(session, user, syllabus_id)
    if evaluation_id is None:
        flash(request, "아직 분석 중이에요. 잠시 후 다시 확인해 주세요.")
        return RedirectResponse(request.headers.get("referer") or "/student", status_code=303)
    return RedirectResponse(f"/student/evaluations/{evaluation_id}", status_code=303)


@router.get("/evaluations/{evaluation_id}")
def evaluation_page(
    request: Request, evaluation_id: int, user: User = Student, session: Session = Depends(get_db)
) -> Response:
    view = views.evaluation_view(session, user, evaluation_id)
    return render(request, "student/evaluation.html", user=user, v=view)


@router.post("/syllabi/{syllabus_id}/supplement")
def supplement(
    request: Request,
    syllabus_id: int,
    file: UploadFile = File(...),
    csrf_token: str = Form(""),
    user: User = Student,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    syllabus = views.own_syllabus(session, user, syllabus_id)
    uploaded = _read([file])
    try:
        if not uploaded:
            raise CreditBridgeError("보완 자료 파일을 선택해 주세요.")
        key = student_service.store_supplement(session, get_storage(), user, syllabus, uploaded[0])
    except CreditBridgeError as exc:
        flash(request, str(exc), "error")
        return RedirectResponse(request.headers.get("referer") or "/student", status_code=303)
    tasks.add_supplement.delay(syllabus.id, key)
    flash(request, "보완 자료를 받았어요. 다시 분석한 뒤 결과를 갱신할게요. 이전 결과는 기록으로 남아요.")
    return RedirectResponse(f"/student/requests/{views.request_id_of(session, syllabus)}", status_code=303)
