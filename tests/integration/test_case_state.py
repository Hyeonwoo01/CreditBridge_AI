"""심사 건 상태 머신과 동시 수정 방지 (리뷰 v3 P0-6)."""

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.models import CourseEvaluation, Decision, User
from backend.repositories import evaluations as evaluation_repo
from backend.services import case_state
from tests.conftest import login
from tests.integration.test_workflow import professor_for


def case_token(page: str) -> str:
    found = re.search(r'name="case_token" value="([0-9a-f]+)"', page)
    assert found, "화면에 상태 토큰이 없어요"
    return found.group(1)


def decisions_of(db: Session, ev: CourseEvaluation) -> list[Decision]:
    db.expire_all()
    return list(db.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).all())


def test_stale_token_is_rejected_without_saving(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "calculus.txt")
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert 'data-case-state="under_review"' in page and "교수 심사 중" in page
    opened = case_token(page)

    # 교수가 화면을 연 뒤 심사관이 보완 자료를 요청했다 → 토큰이 바뀐다
    evaluator = login(client, "rachel@msu.example")
    review_page = client.get(f"/review/evaluations/{ev.id}").text
    r = client.post(
        f"/review/evaluations/{ev.id}/materials",
        data={"items": ["시험지 또는 과제 샘플"], "case_token": case_token(review_page), "csrf_token": evaluator},
    )
    assert "보완 자료를 요청했어요" in r.text

    token = login(client, prof.email)
    r = client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={"action": "approve", "case_token": opened, "csrf_token": token},
    )
    assert r.status_code == 409 and "다른 사람이 이 심사 건을 바꿨어요" in r.text
    assert decisions_of(seeded, ev) == []  # 덮어쓰지도, 새로 저장하지도 않는다

    # 새로 고친 화면의 토큰으로는 저장된다 (보완 자료 대기 중에도 판정할 수 있음)
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert 'data-case-state="needs_information"' in page
    r = client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={"action": "approve", "case_token": case_token(page), "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert len(decisions_of(seeded, ev)) == 1
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert 'data-case-state="decided"' in page


def test_double_submit_saves_one_decision(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    opened = case_token(client.get(f"/professor/evaluations/{ev.id}").text)
    data = {"action": "approve", "case_token": opened, "csrf_token": token}
    first = client.post(f"/professor/evaluations/{ev.id}/decision", data=data, follow_redirects=False)
    second = client.post(f"/professor/evaluations/{ev.id}/decision", data=data, follow_redirects=False)
    assert first.status_code == 303 and second.status_code in (409, 422)
    assert len(decisions_of(seeded, ev)) == 1


def test_superseded_evaluation_cannot_be_decided(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    stored = seeded.get(CourseEvaluation, ev.id)
    assert stored is not None
    stored.is_latest = False  # 다시 분석한 최신 결과가 따로 생긴 상황
    seeded.commit()
    r = client.post(f"/professor/evaluations/{ev.id}/decision", data={"action": "approve", "csrf_token": token})
    assert r.status_code == 422 and "최신 결과" in r.text
    assert decisions_of(seeded, ev) == []


def test_stale_token_on_evaluator_forms(client: TestClient, seeded: Session) -> None:
    ev, prof, _ = professor_for(client, seeded, "calculus.txt")
    token = login(client, "rachel@msu.example")
    opened = case_token(client.get(f"/review/evaluations/{ev.id}").text)
    client.post(
        f"/review/evaluations/{ev.id}/materials",
        data={"items": ["강의 노트"], "case_token": opened, "csrf_token": token},
    )
    # 같은(이제 낡은) 토큰으로 증거 상태·배정을 바꾸려 하면 저장하지 않는다
    r = client.post(
        f"/review/evaluations/{ev.id}/evidence-status",
        data={
            "source_kind": "student_uploaded",
            "authenticity": "verified",
            "verification_method": "포털 대조",
            "case_token": opened,
            "csrf_token": token,
        },
    )
    assert "다른 사람이 이 심사 건을 바꿨어요" in r.text
    other = seeded.scalars(
        select(User.id).where(
            User.role == "professor", User.is_active, User.institution_id == prof.institution_id, User.id != prof.id
        )
    ).first()
    r = client.post(
        f"/review/evaluations/{ev.id}/assign",
        data={"reviewer_id": other, "case_token": opened, "csrf_token": token},
    )
    assert "다른 사람이 이 심사 건을 바꿨어요" in r.text
    assert evaluation_repo.active_assignment(seeded, ev.id).reviewer_id == prof.id  # type: ignore[union-attr]


def test_api_returns_token_and_rejects_stale(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    body = client.get(f"/api/v1/evaluations/{ev.id}").json()
    assert body["case_state"] == "under_review" and body["case_token"]
    headers = {"X-CSRF-Token": token}
    r = client.post(
        "/api/v1/decisions",
        json={"evaluation_id": ev.id, "action": "approve", "case_token": "0000000000000000"},
        headers=headers,
    )
    assert r.status_code == 409
    r = client.post(
        "/api/v1/decisions",
        json={"evaluation_id": ev.id, "action": "approve", "case_token": body["case_token"]},
        headers=headers,
    )
    assert r.status_code == 201
    assert len(decisions_of(seeded, ev)) == 1


def test_row_lock_blocks_concurrent_writer(client: TestClient, seeded: Session) -> None:
    """한 트랜잭션이 심사 건을 잠그고 있으면 다른 트랜잭션은 기다린다 (SELECT … FOR UPDATE)."""
    from backend.db.session import SessionLocal

    ev, _, _ = professor_for(client, seeded, "calculus.txt")
    holder = SessionLocal()
    waiter = SessionLocal()
    try:
        assert case_state.ensure(holder, ev.id, "decide") is not None
        waiter.execute(text("SET LOCAL lock_timeout = '200ms'"))
        with pytest.raises(OperationalError):
            evaluation_repo.lock(waiter, ev.id)
        waiter.rollback()
        holder.rollback()  # 잠금이 풀리면 바로 얻는다
        assert evaluation_repo.lock(waiter, ev.id) is not None
    finally:
        holder.close()
        waiter.rollback()
        waiter.close()
