"""교수가 근거 구절마다 누르는 맞음·틀림과 AI 근거 품질 지표.

맞음·틀림은 판정이 아니라 AI 근거의 품질 표시라 다시 누르면 고친다. 쌓인 값으로 AI 근거 정확도를 재고,
프롬프트 버전별로 원문에 없어서 버린 인용(환각) 비율과 함께 운영 통계에 보여 준다.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.errors import NotFoundError, PermissionDeniedError
from backend.i18n import gettext as tr
from backend.models import EvidenceFeedback, User
from backend.models.enums import EvidenceVerdict, Role
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import evidence as evidence_repo
from backend.security.permissions import ensure_can_view_evaluation


def record(session: Session, user: User, evaluation_id: int, span_id: int, verdict: str) -> str:
    """담당 교수가 누른 맞음·틀림을 저장하고 저장된 값을 돌려준다."""
    if user.role != Role.PROFESSOR:
        raise PermissionDeniedError(tr("담당 교수만 근거를 확인할 수 있어요."))
    if verdict not in set(EvidenceVerdict):
        raise NotFoundError(tr("알 수 없는 값이에요."))
    evaluation = evaluation_repo.get(session, evaluation_id)
    span = evidence_repo.get_span(session, span_id)
    if evaluation is None or span is None or span.course_evaluation_id != evaluation.id:
        raise NotFoundError(tr("근거 구절을 찾을 수 없어요."))
    ensure_can_view_evaluation(session, user, evaluation)
    feedback = evidence_repo.feedback_for(session, span.id, user.id)
    if feedback is None:
        evidence_repo.add_feedback(
            session, EvidenceFeedback(evidence_span_id=span.id, user_id=user.id, verdict=verdict)
        )
    else:
        feedback.verdict = verdict
        feedback.updated_at = utcnow()
    session.commit()
    return verdict


def mine(session: Session, user: User, evaluation_id: int) -> dict[int, str]:
    return evidence_repo.feedback_of_user(session, evaluation_id, user.id) if user.role == Role.PROFESSOR else {}


@dataclass(frozen=True)
class PromptQuality:
    """프롬프트 버전 하나의 AI 근거 품질."""

    prompt_version: str
    evaluations: int  # 새로 AI를 불러 비교한 분석 수
    quotes: int
    unmatched: int  # 원문에 없어서 버린 인용 (지어낸 인용)
    non_teaching: int  # 원문에는 있지만 선수과목·교재 칸이나 부정 문장이라 버린 인용
    correct: int  # 교수가 맞음으로 누른 근거
    wrong: int

    @property
    def unmatched_rate(self) -> float | None:
        return self.unmatched / self.quotes if self.quotes else None

    @property
    def non_teaching_rate(self) -> float | None:
        return self.non_teaching / self.quotes if self.quotes else None

    @property
    def checked(self) -> int:
        return self.correct + self.wrong

    @property
    def precision(self) -> float | None:
        """교수가 확인한 근거 중 맞음 비율."""
        return self.correct / self.checked if self.checked else None


def quality_by_prompt(session: Session, target_institution_id: int) -> list[PromptQuality]:
    counts = {
        v: (n, total, unmatched, non_teaching)
        for v, n, total, unmatched, non_teaching in evidence_repo.quote_counts_by_prompt(session, target_institution_id)
    }
    votes: dict[str, dict[str, int]] = {}
    for version, verdict, n in evidence_repo.feedback_by_prompt(session, target_institution_id):
        votes.setdefault(version, {})[verdict] = n
    out = []
    for version in sorted(set(counts) | set(votes), reverse=True):
        n, total, unmatched, non_teaching = counts.get(version, (0, 0, 0, 0))
        v = votes.get(version, {})
        out.append(
            PromptQuality(
                version or "–",
                n,
                total,
                unmatched,
                non_teaching,
                v.get(EvidenceVerdict.CORRECT, 0),
                v.get(EvidenceVerdict.WRONG, 0),
            )
        )
    return out
