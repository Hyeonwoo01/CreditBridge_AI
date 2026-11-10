"""학점 단위와 환산 (리뷰 v3 P0-1·2). AI 없이 정해진 규칙으로만 계산하는 순수 함수.

원칙: 학점 단위나 승인된 환산 규칙을 모르면 숫자를 지어내지 않고 보류(None + 이유)를 돌려준다.
같은 날짜에 유효한 규칙이 둘 이상이면(정책 충돌) 고르지 않고 보류한다.
교수가 확정한 인정 학점은 대상 대학 단위로 저장하고, 계산에 쓴 출신 학점과 규칙을 함께 남긴다.
"""

from dataclasses import dataclass, replace
from datetime import date

from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.i18n import N_
from backend.models import Course, CreditConversionRule, Syllabus, TransferRequest
from backend.models.enums import CreditBasis, CreditSystem, DecisionResult
from backend.repositories import catalog as catalog_repo
from backend.repositories import requests as request_repo

SYSTEM_LABELS = {
    CreditSystem.KR_CREDIT: N_("한국 학점"),
    CreditSystem.US_SEMESTER: N_("미국 학기제 학점"),
    CreditSystem.US_QUARTER: N_("미국 쿼터제 학점"),
    CreditSystem.ECTS: N_("ECTS"),
    CreditSystem.OTHER: N_("기타 단위"),
}

# 환산을 보류한 이유 (화면에서 | t로 번역)
NO_SOURCE_CREDITS = N_("출신 과목 학점이 성적표·강의계획서에 없어요")
NO_SOURCE_UNIT = N_("출신 대학의 학점 단위가 정해지지 않았어요")
NO_TARGET_UNIT = N_("편입 대학의 학점 단위가 정해지지 않았어요")
NO_RULE = N_("두 학점 단위 사이의 승인된 환산 규칙이 없어요")
RULE_CONFLICT = N_("같은 날짜에 유효한 환산 규칙이 둘 이상이라 고를 수 없어요")


@dataclass(frozen=True)
class Conversion:
    """출신 학점을 대상 대학 단위로 바꾼 결과. value가 None이면 보류(reason에 이유)."""

    source_credits: float | None
    source_unit: str | None
    target_unit: str | None
    value: float | None
    rule: CreditConversionRule | None = None
    reason: str | None = None

    @property
    def known(self) -> bool:
        return self.value is not None


def active_rules(
    rules: list[CreditConversionRule], source_unit: str, target_unit: str, on: date
) -> list[CreditConversionRule]:
    """그 날짜에 유효한 규칙 중 가장 최근에 시작한 것들 (둘 이상이면 충돌)."""
    valid = [
        r
        for r in rules
        if r.source_system == source_unit
        and r.target_system == target_unit
        and r.effective_from <= on
        and (r.effective_to is None or r.effective_to >= on)
    ]
    if not valid:
        return []
    latest = max(r.effective_from for r in valid)
    return [r for r in valid if r.effective_from == latest]


def convert(
    source_credits: float | None,
    source_unit: str | None,
    target_unit: str | None,
    rules: list[CreditConversionRule],
    on: date,
) -> Conversion:
    base = Conversion(source_credits, source_unit, target_unit, None)
    if source_credits is None or source_credits <= 0:
        return replace(base, reason=NO_SOURCE_CREDITS)
    if not source_unit:
        return replace(base, reason=NO_SOURCE_UNIT)
    if not target_unit:
        return replace(base, reason=NO_TARGET_UNIT)
    if source_unit == target_unit and source_unit != CreditSystem.OTHER:
        return replace(base, value=float(source_credits))
    found = active_rules(rules, source_unit, target_unit, on)
    if not found:
        return replace(base, reason=NO_RULE)
    if len(found) > 1:
        return replace(base, reason=RULE_CONFLICT)
    rule = found[0]
    return replace(base, value=round(source_credits * rule.factor, 2), rule=rule)


def suggested_credits(result: str, conversion: Conversion, target: Course | None) -> float | None:
    """판정 결과에 맞는 인정 학점 제안값. 환산을 모르면 None (교수가 직접 적어야 함)."""
    if result == DecisionResult.NONE:
        return 0.0
    if conversion.value is None:
        return None
    if result == DecisionResult.DIRECT and target is not None:
        return min(conversion.value, float(target.credits))
    return conversion.value


def basis_for(result: str, accepted: float, target: Course | None) -> str:
    if result == DecisionResult.NONE:
        return CreditBasis.NOT_ACCEPTED
    if result == DecisionResult.ELECTIVE:
        return CreditBasis.ELECTIVE
    if target is not None and accepted < float(target.credits):
        return CreditBasis.PARTIAL
    return CreditBasis.FULL


def validate_accepted(
    result: str, accepted: float, conversion: Conversion, target: Course | None
) -> tuple[str, float | None] | None:
    """교수가 적은 인정 학점의 문제: (한국어 메시지 번역 키, {credits}에 넣을 값). 문제가 없으면 None."""
    if result == DecisionResult.NONE:
        return None if accepted == 0 else (N_("불인정은 인정 학점이 0이어야 해요."), None)
    if accepted <= 0:
        return N_("인정하는 판정은 인정 학점이 0보다 커야 해요."), None
    if result == DecisionResult.DIRECT and target is not None and accepted > float(target.credits):
        return N_("대상 과목 학점({credits})보다 많이 인정할 수 없어요."), float(target.credits)
    if conversion.value is not None and accepted > conversion.value:
        return N_("환산한 출신 학점({credits})보다 많이 인정할 수 없어요."), conversion.value
    if accepted > 30:
        return N_("인정 학점이 너무 커요. 단위를 확인해 주세요."), None
    return None


# ---------- DB에서 읽어 환산하기 ----------


def source_credits_of(syllabus: Syllabus, transcript_credits: float | None) -> float | None:
    """출신 과목 학점: 성적표에 적힌 값이 먼저, 없으면 강의계획서에서 읽은 값. 둘 다 없으면 모름(기본값 없음)."""
    if transcript_credits is not None and transcript_credits > 0:
        return float(transcript_credits)
    if syllabus.credits is not None and syllabus.credits > 0:
        return float(syllabus.credits)
    return None


def for_request(session: Session, request: TransferRequest) -> "RequestConverter":
    return RequestConverter(
        source_unit=request.source_institution.credit_system,
        target_unit=request.target_institution.credit_system,
        rules=catalog_repo.conversion_rules(session, request.target_institution_id),
        transcript={
            e.syllabus_id: e.credits for e in request_repo.transcript_entries(session, request.id) if e.syllabus_id
        },
    )


@dataclass(frozen=True)
class RequestConverter:
    """한 편입 요청의 과목들을 같은 규칙으로 환산한다 (규칙을 한 번만 읽음)."""

    source_unit: str | None
    target_unit: str | None
    rules: list[CreditConversionRule]
    transcript: dict[int, float | None]

    def convert(self, syllabus: Syllabus, on: date | None = None) -> Conversion:
        credits = source_credits_of(syllabus, self.transcript.get(syllabus.id))
        return convert(credits, self.source_unit, self.target_unit, self.rules, on or utcnow().date())


# ---------- 학점 배분 (리뷰 v3 P0-3) ----------


def source_key(syllabus: Syllabus) -> str:
    """같은 출신 과목을 알아보는 키: 같은 출신 대학의 같은 과목 코드(공백·대소문자 무시), 코드가 없으면 같은 파일."""
    code = "".join((syllabus.course_code or "").split()).upper()
    return f"{syllabus.institution_id}:{code}" if code else f"hash:{syllabus.content_hash}"


def split_credits(accepted: float, remaining: list[float]) -> list[float]:
    """인정 학점을 출신 과목별 남은 학점에 비례해 나눈다 (0.01 단위, 마지막 과목이 나머지)."""
    total = sum(remaining)
    if len(remaining) == 1 or total <= 0:
        return [accepted] + [0.0] * (len(remaining) - 1)
    shares = [round(accepted * r / total, 2) for r in remaining[:-1]]
    return [*shares, round(accepted - sum(shares), 2)]
