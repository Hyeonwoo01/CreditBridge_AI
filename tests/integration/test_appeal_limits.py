"""이의 신청 제한: 직접 인정은 받지 않고, 과목당 한 번(기각·재판정으로 끝나면 다시 못 냄). 학과 사무실 방문 안내."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Appeal
from tests.conftest import login
from tests.integration.test_review_extras import approve, reject
from tests.integration.test_workflow import professor_for

REASON = "학점 차이를 고려해 다시 검토해 주시면 좋겠습니다. 실험 보고서가 있어요."
OFFICE = "학과 사무실을 직접 찾아 문의해 주세요"


def test_direct_decision_cannot_be_appealed(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    approve(client, ev, token)  # AI 추천(직접 인정) 그대로 확정
    token = login(client, "jiwon@student.example")
    page = client.get(f"/student/evaluations/{ev.id}").text
    assert "직접 인정된 과목은 이의 신청을 받지 않아요" in page and OFFICE in page
    assert f"/student/evaluations/{ev.id}/appeal" not in page
    assert f"/student/evaluations/{ev.id}/appeal" not in client.get("/student/appeals").text

    r = client.get(f"/student/evaluations/{ev.id}/appeal")  # 주소로 들어와도 작성 화면 대신 안내
    assert "이의 신청 작성" not in r.text and "직접 인정된 과목은 이의 신청을 받지 않아요" in r.text
    r = client.post(f"/student/evaluations/{ev.id}/appeal", data={"reason": REASON, "csrf_token": token})
    assert r.status_code == 422 and OFFICE in r.text
    assert not seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).all()


def test_dismissed_appeal_cannot_be_filed_again(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)
    token = login(client, "jiwon@student.example")
    assert f"/student/evaluations/{ev.id}/appeal" in client.get("/student/appeals").text  # 불인정은 낼 수 있다
    client.post(f"/student/evaluations/{ev.id}/appeal", data={"reason": REASON, "csrf_token": token})
    appeal = seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()

    staff = login(client, "rachel@msu.example")
    client.post(
        f"/review/appeals/{appeal.id}", data={"action": "dismiss", "note": "근거가 충분해요", "csrf_token": staff}
    )

    token = login(client, "jiwon@student.example")
    appeals_page = client.get("/student/appeals").text
    assert "이 과목은 다시 이의 신청할 수 없어요" in appeals_page and OFFICE in appeals_page
    assert f"/student/evaluations/{ev.id}/appeal" not in appeals_page
    page = client.get(f"/student/evaluations/{ev.id}").text
    assert "이의 신청은 과목당 한 번" in page and f"/student/evaluations/{ev.id}/appeal" not in page
    r = client.post(f"/student/evaluations/{ev.id}/appeal", data={"reason": REASON, "csrf_token": token})
    assert r.status_code == 422 and "다시 신청할 수 없어요" in r.text
    assert len(seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).all()) == 1
