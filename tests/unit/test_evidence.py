from backend.ai.evidence import locate, non_teaching_regions, teaching_evidence, verify_quotes

TEXT = (
    "Week 5: Differentiation rules:  product rule and\nquotient rule\nWeek 6: The chain rule, implicit differentiation"
)


def test_locate_exact_and_whitespace_insensitive() -> None:
    span = locate(TEXT, "product rule and quotient rule")
    assert span is not None
    assert TEXT[span.start : span.end] == "product rule and\nquotient rule"


def test_locate_normalizes_quotes_and_dashes() -> None:
    text = "Use L’Hopital’s rule — carefully"
    span = locate(text, "L'Hopital's rule - carefully")
    assert span is not None and text[span.start : span.end] == "L’Hopital’s rule — carefully"


def test_paraphrase_or_invented_quote_is_rejected() -> None:
    assert locate(TEXT, "the product and quotient rules") is None
    assert locate(TEXT, "Week 9: eigenvalues") is None
    assert locate(TEXT, "Wee") is None  # 너무 짧은 구절


def test_verify_quotes_keeps_only_verified_and_dedupes() -> None:
    spans = verify_quotes(TEXT, ["The chain rule", "The chain rule", "made up sentence"], context="t")
    assert len(spans) == 1
    assert TEXT[spans[0].start : spans[0].end] == "The chain rule"


def test_case_and_punctuation_differences_map_back_to_original_text() -> None:
    text = "Week 3: Continuity, intermediate value theorem; limits at infinity."
    span = locate(text, "week 3 - continuity intermediate value theorem, limits at infinity")
    assert span is not None
    assert text[span.start : span.end] == "Week 3: Continuity, intermediate value theorem; limits at infinity"


def test_ellipsis_quote_covers_the_original_passage() -> None:
    text = "Systems of linear equations, Gaussian elimination, row reduction and echelon forms."
    span = locate(text, "Gaussian elimination ... echelon forms")
    assert span is not None and text[span.start : span.end] == "Gaussian elimination, row reduction and echelon forms"
    assert locate(text, "Gaussian elimination … eigenvalues") is None  # 생략 뒤 조각이 원문에 없으면 버린다


def test_changed_words_are_still_rejected() -> None:
    text = "Topics covered: limits and continuity. Lab work is not covered."
    assert locate(text, "Lab work is covered") is None  # 뜻이 반대인 인용
    assert locate(text, "limit and continuity") is None  # 단어 형태가 다름
    assert locate("Grading: Midterm 40%, Final 60%", "Midterm 40, Final 60") is None  # % 는 의미 있는 기호
    assert locate("3.5 credits", "35 credits") is None  # 문장부호는 공백으로 바뀌어 숫자가 붙지 않는다
    assert locate("product rules", "product rule") is None  # 단어 중간에서 끝나는 일치


def test_wrapping_quotes_and_korean_particles() -> None:
    assert locate("Week 2: Limits", '"Week 2: Limits"') is not None  # 인용 부호로 감싼 구절
    text = "3주차: 미분법과 적분법의 기본 정리"
    span = locate(text, "미분법과 적분법")  # 뒤에 조사가 붙은 원문에서도 원문 위치를 찾는다
    assert span is not None and text[span.start : span.end] == "미분법과 적분법"
    assert locate(text, "미분법과 적분법 정리") is None  # 단어가 빠지면 버린다


def test_ellipsis_with_short_or_distant_parts_is_rejected() -> None:
    weeks = "1주차: 이수 학점 안내와 강의 소개\n2주차: 미분\n3주차: 적분\n4주차: 학점 인정 기준"
    assert locate(weeks, "이수 ... 인정") is None  # 조각이 너무 짧아 여러 주차를 묶어 버린다
    far = "Week 1: Limits and continuity. " + "Filler topic text. " * 30 + "Week 15: Final exam review."
    assert locate(far, "Limits and continuity ... Final exam review") is None  # 조각 사이가 너무 멀다


SYLLABUS = (
    "Course: Business Analytics\n"
    "Prerequisites: Regression analysis (STAT 201)\n"
    "\n"
    "Textbook: Inventory Management, 3rd ed.\n"
    "Week 1: Descriptive statistics and data visualization\n"
    "Week 2: Linear regression and model fitting\n"
    "Machine learning is not covered in this course; see the next course.\n"
    "8주차: 시계열 예측. 딥러닝은 다루지 않는다.\n"
)


def _kept(quote: str, items: list[str] | None = None) -> bool:
    spans = verify_quotes(SYLLABUS, [quote], context="t")
    assert spans, quote  # 원문 검증은 통과하는 구절들
    regions = non_teaching_regions(SYLLABUS, items or [])
    return bool(teaching_evidence(SYLLABUS, spans, regions, context="t"))


def test_quotes_from_prerequisite_or_textbook_sections_are_not_teaching_evidence() -> None:
    assert not _kept("Prerequisites: Regression analysis")
    assert not _kept("Regression analysis (STAT 201)")
    assert not _kept("Inventory Management, 3rd ed.")
    # 칸은 다음 수업 내용 제목에서 끝난다: 교재 줄 바로 아래 주차 계획은 근거로 남는다
    assert _kept("Week 2: Linear regression and model fitting")
    assert _kept("Descriptive statistics and data visualization")


def test_negated_or_deferred_topics_are_not_teaching_evidence() -> None:
    assert not _kept("Machine learning is not covered in this course")
    assert not _kept("딥러닝은 다루지 않는다")
    assert _kept("8주차: 시계열 예측")


def test_extracted_prerequisite_items_mark_regions_without_headings() -> None:
    text = "Students must have completed Calculus I.\nWeek 1: Limits and continuity"
    spans = verify_quotes(text, ["completed Calculus I", "Limits and continuity"], context="t")
    kept = teaching_evidence(text, spans, non_teaching_regions(text, ["completed Calculus I"]), context="t")
    assert [text[s.start : s.end] for s in kept] == ["Limits and continuity"]


def test_korean_prerequisite_heading_section() -> None:
    text = "선수과목: 회귀분석, 기초통계\n\n3주차: 회귀분석 실습"
    regions = non_teaching_regions(text, [])
    spans = verify_quotes(text, ["회귀분석, 기초통계", "3주차: 회귀분석 실습"], context="t")
    kept = teaching_evidence(text, spans, regions, context="t")
    assert [text[s.start : s.end] for s in kept] == ["3주차: 회귀분석 실습"]


def test_concept_quoted_only_from_prerequisites_is_capped() -> None:
    from backend.ai.matching import Reference, concept_results
    from backend.schemas.evaluation import CandidateJudgment, ConceptJudgment
    from backend.services.scoring import UNVERIFIED_CAP, apply_verification

    def judged(concept: str, quote: str) -> ConceptJudgment:
        return ConceptJudgment(
            concept=concept,
            status="taught",
            coverage=90,
            source_quotes=[quote],
            target_quotes=[],
            reason="",
            reason_en="",
        )

    ref = Reference(1, "BUS 300", "Analytics", 3.0, "same", 2, "ref", ["Regression", "Visualization"])
    judgment = CandidateJudgment(
        course_code="BUS 300",
        level="same",
        level_note="",
        level_note_en="",
        summary="",
        summary_en="",
        concepts=[
            judged("Regression", "Regression analysis (STAT 201)"),
            judged("Visualization", "Descriptive statistics and data visualization"),
        ],
    )
    regions = non_teaching_regions(SYLLABUS, ["Regression analysis (STAT 201)"])
    results, spans = concept_results(judgment, ref, SYLLABUS, 7, regions)
    regression, visualization = results
    assert not regression.verified and regression.source_evidence == []
    assert apply_verification(regression.status, regression.coverage, regression.verified) == UNVERIFIED_CAP
    assert visualization.verified and len(spans) == 1


def test_weeks_of_counts_week_blocks_touched_by_evidence() -> None:
    from backend.ai.evidence import weeks_of

    text = (
        "Learning outcomes: apply regression models.\n"
        "Week 1: Intro\nWeek 2: Regression basics\nWeeks 3-4: Multiple regression\n5주차: 회귀 진단\n제6주 시계열"
    )

    def weeks(*quotes: str) -> int:
        return weeks_of(text, verify_quotes(text, list(quotes), context="t"))

    assert weeks("Regression basics") == 1
    assert weeks("Regression basics", "Multiple regression") == 3  # "Weeks 3-4"는 두 주
    assert weeks("회귀 진단", "제6주 시계열") == 2
    assert weeks("apply regression models") == 0  # 주차 계획 밖 (학습 목표)
    assert weeks_of("No schedule here", []) == 0


def test_quote_counts_track_unmatched_and_non_teaching() -> None:
    from backend.ai.evidence import QuoteCounts

    counts = QuoteCounts()
    spans = verify_quotes(SYLLABUS, ["Regression analysis (STAT 201)", "made up", "Week 1"], context="t", counts=counts)
    teaching_evidence(SYLLABUS, spans, non_teaching_regions(SYLLABUS, []), context="t", counts=counts)
    assert (counts.total, counts.unmatched, counts.non_teaching) == (3, 1, 1)


def test_negation_filter_keeps_ordinary_teaching_sentences() -> None:
    from backend.ai.evidence import _NEGATION

    # 시뮬레이션에서 잘못 버리던 수업 문장들
    for kept in (
        "Week 5: Derivatives; quiz in the following class",
        "This course covers limits and derivatives and prepares students for the next course in the sequence",
        "Students will not only learn regression but also classification",
        "Students won't need prior experience; week 2 introduces loops",
        "Pauli exclusion principle and electron configuration",
        "미적분학 II 등 후속 과목의 기초가 되는 극한과 미분을 다룬다",
        "9주차: 이미 배운 미분을 응용하여 최적화 문제를 푼다",
    ):
        assert not _NEGATION.search(kept), kept
    for dropped in (
        "We will not cover eigenvalues",
        "Integration won't be taught until Calculus II",
        "Series are covered in the next course (MATH 102)",
        "Proofs are deferred to the next course",
        "Lab work is not part of this course",
        "This course assumes knowledge of linear algebra",
        "적분은 후속 과목에서 다룬다",
        "다중회귀는 다음 학기에 배운다",
        "선형대수 기초는 알고 있다고 가정한다",
    ):
        assert _NEGATION.search(dropped), dropped


def test_prerequisite_region_stops_at_inline_week_marker() -> None:
    text = "Prerequisites: MATH 101   Week 1: Limits and continuity\nWeek 2: Derivatives"
    spans = verify_quotes(text, ["MATH 101", "Week 1: Limits and continuity"], context="t")
    kept = teaching_evidence(text, spans, non_teaching_regions(text, []), context="t")
    assert [text[s.start : s.end] for s in kept] == ["Week 1: Limits and continuity"]
