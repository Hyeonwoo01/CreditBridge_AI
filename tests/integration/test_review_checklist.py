"""교수 판정 화면의 분야별 확인 항목과 판정 기록 (리뷰 v3 P1-1)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Decision
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
