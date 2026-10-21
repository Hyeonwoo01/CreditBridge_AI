"""문서 삭제 요청: 기관 관리자도 접수 때부터 알림·배지로 알고, 승인하면 요청이 종료돼
학생 화면은 종료 안내로 바뀌고 심사 큐·교수 목록에서 빠진다 (판정 기록은 남는다)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import PrivacyRequest, TransferRequest
from backend.repositories import evaluations as evaluation_repo
from tests.conftest import login
from tests.integration.test_pipeline import latest
from tests.integration.test_review_extras import notes_for
from tests.integration.test_workflow import reviewer_of, submitted_request


def test_admin_sees_new_deletion_request_and_approval_closes_the_request(client: TestClient, seeded: Session) -> None:
    rid = submitted_request(client, seeded, "calculus.txt")
    calc = latest(seeded, "calculus.txt", rid)
    prof = reviewer_of(seeded, calc)  # 제출 때 학과 교수에게 자동 배정됨

    token = login(client, "jiwon@student.example")
    client.post(f"/student/requests/{rid}/delete-documents", data={"csrf_token": token})
    # 심사관 처리 전이라도 기관 관리자에게 알림과 메뉴 배지가 간다
    assert any("문서 삭제 요청이 접수됐어요" in m for m in notes_for(seeded, "admin@msu.example"))
    token = login(client, "admin@msu.example")
    assert "승인할 삭제 요청 1건" in client.get("/admin/stats").text
    privacy = seeded.scalars(select(PrivacyRequest).where(PrivacyRequest.transfer_request_id == rid)).one()
    client.post(f"/admin/privacy/{privacy.id}", data={"csrf_token": token})
    assert "승인할 삭제 요청" not in client.get("/admin/stats").text

    # 요청 종료: 배정이 끝나고 담당 교수에게 알리며, 심사 큐·교수 목록에서 빠진다
    seeded.expire_all()
    assert seeded.get(TransferRequest, rid).status == "closed"  # type: ignore[union-attr]
    assert evaluation_repo.active_assignment(seeded, calc.id) is None
    assert any("심사가 종료됐어요" in m for m in notes_for(seeded, prof.email))
    assert "MATH 101" not in client.get("/admin/assignments?show=all").text
    login(client, "rachel@msu.example")
    assert f'/review/evaluations/{calc.id}"' not in client.get("/review?tab=all").text
    login(client, prof.email)
    assert f"/professor/evaluations/{calc.id}" not in client.get("/professor").text

    # 학생: 진행 단계 대신 종료 안내, 목록은 '문서 삭제로 종료', 더 올리거나 다시 삭제 요청할 수 없다
    token = login(client, "jiwon@student.example")
    page = client.get(f"/student/requests/{rid}").text
    assert "이 요청은 문서 삭제로 종료됐어요" in page and "심사 진행 현황" not in page
    assert "내 문서 삭제 요청" not in page and "학사처에 심사 요청" not in page
    assert "문서 삭제로 종료" in client.get("/student").text
    r = client.post(
        f"/student/requests/{rid}/syllabi",
        files=[("files", ("a.pdf", b"%PDF-1.4", "application/pdf"))],
        data={"csrf_token": token},
    )
    assert "문서를 삭제해 종료된 요청이에요" in r.text
    r = client.post(f"/student/requests/{rid}/delete-documents", data={"csrf_token": token})
    assert "이미 문서를 삭제한 요청이에요" in r.text


def test_admin_assignment_board_marks_automatic_assignment(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt")
    login(client, "admin@msu.example")
    page = client.get("/admin/assignments?show=all").text
    assert "자동 배정 " in page and "배정할 심사 건이 없어요" in client.get("/admin/assignments").text


def test_deletion_also_removes_appeals_from_student_view(client: TestClient, seeded: Session) -> None:
    """이의 신청까지 끝난 요청을 문서 삭제하면 학생 이의 신청 목록·과목 화면에서 함께 사라지고 사유도 지운다."""
    from backend.models import Appeal
    from tests.integration.test_review_extras import reject
    from tests.integration.test_student_dashboard import professor_for

    ev, _, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)
    rid = ev.transfer_request_id
    token = login(client, "jiwon@student.example")
    reason = "미분과 적분의 응용까지 15주 동안 배웠고 강의 노트와 시험지로 증명할 수 있어요."
    client.post(f"/student/evaluations/{ev.id}/appeal", data={"reason": reason, "csrf_token": token})
    appeal = seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()
    token = login(client, "rachel@msu.example")
    client.post(f"/review/appeals/{appeal.id}", data={"action": "dismiss", "note": "근거 충분", "csrf_token": token})

    token = login(client, "jiwon@student.example")
    assert reason in client.get("/student/appeals").text
    client.post(f"/student/requests/{rid}/delete-documents", data={"csrf_token": token})
    token = login(client, "admin@msu.example")
    privacy = seeded.scalars(select(PrivacyRequest).where(PrivacyRequest.transfer_request_id == rid)).one()
    client.post(f"/admin/privacy/{privacy.id}", data={"csrf_token": token})

    seeded.expire_all()
    assert seeded.get(Appeal, appeal.id).reason == ""  # type: ignore[union-attr]
    token = login(client, "jiwon@student.example")
    page = client.get("/student/appeals").text
    assert reason not in page and "근거 충분" not in page and "MATH 101" not in page
    page = client.get(f"/student/evaluations/{ev.id}").text
    assert "근거 충분" not in page and "이의 신청 · " not in page
    assert "문서가 삭제돼 종료된 요청의 과목은 이의 신청할 수 없어요" in page
    r = client.post(f"/student/evaluations/{ev.id}/appeal", data={"reason": reason, "csrf_token": token})
    assert "문서가 삭제돼 종료된 요청의 과목은 이의 신청할 수 없어요" in r.text
    login(client, "rachel@msu.example")
    assert "근거 충분" not in client.get("/review/appeals").text  # 처리 목록에서도 빠진다
