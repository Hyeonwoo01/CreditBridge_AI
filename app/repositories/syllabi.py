from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Course, Syllabus, SyllabusChunk


def get(session: Session, syllabus_id: int) -> Syllabus | None:
    return session.get(Syllabus, syllabus_id)


def of_request(session: Session, request_id: int) -> list[Syllabus]:
    stmt = (
        select(Syllabus)
        .where(Syllabus.transfer_request_id == request_id, Syllabus.status != "deleted")
        .order_by(Syllabus.created_at, Syllabus.id)
    )
    return list(session.scalars(stmt))


def count_of_request(session: Session, request_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Syllabus)
        .where(Syllabus.transfer_request_id == request_id, Syllabus.status != "deleted")
    )
    return int(session.scalar(stmt) or 0)


def add(session: Session, syllabus: Syllabus) -> Syllabus:
    session.add(syllabus)
    session.flush()
    return syllabus


def replace_chunks(session: Session, syllabus_id: int, chunks: list[SyllabusChunk]) -> None:
    session.execute(delete(SyllabusChunk).where(SyllabusChunk.syllabus_id == syllabus_id))
    session.add_all(chunks)
    session.flush()


def chunks_of(session: Session, syllabus_id: int) -> list[SyllabusChunk]:
    stmt = select(SyllabusChunk).where(SyllabusChunk.syllabus_id == syllabus_id).order_by(SyllabusChunk.id)
    return list(session.scalars(stmt))


def reference_concepts(session: Session, course_ids: list[int]) -> dict[int, list[SyllabusChunk]]:
    """대상 과목별 기준 강의계획서의 개념 청크."""
    if not course_ids:
        return {}
    stmt = (
        select(Course.id, SyllabusChunk)
        .join(SyllabusChunk, SyllabusChunk.syllabus_id == Course.reference_syllabus_id)
        .where(Course.id.in_(course_ids))
        .order_by(SyllabusChunk.id)
    )
    out: dict[int, list[SyllabusChunk]] = {cid: [] for cid in course_ids}
    for course_id, chunk in session.execute(stmt):
        out[course_id].append(chunk)
    return out


def in_request_with_hash(session: Session, request_id: int, content_hash: str) -> Syllabus | None:
    stmt = select(Syllabus).where(Syllabus.transfer_request_id == request_id, Syllabus.content_hash == content_hash)
    return session.scalars(stmt).first()


def analyzed_with_hash(session: Session, content_hash: str, exclude_id: int) -> Syllabus | None:
    """같은 원본으로 이미 추출을 마친 강의계획서 (LLM 재호출 없이 결과를 재사용할 출처)."""
    stmt = (
        select(Syllabus)
        .where(
            Syllabus.content_hash == content_hash,
            Syllabus.id != exclude_id,
            Syllabus.status == "ready",
            Syllabus.extracted_json.is_not(None),
        )
        .order_by(Syllabus.id)
        .limit(1)
    )
    return session.scalars(stmt).first()
