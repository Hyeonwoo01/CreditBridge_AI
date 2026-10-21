from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from backend.models import TranscriptEntry, TransferRequest
from backend.models.enums import PASSING_GRADES


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


def delete(session: Session, request: TransferRequest) -> None:
    """서류가 하나도 없는 초안만 지운다 (호출하는 서비스가 확인). 딸린 행이 없어 이 행만 지우면 된다."""
    session.delete(request)
    session.flush()


def transcript_entries(session: Session, request_id: int) -> list[TranscriptEntry]:
    stmt = select(TranscriptEntry).where(TranscriptEntry.transfer_request_id == request_id).order_by(TranscriptEntry.id)
    return list(session.scalars(stmt))


def failing_grade() -> ColumnElement[bool]:
    """성적표 줄의 성적이 인정 최저 성적 미달 (C- 이하·F 등)."""
    return TranscriptEntry.grade.is_not(None) & func.upper(func.trim(TranscriptEntry.grade)).not_in(PASSING_GRADES)


def grade_failed_syllabus_ids(session: Session, syllabus_ids: list[int]) -> set[int]:
    """성적표에 미달 성적으로 연결된 강의계획서 id."""
    if not syllabus_ids:
        return set()
    stmt = select(TranscriptEntry.syllabus_id).where(TranscriptEntry.syllabus_id.in_(syllabus_ids), failing_grade())
    return {i for i in session.scalars(stmt) if i is not None}


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
