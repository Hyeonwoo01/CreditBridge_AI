from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Equivalency


def add_many(session: Session, rows: list[Equivalency]) -> None:
    session.add_all(rows)
    session.flush()


def for_course(
    session: Session, target_institution_id: int, source_institution_id: int, course_key: str
) -> list[Equivalency]:
    stmt = (
        select(Equivalency)
        .where(
            Equivalency.target_institution_id == target_institution_id,
            Equivalency.source_institution_id == source_institution_id,
            Equivalency.source_course_key == course_key,
        )
        .order_by(Equivalency.id.desc())
    )
    return list(session.scalars(stmt))


def of_institution(session: Session, target_institution_id: int, limit: int = 200) -> list[Equivalency]:
    stmt = (
        select(Equivalency)
        .where(Equivalency.target_institution_id == target_institution_id)
        .order_by(Equivalency.id.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))
