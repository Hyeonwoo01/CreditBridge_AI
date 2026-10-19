"""보정 도구가 확정 판정 스냅숏에서 표본을 만든다 (재판정은 마지막 판정만)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Institution
from backend.services import calibration
from tests.integration.test_review_extras import approve
from tests.integration.test_workflow import professor_for


def test_samples_come_from_latest_human_decision(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    approve(client, ev, token)
    target = seeded.scalars(select(Institution).where(Institution.is_target.is_(True))).one()
    samples = calibration.samples_from_decisions(seeded, target.id)
    seeded.refresh(ev)
    mine = [s for s in samples if s.coverage == ev.coverage and s.human == ev.recommendation]
    assert mine, "승인한 판정이 AI 추천과 같은 결과의 표본으로 들어간다"
    assert all(s.human in ("direct", "elective", "none") for s in samples)
