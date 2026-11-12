"""중복 저장 값 정합성 점검 (ERD R2, open-issues H8).

운영자가 scripts/integrity_check.py로 돌리고, 테스트(tests/integration/test_integrity.py)가 매번 확인한다."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.repositories import integrity as integrity_repo


@dataclass(frozen=True)
class Problem:
    name: str
    table: str
    description: str
    count: int
    ids: list[int]


def run(session: Session) -> list[Problem]:
    """어긋난 곳이 있는 점검만 돌려준다 (빈 목록이면 모두 맞음)."""
    out = []
    for check in integrity_repo.CHECKS:
        count, ids = integrity_repo.mismatched_ids(session, check)
        if count:
            out.append(Problem(check.name, check.table, check.description, count, ids))
    return out
