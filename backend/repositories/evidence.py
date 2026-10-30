"""근거 구절 품질: 교수의 맞음·틀림과 AI 인용 구절 수 집계."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import CourseEvaluation, EvidenceFeedback, EvidenceSpan, TransferRequest


def get_span(session: Session, span_id: int) -> EvidenceSpan | None:
    return session.get(EvidenceSpan, span_id)


def feedback_for(session: Session, span_id: int, user_id: int) -> EvidenceFeedback | None:
    stmt = select(EvidenceFeedback).where(
        EvidenceFeedback.evidence_span_id == span_id, EvidenceFeedback.user_id == user_id
    )
    return session.scalars(stmt).first()


def add_feedback(session: Session, feedback: EvidenceFeedback) -> None:
    session.add(feedback)
    session.flush()


def feedback_of_user(session: Session, evaluation_id: int, user_id: int) -> dict[int, str]:
    """한 분석 결과에서 이 사용자가 누른 맞음·틀림 (구절 id -> verdict)."""
    stmt = (
        select(EvidenceFeedback.evidence_span_id, EvidenceFeedback.verdict)
        .join(EvidenceSpan, EvidenceSpan.id == EvidenceFeedback.evidence_span_id)
        .where(EvidenceSpan.course_evaluation_id == evaluation_id, EvidenceFeedback.user_id == user_id)
    )
    return {span_id: verdict for span_id, verdict in session.execute(stmt)}


def quote_counts_by_prompt(session: Session, target_institution_id: int) -> list[tuple[str, int, int, int, int]]:
    """대상 대학의 AI 비교를 프롬프트 버전별로: (버전, 분석 수, 인용 수, 원문에 없어 버림, 가르친 근거 아니라 버림).
    이전 결과를 재사용한 분석(인용 수가 비어 있음)은 세지 않는다."""
    stmt = (
        select(
            CourseEvaluation.prompt_version,
            func.count(),
            func.sum(CourseEvaluation.quotes_total),
            func.sum(CourseEvaluation.quotes_unmatched),
            func.sum(CourseEvaluation.quotes_non_teaching),
        )
        .join(TransferRequest, TransferRequest.id == CourseEvaluation.transfer_request_id)
        .where(
            TransferRequest.target_institution_id == target_institution_id, CourseEvaluation.quotes_total.is_not(None)
        )
        .group_by(CourseEvaluation.prompt_version)
    )
    return [
        (v or "", n, total or 0, unmatched or 0, non_teaching or 0)
        for v, n, total, unmatched, non_teaching in session.execute(stmt)
    ]


def feedback_by_prompt(session: Session, target_institution_id: int) -> list[tuple[str, str, int]]:
    """교수가 누른 맞음·틀림을 프롬프트 버전별로: (버전, verdict, 수)."""
    stmt = (
        select(CourseEvaluation.prompt_version, EvidenceFeedback.verdict, func.count())
        .join(EvidenceSpan, EvidenceSpan.id == EvidenceFeedback.evidence_span_id)
        .join(CourseEvaluation, CourseEvaluation.id == EvidenceSpan.course_evaluation_id)
        .join(TransferRequest, TransferRequest.id == CourseEvaluation.transfer_request_id)
        .where(TransferRequest.target_institution_id == target_institution_id)
        .group_by(CourseEvaluation.prompt_version, EvidenceFeedback.verdict)
    )
    return [(v or "", verdict, n) for v, verdict, n in session.execute(stmt)]
