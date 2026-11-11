"""AI 성능 모니터링·출시 기준·추천 범위 제한 (리뷰 v3 P1-7)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import Decision, Institution
from backend.services import ai_monitoring
from tests.conftest import login
from tests.integration.test_review_extras import approve, reject
from tests.integration.test_workflow import professor_for


def msu_id(db: Session) -> int:
    return db.scalars(select(Institution.id).where(Institution.name == "Midwest State University")).one()


def test_quality_compares_first_decisions_with_ai_snapshot(
    client: TestClient, seeded: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    ev1, _, t1 = professor_for(client, seeded, "calculus.txt")
    approve(client, ev1, t1)  # AI 추천과 같음
    ev2, _, t2 = professor_for(client, seeded, "data_structures.txt")
    reject(client, ev2, t2)  # AI 추천과 다름
    rows = ai_monitoring.quality(seeded, msu_id(seeded))
    ours = [q for q in rows if q.model == "fake-claude"]
    assert len(ours) == 1
    q = ours[0]
    assert q.decisions == 2 and q.compared == 2 and q.agreed == 1 and q.agreement == 0.5
    assert q.reasons  # 반려 사유가 모인다
    assert q.gate == ai_monitoring.SMALL  # 표본 20건 미만
    monkeypatch.setattr(get_settings(), "ai_gate_min_samples", 2)
    assert q.gate == ai_monitoring.FAIL  # 일치율 50% < 70%
    login(client, "admin@msu.example")
    page = client.get("/admin/stats").text
    assert "AI 성능 모니터링" in page and 'data-gate="fail"' in page and "data-ai-gate-alert" in page


def test_evidence_only_mode_hides_grades_and_blocks_approve(
    client: TestClient, seeded: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    monkeypatch.setattr(get_settings(), "ai_recommendation_mode", "evidence_only")
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "data-ai-limited-note" in page and "AI 등급 숨김" in page
    assert 'value="approve"' not in page  # 'AI 추천대로 승인' 없음
    r = client.post(f"/professor/evaluations/{ev.id}/decision", data={"action": "approve", "csrf_token": token})
    assert r.status_code == 422 and "직접 골라" in r.text
    assert seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).first() is None
    r = client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={
            "action": "modify",
            "result": "direct",
            "target_course_id": ev.candidate_course_id,
            "reason_codes": ["other"],
            "reason_memo": "근거 직접 확인",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert r.status_code == 303  # 결과를 직접 고르면 저장된다
    login(client, "jiwon@student.example")
    page = client.get(f"/student/evaluations/{ev.id}").text
    assert "data-ai-limited-note" in page
    login(client, "admin@msu.example")
    assert "AI_RECOMMENDATION_MODE=evidence_only" in client.get("/admin/stats").text


def test_simulation_skips_ai_estimates_when_limited() -> None:
    from types import SimpleNamespace
    from typing import Any

    from backend.services.credits import Conversion
    from backend.services.student import CourseRow, simulate

    ev: Any = SimpleNamespace(status="done", recommendation="direct", confidence="high")
    row = CourseRow(
        syllabus=SimpleNamespace(credits=3),  # type: ignore[arg-type]
        evaluation=ev,
        decision=None,
        stage=1,
        expected_done=None,
        candidate_code="X",
        candidate_credits=3,
        transcript_grade=None,
        conversion=Conversion(3, "kr_credit", "us_semester", 3),
    )
    assert simulate([row], 120, 1000, 15).credits_high == 3
    assert simulate([row], 120, 1000, 15, ai_estimates=False).credits_high == 0
