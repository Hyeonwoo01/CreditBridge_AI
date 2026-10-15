"""세션 기반 CSRF 토큰. 상태를 바꾸는 모든 POST는 폼 필드 csrf_token 또는 X-CSRF-Token 헤더를 검증한다."""

import secrets

from fastapi import HTTPException, Request


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return str(token)


def check_csrf(request: Request, sent: str | None) -> None:
    expected = request.session.get("csrf")
    sent = sent or request.headers.get("X-CSRF-Token")
    if not expected or not sent or not secrets.compare_digest(str(expected), sent):
        raise HTTPException(
            status_code=403, detail="보안 토큰이 만료됐어요. 페이지를 새로고침한 뒤 다시 시도해 주세요."
        )
