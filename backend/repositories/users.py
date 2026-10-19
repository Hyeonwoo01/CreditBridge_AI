from sqlalchemy import ColumnElement, and_, func, or_, select, update
from sqlalchemy.orm import Session

from backend.models import Department, User


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalars(select(User).where(User.email == email.lower().strip())).first()


def get_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def professors_in(session: Session, institution_id: int, department_id: int | None) -> list[User]:
    if department_id is None:
        return []
    stmt = (
        select(User)
        .where(
            User.institution_id == institution_id,
            User.role == "professor",
            User.department_id == department_id,
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


def professor_departments(session: Session, institution_id: int) -> set[int]:
    """활성 교수가 있는 학과 id."""
    stmt = select(User.department_id).where(
        User.institution_id == institution_id,
        User.role == "professor",
        User.department_id.is_not(None),
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


def _needs_attention(locked_threshold: int) -> ColumnElement[bool]:
    """관리자가 챙길 활성 계정: 로그인 실패로 비밀번호가 초기화된 계정, 출신 대학·편입 전공이 빈 학생."""
    return and_(
        User.is_active.is_(True),
        or_(
            User.failed_logins >= locked_threshold,
            and_(
                User.role == "student",
                or_(User.source_institution_id.is_(None), User.department_id.is_(None)),
            ),
        ),
    )


def attention_count(session: Session, institution_id: int, locked_threshold: int) -> int:
    stmt = select(func.count()).where(User.institution_id == institution_id, _needs_attention(locked_threshold))
    return session.scalar(stmt) or 0


def inactive_count(session: Session, institution_id: int) -> int:
    stmt = select(func.count()).where(User.institution_id == institution_id, User.is_active.is_(False))
    return session.scalar(stmt) or 0


def search(
    session: Session,
    institution_id: int,
    query: str = "",
    role: str | None = None,
    active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    attention_threshold: int | None = None,
) -> tuple[list[User], int]:
    """기관 계정 목록 (관리자). 이메일 일부로 찾고, 역할·활성 여부로 거른다. (행, 전체 건수)."""
    conditions = [User.institution_id == institution_id]
    if query:
        conditions.append(User.email.contains(query.lower(), autoescape=True))
    if role:
        conditions.append(User.role == role)
    if active is not None:
        conditions.append(User.is_active.is_(active))
    if attention_threshold is not None:  # '확인 필요' 칩
        conditions.append(_needs_attention(attention_threshold))
    total = session.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    stmt = select(User).where(*conditions).order_by(User.role, User.email).limit(limit).offset(offset)
    return list(session.scalars(stmt)), total


def by_ids(session: Session, ids: list[int]) -> dict[int, User]:
    if not ids:
        return {}
    return {u.id: u for u in session.scalars(select(User).where(User.id.in_(ids)))}


def professors_of(session: Session, institution_id: int) -> list[User]:
    stmt = (
        select(User)
        .where(User.institution_id == institution_id, User.role == "professor", User.is_active.is_(True))
        .outerjoin(Department, Department.id == User.department_id)
        .order_by(Department.name, User.name)
    )
    return list(session.scalars(stmt))
