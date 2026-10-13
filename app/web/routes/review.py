import csv
import io

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.models.enums import Role
from app.security.csrf import check_csrf
from app.security.session import require
from app.services import review as review_service
from app.services import views
from app.web.templating import flash, render

router = APIRouter(prefix="/review")
Evaluator = Depends(require(Role.EVALUATOR))


@router.get("")
def queue(
    request: Request,
    tab: str = Query("high", pattern="^(high|low|insufficient)$"),
    department: str = Query(""),
    sort: str = Query("submitted", pattern="^(submitted|probability|department)$"),
    user: User = Evaluator,
    session: Session = Depends(get_db),
) -> Response:
    rows, counts, departments = review_service.queue(session, user, tab, department or None, sort)
    return render(
        request,
        "review/queue.html",
        user=user,
        rows=rows,
        counts=counts,
        departments=departments,
        tab=tab,
        tabs=review_service.TABS,
        department=department,
        sort=sort,
    )


@router.post("/assign")
def assign(
    request: Request,
    evaluation_ids: list[str] = Form([]),
    tab: str = Form("high"),
    csrf_token: str = Form(""),
    user: User = Evaluator,
    session: Session = Depends(get_db),
) -> Response:
    check_csrf(request, csrf_token)
    if not evaluation_ids:
        flash(request, "배정할 건을 선택해 주세요.", "error")
    else:
        count, problems = review_service.auto_assign(session, user, evaluation_ids)
        flash(request, f"{count}건을 학과 담당 교수에게 배정했어요. 근거 요약이 함께 전달돼요.")
        for p in problems:
            flash(request, p, "error")
    return RedirectResponse(f"/review?tab={tab}", status_code=303)


@router.get("/evaluations/{public_id}")
def evaluation_page(
    request: Request, public_id: str, user: User = Evaluator, session: Session = Depends(get_db)
) -> Response:
    view = views.evaluation_view(session, user, public_id, with_audit=True)
    return render(request, "review/evaluation.html", user=user, v=view)


@router.get("/export.csv")
def export_csv(user: User = Evaluator, session: Session = Depends(get_db)) -> Response:
    rows = views.export_rows(session, user)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "decision_id",
            "student_public_id",
            "source_course",
            "result",
            "target_course",
            "credits",
            "decided_at",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=decisions.csv"},
    )
