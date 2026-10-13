"""운영 통계 (FR-27): 처리량, 평균 소요일, AI-교수 판정 불일치율 등 학사처장용 지표.

개인 단위가 아니라 기관 단위 집계만 보여준다.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.errors import PermissionDeniedError
from app.models import Decision, User
from app.models.enums import AppealStatus, Role
from app.repositories import appeals as appeal_repo
from app.repositories import decisions as decision_repo
from app.repositories import privacy as privacy_repo
from app.repositories import requests as request_repo
from app.services.privacy import is_overdue


@dataclass
class Stats:
    requests_submitted: int = 0
    requests_decided: int = 0
    courses_decided: int = 0
    avg_days_to_decision: float | None = None
    disagreement_rate: float | None = None  # AI 추천(정보 부족 제외)과 교수 판정이 다른 비율
    disagreement_base: int = 0
    actions: dict[str, int] = field(default_factory=dict)  # 승인·수정·반려
    results: dict[str, int] = field(default_factory=dict)  # 직접·선택·불인정
    appeals_total: int = 0
    appeals_open: int = 0
    appeals_dismissed: int = 0
    appeals_changed: int = 0  # 재판정으로 결과가 바뀐 건
    conflict_acknowledged: int = 0
    privacy_open: int = 0
    privacy_overdue: int = 0
    monthly: list[tuple[str, int]] = field(default_factory=list)  # 최근 6개월 판정 건수


def _months(now: datetime, count: int = 6) -> list[str]:
    out = []
    year, month = now.year, now.month
    for _ in range(count):
        out.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(out))


def institution_stats(session: Session, user: User) -> Stats:
    if user.role not in (Role.ADMIN, Role.EVALUATOR) or user.institution_id is None:
        raise PermissionDeniedError("기관 관리자와 심사관만 볼 수 있어요.")
    institution_id = user.institution_id
    now = utcnow()
    stats = Stats()

    requests = request_repo.submitted_of_institution(session, institution_id)
    stats.requests_submitted = len(requests)
    stats.requests_decided = sum(1 for r in requests if r.status == "decided")
    submitted_at = {r.id: r.submitted_at for r in requests}

    rows = decision_repo.all_for_institution(session, institution_id)
    current: dict[int, Decision] = {}
    first: dict[int, Decision] = {}
    request_of: dict[int, int | None] = {}
    for d, e, _ in rows:
        first.setdefault(e.id, d)
        current[e.id] = d
        request_of[e.id] = e.transfer_request_id
    stats.courses_decided = len(current)

    days = []
    for evaluation_id, d in first.items():
        start = submitted_at.get(request_of[evaluation_id] or 0)
        if start is not None:
            days.append((d.decided_at - start).total_seconds() / 86400)
    stats.avg_days_to_decision = round(sum(days) / len(days), 1) if days else None

    compared = [
        d
        for d in first.values()
        if d.ai_recommendation_snapshot.get("recommendation") in ("direct", "elective", "none")
    ]
    stats.disagreement_base = len(compared)
    if compared:
        differ = sum(1 for d in compared if d.result != d.ai_recommendation_snapshot.get("recommendation"))
        stats.disagreement_rate = round(differ / len(compared), 3)
    stats.actions = dict(Counter(d.action for d in first.values()))
    stats.results = dict(Counter(d.result for d in current.values()))
    stats.conflict_acknowledged = sum(1 for d, _, _ in rows if d.conflict_acknowledged)

    appeals = [a for a, _, _, _ in appeal_repo.of_institution(session, institution_id)]
    stats.appeals_total = len(appeals)
    stats.appeals_open = sum(1 for a in appeals if a.status in (AppealStatus.SUBMITTED, AppealStatus.ACCEPTED))
    stats.appeals_dismissed = sum(1 for a in appeals if a.status == AppealStatus.DISMISSED)
    stats.appeals_changed = sum(
        1
        for a in appeals
        if a.status == AppealStatus.REDECIDED
        and current.get(a.course_evaluation_id) is not None
        and first.get(a.course_evaluation_id) is not None
        and current[a.course_evaluation_id].result != first[a.course_evaluation_id].result
    )

    privacy = [p for p, _ in privacy_repo.of_institution(session, institution_id)]
    stats.privacy_open = sum(1 for p in privacy if p.status != "completed")
    stats.privacy_overdue = sum(1 for p in privacy if is_overdue(p, now))

    per_month = Counter(d.decided_at.strftime("%Y-%m") for d, _, _ in rows)
    stats.monthly = [(m, per_month.get(m, 0)) for m in _months(now)]
    return stats
