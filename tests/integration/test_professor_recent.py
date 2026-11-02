"""교수 홈 '최근 판정한 심사': 판정을 마쳐 배정 목록에서 빠진 심사를 다시 열어 볼 수 있다."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Decision, TransferRequest, User
from tests.conftest import login
from tests.integration.test_workflow import professor_for


def test_recent_decisions_on_professor_home(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "calculus.txt")
    home = client.get("/professor").text
    assert "아직 판정한 심사가 없어요." in home and f"/professor/evaluations/{ev.id}" in home  # 배정 목록에만 있음

    client.post(f"/professor/evaluations/{ev.id}/decision", data={"action": "approve", "csrf_token": token})
    home = client.get("/professor").text
    assert "배정된 심사 0건" in home and "최근 판정한 심사" in home
    assert f'href="/professor/evaluations/{ev.id}"' in home and "MATH 101" in home and "MATH 1151" in home
    assert "승인" in home and "직접 인정" in home
    assert client.get(f"/professor/evaluations/{ev.id}").status_code == 200  # 다시 열 수 있다

    # 다른 판정(이의 신청 재판정)이 뒤에 생기면 지금 유효한 결과를 함께 보여 주고, 문서 삭제로 끝난 요청은 표시한다
    other = seeded.scalars(select(User).where(User.role == "professor", User.id != prof.id)).first()
    assert other is not None
    seeded.add(
        Decision(
            course_evaluation_id=ev.id,
            decided_by=other.id,
            action="modify",
            result="elective",
            reason_codes=["other"],
            reason_memo="재판정",
            ai_recommendation_snapshot={},
        )
    )
    request = seeded.get(TransferRequest, ev.transfer_request_id)
    assert request is not None
    request.status = "closed"
    seeded.commit()
    home = client.get("/professor").text
    assert "이의 신청 재판정 → 선택 인정" in home and "문서 삭제로 종료" in home

    # 다른 교수의 목록에는 내가 판정한 건이 나오지 않는다 (그 교수가 판정한 건만)
    login(client, other.email)
    home = client.get("/professor").text
    assert f'href="/professor/evaluations/{ev.id}"' in home  # 재판정한 교수에게는 나옴
    assert "이의 신청 재판정 →" not in home  # 자기 판정이 최신이라 덧붙이지 않음
    third = seeded.scalars(select(User).where(User.role == "professor", User.id.not_in([prof.id, other.id]))).first()
    assert third is not None
    login(client, third.email)
    assert f"/professor/evaluations/{ev.id}" not in client.get("/professor").text

    # 영어 화면
    token = login(client, prof.email)
    page = client.post("/lang", data={"lang": "en", "next": "/professor", "csrf_token": token}).text
    assert "Recently decided" in page and "Re-decided on appeal → " in page
