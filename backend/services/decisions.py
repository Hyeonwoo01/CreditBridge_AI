"""교수 최종 판정(FR-09), 판정 이력(FR-10), 일관성 경보(FR-11).

AI에는 확정 경로가 없다. 판정은 배정된 교수 사용자만 저장할 수 있고 decided_by가 반드시 기록된다.
"""

import re
from dataclasses import dataclass, replace
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.errors import CreditBridgeError, DecisionValidationError, NotFoundError, PermissionDeniedError
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import (
    Course,
    CourseEvaluation,
    CreditAllocation,
    Decision,
    GraduationRequirement,
    Syllabus,
    TransferRequest,
    User,
)
from backend.models.enums import (
    AppealStatus,
    DecisionAction,
    DecisionResult,
    ReasonCode,
    RequestStatus,
    Role,
    SyllabusStatus,
)
from backend.repositories import allocations as allocation_repo
from backend.repositories import catalog as catalog_repo
from backend.repositories import decisions as decision_repo
from backend.repositories import equivalencies as equivalency_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo
from backend.services import appeals as appeal_service
from backend.services import audit, case_state, degree_audit, notifications, review_frameworks, scoring
from backend.services import credits as credit_service
from backend.services import evidence_status as evidence_service
from backend.services import policy as policy_service

# 강의계획서 내용이 이 비율 이상 같으면 '같은 강의계획서'로 본다. 첫 측정 후 확정한다 (기능명세서 FR-11).
SIMILARITY_MIN = 0.80
REASON_LABELS = {
    ReasonCode.WEEKS_INSUFFICIENT: N_("주차 범위 부족"),
    ReasonCode.LEVEL_DIFFERENCE: N_("수준 차이"),
    ReasonCode.NO_LAB: N_("실험·실습 미포함"),
    ReasonCode.PREREQUISITE_DIFFERENCE: N_("선수과목 차이"),
    ReasonCode.OTHER: N_("기타"),
}
# 사유 선택 창에서 각 항목 아래에 보여주는 설명
REASON_HINTS = {
    ReasonCode.WEEKS_INSUFFICIENT: N_("핵심 개념을 다루는 주차가 대상 과목보다 적거나 범위가 좁아요."),
    ReasonCode.LEVEL_DIFFERENCE: N_("입문·심화 등 과목 수준이 대상 과목과 달라요."),
    ReasonCode.NO_LAB: N_("대상 과목에 필요한 실험·실습이 출신 과목에 없어요."),
    ReasonCode.PREREQUISITE_DIFFERENCE: N_("선수과목 체계가 달라 같은 단계의 과목으로 보기 어려워요."),
    ReasonCode.OTHER: N_("위 항목에 없는 사유예요. 메모에 구체적으로 적어 주세요."),
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
    # 기존 동등 과목표에서 가져온 이력 (FR-26). 강의계획서가 없어 유사도를 비교할 수 없으므로 경보 대상이 아니다
    imported: bool = False

    @property
    def same_syllabus(self) -> bool:
        return not self.imported and self.similarity >= SIMILARITY_MIN


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
    """같은 대상 대학에서 내린 같은 출신 대학·같은 과목의 과거 판정과 기존 동등 과목표.
    화면에는 모두 보여주고, 경보는 conflicts()가 고른다."""
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    request = request_repo.get(session, evaluation.transfer_request_id) if evaluation.transfer_request_id else None
    if syllabus is None or request is None:
        return []
    key = course_key(syllabus)
    rows = decision_repo.history_for_course(
        session, request.target_institution_id, syllabus.institution_id, key, exclude_evaluation_id=evaluation.id
    )
    imported = equivalency_repo.for_course(session, request.target_institution_id, syllabus.institution_id, key)
    courses = catalog_repo.courses_by_ids(
        session,
        [d.target_course_id for d, _, _ in rows if d.target_course_id]
        + [e.target_course_id for e in imported if e.target_course_id],
    )
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
    for e in imported:
        items.append(
            HistoryItem(
                decided_at=datetime.combine(e.decided_on, datetime.min.time()) if e.decided_on else e.created_at,
                result=e.result,
                target_code=courses[e.target_course_id].code if e.target_course_id in courses else None,
                reason_codes=[],
                reason_memo=e.note,
                evaluation_id=0,
                similarity=0.0,
                same_target=e.target_course_id is not None and e.target_course_id == evaluation.candidate_course_id,
                imported=True,
            )
        )
    items.sort(key=lambda h: h.decided_at, reverse=True)
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


def course_snapshot(
    target: Course | None,
    syllabus: Syllabus,
    combined: list[Syllabus],
    conversion: credit_service.Conversion,
    source_institution: str | None,
    requirement: GraduationRequirement | None = None,
) -> dict[str, Any]:
    """판정 때의 과목·환산 규칙 값 (리뷰 v3 P0-8 결정 재현). 카탈로그·규칙이 바뀌어도 이 값으로 다시 보여 준다.
    requirement: 교수가 고른 졸업 요건 (없으면 자동 배정, P1-6). 요건을 나중에 고치거나 지워도 그때 값이 남는다."""
    rule = conversion.rule
    return {
        "requirement": {
            "id": requirement.id,
            "program_id": requirement.program_id,
            "area": requirement.area,
            "name": requirement.name,
        }
        if requirement
        else None,
        "target": {
            "id": target.id,
            "code": target.code,
            "title": target.title,
            "credits": float(target.credits),
            "department": target.department_name,
        }
        if target
        else None,
        "sources": [
            {
                "syllabus_id": s.id,
                "code": s.course_code,
                "title": s.course_title,
                "credits": s.credits,
                "content_hash": s.content_hash,
            }
            for s in [syllabus, *combined]
        ],
        "source_institution": source_institution,
        "conversion": {
            "source_credits": conversion.source_credits,
            "source_unit": conversion.source_unit,
            "target_unit": conversion.target_unit,
            "value": conversion.value,
            "rule_id": rule.id if rule else None,
            "factor": float(rule.factor) if rule else None,
            "method": rule.method if rule else None,
            "reason": conversion.reason,
        },
        "rules_version": scoring.RULES_VERSION,
    }


def ensure_assigned(session: Session, professor: User, evaluation: CourseEvaluation) -> None:
    if professor.role != Role.PROFESSOR:
        raise PermissionDeniedError(tr("최종 판정은 배정된 학과 교수만 할 수 있어요."))
    assignment = evaluation_repo.active_assignment(session, evaluation.id)
    if assignment is None or assignment.reviewer_id != professor.id:
        raise PermissionDeniedError(tr("본인에게 배정된 건만 판정할 수 있어요."))


def _validate_reasons(codes: list[str], memo: str, required: bool) -> tuple[list[str], str]:
    unknown = [c for c in codes if c not in ReasonCode.__members__.values()]
    if unknown:
        raise DecisionValidationError(tr("사유를 목록에서 골라 주세요."))
    codes = list(dict.fromkeys(codes))
    memo = memo.strip()
    if required and not codes:
        raise DecisionValidationError(tr("반려하거나 AI 추천과 다르게 판정할 때는 사유를 하나 이상 골라야 해요."))
    if ReasonCode.OTHER in codes and not memo:
        raise DecisionValidationError(tr("'기타'를 고른 경우에는 메모를 적어 주세요."))
    return codes, memo


def _policy_snapshot(session: Session, request: TransferRequest | None) -> dict[str, Any] | None:
    """판정 때 이 학생에게 적용된 학칙 정책 (규칙 id·값). 정책이 바뀌어도 이 판정 기록은 그대로 남는다."""
    student = user_repo.get_by_id(session, request.student_id) if request else None
    if request is None or student is None:
        return None
    return policy_service.for_student(session, student, request.target_institution_id).snapshot()


def credit_conversion(session: Session, evaluation: CourseEvaluation) -> credit_service.Conversion:
    """이 심사 건의 출신 학점을 대상 대학 단위로 환산한 결과 (판정 화면 안내·판정 저장에 같이 쓴다)."""
    request = request_repo.get(session, evaluation.transfer_request_id) if evaluation.transfer_request_id else None
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    if request is None or syllabus is None:
        return credit_service.Conversion(None, None, None, None, reason=credit_service.NO_SOURCE_CREDITS)
    return credit_service.for_request(session, request).convert(syllabus)


def combinable_sources(
    session: Session, evaluation: CourseEvaluation
) -> list[tuple[Syllabus, credit_service.Conversion]]:
    """이 심사 건과 합쳐 인정할 수 있는 같은 학생의 다른 출신 과목 (같은 편입 대학, 종료되지 않은 요청, 성적 기준 통과,
    분석까지 끝난 강의계획서). 환산 결과도 함께 돌려준다."""
    request = request_repo.get(session, evaluation.transfer_request_id) if evaluation.transfer_request_id else None
    if request is None:
        return []
    out: list[tuple[Syllabus, credit_service.Conversion]] = []
    for other in request_repo.of_student(session, request.student_id):
        if other.target_institution_id != request.target_institution_id or other.status == RequestStatus.CLOSED:
            continue
        syllabi = [
            s
            for s in syllabus_repo.of_request(session, other.id)
            if s.id != evaluation.syllabus_id and s.status == SyllabusStatus.READY
        ]
        failed = policy_service.grade_failed_syllabus_ids(session, [s.id for s in syllabi])
        converter = credit_service.for_request(session, other)
        out += [(s, converter.convert(s)) for s in syllabi if s.id not in failed]
    return out


def _combined_sources(
    session: Session, evaluation: CourseEvaluation, syllabus_ids: list[int]
) -> list[tuple[Syllabus, credit_service.Conversion]]:
    if not syllabus_ids:
        return []
    allowed = {s.id: (s, c) for s, c in combinable_sources(session, evaluation)}
    wanted = list(dict.fromkeys(syllabus_ids))
    if any(i not in allowed for i in wanted):
        raise DecisionValidationError(tr("함께 인정할 과목은 이 학생의 다른 출신 과목 목록에서 골라 주세요."))
    return [allowed[i] for i in wanted]


def _allocation_plan(
    session: Session,
    evaluation: CourseEvaluation,
    request: TransferRequest | None,
    primary: Syllabus | None,
    combined: list[tuple[Syllabus, credit_service.Conversion]],
    conversion: credit_service.Conversion,
    final: str,
    accepted: float,
    target: Course | None,
) -> list[tuple[Syllabus, float]]:
    """원장에 남길 (출신 과목, 학점) 목록. 이중 사용·이중 인정이면 판정 오류 (리뷰 v3 13.2 무결성 규칙 1·2·7)."""
    if final == DecisionResult.NONE or accepted <= 0 or request is None or primary is None:
        return []
    earlier = {d.id for d in decision_repo.for_evaluation_all(session, evaluation.id)}
    active = [
        (a, s)
        for a, s in allocation_repo.active_for_student(session, request.student_id)
        if a.decision_id not in earlier  # 재판정이면 이 심사 건의 이전 배분은 대체된다
    ]
    if target is not None and any(a.target_course_id == target.id for a, _ in active):
        raise DecisionValidationError(
            tr("이 학생은 이미 {code}로 인정받았어요. 같은 대상 과목을 두 번 인정할 수 없어요.", code=target.code)
        )
    # 과목마다 환산 학점(인정 가능한 상한). 합쳐 인정하면 모두 환산돼 있다 (decide에서 확인)
    primary_value = credit_conversion(session, evaluation).value if combined else conversion.value
    sources = [(primary, primary_value)] + [(s, c.value) for s, c in combined]
    remaining: list[float] = []
    for syllabus, capacity in sources:
        key = credit_service.source_key(syllabus)
        used = sum(a.credits for a, s in active if credit_service.source_key(s) == key)
        if capacity is None:  # 환산을 모르는 한 과목: 교수가 적은 값을 쓰되, 이미 다른 판정에 쓰인 과목이면 막는다
            if used > 0:
                raise DecisionValidationError(
                    tr(
                        "{course}은(는) 이미 다른 판정에서 인정에 쓰인 과목이에요.",
                        course=syllabus.course_code or syllabus.course_title,
                    )
                )
            remaining.append(accepted)
            continue
        left = round(capacity - used, 2)
        if left <= 0:
            raise DecisionValidationError(
                tr(
                    "{course}의 학점은 이미 모두 다른 인정에 쓰였어요.",
                    course=syllabus.course_code or syllabus.course_title,
                )
            )
        remaining.append(left)
    if sum(remaining) + 1e-9 < accepted:
        raise DecisionValidationError(
            tr("출신 과목에서 아직 쓰지 않은 학점({credits})보다 많이 인정할 수 없어요.", credits=f"{sum(remaining):g}")
        )
    shares = credit_service.split_credits(accepted, remaining)
    return [(syllabus, share) for (syllabus, _), share in zip(sources, shares, strict=True) if share > 0]


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
    accepted_credits: float | None = None,
    combined_syllabus_ids: list[int] | None = None,
    case_token: str | None = None,
    checklist: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    requirement_id: int | None = None,
) -> Decision:
    """accepted_credits: 교수가 적은 인정 학점(대상 대학 단위). 비우면 환산 규칙으로 계산한 제안값을 쓰고,
    환산할 수 없으면 인정하는 판정은 직접 적어야 한다 (학점을 지어내지 않음).
    combined_syllabus_ids: 이 과목과 합쳐 하나로 인정할 같은 학생의 다른 출신 과목(N:1). 인정 학점은 과목별 남은
    학점에 비례해 나눠 원장(credit_allocations)에 한 줄씩 남긴다. 한 출신 과목 학점의 이중 사용과 같은 대상 과목의
    이중 인정은 막는다.
    case_token: 화면을 열 때의 상태 토큰. 그 사이 다른 사람이 판정·배정 등을 바꿨으면 덮어쓰지 않는다 (P0-6).
    requirement_id: 이 인정 학점을 넣을 졸업 요건(학생 프로그램의 요건, P1-6). 비우면 과목 목록 기준 자동 배정."""
    evaluation = evaluation_repo.get(session, evaluation_id)
    if evaluation is None:
        raise NotFoundError(tr("심사 건을 찾을 수 없어요."))
    ensure_assigned(session, professor, evaluation)
    current = decision_repo.for_evaluation(session, evaluation.id)
    appeal = appeal_service.accepted_for(session, evaluation.id) if current is not None else None
    if current is not None and (appeal is None or appeal.decision_id != current.id):
        raise DecisionValidationError(tr("이미 판정된 건이에요. 이의 신청으로 재심사를 진행해 주세요."))
    # 행을 잠그고 상태(최신 분석인지, 판정 가능한 상태인지)와 토큰을 확인한다. 동시에 두 판정이 저장되지 않는다
    evaluation = case_state.ensure(session, evaluation.id, "decide", case_token)
    if current is not None and current.decided_by == professor.id:
        raise DecisionValidationError(tr("이의 신청 재판정은 원 판정 교수가 아닌 다른 교수가 해야 해요."))
    if action not in DecisionAction.__members__.values():
        raise DecisionValidationError(tr("승인·수정·반려 중 하나를 선택해 주세요."))
    if action == DecisionAction.APPROVE and get_settings().ai_limited:
        raise DecisionValidationError(tr("지금은 AI 추천 등급을 쓰지 않아요. '수정'에서 판정 결과를 직접 골라 주세요."))
    hold = evidence_service.hold_reason(syllabus_repo.get(session, evaluation.syllabus_id))
    if hold:  # 진위 검토 중·채택 안 한 자료는 자동 불인정이 아니라 판정 보류
        raise DecisionValidationError(tr(hold))

    ai = ai_result(evaluation)
    ai_course = (
        catalog_repo.get_course(session, evaluation.candidate_course_id) if evaluation.candidate_course_id else None
    )
    target: Course | None = None
    if action == DecisionAction.APPROVE:
        if ai == "insufficient":
            raise DecisionValidationError(tr("정보 부족 건은 그대로 승인할 수 없어요. 수정 또는 반려로 판정해 주세요."))
        final = ai
        target = ai_course if ai == DecisionResult.DIRECT else None
    elif action == DecisionAction.REJECT:
        final = DecisionResult.NONE
    else:
        if result not in DecisionResult.__members__.values():
            raise DecisionValidationError(tr("수정할 판정 등급을 선택해 주세요."))
        final = str(result)
        if final == DecisionResult.DIRECT:
            target = catalog_repo.get_course(session, target_course_id) if target_course_id else None
            if target is None or target.institution_id != professor.institution_id:
                raise DecisionValidationError(tr("직접 인정할 대상 과목을 선택해 주세요."))

    # 대상 과목은 직접 인정일 때만 의미가 있다
    differs = final != ai or (
        final == DecisionResult.DIRECT and (target.id if target else None) != (ai_course.id if ai_course else None)
    )
    codes, memo = _validate_reasons(reason_codes, reason_memo, required=action == DecisionAction.REJECT or differs)

    conversion = credit_conversion(session, evaluation)
    request = request_repo.get(session, evaluation.transfer_request_id) if evaluation.transfer_request_id else None
    primary = syllabus_repo.get(session, evaluation.syllabus_id)
    combined = _combined_sources(session, evaluation, combined_syllabus_ids or [])
    if combined:
        if final == DecisionResult.NONE:
            raise DecisionValidationError(tr("불인정에는 함께 인정할 과목을 고를 수 없어요."))
        if conversion.value is None or any(c.value is None for _, c in combined):
            raise DecisionValidationError(
                tr("학점을 환산할 수 없는 과목이 있어 합쳐 인정할 수 없어요. 학점 단위와 환산 규칙을 먼저 정해 주세요.")
            )
        values = [conversion.value or 0.0] + [c.value or 0.0 for _, c in combined]
        sources = [conversion.source_credits or 0.0] + [c.source_credits or 0.0 for _, c in combined]
        conversion = replace(conversion, value=round(sum(values), 2), source_credits=round(sum(sources), 2))
    if accepted_credits is None:
        accepted = credit_service.suggested_credits(final, conversion, target)
        if accepted is None:
            raise DecisionValidationError(
                tr("학점 단위나 환산 규칙이 없어 인정 학점을 자동으로 계산할 수 없어요. 인정 학점을 직접 적어 주세요.")
            )
    else:
        accepted = round(float(accepted_credits), 2)
    problem = credit_service.validate_accepted(final, accepted, conversion, target)
    if problem is not None:
        message, value = problem
        raise DecisionValidationError(tr(message, credits=f"{value:g}") if value is not None else tr(message))
    basis = credit_service.basis_for(final, accepted, target)
    plan = _allocation_plan(session, evaluation, request, primary, combined, conversion, final, accepted, target)
    requirement = None
    if requirement_id is not None and final != DecisionResult.NONE and request is not None:
        try:
            requirement = degree_audit.chosen_requirement(
                session, user_repo.get_by_id(session, request.student_id), request.target_institution_id, requirement_id
            )
        except CreditBridgeError as exc:
            raise DecisionValidationError(str(exc)) from exc

    found = conflicts(history(session, evaluation), final)
    if found and not acknowledge_conflict:
        raise ConflictNeedsAcknowledgement(
            tr(
                "같은 강의계획서로 내린 과거 판정 {n}건과 결과가 달라요. 이력을 확인한 뒤 다시 확정해 주세요.",
                n=len(found),
            )
        )

    framework_course = target or ai_course  # 분야별 체크리스트: 인정 대상 과목, 없으면 AI 후보 과목의 학과
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
            appeal_id=appeal.id if appeal else None,
            accepted_credits=accepted,
            credit_unit=conversion.target_unit,
            credit_basis=basis,
            source_credits=conversion.source_credits,
            source_credit_unit=conversion.source_unit,
            conversion_rule_id=conversion.rule.id if conversion.rule else None,
            policy_snapshot=_policy_snapshot(session, request),
            evidence_snapshot=evidence_service.snapshot(session, primary),
            course_snapshot=course_snapshot(
                target,
                primary,
                [c for c, _ in combined],
                conversion,
                request.source_institution.name if request else None,
                requirement,
            )
            if primary is not None
            else None,
            review_checklist=review_frameworks.record(
                review_frameworks.for_department(framework_course.department_name if framework_course else None),
                checklist or [],
                missing_evidence or [],
            ),
        ),
    )
    allocation_repo.supersede_for_evaluation(session, evaluation.id, decision.id)
    allocation_repo.add_all(
        session,
        [
            CreditAllocation(
                student_id=request.student_id if request else professor.id,
                decision_id=decision.id,
                syllabus_id=syllabus.id,
                target_course_id=target.id if target else None,
                credits=share,
                credit_unit=conversion.target_unit,
                requirement_id=requirement.id if requirement else None,
            )
            for syllabus, share in plan
        ],
    )
    if appeal is not None:
        appeal.status = AppealStatus.REDECIDED
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
        appeal=appeal.id if appeal else None,
        accepted_credits=accepted,
        credit_basis=basis,
        conversion_rule=conversion.rule.id if conversion.rule else None,
        combined_sources=[s.id for s, _ in combined],
        requirement=requirement.id if requirement else None,
    )
    _notify_student(session, evaluation, final, redecided=appeal is not None)
    if evaluation.transfer_request_id is not None:
        request = request_repo.get(session, evaluation.transfer_request_id)
        if request is not None:
            close_request_if_done(session, request)
    session.commit()
    return decision


def _notify_student(session: Session, evaluation: CourseEvaluation, result: str, *, redecided: bool) -> None:
    request = request_repo.get(session, evaluation.transfer_request_id) if evaluation.transfer_request_id else None
    syllabus = syllabus_repo.get(session, evaluation.syllabus_id)
    student = user_repo.get_by_id(session, request.student_id) if request else None
    if student is None or syllabus is None:
        return
    label = {"direct": N_("직접 인정"), "elective": N_("선택 인정"), "none": N_("불인정")}.get(result, result)
    course = (syllabus.course_code or syllabus.course_title).strip()
    notifications.notify(
        session,
        [student],
        "decision.redecided" if redecided else "decision.created",
        (
            N_("{course} 재판정 결과가 확정됐어요: {result}")
            if redecided
            else N_("{course} 판정 결과가 확정됐어요: {result}")
        ).format(course=course, result=label),
        f"/student/evaluations/{evaluation.id}",
    )


def close_request_if_done(session: Session, request: TransferRequest) -> None:
    """심사를 요청한 과목이 모두 판정됐으면 요청을 판정 완료로. 성적 기준 미달로 빠진 과목은 기다리지 않는다."""
    if request.status != RequestStatus.SUBMITTED:
        return
    syllabi = syllabus_repo.of_request(session, request.id)
    failed = policy_service.grade_failed_syllabus_ids(session, [s.id for s in syllabi])
    latest = [evaluation_repo.latest_for_syllabus(session, s.id) for s in syllabi]
    decided = decision_repo.for_evaluations(session, [e.id for e in latest if e])
    if latest and all(e and (e.id in decided or e.syllabus_id in failed) for e in latest):
        request.status = RequestStatus.DECIDED
