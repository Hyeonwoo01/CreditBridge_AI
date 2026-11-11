"""증거 적용 학기 비교 (리뷰 v3 P0-5)."""

from typing import Any

from backend.services import evidence_status as ev


def test_normalize_term_formats() -> None:
    assert ev.normalize_term("2024-1") == (2024, "1")
    assert ev.normalize_term("2024 Fall") == (2024, "2")
    assert ev.normalize_term("Spring 2024") == (2024, "1")
    assert ev.normalize_term("2024년 2학기") == (2024, "2")
    assert ev.normalize_term("2024 여름") == (2024, "S")
    assert ev.normalize_term("2024") is None and ev.normalize_term("") is None and ev.normalize_term(None) is None


def test_applicability() -> None:
    assert ev.applicability("2024-1", "Spring 2024") == "applicable"
    assert ev.applicability("2023-2", "2024 Fall") == "mismatch"  # 다른 학기 자료는 수강 당시 자료가 아니다
    assert ev.applicability(None, "2024-1") == "unknown"


def test_hold_only_for_suspicious_or_rejected() -> None:
    syl: Any = type("S", (), {"authenticity": "unverified"})()
    assert ev.hold_reason(syl) is None
    syl.authenticity = "suspicious"
    assert ev.hold_reason(syl) is not None
    syl.authenticity = "rejected"
    assert ev.hold_reason(syl) is not None
