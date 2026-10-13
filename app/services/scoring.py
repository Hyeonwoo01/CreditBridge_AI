"""AI 판단(개념별 커버리지) → 3단계 추천·확률·신뢰도 (FR-07, FR-08, FR-16).

LLM은 개념별 판단만 하고, 추천 등급과 확률은 이 모듈의 고정 규칙으로 계산한다.
같은 판단에는 언제나 같은 추천이 나온다.
"""

from dataclasses import dataclass

from app.models.enums import Confidence, Recommendation
from app.schemas.results import ConceptResult

# 아래 규칙을 바꾸면 버전을 올린다. 같은 입력의 이전 결과를 재사용할 때 이 버전도 비교한다.
RULES_VERSION = "scoring-v2"

DIRECT_MIN = 0.75
ELECTIVE_MIN = 0.40
# 원문 근거를 확인하지 못한 개념의 커버리지 상한
UNVERIFIED_CAP = 0.40
# 수준이 낮은 과목은 내용이 겹쳐도 직접 인정을 추천하지 않고 점수를 낮춘다
LOWER_LEVEL_FACTOR = 0.75
# 판단 불가 개념이 이 비율 이상이면 확률 대신 정보 부족으로 안내한다
UNCLEAR_LIMIT = 0.40
LOW_CONFIDENCE_UNCLEAR = 0.25
LOW_CONFIDENCE_VERIFIED = 0.50


@dataclass(frozen=True)
class Score:
    recommendation: Recommendation
    probability: float | None  # 직접 인정 가능성(%), 정보 부족이면 None
    confidence: Confidence
    coverage: float  # 수준 보정 전 개념 평균 0~1
    adjusted: float  # 수준 보정 후
    missing_concepts: list[str]


def apply_verification(status: str, judged_coverage: int, verified: bool) -> float:
    if status == "unclear":
        return 0.0
    coverage = judged_coverage / 100
    if status in ("taught", "partial") and not verified:
        return min(coverage, UNVERIFIED_CAP)
    return coverage


def score_candidate(
    concepts: list[ConceptResult], level: str, *, sparse_document: bool, elective_eligible: bool
) -> Score:
    n = max(len(concepts), 1)
    coverage = sum(c.coverage for c in concepts) / n
    adjusted = coverage * (LOWER_LEVEL_FACTOR if level == "lower" else 1.0)
    unclear = [c.concept for c in concepts if c.status == "unclear"]
    claimed = [c for c in concepts if c.status in ("taught", "partial")]
    verified_ratio = sum(1 for c in claimed if c.verified) / len(claimed) if claimed else 1.0
    unclear_ratio = len(unclear) / n
    missing = unclear + [c.concept for c in claimed if not c.verified]

    margin = min(abs(adjusted - DIRECT_MIN), abs(adjusted - ELECTIVE_MIN))
    if verified_ratio < LOW_CONFIDENCE_VERIFIED or unclear_ratio >= LOW_CONFIDENCE_UNCLEAR:
        confidence = Confidence.LOW
    elif verified_ratio >= 0.8 and margin >= 0.1 and not unclear:
        confidence = Confidence.HIGH
    else:
        confidence = Confidence.MEDIUM

    if sparse_document or unclear_ratio >= UNCLEAR_LIMIT or confidence is Confidence.LOW:
        return Score(Recommendation.INSUFFICIENT, None, Confidence.LOW, coverage, adjusted, missing)

    if adjusted >= DIRECT_MIN and level != "lower":
        recommendation = Recommendation.DIRECT
    elif adjusted >= ELECTIVE_MIN or coverage >= DIRECT_MIN or elective_eligible:
        recommendation = Recommendation.ELECTIVE
    else:
        recommendation = Recommendation.NONE
    probability = round(min(0.98, max(0.02, adjusted * (0.6 + 0.4 * verified_ratio))) * 100, 1)
    return Score(recommendation, probability, confidence, coverage, adjusted, missing)


def is_sparse(weekly_topic_count: int, outcome_count: int) -> bool:
    """주차 계획도 학습 목표도 거의 없는 부실형 강의계획서."""
    return weekly_topic_count < 4 and outcome_count < 3
