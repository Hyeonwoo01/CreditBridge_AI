"""결정 스냅샷 재현 회귀 (리뷰 v3 P0-8, CB-TEMP-011·CB-CREDIT-003).

교수 판정을 저장한 뒤 카탈로그(대상 과목 코드·이름·학점), 학칙 정책, 학점 환산 규칙, 증거 상태가 모두 바뀌어도
판정 행·리포트·학생 화면·SIS 내보내기가 판정 때 값을 그대로 보여 줘야 한다.
"""

import csv
import io
from datetime import date, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.models import Course, CreditConversionRule, Decision, Institution, PolicyRule
from backend.models.enums import PolicyRuleType, PolicyStatus
from backend.services.scoring import RULES_VERSION
from tests.conftest import login
from tests.integration.test_workflow import professor_for


def row_of(decision: Decision) -> dict[str, Any]:
    return {c.key: getattr(decision, c.key) for c in inspect(Decision).mapper.column_attrs}


def export_row(client: TestClient, decision_id: int) -> dict[str, str]:
    rows = list(csv.DictReader(io.StringIO(client.get("/review/export.csv").text)))
    return next(r for r in rows if r["decision_id"] == str(decision_id))


def test_decision_is_reproducible_after_catalog_policy_and_rule_changes(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "calculus.txt")
    assert ev.candidate_course_id is not None
    r = client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={
            "action": "modify",
            "result": "direct",
            "target_course_id": ev.candidate_course_id,
            "accepted_credits": "2",
            "reason_codes": ["weeks_insufficient"],
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    before = row_of(decision)
    course = seeded.get(Course, ev.candidate_course_id)
    assert course is not None
    old_code, old_title, old_credits = course.code, course.title, float(course.credits)

    # 판정 때 값이 모두 남았는가 (스냅샷 모양 회귀)
    assert before["accepted_credits"] == 2 and before["credit_basis"] == "partial"  # CB-CREDIT-003
    snap = before["course_snapshot"]
    assert snap["target"] == {
        "id": course.id,
        "code": old_code,
        "title": old_title,
        "credits": old_credits,
        "department": course.department_name,
    }
    assert snap["sources"][0]["syllabus_id"] == ev.syllabus_id and snap["sources"][0]["content_hash"]
    assert snap["conversion"]["rule_id"] == before["conversion_rule_id"] and snap["conversion"]["factor"] == 1.0
    assert snap["rules_version"] == RULES_VERSION
    assert set(before["policy_snapshot"]) == set(PolicyRuleType)
    assert before["evidence_snapshot"]["authenticity"] == "unverified"
    assert before["ai_recommendation_snapshot"]["candidate_course"] == old_code
    login(client, "rachel@msu.example")
    exported = export_row(client, decision.id)
    report = client.get(f"/evaluations/{ev.id}/report").text
    assert old_code in report and "인정 2학점" in report

    # 세상이 바뀐다: 카탈로그, 학칙 정책, 환산 규칙, 증거 상태
    course.code, course.title, course.credits = "MATH 9999", "Renamed Calculus", 5
    msu = seeded.scalars(select(Institution).where(Institution.name == "Midwest State University")).one()
    for rule in seeded.scalars(select(PolicyRule).where(PolicyRule.institution_id == msu.id)):
        rule.status = PolicyStatus.RETIRED
        seeded.add(
            PolicyRule(
                institution_id=msu.id,
                rule_type=rule.rule_type,
                parameters={**rule.parameters},
                effective_from=date.today(),
                status=PolicyStatus.APPROVED,
                approved_at=utcnow(),
            )
        )
    for conv in seeded.scalars(
        select(CreditConversionRule).where(CreditConversionRule.target_institution_id == msu.id)
    ):
        conv.effective_to = date.today() - timedelta(days=1)
        seeded.add(
            CreditConversionRule(
                target_institution_id=msu.id,
                source_system=conv.source_system,
                target_system=conv.target_system,
                factor=0.5,
                method=conv.method,
                effective_from=date.today(),
                approved_by=conv.approved_by,
            )
        )
    seeded.commit()
    token = login(client, "rachel@msu.example")
    client.post(
        f"/review/evaluations/{ev.id}/evidence-status",
        data={
            "source_kind": "registrar_issued",
            "authenticity": "verified",
            "verification_method": "학사처 발급본 대조",
            "csrf_token": token,
        },
    )

    # 판정 행은 한 글자도 바뀌지 않는다 (INSERT 전용)
    seeded.expire_all()
    assert row_of(seeded.get(Decision, decision.id)) == before  # type: ignore[arg-type]
    # 내보내기·리포트·학생 화면은 판정 때 과목 코드와 인정 학점을 보여 준다
    assert export_row(client, decision.id) == exported
    report = client.get(f"/evaluations/{ev.id}/report").text
    assert old_code in report and "MATH 9999" not in report.split("판정 근거")[0] and "인정 2학점" in report
    login(client, "jiwon@student.example")
    page = client.get(f"/student/evaluations/{ev.id}").text
    assert old_code in page and "인정 2학점" in page
    api = client.get(f"/api/v1/evaluations/{ev.id}").json()
    assert api["decision"]["target_course"] == old_code
    assert prof.id == before["decided_by"]
