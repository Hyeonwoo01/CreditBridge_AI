"""학점 단위·환산 규칙과 교수가 확정하는 인정 학점 (리뷰 v3 P0-1·2)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AuditLog, Course, CreditConversionRule, Decision, Institution
from tests.conftest import login
from tests.integration.test_workflow import professor_for


def _decision(db: Session, evaluation_id: int) -> Decision:
    db.expire_all()
    return db.scalars(select(Decision).where(Decision.course_evaluation_id == evaluation_id)).one()


def test_decision_stores_accepted_credits_from_approved_rule(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "인정 학점" in page and "환산 규칙 #" in page and "한국 학점" in page

    # 대상 과목 학점보다 많이 인정할 수 없다
    url = f"/professor/evaluations/{ev.id}/decision"
    r = client.post(url, data={"action": "approve", "accepted_credits": "9", "csrf_token": token})
    assert r.status_code == 422 and "많이 인정할 수 없어요" in r.text
    r = client.post(url, data={"action": "approve", "accepted_credits": "abc", "csrf_token": token})
    assert r.status_code == 422 and "숫자로" in r.text

    client.post(url, data={"action": "approve", "csrf_token": token})  # 비우면 규칙으로 계산
    d = _decision(seeded, ev.id)
    target = seeded.get(Course, d.target_course_id)
    assert target is not None
    assert d.source_credits == 3 and d.source_credit_unit == "kr_credit" and d.credit_unit == "us_semester"
    assert d.accepted_credits == min(3, target.credits) and d.conversion_rule_id is not None
    assert d.credit_basis == ("full" if target.credits <= 3 else "partial")
    log = seeded.scalars(select(AuditLog).where(AuditLog.action == "decision.create")).first()
    assert log is not None and log.payload_json["accepted_credits"] == d.accepted_credits

    # 학생 화면·리포트·내보내기가 같은 값을 쓴다
    login(client, "jiwon@student.example")
    assert f"인정 {d.accepted_credits:g}학점" in client.get(f"/student/evaluations/{ev.id}").text
    login(client, "rachel@msu.example")
    csv = client.get("/review/export.csv").text
    assert "accepted_credits,credit_unit,credit_basis" in csv and "us_semester" in csv


def test_without_rule_professor_must_enter_credits_and_student_estimate_holds(
    client: TestClient, seeded: Session
) -> None:
    # 관리자가 규칙을 끝내면 환산을 보류한다
    token = login(client, "admin@msu.example")
    rule = seeded.scalars(select(CreditConversionRule)).one()
    client.post(f"/admin/data/conversion-rules/{rule.id}/end", data={"csrf_token": token})
    seeded.expire_all()
    assert seeded.get(CreditConversionRule, rule.id).effective_to is not None  # type: ignore[union-attr]
    # 끝난 날 이후의 날짜로 넣어 오늘부터 보류되게 한다 (오늘까지는 유효)
    seeded.get(CreditConversionRule, rule.id).effective_to = rule.effective_from  # type: ignore[union-attr]
    seeded.commit()

    ev, prof, _ = professor_for(client, seeded, "data_structures.txt")
    login(client, "jiwon@student.example")
    assert "예상치에서 뺐어요" in client.get("/student").text  # 판정 전 과목은 환산할 수 없어 계산에서 빠짐
    token = login(client, prof.email)
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "자동 계산할 수 없어요" in page and "승인된 환산 규칙이 없어요" in page
    url = f"/professor/evaluations/{ev.id}/decision"
    r = client.post(url, data={"action": "approve", "csrf_token": token})
    assert r.status_code == 422 and "직접 적어 주세요" in r.text
    client.post(url, data={"action": "approve", "accepted_credits": "2", "csrf_token": token})
    d = _decision(seeded, ev.id)
    assert d.accepted_credits == 2 and d.conversion_rule_id is None and d.source_credits == 3
    login(client, "jiwon@student.example")
    assert "예상치에서 뺐어요" not in client.get("/student").text  # 교수가 확정한 값은 그대로 씀


def test_admin_sets_units_and_rules(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    page = client.get("/admin/data").text
    assert "학점 단위와 환산 규칙" in page and "1 한국 학점 = 1.0 미국 학기제 학점" in page
    msu = seeded.scalars(select(Institution).where(Institution.is_target.is_(True))).first()
    hankuk = seeded.scalars(select(Institution).where(Institution.country == "KR")).first()
    assert msu is not None and hankuk is not None

    r = client.post(
        "/admin/data/credit-systems",
        data={
            "institution_ids": [str(msu.id), str(hankuk.id)],
            "systems": ["us_semester", "ects"],
            "csrf_token": token,
        },
    )
    assert "1곳 바뀜" in r.text
    seeded.expire_all()
    assert seeded.get(Institution, hankuk.id).credit_system == "ects"  # type: ignore[union-attr]
    r = client.post(
        "/admin/data/credit-systems", data={"institution_ids": [str(msu.id)], "systems": ["bogus"], "csrf_token": token}
    )
    assert "목록에서 골라" in r.text

    data = {"source_system": "ects", "factor": "0.5", "method": "approved_table", "effective_from": "2026-01-01"}
    r = client.post("/admin/data/conversion-rules", data={**data, "csrf_token": token})
    assert "환산 규칙을 추가했어요" in r.text
    r = client.post("/admin/data/conversion-rules", data={**data, "csrf_token": token})
    assert "같은 날 시작하는 환산 규칙" in r.text  # 정책 충돌은 만들지 않는다
    r = client.post(
        "/admin/data/conversion-rules", data={**data, "factor": "9", "effective_from": "", "csrf_token": token}
    )
    assert "이하로 적어" in r.text
    assert client.post("/admin/data/conversion-rules", data=data).status_code == 403  # CSRF

    # 학생·교수는 바꿀 수 없다
    student_token = login(client, "jiwon@student.example")
    r = client.post("/admin/data/conversion-rules", data={**data, "csrf_token": student_token}, follow_redirects=False)
    assert r.status_code in (302, 303, 403)
    seeded.expire_all()
    assert len(seeded.scalars(select(CreditConversionRule)).all()) == 2
