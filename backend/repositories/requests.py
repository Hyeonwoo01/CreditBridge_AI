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


def delete(session: Session, request: TransferRequest) -> None:
    """서류가 하나도 없는 초안만 지운다 (호출하는 서비스가 확인). 딸린 행은 계정 성적표에서 복사한 과목 목록뿐이다."""
    for entry in transcript_entries(session, request.id):
        session.delete(entry)
    session.delete(request)
    session.flush()


def drafts_of_student(session: Session, student_id: int) -> list[TransferRequest]:
    stmt = select(TransferRequest).where(TransferRequest.student_id == student_id, TransferRequest.status == "draft")
    return list(session.scalars(stmt.order_by(TransferRequest.id)))


def transcript_entries(session: Session, request_id: int) -> list[TranscriptEntry]:
    stmt = select(TranscriptEntry).where(TranscriptEntry.transfer_request_id == request_id).order_by(TranscriptEntry.id)
    return list(session.scalars(stmt))


def grades_with_student(session: Session, syllabus_ids: list[int]) -> list[tuple[int, str | None, int, int]]:
    """강의계획서에 연결된 성적표 성적과 그 학생·편입 대학: (강의계획서 id, 성적, 학생 id, 대상 대학 id).
    성적 기준 미달 여부는 학생마다 다른 학칙 정책으로 판단한다 (services/policy.py)."""
    if not syllabus_ids:
        return []
    stmt = (
        select(
            TranscriptEntry.syllabus_id,
            TranscriptEntry.grade,
            TransferRequest.student_id,
            TransferRequest.target_institution_id,
        )
        .join(TransferRequest, TransferRequest.id == TranscriptEntry.transfer_request_id)
        .where(TranscriptEntry.syllabus_id.in_(syllabus_ids))
    )
    return [(sid, grade, student, target) for sid, grade, student, target in session.execute(stmt) if sid is not None]


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
