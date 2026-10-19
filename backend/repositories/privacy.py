from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.errors import DuplicateRowError, is_duplicate
from backend.models import PrivacyRequest, TransferRequest


def add(session: Session, request: PrivacyRequest) -> PrivacyRequest:
    """처리 중인 건이 이미 있으면 DuplicateRowError (앱 검사 뒤 동시 요청은 DB 유니크가 막는다)."""
    try:
        with session.begin_nested():
            session.add(request)
    except IntegrityError as exc:
        if is_duplicate(exc):
            raise DuplicateRowError from exc
        raise
    return request


def get(session: Session, privacy_request_id: int) -> PrivacyRequest | None:
    return session.get(PrivacyRequest, privacy_request_id)


def latest_for_request(session: Session, transfer_request_id: int) -> PrivacyRequest | None:
    stmt = (
        select(PrivacyRequest)
        .where(PrivacyRequest.transfer_request_id == transfer_request_id)
        .order_by(PrivacyRequest.id.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def of_institution(session: Session, target_institution_id: int) -> list[tuple[PrivacyRequest, TransferRequest]]:
    stmt = (
        select(PrivacyRequest, TransferRequest)
        .join(TransferRequest, TransferRequest.id == PrivacyRequest.transfer_request_id)
        .where(TransferRequest.target_institution_id == target_institution_id)
        .order_by(PrivacyRequest.due_at)
    )
    return [(p, r) for p, r in session.execute(stmt)]
