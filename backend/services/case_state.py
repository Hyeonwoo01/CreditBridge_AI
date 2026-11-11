"""심사 건 상태 머신과 동시 수정 방지 (리뷰 v3 P0-6).

상태는 따로 저장하지 않고 이미 있는 기록(분석·판정·배정·보완 요청·이의 신청·요청 상태)에서 계산한다. 그래서 상태와
기록이 어긋날 일이 없다. 각 처리(판정·배정·보완 요청·증거 상태·이의 신청 처리)는 허용된 상태에서만 할 수 있다.

동시 수정: 화면은 그때의 상태 토큰(token)을 함께 보낸다. 저장할 때 심사 건 행을 잠그고(SELECT … FOR UPDATE)
토큰을 다시 계산해 다르면 덮어쓰지 않고 다시 보라고 알린다 (낙관적 잠금). 판정 뒤 정정은 덮어쓰지 않고
이의 신청 재판정(새 판정 행)으로만 한다.
"""

import hashlib
from enum import StrEnum

from sqlalchemy.orm import Session

from backend.errors import ConcurrentChangeError, DecisionValidationError, NotFoundError
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import CourseEvaluation
from backend.models.enums import AppealStatus, EvaluationStatus, RequestStatus
from backend.repositories import appeals as appeal_repo
from backend.repositories import decisions as decision_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import materials as material_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo


class CaseState(StrEnum):
    DRAFT = "draft"  # 학생이 아직 심사를 요청하지 않음 (사전 시뮬레이션)
    ANALYZING = "analyzing"
    ANALYSIS_FAILED = "analysis_failed"
    SUPERSEDED = "superseded"  # 다시 분석한 최신 결과가 따로 있음
    NEEDS_INFORMATION = "needs_information"  # 보완 자료 대기
    ASSIGNMENT_PENDING = "assignment_pending"
    UNDER_REVIEW = "under_review"  # 교수 배정됨, 판정 전
    DECIDED = "decided"
    APPEAL_SUBMITTED = "appeal_submitted"
    APPEAL_REVIEW = "appeal_review"  # 이의 신청 받아들임, 재판정 대기
    CLOSED = "closed"  # 문서 삭제로 종료


LABELS = {
    CaseState.DRAFT: N_("제출 전"),
    CaseState.ANALYZING: N_("AI 분석 중"),
    CaseState.ANALYSIS_FAILED: N_("AI 분석 실패"),
    CaseState.SUPERSEDED: N_("이전 분석 (최신 결과 있음)"),
    CaseState.NEEDS_INFORMATION: N_("보완 자료 대기"),
    CaseState.ASSIGNMENT_PENDING: N_("교수 배정 대기"),
    CaseState.UNDER_REVIEW: N_("교수 심사 중"),
    CaseState.DECIDED: N_("판정 완료"),
    CaseState.APPEAL_SUBMITTED: N_("이의 신청 접수"),
    CaseState.APPEAL_REVIEW: N_("이의 신청 재판정 중"),
    CaseState.CLOSED: N_("문서 삭제로 종료"),
}

# 처리 → 허용 상태 (전이 표). 판정은 교수 심사 중이나 이의 신청 재판정 중일 때만 할 수 있다
ALLOWED: dict[str, frozenset[CaseState]] = {
    "decide": frozenset({CaseState.UNDER_REVIEW, CaseState.NEEDS_INFORMATION, CaseState.APPEAL_REVIEW}),
    "assign": frozenset({CaseState.ASSIGNMENT_PENDING, CaseState.UNDER_REVIEW, CaseState.NEEDS_INFORMATION}),
    "request_materials": frozenset({CaseState.ASSIGNMENT_PENDING, CaseState.UNDER_REVIEW, CaseState.NEEDS_INFORMATION}),
    "evidence_status": frozenset(
        {
            CaseState.ASSIGNMENT_PENDING,
            CaseState.UNDER_REVIEW,
            CaseState.NEEDS_INFORMATION,
            CaseState.APPEAL_SUBMITTED,
            CaseState.APPEAL_REVIEW,
            CaseState.DRAFT,
            CaseState.DECIDED,  # 판정 뒤 위조가 드러나도 기록은 남긴다 (판정은 그대로, 정정은 이의 신청으로)
        }
    ),
    "appeal_process": frozenset({CaseState.APPEAL_SUBMITTED}),
}

BLOCKED_MESSAGES = {
    CaseState.SUPERSEDED: N_("다시 분석한 최신 결과가 있어요. 최신 결과 화면에서 처리해 주세요."),
    CaseState.ANALYZING: N_("AI 분석이 끝난 뒤에 처리할 수 있어요."),
    CaseState.ANALYSIS_FAILED: N_("AI 분석이 실패한 건이에요. 다시 분석한 뒤 처리해 주세요."),
    CaseState.DECIDED: N_("이미 판정된 건이에요. 정정은 이의 신청 재판정으로만 할 수 있어요."),
    CaseState.CLOSED: N_("문서 삭제로 종료된 건이에요."),
    CaseState.DRAFT: N_("학생이 아직 심사를 요청하지 않은 건이에요."),
}


def state_of(session: Session, evaluation: CourseEvaluation) -> CaseState:
    request = request_repo.get(session, evaluation.transfer_request_id) if evaluation.transfer_request_id else None
    if request is not None and request.status == RequestStatus.CLOSED:
        return CaseState.CLOSED
    if not evaluation.is_latest:
        return CaseState.SUPERSEDED
    if evaluation.status in (EvaluationStatus.QUEUED, EvaluationStatus.RUNNING):
        return CaseState.ANALYZING
    if evaluation.status == EvaluationStatus.FAILED:
        return CaseState.ANALYSIS_FAILED
    if request is not None and request.status == RequestStatus.DRAFT:
        return CaseState.DRAFT
    if decision_repo.for_evaluation(session, evaluation.id) is not None:
        appeals = appeal_repo.for_evaluation(session, evaluation.id)
        if any(a.status == AppealStatus.ACCEPTED for a in appeals):
            return CaseState.APPEAL_REVIEW
        if any(a.status == AppealStatus.SUBMITTED for a in appeals):
            return CaseState.APPEAL_SUBMITTED
        return CaseState.DECIDED
    if material_repo.open_for_syllabus(session, evaluation.syllabus_id):
        return CaseState.NEEDS_INFORMATION
    if evaluation_repo.active_assignment(session, evaluation.id) is not None:
        return CaseState.UNDER_REVIEW
    return CaseState.ASSIGNMENT_PENDING


def token(session: Session, evaluation: CourseEvaluation) -> str:
    """심사 건의 지금 상태를 나타내는 짧은 토큰. 판정·배정·보완 요청·이의 신청·증거 확인이 바뀌면 달라진다."""
    decisions = [d.id for d in decision_repo.for_evaluation_all(session, evaluation.id)]
    assignment = evaluation_repo.active_assignment(session, evaluation.id)
    materials = [m.id for m in material_repo.open_for_syllabus(session, evaluation.syllabus_id)]
    appeals = [(a.id, a.status) for a in appeal_repo.for_evaluation(session, evaluation.id)]
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    parts = (
        evaluation.id,
        evaluation.is_latest,
        evaluation.status,
        decisions,
        assignment.id if assignment else None,
        materials,
        appeals,
        syllabus.verified_at.isoformat() if syllabus and syllabus.verified_at else None,
    )
    return hashlib.sha256(repr(parts).encode()).hexdigest()[:16]


def ensure(session: Session, evaluation_id: int, action: str, expected_token: str | None = None) -> CourseEvaluation:
    """심사 건 행을 잠그고, 화면이 본 뒤 바뀌지 않았는지(토큰)와 이 처리가 지금 상태에서 허용되는지 확인한다."""
    evaluation = evaluation_repo.lock(session, evaluation_id)
    if evaluation is None:
        raise NotFoundError(tr("심사 건을 찾을 수 없어요."))
    if expected_token and expected_token != token(session, evaluation):
        raise ConcurrentChangeError(
            tr("화면을 연 뒤 다른 사람이 이 심사 건을 바꿨어요. 새로 고침해 바뀐 내용을 확인한 뒤 다시 해 주세요.")
        )
    state = state_of(session, evaluation)
    if state not in ALLOWED[action]:
        message = BLOCKED_MESSAGES.get(state, N_("지금 상태({state})에서는 할 수 없는 처리예요."))
        raise DecisionValidationError(tr(message, state=tr(LABELS[state])) if "{state}" in message else tr(message))
    return evaluation
