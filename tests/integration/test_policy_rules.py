"""학칙 정책 관리와 적용 (리뷰 v3 P0-4): 초안은 쓰지 않음, 학과·입학연도별 적용, 판정 스냅샷 불변."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Decision, Department, PolicyRule, User
from backend.services import policy as policy_service
from tests.conftest import login
from tests.integration.test_workflow import professor_for


def _draft(client: TestClient, token: str, **data: str) -> PolicyRule:
    r = client.post("/admin/data/policies", data={**data, "csrf_token": token})
    assert "정책 초안을 추가했어요" in r.text, r.text[:200]
    return client.app_state_db.scalars(  # type: ignore[attr-defined]
        select(PolicyRule).where(PolicyRule.status == "draft").order_by(PolicyRule.id.desc())
    ).first()


def test_policy_lifecycle_scope_and_snapshot(client: TestClient, seeded: Session) -> None:
    client.app_state_db = seeded  # type: ignore[attr-defined]
    student = seeded.scalars(select(User).where(User.email == "jiwon@student.example")).one()
    cse = seeded.get(Department, student.department_id)
    assert cse is not None

    # 판정 때 적용한 정책이 스냅샷으로 남는다
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    client.post(f"/professor/evaluations/{ev.id}/decision", data={"action": "approve", "csrf_token": token})
    seeded.expire_all()
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    snap = dict(decision.policy_snapshot or {})
    assert snap["transfer_cap"]["params"] == {"credits": 60} and snap["min_grade"]["status"] == "resolved"

    token = login(client, "admin@msu.example")
    page = client.get("/admin/data").text
    assert "학칙 정책" in page and "C 이상 (P/PASS/S 인정)" in page

    # 초안은 적용되지 않는다
    draft = _draft(client, token, rule_type="transfer_cap", value="30", department=cse.name)
    seeded.expire_all()
    assert policy_service.for_student(seeded, student).get("transfer_cap").credits == 60
    # 승인하면 그 학과 학생에게만 적용 (학과 규칙이 대학 전체보다 우선)
    client.post(f"/admin/data/policies/{draft.id}/approve", data={"csrf_token": token})
    seeded.expire_all()
    assert policy_service.for_student(seeded, student).get("transfer_cap").credits == 30
    other = seeded.scalars(select(User).where(User.email == "senior@student.example")).one()
    other.department_id = None
    seeded.commit()
    assert policy_service.for_student(seeded, other).get("transfer_cap").credits == 60

    # 입학연도 규칙: 계정에 입학연도를 넣은 학생에게만
    cohort = _draft(client, token, rule_type="transfer_cap", value="20", department=cse.name, admission_year="2026")
    client.post(f"/admin/data/policies/{cohort.id}/approve", data={"csrf_token": token})
    form = {
        "department_id": str(cse.id),
        "source_institution_id": str(student.source_institution_id),
        "admission_year": "2026",
        "csrf_token": token,
    }
    client.post(f"/admin/accounts/{student.id}", data=form)
    seeded.expire_all()
    assert policy_service.for_student(seeded, student).get("transfer_cap").credits == 20

    # 정책이 바뀌어도 지난 판정의 스냅샷은 그대로
    seeded.refresh(decision)
    assert decision.policy_snapshot == snap

    # 같은 범위·같은 날 시작 승인 규칙은 충돌이라 승인 거절, 잘못된 값은 초안부터 거절
    twin = _draft(client, token, rule_type="transfer_cap", value="25", department=cse.name, admission_year="2026")
    r = client.post(f"/admin/data/policies/{twin.id}/approve", data={"csrf_token": token})
    assert "같은 날 시작하는 승인된 정책" in r.text
    r = client.post("/admin/data/policies", data={"rule_type": "min_grade", "value": "Z", "csrf_token": token})
    assert "A+~F" in r.text
    r = client.post("/admin/data/policies", data={"rule_type": "degree_credits", "value": "0", "csrf_token": token})
    assert "1~400" in r.text

    # 끝내면 맞는 규칙이 없어 미정: 학생 화면은 기본값 없이 안내
    for rid in [r.id for r in seeded.scalars(select(PolicyRule).where(PolicyRule.rule_type == "degree_credits"))]:
        client.post(f"/admin/data/policies/{rid}/retire", data={"csrf_token": token})
    seeded.expire_all()
    for r in seeded.scalars(select(PolicyRule).where(PolicyRule.rule_type == "degree_credits")):
        r.effective_to = r.effective_from  # 오늘까지 유효한 것을 지난 날로 (오늘부터 미정)
    seeded.commit()
    assert policy_service.for_student(seeded, student).get("degree_credits").status == "unresolved"
    login(client, "jiwon@student.example")
    page = client.get(f"/student/requests/{ev.transfer_request_id}").text
    assert "정책이 아직 정해지지 않았어요" in page

    # 학생·교수는 정책을 바꿀 수 없다
    student_token = login(client, "jiwon@student.example")
    r = client.post(
        "/admin/data/policies",
        data={"rule_type": "transfer_cap", "value": "1", "csrf_token": student_token},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303, 403)
