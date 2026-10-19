import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.config import get_settings
from backend.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from backend.i18n import COOKIE, from_accept_language, normalize, set_locale
from backend.logging_setup import configure_logging
from backend.security.session import PASSWORD_PAGE, LoginRequired, PasswordChangeRequired
from backend.web.api import decisions as api_decisions
from backend.web.api import evaluations as api_evaluations
from backend.web.api import sis as api_sis
from backend.web.routes import account, admin, auth, notifications, professor, review, shared, student
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


@app.middleware("http")
async def choose_locale(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """요청마다 화면 언어를 정한다: cb_lang 쿠키(로그인·언어 전환 때 저장) → 브라우저 언어 → 한국어."""
    set_locale(normalize(request.cookies.get(COOKIE)) or from_accept_language(request.headers.get("accept-language")))
    return await call_next(request)


# 화면 파일(템플릿·CSS·JS·이미지)은 저장소 루트의 frontend/ 에 있다
FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND / "static"), name="static")


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> Response:
    """웹 푸시 서비스 워커. 사이트 전체(/)를 범위로 쓰려면 루트 주소에서 내보내야 한다."""
    return FileResponse(
        FRONTEND / "static" / "js" / "sw.js",
        media_type="text/javascript",
        headers={"Cache-Control": "no-cache"},
    )


for router in (
    auth.router,
    student.router,
    review.router,
    professor.router,
    shared.router,
    admin.router,
    notifications.router,
    account.router,
):
    app.include_router(router)
# JSON API는 버전을 붙여 연다. 버전 없는 옛 경로(/api/...)는 이미 연동한 시스템을 위해 남기되
# 폐기 예정으로 표시하고, 응답 헤더로 새 경로를 알려 준다 (docs/API_Spec.md 2.7)
API_VERSION = "v1"


def legacy_api_notice(request: Request, response: Response) -> None:
    response.headers["Deprecation"] = "true"
    successor = f"/api/{API_VERSION}" + request.url.path.removeprefix("/api")
    response.headers["Link"] = f'<{successor}>; rel="successor-version"'


for api in (api_evaluations.router, api_decisions.router, api_sis.router):
    app.include_router(api, prefix=f"/api/{API_VERSION}")
    app.include_router(api, prefix="/api", deprecated=True, dependencies=[Depends(legacy_api_notice)])


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(LoginRequired)
def login_required(request: Request, exc: LoginRequired) -> Response:
    if request.url.path.startswith("/api/"):
        return Response(status_code=401)
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(PasswordChangeRequired)
def password_change_required(request: Request, exc: PasswordChangeRequired) -> Response:
    if request.url.path.startswith("/api/"):
        return Response(status_code=403)
    if request.headers.get("HX-Request"):
        return Response(status_code=204, headers={"HX-Redirect": PASSWORD_PAGE})
    return RedirectResponse(PASSWORD_PAGE, status_code=303)


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
