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
