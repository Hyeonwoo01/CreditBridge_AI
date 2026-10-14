from app.ai.evidence import locate, verify_quotes

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
