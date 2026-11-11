"""AI 성능 모니터링과 출시 기준 (리뷰 v3 P1-7, 13.11).

교수의 첫 판정(이의 신청 재판정 제외)과 판정 때 남은 AI 추천 스냅샷(decisions.ai_recommendation_snapshot: 추천·신뢰도·
프롬프트 버전·모델)을 비교한다. 개인정보 없이 집계만 낸다. 교수 판정을 AI 정답 라벨로 단정하지 않으므로, 기준 미달은
'사람이 살펴볼 신호'이고 자동으로 무언가를 바꾸지 않는다. 대응은 이전 프롬프트·모델로 되돌리거나(버전 관리됨)
AI_RECOMMENDATION_MODE=evidence_only로 추천 범위를 줄이는 것이다.
"""

from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.i18n import N_
from backend.models import CourseEvaluation, Decision
from backend.models.enums import Confidence, DecisionResult, Recommendation
from backend.repositories import catalog as catalog_repo
from backend.repositories import decisions as decision_repo

OK, FAIL, SMALL = "ok", "fail", "small_sample"
GATE_LABELS = {OK: N_("기준 충족"), FAIL: N_("기준 미달"), SMALL: N_("표본 부족")}


@dataclass
class VersionQuality:
    prompt_version: str
    model: str
    decisions: int = 0
    compared: int = 0  # 정보 부족이 아닌 추천 (일치율 분모)
    agreed: int = 0
    strong: int = 0  # 신뢰도 '상'으로 인정(직접·선택)을 추천한 건
    strong_wrong: int = 0  # 그중 교수가 다른 결과로 판정
    insufficient: int = 0  # 정보 부족으로 보류한 건
    reasons: Counter[str] = field(default_factory=Counter)  # 수정·반려 사유
    departments: dict[str, list[int]] = field(default_factory=dict)  # 학과 → [비교, 일치]

    @property
    def agreement(self) -> float | None:
        return self.agreed / self.compared if self.compared else None

    @property
    def strong_wrong_rate(self) -> float | None:
        return self.strong_wrong / self.strong if self.strong else None

    @property
    def insufficient_rate(self) -> float | None:
        return self.insufficient / self.decisions if self.decisions else None

    @property
    def gate(self) -> str:
        s = get_settings()
        if self.compared < s.ai_gate_min_samples:
            return SMALL
        agreement = self.agreement or 0.0
        wrong = self.strong_wrong_rate or 0.0
        return OK if agreement >= s.ai_gate_min_agreement and wrong <= s.ai_gate_max_strong_wrong else FAIL

    def department_rates(self) -> list[tuple[str, int, float]]:
        return sorted(
            ((name, c, a / c) for name, (c, a) in self.departments.items() if c),
            key=lambda row: (row[2], -row[1]),
        )


def quality(session: Session, institution_id: int) -> list[VersionQuality]:
    """프롬프트 버전·모델별 품질 (최근 버전부터)."""
    first: dict[int, tuple[Decision, CourseEvaluation]] = {}
    for decision, evaluation, _ in decision_repo.all_for_institution(session, institution_id):
        if decision.appeal_id is None and evaluation.id not in first:
            first[evaluation.id] = (decision, evaluation)
    course_ids = {e.candidate_course_id for _, e in first.values() if e.candidate_course_id}
    courses = catalog_repo.courses_by_ids(session, list(course_ids))
    groups: dict[tuple[str, str], VersionQuality] = {}
    order: list[tuple[str, str]] = []
    for decision, evaluation in first.values():
        snap = decision.ai_recommendation_snapshot or {}
        key = (str(snap.get("prompt_version") or "–"), str(snap.get("model") or "–"))
        if key not in groups:
            groups[key] = VersionQuality(*key)
            order.append(key)
        q = groups[key]
        q.decisions += 1
        recommendation, confidence, result = snap.get("recommendation"), snap.get("confidence"), decision.result
        if decision.action != "approve":
            q.reasons.update(decision.reason_codes or [])
        if recommendation == Recommendation.INSUFFICIENT:
            q.insufficient += 1
            continue
        q.compared += 1
        agreed = recommendation == result
        q.agreed += agreed
        course = courses.get(evaluation.candidate_course_id) if evaluation.candidate_course_id else None
        department = course.department_name if course and course.department_name else "–"
        bucket = q.departments.setdefault(department, [0, 0])
        bucket[0] += 1
        bucket[1] += agreed
        if confidence == Confidence.HIGH and recommendation in (DecisionResult.DIRECT, DecisionResult.ELECTIVE):
            q.strong += 1
            q.strong_wrong += not agreed
    return [groups[k] for k in reversed(order)]


def current_failing(rows: list[VersionQuality]) -> VersionQuality | None:
    """가장 최근에 판정이 쌓인 버전이 기준 미달이면 그 버전 (관리자 콘솔 경고)."""
    return rows[0] if rows and rows[0].gate == FAIL else None
