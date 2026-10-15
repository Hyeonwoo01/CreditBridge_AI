from datetime import datetime

import pytest

from backend.errors import DecisionValidationError
from backend.services.decisions import SIMILARITY_MIN, HistoryItem, _validate_reasons, conflicts, similarity


def item(result: str, sim: float, same_target: bool = True) -> HistoryItem:
    return HistoryItem(datetime(2025, 1, 1), result, "MATH 2568", [], "", 1, sim, same_target)


def test_reason_codes_required_when_rejecting_or_differing() -> None:
    with pytest.raises(DecisionValidationError, match="하나 이상"):
        _validate_reasons([], "", required=True)
    assert _validate_reasons([], "  ", required=False) == ([], "")
    assert _validate_reasons(["no_lab", "no_lab"], "", required=True) == (["no_lab"], "")


def test_memo_required_only_for_other() -> None:
    with pytest.raises(DecisionValidationError, match="기타"):
        _validate_reasons(["other"], "", required=True)
    assert _validate_reasons(["other"], " 실험 보고서 없음 ", required=True) == (["other"], "실험 보고서 없음")
    with pytest.raises(DecisionValidationError):
        _validate_reasons(["made_up"], "", required=True)


def test_conflict_needs_same_target_similar_syllabus_and_different_result() -> None:
    assert conflicts([item("direct", 0.95)], "none")
    assert not conflicts([item("none", 0.95)], "none")  # 판정이 같음
    assert not conflicts([item("direct", 0.40)], "none")  # 강의계획서 개편
    assert not conflicts([item("direct", 0.95, same_target=False)], "none")  # 다른 대상 과목


def test_similarity_ignores_whitespace_and_detects_revisions() -> None:
    a = "Week 1: Limits\nWeek 2: Derivatives\nWeek 3: Integrals"
    assert similarity(a, "Week 1:  Limits Week 2: Derivatives\n\nWeek 3: Integrals") >= 0.99
    assert similarity(a, "Week 1: Matrices\nWeek 2: Vector spaces\nWeek 3: Eigenvalues") < SIMILARITY_MIN
    assert similarity("", a) == 0.0
