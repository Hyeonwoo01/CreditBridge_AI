from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Course, Department, Institution


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
    """과목이 있는 학과 이름 (학생 편입 전공 선택지 등)."""
    stmt = (
        select(Department.name)
        .join(Course, Course.department_id == Department.id)
        .where(Department.institution_id == institution_id)
        .distinct()
        .order_by(Department.name)
    )
    return list(session.scalars(stmt))


def course_departments(session: Session, institution_id: int) -> list[Department]:
    """과목이 있는 학과 (교수에게 고를 수 있는 학과)."""
    stmt = (
        select(Department)
        .where(Department.institution_id == institution_id, Department.id.in_(select(Course.department_id)))
        .order_by(Department.name)
    )
    return list(session.scalars(stmt))


def department_by_name(session: Session, institution_id: int, name: str) -> Department | None:
    stmt = select(Department).where(Department.institution_id == institution_id, Department.name == name)
    return session.scalars(stmt).first()


def get_department(session: Session, department_id: int) -> Department | None:
    return session.get(Department, department_id)


def add_department(session: Session, department: Department) -> Department:
    session.add(department)
    session.flush()
    return department


def source_institution_by_name(session: Session, name: str) -> Institution | None:
    stmt = select(Institution).where(Institution.is_target.is_(False), Institution.name == name.strip())
    return session.scalars(stmt).first()


def institution_by_token_hash(session: Session, token_hash: str) -> Institution | None:
    stmt = select(Institution).where(Institution.is_target.is_(True), Institution.sis_token_hash == token_hash)
    return session.scalars(stmt).first()


def add_course(session: Session, course: Course) -> Course:
    session.add(course)
    session.flush()
    return course


def add_institution(session: Session, institution: Institution) -> Institution:
    session.add(institution)
    session.flush()
    return institution


def target_institution_by_name(session: Session, name: str) -> Institution | None:
    stmt = select(Institution).where(Institution.is_target.is_(True), Institution.name == name.strip())
    return session.scalars(stmt).first()
