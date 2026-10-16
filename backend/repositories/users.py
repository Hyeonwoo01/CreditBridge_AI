from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.models import User


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalars(select(User).where(User.email == email.lower().strip())).first()


def get_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def professors_in(session: Session, institution_id: int, department: str) -> list[User]:
    stmt = (
        select(User)
        .where(
            User.institution_id == institution_id,
            User.role == "professor",
            User.department == department,
            User.is_active.is_(True),
        )
        .order_by(User.id)
    )
    return list(session.scalars(stmt))


def add(session: Session, user: User) -> User:
    session.add(user)
    session.flush()
    return user


def staff_of(session: Session, institution_id: int, role: str) -> list[User]:
    stmt = (
        select(User)
        .where(User.institution_id == institution_id, User.role == role, User.is_active.is_(True))
        .order_by(User.id)
    )
    return list(session.scalars(stmt))


def role_counts(session: Session, institution_id: int) -> dict[str, int]:
    stmt = (
        select(User.role, func.count())
        .where(User.institution_id == institution_id, User.is_active.is_(True))
        .group_by(User.role)
    )
    return {role: count for role, count in session.execute(stmt).all()}


def pending_password_change(session: Session, institution_id: int) -> int:
    stmt = select(func.count()).where(User.institution_id == institution_id, User.must_change_password.is_(True))
    return session.scalar(stmt) or 0


def professor_departments(session: Session, institution_id: int) -> set[str]:
    stmt = select(User.department).where(
        User.institution_id == institution_id,
        User.role == "professor",
        User.department.is_not(None),
        User.is_active.is_(True),
    )
    return {d for d in session.scalars(stmt) if d}


def add_failed_login(session: Session, user_id: int) -> int:
    """연속 로그인 실패를 1 늘리고 새 값을 돌려준다 (동시에 들어온 시도도 빠짐없이 센다)."""
    session.execute(update(User).where(User.id == user_id).values(failed_logins=User.failed_logins + 1))
    return session.scalar(select(User.failed_logins).where(User.id == user_id)) or 0


def locked_out_count(session: Session, institution_id: int, threshold: int) -> int:
    stmt = select(func.count()).where(User.institution_id == institution_id, User.failed_logins >= threshold)
    return session.scalar(stmt) or 0


def inactive_count(session: Session, institution_id: int) -> int:
    stmt = select(func.count()).where(User.institution_id == institution_id, User.is_active.is_(False))
    return session.scalar(stmt) or 0
