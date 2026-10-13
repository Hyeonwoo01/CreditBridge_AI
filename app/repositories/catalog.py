from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Institution


def target_institutions(session: Session) -> list[Institution]:
    return list(session.scalars(select(Institution).where(Institution.is_target.is_(True)).order_by(Institution.name)))


def source_institutions(session: Session) -> list[Institution]:
    return list(session.scalars(select(Institution).where(Institution.is_target.is_(False)).order_by(Institution.name)))


def get_institution(session: Session, institution_id: int) -> Institution | None:
    return session.get(Institution, institution_id)


def get_course(session: Session, course_id: int) -> Course | None:
    return session.get(Course, course_id)


def courses_by_ids(session: Session, ids: list[int]) -> dict[int, Course]:
    if not ids:
        return {}
    return {c.id: c for c in session.scalars(select(Course).where(Course.id.in_(ids)))}


def courses_of(session: Session, institution_id: int) -> list[Course]:
    return list(session.scalars(select(Course).where(Course.institution_id == institution_id).order_by(Course.code)))


def course_by_code(session: Session, institution_id: int, code: str) -> Course | None:
    stmt = select(Course).where(Course.institution_id == institution_id, Course.code == code)
    return session.scalars(stmt).first()


def departments_of(session: Session, institution_id: int) -> list[str]:
    stmt = (
        select(Course.department).where(Course.institution_id == institution_id).distinct().order_by(Course.department)
    )
    return list(session.scalars(stmt))
