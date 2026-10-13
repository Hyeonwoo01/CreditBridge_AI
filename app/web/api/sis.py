from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import sis as sis_service

router = APIRouter(tags=["sis"])


@router.get("/sis/decisions")
def sis_decisions(
    since: datetime | None = Query(None, description="이 시각(UTC) 이후 확정된 판정만"),
    authorization: str = Header(""),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """학사정보시스템 연동 (FR-24). 기관 관리자가 발급한 토큰으로 인증한다: `Authorization: Bearer cbsis_...`"""
    scheme, _, token = authorization.partition(" ")
    institution = sis_service.institution_for_token(session, token.strip()) if scheme.lower() == "bearer" else None
    if institution is None:
        raise HTTPException(status_code=401, detail="유효한 연동 토큰이 필요해요.")
    if since is not None and since.tzinfo is not None:
        since = since.astimezone(UTC).replace(tzinfo=None)  # DB는 UTC naive로 저장한다
    rows = sis_service.export_rows(session, institution.id, since)
    return {"institution": institution.name, "count": len(rows), "decisions": rows}
