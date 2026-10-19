from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.errors import DecisionValidationError
from backend.models import User
from backend.security.csrf import check_csrf
from backend.security.session import current_user
from backend.services import decisions as decision_service
from backend.web.notify import send_notifications

router = APIRouter(tags=["decisions"])


class DecisionIn(BaseModel):
    evaluation_id: int
    action: str
    result: str | None = None
    target_course_id: int | None = None
    reason_codes: list[str] = []
    reason_memo: str = ""
    acknowledge_conflict: bool = False


@router.post("/decisions", status_code=201)
def create_decision(
    body: DecisionIn, request: Request, user: User = Depends(current_user), session: Session = Depends(get_db)
) -> dict[str, Any]:
    """최종 판정은 로그인한 배정 교수만 저장할 수 있다. 판정자 정보 없는 요청은 거부된다 (TC-16)."""
    check_csrf(request, None)
    try:
        decision = decision_service.decide(
            session,
            user,
            body.evaluation_id,
            body.action,
            body.result,
            body.target_course_id,
            body.reason_codes,
            body.reason_memo,
            body.acknowledge_conflict,
        )
    except decision_service.ConflictNeedsAcknowledgement as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DecisionValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    send_notifications()
    return {"id": decision.id, "result": decision.result, "decided_by": user.id}
