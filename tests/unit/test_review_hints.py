"""분야별 확인 항목 미리 채우기 (리뷰 v3 P1-1): 인용은 원문과 일치할 때만, 판정을 대신하지 않음."""

import json

from backend.ai import matching
from backend.ai.prompts_loader import load_prompt
from backend.schemas.evaluation import CandidateJudgment, ReviewItemFinding

STUDENT = (
    "MATH 101 Calculus I (3 credits)\n"
    "Learning outcomes: compute limits and derivatives.\n"
    "Prerequisite: Precalculus.\n"
    "Week 1: Limits and continuity\n"
)
REF = matching.Reference(
    course_id=1,
    code="MATH 1151",
    title="Calculus I",
    credits=4,
    level="intro",
    syllabus_id=2,
    text="Week 1: Limits",
    concepts=["Limits"],
    department="Mathematics",
)


def judgment(items: list[ReviewItemFinding]) -> CandidateJudgment:
    return CandidateJudgment(
        course_code="MATH 1151",
        level="same",
        level_note="",
        level_note_en="",
        concepts=[],
        summary="",
        summary_en="",
        review_items=items,
    )


def test_prompt_lists_findable_items_of_the_candidate_field() -> None:
    prompt, version = matching.build_prompt("MSU", [REF], 3, STUDENT)
    assert version == load_prompt("evaluation").version == "evaluation-v4"
    header = json.loads(prompt.split("<candidate>\n", 1)[1].split("\n", 1)[0])
    keys = [i["key"] for i in header["review_items"]]
    assert "proofs" in keys and "prerequisites" in keys  # 수학 분야 항목
    assert "evidence" not in keys and "ai_inferred" not in keys  # 교수가 직접 하는 확인은 묻지 않는다


def test_quotes_are_kept_only_when_they_match_the_original() -> None:
    found = matching.review_item_results(
        judgment(
            [
                ReviewItemFinding(key="prerequisites", stated=True, quote="Prerequisite: Precalculus."),
                ReviewItemFinding(key="outcomes", stated=True, quote="Students will master proofs."),  # 원문에 없음
                ReviewItemFinding(key="proofs", stated=False, quote=""),
                ReviewItemFinding(key="lab_hours", stated=True, quote="Week 1"),  # 수학 분야 항목이 아님
            ]
        ),
        REF,
        STUDENT,
    )
    by_key = {r.key: r for r in found}
    assert set(by_key) == {"prerequisites", "outcomes", "proofs"}
    pre = by_key["prerequisites"]
    assert pre.status == "found" and STUDENT[pre.char_start : pre.char_end] == pre.quote  # type: ignore[misc]
    assert by_key["outcomes"].status == "unverified" and by_key["outcomes"].quote == ""
    assert by_key["proofs"].status == "not_found"
    # 결과 순서는 분야 항목 순서
    assert [r.key for r in found] == ["outcomes", "proofs", "prerequisites"]
