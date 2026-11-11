"""학점 계산 회귀 (리뷰 v3 P0-8). 기대값은 tests/fixtures/regression/credit_cases.json 한 곳에 표로 둔다."""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from backend.services import credits
from backend.services.student import CourseRow, cap_simulation, simulate

CASES = json.loads((Path(__file__).resolve().parents[1] / "fixtures/regression/credit_cases.json").read_text("utf-8"))


def ids(section: str) -> list[str]:
    return [c["id"] for c in CASES[section]]


def rule(spec: dict[str, Any], source: str, target: str) -> Any:
    return SimpleNamespace(
        id=hash(json.dumps(spec)) % 1000,
        source_system=source,
        target_system=target,
        factor=spec["factor"],
        effective_from=date.fromisoformat(spec["from"]),
        effective_to=date.fromisoformat(spec["to"]) if spec["to"] else None,
    )


@pytest.mark.parametrize("case", CASES["convert"], ids=ids("convert"))
def test_convert(case: dict[str, Any]) -> None:
    rules = [rule(r, case["from"], case["to"]) for r in case["rules"]]
    result = credits.convert(case["source"], case["from"], case["to"], rules, date.fromisoformat(case["on"]))
    assert result.value == case["value"]
    assert result.reason == (getattr(credits, case["reason"]) if case["reason"] else None)


def conversion(value: float | None) -> credits.Conversion:
    return credits.Conversion(value, "kr_credit", "us_semester", value)


def course(credit: float | None) -> Any:
    return SimpleNamespace(credits=credit) if credit is not None else None


@pytest.mark.parametrize("case", CASES["suggest"], ids=ids("suggest"))
def test_suggested(case: dict[str, Any]) -> None:
    assert (
        credits.suggested_credits(case["result"], conversion(case["value"]), course(case["target"])) == case["expect"]
    )


@pytest.mark.parametrize("case", CASES["basis"], ids=ids("basis"))
def test_basis(case: dict[str, Any]) -> None:
    assert credits.basis_for(case["result"], case["accepted"], course(case["target"])) == case["expect"]


@pytest.mark.parametrize("case", CASES["validate"], ids=ids("validate"))
def test_validate(case: dict[str, Any]) -> None:
    problem = credits.validate_accepted(
        case["result"], case["accepted"], conversion(case["value"]), course(case["target"])
    )
    assert (problem[0] if problem else None) == case["problem"]


@pytest.mark.parametrize("case", CASES["split"], ids=ids("split"))
def test_split(case: dict[str, Any]) -> None:
    shares = credits.split_credits(case["accepted"], case["remaining"])
    assert shares == case["expect"]
    assert round(sum(shares), 2) == case["accepted"]  # 나눈 합은 언제나 인정 학점과 같다


def row(spec: dict[str, Any]) -> CourseRow:
    source = spec["source"]
    decided = spec.get("decided")
    return CourseRow(
        syllabus=SimpleNamespace(credits=source),  # type: ignore[arg-type]
        evaluation=SimpleNamespace(status="done", recommendation=spec["rec"], confidence=spec["conf"]),  # type: ignore[arg-type]
        decision=SimpleNamespace(result=decided, accepted_credits=spec.get("accepted")) if decided else None,  # type: ignore[arg-type]
        stage=1,
        expected_done=None,
        candidate_code="X",
        candidate_credits=spec["target"],
        transcript_grade=spec.get("grade"),
        failed_grade=spec.get("grade") in {"C-", "D+", "D", "F"},
        conversion=credits.Conversion(source, "kr_credit", "us_semester", source, reason=None if source else "x"),
        allocated=spec.get("allocated"),
    )


@pytest.mark.parametrize("case", CASES["simulate"], ids=ids("simulate"))
def test_simulate(case: dict[str, Any]) -> None:
    sim = simulate([row(r) for r in case["rows"]], case["degree"], case["tuition"], case["per_semester"])
    sim = cap_simulation(sim, case["cap"])
    want = case["expect"]
    got = {
        "low": sim.credits_low,
        "high": sim.credits_high,
        "source": sim.source_credits,
        "unknown": sim.unknown,
        "sem_low": sim.semesters_low,
        "sem_high": sim.semesters_high,
        "cost_low": sim.extra_cost_low,
        "cost_high": sim.extra_cost_high,
    }
    assert {k: got[k] for k in want} == want
