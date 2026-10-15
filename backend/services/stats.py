"""운영 통계 (FR-27): 처리량, 평균 소요일, AI-교수 판정 불일치율 등 학사처장용 지표.

개인 단위가 아니라 기관 단위 집계만 보여준다.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.errors import PermissionDeniedError
from backend.models import AuditLog, Decision, User
from backend.models.enums import AppealStatus, Role
from backend.repositories import appeals as appeal_repo
from backend.repositories import audit as audit_repo
from backend.repositories import catalog as catalog_repo
from backend.repositories import decisions as decision_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import privacy as privacy_repo
from backend.repositories import requests as request_repo
from backend.repositories import users as user_repo
from backend.services.privacy import is_overdue


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
    queue_waiting: int = 0  # 판정을 기다리는 과목
    departments: list["DepartmentStat"] = field(default_factory=list)
    transcripts_masked: int = 0  # 이름·학번을 가리고 분석한 성적표
    privacy_completed: int = 0
    privacy_on_time: int = 0
    sis_token: bool = False

    @property
    def acceptance_rate(self) -> float | None:
        """교수가 AI 추천과 같은 결과로 판정한 비율 (정보 부족 제외, 첫 판정 기준)."""
        return None if self.disagreement_rate is None else round(1 - self.disagreement_rate, 3)


@dataclass(frozen=True)
class DepartmentStat:
    name: str
    received: int  # 심사 큐에 들어온 과목 (대기 + 판정)
    decided: int
    avg_days: float | None

    @property
    def rate(self) -> float:
        return self.decided / self.received if self.received else 0.0


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

    # 학과별 처리 지표: 판정 대상 과목(판정했으면 판정 과목, 아니면 AI 후보)의 학과 기준
    waiting = evaluation_repo.review_queue(session, institution_id)
    stats.queue_waiting = len(waiting)
    candidate_of = {e.id: e.candidate_course_id for _, e, _ in rows}
    course_ids: list[int] = [e.candidate_course_id for e, _, _ in waiting if e.candidate_course_id]
    for evaluation_id, d in current.items():
        target = d.target_course_id or candidate_of.get(evaluation_id)
        if target:
            course_ids.append(target)
    courses = catalog_repo.courses_by_ids(session, course_ids)
    received: Counter[str] = Counter()
    decided: Counter[str] = Counter()
    dept_days: dict[str, list[float]] = {}
    for e, _, _ in waiting:
        course = courses.get(e.candidate_course_id) if e.candidate_course_id else None
        received[course.department if course else "미분류"] += 1
    for evaluation_id, d in current.items():
        target = d.target_course_id or candidate_of.get(evaluation_id)
        course = courses.get(target) if target else None
        name = course.department if course else "미분류"
        received[name] += 1
        decided[name] += 1
        start = submitted_at.get(request_of[evaluation_id] or 0)
        if start is not None:
            dept_days.setdefault(name, []).append((first[evaluation_id].decided_at - start).total_seconds() / 86400)
    stats.departments = sorted(
        (
            DepartmentStat(
                name=name,
                received=count,
                decided=decided[name],
                avg_days=round(sum(dept_days[name]) / len(dept_days[name]), 1) if dept_days.get(name) else None,
            )
            for name, count in received.items()
        ),
        key=lambda d: -d.received,
    )

    stats.transcripts_masked = sum(1 for r in requests if r.transcript_masked_name)
    done = [p for p in privacy if p.status == "completed" and p.completed_at is not None]
    stats.privacy_completed = len(done)
    stats.privacy_on_time = sum(1 for p in done if p.completed_at and p.completed_at <= p.due_at)
    institution = catalog_repo.get_institution(session, institution_id)
    stats.sis_token = bool(institution and institution.sis_token_hash)
    return stats


# 감사 로그 행위 → 화면 표시 (이름, 배지 톤)
ACTION_LABELS = {
    "decision.create": ("판정 확정", "decision"),
    "assignment.create": ("교수 배정", "neutral"),
    "material.request": ("보완 서류 요청", "elective"),
    "material.fulfilled": ("보완 서류 제출", "neutral"),
    "appeal.submit": ("이의 신청 접수", "elective"),
    "appeal.accept": ("이의 신청 수용", "neutral"),
    "appeal.dismiss": ("이의 신청 기각", "reject"),
    "privacy.request": ("삭제 요청", "elective"),
    "privacy.review": ("삭제 요청 처리", "neutral"),
    "privacy.delete_documents": ("문서 삭제 완료", "reject"),
    "request.submit": ("심사 요청", "neutral"),
    "syllabus.upload": ("강의계획서 업로드", "neutral"),
    "syllabus.supplement": ("보완 자료 업로드", "neutral"),
    "sis.token_issue": ("연동 토큰 발급", "neutral"),
    "sis.token_revoke": ("연동 토큰 폐기", "neutral"),
    "equivalency.import": ("동등 과목표 가져오기", "neutral"),
    "professor.away": ("부재 설정", "neutral"),
    "auth.login": ("로그인", "neutral"),
    "auth.password_change": ("비밀번호 변경", "neutral"),
    "auth.password_reset_request": ("비밀번호 재설정 요청", "neutral"),
    "auth.password_reset": ("비밀번호 재설정", "neutral"),
    "auth.lockout": ("로그인 1분 잠금", "elective"),
    "auth.lockout_reset": ("로그인 실패로 비밀번호 초기화", "reject"),
    "account.password_reset_by_admin": ("임시 비밀번호 재발급", "elective"),
    "account.import": ("계정 가져오기", "neutral"),
    "account.bootstrap": ("첫 관리자 생성", "neutral"),
    "course.import": ("과목 가져오기", "neutral"),
    "course.reference_upload": ("기준 강의계획서 등록", "neutral"),
    "institution.create": ("출신 대학 등록", "neutral"),
}


@dataclass(frozen=True)
class AuditRow:
    log: AuditLog
    actor: User | None
    label: str
    tone: str  # decision(결과 색) / elective / reject / neutral
    result: str | None  # 판정 결과 (decision.create)
    ai: str | None  # 판정 당시 AI 추천
    reasons: list[str]


def recent_audit(session: Session, user: User, limit: int = 8) -> list[AuditRow]:
    """소속 기관 사용자가 남긴 최근 감사 로그 (로그인 기록 제외)."""
    if user.role != Role.ADMIN or user.institution_id is None:
        raise PermissionDeniedError("기관 관리자만 볼 수 있어요.")
    out: list[AuditRow] = []
    actors: dict[int, User | None] = {}
    for log in audit_repo.recent(session, limit=300):
        if log.action == "auth.login":
            continue
        if log.actor_id is not None and log.actor_id not in actors:
            actors[log.actor_id] = user_repo.get_by_id(session, log.actor_id)
        actor = actors.get(log.actor_id) if log.actor_id is not None else None
        if actor is None or actor.institution_id != user.institution_id:
            continue
        label, tone = ACTION_LABELS.get(log.action, (log.action, "neutral"))
        payload = log.payload_json or {}
        out.append(
            AuditRow(
                log=log,
                actor=actor,
                label=label,
                tone=tone,
                result=payload.get("result"),
                ai=payload.get("ai_recommendation"),
                reasons=list(payload.get("reason_codes") or []),
            )
        )
        if len(out) >= limit:
            break
    return out


@dataclass(frozen=True)
class WorkspaceCounts:
    institution: str
    submitted: int
    waiting: int
    decided: int


def workspace_counts(session: Session, user: User) -> WorkspaceCounts | None:
    """심사관·교수·관리자 화면 상단 보조 바의 기관 집계. 학생에게는 보여주지 않는다."""
    if user.role == Role.STUDENT or user.institution_id is None:
        return None
    institution = catalog_repo.get_institution(session, user.institution_id)
    rows = decision_repo.all_for_institution(session, user.institution_id)
    return WorkspaceCounts(
        institution=institution.name if institution else "",
        submitted=len(request_repo.submitted_of_institution(session, user.institution_id)),
        waiting=len(evaluation_repo.review_queue(session, user.institution_id)),
        decided=len({e.id for _, e, _ in rows}),
    )
