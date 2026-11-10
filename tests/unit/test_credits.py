"""학점 단위·환산 규칙 (리뷰 v3 P0-1·2): 단위나 승인된 규칙을 모르면 숫자를 만들지 않는다."""

from datetime import date
from typing import Any

from backend.models import CreditConversionRule
from backend.services import credits

D = date(2026, 11, 10)


def rule(factor: float, start: date, end: date | None = None, source: str = "ects", rid: int = 1) -> Any:
    return CreditConversionRule(
        id=rid,
        target_institution_id=1,
        source_system=source,
        target_system="us_semester",
        factor=factor,
        method="approved_table",
        effective_from=start,
        effective_to=end,
        approved_by=1,
    )


def test_same_unit_needs_no_rule_and_missing_parts_hold() -> None:
    assert credits.convert(3, "us_semester", "us_semester", [], D).value == 3
    assert credits.convert(None, "kr_credit", "us_semester", [], D).reason == credits.NO_SOURCE_CREDITS
    assert credits.convert(3, None, "us_semester", [], D).reason == credits.NO_SOURCE_UNIT
    assert credits.convert(3, "kr_credit", None, [], D).reason == credits.NO_TARGET_UNIT
    held = credits.convert(3, "kr_credit", "us_semester", [], D)
    assert held.value is None and held.reason == credits.NO_RULE
    assert credits.convert(3, "other", "other", [], D).reason == credits.NO_RULE  # '기타'끼리는 같다고 보지 않음


def test_rule_by_effective_date_and_conflict_holds() -> None:
    old = rule(0.5, date(2020, 1, 1), date(2025, 12, 31), rid=1)
    new = rule(0.6, date(2026, 1, 1), rid=2)
    c = credits.convert(6, "ects", "us_semester", [old, new], D)
    assert c.value == 3.6 and c.rule is new
    assert credits.convert(6, "ects", "us_semester", [old, new], date(2024, 5, 1)).value == 3.0
    assert credits.convert(6, "ects", "us_semester", [old], D).reason == credits.NO_RULE  # 끝난 규칙
    twin = rule(0.7, date(2026, 1, 1), rid=3)
    assert credits.convert(6, "ects", "us_semester", [new, twin], D).reason == credits.RULE_CONFLICT


def test_suggestion_basis_and_validation() -> None:
    conv = credits.convert(3, "us_semester", "us_semester", [], D)
    target: Any = type("C", (), {"credits": 4.0})()
    assert credits.suggested_credits("direct", conv, target) == 3
    assert credits.basis_for("direct", 3, target) == "partial" and credits.basis_for("direct", 4, target) == "full"
    assert (
        credits.suggested_credits("elective", conv, None) == 3 and credits.basis_for("elective", 3, None) == "elective"
    )
    assert credits.suggested_credits("none", conv, None) == 0 and credits.basis_for("none", 0, None) == "not_accepted"
    unknown = credits.convert(None, "kr_credit", "us_semester", [], D)
    assert credits.suggested_credits("direct", unknown, target) is None  # 교수가 직접 적어야 함
    assert credits.validate_accepted("direct", 3, conv, target) is None
    assert credits.validate_accepted("direct", 5, conv, target) is not None  # 대상 과목보다 많음
    big: Any = type("C", (), {"credits": 10.0})()
    assert credits.validate_accepted("direct", 3.5, conv, big) is not None  # 환산 학점보다 많음
    assert credits.validate_accepted("elective", 0, conv, None) is not None
    assert credits.validate_accepted("none", 1, conv, None) is not None
    assert credits.validate_accepted("elective", 2, unknown, None) is None  # 환산 모름: 교수 값을 받음
