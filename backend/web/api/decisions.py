from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.errors import ConcurrentChangeError, DecisionValidationError
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
    accepted_credits: float | None = None  # 대상 대학 단위, 비우면 환산 규칙으로 계산
    combined_syllabus_ids: list[int] = []  # 합쳐 하나로 인정할 같은 학생의 다른 출신 과목 (N:1)
    case_token: str | None = None  # 조회 때 받은 상태 토큰. 그 사이 바뀌었으면 409 (낙관적 잠금)
    checklist: list[str] = []  # 분야별 심사 체크리스트에서 확인한 항목 키 (리뷰 v3 P1-1)
    missing_evidence: list[str] = []  # 자료가 없어 확인하지 못한 항목 키


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
            accepted_credits=body.accepted_credits,
            combined_syllabus_ids=body.combined_syllabus_ids,
            case_token=body.case_token,
            checklist=body.checklist,
            missing_evidence=body.missing_evidence,
        )
    except (decision_service.ConflictNeedsAcknowledgement, ConcurrentChangeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DecisionValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    send_notifications()
    return {
        "id": decision.id,
        "result": decision.result,
        "decided_by": user.id,
        "accepted_credits": decision.accepted_credits,
        "credit_unit": decision.credit_unit,
        "credit_basis": decision.credit_basis,
    }
