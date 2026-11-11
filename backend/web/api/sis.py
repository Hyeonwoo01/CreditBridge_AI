from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.errors import CreditBridgeError, IdempotencyConflictError
from backend.i18n import gettext as tr
from backend.models import Institution
from backend.services import sis as sis_service

router = APIRouter(tags=["sis"])


def _institution(session: Session, authorization: str) -> Institution:
    scheme, _, token = authorization.partition(" ")
    institution = sis_service.institution_for_token(session, token.strip()) if scheme.lower() == "bearer" else None
    if institution is None:
        raise HTTPException(status_code=401, detail=tr("유효한 연동 토큰이 필요해요."))
    return institution


@router.get("/sis/decisions")
def sis_decisions(
    since: datetime | None = Query(None, description="이 시각(UTC) 이후 확정된 판정만"),
    status: str = Query("all", description="반영 상태: all · unsent(대기+실패) · pending · failed · applied"),
    authorization: str = Header(""),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """학사정보시스템 연동 (FR-24). 기관 관리자가 발급한 토큰으로 인증한다: `Authorization: Bearer cbsis_...`
    판정마다 idempotency_key(cb-decision-{id})를 함께 준다. SIS는 이 키로 같은 판정을 두 번 반영하지 않는다."""
    institution = _institution(session, authorization)
    if status not in sis_service.SYNC_FILTERS:
        raise HTTPException(status_code=422, detail=tr("status는 all·unsent·pending·failed·applied 중 하나예요."))
    if since is not None and since.tzinfo is not None:
        since = since.astimezone(UTC).replace(tzinfo=None)  # DB는 UTC naive로 저장한다
    rows = sis_service.export_rows(session, institution.id, since, status)
    return {"institution": institution.name, "count": len(rows), "decisions": rows}


@router.post("/sis/acks")
def sis_acks(
    response: Response,
    body: dict[str, Any],
    authorization: str = Header(""),
    idempotency_key: str = Header("", alias="Idempotency-Key"),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """SIS가 판정마다 반영 결과를 보낸다 (리뷰 v3 P1-4): `{"results": [{"decision_id", "status": "applied"|"failed",
    "external_reference_id", "error"}]}`. Idempotency-Key 헤더가 필요하고, 같은 키·같은 내용을 다시 보내면 처음 응답을
    그대로 돌려준다(`Idempotent-Replay: true`). 쿠키가 아니라 연동 토큰으로 인증하므로 CSRF 토큰은 쓰지 않는다."""
    institution = _institution(session, authorization)
    try:
        result, replay = sis_service.acknowledge(session, institution, idempotency_key, body)
    except IdempotencyConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CreditBridgeError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if replay:
        response.headers["Idempotent-Replay"] = "true"
    return result
