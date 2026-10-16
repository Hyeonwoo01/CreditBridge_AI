"""화면 언어: 번역 목록이 코드·템플릿과 맞는지, 언어 고르기, 저장된 한국어 글 번역."""

from backend.i18n import from_accept_language, gettext, normalize, translate_stored, use_locale
from scripts.i18n_check import problems


def test_catalog_covers_every_message() -> None:
    missing, unused, mismatched = problems()
    assert not missing, "\n".join(missing[:20])
    assert not mismatched, "\n".join(mismatched[:20])
    assert not unused, "\n".join(unused[:20])


def test_locale_choice() -> None:
    assert normalize("en-US") == "en" and normalize("KO") == "ko" and normalize("fr") is None
    assert from_accept_language("en-US,en;q=0.9,ko;q=0.8") == "en"
    assert from_accept_language("ko-KR,ko;q=0.9,en-US;q=0.8") == "ko"
    assert from_accept_language("fr-FR,de;q=0.9") is None and from_accept_language(None) is None


def test_gettext_formats_and_picks_plural() -> None:
    assert gettext("판정할 심사 {pending}건", pending=2) == "판정할 심사 2건"  # 한국어는 원문 그대로
    with use_locale("en"):
        assert gettext("판정할 심사 {pending}건", pending=1) == "1 review to decide"
        assert gettext("판정할 심사 {pending}건", pending=3) == "3 reviews to decide"
        assert gettext("없는 원문") == "없는 원문"  # 번역이 없으면 한국어 그대로


def test_stored_korean_text_is_translated_for_display() -> None:
    stored = "기한 알림: 판정 기한이 지난 심사 1건 · 내일까지 판정할 심사 2건"
    assert translate_stored(stored) == stored
    with use_locale("en"):
        assert translate_stored(stored) == (
            "Deadline reminder: 1 review past its decision deadline · 2 reviews to decide by tomorrow"
        )
        assert translate_stored("MATH 101 판정 결과가 확정됐어요: 직접 인정") == (
            "The decision for MATH 101 is final: Direct credit"
        )
        assert translate_stored("AI 분석에 실패했어요. 잠시 후 다시 분석을 요청해 주세요.").startswith(
            "The AI analysis"
        )
        assert translate_stored("학생이 직접 쓴 글") == "학생이 직접 쓴 글"


def test_ai_text_falls_back_to_korean_for_older_results() -> None:
    from backend.schemas.results import ConceptResult, EvaluationResult
    from backend.web.templating import ai_list, ai_text, ai_warnings

    old = ConceptResult(
        concept="Limits",
        status="taught",
        coverage=0.9,
        reason="극한을 다뤄요",
        verified=True,
        source_evidence=[],
        target_evidence=[],
    )
    new = old.model_copy(update={"reason_en": "Limits are covered"})
    result = EvaluationResult(
        candidates=[],
        missing_fields=[],
        missing_concepts=[],
        missing_materials=["주차별 상세 강의 계획", "AI가 제안한 자료"],
        warnings=["AI가 쓴 경고", "판정을 유도하는 의심 문구가 있어 해당 줄을 분석에서 제외했어요."],
        no_match_reason="",
        injection_flags=[],
        warnings_en=["AI warning", ""],
    )
    assert ai_text(new, "reason") == "극한을 다뤄요"
    with use_locale("en"):
        assert ai_text(new, "reason") == "Limits are covered"
        assert ai_text(old, "reason") == "극한을 다뤄요"  # evaluation-v1 결과는 한국어 그대로
        assert ai_text(None, "summary", "요약") == "요약"
        assert ai_list(result, "missing_materials") == ["Detailed weekly course plan", "AI가 제안한 자료"]
        warnings = ai_warnings(result)
        assert warnings[0] == "AI warning" and warnings[1].startswith("Suspicious wording")
