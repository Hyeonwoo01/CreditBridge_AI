from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import User


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalars(select(User).where(User.email == email.lower().strip())).first()


def get_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def professors_in(session: Session, institution_id: int, department: str) -> list[User]:
    stmt = (
        select(User)
        .where(User.institution_id == institution_id, User.role == "professor", User.department == department)
        .order_by(User.id)
    )
    return list(session.scalars(stmt))


def add(session: Session, user: User) -> User:
    session.add(user)
    session.flush()
    return user


def staff_of(session: Session, institution_id: int, role: str) -> list[User]:
    stmt = select(User).where(User.institution_id == institution_id, User.role == role).order_by(User.id)
    return list(session.scalars(stmt))


def role_counts(session: Session, institution_id: int) -> dict[str, int]:
    stmt = select(User.role, func.count()).where(User.institution_id == institution_id).group_by(User.role)
    return {role: count for role, count in session.execute(stmt).all()}


def pending_password_change(session: Session, institution_id: int) -> int:
    stmt = select(func.count()).where(User.institution_id == institution_id, User.must_change_password.is_(True))
    return session.scalar(stmt) or 0


def professor_departments(session: Session, institution_id: int) -> set[str]:
    stmt = select(User.department).where(
        User.institution_id == institution_id, User.role == "professor", User.department.is_not(None)
    )
    return {d for d in session.scalars(stmt) if d}
