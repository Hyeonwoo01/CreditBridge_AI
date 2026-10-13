"""학사정보시스템 내보내기 (FR-24, NF-10): 확정 판정을 CSV와 토큰 인증 JSON API로 내보낸다.

이의 신청으로 재판정된 건은 최신 판정만 내보내고, 대체한 이전 판정 번호(replaces_decision_id)를 함께 준다.
"""

import hashlib
import secrets
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.errors import PermissionDeniedError
from app.models import Decision, Institution, User
from app.models.enums import Role
from app.repositories import catalog as catalog_repo
from app.repositories import decisions as decision_repo
from app.repositories import requests as request_repo
from app.services import audit

FIELDS = [
    "decision_id",
    "replaces_decision_id",
    "student_id",
    "source_institution",
    "source_course",
    "result",
    "target_course",
    "credits",
    "decided_at",
]


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def export_rows(session: Session, institution_id: int, since: datetime | None = None) -> list[dict[str, Any]]:
    """심사 건마다 현재 유효한 판정 한 줄."""
    rows = decision_repo.all_for_institution(session, institution_id)
    latest: dict[int, tuple[Decision, Any, Any]] = {}
    previous: dict[int, int] = {}
    for d, e, s in rows:  # 판정 순이므로 마지막이 현재 판정
        if e.id in latest:
            previous[e.id] = latest[e.id][0].id
        latest[e.id] = (d, e, s)
    courses = catalog_repo.courses_by_ids(
        session, [d.target_course_id for d, _, _ in latest.values() if d.target_course_id]
    )
    out = []
    for d, e, s in latest.values():
        if since is not None and d.decided_at < since:
            continue
        request = request_repo.get(session, e.transfer_request_id) if e.transfer_request_id else None
        out.append(
            {
                "decision_id": d.id,
                "replaces_decision_id": previous.get(e.id, ""),
                "student_id": request.student_id if request else "",
                "source_institution": request.source_institution.name if request else "",
                "source_course": s.course_code or s.course_title,
                "result": d.result,
                "target_course": courses[d.target_course_id].code if d.target_course_id in courses else "",
                "credits": s.credits if s.credits is not None else "",
                "decided_at": d.decided_at.isoformat(timespec="seconds") + "Z",
            }
        )
    out.sort(key=lambda r: r["decision_id"])
    return out


def issue_token(session: Session, admin: User) -> str:
    """새 연동 토큰을 발급한다. 이전 토큰은 즉시 무효가 된다. 원문은 이때 한 번만 돌려준다."""
    institution = _own_institution(session, admin)
    token = "cbsis_" + secrets.token_urlsafe(32)
    institution.sis_token_hash = _hash(token)
    audit.record(session, admin, "sis.token_issue", "institution", str(institution.id))
    session.commit()
    return token


def revoke_token(session: Session, admin: User) -> None:
    institution = _own_institution(session, admin)
    institution.sis_token_hash = None
    audit.record(session, admin, "sis.token_revoke", "institution", str(institution.id))
    session.commit()


def institution_for_token(session: Session, token: str) -> Institution | None:
    if not token.startswith("cbsis_"):
        return None
    return catalog_repo.institution_by_token_hash(session, _hash(token))


def has_token(session: Session, admin: User) -> bool:
    return _own_institution(session, admin).sis_token_hash is not None


def _own_institution(session: Session, admin: User) -> Institution:
    institution = catalog_repo.get_institution(session, admin.institution_id) if admin.institution_id else None
    if admin.role != Role.ADMIN or institution is None or not institution.is_target:
        raise PermissionDeniedError("대상 대학의 기관 관리자만 연동 토큰을 관리할 수 있어요.")
    return institution
