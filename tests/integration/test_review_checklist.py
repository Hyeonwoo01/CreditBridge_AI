"""교수 판정 화면의 분야별 확인 항목과 판정 기록 (리뷰 v3 P1-1)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Decision, Syllabus
from tests.conftest import login
from tests.integration.test_workflow import professor_for


def test_checklist_shown_and_recorded_with_decision(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert 'data-checklist="math"' in page and "정리·증명" in page  # 수학과 과목 → 수학·통계 체크리스트
    r = client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={
            "action": "approve",
            "checklist": ["outcomes", "weeks", "proofs"],
            "missing_evidence": ["problem_types"],
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    assert decision.review_checklist == {
        "version": "frameworks-v1",
        "framework": "math",
        "checked": ["outcomes", "weeks", "proofs"],
        "missing_evidence": ["problem_types"],
    }
    login(client, "rachel@msu.example")
    page = client.get(f"/review/evaluations/{ev.id}").text
    assert "data-checklist-record" in page and "분야별 확인 3개" in page and "문제 유형과 수학적 난도" in page
    login(client, "jiwon@student.example")
    assert "data-checklist-record" not in client.get(f"/student/evaluations/{ev.id}").text  # 학생에게는 안 보임


def test_decision_without_checklist_still_saves(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "general_chemistry.txt")
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "실험실 시간" in page  # 화학 → 실험 과학 체크리스트
    client.post(f"/professor/evaluations/{ev.id}/decision", data={"action": "approve", "csrf_token": token})
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    assert decision.review_checklist is not None and decision.review_checklist["checked"] == []


def test_ai_prefills_checklist_hints_without_checking(client: TestClient, seeded: Session) -> None:
    """AI가 찾은 위치를 항목 옆에 보여 주지만 체크는 교수가 한다 (evaluation-v4)."""
    ev, _, _ = professor_for(client, seeded, "calculus.txt")
    seeded.refresh(ev)
    best = next(c for c in ev.coverage_json["candidates"] if c["course_id"] == ev.candidate_course_id)
    assert best["review_items"], "미리 채우기 결과가 저장돼야 해요"
    assert all(r["status"] in ("found", "not_found", "unverified") for r in best["review_items"])
    found = [r for r in best["review_items"] if r["status"] == "found"]
    syllabus = seeded.get(Syllabus, ev.syllabus_id)
    assert syllabus is not None and all(syllabus.raw_text[r["char_start"] : r["char_end"]] == r["quote"] for r in found)
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "data-review-hint=" in page and "확인한 뒤 직접 체크해 주세요" in page
    assert 'name="checklist" value="weeks" class="size-4" checked' not in page  # 미리 체크하지 않는다
