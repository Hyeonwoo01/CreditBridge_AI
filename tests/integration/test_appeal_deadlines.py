"""이의 신청 기한·처리 기한 (리뷰 v3 P1-5, CB-APPEAL-001)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.models import Appeal, Institution, PolicyRule
from backend.models.enums import PolicyRuleType, PolicyStatus
from backend.services import appeals as appeal_service
from backend.services import reminders
from tests.conftest import login
from tests.integration.test_review_extras import reject
from tests.integration.test_workflow import professor_for

REASON = "미분과 적분의 응용까지 15주 동안 배웠고 강의 노트와 시험지로 증명할 수 있어요."


def msu(db: Session) -> Institution:
    return db.scalars(select(Institution).where(Institution.name == "Midwest State University")).one()


def window_rules(db: Session) -> list[PolicyRule]:
    return list(
        db.scalars(
            select(PolicyRule).where(
                PolicyRule.institution_id == msu(db).id, PolicyRule.rule_type == PolicyRuleType.APPEAL_WINDOW
            )
        )
    )


def file(client: TestClient, ev_id: int) -> str:
    token = login(client, "jiwon@student.example")
    return client.post(f"/student/evaluations/{ev_id}/appeal", data={"reason": REASON, "csrf_token": token}).text


def test_deadline_is_shown_and_review_due_is_set(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)
    login(client, "jiwon@student.example")
    page = client.get(f"/student/evaluations/{ev.id}").text
    assert "data-appeal-deadline" in page and "이의 신청 기한:" in page  # 데모 학칙: 판정 뒤 30일
    assert "이의 신청 기한:" in client.get("/student/appeals").text
    assert "이의 신청을 접수했어요" in file(client, ev.id)
    appeal = seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()
    assert appeal.due_at is not None
    assert abs((appeal.due_at - appeal.created_at) - timedelta(days=14)) < timedelta(minutes=1)  # 처리 기한 14일
    login(client, "rachel@msu.example")
    assert "data-appeal-due" in client.get("/review/appeals").text


def test_appeal_after_window_is_refused(client: TestClient, seeded: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)
    later = utcnow() + timedelta(days=31)
    monkeypatch.setattr(appeal_service, "utcnow", lambda: later)
    login(client, "jiwon@student.example")
    assert "이의 신청 기간이 지났어요" in client.get(f"/student/evaluations/{ev.id}").text
    assert "이의 신청 기간이 지났어요" in file(client, ev.id)
    assert seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).first() is None
    assert "이의 신청 기한:" not in client.get("/student/appeals").text  # 신청할 수 있는 과목 목록에서도 빠짐


def test_conflicting_window_policies_hold_appeals(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)
    seeded.add(
        PolicyRule(
            institution_id=msu(seeded).id,
            rule_type=PolicyRuleType.APPEAL_WINDOW,
            parameters={"days": 7},
            effective_from=date(2020, 1, 1),
            status=PolicyStatus.APPROVED,
        )
    )
    seeded.commit()
    assert "학칙이 서로 달라" in file(client, ev.id)
    assert seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).first() is None


def test_no_window_policy_means_no_deadline(client: TestClient, seeded: Session) -> None:
    for rule in window_rules(seeded):
        rule.status = PolicyStatus.RETIRED
    seeded.commit()
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)
    login(client, "jiwon@student.example")
    assert "이의 신청 기한:" not in client.get(f"/student/evaluations/{ev.id}").text
    assert "이의 신청을 접수했어요" in file(client, ev.id)


def test_reminder_for_appeals_near_review_deadline(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)
    file(client, ev.id)
    institution = msu(seeded)
    assert reminders.plan(seeded, institution.id).appeals_due == 0
    assert reminders.plan(seeded, institution.id, now=utcnow() + timedelta(days=13, hours=1)).appeals_due == 1
