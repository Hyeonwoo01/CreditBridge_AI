"""강의계획서 버전 비교: 개념별 변화 판단과 덧붙인 보완 자료 찾기."""

from datetime import datetime

from backend.models import CourseEvaluation, SupplementFile, Syllabus
from backend.schemas.results import CandidateResult, ConceptResult, EvaluationResult
from backend.services import versions


def _evaluation(eid: int, rec: str, coverage: float, concepts: list[tuple[str, str, float, int]], course: int = 1):
    result = EvaluationResult(
        candidates=[
            CandidateResult(
                course_id=course,
                course_code=f"C{course}",
                course_title="",
                credits=3,
                level="same",
                level_note="",
                summary="",
                coverage=coverage,
                concepts=[
                    ConceptResult(
                        concept=name,
                        status=status,
                        coverage=cov,
                        reason="",
                        verified=True,
                        source_evidence=[
                            {"side": "source", "text": "x", "char_start": 0, "char_end": 1} for _ in range(n)
                        ],  # type: ignore[misc]
                        target_evidence=[],
                    )
                    for name, status, cov, n in concepts
                ],
            )
        ],
        missing_fields=[],
        missing_concepts=[],
        missing_materials=[],
        warnings=[],
        no_match_reason="",
        injection_flags=[],
    )
    return CourseEvaluation(
        id=eid,
        syllabus_id=1,
        status="done",
        recommendation=rec,
        coverage=coverage,
        confidence="medium",
        coverage_json=result.model_dump(),
        prompt_version="evaluation-v1",
        created_at=datetime(2026, 10, eid),
    )


def test_concept_trends_and_added_text() -> None:
    before = _evaluation(1, "elective", 0.5, [("Limits", "partial", 0.5, 1), ("Series", "taught", 0.9, 1)])
    after = _evaluation(
        2, "direct", 0.8, [("limits", "taught", 0.9, 2), ("Series", "taught", 0.8, 1), ("Proofs", "taught", 0.7, 1)]
    )
    syllabus = Syllabus(raw_text="Week 1\n\n[보완 자료: plan.pdf]\nWeek 9: Eigenvalues")
    files = [SupplementFile(id=1, file_key="k/plan.pdf", created_at=datetime(2026, 10, 1, 12))]
    cmp = versions.compare(before, after, syllabus, files)
    assert [c.trend for c in cmp.concepts] == ["up", "down", "new"]
    assert cmp.counts["up"] == 1 and cmp.trend("rec") == "up" and cmp.trend("coverage") == "up"
    assert cmp.concepts[0].evidence_before == 1 and cmp.concepts[0].evidence_after == 2
    assert [(a.filename, a.text) for a in cmp.added] == [("plan.pdf", "Week 9: Eigenvalues")]
    assert versions.previous_done(after, [after, before]) is before
    assert versions.previous_done(before, [after, before]) is None

    other = _evaluation(3, "elective", 0.6, [("Vectors", "partial", 0.6, 1)], course=2)
    cmp = versions.compare(after, other, syllabus, [])
    assert not cmp.same_candidate and not cmp.concepts and not cmp.added
