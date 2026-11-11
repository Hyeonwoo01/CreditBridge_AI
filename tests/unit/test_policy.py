"""학칙 정책 엔진 (리뷰 v3 P0-4, 13.14 정책 엔진 테스트)."""

from datetime import date
from typing import Any

from backend.models import PolicyRule
from backend.services import policy

D = date(2026, 11, 11)


def rule(rid: int, rtype: str, params: dict[str, Any], **kw: Any) -> PolicyRule:
    base: dict[str, Any] = {
        "institution_id": 1,
        "status": "approved",
        "effective_from": date(2020, 1, 1),
        "effective_to": None,
        "department_id": None,
        "admission_year": None,
    }
    return PolicyRule(id=rid, rule_type=rtype, parameters=params, **{**base, **kw})


def test_more_specific_scope_wins_for_department_and_cohort() -> None:
    rules = [
        rule(1, "transfer_cap", {"credits": 60}),
        rule(2, "transfer_cap", {"credits": 45}, department_id=7),
        rule(3, "transfer_cap", {"credits": 30}, department_id=7, admission_year=2026),
    ]
    assert policy.resolve(rules, "transfer_cap", policy.Context(1), D).credits == 60
    assert policy.resolve(rules, "transfer_cap", policy.Context(1, 7), D).credits == 45
    assert policy.resolve(rules, "transfer_cap", policy.Context(1, 7, 2026), D).credits == 30
    assert policy.resolve(rules, "transfer_cap", policy.Context(1, 8, 2026), D).credits == 60


def test_drafts_retired_expired_and_other_institutions_are_ignored() -> None:
    rules = [
        rule(1, "degree_credits", {"credits": 130}, status="draft"),
        rule(2, "degree_credits", {"credits": 124}, status="retired"),
        rule(3, "degree_credits", {"credits": 128}, effective_to=date(2025, 12, 31)),
        rule(4, "degree_credits", {"credits": 126}, institution_id=2),
        rule(5, "degree_credits", {"credits": 132}, effective_from=date(2027, 1, 1)),
    ]
    res = policy.resolve(rules, "degree_credits", policy.Context(1), D)
    assert res.status == policy.UNRESOLVED and res.credits is None  # 기본값을 쓰지 않는다


def test_same_specificity_with_different_values_is_conflict() -> None:
    rules = [rule(1, "semester_load", {"credits": 15}), rule(2, "semester_load", {"credits": 18})]
    res = policy.resolve(rules, "semester_load", policy.Context(1), D)
    assert res.status == policy.CONFLICT and res.conflicting == (1, 2) and res.credits is None
    same = [rule(1, "semester_load", {"credits": 15}), rule(2, "semester_load", {"credits": 15})]
    assert policy.resolve(same, "semester_load", policy.Context(1), D).credits == 15  # 값이 같으면 충돌 아님


def test_minimum_grade_rule() -> None:
    sp = policy.for_context([rule(1, "min_grade", {"min_grade": "C", "accept_pass": True})], policy.Context(1), D)
    assert not sp.grade_failed("C") and not sp.grade_failed(" c0 ") and not sp.grade_failed("P")
    assert sp.grade_failed("C-") and sp.grade_failed("D+") and sp.grade_failed("W")  # 표에 없는 성적은 통과 아님
    strict = policy.for_context([rule(1, "min_grade", {"min_grade": "B", "accept_pass": False})], policy.Context(1), D)
    assert strict.grade_failed("C+") and strict.grade_failed("PASS") and not strict.grade_failed("B0")
    unknown = policy.for_context([], policy.Context(1), D)
    assert not unknown.grade_failed("F")  # 정책이 미정이면 빼지 않고 교수 심사로 넘긴다
    assert policy.grade_passes("F", unknown.get("min_grade")) is None


def test_snapshot_records_rule_ids_and_values() -> None:
    sp = policy.for_context([rule(9, "transfer_cap", {"credits": 60})], policy.Context(1), D)
    snap = sp.snapshot()
    assert snap["transfer_cap"] == {"status": "resolved", "rule_id": 9, "params": {"credits": 60}, "conflict": []}
    assert snap["degree_credits"]["status"] == "unresolved"
