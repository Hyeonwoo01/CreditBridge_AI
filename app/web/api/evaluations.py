from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.security.session import current_user
from app.services import views

router = APIRouter(tags=["evaluations"])


@router.get("/evaluations/{public_id}")
def get_evaluation(
    public_id: str, user: User = Depends(current_user), session: Session = Depends(get_db)
) -> dict[str, Any]:
    """AI 분석 결과(추천일 뿐, 확정 아님)와 사람 판정."""
    v = views.evaluation_view(session, user, public_id)
    return {
        "id": v.evaluation.public_id,
        "status": v.evaluation.status,
        "recommendation": v.evaluation.recommendation,
        "probability": v.evaluation.probability,
        "confidence": v.evaluation.confidence,
        "candidate_course": v.candidate.code if v.candidate else None,
        "result": v.result.model_dump() if v.result else None,
        "decision": {
            "result": v.decision.result,
            "action": v.decision.action,
            "decided_at": v.decision.decided_at.isoformat(),
            "target_course": v.decided_target.code if v.decided_target else None,
        }
        if v.decision
        else None,
    }
