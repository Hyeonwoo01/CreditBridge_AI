from types import SimpleNamespace
from typing import Any

from backend.ai.prompts_loader import load_prompt
from backend.services.analysis import link_score
from backend.services.credits import Conversion
from backend.services.student import CourseRow, simulate


def row(
    rec: str,
    conf: str,
    source: float | None,
    target: float,
    grade: str | None = None,
    decided: str | None = None,
    accepted: float | None = None,
    allocated: float | None = None,
) -> CourseRow:
    ev: Any = SimpleNamespace(status="done", recommendation=rec, confidence=conf)
    syl: Any = SimpleNamespace(credits=source)
    dec: Any = SimpleNamespace(result=decided, accepted_credits=accepted) if decided else None
    conv = Conversion(source, "kr_credit", "us_semester", source, reason=None if source else "no credits")
    return CourseRow(
        syllabus=syl,
        evaluation=ev,
        decision=dec,
        stage=1,
        expected_done=None,
        candidate_code="X",
        candidate_credits=target,
        transcript_grade=grade,
        conversion=conv,
        allocated=allocated,
    )


def test_simulation_ranges_and_cost() -> None:
    rows = [
        row("direct", "high", 3, 4),
        row("direct", "medium", 3, 3),
        row("insufficient", "low", 3, 3),
        row("none", "medium", 2, 3),
    ]
    sim = simulate(rows, degree_credits=120, tuition_per_credit=1000)
    assert (sim.credits_low, sim.credits_high) == (3, 9)
    assert sim.source_credits == 11
    assert sim.extra_cost_low == 2000 and sim.extra_cost_high == 8000  # (11-9)*1000, (11-3)*1000
    assert sim.semesters_low == 8 and sim.semesters_high == 8


def test_failing_grade_and_decisions_override_ai() -> None:
    sim = simulate([row("direct", "high", 3, 3, grade="D"), row("direct", "high", 3, 3, decided="none")], 120, 1000)
    assert sim.credits_high == 0


def test_unknown_credits_are_left_out_not_guessed() -> None:
    # 예전에는 학점이 없으면 3.0을 넣었다: 이제는 계산에서 빼고 몇 과목을 뺐는지 알린다
    sim = simulate([row("direct", "high", None, 3), row("direct", "high", 3, 3)], 120, 1000)
    assert (sim.credits_low, sim.credits_high, sim.source_credits) == (3, 3, 3)
    assert sim.unknown == 1 and sim.unknown_reason == "no credits"


def test_professor_accepted_credits_win_over_estimates() -> None:
    # 교수가 부분 인정 2학점으로 확정했으면 대상 과목 4학점이 아니라 2학점을 쓴다
    # (확정 학점은 승인된 배분 원장의 합계로 센다)
    sim = simulate([row("direct", "high", 3, 4, decided="direct", accepted=2, allocated=2)], 120, 1000)
    assert (sim.credits_low, sim.credits_high) == (2, 2)
    # 환산할 수 없는 과목이어도 교수가 확정한 값은 쓴다
    sim = simulate([row("direct", "high", None, 4, decided="elective", accepted=3, allocated=3)], 120, 1000)
    assert (sim.credits_low, sim.credits_high, sim.unknown) == (3, 3, 0)
    # 다른 과목과 합쳐 인정돼 이 과목 판정은 없지만 원장에 배분이 있으면 그 값을 쓴다 (두 번 세지 않음)
    sim = simulate(
        [row("direct", "high", 3, 4, allocated=2), row("none", "low", 3, 4, decided="none", accepted=0)], 120, 1000
    )
    assert (sim.credits_low, sim.credits_high) == (2, 2)


def test_transcript_link_score() -> None:
    entry: Any = SimpleNamespace(code=None, title="미분적분학 I (Calculus I)")
    syllabus: Any = SimpleNamespace(course_code="MATH 101", course_title="Calculus I")
    assert link_score(entry, syllabus) > 0.5
    entry2: Any = SimpleNamespace(code="math101", title="x")
    assert link_score(entry2, syllabus) == 1.0


def test_prompts_have_versions_and_render() -> None:
    p = load_prompt("evaluation")
    assert p.version == "evaluation-v3"
    rendered = p.render(target_institution="MSU", candidates="C", credits="3", student_syllabus="S")
    assert '<student_syllabus credits="3">' in rendered and "$" not in rendered.split("<catalog_candidates>")[1][:5]
