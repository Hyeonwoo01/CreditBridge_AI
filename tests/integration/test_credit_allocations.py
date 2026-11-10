"""학점 배분 원장 (리뷰 v3 P0-3): 여러 출신 과목 합쳐 인정(N:1), 출신 학점 이중 사용·대상 과목 이중 인정 차단."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Course, CreditAllocation, Institution, Syllabus
from backend.repositories import allocations as allocation_repo
from tests.conftest import login
from tests.integration.test_pipeline import latest
from tests.integration.test_workflow import assign, reviewer_of, submitted_request


def _active(db: Session) -> list[CreditAllocation]:
    db.expire_all()
    return list(db.scalars(select(CreditAllocation).where(CreditAllocation.status == "active")))


def test_combined_courses_share_credits_without_double_counting(client: TestClient, seeded: Session) -> None:
    rid = submitted_request(client, seeded, "calculus.txt", "linear_algebra_detailed.txt")
    calc, linear = latest(seeded, "calculus.txt", rid), latest(seeded, "linear_algebra_detailed.txt", rid)
    assign(client, calc, linear)
    prof = reviewer_of(seeded, calc)
    token = login(client, prof.email)
    page = client.get(f"/professor/evaluations/{calc.id}").text
    assert "함께 인정할 출신 과목" in page and f'value="{linear.syllabus_id}"' in page

    url = f"/professor/evaluations/{calc.id}/decision"
    r = client.post(
        url,
        data={
            "action": "reject",
            "reason_codes": ["level_difference"],
            "combined_syllabus_ids": [str(linear.syllabus_id)],
            "csrf_token": token,
        },
    )
    assert r.status_code == 422 and "불인정에는 함께" in r.text
    r = client.post(url, data={"action": "approve", "combined_syllabus_ids": ["999999"], "csrf_token": token})
    assert r.status_code == 422 and "목록에서 골라" in r.text

    # 미적분(3) + 선형대수(3)를 합쳐 MATH 1151(4학점)으로: 과목별 남은 학점에 비례해 2 + 2
    r = client.post(
        url,
        data={
            "action": "approve",
            "accepted_credits": "4",
            "combined_syllabus_ids": [str(linear.syllabus_id)],
            "csrf_token": token,
        },
    )
    assert r.status_code == 200
    rows = _active(seeded)
    assert sorted((a.syllabus_id, a.credits) for a in rows) == sorted(
        [(calc.syllabus_id, 2.0), (linear.syllabus_id, 2.0)]
    )
    math1151 = seeded.scalars(select(Course).where(Course.code == "MATH 1151")).one()
    assert {a.target_course_id for a in rows} == {math1151.id}

    # 학생: 선형대수는 '다른 과목과 합쳐 인정', 확정 학점은 원장 합계 4 (6이 아님)
    login(client, "jiwon@student.example")
    report = client.get(f"/student/requests/{rid}").text
    assert "다른 과목과 합쳐 인정" in report and "→ MATH 1151" in report
    assert "출신 2과목을 합쳐 인정" in client.get(f"/student/evaluations/{calc.id}").text
    login(client, "rachel@msu.example")
    assert "MATH 101 + MATH 201" in client.get("/review/export.csv").text

    # 선형대수 자체 판정: 같은 대상 과목은 두 번 인정할 수 없고, 남은 학점(1)보다 많이 쓸 수 없다
    la_prof = reviewer_of(seeded, linear)
    token = login(client, la_prof.email)
    url = f"/professor/evaluations/{linear.id}/decision"
    r = client.post(
        url,
        data={
            "action": "modify",
            "result": "direct",
            "target_course_id": str(math1151.id),
            "accepted_credits": "1",
            "reason_codes": ["other"],
            "reason_memo": "m",
            "csrf_token": token,
        },
    )
    assert r.status_code == 422 and "이미 MATH 1151로 인정받았어요" in r.text
    r = client.post(
        url,
        data={
            "action": "modify",
            "result": "elective",
            "accepted_credits": "3",
            "reason_codes": ["other"],
            "reason_memo": "m",
            "csrf_token": token,
        },
    )
    assert r.status_code == 422 and "아직 쓰지 않은 학점(1)" in r.text
    r = client.post(
        url,
        data={
            "action": "modify",
            "result": "elective",
            "accepted_credits": "1",
            "reason_codes": ["other"],
            "reason_memo": "m",
            "acknowledge_conflict": "true",  # 작년 선형대수 직접 인정 이력과 결과가 다름
            "csrf_token": token,
        },
    )
    assert r.status_code == 200
    linear_total = sum(a.credits for a in _active(seeded) if a.syllabus_id == linear.syllabus_id)
    assert linear_total == 3.0  # 출신 3학점을 넘지 않음

    # 재판정이면 이전 배분은 지우지 않고 대체됨으로 바뀐다
    decision_id = max(a.decision_id for a in _active(seeded))
    assert allocation_repo.supersede_for_evaluation(seeded, calc.id, decision_id) == 2
    seeded.commit()
    assert len(seeded.scalars(select(CreditAllocation)).all()) == 3  # 지운 줄 없음


def test_combining_needs_known_conversion(client: TestClient, seeded: Session) -> None:
    rid = submitted_request(client, seeded, "calculus.txt", "linear_algebra_detailed.txt")
    calc, linear = latest(seeded, "calculus.txt", rid), latest(seeded, "linear_algebra_detailed.txt", rid)
    assign(client, calc)
    hankuk = seeded.scalars(select(Institution).where(Institution.country == "KR")).one()
    hankuk.credit_system = None
    seeded.commit()
    token = login(client, reviewer_of(seeded, calc).email)
    r = client.post(
        f"/professor/evaluations/{calc.id}/decision",
        data={
            "action": "approve",
            "accepted_credits": "4",
            "combined_syllabus_ids": [str(linear.syllabus_id)],
            "csrf_token": token,
        },
    )
    assert r.status_code == 422 and "합쳐 인정할 수 없어요" in r.text
    assert _active(seeded) == []
    assert seeded.get(Syllabus, linear.syllabus_id) is not None
