from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.types import to_vector_text
from app.models import Course, Syllabus, SyllabusChunk


@dataclass(frozen=True)
class ChunkHit:
    course_id: int
    chunk_id: int
    concept: str
    distance: float


def get(session: Session, syllabus_id: int) -> Syllabus | None:
    return session.get(Syllabus, syllabus_id)


def get_by_public_id(session: Session, public_id: str) -> Syllabus | None:
    return session.scalars(select(Syllabus).where(Syllabus.public_id == public_id)).first()


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


def nearest_target_chunks(session: Session, embedding: list[float], institution_id: int, k: int) -> list[ChunkHit]:
    """대상 대학 기준 강의계획서 청크 중 코사인 거리가 가까운 k개 (MariaDB 벡터 인덱스 사용)."""
    vec = func.VEC_FromText(to_vector_text(embedding))
    distance = func.VEC_DISTANCE_COSINE(SyllabusChunk.embedding, vec).label("distance")
    stmt = (
        select(Course.id, SyllabusChunk.id, SyllabusChunk.concept, distance)
        .join(Course, Course.reference_syllabus_id == SyllabusChunk.syllabus_id)
        .where(Course.institution_id == institution_id)
        .order_by(distance)
        .limit(k)
    )
    return [ChunkHit(course_id=r[0], chunk_id=r[1], concept=r[2], distance=float(r[3])) for r in session.execute(stmt)]
