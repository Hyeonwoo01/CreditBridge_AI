"""강의계획서 버전 비교: 보완 자료나 분석 기준이 바뀌어 다시 분석했을 때 바로 앞 분석과 무엇이 달라졌는지.

같은 강의계획서의 분석은 고치지 않고 새 행으로 쌓이므로(course_evaluations), 바로 앞의 완료된 분석과
1순위 후보·추천·커버리지·신뢰도, 개념별 판단·근거 구절 수를 나란히 놓고, 그 사이에 덧붙인 보완 자료를 보여 준다."""

import re
from dataclasses import dataclass, field

from backend.i18n import gettext as tr
from backend.models import CourseEvaluation, SupplementFile, Syllabus
from backend.models.enums import EvaluationStatus
from backend.schemas.results import CandidateResult, ConceptResult, EvaluationResult

# 판단이 좋아진 정도를 비교하는 순서 (다룸이 가장 좋음)
STATUS_RANK = {"not_taught": 0, "unclear": 1, "partial": 2, "taught": 3}
REC_RANK = {"none": 0, "insufficient": 0, "elective": 1, "direct": 2}
CONF_RANK = {"low": 0, "medium": 1, "high": 2}
SUPPLEMENT_MARK = re.compile(r"\n\n\[보완 자료: ([^\]\n]+)\]\n")


@dataclass
class ConceptChange:
    concept: str
    before: ConceptResult | None  # 이전 분석에 없던 개념이면 None
    after: ConceptResult | None  # 이번 분석에서 빠진 개념이면 None

    @property
    def trend(self) -> str:
        """up / down / same / new / gone"""
        if self.before is None:
            return "new"
        if self.after is None:
            return "gone"
        rank = STATUS_RANK.get(self.after.status, 0) - STATUS_RANK.get(self.before.status, 0)
        delta = round(self.after.coverage - self.before.coverage, 3)
        if rank > 0 or (rank == 0 and delta > 0):
            return "up"
        if rank < 0 or (rank == 0 and delta < 0):
            return "down"
        return "same"

    @property
    def evidence_before(self) -> int:
        return len(self.before.source_evidence) if self.before else 0

    @property
    def evidence_after(self) -> int:
        return len(self.after.source_evidence) if self.after else 0


@dataclass
class AddedMaterial:
    filename: str
    text: str  # 원문에 덧붙인 글 (없으면 "")


@dataclass
class Comparison:
    previous: CourseEvaluation
    current: CourseEvaluation
    previous_primary: CandidateResult | None
    current_primary: CandidateResult | None
    concepts: list[ConceptChange] = field(default_factory=list)
    added: list[AddedMaterial] = field(default_factory=list)

    @property
    def same_candidate(self) -> bool:
        p, c = self.previous_primary, self.current_primary
        return p is not None and c is not None and p.course_id == c.course_id

    @property
    def prompt_changed(self) -> bool:
        return (self.previous.prompt_version or "") != (self.current.prompt_version or "")

    def trend(self, kind: str) -> str:
        """추천(rec)·커버리지(coverage)·신뢰도(conf)가 좋아졌는지: up / down / same"""
        p, c = self.previous, self.current
        if kind == "coverage":
            diff = round((c.coverage or 0) - (p.coverage or 0), 3)
        elif kind == "rec":
            diff = REC_RANK.get(c.recommendation or "", 0) - REC_RANK.get(p.recommendation or "", 0)
            if diff == 0 and p.recommendation != c.recommendation:
                return "up" if p.recommendation == "insufficient" else "down"
        else:
            diff = CONF_RANK.get(c.confidence or "", 0) - CONF_RANK.get(p.confidence or "", 0)
        return "up" if diff > 0 else "down" if diff < 0 else "same"

    @property
    def counts(self) -> dict[str, int]:
        out = {"up": 0, "down": 0, "same": 0, "new": 0, "gone": 0}
        for change in self.concepts:
            out[change.trend] += 1
        return out


def _result(evaluation: CourseEvaluation) -> EvaluationResult | None:
    return EvaluationResult.model_validate(evaluation.coverage_json) if evaluation.coverage_json else None


def _primary(result: EvaluationResult | None) -> CandidateResult | None:
    return result.candidates[0] if result and result.candidates else None


def previous_done(current: CourseEvaluation, history: list[CourseEvaluation]) -> CourseEvaluation | None:
    """current보다 먼저 끝난 분석 중 가장 최근 것."""
    older = [
        e
        for e in history
        if e.status == EvaluationStatus.DONE
        and e.id != current.id
        and (e.created_at, e.id) < (current.created_at, current.id)
    ]
    return max(older, key=lambda e: (e.created_at, e.id), default=None)


def added_materials(
    syllabus: Syllabus, files: list[SupplementFile], previous: CourseEvaluation, current: CourseEvaluation
) -> list[AddedMaterial]:
    """두 분석 사이에 올린 보완 자료와 원문에 덧붙인 글."""
    sections: dict[str, str] = {}
    marks = list(SUPPLEMENT_MARK.finditer(syllabus.raw_text))
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(syllabus.raw_text)
        sections[mark.group(1)] = syllabus.raw_text[mark.end() : end].strip()
    out = []
    for f in sorted(files, key=lambda f: (f.created_at, f.id)):
        if not previous.created_at < f.created_at <= current.created_at:
            continue
        name = (f.file_key or "").rsplit("/", 1)[-1] or tr("보완 자료")
        out.append(AddedMaterial(filename=name, text=sections.get(name, "")))
    return out


def compare(
    previous: CourseEvaluation, current: CourseEvaluation, syllabus: Syllabus, files: list[SupplementFile]
) -> Comparison:
    before, after = _result(previous), _result(current)
    current_primary = _primary(after)
    # 이전 분석의 후보 중 이번 1순위와 같은 과목을 찾아 개념을 맞춘다 (없으면 개념 비교는 하지 않는다)
    previous_candidates = before.candidates if before else []
    previous_same = next(
        (c for c in previous_candidates if current_primary and c.course_id == current_primary.course_id), None
    )
    comparison = Comparison(previous, current, _primary(before), current_primary)
    if current_primary is not None and previous_same is not None:
        old = {k.concept.strip().lower(): k for k in previous_same.concepts}
        seen = set()
        for k in current_primary.concepts:
            key = k.concept.strip().lower()
            seen.add(key)
            comparison.concepts.append(ConceptChange(k.concept, old.get(key), k))
        for key, k in old.items():
            if key not in seen:
                comparison.concepts.append(ConceptChange(k.concept, k, None))
    comparison.added = added_materials(syllabus, files, previous, current)
    return comparison
