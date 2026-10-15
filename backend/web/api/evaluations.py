from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models import User
from backend.security.session import current_user
from backend.services import views

router = APIRouter(tags=["evaluations"])


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(
    evaluation_id: int, user: User = Depends(current_user), session: Session = Depends(get_db)
) -> dict[str, Any]:
    """AI 분석 결과(추천일 뿐, 확정 아님)와 사람 판정. MVP는 판정 확률을 제공하지 않는다."""
    v = views.evaluation_view(session, user, evaluation_id)
    return {
        "id": v.evaluation.id,
        "status": v.evaluation.status,
        "recommendation": v.evaluation.recommendation,
        "coverage": v.evaluation.coverage,
        "confidence": v.evaluation.confidence,
        "candidate_course": v.candidate.code if v.candidate else None,
        "result": v.result.model_dump() if v.result else None,
        "decision": {
            "result": v.decision.result,
            "action": v.decision.action,
            "reason_codes": v.decision.reason_codes,
            "decided_at": v.decision.decided_at.isoformat(),
            "target_course": v.decided_target.code if v.decided_target else None,
        }
        if v.decision
        else None,
    }
