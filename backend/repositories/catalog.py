from sqlalchemy import ColumnElement, CompoundSelect, delete, func, or_, select, union
from sqlalchemy.orm import Session

from backend.models import (
    Course,
    Department,
    Equivalency,
    Institution,
    InstitutionSource,
    Syllabus,
    TransferRequest,
    User,
)


def target_institutions(session: Session) -> list[Institution]:
    return list(session.scalars(select(Institution).where(Institution.is_target.is_(True)).order_by(Institution.name)))


def source_institutions(session: Session, institution_id: int) -> list[Institution]:
    """그 대상 대학의 ④ 출신 대학 목록."""
    stmt = (
        select(Institution)
        .join(InstitutionSource, InstitutionSource.source_institution_id == Institution.id)
        .where(InstitutionSource.institution_id == institution_id)
        .order_by(Institution.name)
    )
    return list(session.scalars(stmt))


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


def add_department(session: Session, department: Department) -> Department:
    session.add(department)
    session.flush()
    return department


def source_institution_by_name(session: Session, institution_id: int, name: str) -> Institution | None:
    """그 대상 대학 목록에 있는 출신 대학 (계정·동등 과목표 CSV의 이름 확인)."""
    stmt = (
        select(Institution)
        .join(InstitutionSource, InstitutionSource.source_institution_id == Institution.id)
        .where(InstitutionSource.institution_id == institution_id, Institution.name == name.strip())
    )
    return session.scalars(stmt).first()


def shared_source_by_name(session: Session, name: str) -> Institution | None:
    """다른 대학이 이미 만든 같은 이름의 출신 대학 행 (새로 등록할 때 같은 행을 함께 쓴다)."""
    stmt = select(Institution).where(Institution.is_target.is_(False), Institution.name == name.strip())
    return session.scalars(stmt).first()


def source_link(session: Session, institution_id: int, source_id: int) -> InstitutionSource | None:
    stmt = select(InstitutionSource).where(
        InstitutionSource.institution_id == institution_id, InstitutionSource.source_institution_id == source_id
    )
    return session.scalars(stmt).first()


def add_source_link(session: Session, institution_id: int, source_id: int) -> InstitutionSource:
    link = InstitutionSource(institution_id=institution_id, source_institution_id=source_id)
    session.add(link)
    session.flush()
    return link


def remove_source_link(session: Session, institution_id: int, source_id: int) -> None:
    session.execute(
        delete(InstitutionSource).where(
            InstitutionSource.institution_id == institution_id, InstitutionSource.source_institution_id == source_id
        )
    )


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


def _count(session: Session, model: type, *conditions: ColumnElement[bool]) -> int:
    return int(session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)


def used_source_institution_ids(session: Session, institution_id: int) -> set[int]:
    """그 대상 대학의 학생 계정·편입 요청·동등 과목표 중 한 곳이라도 가리키는 출신 대학 id."""
    stmt: CompoundSelect[tuple[int | None]] = union(
        select(User.source_institution_id).where(
            User.institution_id == institution_id, User.source_institution_id.is_not(None)
        ),
        select(TransferRequest.source_institution_id).where(TransferRequest.target_institution_id == institution_id),
        select(Equivalency.source_institution_id).where(Equivalency.target_institution_id == institution_id),
    )
    return {int(i) for i in session.scalars(stmt) if i is not None}


def source_usage(session: Session, institution_id: int, source_id: int) -> dict[str, int]:
    """그 대상 대학에서 출신 대학을 가리키는 행 수 (목록에서 뺄 수 있는지 확인용). 0인 항목도 돌려준다."""
    return {
        "students": _count(
            session, User, User.institution_id == institution_id, User.source_institution_id == source_id
        ),
        "requests": _count(
            session,
            TransferRequest,
            TransferRequest.target_institution_id == institution_id,
            TransferRequest.source_institution_id == source_id,
        ),
        "equivalencies": _count(
            session,
            Equivalency,
            Equivalency.target_institution_id == institution_id,
            Equivalency.source_institution_id == source_id,
        ),
    }


def institution_referenced(session: Session, institution_id: int) -> bool:
    """어느 행이든 이 기관을 가리키면 True (출신 대학 행 자체를 지워도 되는지)."""

    def any_of(model: type, *conditions: ColumnElement[bool]) -> bool:
        return _count(session, model, or_(*conditions)) > 0

    return (
        any_of(User, User.source_institution_id == institution_id, User.institution_id == institution_id)
        or any_of(
            TransferRequest,
            TransferRequest.source_institution_id == institution_id,
            TransferRequest.target_institution_id == institution_id,
        )
        or any_of(
            Equivalency,
            Equivalency.source_institution_id == institution_id,
            Equivalency.target_institution_id == institution_id,
        )
        or any_of(
            InstitutionSource,
            InstitutionSource.source_institution_id == institution_id,
            InstitutionSource.institution_id == institution_id,
        )
        or any_of(Syllabus, Syllabus.institution_id == institution_id)
        or any_of(Course, Course.institution_id == institution_id)
        or any_of(Department, Department.institution_id == institution_id)
    )


def delete_institution(session: Session, institution: Institution) -> None:
    session.delete(institution)
    session.flush()
