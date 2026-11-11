"""학사정보시스템 반영 확인·중복 방지·재전송·대사 (리뷰 v3 P1-4, CB-REG-002·003)."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import SisAckRequest, SisSync
from tests.conftest import login
from tests.integration.test_review_extras import approve, reject
from tests.integration.test_workflow import professor_for


def issue(client: TestClient) -> dict[str, str]:
    token = login(client, "admin@msu.example")
    page = client.post("/admin/sis", data={"action": "issue", "csrf_token": token}).text
    secret = "cbsis_" + page.split("cbsis_", 1)[1].split("<", 1)[0].strip()
    client.cookies.clear()
    return {"Authorization": f"Bearer {secret}"}


def decisions(client: TestClient, auth: dict[str, str], status: str = "all") -> list[dict[str, object]]:
    r = client.get(f"/api/v1/sis/decisions?status={status}", headers=auth)
    assert r.status_code == 200, r.text
    return r.json()["decisions"]


def ack(client: TestClient, auth: dict[str, str], key: str, results: list[dict[str, object]]):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/sis/acks", json={"results": results}, headers={**auth, "Idempotency-Key": key})


def ours(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """이 테스트가 만든 판정만 (데모에는 작년 판정 하나가 들어 있다)."""
    return [r for r in rows if r["source_course"] in ("MATH 101", "CSE 204")]


def two_decisions(client: TestClient, db: Session) -> None:
    ev, _, token = professor_for(client, db, "calculus.txt")
    approve(client, ev, token)
    ev2, _, token2 = professor_for(client, db, "data_structures.txt")
    reject(client, ev2, token2)


def test_rows_carry_stable_idempotency_key_and_status(client: TestClient, seeded: Session) -> None:
    two_decisions(client, seeded)
    auth = issue(client)
    rows = ours(decisions(client, auth))
    assert len(rows) == 2
    for row in rows:
        assert row["idempotency_key"] == f"cb-decision-{row['decision_id']}"
        assert row["sync_status"] == "pending" and row["external_reference_id"] == ""
    assert ours(decisions(client, auth)) == rows  # 다시 가져가도 같은 키 (SIS가 중복 반영을 막는 기준)
    assert client.get("/api/v1/sis/decisions?status=bogus", headers=auth).status_code == 422


def test_ack_is_idempotent_and_partial_failure_is_resent(client: TestClient, seeded: Session) -> None:
    two_decisions(client, seeded)
    auth = issue(client)
    a, b = (int(r["decision_id"]) for r in ours(decisions(client, auth)))  # type: ignore[call-overload]
    results = [
        {"decision_id": a, "status": "applied", "external_reference_id": "SIS-001"},
        {"decision_id": b, "status": "failed", "error": "unknown course code"},
    ]
    assert ack(client, auth, "", results).status_code == 422  # 키 없이는 받지 않음
    first = ack(client, auth, "batch-1", results)
    assert first.status_code == 200
    assert [r["outcome"] for r in first.json()["results"]] == ["recorded", "recorded"]
    again = ack(client, auth, "batch-1", results)  # 네트워크 재시도: 같은 키·같은 내용
    assert again.json() == first.json() and again.headers.get("Idempotent-Replay") == "true"
    assert seeded.scalar(select(func.count()).select_from(SisAckRequest)) == 1
    seeded.expire_all()
    assert seeded.scalars(select(SisSync).where(SisSync.decision_id == b)).one().attempts == 1  # 두 번 세지 않음
    assert ack(client, auth, "batch-1", results[:1]).status_code == 409  # 같은 키에 다른 내용

    # 실패한 판정만 다시 가져간다 (CB-REG-003)
    assert b in [r["decision_id"] for r in decisions(client, auth, "unsent")]
    assert a not in [r["decision_id"] for r in decisions(client, auth, "unsent")]
    assert [r["decision_id"] for r in decisions(client, auth, "applied")] == [a]

    # 이미 반영된 판정: 같은 번호면 중복, 다른 번호면 덮어쓰지 않고 불일치로 알림
    r = ack(
        client,
        auth,
        "batch-2",
        [
            {"decision_id": a, "status": "applied", "external_reference_id": "SIS-001"},
            {"decision_id": a, "status": "applied", "external_reference_id": "SIS-999"},
            {"decision_id": 999999, "status": "applied"},
            {"decision_id": b, "status": "maybe"},
        ],
    ).json()
    assert [x["outcome"] for x in r["results"]] == ["duplicate", "conflict", "rejected", "rejected"]
    seeded.expire_all()
    assert seeded.scalars(select(SisSync).where(SisSync.decision_id == a)).one().external_reference_id == "SIS-001"


def test_admin_reconciliation_and_retry(client: TestClient, seeded: Session) -> None:
    two_decisions(client, seeded)
    auth = issue(client)
    a, b = (int(r["decision_id"]) for r in ours(decisions(client, auth)))  # type: ignore[call-overload]
    ack(
        client,
        auth,
        "k1",
        [
            {"decision_id": a, "status": "applied", "external_reference_id": "SIS-1"},
            {"decision_id": b, "status": "failed", "error": "course code not mapped"},
        ],
    )
    token = login(client, "admin@msu.example")
    page = client.get("/admin/sis").text
    assert (
        'data-recon="1">3<' in page and 'data-recon="2">1<' in page and 'data-recon="4">1<' in page
    )  # 전체 3(데모 판정 포함)·반영 1·실패 1
    assert "course code not mapped" in page
    r = client.post("/admin/sis/retry", data={"decision_ids": [b], "csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303
    seeded.expire_all()
    assert seeded.scalars(select(SisSync).where(SisSync.decision_id == b)).one().status == "pending"
    assert 'data-recon="3">2<' in client.get("/admin/sis").text  # 대기 2 (데모 판정 + 다시 보낼 판정)
    # 다른 기관 토큰·학생은 대사·재전송을 할 수 없다
    login(client, "rachel@msu.example")
    assert client.post("/admin/sis/retry", data={"decision_ids": [b], "csrf_token": token}).status_code == 403


def test_redecision_after_apply_needs_resend(client: TestClient, seeded: Session) -> None:
    from backend.models import Appeal, User
    from backend.services import sis as sis_service

    ev, prof, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)
    auth = issue(client)
    old = next(int(r["decision_id"]) for r in ours(decisions(client, auth)))  # type: ignore[call-overload]
    ack(client, auth, "k1", [{"decision_id": old, "status": "applied", "external_reference_id": "SIS-7"}])
    # 학생 이의 신청 → 심사관이 다른 교수에게 재판정 배정 → 재판정
    student = login(client, "jiwon@student.example")
    client.post(
        f"/student/evaluations/{ev.id}/appeal",
        data={"reason": "미분과 적분의 응용까지 15주 동안 배웠고 강의 노트로 증명할 수 있어요.", "csrf_token": student},
    )
    appeal = seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()
    other = seeded.scalars(
        select(User).where(User.department_id == prof.department_id, User.role == "professor", User.id != prof.id)
    ).first()
    assert other is not None
    evaluator = login(client, "rachel@msu.example")
    client.post(
        f"/review/appeals/{appeal.id}", data={"action": "accept", "reviewer_id": other.id, "csrf_token": evaluator}
    )
    approve(client, ev, login(client, other.email))

    admin = seeded.scalars(select(User).where(User.email == "admin@msu.example")).one()
    seeded.expire_all()
    recon = sis_service.reconciliation(seeded, admin)
    assert [(s.decision_id, d.id != old) for s, d in recon.resend] == [(old, True)]
    assert "새 판정을 다시 반영해야" in (login(client, "admin@msu.example") and client.get("/admin/sis").text)
    client.cookies.clear()
    # 대체된 옛 판정에 대한 결과는 기록하지 않고 대체 사실을 알린다
    r = ack(client, auth, "k2", [{"decision_id": old, "status": "applied", "external_reference_id": "SIS-7"}]).json()
    assert r["results"][0]["outcome"] == "superseded"
