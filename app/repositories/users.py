from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


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
