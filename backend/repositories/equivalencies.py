from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from backend.models import Course, Equivalency, Institution


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


def search(
    session: Session,
    target_institution_id: int,
    query: str = "",
    result: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[tuple[Equivalency, str, Course | None]], int]:
    """기관 동등 과목표 전체 검색 (심사관). 출신 과목·출신 대학·대상 과목 코드·이름 일부로 찾는다.
    (이력, 출신 대학 이름, 대상 과목) 최신순과 전체 건수."""
    source = aliased(Institution)
    conditions = [Equivalency.target_institution_id == target_institution_id]
    if query:
        conditions.append(
            or_(
                Equivalency.source_course_label.icontains(query, autoescape=True),
                source.name.icontains(query, autoescape=True),
                Course.code.icontains(query, autoescape=True),
                Course.title.icontains(query, autoescape=True),
            )
        )
    if result:
        conditions.append(Equivalency.result == result)
    base = (
        select(Equivalency, source.name, Course)
        .join(source, source.id == Equivalency.source_institution_id)
        .outerjoin(Course, Course.id == Equivalency.target_course_id)
        .where(*conditions)
    )
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.execute(base.order_by(Equivalency.id.desc()).limit(limit).offset(offset))
    return [(e, name, course) for e, name, course in rows], int(total)


def of_pair(session: Session, target_institution_id: int, source_institution_id: int) -> list[Equivalency]:
    stmt = select(Equivalency).where(
        Equivalency.target_institution_id == target_institution_id,
        Equivalency.source_institution_id == source_institution_id,
    )
    return list(session.scalars(stmt))
