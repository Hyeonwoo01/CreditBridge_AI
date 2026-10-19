"""기관 계정 목록·수정 (기관 관리자, 권한 매트릭스 "사용자·학과·대리자 설정").

- 목록: 이메일로 찾고 역할·상태로 거른다. 교수·관리자 화면에는 학생 이름을 보여 주지 않으므로 학생 행은 이메일만.
- 수정: 교직원 이름, 교수·심사관의 학과, 교수의 대리 심사자. 역할은 바꾸지 않는다(판정·요청 기록이 역할에 묶여 있어
  새 계정을 만든다). 학과는 과목에 있는 학과명만 고를 수 있다(철자가 다르면 자동 배정이 안 된다).
- 진행 중인 배정은 그대로 둔다. 감사 로그에는 바뀐 항목 이름만 남기고 값(이름)은 남기지 않는다.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.errors import CreditBridgeError, NotFoundError
from backend.i18n import gettext as tr
from backend.models import Department, User
from backend.models.enums import Role
from backend.repositories import catalog as catalog_repo
from backend.repositories import users as user_repo
from backend.services import audit
from backend.services.auth import RESET_AFTER
from backend.services.institution_data import ensure_admin

PAGE_SIZE = 50
STATUSES = ("active", "inactive", "all")
STAFF = (Role.EVALUATOR, Role.PROFESSOR, Role.ADMIN)
MAX_NAME = 100


@dataclass(frozen=True)
class AccountRow:
    user: User
    delegate: User | None

    @property
    def show_name(self) -> bool:
        return self.user.role in STAFF

    @property
    def state(self) -> str:
        """inactive(비활성) / locked(로그인 실패로 초기화) / pending(첫 비밀번호 변경 대기) / active."""
        if not self.user.is_active:
            return "inactive"
        if self.user.failed_logins >= RESET_AFTER:
            return "locked"
        if self.user.must_change_password:
            return "pending"
        return "active"


@dataclass(frozen=True)
class AccountList:
    rows: list[AccountRow]
    total: int
    page: int
    query: str
    role: str
    status: str

    @property
    def pages(self) -> int:
        return max((self.total + PAGE_SIZE - 1) // PAGE_SIZE, 1)

    @property
    def first(self) -> int:
        return (self.page - 1) * PAGE_SIZE + 1 if self.total else 0

    @property
    def last(self) -> int:
        return min(self.page * PAGE_SIZE, self.total)


def list_accounts(session: Session, admin: User, query: str, role: str, status: str, page: int) -> AccountList:
    institution_id = ensure_admin(admin)
    role = role if role in {r.value for r in Role} else ""
    status = status if status in STATUSES else "active"
    query = query.strip()
    active = None if status == "all" else status == "active"
    users, total = user_repo.search(
        session, institution_id, query, role or None, active, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE
    )
    delegates = user_repo.by_ids(session, [u.delegate_user_id for u in users if u.delegate_user_id])
    rows = [AccountRow(u, delegates.get(u.delegate_user_id) if u.delegate_user_id else None) for u in users]
    return AccountList(rows, total, page, query, role, status)


@dataclass(frozen=True)
class AccountForm:
    row: AccountRow
    departments: list[Department]  # 과목이 있는 학과 (+ 지금 학과가 목록에 없으면 그 학과)
    delegate_options: list[User]  # 같은 기관의 다른 활성 교수 (학과별로 정렬)

    @property
    def user(self) -> User:
        return self.row.user


def _load(session: Session, admin: User, user_id: int) -> tuple[int, User]:
    institution_id = ensure_admin(admin)
    user = user_repo.get_by_id(session, user_id)
    if user is None or user.institution_id != institution_id:
        raise NotFoundError(tr("우리 기관에 그 계정이 없어요."))
    return institution_id, user


def account_form(session: Session, admin: User, user_id: int) -> AccountForm:
    institution_id, user = _load(session, admin, user_id)
    departments = catalog_repo.course_departments(session, institution_id)
    if user.dept is not None and user.dept not in departments:
        departments = [user.dept, *departments]
    delegate = user_repo.get_by_id(session, user.delegate_user_id) if user.delegate_user_id else None
    options = [p for p in user_repo.professors_of(session, institution_id) if p.id != user.id]
    return AccountForm(AccountRow(user, delegate), departments, options)


def update_account(
    session: Session, admin: User, user_id: int, name: str, department_id: int | None, delegate_id: int | None
) -> list[str]:
    """교직원 이름·학과·대리 심사자를 고친다. 바뀐 항목 이름을 돌려준다 (없으면 빈 목록)."""
    institution_id, user = _load(session, admin, user_id)
    changed: list[str] = []

    if user.role in STAFF:
        name = name.strip()
        if not name:
            raise CreditBridgeError(tr("이름을 적어 주세요."))
        if len(name) > MAX_NAME:
            raise CreditBridgeError(tr("이름은 {max_name}자까지 적을 수 있어요.", max_name=MAX_NAME))
        if name != user.name:
            user.name = name
            changed.append("name")

    if user.role in (Role.PROFESSOR, Role.EVALUATOR):
        department_id = department_id or None
        if (
            department_id is not None
            and department_id != user.department_id
            and department_id not in {d.id for d in catalog_repo.course_departments(session, institution_id)}
        ):
            raise CreditBridgeError(tr("과목에 있는 학과 이름을 골라 주세요."))
        if user.role == Role.PROFESSOR and department_id is None:
            raise CreditBridgeError(tr("교수는 학과를 골라야 심사를 배정받을 수 있어요."))
        if department_id != user.department_id:
            user.department_id = department_id
            changed.append("department")

    if user.role == Role.PROFESSOR:
        if delegate_id:
            delegate = user_repo.get_by_id(session, delegate_id)
            if (
                delegate is None
                or delegate.id == user.id
                or delegate.institution_id != institution_id
                or delegate.role != Role.PROFESSOR
                or not delegate.is_active
            ):
                raise CreditBridgeError(tr("우리 기관의 다른 교수를 대리 심사자로 골라 주세요."))
        if (delegate_id or None) != user.delegate_user_id:
            user.delegate_user_id = delegate_id or None
            changed.append("delegate")

    if changed:
        audit.record(session, admin, "account.update", "user", str(user.id), fields=changed)
        session.commit()
    return changed
