"""AI 판단(개념별 커버리지) → 3단계 추천·신뢰도 (FR-07, FR-08, FR-16).

LLM은 개념별 판단만 하고, 추천 등급과 신뢰도는 이 모듈의 고정 규칙으로 계산한다.
MVP는 판정 확률(%)을 계산하지 않는다 (실제 판정 데이터로 보정할 수 있는 파일럿 이후 추가).
같은 판단에는 언제나 같은 추천이 나온다.
"""

from dataclasses import dataclass

from backend.models.enums import Confidence, Recommendation
from backend.schemas.results import ConceptResult

# 아래 규칙을 바꾸면 버전을 올린다. 같은 입력의 이전 결과를 재사용할 때 이 버전도 비교한다.
# 근거로 인정하는 구절의 기준(ai/evidence.py)이 바뀌어도 올린다. v4: 선수과목·교재 칸·부정 문장 구절 제외
RULES_VERSION = "scoring-v4"

DIRECT_MIN = 0.75
ELECTIVE_MIN = 0.40
# 원문 근거를 확인하지 못한 개념의 커버리지 상한
UNVERIFIED_CAP = 0.40
# 수준이 낮은 과목은 내용이 겹쳐도 직접 인정을 추천하지 않고 점수를 낮춘다
LOWER_LEVEL_FACTOR = 0.75
# 판단 불가 개념이 이 비율 이상이면 추천 대신 정보 부족으로 안내한다
UNCLEAR_LIMIT = 0.40
LOW_CONFIDENCE_UNCLEAR = 0.25
LOW_CONFIDENCE_VERIFIED = 0.50


@dataclass(frozen=True)
class Score:
    recommendation: Recommendation
    confidence: Confidence
    coverage: float  # 수준 보정 전 개념 평균 0~1
    adjusted: float  # 수준 보정 후
    missing_concepts: list[str]


def apply_verification(status: str, coverage: float, verified: bool) -> float:
    """AI가 매긴 개념 커버리지(0~1)에 근거 검증 결과를 반영한다."""
    if status == "unclear":
        return 0.0
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
        return Score(Recommendation.INSUFFICIENT, Confidence.LOW, coverage, adjusted, missing)

    if adjusted >= DIRECT_MIN and level != "lower":
        recommendation = Recommendation.DIRECT
    elif adjusted >= ELECTIVE_MIN or coverage >= DIRECT_MIN or elective_eligible:
        recommendation = Recommendation.ELECTIVE
    else:
        recommendation = Recommendation.NONE
    return Score(recommendation, confidence, coverage, adjusted, missing)


def is_sparse(weekly_topic_count: int, outcome_count: int) -> bool:
    """주차 계획도 학습 목표도 거의 없는 부실형 강의계획서."""
    return weekly_topic_count < 4 and outcome_count < 3
