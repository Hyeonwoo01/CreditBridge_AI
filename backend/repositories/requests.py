from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import TranscriptEntry, TransferRequest


def get(session: Session, request_id: int) -> TransferRequest | None:
    return session.get(TransferRequest, request_id)


def of_student(session: Session, student_id: int) -> list[TransferRequest]:
    stmt = (
        select(TransferRequest)
        .where(TransferRequest.student_id == student_id)
        .order_by(TransferRequest.created_at.desc())
    )
    return list(session.scalars(stmt))


def add(session: Session, request: TransferRequest) -> TransferRequest:
    session.add(request)
    session.flush()
    return request


def transcript_entries(session: Session, request_id: int) -> list[TranscriptEntry]:
    stmt = select(TranscriptEntry).where(TranscriptEntry.transfer_request_id == request_id).order_by(TranscriptEntry.id)
    return list(session.scalars(stmt))


def replace_transcript_entries(session: Session, request_id: int, entries: list[TranscriptEntry]) -> None:
    for old in transcript_entries(session, request_id):
        session.delete(old)
    session.flush()
    session.add_all(entries)
    session.flush()


def get_entry(session: Session, entry_id: int) -> TranscriptEntry | None:
    return session.get(TranscriptEntry, entry_id)


def submitted_of_institution(session: Session, target_institution_id: int) -> list[TransferRequest]:
    stmt = select(TransferRequest).where(
        TransferRequest.target_institution_id == target_institution_id, TransferRequest.status != "draft"
    )
    return list(session.scalars(stmt))
