"""교수 최종 판정(FR-09), 판정 이력(FR-10), 일관성 경보(FR-11).

AI에는 확정 경로가 없다. 판정은 배정된 교수 사용자만 저장할 수 있고 decided_by가 반드시 기록된다.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from app.errors import DecisionValidationError, NotFoundError, PermissionDeniedError
from app.models import Course, CourseEvaluation, Decision, Syllabus, User
from app.models.enums import DecisionAction, DecisionResult, ReasonCode, RequestStatus, Role
from app.repositories import catalog as catalog_repo
from app.repositories import decisions as decision_repo
from app.repositories import evaluations as evaluation_repo
from app.repositories import requests as request_repo
from app.repositories import syllabi as syllabus_repo
from app.services import audit

# 강의계획서 내용이 이 비율 이상 같으면 '같은 강의계획서'로 본다. 첫 측정 후 확정한다 (기능명세서 FR-11).
SIMILARITY_MIN = 0.80
REASON_LABELS = {
    ReasonCode.WEEKS_INSUFFICIENT: "주차 범위 부족",
    ReasonCode.LEVEL_DIFFERENCE: "수준 차이",
    ReasonCode.NO_LAB: "실험·실습 미포함",
    ReasonCode.PREREQUISITE_DIFFERENCE: "선수과목 차이",
    ReasonCode.OTHER: "기타",
}


class ConflictNeedsAcknowledgement(DecisionValidationError):
    """상충하는 과거 판정이 있다 — 확인 후 다시 제출해야 한다."""


@dataclass(frozen=True)
class HistoryItem:
    decided_at: datetime
    result: str
    target_code: str | None
    reason_codes: list[str]
    reason_memo: str
    evaluation_id: int
    similarity: float  # 현재 강의계획서와의 내용 유사도 0~1
    same_target: bool  # 같은 대상 과목을 두고 내린 판정인지

    @property
    def same_syllabus(self) -> bool:
        return self.similarity >= SIMILARITY_MIN


def course_key(syllabus: Syllabus) -> str:
    """같은 과목 판별 키: 과목 코드(없으면 과목명)를 소문자·공백 제거로 정규화. SQL 쪽 정규화와 같아야 한다."""
    return (syllabus.course_code or syllabus.course_title).lower().replace(" ", "")


def similarity(a: str, b: str) -> float:
    def norm(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    if not a.strip() or not b.strip():
        return 0.0
    return round(SequenceMatcher(None, norm(a), norm(b), autojunk=False).ratio(), 3)


def history(session: Session, evaluation: CourseEvaluation) -> list[HistoryItem]:
    """같은 출신 대학·같은 과목의 과거 판정. 화면에는 모두 보여주고, 경보는 conflicts()가 고른다."""
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    if syllabus is None:
        return []
    rows = decision_repo.history_for_course(
        session, syllabus.institution_id, course_key(syllabus), exclude_evaluation_id=evaluation.id
    )
    courses = catalog_repo.courses_by_ids(session, [d.target_course_id for d, _, _ in rows if d.target_course_id])
    items = []
    for d, past_eval, past_syllabus in rows:
        past_target = d.target_course_id or past_eval.candidate_course_id
        items.append(
            HistoryItem(
                decided_at=d.decided_at,
                result=d.result,
                target_code=courses[d.target_course_id].code if d.target_course_id in courses else None,
                reason_codes=list(d.reason_codes or []),
                reason_memo=d.reason_memo,
                evaluation_id=past_eval.id,
                similarity=similarity(syllabus.raw_text, past_syllabus.raw_text),
                same_target=past_target is not None and past_target == evaluation.candidate_course_id,
            )
        )
    return items


def conflicts(items: list[HistoryItem], result: str) -> list[HistoryItem]:
    """상충 조건(같은 출신 대학·과목, 같은 대상 과목, 강의계획서 내용 유사, 판정 결과 다름)을 모두 만족하는 이력."""
    return [h for h in items if h.same_target and h.same_syllabus and h.result != result]


def ai_result(evaluation: CourseEvaluation) -> str:
    rec = evaluation.recommendation or "none"
    return rec if rec in ("direct", "elective", "none") else "insufficient"


def snapshot(evaluation: CourseEvaluation, course: Course | None) -> dict[str, Any]:
    return {
        "recommendation": evaluation.recommendation,
        "confidence": evaluation.confidence,
        "coverage": evaluation.coverage,
        "candidate_course": course.code if course else None,
        "level": evaluation.level_flag,
        "prompt_version": evaluation.prompt_version,
        "model": evaluation.model,
    }


def ensure_assigned(session: Session, professor: User, evaluation: CourseEvaluation) -> None:
    if professor.role != Role.PROFESSOR:
        raise PermissionDeniedError("최종 판정은 배정된 학과 교수만 할 수 있어요.")
    assignment = evaluation_repo.active_assignment(session, evaluation.id)
    if assignment is None or assignment.reviewer_id != professor.id:
        raise PermissionDeniedError("본인에게 배정된 건만 판정할 수 있어요.")


def _validate_reasons(codes: list[str], memo: str, required: bool) -> tuple[list[str], str]:
    unknown = [c for c in codes if c not in ReasonCode.__members__.values()]
    if unknown:
        raise DecisionValidationError("사유를 목록에서 골라 주세요.")
    codes = list(dict.fromkeys(codes))
    memo = memo.strip()
    if required and not codes:
        raise DecisionValidationError("반려하거나 AI 추천과 다르게 판정할 때는 사유를 하나 이상 골라야 해요.")
    if ReasonCode.OTHER in codes and not memo:
        raise DecisionValidationError("'기타'를 고른 경우에는 메모를 적어 주세요.")
    return codes, memo


def decide(
    session: Session,
    professor: User,
    evaluation_id: int,
    action: str,
    result: str | None,
    target_course_id: int | None,
    reason_codes: list[str],
    reason_memo: str,
    acknowledge_conflict: bool,
) -> Decision:
    evaluation = evaluation_repo.get(session, evaluation_id)
    if evaluation is None:
        raise NotFoundError("심사 건을 찾을 수 없어요.")
    ensure_assigned(session, professor, evaluation)
    if decision_repo.for_evaluation(session, evaluation.id) is not None:
        raise DecisionValidationError("이미 판정된 건이에요. 이의 신청으로 재심사를 진행해 주세요.")
    if action not in DecisionAction.__members__.values():
        raise DecisionValidationError("승인·수정·반려 중 하나를 선택해 주세요.")

    ai = ai_result(evaluation)
    ai_course = (
        catalog_repo.get_course(session, evaluation.candidate_course_id) if evaluation.candidate_course_id else None
    )
    target: Course | None = None
    if action == DecisionAction.APPROVE:
        if ai == "insufficient":
            raise DecisionValidationError("정보 부족 건은 그대로 승인할 수 없어요. 수정 또는 반려로 판정해 주세요.")
        final = ai
        target = ai_course if ai == DecisionResult.DIRECT else None
    elif action == DecisionAction.REJECT:
        final = DecisionResult.NONE
    else:
        if result not in DecisionResult.__members__.values():
            raise DecisionValidationError("수정할 판정 등급을 선택해 주세요.")
        final = str(result)
        if final == DecisionResult.DIRECT:
            target = catalog_repo.get_course(session, target_course_id) if target_course_id else None
            if target is None or target.institution_id != professor.institution_id:
                raise DecisionValidationError("직접 인정할 대상 과목을 선택해 주세요.")

    # 대상 과목은 직접 인정일 때만 의미가 있다
    differs = final != ai or (
        final == DecisionResult.DIRECT and (target.id if target else None) != (ai_course.id if ai_course else None)
    )
    codes, memo = _validate_reasons(reason_codes, reason_memo, required=action == DecisionAction.REJECT or differs)

    found = conflicts(history(session, evaluation), final)
    if found and not acknowledge_conflict:
        raise ConflictNeedsAcknowledgement(
            f"같은 강의계획서로 내린 과거 판정 {len(found)}건과 결과가 달라요. 이력을 확인한 뒤 다시 확정해 주세요."
        )

    decision = decision_repo.add(
        session,
        Decision(
            course_evaluation_id=evaluation.id,
            decided_by=professor.id,
            action=action,
            result=final,
            target_course_id=target.id if target else None,
            reason_codes=codes,
            reason_memo=memo,
            ai_recommendation_snapshot=snapshot(evaluation, ai_course),
            conflict_acknowledged=bool(found),
        ),
    )
    audit.record(
        session,
        professor,
        "decision.create",
        "course_evaluation",
        str(evaluation.id),
        decision_action=action,
        result=final,
        ai_recommendation=evaluation.recommendation,
        differs_from_ai=differs,
        reason_codes=codes,
        conflicts=len(found),
    )
    _close_request_if_done(session, evaluation)
    session.commit()
    return decision


def _close_request_if_done(session: Session, evaluation: CourseEvaluation) -> None:
    if evaluation.transfer_request_id is None:
        return
    request = request_repo.get(session, evaluation.transfer_request_id)
    if request is None:
        return
    latest = [evaluation_repo.latest_for_syllabus(session, s.id) for s in syllabus_repo.of_request(session, request.id)]
    decided = decision_repo.for_evaluations(session, [e.id for e in latest if e])
    if latest and all(e and e.id in decided for e in latest):
        request.status = RequestStatus.DECIDED
