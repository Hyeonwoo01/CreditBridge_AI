from typing import Any

from sqlalchemy.orm import Session

from app.models import User
from app.repositories import audit as audit_repo


def record(session: Session, actor: User | None, action: str, target_type: str, target_id: str, **payload: Any) -> None:
    """감사 로그. payload에는 식별자와 판정값만 넣고 이름·학번·성적은 넣지 않는다."""
    audit_repo.add(session, actor.id if actor else None, action, target_type, target_id, payload)
