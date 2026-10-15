import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.config import get_settings
from backend.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from backend.logging_setup import configure_logging
from backend.security.session import LoginRequired
from backend.web.api import decisions as api_decisions
from backend.web.api import evaluations as api_evaluations
from backend.web.api import sis as api_sis
from backend.web.routes import admin, auth, notifications, professor, review, shared, student
from backend.web.templating import render

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title="CreditBridge AI", docs_url="/api/docs" if not settings.is_production else None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="cb_session",
    same_site="lax",
    https_only=settings.is_production,
    max_age=60 * 60 * 8,
)
# 화면 파일(템플릿·CSS·JS·이미지)은 저장소 루트의 frontend/ 에 있다
FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND / "static"), name="static")

for router in (
    auth.router,
    student.router,
    review.router,
    professor.router,
    shared.router,
    admin.router,
    notifications.router,
):
    app.include_router(router)
app.include_router(api_evaluations.router, prefix="/api")
app.include_router(api_decisions.router, prefix="/api")
app.include_router(api_sis.router, prefix="/api")


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(LoginRequired)
def login_required(request: Request, exc: LoginRequired) -> Response:
    if request.url.path.startswith("/api/"):
        return Response(status_code=401)
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(PermissionDeniedError)
def forbidden(request: Request, exc: PermissionDeniedError) -> Response:
    if request.url.path.startswith("/api/"):
        return Response(content=f'{{"detail": "{exc}"}}', status_code=403, media_type="application/json")
    return render(request, "error.html", status_code=403, message=str(exc))


@app.exception_handler(NotFoundError)
def not_found(request: Request, exc: NotFoundError) -> Response:
    return render(request, "error.html", status_code=404, message=str(exc))


@app.exception_handler(CreditBridgeError)
def business_error(request: Request, exc: CreditBridgeError) -> Response:
    return render(request, "error.html", status_code=400, message=str(exc))


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException) -> Response:
    if request.url.path.startswith("/api/"):
        return Response(
            content=f'{{"detail": "{exc.detail}"}}', status_code=exc.status_code, media_type="application/json"
        )
    return render(request, "error.html", status_code=exc.status_code, message=str(exc.detail))
