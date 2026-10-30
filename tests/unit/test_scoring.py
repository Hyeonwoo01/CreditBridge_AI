from backend.models.enums import Confidence, Recommendation
from backend.schemas.results import ConceptResult
from backend.services.scoring import apply_verification, is_sparse, score_candidate


def concept(status: str, coverage: int, verified: bool = True) -> ConceptResult:
    return ConceptResult(
        concept=f"c{coverage}{status}",
        status=status,
        coverage=apply_verification(status, coverage / 100, verified),
        reason="",
        verified=verified,
        source_evidence=[],
        target_evidence=[],
    )


def test_full_verified_coverage_is_direct_with_high_confidence() -> None:
    s = score_candidate([concept("taught", 95)] * 5, "same", sparse_document=False, elective_eligible=True)
    assert s.recommendation is Recommendation.DIRECT
    assert s.confidence is Confidence.HIGH
    assert s.coverage >= 0.9


def test_lower_level_never_direct() -> None:
    s = score_candidate([concept("taught", 100)] * 4, "lower", sparse_document=False, elective_eligible=False)
    assert s.recommendation is Recommendation.ELECTIVE
    assert s.adjusted == 0.75


def test_unverified_claims_are_capped_and_lower_confidence() -> None:
    concepts = [concept("taught", 100, verified=False)] * 3 + [concept("taught", 100)]
    s = score_candidate(concepts, "same", sparse_document=False, elective_eligible=True)
    assert s.recommendation is Recommendation.INSUFFICIENT  # 근거 확인 25% → 신뢰도 하 → 정보 부족
    assert s.confidence is Confidence.LOW


def test_many_unclear_concepts_means_insufficient() -> None:
    concepts = [concept("unclear", 0)] * 2 + [concept("taught", 90)] * 2
    s = score_candidate(concepts, "same", sparse_document=False, elective_eligible=True)
    assert s.recommendation is Recommendation.INSUFFICIENT
    assert len(s.missing_concepts) == 2


def test_partial_overlap_is_elective_and_no_overlap_is_none() -> None:
    mid = score_candidate(
        [concept("taught", 90)] * 2 + [concept("not_taught", 0)] * 2,
        "same",
        sparse_document=False,
        elective_eligible=False,
    )
    assert mid.recommendation is Recommendation.ELECTIVE
    low = score_candidate([concept("not_taught", 0)] * 4, "same", sparse_document=False, elective_eligible=False)
    assert low.recommendation is Recommendation.NONE


def test_same_input_same_output() -> None:
    concepts = [concept("taught", 80), concept("partial", 50), concept("taught", 95)]
    a = score_candidate(concepts, "same", sparse_document=False, elective_eligible=True)
    b = score_candidate(concepts, "same", sparse_document=False, elective_eligible=True)
    assert a == b


def test_sparse_document_detection() -> None:
    assert is_sparse(0, 1)
    assert not is_sparse(12, 0)


def test_score_has_no_probability() -> None:
    """MVP는 판정 확률을 계산하지 않는다 (기능명세서 FR-07)."""
    s = score_candidate([concept("taught", 90)] * 3, "same", sparse_document=False, elective_eligible=True)
    assert not hasattr(s, "probability")


def test_concept_mentioned_in_one_week_is_partial_when_reference_spends_more() -> None:
    from backend.services.scoring import SHALLOW_CAP, apply_depth

    shallow = concept("taught", 95)
    shallow.source_weeks, shallow.target_weeks = 1, 3
    apply_depth(shallow)
    assert shallow.status == "partial" and shallow.coverage == SHALLOW_CAP and shallow.shallow

    for source_weeks, target_weeks in ((2, 3), (1, 1), (0, 3), (1, 0)):  # 여러 주 다룸·같은 깊이·주차 모름
        c = concept("taught", 95)
        c.source_weeks, c.target_weeks = source_weeks, target_weeks
        apply_depth(c)
        assert c.status == "taught" and c.coverage == 0.95 and not c.shallow
