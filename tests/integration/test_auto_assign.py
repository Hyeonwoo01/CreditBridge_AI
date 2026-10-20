"""정보가 충분한 과목은 학생이 심사를 요청하는 순간 학과 교수에게 자동 배정된다. 나머지는 심사관 대기열에 남는다."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Assignment, AuditLog, Notification, Syllabus, TransferRequest, User
from backend.repositories import evaluations as evaluation_repo
from tests.conftest import demo_pdf, login
from tests.integration.test_pipeline import latest, new_request, upload
from tests.integration.test_workflow import reviewer_of


def test_submit_auto_assigns_only_courses_with_enough_information(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt", "linear_algebra_sparse.txt", "korean_history.txt")
    calc = latest(seeded, "calculus.txt", rid)
    assert evaluation_repo.active_assignment(seeded, calc.id) is None  # 제출 전(사전 시뮬레이션)에는 배정하지 않는다

    r = client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token})
    assert "1과목은 학과 교수에게 바로 배정됐어요" in r.text

    prof = reviewer_of(seeded, calc)
    assert prof.department_name == "Mathematics"
    assignment = seeded.scalars(select(Assignment).where(Assignment.course_evaluation_id == calc.id)).one()
    assert assignment.assigned_by is None  # 시스템 자동 배정
    log = seeded.scalars(select(AuditLog).where(AuditLog.action == "assignment.create")).one()
    assert log.actor_id is None and log.payload_json["auto"] is True
    note = seeded.scalars(select(Notification).where(Notification.user_id == prof.id)).one()
    assert "새 심사가 배정됐어요" in note.message

    # 정보 부족(선형대수 부실형)·대응 과목 없음(한국사)은 심사관 대기열에 남는다
    sparse = latest(seeded, "linear_algebra_sparse.txt", rid)
    history = latest(seeded, "korean_history.txt", rid)
    assert evaluation_repo.active_assignment(seeded, sparse.id) is None
    assert evaluation_repo.active_assignment(seeded, history.id) is None
    token = login(client, "rachel@msu.example")
    assert "교수 배정이 필요한 과목 2개" in client.get("/review").text

    # 심사관이 보완 자료를 요청하고, 학생이 낸 자료로 다시 분석해 정보가 충분해지면 그때 자동 배정한다
    r = client.post(
        f"/review/evaluations/{sparse.id}/materials", data={"items": ["주차별 상세 강의 계획"], "csrf_token": token}
    )
    assert "보완 자료를 요청했어요" in r.text
    token = login(client, "jiwon@student.example")
    syllabus = seeded.get(Syllabus, sparse.syllabus_id)
    assert syllabus is not None
    r = client.post(
        f"/student/syllabi/{syllabus.id}/supplement",
        files={"file": ("weekly_plan.pdf", demo_pdf("linear_algebra_detailed.txt"), "application/pdf")},
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    again = latest(seeded, "linear_algebra_sparse.txt", rid)
    assert again.id != sparse.id and again.recommendation == "direct"
    assert reviewer_of(seeded, again).department_name == "Mathematics"
    login(client, "rachel@msu.example")
    assert "교수 배정이 필요한 과목 1개" in client.get("/review").text  # 한국사만 남음


def test_evaluator_picks_professor_for_case_without_candidate(client: TestClient, seeded: Session) -> None:
    """후보 과목이 없는 선택 인정 건: 심사관이 심사 건 화면에서 교수를 골라 배정하고, 바꿀 수도 있다."""
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "korean_history.txt")
    client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token})
    history = latest(seeded, "korean_history.txt", rid)
    assert history.candidate_course_id is None and evaluation_repo.active_assignment(seeded, history.id) is None

    token = login(client, "rachel@msu.example")
    r = client.post("/review/assign", data={"evaluation_ids": [history.id], "csrf_token": token})
    assert "&#39;담당 교수 배정&#39;에서 교수를 골라 주세요" in r.text  # 일괄 배정은 학과를 몰라 안내만

    page = client.get(f"/review/evaluations/{history.id}").text
    assert "담당 교수 배정" in page and "학생의 편입 전공 학과 교수를 먼저 골라 두었어요" in page
    major = seeded.get(TransferRequest, rid).major  # type: ignore[union-attr]
    professors = sorted(seeded.scalars(select(User).where(User.role == "professor")), key=lambda p: p.name)
    first = next(p for p in professors if p.department_name == major)
    second = next(p for p in professors if p.id != first.id and p.is_active)
    assert f'value="{first.id}" selected' in page  # 학생 편입 전공 학과의 첫 교수가 기본 선택

    r = client.post(f"/review/evaluations/{history.id}/assign", data={"reviewer_id": first.id, "csrf_token": token})
    assert f"{first.name} 교수에게 배정했어요" in r.text
    assert reviewer_of(seeded, history).id == first.id
    r = client.post(f"/review/evaluations/{history.id}/assign", data={"reviewer_id": first.id, "csrf_token": token})
    assert "이미 그 교수에게 배정돼 있어요" in r.text

    # 다른 교수로 바꾸면 새 교수와 이전 교수 모두 알림을 받는다
    client.post(f"/review/evaluations/{history.id}/assign", data={"reviewer_id": second.id, "csrf_token": token})
    seeded.expire_all()
    assert reviewer_of(seeded, history).id == second.id
    moved = seeded.scalars(select(Notification).where(Notification.user_id == first.id)).all()
    assert any("다른 교수에게 넘어갔어요" in n.message for n in moved)

    # 심사관만 (교수·학생은 이 경로로 배정할 수 없다)
    token = login(client, "jiwon@student.example")
    r = client.post(f"/review/evaluations/{history.id}/assign", data={"reviewer_id": first.id, "csrf_token": token})
    assert r.status_code == 403
