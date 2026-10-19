"""알림 페이지 나누기(P14)와 동등 과목표 전체 검색(P09)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Notification, User
from tests.conftest import login

HEADER = "source_institution,source_course,target_course,result,decided_on,note\n"
HANKUK = "Hankuk University (한국대학교)"


def test_notifications_are_paged_and_keep_unread_marks(client: TestClient, seeded: Session) -> None:
    prof = seeded.scalars(select(User).where(User.email == "mbrown@msu.example")).one()
    seeded.add_all(Notification(user_id=prof.id, kind="test", message=f"알림 번호 {i:02d}") for i in range(55))
    seeded.commit()
    login(client, prof.email)

    first = client.get("/notifications").text
    assert "알림 번호 54" in first and "알림 번호 05" in first and "알림 번호 04" not in first
    assert "1 / 2 페이지" in first and "/notifications?page=2" in first
    assert first.count('class="dot ') >= 50  # 읽기 전 상태로 보여 주고
    assert client.get("/notifications/count").text == ""  # 열면 모두 읽음

    second = client.get("/notifications?page=2").text
    assert "알림 번호 04" in second and "알림 번호 00" in second and "알림 번호 05" not in second
    assert "2 / 2 페이지" in second and 'class="dot ' not in second
    assert "알림 번호 00" in client.get("/notifications?page=9").text  # 범위를 넘으면 마지막 페이지


def test_equivalency_table_search_filters_and_pages(client: TestClient, seeded: Session) -> None:
    token = login(client, "rachel@msu.example")
    rows = [f"{HANKUK},PHY {100 + i},,none,2018-03-0{1 + i % 9},메모{i}\n" for i in range(52)]
    rows.append(f"{HANKUK},Linear Algebra,MATH 2568,direct,2021-02-01,선형대수 직접 인정\n")
    r = client.post(
        "/review/equivalencies",
        files={"file": ("eq.csv", (HEADER + "".join(rows)).encode(), "text/csv")},
        data={"csrf_token": token},
    )
    assert "53건을 가져왔어요" in r.text

    page = client.get("/review/equivalencies").text
    assert "이력 53건 중 1–50" in page and "1 / 2 페이지" in page
    assert "MATH 2568" in page and "Linear Algebra" in page  # 대상 과목 코드·이름과 출신 대학까지 보여 준다

    by_target = client.get("/review/equivalencies", params={"q": "linear alg"}).text
    assert "이력 1건 중 1–1" in by_target and "선형대수 직접 인정" in by_target
    assert "이력 1건" in client.get("/review/equivalencies", params={"q": "2568"}).text
    assert "이력 53건" in client.get("/review/equivalencies", params={"q": "hankuk"}).text  # 출신 대학 이름
    assert "이력 1건" in client.get("/review/equivalencies", params={"result": "direct"}).text
    assert "이력 52건" in client.get("/review/equivalencies", params={"result": "none", "q": "PHY"}).text
    second = client.get("/review/equivalencies", params={"page": 2}).text
    assert "이력 53건 중 51–53" in second
    empty = client.get("/review/equivalencies", params={"q": "100%_없음"}).text
    assert "조건에 맞는 이력이 없어요." in empty  # %·_는 글자 그대로 찾는다
    assert client.get("/review/equivalencies", params={"result": "bogus"}).status_code == 200  # 모르는 값은 전체

    login(client, "mbrown@msu.example")
    assert client.get("/review/equivalencies").status_code == 403
