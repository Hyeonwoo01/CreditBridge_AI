"""AI(Claude·GPT) 비교로 매핑·개념별 커버리지 산출 (FR-05, FR-06). 근거 구절은 원문 검증을 통과한 것만 남기고,
학생 쪽은 선수과목·교재 칸이나 부정 문장에서 나온 구절도 뺀다."""

import json
from dataclasses import dataclass

from backend.ai import injection
from backend.ai.evidence import QuoteCounts, Span, teaching_evidence, verify_quotes, weeks_of
from backend.ai.llm_client import LLMClient, LLMResult
from backend.ai.prompts_loader import load_prompt
from backend.schemas.evaluation import CandidateJudgment, EvaluationOutput
from backend.schemas.results import ConceptResult, EvidenceView, ReviewItemResult
from backend.services import review_frameworks


@dataclass(frozen=True)
class Reference:
    """비교 대상 과목과 기준 강의계획서."""

    course_id: int
    code: str
    title: str
    credits: float
    level: str
    syllabus_id: int
    text: str
    concepts: list[str]
    department: str = ""  # 분야별 확인 항목을 고르는 학과 이름 (review_frameworks.for_department)


@dataclass(frozen=True)
class VerifiedSpan:
    side: str  # source | target
    syllabus_id: int
    start: int
    end: int
    concept: str


def build_prompt(
    target_institution: str, references: list[Reference], credits: float | None, student_text: str
) -> tuple[str, str]:
    """평가 프롬프트와 프롬프트 버전. 학생 문서의 의심 문구 줄은 제외하고 넣는다."""
    blocks = []
    for ref in references:
        header = json.dumps(
            {
                "course_code": ref.code,
                "title": ref.title,
                "credits": ref.credits,
                "level": ref.level,
                "concepts": ref.concepts,
                # 교수 체크리스트 중 문서에 적혀 있는지로 답할 수 있는 항목 (미리 채우기, 판정이 아님)
                "review_items": [
                    {"key": key, "look_for": look_for}
                    for key, look_for in review_frameworks.findable(review_frameworks.for_department(ref.department))
                ],
            },
            ensure_ascii=False,
        )
        # 기관이 올린 기준 강의계획서도 문서 속 지시 문구는 데이터로만 다룬다 (근거 검증은 원문 기준)
        ref_text = injection.sanitize(ref.text, injection.detect(ref.text))
        blocks.append(f"<candidate>\n{header}\n<reference_syllabus>\n{ref_text}\n</reference_syllabus>\n</candidate>")
    prompt = load_prompt("evaluation")
    rendered = prompt.render(
        target_institution=target_institution,
        candidates="\n".join(blocks),
        credits=f"{credits:g}" if credits is not None else "not stated",
        student_syllabus=injection.sanitize(student_text, injection.detect(student_text)),
    )
    return rendered, prompt.version


def compare(llm: LLMClient, prompt: str) -> LLMResult[EvaluationOutput]:
    return llm.parse(prompt, EvaluationOutput, effort="medium")


def concept_results(
    judgment: CandidateJudgment,
    ref: Reference,
    student_text: str,
    student_syllabus_id: int,
    non_teaching: list[Span] | None = None,
    counts: QuoteCounts | None = None,
) -> tuple[list[ConceptResult], list[VerifiedSpan]]:
    """대상 과목의 필수 개념 순서대로 판단을 정리한다. coverage는 AI가 매긴 원점수(0~1)이고,
    근거 검증에 따른 보정은 services/scoring.py가 한다. 응답에 빠진 개념은 판단 불가로 둔다.
    non_teaching은 학생 강의계획서의 선수과목·교재 칸 위치(evidence.non_teaching_regions), counts는 받은·버린 인용 수.
    source_weeks·target_weeks는 검증된 근거가 걸친 주차 수(깊이 비교, services/scoring.apply_depth)."""
    by_name = {c.concept.strip().lower(): c for c in judgment.concepts}
    results: list[ConceptResult] = []
    spans: list[VerifiedSpan] = []
    for concept in ref.concepts:
        j = by_name.get(concept.strip().lower())
        if j is None:
            results.append(
                ConceptResult(
                    concept=concept,
                    status="unclear",
                    coverage=0.0,
                    reason="",
                    verified=False,
                    source_evidence=[],
                    target_evidence=[],
                )
            )
            continue
        context = f"{ref.code}|{concept}"[:255]
        src = verify_quotes(student_text, j.source_quotes, context=context, counts=counts)
        src = teaching_evidence(student_text, src, non_teaching or [], context=context, counts=counts)
        tgt = verify_quotes(ref.text, j.target_quotes, context=context, counts=counts)
        spans += [VerifiedSpan("source", student_syllabus_id, s.start, s.end, context) for s in src]
        spans += [VerifiedSpan("target", ref.syllabus_id, s.start, s.end, context) for s in tgt]
        results.append(
            ConceptResult(
                concept=concept,
                status=j.status,
                coverage=j.coverage / 100,
                reason=j.reason,
                reason_en=j.reason_en,
                verified=bool(src),
                source_weeks=weeks_of(student_text, src),
                target_weeks=weeks_of(ref.text, tgt),
                source_evidence=[
                    EvidenceView(side="source", text=student_text[s.start : s.end], char_start=s.start, char_end=s.end)
                    for s in src
                ],
                target_evidence=[
                    EvidenceView(side="target", text=ref.text[s.start : s.end], char_start=s.start, char_end=s.end)
                    for s in tgt
                ],
            )
        )
    return results, spans


def review_item_results(judgment: CandidateJudgment, ref: Reference, student_text: str) -> list[ReviewItemResult]:
    """체크리스트 항목 미리 채우기. 이 후보 분야의 항목 순서대로, 인용은 원문과 일치할 때만 남긴다.
    적혀 있다고 했는데 인용이 원문과 다르면 unverified(근거 없음)로 둔다. 응답에 없는 항목은 빼고 모르는 키는 버린다."""
    wanted = [k for k, _ in review_frameworks.findable(review_frameworks.for_department(ref.department))]
    by_key = {f.key.strip(): f for f in judgment.review_items}
    out: list[ReviewItemResult] = []
    for key in wanted:
        finding = by_key.get(key)
        if finding is None:
            continue
        if not finding.stated:
            out.append(ReviewItemResult(key=key, status="not_found"))
            continue
        spans = verify_quotes(student_text, [finding.quote] if finding.quote else [], context=f"review|{key}")
        if not spans:
            out.append(ReviewItemResult(key=key, status="unverified"))
            continue
        span = spans[0]
        out.append(
            ReviewItemResult(
                key=key,
                status="found",
                quote=student_text[span.start : span.end],
                char_start=span.start,
                char_end=span.end,
            )
        )
    return out
