"""추천 등급 기준값(scoring.DIRECT_MIN·ELECTIVE_MIN) 보정 도구 (open-issues B2).

교수의 최종 판정(또는 전문가 라벨 골든셋)을 정답으로 보고, 기준값 조합마다 AI 추천이 정답과 얼마나 맞는지 계산해
"오인정률(AI가 사람보다 높은 등급을 추천한 비율)이 목표 이하인 조합 중 일치율이 가장 높은 값"을 제안한다.

- 제안만 한다. 실제 기준값은 사람이 검토한 뒤 scoring.py를 고치고 RULES_VERSION을 올려 바꾼다.
- 정보 부족(insufficient)으로 추천한 건은 기준값과 상관없으므로 뺀다.
- 판정 당시 스냅숏(decisions.ai_recommendation_snapshot)의 커버리지·수준을 쓴다. 이의 신청으로 다시 판정한 건은
  마지막 판정을 정답으로 본다.
- 선택 인정 자격(elective_eligible)은 스냅숏에 없어 보정 계산에서는 빼고 본다.
"""

import csv
import io
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.models.enums import Recommendation
from backend.repositories import decisions as decision_repo
from backend.services import scoring

RANK = {Recommendation.NONE: 0, Recommendation.ELECTIVE: 1, Recommendation.DIRECT: 2}
RESULTS = (Recommendation.DIRECT, Recommendation.ELECTIVE, Recommendation.NONE)
# 이보다 표본이 적으면 제안값을 참고로만 쓴다
MIN_SAMPLES = 50
DEFAULT_MAX_OVER = 0.05


@dataclass(frozen=True)
class Sample:
    coverage: float  # 수준 보정 전 개념 평균 0~1
    level: str | None  # same / lower / higher
    human: str  # 사람이 내린 결과: direct / elective / none


@dataclass
class Metrics:
    direct_min: float
    elective_min: float
    n: int
    agreement: float  # AI 추천 = 사람 판정
    over_rate: float  # AI가 사람보다 높은 등급 (오인정 위험)
    under_rate: float  # AI가 사람보다 낮은 등급
    confusion: Counter[tuple[str, str]] = field(default_factory=Counter)  # (AI, 사람) → 건수


@dataclass
class Report:
    current: Metrics
    suggested: Metrics | None  # 목표 오인정률을 지키는 조합이 없으면 None
    max_over: float

    @property
    def enough_samples(self) -> bool:
        return self.current.n >= MIN_SAMPLES


def predict(sample: Sample, direct_min: float, elective_min: float) -> str:
    """scoring.score_candidate의 등급 규칙을 기준값만 바꿔 적용한다 (정보 부족 판정은 제외된 표본)."""
    lower = sample.level == "lower"
    adjusted = sample.coverage * (scoring.LOWER_LEVEL_FACTOR if lower else 1.0)
    if adjusted >= direct_min and not lower:
        return Recommendation.DIRECT
    if adjusted >= elective_min or sample.coverage >= direct_min:
        return Recommendation.ELECTIVE
    return Recommendation.NONE


def evaluate(samples: list[Sample], direct_min: float, elective_min: float) -> Metrics:
    confusion: Counter[tuple[str, str]] = Counter()
    over = under = same = 0
    for s in samples:
        ai = predict(s, direct_min, elective_min)
        confusion[(ai, s.human)] += 1
        diff = RANK[Recommendation(ai)] - RANK[Recommendation(s.human)]
        over += diff > 0
        under += diff < 0
        same += diff == 0
    n = len(samples)
    return Metrics(
        direct_min=direct_min,
        elective_min=elective_min,
        n=n,
        agreement=same / n if n else 0.0,
        over_rate=over / n if n else 0.0,
        under_rate=under / n if n else 0.0,
        confusion=confusion,
    )


def suggest(samples: list[Sample], max_over: float = DEFAULT_MAX_OVER, step: float = 0.01) -> Report:
    """기준값 조합을 훑어 오인정률 ≤ max_over 중 일치율이 가장 높은 조합을 고른다.
    같으면 오인정률이 낮은 쪽, 그다음 지금 기준값에 가까운 쪽."""
    current = evaluate(samples, scoring.DIRECT_MIN, scoring.ELECTIVE_MIN)
    if not samples:
        return Report(current=current, suggested=None, max_over=max_over)
    best: tuple[float, float, float] | None = None
    best_metrics: Metrics | None = None
    steps = round(1 / step)
    for d in range(round(0.30 / step), steps + 1):
        for e in range(round(0.10 / step), d):
            m = evaluate(samples, round(d * step, 2), round(e * step, 2))
            if m.over_rate > max_over:
                continue
            distance = abs(m.direct_min - scoring.DIRECT_MIN) + abs(m.elective_min - scoring.ELECTIVE_MIN)
            key = (m.agreement, -m.over_rate, -distance)
            if best is None or key > best:
                best, best_metrics = key, m
    return Report(current=current, suggested=best_metrics, max_over=max_over)


def samples_from_decisions(session: Session, target_institution_id: int) -> list[Sample]:
    """기관의 확정 판정에서 표본을 만든다. 심사 건마다 마지막 판정(이의 신청 재판정 포함)만 쓴다."""
    latest: dict[int, Sample] = {}
    for decision, evaluation, _ in decision_repo.all_for_institution(session, target_institution_id):
        snap = decision.ai_recommendation_snapshot or {}
        coverage = snap.get("coverage")
        if snap.get("recommendation") == Recommendation.INSUFFICIENT or coverage is None:
            latest.pop(evaluation.id, None)
            continue
        if decision.result not in RESULTS:
            continue
        latest[evaluation.id] = Sample(coverage=float(coverage), level=snap.get("level"), human=decision.result)
    return list(latest.values())


def samples_from_csv(data: str) -> list[Sample]:
    """전문가 라벨 골든셋 CSV: coverage(0~1), level(same·lower·higher, 비워도 됨), result(direct·elective·none)."""
    reader = csv.DictReader(io.StringIO(data.lstrip("﻿")))
    missing = {"coverage", "result"} - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"missing columns: {', '.join(sorted(missing))}")
    samples = []
    for line, row in enumerate(reader, start=2):
        result = (row.get("result") or "").strip().lower()
        try:
            coverage = float(row["coverage"])
        except ValueError as exc:
            raise ValueError(f"line {line}: coverage must be a number") from exc
        if result not in RESULTS or not 0 <= coverage <= 1:
            raise ValueError(f"line {line}: result must be direct/elective/none and coverage 0..1")
        samples.append(Sample(coverage=coverage, level=(row.get("level") or "").strip() or None, human=result))
    return samples
