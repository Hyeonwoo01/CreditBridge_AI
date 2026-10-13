from types import SimpleNamespace
from typing import Any

from app.ai.prompts_loader import load_prompt
from app.services.analysis import link_score
from app.services.student import CourseRow, simulate


def row(
    rec: str, conf: str, source: float, target: float, grade: str | None = None, decided: str | None = None
) -> CourseRow:
    ev: Any = SimpleNamespace(status="done", recommendation=rec, confidence=conf)
    syl: Any = SimpleNamespace(credits=source)
    dec: Any = SimpleNamespace(result=decided) if decided else None
    return CourseRow(
        syllabus=syl,
        evaluation=ev,
        decision=dec,
        stage=1,
        expected_done=None,
        candidate_code="X",
        candidate_credits=target,
        transcript_grade=grade,
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


def test_transcript_link_score() -> None:
    entry: Any = SimpleNamespace(code=None, title="미분적분학 I (Calculus I)")
    syllabus: Any = SimpleNamespace(course_code="MATH 101", course_title="Calculus I")
    assert link_score(entry, syllabus) > 0.5
    entry2: Any = SimpleNamespace(code="math101", title="x")
    assert link_score(entry2, syllabus) == 1.0


def test_prompts_have_versions_and_render() -> None:
    p = load_prompt("evaluation")
    assert p.version == "evaluation-v1"
    rendered = p.render(target_institution="MSU", candidates="C", credits="3", student_syllabus="S")
    assert '<student_syllabus credits="3">' in rendered and "$" not in rendered.split("<catalog_candidates>")[1][:5]
