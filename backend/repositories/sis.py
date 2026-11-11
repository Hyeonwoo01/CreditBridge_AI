"""학사정보시스템 반영 상태 (리뷰 v3 P1-4)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.errors import DuplicateRowError, is_duplicate
from backend.models import SisAckRequest, SisSync


def syncs_for(session: Session, institution_id: int) -> dict[int, SisSync]:
    rows = session.execute(select(SisSync).where(SisSync.institution_id == institution_id)).scalars()
    return {s.decision_id: s for s in rows}


def sync_for_update(session: Session, decision_id: int) -> SisSync | None:
    return session.execute(select(SisSync).where(SisSync.decision_id == decision_id).with_for_update()).scalar()


def add_sync(session: Session, sync: SisSync) -> SisSync:
    session.add(sync)
    session.flush()
    return sync


def ack_request(session: Session, institution_id: int, key: str) -> SisAckRequest | None:
    return session.execute(
        select(SisAckRequest).where(
            SisAckRequest.institution_id == institution_id, SisAckRequest.idempotency_key == key
        )
    ).scalar()


def add_ack_request(session: Session, request: SisAckRequest) -> SisAckRequest:
    """같은 기관·같은 키가 이미 있으면 DuplicateRowError (동시에 들어온 같은 요청은 DB 유니크가 막는다)."""
    try:
        with session.begin_nested():
            session.add(request)
    except IntegrityError as exc:
        if is_duplicate(exc):
            raise DuplicateRowError from exc
        raise
    return request
