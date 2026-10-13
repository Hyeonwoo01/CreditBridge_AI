"""심사 워크플로우와 권한 (TS-03~05, TC-11, TC-14~18, TC-20, NF-04~06, NF-10)."""

from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Assignment, AuditLog, CourseEvaluation, Decision, Syllabus, TransferRequest, User
from tests.conftest import login
from tests.integration.test_pipeline import latest, new_request, upload


def submitted_request(client: TestClient, db: Session, *files: str) -> str:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, db, token)
    upload(client, rid, token, *files)
    r = client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303
    return rid


def assign(client: TestClient, *evaluations: CourseEvaluation) -> None:
    token = login(client, "rachel@msu.example")
    r = client.post(
        "/review/assign",
        data={"evaluation_ids": [e.public_id for e in evaluations], "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303


def reviewer_of(db: Session, ev: CourseEvaluation) -> User:
    db.expire_all()
    a = db.scalars(
        select(Assignment).where(Assignment.course_evaluation_id == ev.id, Assignment.is_active.is_(True))
    ).one()
    user = db.get(User, a.reviewer_id)
    assert user is not None
    return user


def test_queue_tabs_and_department_assignment(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt", "data_structures.txt", "linear_algebra_sparse.txt")
    token = login(client, "rachel@msu.example")
    high = client.get("/review?tab=high").text
    assert "MATH 101" in high and "CSE 204" in high
    insufficient = client.get("/review?tab=insufficient").text
    assert "Linear Algebra" in insufficient

    calc, ds = latest(seeded, "calculus.txt"), latest(seeded, "data_structures.txt")
    client.post("/review/assign", data={"evaluation_ids": [calc.public_id, ds.public_id], "csrf_token": token})
    assert reviewer_of(seeded, calc).department == "Mathematics"
    assert reviewer_of(seeded, ds).department == "Computer Science and Engineering"


def test_away_professor_is_replaced_by_delegate(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt")
    calc = latest(seeded, "calculus.txt")
    assign(client, calc)
    first = reviewer_of(seeded, calc)
    colleague = seeded.scalars(select(User).where(User.department == "Mathematics", User.id != first.id)).one()

    token = login(client, first.email)
    r = client.post(
        "/professor/away",
        data={"days": 14, "delegate_id": colleague.public_id, "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    now = reviewer_of(seeded, calc)
    assert now.id == colleague.id
    a = seeded.scalars(
        select(Assignment).where(Assignment.course_evaluation_id == calc.id, Assignment.is_active.is_(True))
    ).one()
    assert a.reassigned_from == first.id
    login(client, "rachel@msu.example")
    assert "대리 재배정" in client.get("/review?tab=high").text


def test_professor_decision_rules_and_portal(client: TestClient, seeded: Session) -> None:
    rid = submitted_request(client, seeded, "calculus.txt")
    calc = latest(seeded, "calculus.txt")
    assign(client, calc)
    prof = reviewer_of(seeded, calc)
    token = login(client, prof.email)

    page = client.get(f"/professor/evaluations/{calc.public_id}")
    assert page.status_code == 200 and "학생 강의계획서" in page.text

    # 반려는 사유 없이 저장 불가 (TC-17)
    r = client.post(
        f"/professor/evaluations/{calc.public_id}/decision",
        data={"action": "reject", "reason": "", "csrf_token": token},
    )
    assert r.status_code == 422 and "사유" in r.text
    assert seeded.scalars(select(Decision).where(Decision.course_evaluation_id == calc.id)).first() is None

    r = client.post(
        f"/professor/evaluations/{calc.public_id}/decision",
        data={"action": "approve", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == calc.id)).one()
    assert decision.decided_by == prof.id and decision.result == "direct"
    assert decision.ai_recommendation_snapshot["recommendation"] == "direct"
    assert seeded.scalars(select(AuditLog).where(AuditLog.action == "decision.create")).first() is not None

    # 학생 포털에 확정 반영 (TC-20), 요청 상태 완료
    login(client, "jiwon@student.example")
    assert "확정 · 직접 인정" in client.get(f"/student/requests/{rid}").text
    seeded.expire_all()
    assert seeded.scalars(select(TransferRequest).where(TransferRequest.public_id == rid)).one().status == "decided"

    # 확정 결과 내보내기 (NF-10)
    login(client, "rachel@msu.example")
    csv = client.get("/review/export.csv").text
    assert "MATH 101" in csv and "MATH 1151" in csv and "direct" in csv


def test_consistency_alert_for_conflicting_past_decision(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "linear_algebra_detailed.txt")
    ev = latest(seeded, "linear_algebra_detailed.txt")
    assign(client, ev)
    prof = reviewer_of(seeded, ev)
    token = login(client, prof.email)

    page = client.get(f"/professor/evaluations/{ev.public_id}").text
    assert "같은 과목의 과거 판정 1건" in page  # 작년 직접 인정 이력

    data = {"action": "reject", "reason": "고유값 단원이 부족함", "csrf_token": token}
    r = client.post(f"/professor/evaluations/{ev.public_id}/decision", data=data)
    assert r.status_code == 409 and "과거 판정" in r.text
    assert seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).first() is None

    r = client.post(
        f"/professor/evaluations/{ev.public_id}/decision",
        data={**data, "acknowledge_conflict": "true"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    assert decision.conflict_acknowledged and decision.result == "none"

    report = client.get(f"/evaluations/{ev.public_id}/report").text
    assert "고유값 단원이 부족함" in report and "판정 당시 AI 추천" in report and prof.name in report


def test_no_decision_without_assigned_professor(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt")
    calc = latest(seeded, "calculus.txt")
    body = {"evaluation_id": calc.public_id, "action": "approve"}

    # 로그인 없이 API 호출 → 거부 (TC-16)
    client.cookies.clear()
    assert client.post("/api/decisions", json=body).status_code == 401
    # 학생·심사관도 확정 불가
    for email in ("jiwon@student.example", "rachel@msu.example"):
        token = login(client, email)
        r = client.post("/api/decisions", json=body, headers={"X-CSRF-Token": token})
        assert r.status_code == 403
    # 배정되지 않은 교수도 불가
    assign(client, calc)
    other = seeded.scalars(select(User).where(User.department == "Physics")).first()
    assert other is not None
    token = login(client, other.email)
    assert client.post("/api/decisions", json=body, headers={"X-CSRF-Token": token}).status_code == 403
    assert seeded.scalars(select(Decision).where(Decision.course_evaluation_id == calc.id)).first() is None

    prof = reviewer_of(seeded, calc)
    token = login(client, prof.email)
    r = client.post("/api/decisions", json=body, headers={"X-CSRF-Token": token})
    assert r.status_code == 201 and r.json()["decided_by"] == prof.public_id


def test_role_based_access(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt")
    calc = latest(seeded, "calculus.txt")

    # 다른 학생은 볼 수 없다
    login(client, "senior@student.example")
    assert client.get(f"/student/evaluations/{calc.public_id}").status_code == 403
    assert client.get(f"/api/evaluations/{calc.public_id}").status_code == 403
    # 배정 전 교수는 볼 수 없다
    login(client, "dkim@msu.example")
    assert client.get(f"/professor/evaluations/{calc.public_id}").status_code == 403
    # 학생은 심사 큐에 들어갈 수 없다
    login(client, "jiwon@student.example")
    assert client.get("/review").status_code == 403
    # 관리자는 판정 원문 대신 감사 로그만
    login(client, "admin@msu.example")
    assert client.get(f"/evaluations/{calc.public_id}/report").status_code == 403
    assert client.get("/admin/audit").status_code == 200


def test_csrf_required(client: TestClient, seeded: Session) -> None:
    login(client, "jiwon@student.example")
    r = client.post(
        "/student/requests", data={"source_institution_id": 1, "target_institution_id": 2, "csrf_token": "bad"}
    )
    assert r.status_code == 403


def test_privacy_delete_removes_files_and_text(client: TestClient, seeded: Session, fake_storage) -> None:  # type: ignore[no-untyped-def]
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")
    assert fake_storage.objects
    client.post(f"/student/requests/{rid}/delete-documents", data={"csrf_token": token})
    assert not fake_storage.objects
    seeded.expire_all()
    syllabus = seeded.scalars(select(Syllabus).where(Syllabus.original_filename == "calculus.txt")).one()
    assert syllabus.raw_text == "" and syllabus.status == "deleted"


def test_decisions_table_has_no_update_path(seeded: Session) -> None:
    """decisions·audit_logs 저장소 코드에는 UPDATE/DELETE가 없다 (추가 전용)."""
    import inspect

    from app.repositories import audit, decisions

    for module in (audit, decisions):
        source = inspect.getsource(module)
        assert "update(" not in source and "delete(" not in source and ".delete" not in source
    # DB 권한 예시: 운영 계정에는 이 두 테이블의 UPDATE/DELETE 권한을 주지 않는다 (docs 참고)
    assert seeded.execute(text("SELECT COUNT(*) FROM decisions")).scalar() == 1  # 시드 이력
