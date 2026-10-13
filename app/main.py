import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from app.logging_setup import configure_logging
from app.security.session import LoginRequired
from app.web.api import decisions as api_decisions
from app.web.api import evaluations as api_evaluations
from app.web.routes import admin, auth, professor, review, shared, student
from app.web.templating import render

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
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web" / "static"), name="static")

for router in (auth.router, student.router, review.router, professor.router, shared.router, admin.router):
    app.include_router(router)
app.include_router(api_evaluations.router, prefix="/api")
app.include_router(api_decisions.router, prefix="/api")


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
