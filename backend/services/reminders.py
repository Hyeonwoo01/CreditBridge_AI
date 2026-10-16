"""기한 알림: 매일 한 번(Celery beat, Settings.reminder_hour_utc) 처리 기한이 지났거나 다가온 일을 담당자에게 알린다.

- 교수: 판정 기한(배정 + review_sla_days)이 지났거나 하루 남은 심사
- 심사관: 판정 기한이 지난 심사, 교수 배정 없이 오래 기다린 과목, 처리 기한이 다가온 삭제 요청
- 기관 관리자: 승인 기한이 다가온 삭제 요청
- 학생: 며칠째 답하지 않은 보완 자료 요청

같은 사람에게 같은 종류의 기한 알림은 하루에 한 번만 쌓는다. 메시지에는 건수와 과목 코드만 넣는다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.db.base import utcnow
from backend.i18n import N_
from backend.models import Institution, PrivacyRequest, Syllabus, User
from backend.models.enums import PrivacyStatus, Role
from backend.repositories import catalog as catalog_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import materials as material_repo
from backend.repositories import notifications as notification_repo
from backend.repositories import privacy as privacy_repo
from backend.repositories import users as user_repo
from backend.services import notifications

ONCE_PER = timedelta(hours=20)  # 같은 종류의 기한 알림을 다시 쌓기 전 최소 간격


@dataclass
class Plan:
    """한 대상 대학의 오늘 기한 알림 대상 (관리자 콘솔 미리보기에도 쓴다)."""

    overdue: dict[int, int] = field(default_factory=dict)  # 교수 id → 판정 기한이 지난 심사 수
    due_soon: dict[int, int] = field(default_factory=dict)  # 교수 id → 하루 안에 기한인 심사 수
    unassigned: int = 0  # 교수 배정 없이 reminder_unassigned_days를 넘긴 과목
    privacy_review: list[PrivacyRequest] = field(default_factory=list)  # 심사관 처리 대기, 기한 임박·초과
    privacy_approve: list[PrivacyRequest] = field(default_factory=list)  # 관리자 승인 대기, 기한 임박·초과
    materials: dict[int, list[Syllabus]] = field(default_factory=dict)  # 학생 id → 답하지 않은 과목

    @property
    def overdue_total(self) -> int:
        return sum(self.overdue.values())

    @property
    def materials_total(self) -> int:
        return sum(len(v) for v in self.materials.values())

    @property
    def empty(self) -> bool:
        return (
            not (self.overdue or self.due_soon or self.unassigned or self.privacy_review or self.privacy_approve)
            and not self.materials
        )


def plan(session: Session, institution_id: int, now: datetime | None = None, settings: Settings | None = None) -> Plan:
    settings = settings or get_settings()
    now = now or utcnow()
    sla = timedelta(days=settings.review_sla_days)
    out = Plan()
    for evaluation, _, request in evaluation_repo.review_queue(session, institution_id):
        assignment = evaluation_repo.active_assignment(session, evaluation.id)
        if assignment is None:
            waiting_since = request.submitted_at or evaluation.created_at
            if waiting_since < now - timedelta(days=settings.reminder_unassigned_days):
                out.unassigned += 1
            continue
        due = assignment.assigned_at + sla
        if due <= now:
            out.overdue[assignment.reviewer_id] = out.overdue.get(assignment.reviewer_id, 0) + 1
        elif due <= now + timedelta(days=1):
            out.due_soon[assignment.reviewer_id] = out.due_soon.get(assignment.reviewer_id, 0) + 1
    soon = now + timedelta(days=settings.reminder_privacy_days)
    for privacy, _ in privacy_repo.of_institution(session, institution_id):
        if privacy.due_at > soon:
            continue
        if privacy.status == PrivacyStatus.REQUESTED:
            out.privacy_review.append(privacy)
        elif privacy.status == PrivacyStatus.REVIEWED:
            out.privacy_approve.append(privacy)
    before = now - timedelta(days=settings.reminder_material_days)
    for _, syllabus in material_repo.open_before(session, institution_id, before):
        if syllabus.owner_id is not None:
            out.materials.setdefault(syllabus.owner_id, []).append(syllabus)
    return out


def _course(syllabus: Syllabus) -> str:
    return (syllabus.course_code or syllabus.course_title or N_("강의계획서")).strip()


def _send(session: Session, user: User | None, kind: str, message: str, link: str, now: datetime) -> int:
    if user is None or not user.is_active:
        return 0
    if notification_repo.sent_since(session, user.id, kind, now - ONCE_PER):
        return 0
    notifications.notify(session, [user], kind, message, link)
    return 1


def send_for_institution(session: Session, institution: Institution, now: datetime | None = None) -> int:
    """한 대학의 기한 알림을 쌓고 쌓은 알림 수를 돌려준다. 커밋은 호출한 쪽이 한다."""
    now = now or utcnow()
    p = plan(session, institution.id, now)
    sent = 0
    for professor_id in set(p.overdue) | set(p.due_soon):
        parts = []
        if p.overdue.get(professor_id):
            parts.append(N_("판정 기한이 지난 심사 {n}건").format(n=p.overdue[professor_id]))
        if p.due_soon.get(professor_id):
            parts.append(N_("내일까지 판정할 심사 {n}건").format(n=p.due_soon[professor_id]))
        message = N_("기한 알림: {items}").format(items=" · ".join(parts))
        sent += _send(
            session, user_repo.get_by_id(session, professor_id), "reminder.review", message, "/professor", now
        )
    staff_parts = []
    if p.overdue_total:
        staff_parts.append(N_("판정 기한이 지난 심사 {n}건").format(n=p.overdue_total))
    if p.unassigned:
        staff_parts.append(N_("교수 배정을 기다리는 과목 {n}개").format(n=p.unassigned))
    if p.privacy_review:
        staff_parts.append(N_("처리 기한이 다가온 삭제 요청 {n}건").format(n=len(p.privacy_review)))
    if staff_parts:
        message = N_("기한 알림: {items}").format(items=" · ".join(staff_parts))
        for evaluator in notifications.staff(session, institution.id, Role.EVALUATOR):
            sent += _send(session, evaluator, "reminder.evaluator", message, "/review", now)
    if p.privacy_approve:
        message = N_("기한 알림: {items}").format(
            items=N_("승인 기한이 다가온 삭제 요청 {n}건").format(n=len(p.privacy_approve))
        )
        for admin in notifications.staff(session, institution.id, Role.ADMIN):
            sent += _send(session, admin, "reminder.admin", message, "/admin/privacy", now)
    for student_id, syllabi in p.materials.items():
        courses = ", ".join(sorted({_course(s) for s in syllabi}))
        message = N_("기한 알림: {courses} 보완 자료 요청에 아직 답하지 않았어요. 늦어지면 심사도 늦어져요.").format(
            courses=courses
        )
        link = f"/student/syllabi/{syllabi[0].id}"
        sent += _send(session, user_repo.get_by_id(session, student_id), "reminder.material", message, link, now)
    return sent


def send_daily(session: Session, now: datetime | None = None) -> int:
    """모든 대상 대학의 기한 알림 (작업 큐 reminders.daily). 메일은 이어서 notifications.deliver가 보낸다."""
    total = 0
    for institution in catalog_repo.target_institutions(session):
        total += send_for_institution(session, institution, now)
    session.commit()
    return total
